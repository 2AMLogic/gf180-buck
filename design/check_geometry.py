#!/usr/bin/env python3
"""Netlist-level geometry pre-check (issue #116).

Stdlib only; needs no PDK and no klt. Reads every ``design/netlists/*.spice``,
joins ``+`` continuation lines, and for each MOSFET instance checks

  * finger width  W/nf   against the COMP minimum, and
  * gate length   L      against the gate-poly (channel length) minimum,

per device flavour. ``m`` is a device multiplier and does not change the finger
width, so it is reported but never enters the check. Layout-side checks
(``layout/check_layout.py``) only run after layout exists; this one runs on the
schematic netlist.

Usage:  python3 design/check_geometry.py [NETLIST ...]     (default: all netlists)
Exit:   0 = no new violation; 1 = a violation that is not on KNOWN_VIOLATIONS,
        or a KNOWN_VIOLATIONS entry that no longer matches a violation (stale);
        2 = a MOSFET instance could not be parsed.

Sources of the minimums (simulated design check, never a measurement):

  Rule            Value (um)  Applies to       Source / content hash
  --------------  ----------  ---------------  --------------------------------
  comp.width.1    0.22        *_03v3  W/nf     klt deck ``gf180mcu`` (DRM 7.5, DF.1a_LV),
                                               pinned klt 0.9.0, deck content hash
                                               sha256:cf44de63f0a5b01c1d09c4d58e0535e990aa4b070bcaae17fd3a94a67a1d97e1
                                               (the hash recorded in layout/drc/README.md)
  comp.width.mv.1 0.30        *_06v0  W/nf     same klt deck and hash (DF.1a_MV, inside Dualgate)
  PL.2_LV         0.28        *_03v3  L        NOT in the klt deck (it lists PL.2_MV as unmodelled and
                                               models poly2.width.1 = PL.1 0.18 um instead). Taken from
                                               the PDK's own klayout deck, rule_decks/poly2.rb, file
                                               sha256:98872935f83315cce2b59539594aee401f7f1e12e23ad7940cdb8d455cde3891
  PL.2_MV         0.70 nfet   *_06v0  L        same PDK file (``ngate_6v`` 0.7, ``pgate_6v`` 0.55)
                  0.55 pfet

  Caveat on the PL.2 file hash: it was read from the PDK revision installed on the
  host that wrote this table (open_pdks f6eeac7d..., gf180mcuA), not from the
  revision pinned in sim/pdk.json (c6d73a35..., gf180mcuD), which was not installed.
  Re-check the three PL.2 numbers against the pinned revision when it is available.
"""

from __future__ import annotations

import glob
import os
import re
import sys
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Minimums. Values are um; (rule id, value).
# ---------------------------------------------------------------------------
KLT_DECK_HASH = "sha256:cf44de63f0a5b01c1d09c4d58e0535e990aa4b070bcaae17fd3a94a67a1d97e1"
PDK_POLY2_HASH = "sha256:98872935f83315cce2b59539594aee401f7f1e12e23ad7940cdb8d455cde3891"

# Finger width (W/nf) by voltage class.
MIN_FINGER_W = {
    "03v3": ("comp.width.1", 0.22),
    "06v0": ("comp.width.mv.1", 0.30),
}
# Gate length by (voltage class, polarity).
MIN_L = {
    ("03v3", "nfet"): ("PL.2_LV", 0.28),
    ("03v3", "pfet"): ("PL.2_LV", 0.28),
    ("06v0", "nfet"): ("PL.2_MV", 0.70),
    ("06v0", "pfet"): ("PL.2_MV", 0.55),
}
RULE_SOURCE = {
    "comp.width.1": f"klt gf180mcu deck 0.9.0, {KLT_DECK_HASH}",
    "comp.width.mv.1": f"klt gf180mcu deck 0.9.0, {KLT_DECK_HASH}",
    "PL.2_LV": f"PDK rule_decks/poly2.rb, {PDK_POLY2_HASH}",
    "PL.2_MV": f"PDK rule_decks/poly2.rb, {PDK_POLY2_HASH}",
}

# ---------------------------------------------------------------------------
# Known violations: (netlist file name, instance name, rule id) -> owning issue.
# Each is printed as a warning. A new violation fails the check; an entry that
# no longer matches a violation also fails (stale entries must be removed).
# ---------------------------------------------------------------------------
KNOWN_VIOLATIONS = {
    ("gate_drive.spice", "XMP_HG5", "comp.width.mv.1"): "#109",
    ("gate_drive.spice", "XMP_LG5", "comp.width.mv.1"): "#109",
    ("buck_top.spice", "XMP_HG5", "comp.width.mv.1"): "#109",
    ("buck_top.spice", "XMP_LG5", "comp.width.mv.1"): "#109",
}

DEVICE_RE = re.compile(r"^(?P<flavour>(?P<pol>nfet|pfet)_(?P<volt>03v3|06v0))$")
SI = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "": 1.0}
NUM_RE = re.compile(r"^([0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)([fpnumFPNUM]?)(?:m|meter)?$")
EPS = 1e-9  # um; absorbs float noise so "exactly at the minimum" passes


@dataclass(frozen=True)
class Mos:
    file: str
    name: str
    model: str
    pol: str
    volt: str
    w_um: float
    l_um: float
    nf: float
    m: float
    line: int

    @property
    def finger_um(self) -> float:
        return self.w_um / self.nf


