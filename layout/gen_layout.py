#!/usr/bin/env python3
"""Deterministic generator for the gf180-buck power-stage layout (T1 item 2).

PDK variant gf180mcuA (3LM, 30 kA top metal): Metal1 34/0, Metal2 36/0,
Metal3 = MetalTop 42/0, Via1 35/0, Via2 38/0, slot mark Metal3_Slot 42/3.

Usage (from the repository root):

    python3 -I layout/gen_layout.py [--current 500] [--out layout/buck.gds]

Device sizes (W, L, nf, m of MHS / MLS) are read from
design/schematics/power_stage.sch, so a design change is a regenerate.
Strap widths and cut counts are derived from the EM table of spec R18 /
decision record 0001 section 5.1 at the chosen load current (default 500 mA).

What is drawn: the HS pfet and LS nfet arrays, their Metal1/Metal2 collection
network, slotted Metal3 trunks for VIN, SW and GND, body ties, two bond pads
per power net, and gate buses.  What is NOT drawn: the control blocks (they
are floorplan reservations on a marker layer, see layout/README.md).
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys

import klayout.db as db

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---------------------------------------------------------------- layers
LAYERS = {
    "COMP": (22, 0), "NWELL": (21, 0), "DUALGATE": (55, 0), "POLY2": (30, 0),
    "NPLUS": (32, 0), "PPLUS": (31, 0), "CONTACT": (33, 0),
    "METAL1": (34, 0), "VIA1": (35, 0), "METAL2": (36, 0), "VIA2": (38, 0),
    "METAL3": (42, 0), "M3SLOT": (42, 3), "M3LABEL": (42, 10),
    "M2LABEL": (36, 10), "M1LABEL": (34, 10),
    "PAD": (37, 0),
    # not a PDK layer: floorplan reservation for undrawn control blocks
    "RESERVE": (998, 0), "DIE": (999, 0),
}

# ------------------------------------------------- EM table (spec R18, x0.8)
EM_TOP = 5.37 * 0.8       # mA/um, MetalTop 30 kA at 125 C unidirectional
EM_LOW = 0.67 * 0.8       # mA/um, Metal1 / Metal2
EM_CUT = 0.18 * 0.8       # mA per cut, contact / Via1 / Via2

# duty bounds from decision record 0001 section 5.1 (target tier)
D_MAX, D_MIN = 0.45, 0.30     # VIN path D_max*Iout; LS path (1-D_min)*Iout

# ------------------------------------------------------------- geometry
GRID = 0.005
SD = 0.56                 # source/drain column width (contact 0.22 + 2 x 0.17)
CT, CT_P = 0.22, 0.50     # contact size and pitch
VS, VS_P = 0.26, 0.52     # via size and pitch
M1_COL = 0.34             # Metal1 stripe over a contact column
RAIL = 3.4                # Metal1 S and D rail width
GATE_RAIL = 1.0
FIN_W = 10.0              # finger width, from W/nf
GROUP, GAP = 20.0, 4.0    # Metal3 strip width and gap
PERIOD = 2 * (GROUP + GAP)
STRAP_W, STRAP_P, N_STRAP = 3.4, 4.0, 5     # Metal2 S/D straps per group
GSTRAP_W = 1.5            # Metal2 gate strap
ROW_GAP = 0.5
SLOT_W, SLOT_PITCH_MIN = 2.0, 30.0   # slot width; metal between slots
SLOT_LEN, SLOT_GAP = 250.0, 10.0
SLOT_EDGE = 10.0


def snap(v):
    return round(round(v / GRID) * GRID, 3)


def parse_power_stage():
    """Read MHS/MLS W, L, nf, m from the schematic (the source of truth)."""
    txt = open(os.path.join(ROOT, "design/schematics/power_stage.sch")).read()
    out = {}
    for name in ("MHS", "MLS"):
        m = re.search(r"\{name=%s model=(\w+) W=([\d.]+)u L=([\d.]+)u nf=(\d+) m=(\d+)\}" % name, txt)
        if not m:
            sys.exit("cannot parse %s from power_stage.sch" % name)
        out[name] = dict(model=m.group(1), W=float(m.group(2)), L=float(m.group(3)),
                         nf=int(m.group(4)), m=int(m.group(5)))
    return out


def required(iout_a):
    """EM requirement per net (decision record 0001 section 5.1)."""
    def req(i):
        return dict(current_a=i, top_um=i * 1e3 / EM_TOP, cuts=math.ceil(i * 1e3 / EM_CUT))
    return {"SW": req(iout_a), "VIN": req(D_MAX * iout_a), "GND": req((1 - D_MIN) * iout_a)}


class Gen:
    def __init__(self, iout_a):
        self.iout = iout_a
        self.dev = parse_power_stage()
        self.req = required(iout_a)
        self.ly = db.Layout()
        self.ly.dbu = 0.001
        self.L = {k: self.ly.layer(*v) for k, v in LAYERS.items()}
        self.nets = {}      # label -> record data
        self.info = {}

    # -------------------------------------------------------- primitives
    def box(self, cell, layer, x0, y0, x1, y1):
        cell.shapes(self.L[layer]).insert(db.DBox(snap(x0), snap(y0), snap(x1), snap(y1)))

    def via_array(self, cell, layer, x0, y0, x1, y1, size, pitch, enc):
        """Fill [x0,x1]x[y0,y1] (the shared metal area) with a via grid; returns count."""
        w, h = x1 - x0 - 2 * enc, y1 - y0 - 2 * enc
        if w < size or h < size:
            return 0
        nx, ny = int((w - size) / pitch + 1e-9) + 1, int((h - size) / pitch + 1e-9) + 1
        ox = x0 + enc + (w - ((nx - 1) * pitch + size)) / 2
        oy = y0 + enc + (h - ((ny - 1) * pitch + size)) / 2
        tmpl = self.via_cell(layer, size)
        tr = db.DCplxTrans(1.0, 0.0, False, snap(ox), snap(oy))
        if nx * ny == 1:
            cell.insert(db.DCellInstArray(tmpl.cell_index(), tr))
        else:
            cell.insert(db.DCellInstArray(tmpl.cell_index(), tr, db.DVector(pitch, 0), db.DVector(0, pitch), nx, ny))
        return nx * ny

    def via_cell(self, layer, size):
        name = "%s_%d" % (layer, round(size * 1000))
        c = self.ly.cell(name)
        if c is None:
            c = self.ly.create_cell(name)
            self.box(c, layer, 0, 0, size, size)
        return c

    # ------------------------------------------------------ transistor row
    def build_row(self, kind, L, nfing):
        """One row of nfing fingers; local origin = bottom-left of COMP.
        Returns (cell, dict of geometry)."""
        p = snap(L + SD)
        wrow = snap(nfing * p + SD)
        c = self.ly.create_cell("ROW_%s_%d" % (kind, nfing))
        H = FIN_W
        yS_top = -0.4
        yS_bot = yS_top - RAIL
        gr_top = yS_bot - 0.3
        gr_bot = gr_top - GATE_RAIL
        gy = (gr_top + gr_bot) / 2
        bar0, bar1 = gy - 0.3, gy + 0.3
        yD_bot = H + 0.4
        yD_top = yD_bot + RAIL
        implant = "NPLUS" if kind == "n" else "PPLUS"
        self.box(c, "COMP", 0, 0, wrow, H)
        self.box(c, implant, -0.3, -0.3, wrow + 0.3, H + 0.3)
        self.box(c, "DUALGATE", -0.5, -0.5, wrow + 0.5, H + 0.5)
        # poly fingers and the gate bar
        fin = self.ly.create_cell("FIN_%s" % kind)
        self.box(fin, "POLY2", 0, bar0, L, H + 0.4)
        c.insert(db.DCellInstArray(fin.cell_index(), db.DTrans(snap(SD), 0), db.DVector(p, 0), db.DVector(0, 0), nfing, 1))
        self.box(c, "POLY2", SD, bar0, nfing * p, bar1)
        # contact + Metal1 columns (S down to the S rail, D up to the D rail)
        ncont = int((H - 0.78 - CT) / CT_P) + 1
        cy0 = (H - ((ncont - 1) * CT_P + CT)) / 2
        for typ, y0, y1 in (("S", yS_top - 0.1, H - 0.2), ("D", 0.2, yD_bot + 0.1)):
            col = self.ly.create_cell("COL_%s_%s" % (kind, typ))
            ct = self.via_cell("CONTACT", CT)
            col.insert(db.DCellInstArray(ct.cell_index(), db.DTrans(snap((SD - CT) / 2), snap(cy0)),
                                         db.DVector(0, 0), db.DVector(0, CT_P), 1, ncont))
            self.box(col, "METAL1", (SD - M1_COL) / 2, y0, (SD + M1_COL) / 2, y1)
            n = nfing // 2 + 1 if typ == "S" else nfing // 2
            off = 0 if typ == "S" else p
            c.insert(db.DCellInstArray(col.cell_index(), db.DTrans(snap(off), 0), db.DVector(2 * p, 0), db.DVector(0, 0), n, 1))
        # rails and gate rail
        self.box(c, "METAL1", 0, yS_bot, wrow, yS_top)
        self.box(c, "METAL1", 0, yD_bot, wrow, yD_top)
        self.box(c, "METAL1", 0, gr_bot, wrow, gr_top)
        # gate contacts along the bar
        gc = self.via_cell("CONTACT", CT)
        ngc = int((wrow - 2 * SD) / 2.0)
        c.insert(db.DCellInstArray(gc.cell_index(), db.DTrans(snap(SD + 0.5), snap(gy - CT / 2)),
                                   db.DVector(2.0, 0), db.DVector(0, 0), ngc, 1))
        g = dict(p=p, wrow=wrow, H=H, yS=(yS_bot, yS_top), yD=(yD_bot, yD_top), yG=(gr_bot, gr_top),
                 ybot=gr_bot, ytop=yD_top, ncont=ncont, nS=nfing // 2 + 1, nD=nfing // 2)
        return c, g

    # ------------------------------------------------------------- stack
    def build(self):
        hs, ls = self.dev["MHS"], self.dev["MLS"]
        nfing_hs, nfing_ls = hs["nf"] * hs["m"], ls["nf"] * ls["m"]
        finger_w = hs["W"] / hs["nf"]
        assert abs(finger_w - FIN_W) < 1e-9 and abs(ls["W"] / ls["nf"] - FIN_W) < 1e-9, "finger width != 10 um"
        # rows: pick rows so every row has the same even finger count
        def split(n, target_w, L):
            p = snap(L + SD)
            rows = max(1, math.ceil(n * p / target_w))
            while n % rows or (n // rows) % 2:
                rows += 1
            return rows, n // rows
        n_per = 12
        width_goal = n_per * PERIOD
        rows_hs, nf_hs_row = split(nfing_hs, width_goal, hs["L"])
        rows_ls, nf_ls_row = split(nfing_ls, width_goal, ls["L"])
        top = self.ly.create_cell("BUCK_POWER")
        row_hs, g_hs = self.build_row("p", hs["L"], nf_hs_row)
        row_ls, g_ls = self.build_row("n", ls["L"], nf_ls_row)
        assert g_hs["wrow"] <= width_goal and g_ls["wrow"] <= width_goal, "row wider than the strap field"
        self.info.update(rows_hs=rows_hs, rows_ls=rows_ls, fingers_hs=nfing_hs, fingers_ls=nfing_ls,
                         fingers_per_row_hs=nf_hs_row, fingers_per_row_ls=nf_ls_row, periods=n_per,
                         width_um=width_goal)

        # ---- trunk heights from the slotting rules (net of slots)
        def trunk(net):
            need = self.req[net]["top_um"]
            rows = max(1, math.ceil(need / SLOT_PITCH_MIN))
            nslots = rows - 1
            return dict(rows=rows, nslots=nslots, drawn=rows * SLOT_PITCH_MIN + nslots * SLOT_W,
                        net_w=rows * SLOT_PITCH_MIN)
        T = {n: trunk(n) for n in ("VIN", "SW", "GND")}
        self.info["trunks"] = T
        pitch_hs = snap(g_hs["ytop"] - g_hs["ybot"] + ROW_GAP)
        pitch_ls = snap(g_ls["ytop"] - g_ls["ybot"] + ROW_GAP)
        # y plan, bottom to top (um); trunks left-aligned at x0 = -TAIL_L
        y = 0.0
        y_gnd0, y_gnd1 = y, y + T["GND"]["drawn"]
        y_ls0 = y_gnd1 + GAP                       # LS region bottom
        ls_h = rows_ls * pitch_ls + 4.0            # + room for the LS gate bus
        y_ls1 = y_ls0 + ls_h
        y_sw0 = y_ls1 + GAP
        y_sw1 = y_sw0 + T["SW"]["drawn"]
        y_hs0 = y_sw1 + GAP
        hs_h = rows_hs * pitch_hs + 4.0
        y_hs1 = y_hs0 + hs_h
        y_vin0 = y_hs1 + GAP
        y_vin1 = y_vin0 + T["VIN"]["drawn"]
        W = width_goal
        TAIL_L, TAIL_R = 12.0, 330.0
        x_lo, x_hi = -TAIL_L, W + TAIL_R
        self.info["trunk_y"] = dict(GND=(y_gnd0, y_gnd1), SW=(y_sw0, y_sw1), VIN=(y_vin0, y_vin1))

        # ---- Metal3 trunks, slots, labels
        def m3_trunk(net, ya, yb, label_x):
            self.box(top, "METAL3", x_lo, ya, x_hi, yb)
            t = T[net]
            # slots parallel to the current (x direction): metal rows of SLOT_PITCH_MIN between slots,
            # slot rows staggered by half a slot period (MSLOT.6)
            for k in range(1, t["rows"]):
                ys = ya + k * SLOT_PITCH_MIN + (k - 1) * SLOT_W
                x = x_lo + SLOT_EDGE + (0 if k % 2 else (SLOT_LEN + SLOT_GAP) / 2)
                while x + 20.0 < x_hi - SLOT_EDGE - TAIL_PAD_FREE[net]:
                    xe = min(x + SLOT_LEN, x_hi - SLOT_EDGE - TAIL_PAD_FREE[net])
                    if xe - x >= 10.0:
                        self.box(top, "M3SLOT", x, ys, xe, ys + SLOT_W)
                    x += SLOT_LEN + SLOT_GAP
            top.shapes(self.L["M3LABEL"]).insert(db.DText(net, db.DTrans(snap(label_x), snap((ya + yb) / 2))))
        # slot-free zone at the tail end (the pads sit there)
        TAIL_PAD_FREE = {"VIN": 0.0, "SW": 0.0, "GND": 0.0}
        m3_trunk("GND", y_gnd0, y_gnd1, x_lo + 3)
        m3_trunk("SW", y_sw0, y_sw1, x_lo + 3)
        m3_trunk("VIN", y_vin0, y_vin1, x_lo + 3)

        # ---- arrays
        cnt = {k: {"CONTACT": 0, "VIA1": 0, "VIA2": 0} for k in ("VIN", "SW_HS", "SW_LS", "GND")}
        self.build_array(top, row_hs, g_hs, rows_hs, pitch_hs, y_hs0 + 4.0, y_hs0, y_hs1, n_per,
                         dict(A="VIN", B="SW_HS"), cnt, "HS", y_sw1, y_vin0, T)
        self.build_array(top, row_ls, g_ls, rows_ls, pitch_ls, y_ls0, y_ls0, y_ls1, n_per,
                         dict(A="GND", B="SW_LS"), cnt, "LS", y_gnd1, y_sw0, T)
        self.info["drawn_cuts"] = cnt

        # ---- Nwell for the pfet array; body ties
        self.box(top, "NWELL", -9.0, y_hs0 - 1.0, W + 9.0, y_hs1 + 0.5)
        self.body_ties(top, "HS", y_hs0, y_hs1, W, y_vin0 + 5.0, "VIN")
        self.body_ties(top, "LS", y_ls0, y_ls1, W, y_gnd1 - 5.0, "GND")

        # ---- bond pads: two per power net on the trunk tails
        PAD = 80.0
        pads = []
        for net, (ya, yb) in (("VIN", (y_vin0, y_vin1)), ("SW", (y_sw0, y_sw1)), ("GND", (y_gnd0, y_gnd1))):
            for i in range(2):
                x0 = W + 30.0 + i * (PAD + 40.0)
                y0 = (ya + yb) / 2 - PAD / 2
                self.box(top, "PAD", x0, y0, x0 + PAD, y0 + PAD)
                top.shapes(self.L["M3LABEL"]).insert(db.DText("%s_PAD%d" % (net, i + 1),
                                                          db.DTrans(snap(x0 + PAD / 2), snap(y0 + PAD / 2))))
                pads.append(dict(net=net, index=i + 1, x=[x0, x0 + PAD], y=[y0, y0 + PAD]))
        self.info["pads"] = pads

        # ---- die outline and reserved control area (not drawn)
        bx0, bx1 = x_lo, x_hi
        by0, by1 = y_gnd0, y_vin1
        CTRL_W = 900.0
        self.box(top, "RESERVE", bx0 - CTRL_W - 20.0, by0, bx0 - 20.0, by1)
        top.shapes(self.L["M3LABEL"]).insert(db.DText("CONTROL_RESERVED_NOT_DRAWN", db.DTrans(snap(bx0 - CTRL_W / 2), snap((by0 + by1) / 2))))
        margin = 400.0
        die = (bx0 - CTRL_W - 20.0 - margin, by0 - margin, bx1 + margin, by1 + margin)
        self.box(top, "DIE", *die)
        self.info["die"] = dict(x=[die[0], die[2]], y=[die[1], die[3]])
        self.info["power_bbox"] = dict(x=[x_lo, x_hi], y=[y_gnd0, y_vin1])
        self.info["array_bbox"] = dict(HS=[0, y_hs0, W, y_hs1], LS=[0, y_ls0, W, y_ls1])
        return top

    def build_array(self, top, row, g, nrows, pitch, y0, yreg0, yreg1, n_per, grp, cnt, tag, y_trunk_a, y_trunk_b, T):
        """Rows, Metal2 straps, Via1/Via2, Metal3 strips and the gate bus for one array."""
        W = n_per * PERIOD
        # rows: local origin (0,0) is COMP bottom-left; row bottom (gate rail) is g['ybot']
        base = y0 - g["ybot"]
        if tag == "LS":
            base = y0 - g["ybot"]
        for r in range(nrows):
            top.insert(db.DCellInstArray(row.cell_index(), db.DTrans(0.0, snap(base + r * pitch))))
        rows_bot = base + g["ybot"]
        rows_top = base + (nrows - 1) * pitch + g["ytop"]
        gate_bus_y = (rows_bot - 3.0, rows_bot - 1.5) if tag == "HS" else (rows_top + 1.5, rows_top + 3.0)
        # Metal2 straps span the rows only
        s_net = grp["A"]; d_net = grp["B"]
        def strap_cut_counts(net, key, n):
            cnt[net][key] += n
        for k in range(n_per):
            x0 = k * PERIOD
            for gi, net, typ in ((0, s_net, "S"), (1, d_net, "D")):
                gx0 = x0 + gi * (GROUP + GAP)
                for i in range(N_STRAP):
                    sx0 = gx0 + 0.3 + i * STRAP_P
                    sx1 = sx0 + STRAP_W
                    self.box(top, "METAL2", sx0, rows_bot, sx1, rows_top)
                    # Via2 up to the Metal3 strip along the whole strap
                    n2 = self.via_array(top, "VIA2", sx0, rows_bot, sx1, rows_top, VS, VS_P, 0.06)
                    cnt[net]["VIA2"] += n2
                    for r in range(nrows):
                        yb = base + r * pitch
                        ya, yz = (g["yS"] if typ == "S" else g["yD"])
                        n1 = self.via_array(top, "VIA1", sx0, yb + ya, sx1, yb + yz, VS, VS_P, 0.06)
                        cnt[net]["VIA1"] += n1
            # gate straps in the two gaps of the period
            for gx in (x0 + GROUP + GAP / 2, x0 + PERIOD - GAP / 2):
                self.box(top, "METAL2", gx - GSTRAP_W / 2, gate_bus_y[0], gx + GSTRAP_W / 2, rows_top if tag == "HS" else gate_bus_y[1])
                for r in range(nrows):
                    yb = base + r * pitch
                    ya, yz = g["yG"]
                    self.via_array(top, "VIA1", gx - GSTRAP_W / 2, yb + ya, gx + GSTRAP_W / 2, yb + yz, VS, VS_P, 0.06)
        # gate bus (Metal2) running left to the control area
        self.box(top, "METAL2", -30.0, gate_bus_y[0], W - 0.0, gate_bus_y[1])
        top.shapes(self.L["M2LABEL"]).insert(db.DText("GH" if tag == "HS" else "GL", db.DTrans(-29.0, snap((gate_bus_y[0] + gate_bus_y[1]) / 2))))
        # Metal3 strips: A strips hang from the far trunk, B strips from the near trunk
        for k in range(n_per):
            x0 = k * PERIOD
            if tag == "HS":
                # A (VIN) from the VIN trunk down to region bottom; B (SW) from the SW trunk up to region top
                self.box(top, "METAL3", x0, yreg0, x0 + GROUP, y_trunk_b)
                self.box(top, "METAL3", x0 + GROUP + GAP, y_trunk_a, x0 + PERIOD - GAP, yreg1)
            else:
                self.box(top, "METAL3", x0, y_trunk_a, x0 + GROUP, yreg1)
                self.box(top, "METAL3", x0 + GROUP + GAP, yreg0, x0 + PERIOD - GAP, y_trunk_b)
        self.info.setdefault("rows_y", {})[tag] = [rows_bot, rows_top]

    def body_ties(self, top, tag, y0, y1, W, y_trunk, net):
        """Body tie strips at both array ends, Metal2 up/down to the trunk (not counted as power-path cuts)."""
        kind = "N" if tag == "HS" else "P"
        for side, x in (("L", -7.0), ("R", W + 5.0)):
            self.box(top, "COMP", x, y0, x + 1.2, y1)
            self.box(top, "NPLUS" if kind == "N" else "PPLUS", x - 0.3, y0 - 0.3, x + 1.5, y1 + 0.3)
            ct = self.via_cell("CONTACT", CT)
            nct = int((y1 - y0 - 0.7) / CT_P) + 1
            top.insert(db.DCellInstArray(ct.cell_index(), db.DTrans(snap(x + 0.49), snap(y0 + 0.2)), db.DVector(0, 0), db.DVector(0, CT_P), 1, nct))
            self.box(top, "METAL1", x + 0.3, y0, x + 0.9, y1)
            self.box(top, "METAL2", x - 0.7, min(y0, y_trunk), x + 1.9, max(y1, y_trunk))
            self.via_array(top, "VIA1", x + 0.3, y0, x + 0.9, y1, VS, VS_P, 0.06 - 0.1 + 0.1)
            # Via2 into the trunk
            ya, yb = (y_trunk - 3.0, y_trunk + 3.0)
            self.via_array(top, "VIA2", x - 0.7, ya, x + 1.9, yb, VS, VS_P, 0.06)


# -------------------------------------------------------------- output
def write_gds(gen, top, path):
    gen.ly.top_cell().name if False else None
    opts = db.SaveLayoutOptions()
    opts.format = "GDS2"
    opts.gds2_write_timestamps = False
    opts.gds2_write_cell_properties = False
    opts.gds2_write_file_properties = False
    opts.gds2_libname = "gf180_buck"
    gen.ly.write(path, opts)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--current", type=float, default=500.0, help="load current in mA the EM budget is taken at")
    ap.add_argument("--out", default=os.path.join(HERE, "buck.gds"))
    ap.add_argument("--info", default=os.path.join(HERE, "buck.info.json"))
    a = ap.parse_args()
    g = Gen(a.current / 1000.0)
    top = g.build()
    write_gds(g, top, a.out)
    g.info["generator"] = "layout/gen_layout.py"
    g.info["current_ma"] = a.current
    g.info["requirement"] = g.req
    g.info["devices"] = g.dev
    with open(a.info, "w") as f:
        json.dump(g.info, f, indent=1, sort_keys=True)
        f.write("\n")
    print("wrote", a.out, hashlib.sha256(open(a.out, "rb").read()).hexdigest())


if __name__ == "__main__":
    main()
