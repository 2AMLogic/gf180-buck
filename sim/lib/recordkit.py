"""Shared record plumbing of the sim/*/collect.py graders.

One copy of what every bench's collector needs to write an append-only evidence record: the klt corner-id
parser, the file hash, the environment header (git sha, UTC stamp, klt / ngspice versions, the remote-job
subset of a klt report, files_sha256) and the refuse-to-overwrite writer. A fix here reaches every bench.
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
REMOTE_FIELDS = ("provider", "job_id", "instance_type", "lifecycle", "elapsed_seconds", "state")


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


def remote_subset(report, fields=REMOTE_FIELDS):
    """The remote-job fields of a klt sim report's environment."""
    remote = (report.get("environment") or {}).get("remote") or {}
    return {k: remote.get(k) for k in fields}


def report_env(report, path, fields=REMOTE_FIELDS, jobs=False):
    """{report file, status, remote subset[, jobs]} of one klt sim report."""
    env = {"report": os.path.basename(path), "status": report.get("status"), "remote": remote_subset(report, fields)}
    if jobs:
        env["jobs"] = [j for j in ((report.get("environment") or {}).get("remote") or {}).get("jobs", [])] or None
    return env


def write_record(path, rec, dry=False):
    """Write rec as JSON at path; records are append-only, so an existing path is refused (returns 1)."""
    if dry:
        print(path)
        return 0
    if os.path.exists(path):
        print("collect.py: records are append-only; %s exists" % path, file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(json.dumps(rec, indent=1) + "\n")
    print("collect.py: record %s" % path)
    return 0
