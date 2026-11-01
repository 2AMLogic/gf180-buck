#!/usr/bin/env bash
# Single-corner local smoke for the controller blocks (issue #34).
# One ngspice process per bench, run one after another: typical corner, 27 C,
# nominal rails. NOT a corner or Monte Carlo grid -- those go to `klt sim`
# (issue #25). Prints the RESULT lines; with --record also writes a new
# append-only record under design/smoke/records/.
#   design/smoke/run.sh [--record] [bench ...]    (default: all five)
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
source "$root/sim/env.sh" >/dev/null
command -v ngspice >/dev/null || { echo "run.sh: MISSING_TOOL: ngspice" >&2; exit 1; }
record=0; [[ "${1:-}" == "--record" ]] && { record=1; shift; }
benches=("$@"); [[ ${#benches[@]} -gt 0 ]] || benches=(osc_ramp pwm_comp soft_start ocp_fwd ocp_rev)
build="$root/design/smoke/build"; mkdir -p "$build"
out=""
for b in "${benches[@]}"; do
  sed -e "s|@MODEL_FILE@|$GF180_MODEL_FILE|" -e "s|@DESIGN_INC@|$GF180_DESIGN_INC|" \
      -e "s|@NETLIST_DIR@|$root/design/netlists|" "$here/$b.spice" > "$build/$b.run.spice"
  ngspice -b -o "$build/$b.log" "$build/$b.run.spice" >/dev/null 2>&1 || true
  line="$(grep -m1 '^RESULT' "$build/$b.log" || echo "RESULT $b FAILED (see $build/$b.log)")"
  echo "$line"; out+="$line"$'\n'
  grep -E '^(tper20|vhi|vlo|idd|vrhi|vrlo|duty_[a-z]+|t10|t90|t_trip|trip_max) ' "$build/$b.log" | sed 's/^/    /' || true
done
if [[ $record -eq 1 ]]; then
  mkdir -p "$here/records"
  sha="$(git -C "$root" rev-parse --short=12 HEAD)"; ts="$(date -u +%Y%m%dT%H%M%SZ)"
  rec="$here/records/$ts-$sha.md"
  [[ ! -e "$rec" ]] || { echo "records are append-only; $rec exists" >&2; exit 1; }
  {
    echo "# Controller smoke record $ts (simulated, not measured)"
    echo
    echo "- simulator: $(ngspice --version | grep -m1 -o 'ngspice-[0-9][0-9.]*')"
    echo "- PDK: gf180mcu $PDK revision $GF180_PDK_REVISION (sim/pdk.json); typical corner, 27 C, one process per bench"
    echo "- netlist sha256: $(cat "$root"/design/netlists/*.spice | sha256sum | cut -d' ' -f1) (cat of design/netlists/*.spice)"
    echo "- repo commit at run: $sha"
    echo "- command: \`design/smoke/run.sh --record\`"
    echo
    echo '```'
    printf '%s' "$out"
    echo '```'
  } > "$rec"
  echo "wrote $rec"
fi
