#!/usr/bin/env bash
# Ideal-switch buck bench: one local ngspice process (a single unit), then
# sim/lib/buckmeas.py, then a new append-only JSON record under
# sim/buck-ideal/records/. PDK-free: does not source sim/env.sh.
# Usage: sim/buck-ideal/run.sh
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
for tool in ngspice jq sha256sum python3 git; do
  command -v "$tool" >/dev/null || { echo "run.sh: MISSING_TOOL: $tool not on PATH" >&2; exit 1; }
done

build="$root/sim/build/buck-ideal"; mkdir -p "$build" "$here/records"
params="$here/params.json"
jq -r 'to_entries[] | select(.value|type=="number") | ".param \(.key)=\(.value)"' "$params" \
  > "$build/params.inc"
sed -e "/@PARAMS_INC@/{r $build/params.inc" -e "d}" \
    -e "s|@WRDATA@|$build/wrdata.dat|" \
  "$here/buck.spice" > "$build/buck.run.spice"

deck_sha="$(sha256sum "$here/buck.spice" | cut -d' ' -f1)"
params_sha="$(sha256sum "$params" | cut -d' ' -f1)"
ngspice_ver="$(ngspice --version | grep -m1 -o 'ngspice-[0-9][0-9.]*')"
cmd="ngspice -b -o sim/build/buck-ideal/ngspice.log sim/build/buck-ideal/buck.run.spice"
(cd "$root" && $cmd)
[[ -s "$build/wrdata.dat" ]] || { echo "run.sh: FAIL: ngspice wrote no wrdata" >&2; exit 1; }

sha="$(git -C "$root" rev-parse --short=12 HEAD)"
ts="$(date -u +%Y%m%dT%H%M%SZ)"
rec="$here/records/$ts-$sha.json"
[[ ! -e "$rec" ]] || { echo "run.sh: records are append-only; $rec exists" >&2; exit 1; }

# Exit 2 from the module means "not settled": still record it, then fail.
rc=0
python3 -I "$root/sim/lib/buckmeas.py" "$build/wrdata.dat" --params "$params" \
  --out "$build/analysis.json" || rc=$?
[[ $rc -eq 0 || $rc -eq 2 ]] || { echo "run.sh: FAIL: buckmeas exit $rc" >&2; exit 1; }

jq --arg ver "$ngspice_ver" --arg deck "$deck_sha" --arg psha "$params_sha" \
   --arg sha "$sha" --arg ts "$ts" --arg cmd "$cmd" \
  '{record: "simulated, not measured; open-loop ideal-switch bench, no claim against a spec row",
    environment: {simulator: $ver, deck: "sim/buck-ideal/buck.spice", deck_sha256: $deck,
                  params: "sim/buck-ideal/params.json", params_sha256: $psha,
                  repo_commit: $sha, utc: $ts, command: $cmd},
    settled: .settle.settled,
    run_stop_time_s: .run.t_last_s,
    result: .}' "$build/analysis.json" > "$rec"
echo "run.sh: record $rec"
[[ $rc -eq 0 ]] || { echo "run.sh: FAIL: run did not settle (§0.4)" >&2; exit 1; }
echo "run.sh: OK"
