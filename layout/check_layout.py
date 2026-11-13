#!/usr/bin/env python3
"""Recompute the power-path numbers from layout/buck.gds and compare them with
the EM requirement of spec R18 / decision record 0001 section 5 (500 mA row).

    python3 layout/check_layout.py            # assert only
    python3 layout/check_layout.py --write    # also (re)write layout/record.md

The GDS is the only input to the measurements (nets are found from the text
labels on the Metal3 trunks and propagated through vias by geometry); the
requirement is recomputed here from the EM table, independently of the
generator.  Exit 0 only if every row passes.
"""
import argparse
import hashlib
import math
import os
import re
import sys

import klayout.db as db

HERE = os.path.dirname(os.path.abspath(__file__))
GDS = os.path.join(HERE, "buck.gds")
EM_TOP, EM_CUT = 5.37 * 0.8, 0.18 * 0.8
IOUT = 0.500
REQ = {"SW": IOUT, "VIN": 0.45 * IOUT, "GND": 0.70 * IOUT}   # 0001 section 5.1
LY = {"COMP": (22, 0), "CONTACT": (33, 0), "METAL1": (34, 0), "VIA1": (35, 0), "METAL2": (36, 0),
      "VIA2": (38, 0), "METAL3": (42, 0), "M3SLOT": (42, 3), "M3LABEL": (42, 10), "M2LABEL": (36, 10),
      "PAD": (37, 0), "POLY2": (30, 0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--gds", default=GDS)
    a = ap.parse_args()
    ly = db.Layout()
    ly.read(a.gds)
    top = ly.top_cell()
    R = {}
    for k, (l, d) in LY.items():
        idx = ly.find_layer(l, d)
        R[k] = db.Region(top.begin_shapes_rec(idx)) if idx is not None else db.Region()
    um = 1000

    def labels(layer):
        out = {}
        idx = ly.find_layer(*LY[layer])
        it = top.begin_shapes_rec(idx)
        while not it.at_end():
            s = it.shape()
            if s.is_text():
                t = s.text.transformed(it.trans())
                out[t.string] = (t.x, t.y)
            it.next()
        return out
    m3l, m2l = labels("M3LABEL"), labels("M2LABEL")
    m3, m2, m1 = R["METAL3"].merged(), R["METAL2"].merged(), R["METAL1"].merged()

    def at(region, pt):
        return region.interacting(db.Region(db.Box(pt[0] - 1, pt[1] - 1, pt[0] + 1, pt[1] + 1)))
    trunk = {n: at(m3, m3l[n]) for n in ("VIN", "SW", "GND")}
    assert len({t.bbox().to_s() for t in trunk.values()}) == 3, "trunks merged (short)"

    def trunk_band(net):
        # the trunk proper is the widest horizontal slab, reconstructed by
        # scanning the labelled polygon's left edge column (x = left+1)
        tb = trunk[net].bbox()
        col = trunk[net] & db.Region(db.Box(tb.left, tb.bottom, tb.left + 2 * um, tb.top))
        b = col.bbox()
        return (b.bottom, b.top)

    # array boxes: rows of each array, from the generator's geometry (x 0..W)
    comp_rows = R["COMP"].merged()
    big = [p.bbox() for p in comp_rows.each() if p.bbox().width() > 100 * um]
    big.sort(key=lambda b: b.bottom)
    swb = trunk_band("SW")
    ls_rows = [b for b in big if b.top < swb[0]]
    hs_rows = [b for b in big if b.bottom > swb[1]]
    def span(rows, pad=8 * um):
        return db.Box(0, min(r.bottom for r in rows) - pad, max(r.right for r in rows) + pad,
                      max(r.top for r in rows) + pad)
    arr = {"HS": span(hs_rows, 6 * um), "LS": span(ls_rows, 6 * um)}
    # net propagation inside an array box
    def cuts_in(tag, net_top):
        v2 = db.Region([p for p in R["VIA2"].each() if arr[tag].contains(p.bbox().center())
                        and not (net_top & db.Region(p.bbox())).is_empty()])
        m2n = m2.interacting(v2)
        v1 = db.Region([p for p in R["VIA1"].each() if arr[tag].contains(p.bbox().center())
                        and not (m2n & db.Region(p.bbox())).is_empty()])
        m1n = m1.interacting(v1)
        ct = db.Region([p for p in R["CONTACT"].each() if arr[tag].contains(p.bbox().center())
                        and not (m1n & db.Region(p.bbox())).is_empty()])
        return v2.count(), m2n, v1.count(), m1n, ct.count()

    nets = {}
    for net, tag in (("VIN", "HS"), ("SW", "HS"), ("SW", "LS"), ("GND", "LS")):
        c2, m2n, c1, m1n, cc = cuts_in(tag, trunk[net])
        nets[(net, tag)] = dict(via2=c2, via1=c1, contact=cc, m2=m2n, m1=m1n)
    gate = {t: at(m2, m2l[t]) for t in ("GH", "GL")}
    # shorts: the power nets' Metal1/Metal2 must not touch each other or the gate buses
    problems = []
    keys = list(nets)
    for i, ka in enumerate(keys):
        for kb in keys[i + 1:]:
            for lay in ("m1", "m2"):
                if not (nets[ka][lay] & nets[kb][lay]).is_empty():
                    problems.append("short %s/%s on %s" % (ka, kb, lay))
    for g, reg in gate.items():
        for k in keys:
            if not (nets[k]["m2"] & reg).is_empty():
                problems.append("gate %s shorts to %s" % (g, k))
    if not (trunk["VIN"] & trunk["SW"]).is_empty() or not (trunk["SW"] & trunk["GND"]).is_empty():
        problems.append("trunks touch")

    # trunk width net of slots: worst case over cut positions along the trunk
    def net_width(net):
        t = trunk[net] - R["M3SLOT"]
        tb = trunk[net].bbox()
        # restrict to the horizontal band of the trunk proper (strips excluded)
        info_y = trunk_band(net)
        worst = None
        x = tb.left + 2 * um
        while x < tb.right:
            cut = db.Region(db.Box(x, info_y[0], x + 500, info_y[1]))
            w = (cut & t).area() / 500.0 / um
            worst = w if worst is None else min(worst, w)
            x += 7 * um
        return worst

    rows = []
    ok = not problems
    def row(name, req, got, unit):
        nonlocal ok
        p = got + 1e-9 >= req
        ok &= p
        rows.append((name, req, got, unit, p))
    w_req = {n: REQ[n] * 1e3 / EM_TOP for n in REQ}
    c_req = {n: math.ceil(REQ[n] * 1e3 / EM_CUT) for n in REQ}
    for net in ("SW", "VIN", "GND"):
        w = net_width(net)
        row("%s MetalTop trunk width net of slots" % net, w_req[net], w, "um")
    for net, tag in nets:
        d = nets[(net, tag)]
        nm = "%s (%s array)" % (net, tag)
        row("%s Contact cuts" % nm, c_req[net], d["contact"], "cuts")
        row("%s Via1 cuts" % nm, c_req[net], d["via1"], "cuts")
        row("%s Via2 cuts" % nm, c_req[net], d["via2"], "cuts")
    # finger counts vs schematic
    sch = open(os.path.join(HERE, "../design/schematics/power_stage.sch")).read()
    want = {}
    for nm, tag in (("MHS", "HS"), ("MLS", "LS")):
        m = re.search(r"name=%s .*? nf=(\d+) m=(\d+)" % nm, sch)
        want[tag] = int(m.group(1)) * int(m.group(2))
    got_f = {}
    for tag in ("HS", "LS"):
        n = 0
        for p in (R["POLY2"] & R["COMP"]).merged().each():
            if arr[tag].contains(p.bbox().center()):
                n += 1
        got_f[tag] = n
    # 2 pads per power net on the trunk
    pads = {}
    for p in R["PAD"].each():
        for net in trunk:
            if not (trunk[net] & db.Region(p.bbox())).is_empty():
                pads[net] = pads.get(net, 0) + 1
    for net in ("VIN", "SW", "GND"):
        row("%s bond pads on the trunk (2 wires per net, R19)" % net, 2, pads.get(net, 0), "pads")
    for tag in ("HS", "LS"):
        ok &= got_f[tag] == want[tag]
        if got_f[tag] != want[tag]:
            problems.append("%s fingers %d != schematic nf*m %d" % (tag, got_f[tag], want[tag]))
    sha = hashlib.sha256(open(a.gds, "rb").read()).hexdigest()
    print("GDS sha256", sha)
    for r in rows:
        print("%-62s req %10.1f  got %10.1f %-5s %s" % (r[0], r[1], r[2], r[3], "PASS" if r[4] else "FAIL"))
    print("fingers (poly crossing diffusion): drawn %s, schematic nf*m %s" % (got_f, want))
    for p in problems:
        print("PROBLEM", p)
    if a.write:
        with open(os.path.join(HERE, "record.md"), "w") as f:
            f.write("# Layout record: power-path metal vs the 500 mA EM row\n\n")
            f.write("Generated by `python3 layout/check_layout.py --write` from `layout/buck.gds`; do not edit.\n\n")
            f.write("- GDS sha256: `%s`\n- Variant: gf180mcuA (3LM, 30 kA MetalTop = Metal3 42/0)\n" % sha)
            f.write("- Requirement: spec R18 / decision record 0001 section 5.1, 500 mA target row, 125 C, unidirectional, x0.8\n")
            f.write("- Measured by recomputing from the GDS (nets from Metal3 trunk labels, propagated through vias; cuts counted inside each array's box, body-tie cuts excluded). SW is counted per array, each against the full SW row (conservative).\n")
            f.write("- Trunk width is the worst case over cut positions along the trunk of Metal3 minus the `Metal3_Slot` mark (net of slots).\n\n")
            f.write("| Row | Required | Drawn | Unit | Result |\n|---|---|---|---|---|\n")
            for r in rows:
                f.write("| %s | %.1f | %.1f | %s | %s |\n" % (r[0], r[1], r[2], r[3], "pass" if r[4] else "FAIL"))
            f.write("\nPoly fingers crossing diffusion: drawn %s; schematic `nf*m` %s.\n" % (got_f, want))
            f.write("\nNot measured here: Metal1/Metal2 current density along rails and straps (sized by construction in the generator, see layout/README.md), IR drop, DRC, LVS.\n")
    if problems or not ok:
        print("FAIL")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
