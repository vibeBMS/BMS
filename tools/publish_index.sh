#!/bin/bash
# Write each event's index.json (tools/index.py) into its release and into
# this repository as <event>/index.json, then commit those files. Players
# read the repository's copy: raw.githubusercontent.com serves it to web
# pages (CORS), release downloads are not.
#
#     tools/publish_index.sh bof22 bof21 ...
set -euo pipefail
cd "$(dirname "$0")/.."
for ev in "$@"; do
  python3 tools/label.py "$ev"
  python3 tools/index.py "$ev" > "$ev/index.json"
  gh release upload "$ev" "$ev/index.json" --clobber
done
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -- "${@/%//index.json}"
git diff --cached --quiet && exit 0
git commit -q -m "index.json: $*"
# another run may have pushed the same event's files meanwhile (two lists
# of events with one in common): this run's, the newer, win
for i in 1 2 3 4 5; do
  if git pull -q --rebase -X theirs origin main; then
    git push -q origin HEAD:main && exit 0
  else
    git rebase --abort 2>/dev/null || true
  fi
  sleep $((i * 5))
done
exit 1
