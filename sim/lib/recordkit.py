"""Shared record plumbing of the sim/*/collect.py graders.

One copy of what every bench's collector needs to write an append-only evidence record: the klt corner-id
parser, the file hash, the environment header (git sha, UTC stamp, klt / ngspice versions, the remote-job
subset of a klt report, files_sha256), the corner-matrix coverage verdict of the handed klt sim report,
and the refuse-to-overwrite writer. A fix here reaches every bench.
This module is itself hashed into every record's files_sha256 (files_sha256() adds it), so a record
still pins every file that graded it.

Imported by the collectors as `import recordkit` after they put sim/lib on sys.path. Run its tests:
python3 -I -m unittest discover sim/lib
"""
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

LIB = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(LIB, "..", ".."))
IDRE = re.compile(r"^(?P<proc>[a-z]+)/(?P<vin>[0-9.]+)V/(?P<temp>-?[0-9.]+)C/params:(?P<params>.*)$")
# runner_klt_version / client_klt_version / runner_compatibility are which klt actually produced the
# numbers: on a batch run header()'s local `klt --version` names the grading host, not the fleet runner.
REMOTE_FIELDS = ("provider", "job_id", "instance_type", "lifecycle", "elapsed_seconds", "state",
                 "runner_klt_version", "client_klt_version", "runner_compatibility", "region")
# A sharded (split) batch run moves job identity inside remote.fleet[] -- one job block per shard,
# null where a shard was lost -- and leaves only the job_ids / worst-of runner_compatibility
# roll-ups at the top level (klayout-tools#5522, settled by #5529), so the single-job scalars are
# all absent. remote_subset() summarises that shape; these name what the summary rolls up.
FLEET_IDENTITY_FIELDS = ("provider", "region", "instance_type", "lifecycle", "state")
FLEET_VERSION_FIELDS = ("runner_klt_version", "client_klt_version")
# klt's own worst-of precedence (sim_batch_features._COMPATIBILITY_RANK): a proved skew outranks
# an unreadable or lost shard, which outranks a clean match.
COMPATIBILITY_RANK = ("mismatch", "unknown", "match")
JOB_IDS_MAX = 32  # beyond this a record carries a sha256 of the sorted ids, not the list
GRADEABLE_STATUS = ("pass", "fail")  # a klt corner grades only once it reached a verdict
DIAG_MSG_TAIL = 90  # chars of a diagnostic message kept in a no-waveform reason


def parse_corner(cid):
    """klt corner id -> ({process, vin_v, temp_c}, {param: float})."""
    m = IDRE.match(cid)
    if not m:
        raise ValueError("unrecognised corner id %r" % cid)
    params = {k: float(v) for k, v in (kv.split("=") for kv in m.group("params").split(","))}
    return {"process": m.group("proc"), "vin_v": float(m.group("vin")), "temp_c": float(m.group("temp"))}, params


def parse_id(cid, lfac_default=None):
    """Corner id of an iload bench -> process, vin_v, temp_c, iload_a; `lfac` when the id carries it
    (or lfac_default when that is not None)."""
    key, params = parse_corner(cid)
    key["iload_a"] = params["iload"]
    if "lfac" in params:
        key["lfac"] = params["lfac"]
    elif lfac_default is not None:
        key["lfac"] = lfac_default
    return key


def _msg_text(message):
    """A klt-supplied message as text, at the one point it becomes one: a str passes through
    unchanged, a falsy value stays '' (what both readers already make of a missing message),
    and any other non-string becomes repr(message) so it can neither raise nor slice as one."""
    if isinstance(message, str):
        return message
    return repr(message) if message else ""


def waveform_or_reason(corner, msg_tail=DIAG_MSG_TAIL):
    """(raw path, None) when a klt corner has a gradeable waveform, else (None, reason).

    A unit carries a value only if klt ran its corner to a verdict (`pass` or `fail`) and
    the `waveform.raw` it named is on disk; a corner that timed out, errored, or never wrote
    its raw carries none, and the record says why instead. The reason names the klt status and
    the first diagnostic as (code, last `msg_tail` chars of its message) -- the code alone does
    not distinguish, say, two different `spice_error`s. One format for every bench.
    """
    raw = (corner.get("artifacts") or {}).get("raw")
    if corner.get("status") in GRADEABLE_STATUS and raw and os.path.exists(raw):
        return raw, None
    diag = [(d.get("code"), _msg_text(d.get("message"))[-msg_tail:]) for d in corner.get("diagnostics") or []][:1]
    return None, "no waveform: klt status %s %s" % (corner.get("status"), diag)


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def files_sha256(here, files, root_files=(), lib_files=()):
    """Hash of every file that graded a record. `files` are relative to the bench dir `here` and keep the
    given name; `root_files` are repo-root relative; `lib_files` are sim/lib names (keyed sim/lib/<name>).
    recordkit.py is always included."""
    out = {f: sha256(os.path.join(here, f)) for f in files}
    for f in root_files:
        out[f] = sha256(os.path.join(ROOT, f))
    for f in tuple(lib_files) + ("recordkit.py",):
        out["sim/lib/" + f] = sha256(os.path.join(LIB, f))
    return out


