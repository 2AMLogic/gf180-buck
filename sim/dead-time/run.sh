#!/usr/bin/env bash
# Dead-time smoke (issue #33): ONE operating point, run locally through
# `klt sim --backend local` (a single unit; no corner grid, no ngspice loop).
# Runs the real gate drive + power stage (request.json) and a no-dead-time
# negative control (request_control.json), then writes a new append-only
# record under sim/dead-time/records/. Usage: sim/dead-time/run.sh
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
for tool in klt jq sha256sum git ngspice; do
  command -v "$tool" >/dev/null || { echo "run.sh: MISSING_TOOL: $tool not on PATH" >&2; exit 1; }
done
source "$root/sim/env.sh"
# klt picks the first PDK install it finds; pin the one sim/env.sh verified.
export PDK_ROOT="$(dirname "$GF180_VARIANT_DIR")"

build="$root/sim/build/dead-time"; rm -rf "$build"; mkdir -p "$build" "$here/records"
run_one() {  # $1 = name, $2 = request
  klt sim "$here/$2" --backend local -o "$build/$1" --report-out "$build/$1.json" \
    --format json >"$build/$1.stdout" 2>"$build/$1.stderr" || true
  [[ -s "$build/$1.json" ]] || { echo "run.sh: FAIL: no report for $1" >&2; tail -5 "$build/$1.stderr" >&2; exit 1; }
}
run_one dut request.json
run_one control request_control.json

m() { jq -r --arg n "$2" '.corners[0].measurements[] | select(.name==$n) | .value' "$build/$1.json"; }
[[ "$(jq -r .status "$build/dut.json")" == pass && "$(jq -r .status "$build/control.json")" == pass ]] \
  || { echo "run.sh: FAIL: klt sim did not complete cleanly (see $build/*.json)" >&2; exit 1; }

sha="$(git -C "$root" rev-parse --short=12 HEAD)"; ts="$(date -u +%Y%m%dT%H%M%SZ)"
rec="$here/records/$ts-$sha.json"
[[ ! -e "$rec" ]] || { echo "run.sh: records are append-only; $rec exists" >&2; exit 1; }
h() { sha256sum "$root/$1" | cut -d' ' -f1; }
ov="$(m dut overlap_max)"; ovc="$(m control overlap_max)"
jq -n --arg ts "$ts" --arg sha "$sha" --arg ver "$(ngspice --version | grep -m1 -o 'ngspice-[0-9][0-9.]*')" \
  --arg klt "$(klt --version)" --arg lib "$(jq -r .environment.models_lib_sha256 "$build/dut.json")" \
  --arg dsha "$(h sim/dead-time/deadtime.spice)" --arg csha "$(h sim/dead-time/control.spice)" \
  --arg gsha "$(h design/netlists/gate_drive.spice)" --arg psha "$(h design/netlists/power_stage.spice)" \
  --argjson ov "$ov" --argjson ovc "$ovc" \
  --argjson tda "$(m dut td_ls_off_to_hs_on)" --argjson tdb "$(m dut td_hs_off_to_ls_on)" \
  --argjson swmax "$(m dut sw_max)" --argjson swmin "$(m dut sw_min)" '
  {record: "simulated, not measured; ONE operating point, no corner grid, no claim against R14 or R2",
   environment: {utc: $ts, repo_commit: $sha, simulator: $ver, klt: $klt, models_lib_sha256: $lib,
     command: "sim/dead-time/run.sh -> klt sim --backend local (typical, 27 C)",
     decks: {"sim/dead-time/deadtime.spice": $dsha, "sim/dead-time/control.spice": $csha,
             "design/netlists/gate_drive.spice": $gsha, "design/netlists/power_stage.spice": $psha}},
   operating_point: {process: "typical", temperature_c: 27, vin_v: 5.0, vdd3_v: 3.3, load: "0.5 A DC sink on SW",
     pwm: "500 ns period, 180 ns high (D = 0.36)", overlap_thresholds: "GL > 0.5 V and (VIN - GH) > 0.5 V",
     tran: "step 20 ps max, stop 2.6 us; measured over 1.0-2.6 us (the third to fifth period; edges numbered 3 of the run); no steady-state claim: logic-only state, no slow node"},
   result: {overlap_max: $ov, overlap_max_negative_control: $ovc,
     dead_time_ls_off_to_hs_on_s: $tda, dead_time_hs_off_to_ls_on_s: $tdb,
     sw_max_v: $swmax, sw_min_v: $swmin}}' > "$rec"
echo "run.sh: record $rec"
jq -en --argjson a "$ov" --argjson b "$ovc" '$a == 0 and $b == 1' >/dev/null || { echo "run.sh: FAIL: overlap_max=$ov (want 0), control=$ovc (want 1)" >&2; exit 1; }
echo "run.sh: OK"
