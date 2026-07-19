#!/bin/sh
# F-S12-2 permanent guard — fail LOUD, never strip silently.
# Usable as pre-commit hook (.git/hooks/pre-commit -> ../../scripts/check_repo_hygiene.sh) and in CI.
# Origin: public/public + doctype self-symlinks were swept in by blanket `git add` commits
# (696b5c4 2026-02-20, 5179be4 2026-04-12) and hidden for months by bake-side strip
# workarounds. This check makes recurrence a hard stop at the earliest gate.
set -u
fail=0

# 1. No committed symlinks, period. (The app has zero legitimate ones; any symlink
#    is either a self-alias — projects duplicate trees, dual import paths — or an
#    absolute link that encodes one substrate's bench root.)
links=$(git ls-files -s | awk '$1 == 120000 {print $4}')
if [ -n "$links" ]; then
    echo "HYGIENE FAIL: committed symlink(s) — remove at source, do NOT strip in bakes:"
    echo "$links" | sed 's/^/  /'
    fail=1
fi

# 2. Module Def casing: modules.txt must be exactly the canonical single entry.
if [ "$(cat amb_w_tds/modules.txt)" != "Amb W Tds" ]; then
    echo "HYGIENE FAIL: amb_w_tds/modules.txt must contain exactly 'Amb W Tds'"
    fail=1
fi

# 3. No non-canonical module casing in tracked json/py ("AMB_W_TDS" / "module": "amb_w_tds").
bad=$(git grep -l -E '"module": *"(AMB_W_TDS|amb_w_tds)"' -- '*.json' 2>/dev/null)
if [ -n "$bad" ]; then
    echo "HYGIENE FAIL: non-canonical module casing (canonical: \"Amb W Tds\") in:"
    echo "$bad" | sed 's/^/  /'
    fail=1
fi

[ $fail -eq 0 ] && echo "repo hygiene OK (0 symlinks, module casing canonical)"
exit $fail