def ngspice_banner():
    """Second line of `ngspice --version` (the version string)."""
    out = subprocess.run(["ngspice", "--version"], capture_output=True, text=True).stdout
    return (out.split("\n") + [""])[1].strip()


def header(here):
    """(utc stamp, git short sha, {utc, repo_commit, klt}) for a record written from bench dir `here`."""
    sha = subprocess.check_output(["git", "-C", here, "rev-parse", "--short=12", "HEAD"], text=True).strip()
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    klt = subprocess.check_output(["klt", "--version"], text=True).strip()
    return ts, sha, {"utc": ts, "repo_commit": sha, "klt": klt}


def fleet_runner_compatibility(fleet):
    """Worst-of runner_compatibility across fleet[] -- klt rolled this up at the top level itself
    since klayout-tools#5529; this re-derives it for an older report that carries only fleet[].
    A lost (null) shard, a field-less pre-#2719 block, or a value this klt does not define folds
    into "unknown", and an empty fleet degrades to "unknown": the summary never reads as clean
    on evidence it does not have."""
    statuses = {e.get("runner_compatibility") if isinstance(e, dict)
                and e.get("runner_compatibility") in COMPATIBILITY_RANK else "unknown"
                for e in fleet}
    return next((s for s in COMPATIBILITY_RANK if s in statuses), "unknown")


def fleet_summary(remote):
    """Record-ready roll-up of a sharded batch report's environment.remote (issue #232).

    Splitting (batch.max_units_per_job / job_ceiling_check "split" / remote.hosts > 1) moves job
    identity inside remote.fleet[], so a reader written against the single-job scalars recorded
    an all-None provenance block on exactly the large grids where provenance matters most. The
    summary states the whole fleet instead: the shard count and lost slots; provider / region /
    instance_type / lifecycle / state as the bare value while the shards agree, a sorted list
    where they differ, None where no shard names one; sorted runner/client klt version sets;
    the worst-of runner_compatibility (klt's own top-level roll-up when present, re-derived from
    fleet[] otherwise); the summed elapsed_seconds; and job_ids in shard order -- a sha256 of
    the sorted ids once the list passes JOB_IDS_MAX."""
    fleet = remote.get("fleet") or []
    shards = [e for e in fleet if isinstance(e, dict)]
    out = {"job_count": len(fleet), "jobs_lost": len(fleet) - len(shards)}
    for f in FLEET_IDENTITY_FIELDS + FLEET_VERSION_FIELDS:
        vals = sorted({e.get(f) for e in shards if e.get(f) is not None})
        out[f] = None if not vals else (vals[0] if len(vals) == 1 and f in FLEET_IDENTITY_FIELDS else vals)
    out["runner_compatibility"] = remote.get("runner_compatibility") or fleet_runner_compatibility(fleet)
    elapsed = [e["elapsed_seconds"] for e in shards if isinstance(e.get("elapsed_seconds"), (int, float))]
    out["elapsed_seconds"] = sum(elapsed) if elapsed else None
    ids = [e["job_id"] for e in shards if e.get("job_id")] or remote.get("job_ids") or None
    if ids and len(ids) > JOB_IDS_MAX:
        ids = "sha256:" + hashlib.sha256(json.dumps(sorted(ids)).encode()).hexdigest()
    out["job_ids"] = ids
    return out


def backend_resolved(report):
    """environment.backend.resolved of a klt sim report: which backend actually executed
    (--backend > request.backend > $KLT_SIM_BACKEND > local, klayout-tools issue #2977). None
    when the report carries no such block."""
    backend = (report.get("environment") or {}).get("backend")
    return backend.get("resolved") if isinstance(backend, dict) else None


def remote_subset(report, fields=REMOTE_FIELDS):
    """The remote-job fields of a klt sim report's environment: the single-job scalar block as
    before (`fields`), or -- when the run was sharded (environment.remote.fleet is a list) --
    fleet_summary(), so a split run still states where it ran, on which klt, and under which job
    ids instead of an all-None block (issue #232). A local run has no remote block and keeps the
    all-None scalar shape."""
    remote = (report.get("environment") or {}).get("remote") or {}
    if isinstance(remote.get("fleet"), list):
        return fleet_summary(remote)
    return {k: remote.get(k) for k in fields}


def report_env(report, path, fields=REMOTE_FIELDS):
    """{report file, backend, status, remote subset} of one klt sim report. The old remote["jobs"]
    read is gone: klt never wrote that key -- a sharded run's job list is remote.fleet[], which
    remote_subset() summarises into the remote block, ids included."""
    return {"report": os.path.basename(path), "status": report.get("status"),
            "backend": backend_resolved(report), "remote": remote_subset(report, fields)}


