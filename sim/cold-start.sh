#!/usr/bin/env bash
# The one cold-start command for T1 item 9: the smoke bench, the ideal-buck
# bench, the sim/lib and design/averaged unit tests and the averaged-model
# grid, in order. Usage: sim/cold-start.sh
# Not every attested bench: the rest are hashed in
# manifests/item9-inventory.json but not run here (see sim/README.md).
# Each bench appends a new record under its records/ (append-only evidence).
# design/averaged/run.sh sends its grid through `klt sim` (batch fleet); a
# batch submit failure fails this script. There is no local-grid fallback.
# Needs the pinned PDK (sim/pdk.json), ngspice, jq, python3, and klt on PATH.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

echo "cold-start: smoke bench"
sim/smoke/run.sh
echo "cold-start: ideal-buck bench"
sim/buck-ideal/run.sh
echo "cold-start: unit tests"
python3 -m unittest discover sim/lib
python3 -m unittest discover -s design/averaged -p "test_*.py"
echo "cold-start: averaged-model grid (klt sim, batch)"
design/averaged/run.sh
echo "cold-start: OK"
