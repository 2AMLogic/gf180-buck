#!/usr/bin/env bash
# The one cold-start command for T1 item 9: every shipped bench and its unit
# tests, in order. Usage: sim/cold-start.sh
# Each bench appends a new record under its records/ (append-only evidence).
# design/averaged/run.sh sends its grid through `klt sim` (batch fleet); a
# launch refused for fleet capacity waits up to 600 s with backoff first, and
# a submit that still fails fails this script. There is no local-grid fallback.
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