@dataclass(frozen=True)
class Finding:
    dev: Mos
    rule: str
    kind: str  # "finger_w" | "length"
    value_um: float
    minimum_um: float

    def describe(self) -> str:
        d = self.dev
        return (
            f"{d.file}:{d.line} {d.name} ({d.model}) {self.kind}={self.value_um:.4f} um "
            f"< {self.minimum_um:.2f} um [{self.rule}]; W={d.w_um:.4f} um nf={d.nf:g} "
            f"W/nf={d.finger_um:.4f} um L={d.l_um:.4f} um m={d.m:g}"
        )


def parse_value(text: str) -> float:
    """SPICE number with optional SI suffix -> metres (``79.245u`` -> 7.9245e-05).

    Raises ValueError for expressions, which this check cannot evaluate.
    """
    t = text.strip().strip("'\"")
    mt = NUM_RE.match(t)
    if not mt:
        raise ValueError(f"not a plain number: {text!r}")
    num, suf = mt.group(1), mt.group(2)
    # SPICE: "m" is milli, "meg" mega; this check only meets f p n u m.
    return float(num) * SI[suf.lower()]


def join_continuations(text: str) -> list[tuple[int, str]]:
    """Return (first physical line number, joined logical line) pairs."""
    out: list[tuple[int, str]] = []
    for no, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        if line.startswith("+") and out:
            n0, prev = out[-1]
            out[-1] = (n0, prev + " " + line[1:].strip())
        else:
            out.append((no, line))
    return out


PARAM_RE = re.compile(r"""([A-Za-z_]\w*)\s*=\s*('[^']*'|"[^"]*"|[^\s]+)""")


def parse_netlist(path: str) -> list[Mos]:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    fname = os.path.basename(path)
    devices: list[Mos] = []
    for no, line in join_continuations(text):
        if not line or line[0] != "X":
            continue
        tokens = line.split()
        model_idx = next(
            (i for i, t in enumerate(tokens[1:], 1) if DEVICE_RE.match(t) and "=" not in t),
            None,
        )
        if model_idx is None:
            continue
        mm = DEVICE_RE.match(tokens[model_idx])
        params = {k.lower(): v for k, v in PARAM_RE.findall(" ".join(tokens[model_idx + 1 :]))}
        try:
            w = parse_value(params["w"]) * 1e6
            l_ = parse_value(params["l"]) * 1e6
            nf = float(params.get("nf", "1"))
            m = float(params.get("m", "1"))
        except (KeyError, ValueError) as exc:
            raise SystemExit_(f"{fname}:{no}: cannot parse {tokens[0]} ({exc})") from exc
        if nf <= 0:
            raise SystemExit_(f"{fname}:{no}: {tokens[0]} has nf={nf:g}")
        devices.append(
            Mos(fname, tokens[0], tokens[model_idx], mm["pol"], mm["volt"], w, l_, nf, m, no)
        )
    return devices


class SystemExit_(Exception):
    """Unparseable instance; main() maps this to exit status 2."""


def check_device(dev: Mos) -> list[Finding]:
    findings: list[Finding] = []
    rule, minimum = MIN_FINGER_W[dev.volt]
    if dev.finger_um < minimum - EPS:
        findings.append(Finding(dev, rule, "finger_w", dev.finger_um, minimum))
    rule, minimum = MIN_L[(dev.volt, dev.pol)]
    if dev.l_um < minimum - EPS:
        findings.append(Finding(dev, rule, "length", dev.l_um, minimum))
    return findings


def run(paths: list[str], known: dict, out=sys.stdout, err=sys.stderr) -> int:
    all_findings: list[Finding] = []
    n_dev = 0
    try:
        for p in paths:
            devs = parse_netlist(p)
            n_dev += len(devs)
            for d in devs:
                all_findings.extend(check_device(d))
    except SystemExit_ as exc:
        print(f"ERROR: {exc}", file=err)
        return 2

    seen_known = set()
    new: list[Finding] = []
    for f in all_findings:
        key = (f.dev.file, f.dev.name, f.rule)
        if key in known:
            seen_known.add(key)
            print(f"WARNING known violation ({known[key]}): {f.describe()}", file=out)
        else:
            new.append(f)
    stale = [k for k in known if k not in seen_known and any(os.path.basename(p) == k[0] for p in paths)]

    for f in new:
        print(f"FAIL {f.describe()}\n     rule source: {RULE_SOURCE[f.rule]}", file=err)
    for k in stale:
        print(
            f"FAIL stale known-violation entry {k} ({known[k]}): the device no longer "
            f"violates the rule; remove it from KNOWN_VIOLATIONS",
            file=err,
        )
    print(
        f"checked {n_dev} MOSFET instances in {len(paths)} netlists: "
        f"{len(seen_known)} known, {len(new)} new violations, {len(stale)} stale entries",
        file=out,
    )
    return 1 if (new or stale) else 0


def main(argv: list[str]) -> int:
    paths = argv or sorted(
        glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "netlists", "*.spice"))
    )
    if not paths:
        print("ERROR: no netlists found", file=sys.stderr)
        return 2
    return run(paths, KNOWN_VIOLATIONS)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
