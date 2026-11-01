#!/usr/bin/env bash
# design/netlist.sh -- (re)generate or check the controller netlists.
#
#   design/netlist.sh                       # export design/schematics/*.sch -> design/netlists/*.spice
#   design/netlist.sh --check               # klt netlist --check per schematic; exit 0 only if all 'match'
#   design/netlist.sh [--check] BLOCK...    # only the named blocks (the item-1 inventory checks one each)
#
# Netlisting goes through `klt netlist` (never raw xschem: it forces headless
# flags and kills a hung run). xschem stamps an absolute `** sch_path:` comment
# into the output; it is rewritten to a repo-relative path after export, and
# --check runs with --ignore-comments so the comparison is on the circuit.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$root/sim/env.sh" >/dev/null
blocks=(power_stage gate_drive osc_ramp pwm_comp soft_start ocp_sense compensator buck_top)
mode=write
if [[ "${1:-}" == "--check" ]]; then mode=--check; shift; fi
if [[ $# -gt 0 ]]; then blocks=("$@"); fi
rc=0
for b in "${blocks[@]}"; do
  sch="$root/design/schematics/$b.sch"
  out="$root/design/netlists/$b.spice"
  common=(--rcfile "$root/design/schematics/xschemrc" --block
          --pdk-root "$(dirname "$GF180_VARIANT_DIR")" --format text)
  if [[ "$mode" == "--check" ]]; then
    klt netlist "${common[@]}" --ignore-comments --check -o "$out" "$sch" 2>&1 | grep -E 'match|drifted|error' || true
    klt netlist "${common[@]}" --ignore-comments --check -o "$out" "$sch" >/dev/null 2>&1 || { echo "$b: DRIFTED"; rc=1; }
  else
    mkdir -p "$root/design/netlists"
    klt netlist "${common[@]}" -o "$out" "$sch" >/dev/null
    # every descended block carries its own sch_path line: rewrite each to its repo-relative path
    sed -i -E 's|^\*\* sch_path: .*/design/schematics/([^/]+\.sch)$|** sch_path: design/schematics/\1|' "$out"
    echo "wrote design/netlists/$b.spice"
  fi
done
exit $rc