def _bounded_reason(message, tail=DIAG_MSG_TAIL):
    """One bounded, non-empty, host-free line out of a klt refusal message, in the order the
    block's other fields already follow: coerce the message to text first (_msg_text -- a
    non-string envelope message neither raises nor slices as one), keep the last non-empty
    line (a traceback keeps only its exception line, not its frame lines -- those carry the
    host paths), basename every path-shaped token the way `corner_matrix_check` basenames its
    matrix/report, then tail-slice to `tail` chars like waveform_or_reason. A clean one-line
    refusal passes through unchanged; a message that sanitizes to nothing keeps a non-empty
    sentinel, so a recorded error is never falsy."""
    line = (_msg_text(message).strip().splitlines() or [""])[-1]
    words = [os.path.basename(w.rstrip("/")) or w if "/" in w else w for w in line.split()]
    return " ".join(words)[-tail:] or "klt refused with an empty message"


def corner_matrix_check(matrix, report):
    """Record-ready verdict of `klt corner-matrix check MATRIX --report REPORT --format json`,
    the completeness check of the declared corner matrix (the matrix the bench's gen_requests.py
    wrote) against the klt sim report this collector was handed -- what actually simulated, not
    what the request declared.

    klt exit codes: 0 complete, 3 ran clean but incomplete -- both carry the verdict JSON on
    stdout, and both come back parsed: the matrix and report basenames plus matrix_size,
    observed_count and the six id lists (missing, extra, duplicate, not_simulated, non_finite,
    out_of_bounds). A klt refusal (exit 1: an unreadable file, an unknown matrix key, or a
    committed records/*.json with no corners[] array) comes back as an {"error": message} block
    naming the refusal instead of raising, so the collector can record it and then fail on it.
    The recorded message is bounded the way the block's other fields already are
    (_bounded_reason): one DIAG_MSG_TAIL line, exception line only if klt crashed instead of
    emitting its envelope, paths basenamed -- a host path or a traceback never lands in the
    append-only record.

    Coverage is judged on missing/extra/duplicate ONLY (coverage_failures): klt's own `complete`
    flag and exit status are NOT a coverage verdict -- they fold the per-corner lists in, and
    out_of_bounds is every corner whose klt status is `fail`, so a bench that correctly records
    a failing corner reports complete: false. Those lists are recorded, never gated.
    """
    proc = subprocess.run(
        ["klt", "corner-matrix", "check", matrix, "--report", report, "--format", "json"],
        capture_output=True, text=True)
    verdict = None
    if proc.returncode in (0, 3):
        try:
            verdict = json.loads(proc.stdout)
        except ValueError:
            verdict = None
    if isinstance(verdict, dict) and "matrix_size" in verdict:
        out = {"matrix": os.path.basename(matrix), "report": os.path.basename(report)}
        out.update({k: verdict[k] for k in ("matrix_size", "observed_count", "missing", "extra",
                                            "duplicate", "not_simulated", "non_finite", "out_of_bounds")})
        return out
    message = (proc.stderr.strip() or proc.stdout.strip()
               or "klt corner-matrix exited %d with no output" % proc.returncode)
    try:  # the --format json refusal envelope: {"error": {"command": ..., "message": ...}}
        message = json.loads(message)["error"]["message"]
    except (ValueError, KeyError, TypeError):
        pass
    return {"matrix": os.path.basename(matrix), "report": os.path.basename(report),
            "error": _bounded_reason(message)}


def coverage_failures(entries):
    """One message per corner_matrix entry that is not exact coverage of its matrix: a klt
    refusal (key presence -- the gate fires whatever the recorded message contains, so a
    falsy message cannot pass silently), or a non-empty missing / extra / duplicate. The
    message names the counts. not_simulated / non_finite / out_of_bounds are per-corner
    verdicts, never a failure here (see corner_matrix_check)."""
    out = []
    for e in entries:
        if "error" in e:
            out.append("%s: corner-matrix refused the report (%s)" % (e["matrix"], e["error"]))
            continue
        counts = [(k, len(e[k])) for k in ("missing", "extra", "duplicate") if e.get(k)]
        if counts:
            out.append("%s: coverage incomplete: %s"
                       % (e["matrix"], ", ".join("%d %s" % (n, k) for k, n in counts)))
    return out


def coverage_exit(entries, tool="collect.py"):
    """Print one stderr line per coverage failure and 1 if there was one, else 0. The collector
    calls this AFTER writing its record -- a run that happened is evidence, so a coverage
    failure never suppresses it -- and on --dry, where there is no record to keep."""
    failures = coverage_failures(entries)
    for f in failures:
        print("%s: %s" % (tool, f), file=sys.stderr)
    return 1 if failures else 0


def write_record(path, rec, dry=False, tool="collect.py"):
    """Write rec as sorted-key JSON at path; records are append-only, so an existing path is refused
    (returns 1). Sorting makes a re-run of the same record byte-identical."""
    if dry:
        print(path)
        return 0
    if os.path.exists(path):
        print("%s: records are append-only; %s exists" % (tool, path), file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print("%s: record %s" % (tool, path))
    return 0
