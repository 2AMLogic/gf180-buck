#!/usr/bin/env bash
# sim/env.sh -- source me: resolve the gf180mcu PDK, verify it is the revision
# pinned in sim/pdk.json, and print the resolved paths.
#
#   source sim/env.sh
#
# Resolution is delegated to sim/lib/pdk_env.sh (adopted from 2AMLogic/gf180-sram,
# pinned in reuse.lock.json). The revision check is this repo's own: the
# resolved install must match pdk.json's revision AND its model files must
# match the pinned sha256. On mismatch it prints "env.sh: PDK_MISMATCH: ..."
# on stderr and returns non-zero.
#
# Test hook: PDK_PIN_FILE=<path> reads a different pdk.json.

_buck_env_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_buck_env_pin="${PDK_PIN_FILE:-$_buck_env_dir/pdk.json}"

_buck_env_fail() { echo "env.sh: $*" >&2; unset -f _buck_env_fail; return 1 2>/dev/null || exit 1; }

command -v jq >/dev/null 2>&1 || { _buck_env_fail "MISSING_TOOL: jq not found on PATH"; return 1 2>/dev/null || exit 1; }
[[ -f "$_buck_env_pin" ]] || { _buck_env_fail "NO_PIN_FILE: $_buck_env_pin not found"; return 1 2>/dev/null || exit 1; }

_buck_env_variant="$(jq -r .variant "$_buck_env_pin")"
_buck_env_rev="$(jq -r .revision "$_buck_env_pin")"
if [[ -n "${PDK:-}" && "$PDK" != "$_buck_env_variant" ]]; then
  _buck_env_fail "PDK_MISMATCH: PDK=$PDK but sim/pdk.json pins variant $_buck_env_variant"
  return 1 2>/dev/null || exit 1
fi
export PDK="$_buck_env_variant"

# shellcheck source=lib/pdk_env.sh
source "$_buck_env_dir/lib/pdk_env.sh" || { echo "env.sh: PDK_NOT_FOUND: see pdk_env.sh message above" >&2; return 1 2>/dev/null || exit 1; }

if [[ "$GF180_PDK_VERSION" != "$_buck_env_rev" ]]; then
  _buck_env_fail "PDK_MISMATCH: installed revision '${GF180_PDK_VERSION:-unknown}' (from $GF180_VARIANT_DIR) != pinned '$_buck_env_rev' (sim/pdk.json)"
  return 1 2>/dev/null || exit 1
fi

while IFS=$'\t' read -r _buck_env_rel _buck_env_want; do
  _buck_env_got="$(sha256sum "$GF180_VARIANT_DIR/$_buck_env_rel" | cut -d' ' -f1)"
  if [[ "$_buck_env_got" != "$_buck_env_want" ]]; then
    _buck_env_fail "PDK_MISMATCH: $_buck_env_rel sha256 $_buck_env_got != pinned $_buck_env_want"
    return 1 2>/dev/null || exit 1
  fi
done < <(jq -r '.model_files | to_entries[] | [.key, .value] | @tsv' "$_buck_env_pin")

export GF180_PDK_REVISION="$GF180_PDK_VERSION"
echo "env.sh: pdk=gf180mcu variant=$PDK revision=$GF180_PDK_REVISION"
echo "env.sh: GF180_VARIANT_DIR=$GF180_VARIANT_DIR"
echo "env.sh: GF180_MODEL_FILE=$GF180_MODEL_FILE"
echo "env.sh: GF180_DESIGN_INC=$GF180_DESIGN_INC"
unset -f _buck_env_fail
unset _buck_env_dir _buck_env_pin _buck_env_variant _buck_env_rev _buck_env_rel _buck_env_want _buck_env_got
