#!/usr/bin/env bash
# Cold-start smoke run: one .op + one short .tran, a single ngspice process.
# Writes sim/build/smoke/ (ignored). A record is appended under
# sim/smoke/records/ only when its evidence is new (issue #180): if the
# newest existing record already carries this run's simulator version, PDK
# revision, model file, deck sha256 and all five printed numbers, the run is
# a duplicate and no record is written. Anything unparseable writes anyway
# (fail open); so does ambiguous evidence (a missing, duplicated or
# non-numeric measurement or header). A failed measurement fails the run.
# Usage: sim/smoke/run.sh
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
source "$root/sim/env.sh"
command -v ngspice >/dev/null || { echo "run.sh: MISSING_TOOL: ngspice not on PATH" >&2; exit 1; }

build="$root/sim/build/smoke"; mkdir -p "$build" "$here/records"
deck_sha="$(sha256sum "$here/inverter.spice" | cut -d' ' -f1)"
sed -e "s|@MODEL_FILE@|$GF180_MODEL_FILE|" -e "s|@DESIGN_INC@|$GF180_DESIGN_INC|" \
  "$here/inverter.spice" > "$build/inverter.run.spice"

ngspice_ver="$(ngspice --version | grep -m1 -o 'ngspice-[0-9][0-9.]*')"
cmd="ngspice -b -o sim/build/smoke/ngspice.log sim/build/smoke/inverter.run.spice"
(cd "$root" && $cmd)

num='-?[0-9]+(\.[0-9]*)?([eE][-+]?[0-9]+)?'

# pick_one PATTERN TEXT: print the one line of TEXT matching PATTERN; fail
# when there are none or more than one (ambiguous evidence is not evidence).
pick_one() {
  local n
  n="$(grep -cE -- "$1" <<<"$2" || true)"
  [[ "$n" -eq 1 ]] || return 1
  grep -E -- "$1" <<<"$2"
}

# meas_lines TEXT: print the four .meas lines (vout_hi, vout_lo, tphl, tplh),
# each present exactly once with a numeric value; fail otherwise.
meas_lines() {
  local name line
  for name in vout_hi vout_lo tphl tplh; do
    line="$(pick_one "^$name " "$1")" || return 1
    [[ "$line" =~ ^$name\ +=\ +$num(\ |$) ]] || return 1
    printf '%s\n' "$line"
  done
}

# op_line TEXT: print the single parseable RESULT op line; fail otherwise.
op_line() {
  local line
  line="$(pick_one '^RESULT op' "$1")" || return 1
  [[ "$line" =~ ^RESULT\ op\ vin=[^\ ]+\ v\(out\)=\ *$num\ idd=\ *$num\ *$ ]] || return 1
  printf '%s\n' "$line"
}

log="$(cat "$build/ngspice.log")"
op="$(op_line "$log")" || { echo "run.sh: FAIL: no single parseable operating-point result in log" >&2; exit 1; }
meas="$(meas_lines "$log")" || { echo "run.sh: FAIL: a .meas result is missing, duplicated or non-numeric in log" >&2; exit 1; }

sha="$(git -C "$root" rev-parse --short=12 HEAD)"
ts="$(date -u +%Y%m%dT%H%M%SZ)"
rec="$here/records/$ts-$sha.md"
body="$(printf '%s\n' \
  "# Smoke record $ts (simulated, not measured)" \
  "" \
  "- simulator: $ngspice_ver" \
  "- PDK: gf180mcu $PDK revision $GF180_PDK_REVISION (sim/pdk.json)" \
  "- model file: $GF180_MODEL_FILE (typical corner), supply 5 V" \
  "- deck: sim/smoke/inverter.spice sha256 $deck_sha" \
  "- repo commit at run: $sha" \
  "- command: \`sim/smoke/run.sh\` -> \`$cmd\`" \
  "- run length: .op, then .tran step 50p stop 60n (3 input periods of 20 ns, no steady-state claim needed: a single-stage CMOS inverter has no slow state)" \
  "" \
  "## Headline numbers (ngspice output, verbatim)" \
  '```' \
  "$op" \
  "$meas" \
  '```')"

# evidence: print a record body's evidence fields (simulator, PDK, model file,
# deck sha256, the RESULT op line and the four .meas lines) on stdout. Each
# header must appear exactly once and parse, the op line and every .meas line
# must be single and usable; otherwise fail, so an ambiguous or unparseable
# body never suppresses a write.
evidence() {
  local src sim pdk model deck o m
  src="$(cat)"
  sim="$(pick_one '^- simulator: ' "$src")"    || return 1
  pdk="$(pick_one '^- PDK: ' "$src")"          || return 1
  model="$(pick_one '^- model file: ' "$src")" || return 1
  deck="$(pick_one '^- deck: ' "$src")"        || return 1
  [[ "$sim" =~ ^-\ simulator:\ ngspice-[0-9][0-9.]*$ ]]             || return 1
  [[ "$pdk" =~ ^-\ PDK:\ .*\ revision\ [0-9a-f]{40}\  ]]           || return 1
  [[ "$model" =~ ^-\ model\ file:\ [^\ ]+\  ]]                      || return 1
  [[ "$deck" =~ ^-\ deck:\ .*\ sha256\ [0-9a-f]{64}$ ]]            || return 1
  o="$(op_line "$src")"                         || return 1
  m="$(meas_lines "$src")"                      || return 1
  printf '%s\n%s\n%s\n%s\n%s\n%s\n' "$sim" "$pdk" "$model" "$deck" "$o" "$m"
}

newest=""
shopt -s nullglob
recs=( "$here/records"/*.md )
shopt -u nullglob
if [[ ${#recs[@]} -gt 0 ]]; then newest="${recs[${#recs[@]}-1]}"; fi
if [[ -n "$newest" ]] \
   && new_ev="$(printf '%s\n' "$body" | evidence)" \
   && old_ev="$(evidence < "$newest")" \
   && [[ "$new_ev" == "$old_ev" ]]; then
  echo "run.sh: OK, unchanged since $(basename "$newest" .md); no new record"
  exit 0
fi
[[ ! -e "$rec" ]] || { echo "run.sh: records are append-only; $rec exists" >&2; exit 1; }
printf '%s\n' "$body" > "$rec"
echo "run.sh: OK, record $rec"
