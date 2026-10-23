#!/usr/bin/env bash
# The one documented command: regenerate the request, run the 162-point grid
# through `klt sim` (batch fleet by default), extract fc/PM/GM, write a record.
# Usage: design/averaged/run.sh [--fail-on-violation]
# The grid is never run as a local ngspice loop. A batch submit failure exits
# non-zero; report it, do not fall back to --backend local.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
build="$here/build"; rm -rf "$build"; mkdir -p "$build"
command -v klt >/dev/null || { echo "run.sh: MISSING_TOOL: klt not on PATH" >&2; exit 1; }

python3 -I "$here/gen_request.py"
backend="${KLT_SIM_BACKEND:-batch}"
set +e
klt sim "$here/sweep_request.json" --backend "$backend" -o "$build/out" \
  --report-out "$build/report.json" --format json >"$build/stdout.json" 2>"$build/stderr.log"
rc=$?
set -e
# klt exits 0 (all pass) / 3 (graded failures) / 4 (errors); 1 is a request or
# submit failure. Our graded quantities come from extract.py, not klt's grading.
if [[ ! -s "$build/report.json" ]]; then
  echo "run.sh: klt sim produced no report (exit $rc, backend $backend):" >&2
  tail -20 "$build/stderr.log" >&2
  exit 1
fi
exec python3 -I "$here/extract.py" --report "$build/report.json" \
  --request "$here/sweep_request.json" --out-dir "$here/records" "$@"
