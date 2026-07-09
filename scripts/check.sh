#!/usr/bin/env bash
# Run every invariant this repo depends on. Exit non-zero if any fails.
#
#   ./scripts/check.sh [reference.md]
#
# Without an argument, the current docs/ tree is checked against itself (parse ->
# render). Pass the published document to also prove docs/ still reconstructs it.
set -uo pipefail
cd "$(dirname "$0")"

fail=0
run() { echo "--- $1"; shift; "$@" || fail=1; }

run "parse: docs/dex -> data/dex.json"        python3 parse_dex.py
run "render: data/dex.json == docs/dex"       python3 render_dex.py --check
run "publish guards (census, no network)"     python3 publish.py --dry-run

if [ $# -ge 1 ]; then
  run "round-trip: concat(docs) == $1"        python3 verify_roundtrip.py "$1"
fi

echo
if [ $fail -eq 0 ]; then echo "ALL CHECKS PASSED"; else echo "CHECKS FAILED"; fi
exit $fail
