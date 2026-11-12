#!/usr/bin/env python3
"""stressmeas: R2 (device stress) and R14 (dead time) measures on a switched buck_top waveform.

Pure functions over lists of floats (stdlib only), driven by sim/device-stress/collect.py.
Terminals are the die-side nodes of the power stage: vin = V(vin_d), sw = V(sw_d), gnd = V(gnd_d),
gh / gl = the power-device gates. The high-side device is a PMOS (source = VIN, drain = SW), the
low-side an NMOS (source = GND, drain = SW); each bulk is tied to its source.

R2 (spec target tier): SW >= -0.7 V and every power-device terminal-to-terminal voltage <= 6.0 V,
peaks over the whole saved window, no transient credit. R14: dead time between the commanded
turn-off of one device and the turn-on of the other, measured at |Vgs| = the device's Vth for this
corner (the replica level), zero overlap = never both |Vgs| above their Vth.
"""
import bisect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from buckmeas import crossings  # noqa: E402

R2_SW_MIN = -0.7      # V
R2_TERM_MAX = 6.0     # V
EDGE_STEP_MAX = 100e-12   # s, spec 0.4
EDGE_PRE, EDGE_POST = 2e-9, 10e-9   # edge window around a mid-swing crossing: [-2 ns, +10 ns] (ringing)


def device_voltages(vin, sw, gnd, gh, gl):
    """Per-sample terminal voltages of both power devices (lists, same length)."""
    return {
        "hs_vgs": [g - v for g, v in zip(gh, vin)], "hs_vds": [s - v for s, v in zip(sw, vin)],
        "hs_vgd": [g - s for g, s in zip(gh, sw)],
        "ls_vgs": [g - n for g, n in zip(gl, gnd)], "ls_vds": [s - n for s, n in zip(sw, gnd)],
        "ls_vgd": [g - s for g, s in zip(gl, sw)],
    }


def stress_peaks(t, vin, sw, gnd, gh, gl):
    """R2 peaks over the whole waveform: SW min / max (die side, and relative to the die ground) and the
    largest |terminal voltage| of the six device pairs, with the time and the name of each."""
    dv = device_voltages(vin, sw, gnd, gh, gl)
    sw_rel = [s - n for s, n in zip(sw, gnd)]
    i_min = min(range(len(sw)), key=lambda k: min(sw[k], sw_rel[k]))
    worst = None
    for name, y in dv.items():
        k = max(range(len(y)), key=lambda j: abs(y[j]))
        if worst is None or abs(y[k]) > worst["abs_v"]:
            worst = {"terminal": name, "abs_v": abs(y[k]), "signed_v": y[k], "t_s": t[k]}
    return {"sw_min_v": min(min(sw), min(sw_rel)), "sw_min_t_s": t[i_min],
            "sw_min_die_abs_v": min(sw), "sw_min_vs_gnd_v": min(sw_rel),
            "sw_max_v": max(sw), "terminal_max": worst,
            "per_terminal_max_abs_v": {n: max(abs(v) for v in y) for n, y in dv.items()}}


def r2_verdict(peaks):
    """(sw_ok, term_ok, binding) for one unit. Pure comparison against the unrelaxed limits."""
    sw_ok = peaks["sw_min_v"] >= R2_SW_MIN
    term_ok = max(peaks["terminal_max"]["abs_v"], peaks["sw_max_v"]) <= R2_TERM_MAX
    return sw_ok, term_ok


def edge_resolution(t, sw, vin_level, gh, gl):
    """Largest .tran step inside the edge windows, [-2 ns, +10 ns] around every mid-swing crossing
    of SW (vin/2) and of both gates (mid of each gate's own min..max in the window). Returns
    {max_step_s, n_windows, ok}; ok False when any edge window has a step above 100 ps, or no edge at all."""
    mids = []
    for y, lvl in ((sw, vin_level / 2.0), (gh, 0.5 * (min(gh) + max(gh))), (gl, 0.5 * (min(gl) + max(gl)))):
        mids += crossings(t, y, lvl, True) + crossings(t, y, lvl, False)
    mids.sort()
    worst = 0.0
    for c in mids:
        i0 = bisect.bisect_left(t, c - EDGE_PRE)
        i1 = bisect.bisect_right(t, c + EDGE_POST)
        for k in range(max(i0, 1), min(i1, len(t))):
            worst = max(worst, t[k] - t[k - 1])
    return {"max_step_s": worst if mids else None, "n_windows": len(mids),
            "ok": bool(mids) and worst <= EDGE_STEP_MAX * (1 + 1e-9)}


def dead_time(t, vin, gnd, gh, gl, vth_n, vth_p, t0, t1):
    """R14 on [t0, t1]: LS-gate turn-off (Vgs_n falls through vth_n) to the next HS turn-on (Vsg_p
    rises through vth_p), and HS turn-off to the next LS turn-on, per transition pair; plus the overlap
    time, i.e. the total time both devices have |Vgs| above their thresholds (zero required).
    Returns the lists of dead times, the min / max of each, the overlap duration and the pair counts.
    `overlap_s` sums every sample interval with at least one overlapped end sample, so it is an upper bound,
    quantised to the .tran step (100 ps); any non-zero value means the zero-overlap rule is broken.
    A transition with no partner (window edge) is not counted."""
    idx = [i for i in range(len(t)) if t0 <= t[i] <= t1]
    tt = [t[i] for i in idx]
    vn = [gl[i] - gnd[i] for i in idx]       # NMOS Vgs
    vp = [vin[i] - gh[i] for i in idx]       # PMOS Vsg
    ls_off, ls_on = crossings(tt, vn, vth_n, False), crossings(tt, vn, vth_n, True)
    hs_on, hs_off = crossings(tt, vp, vth_p, True), crossings(tt, vp, vth_p, False)

    def pairs(offs, ons):
        out = []
        for o in offs:
            k = bisect.bisect_right(ons, o)
            nxt = offs[bisect.bisect_right(offs, o)] if bisect.bisect_right(offs, o) < len(offs) else None
            if k < len(ons) and (nxt is None or ons[k] < nxt):
                out.append(ons[k] - o)
        return out
    td_ls_hs = pairs(ls_off, hs_on)
    td_hs_ls = pairs(hs_off, ls_on)
    overlap = 0.0
    for k in range(1, len(tt)):
        a = vn[k - 1] > vth_n and vp[k - 1] > vth_p
        b = vn[k] > vth_n and vp[k] > vth_p
        if a or b:
            overlap += tt[k] - tt[k - 1]
    allv = td_ls_hs + td_hs_ls
    return {"td_ls_off_to_hs_on_s": td_ls_hs, "td_hs_off_to_ls_on_s": td_hs_ls,
            "n_pairs": [len(td_ls_hs), len(td_hs_ls)],
            "min_s": min(allv) if allv else None, "max_s": max(allv) if allv else None,
            "overlap_s": overlap}
