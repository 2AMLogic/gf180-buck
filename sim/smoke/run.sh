#!/usr/bin/env bash
# Cold-start smoke run: one .op + one short .tran, a single ngspice process.
# Writes sim/build/smoke/ (ignored) and a new append-only record under
# sim/smoke/records/. Usage: sim/smoke/run.sh
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

res() { grep -m1 -E "^$1 " "$build/ngspice.log" | sed -E 's/^[a-z_]+ *= *//; s/ .*//'; }
op_line="$(grep -m1 '^RESULT op' "$build/ngspice.log")"
[[ -n "$op_line" ]] || { echo "run.sh: FAIL: no operating-point result in log" >&2; exit 1; }

sha="$(git -C "$root" rev-parse --short=12 HEAD)"
ts="$(date -u +%Y%m%dT%H%M%SZ)"
rec="$here/records/$ts-$sha.md"
[[ ! -e "$rec" ]] || { echo "run.sh: records are append-only; $rec exists" >&2; exit 1; }
{
  echo "# Smoke record $ts (simulated, not measured)"
  echo
  echo "- simulator: $ngspice_ver"
  echo "- PDK: gf180mcu $PDK revision $GF180_PDK_REVISION (sim/pdk.json)"
  echo "- model file: $GF180_MODEL_FILE (typical corner), supply 5 V"
  echo "- deck: sim/smoke/inverter.spice sha256 $deck_sha"
  echo "- repo commit at run: $sha"
  echo "- command: \`sim/smoke/run.sh\` -> \`$cmd\`"
  echo "- run length: .op, then .tran step 50p stop 60n (3 input periods of 20 ns, no steady-state claim needed: a single-stage CMOS inverter has no slow state)"
  echo
  echo "## Headline numbers (ngspice output, verbatim)"
  echo '```'
  echo "$op_line"
  grep -E '^(vout_hi|vout_lo|tphl|tplh) ' "$build/ngspice.log"
  echo '```'
} > "$rec"
echo "run.sh: OK, record $rec"
