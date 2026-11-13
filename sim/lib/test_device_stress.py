"""Tests for sim/device-stress: verdict rules of collect.py, request/bench drift guards.

Run: python3 -m unittest discover sim/lib
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DS = os.path.join(ROOT, "sim", "device-stress")
sys.path.insert(0, DS)
sys.path.insert(0, HERE)
import collect  # noqa: E402


def unit(uid, sw_min=0.0, term=5.0, settled=True, edge_ok=True, dead=(2e-9, 4e-9), overlap=0.0):
    p = {"sw_min_v": sw_min, "sw_max_v": 5.0, "terminal_max": {"abs_v": term}}
    d = {"min_s": dead[0], "max_s": dead[1], "overlap_s": overlap}
    return {"id": uid, "peaks": p, "settled": settled, "edge": {"ok": edge_ok}, "dead_time": d,
            "dead_time_saved_window": d}


def row(units, fn, expected):
    return collect.judge(units, "x", fn, expected, "t", {})


class VerdictTest(unittest.TestCase):
    def test_complete_clean_set_passes(self):
        n = collect.EXPECTED["grid"]
        r = row([unit("u%d" % i) for i in range(n)], collect.r2_margin, n)
        self.assertEqual(r["verdict"], "pass")
        self.assertTrue(r["corner_set_complete"])

    def test_clean_ctyp_subset_is_not_demonstrated(self):
        n = collect.EXPECTED["ctyp"]
        for fn in (collect.r2_margin, collect.r14_margin):
            r = row([unit("u%d" % i) for i in range(n)], fn, n)
            self.assertEqual(r["verdict"], "not_demonstrated")
            self.assertFalse(r["corner_set_complete"])

    def test_ctyp_subset_with_a_failure_still_fails(self):
        n = collect.EXPECTED["ctyp"]
        us = [unit("u%d" % i) for i in range(n - 1)] + [unit("bad", sw_min=-0.71)]
        self.assertEqual(row(us, collect.r2_margin, n)["verdict"], "fail")

    def test_134_of_135_clean_is_not_demonstrated(self):
        n = collect.EXPECTED["grid"] - 1
        self.assertEqual(row([unit("u%d" % i) for i in range(n)], collect.r2_margin, 135)["verdict"], "not_demonstrated")

    def test_135_with_one_no_value_unit_is_not_demonstrated(self):
        n = collect.EXPECTED["grid"]
        us = [unit("u%d" % i) for i in range(n - 1)] + [unit("x", settled=False)]
        self.assertEqual(row(us, collect.r2_margin, n)["verdict"], "not_demonstrated")

    def test_subset_cannot_pass_the_row(self):
        r = row([unit("a"), unit("b")], collect.r2_margin, 135)
        self.assertEqual(r["verdict"], "not_demonstrated")
        self.assertFalse(r["corner_set_complete"])

    def test_unsettled_run_yields_no_value(self):
        r = row([unit("a"), unit("b", settled=False)], collect.r2_margin, 2)
        self.assertEqual(r["verdict"], "not_demonstrated")
        self.assertEqual(r["no_value_units"], ["b"])

    def test_unresolved_edges_cannot_pass(self):
        r = row([unit("a", edge_ok=False)], collect.r2_margin, 1)
        self.assertEqual(r["verdict"], "not_demonstrated")

    def test_exceedance_fails_even_when_unsettled_and_unresolved(self):
        r = row([unit("a"), unit("b", sw_min=-0.71, settled=False, edge_ok=False)], collect.r2_margin, 2)
        self.assertEqual(r["verdict"], "fail")
        self.assertEqual(r["failing_units"], ["b"])
        self.assertEqual(r["binding"]["id"], "b")

    def test_six_volts_exactly_is_not_a_failure(self):
        self.assertGreaterEqual(collect.r2_margin(unit("a", term=6.0)), 0)
        self.assertLess(collect.r2_margin(unit("a", term=6.01)), 0)

    def test_dead_time_band_and_overlap(self):
        full = collect.EXPECTED["grid"]
        self.assertEqual(row([unit("u%d" % i, dead=(1e-9, 6e-9)) for i in range(full)], collect.r14_margin, full)["verdict"], "pass")
        self.assertEqual(row([unit("a", dead=(0.9e-9, 5e-9))], collect.r14_margin, 1)["verdict"], "fail")
        self.assertEqual(row([unit("a", dead=(2e-9, 6.1e-9))], collect.r14_margin, 1)["verdict"], "fail")
        self.assertEqual(row([unit("a", overlap=1e-12)], collect.r14_margin, 1)["verdict"], "fail")

    def test_missing_threshold_gives_no_value(self):
        u = unit("a")
        u["dead_time"] = None
        self.assertEqual(row([u], collect.r14_margin, 1)["verdict"], "not_demonstrated")

    def test_corner_id_parse(self):
        k = collect.parse_id("sf/5.500V/-40C/params:iload=0.05")
        self.assertEqual((k["process"], k["vin_v"], k["temp_c"], k["iload_a"]), ("sf", 5.5, -40.0, 0.05))


HARNESS = os.path.join(ROOT, "sim", "lib", "bench_harness.spice")
CLOSED_LOOP_BENCHES = ("steady-state", "current-limit", "device-stress", "load-step", "soft-start")


# What the shared harness reads from the deck that includes it.
HARNESS_PARAMS = ("r_wire", "l_wire", "wires", "c_die", "esr_die", "vdd3", "vbg",
                  "t_en", "l_ind", "dcr", "c_wind", "r_wind", "c_out", "esr", "esl")

# Values that must mean the same thing in every closed-loop bench: the spec 0.2 external parts,
# the spec 0.3 package, the control-domain rails, and the inlined design.ngspice switches.
SHARED_ASSUMPTIONS = HARNESS_PARAMS + (
    "sw_stat_global", "sw_stat_mismatch", "mc_skew", "res_mc_skew", "cap_mc_skew", "fnoicor")

PARAM_ASSIGN = re.compile(r"(\w+)\s*=\s*(\S+)")


def params(path):
    """{name: value-as-written} over every .param line of a SPICE deck, continuations included."""
    out = {}
    for line in open(path).read().splitlines():
        s = line.strip()
        if not (s.startswith(".param") or s.startswith("+")):
            continue
        s = s[len(".param"):] if s.startswith(".param") else s[1:]
        out.update(PARAM_ASSIGN.findall(s))
    return out


def element_cards(path):
    """Lower-cased instance names of the element cards in a SPICE file (no directives,
    no comments, no continuations)."""
    names = []
    for line in open(path).read().splitlines():
        s = line.strip()
        if not s or s[0] in "*.+":
            continue
        names.append(s.split()[0].lower())
    return names


class DriftTest(unittest.TestCase):
    """Every closed-loop bench shares one harness instead of copying it (issue #151).

    This replaces the line-for-line comparison of the device-stress deck against the
    steady-state deck: the package, die decoupling, control-domain sources, buck_top
    instance and external L/C now live once in sim/lib/bench_harness.spice, and the
    guard covers all five decks rather than device-stress alone.
    """

    def test_harness_holds_the_shared_element_cards(self):
        names = element_cards(HARNESS)
        self.assertEqual(sorted(names), sorted(set(names)), "duplicate element name in the harness")
        for card in ("rwv", "lwv", "rws", "lws", "rwg", "lwg", "cdie", "rdie",
                     "vdd33", "vbg", "ipwm", "iss", "iocp", "iea",
                     "vt0", "vt1", "vt2", "ven", "xtop",
                     "lind", "rdcr", "cwind", "rwind", "cout", "resr", "lesl"):
            self.assertIn(card, names, "shared harness lost element card %r" % card)

    def test_every_closed_loop_bench_includes_the_harness(self):
        for bench in CLOSED_LOOP_BENCHES:
            deck = open(os.path.join(ROOT, "sim", bench, "bench.spice")).read()
            self.assertIn(".include ../lib/bench_harness.spice", deck,
                          "%s bench does not include the shared harness" % bench)

    def test_no_bench_redeclares_a_harness_card(self):
        shared = set(element_cards(HARNESS))
        for bench in CLOSED_LOOP_BENCHES:
            for name in element_cards(os.path.join(ROOT, "sim", bench, "bench.spice")):
                self.assertNotIn(name, shared,
                                 "%s bench re-declares harness card %r: the copy is back" % (bench, name))

    def test_vsrc_and_iosc_stay_in_every_top_level_deck(self):
        """The two cards the harness deliberately does not own.

        Vsrc: klt rescales that PWL per corner, which it can only do in the top-level deck
        (sim/device-stress/README.md). Iosc: current-limit sweeps the oscillator bias as
        osc_k, and ngspice does not re-parse `{12u*osc_k}` to the same double as the literal
        `12u`, so a single shared expression form would move every other deck's trajectory.
        """
        harness = element_cards(HARNESS)
        for card in ("vsrc", "iosc"):
            self.assertNotIn(card, harness, "%r does not belong in the shared harness" % card)
            for bench in CLOSED_LOOP_BENCHES:
                self.assertIn(card, element_cards(os.path.join(ROOT, "sim", bench, "bench.spice")),
                              "%s bench has no top-level %r" % (bench, card))

    def test_the_osc_bias_card_is_the_same_wherever_it_is_not_swept(self):
        """Only current-limit sweeps osc_k; the other four must write the identical literal."""
        cards = {}
        for bench in CLOSED_LOOP_BENCHES:
            for line in open(os.path.join(ROOT, "sim", bench, "bench.spice")).read().splitlines():
                if line.strip().lower().startswith("iosc "):
                    cards[bench] = line.strip()
        self.assertEqual(cards["current-limit"], "Iosc gnd_d ib_osc PWL(0 0 5u {12u*osc_k})")
        fixed = {b: c for b, c in cards.items() if b != "current-limit"}
        self.assertEqual(set(fixed.values()), {"Iosc gnd_d ib_osc PWL(0 0 5u 12u)"},
                         "the oscillator-bias card has drifted between decks: %r" % fixed)

    def test_every_bench_defines_the_params_the_harness_reads(self):
        # The harness is pure element cards; each deck declares the values it reads.
        for bench in CLOSED_LOOP_BENCHES:
            declared = params(os.path.join(ROOT, "sim", bench, "bench.spice"))
            for name in HARNESS_PARAMS:
                self.assertIn(name, declared,
                              "%s bench does not define %r, which the shared harness reads" % (bench, name))

    def test_the_shared_assumptions_agree_across_every_bench(self):
        """The P-T part and package values stay in each top-level deck, so guard them by value.

        They are not moved into the harness on purpose: `c_out` and `esr` are request axes in
        sim/load-step/request_{tol,full}.json and `c_wind` in sim/soft-start/probe_single3.json,
        while the same names are fixed assumptions in the other decks -- a deck's own axis
        defaults belong to that deck. (A `klt sim` corners.params override does reach a .param
        declared in an included file: probed on issue #151 with lfac=0.8, which gave l_ind
        2.64 uH. The mechanism is not the reason these lines stayed put.)
        """
        ref = params(os.path.join(ROOT, "sim", CLOSED_LOOP_BENCHES[0], "bench.spice"))
        for bench in CLOSED_LOOP_BENCHES[1:]:
            other = params(os.path.join(ROOT, "sim", bench, "bench.spice"))
            for name in SHARED_ASSUMPTIONS:
                self.assertEqual(ref[name], other[name],
                                 "%s bench has drifted on %r: %r vs %r in %s"
                                 % (bench, name, other[name], ref[name], CLOSED_LOOP_BENCHES[0]))

    def test_device_stress_keeps_its_own_includes_and_replicas(self):
        ds = open(os.path.join(DS, "bench.spice")).read()
        self.assertIn(".include ../steady-state/opamp_two_stage.spice", ds)
        for card in ("Xvthn", "Ithn", "Xvthp", "Vthp_s", "Ithp", "Bvthp"):
            self.assertIn(card, ds, "device-stress bench lost Vth replica card %r" % card)

    def test_generated_requests_match_committed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            # the generator imports sim/lib/genkit.py as ../lib/genkit.py: mirror that layout under tmp
            out = os.path.join(tmp, "device-stress")
            os.makedirs(out)
            shutil.copy(os.path.join(DS, "gen_requests.py"), out)
            shutil.copytree(os.path.join(ROOT, "sim", "lib"), os.path.join(tmp, "lib"))
            subprocess.run([sys.executable, "-I", os.path.join(out, "gen_requests.py")], check=True)
            for f in ("request_grid.json", "request_ctyp.json", "matrix_grid.json", "matrix_ctyp.json"):
                self.assertEqual(json.load(open(os.path.join(out, f))), json.load(open(os.path.join(DS, f))), f)

    def test_request_states_the_100ps_step_and_c_full(self):
        req = json.load(open(os.path.join(DS, "request_grid.json")))
        self.assertTrue(req["analysis"]["args"].startswith("100p "))
        self.assertEqual(req["analysis"]["args"].split()[-1], "100p")        # tmax
        c = req["corners"]
        self.assertEqual(len(c["process"]) * len(c["temperature_c"]) * len(c["supply_v"]["vsrc"]), 45)
        self.assertEqual(c["params"]["iload"], [0.0, 0.05, 0.5])


if __name__ == "__main__":
    unittest.main()
