#!/usr/bin/env python3
"""Generate the controller schematics (issue #34) as xschem .sch files.

The .sch files are the source of truth once committed; this script is the
reproducible way they were drawn (connectivity is by lab_pin net labels, so
no wire routing is generated).  Re-running it rewrites the four files
byte-identically.  Device sizes live here, next to the topology, and are
cited from design/README.md.

    python3 design/schematics/gen_schematics.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))


class Sch:
    def __init__(self, title, notes):
        self.lines = [
            "v {xschem version=3.4.7 file_version=1.2}", "G {}", "K {}", "V {}", "S {}", "E {}",
            "T {%s} -600 -900 0 0 0.5 0.5 {}" % title,
        ]
        for i, n in enumerate(notes):
            self.lines.append("T {%s} -600 %d 0 0 0.3 0.3 {}" % (n, -850 + 30 * i))
        self.names = set()
        self.n = 0
        self.pinrow = 0

    def _xy(self):
        x = -400 + 300 * (self.n % 8)
        y = -300 + 250 * (self.n // 8)
        self.n += 1
        return x, y

    def _name(self, n):
        assert n not in self.names, "duplicate instance name " + n
        self.names.add(n)

    def lab(self, name, x, y, net):
        self.lines.append("C {lab_pin.sym} %d %d 0 0 {name=l_%s lab=%s}" % (x, y, name, net))

    def pin(self, kind, net):
        y = -800 + 40 * self.pinrow
        self.pinrow += 1
        self.lines.append("C {%s.sym} -900 %d 0 0 {name=p_%s lab=%s}" % (kind, y, net, net))

    def mos(self, name, dev, d, g, s, b, w, l, m=1):
        self._name(name)
        x, y = self._xy()
        p = dev.startswith("p")
        self.lines.append(
            "C {%s.sym} %d %d 0 0 {name=%s model=%s W=%s L=%s nf=1 m=%d}" % (dev, x, y, name, dev, w, l, m))
        self.lab(name + "_D", x + 20, y + (30 if p else -30), d)
        self.lab(name + "_G", x - 20, y, g)
        self.lab(name + "_S", x + 20, y + (-30 if p else 30), s)
        self.lab(name + "_B", x + 20, y, b)

    def res(self, name, p, m, b, w, l):
        self._name(name)
        x, y = self._xy()
        self.lines.append(
            "C {ppolyf_u.sym} %d %d 0 0 {name=%s model=ppolyf_u W=%s L=%s m=1}" % (x, y, name, w, l))
        self.lab(name + "_P", x, y - 30, p)
        self.lab(name + "_M", x, y + 30, m)
        self.lab(name + "_B", x - 20, y, b)

    def cap(self, name, top, bot, w, l):
        self._name(name)
        x, y = self._xy()
        self.lines.append(
            "C {cap_mim_2f0fF.sym} %d %d 0 0 {name=%s model=cap_mim_2f0fF W=%s L=%s m=1}" % (x, y, name, w, l))
        self.lab(name + "_G", x, y - 30, top)
        self.lab(name + "_B", x, y + 30, bot)

    def write(self, fname):
        with open(os.path.join(HERE, fname), "w") as f:
            f.write("\n".join(self.lines) + "\n")


N3, P3 = "nfet_03v3", "pfet_03v3"
N6, P6 = "nfet_06v0", "pfet_06v0"
VDD, VSS = "VDD33", "VSS"


def inv(s, p, i, o, wn="2u", wp="4u", l="0.35u"):
    s.mos(p + "N", N3, o, i, VSS, VSS, wn, l)
    s.mos(p + "P", P3, o, i, VDD, VDD, wp, l)


def nand2(s, p, a, b, o, wn="4u", wp="4u", l="0.35u"):
    s.mos(p + "NA", N3, o, a, p + "_n", VSS, wn, l)
    s.mos(p + "NB", N3, p + "_n", b, VSS, VSS, wn, l)
    s.mos(p + "PA", P3, o, a, VDD, VDD, wp, l)
    s.mos(p + "PB", P3, o, b, VDD, VDD, wp, l)


def nor2(s, p, a, b, o, wn="2u", wp="8u", l="0.35u"):
    s.mos(p + "NA", N3, o, a, VSS, VSS, wn, l)
    s.mos(p + "NB", N3, o, b, VSS, VSS, wn, l)
    s.mos(p + "PA", P3, p + "_p", a, VDD, VDD, wp, l)
    s.mos(p + "PB", P3, o, b, p + "_p", VDD, wp, l)


def nand3(s, p, a, b, c, o, wn="6u", wp="4u", l="0.35u"):
    s.mos(p + "NA", N3, o, a, p + "_n1", VSS, wn, l)
    s.mos(p + "NB", N3, p + "_n1", b, p + "_n2", VSS, wn, l)
    s.mos(p + "NC", N3, p + "_n2", c, VSS, VSS, wn, l)
    for k, x in zip("ABC", (a, b, c)):
        s.mos(p + "P" + k, P3, o, x, VDD, VDD, wp, l)


def schmitt(s, p, i, o):
    """Classic 6T Schmitt trigger (inverting): thresholds set by the feedback devices."""
    s.mos(p + "P1", P3, p + "_pa", i, VDD, VDD, "8u", "0.5u")
    s.mos(p + "P2", P3, o, i, p + "_pa", VDD, "8u", "0.5u")
    s.mos(p + "N2", N3, o, i, p + "_na", VSS, "4u", "0.5u")
    s.mos(p + "N1", N3, p + "_na", i, VSS, VSS, "4u", "0.5u")
    s.mos(p + "NF", N3, VDD, o, p + "_na", VSS, "2u", "0.5u")
    s.mos(p + "PF", P3, VSS, o, p + "_pa", VDD, "4u", "0.5u")


def ct_comp(s, p, kind, inp, inn, o, bias_net):
    """Continuous-time single-stage comparator + two inverters. OUT = (INP > INN).

    kind 'n': NMOS input pair, tail sinks from an NMOS mirror of bias_net.
    kind 'p': PMOS input pair, tail sources from a PMOS mirror of bias_net.
    bias_net is the net a diode-connected reference already holds.
    """
    if kind == "n":
        s.mos(p + "T", N3, p + "_t", bias_net, VSS, VSS, "10u", "2u")
        s.mos(p + "M1", N3, p + "_y1", inp, p + "_t", VSS, "8u", "1u")
        s.mos(p + "M2", N3, p + "_y2", inn, p + "_t", VSS, "8u", "1u")
        s.mos(p + "L1", P3, p + "_y1", p + "_y1", VDD, VDD, "8u", "1u")
        s.mos(p + "L2", P3, p + "_y2", p + "_y1", VDD, VDD, "8u", "1u")
    else:
        s.mos(p + "T", P3, p + "_t", bias_net, VDD, VDD, "20u", "2u")
        s.mos(p + "M1", P3, p + "_y1", inp, p + "_t", VDD, "16u", "1u")
        s.mos(p + "M2", P3, p + "_y2", inn, p + "_t", VDD, "16u", "1u")
        s.mos(p + "L1", N3, p + "_y1", p + "_y1", VSS, VSS, "4u", "1u")
        s.mos(p + "L2", N3, p + "_y2", p + "_y1", VSS, VSS, "4u", "1u")
    inv(s, p + "I1", p + "_y2", p + "_z")
    inv(s, p + "I2", p + "_z", o)


def osc_ramp():
    s = Sch("osc_ramp: 2 MHz relaxation oscillator + PWM sawtooth ramp (R7, R6 forced PWM)", [
        "Charge: IBIAS (nom. 12 uA into the pin) -> NMOS mirror x0.6 (7.2 uA) -> PMOS mirror x1 -> RAMP node (current source into C).",
        "Schmitt on RAMP; its output resets RAMP through MDIS and is the CLK pulse (rising = ramp reset = cycle start).",
        "Trim: TRIM<2:0> switch binary-weighted MIM caps onto RAMP (single-point trim at test, spec R7).",
        "Supply: 3.3 V control rail (decision record 0003). T = C*dV/I: depends on C, IBIAS and the Schmitt window.",
        "Sibling gf180-rcosc is kept, not adopted (reuse.lock.json): topology idea only, nothing copied.",
    ])
    for k, n in (("ipin", "IBIAS"), ("ipin", "TRIM0"), ("ipin", "TRIM1"), ("ipin", "TRIM2"),
                 ("opin", "CLK"), ("opin", "RAMP"), ("iopin", VDD), ("iopin", VSS)):
        s.pin(k, n)
    s.mos("MN0", N3, "IBIAS", "IBIAS", VSS, VSS, "10u", "2u")
    s.mos("MN1", N3, "PD", "IBIAS", VSS, VSS, "6u", "2u")
    s.mos("MP0", P3, "PD", "PD", VDD, VDD, "20u", "2u")
    s.mos("MP1", P3, "RAMP", "PD", VDD, VDD, "20u", "2u")
    s.cap("CR", "RAMP", VSS, "45u", "45u")
    # trim bank: unit cap 15x15 um (~0.45 pF) x 1,2,4 (0 to +3.15 pF on a 4.05 pF base); NMOS switch to VSS
    for i, m in enumerate((1, 2, 4)):
        s.cap("CT%d" % i, "RAMP", "CTB%d" % i, "15u", str(15 * m) + "u")
        s.mos("MT%d" % i, N3, "CTB%d" % i, "TRIM%d" % i, VSS, VSS, "8u", "0.35u")
    schmitt(s, "SC", "RAMP", "SCO")
    inv(s, "IV1", "SCO", "DIS")
    inv(s, "IV2", "DIS", "CKB", wn="4u", wp="8u")
    inv(s, "IV3", "CKB", "CLK", wn="8u", wp="16u")
    s.mos("MDIS", N3, "RAMP", "DIS", VSS, VSS, "2u", "1u")
    s.write("osc_ramp.sch")


def pwm_comp():
    s = Sch("pwm_comp: voltage-mode PWM comparator + set/reset latch with cycle-by-cycle OCP reset", [
        "Comparator OUT = (VC > RAMP).  PWM sets on the CLK pulse (ramp reset) and resets when RAMP crosses VC or OCP_TRIP asserts.",
        "Deviation recorded (design/README.md): sibling comparator_dut is a clocked StrongARM latch; a continuous PWM crossing needs a",
        "continuous-time stage, so a small single-stage comparator is drawn here rather than sizing a second sibling copy.",
        "NMOS-input pair: valid for VC and RAMP between ~1.1 V and ~2.2 V on the 3.3 V rail (checked in the smoke bench).",
    ])
    for k, n in (("ipin", "VC"), ("ipin", "RAMP"), ("ipin", "CLK"), ("ipin", "OCP_TRIP"), ("ipin", "IBIAS"),
                 ("opin", "PWM"), ("iopin", VDD), ("iopin", VSS)):
        s.pin(k, n)
    s.mos("MR", N3, "IBIAS", "IBIAS", VSS, VSS, "10u", "2u")
    ct_comp(s, "CP", "n", "VC", "RAMP", "CMP", "IBIAS")
    inv(s, "IO", "OCP_TRIP", "OCPB")
    nand2(s, "NR", "CMP", "OCPB", "RST")
    nor2(s, "L1", "RST", "QB", "Q")
    nor2(s, "L2", "CLK", "Q", "QB")
    inv(s, "IQ1", "Q", "QN")
    inv(s, "IQ2", "QN", "PWM", wn="4u", wp="8u")
    s.write("pwm_comp.sch")


def soft_start():
    s = Sch("soft_start: analog reference ramp, no counter (R15)", [
        "Iss (IBIAS mirrored down ~1:80, nom. ~125 nA) charges CSS; EN low holds CSS at 0.  VREF_SS = min(CSS, VBG) from a",
        "PMOS-input unity-gain OTA with CSS and VBG as parallel inputs (the lower gate wins, PMOS conducts more).",
        "VREF_SS feeds the error-amplifier reference input; VBG is the adopted bandgap's 1.20 V output.",
        "Ramp time 0 -> 1.2 V = CSS*1.2/Iss; the R15 window is 100-500 us (target tier).",
    ])
    for k, n in (("ipin", "IBIAS"), ("ipin", "VBG"), ("ipin", "EN"), ("opin", "VREF_SS"),
                 ("opin", "CSS"), ("iopin", VDD), ("iopin", VSS)):
        s.pin(k, n)
    s.mos("MN0", N3, "IBIAS", "IBIAS", VSS, VSS, "10u", "2u")
    s.mos("MNS", N3, "SD", "IBIAS", VSS, VSS, "1u", "16u")
    s.mos("MP0", P3, "SD", "SD", VDD, VDD, "4u", "4u")
    s.mos("MP1", P3, "CSS", "SD", VDD, VDD, "4u", "4u")
    s.cap("CS", "CSS", VSS, "100u", "100u")
    inv(s, "IE", "EN", "ENB")
    s.mos("MRST", N3, "CSS", "ENB", VSS, VSS, "2u", "0.5u")
    # min-select OTA, PMOS inputs; tail from a PMOS mirror of IBIAS/2
    s.mos("MCD", N3, "PB", "IBIAS", VSS, VSS, "5u", "2u")
    s.mos("MPB", P3, "PB", "PB", VDD, VDD, "20u", "2u")
    s.mos("MPT", P3, "TL", "PB", VDD, VDD, "20u", "2u")
    s.mos("MA", P3, "Y1", "CSS", "TL", VDD, "16u", "1u")
    s.mos("MB", P3, "Y1", "VBG", "TL", VDD, "16u", "1u")
    s.mos("MF", P3, "VREF_SS", "VREF_SS", "TL", VDD, "16u", "1u")
    s.mos("ML1", N3, "Y1", "Y1", VSS, VSS, "4u", "1u")
    s.mos("ML2", N3, "VREF_SS", "Y1", VSS, VSS, "4u", "1u")
    s.write("soft_start.sch")


def ocp_sense():
    s = Sch("ocp_sense: Ron-sense cycle-by-cycle current limit on the high-side switch (R16, R6 no-trip)", [
        "Senses VIN - SW across the high-side pFET while it conducts.  NMOS pair (thick 6 V) with gates at SW and at VTHP = VIN - Itrip*RT;",
        "branch currents are mirrored from the VIN domain into resistors on the 3.3 V rail; a PMOS-input comparator compares them.",
        "Reverse (negative) inductor current makes SW > VIN, so the pair never trips (R6).  TRIP = raw & HS_ON & blank-delayed HS_ON.",
        "Trip current = Vtrip / Ron_HS: inherits Ron's PVT window (3:1), a die-protection threshold, not a precision limit (R16).",
        "Deviation recorded: sibling comparator_dut cannot take SW/VIN inputs (3.3 V part) and is clocked; the VIN-domain front end is new.",
    ])
    for k, n in (("ipin", "SW"), ("ipin", "HS_ON"), ("ipin", "IBIAS"), ("opin", "TRIP"),
                 ("iopin", "VIN"), ("iopin", VDD), ("iopin", VSS)):
        s.pin(k, n)
    # current references (thick devices, one type so the mirror matches)
    s.mos("MR", N6, "IBIAS", "IBIAS", VSS, VSS, "10u", "2u")
    s.mos("MTAIL", N6, "TAIL", "IBIAS", VSS, VSS, "10u", "2u")
    s.mos("MTRIP", N6, "VTHP", "IBIAS", VSS, VSS, "5u", "2u")
    s.res("RT", "VIN", "VTHP", VSS, "2u", "120u")
    s.mos("MS", N6, "D1", "SW", "TAIL", VSS, "20u", "1u")
    s.mos("MT", N6, "D2", "VTHP", "TAIL", VSS, "20u", "1u")
    s.mos("MP1", P6, "D1", "D1", "VIN", "VIN", "10u", "2u")
    s.mos("MP2", P6, "D2", "D2", "VIN", "VIN", "10u", "2u")
    s.mos("MC1", P6, "V1", "D1", "VIN", "VIN", "10u", "2u")
    s.mos("MC2", P6, "V2", "D2", "VIN", "VIN", "10u", "2u")
    s.res("R1", "V1", VSS, VSS, "2u", "250u")
    s.res("R2", "V2", VSS, VSS, "2u", "250u")
    # 3.3 V domain: pbias for the PMOS-input comparator tail
    s.mos("MNC", N6, "PB", "IBIAS", VSS, VSS, "5u", "2u")
    s.mos("MPB", P3, "PB", "PB", VDD, VDD, "20u", "2u")
    ct_comp(s, "CC", "p", "V2", "V1", "RAW", "PB")
    # gating: TRIP = RAW & HS_ON & blank-delayed HS_ON
    s.res("RB", "HS_ON", "BLR", VSS, "2u", "300u")
    s.cap("CB", "BLR", VSS, "19u", "19u")
    inv(s, "IB1", "BLR", "BLN")
    inv(s, "IB2", "BLN", "BLD")
    nand3(s, "NG", "RAW", "HS_ON", "BLD", "TRN")
    inv(s, "IT", "TRN", "TRIP", wn="4u", wp="8u")
    s.write("ocp_sense.sch")


if __name__ == "__main__":
    osc_ramp()
    pwm_comp()
    soft_start()
    ocp_sense()
    print("wrote 4 schematics in", HERE)
