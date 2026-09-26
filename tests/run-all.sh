#!/bin/sh
# Every suite in one command. Browser test last; skip it with NO_BROWSER=1.
set -e
cd "$(dirname "$0")/.."
for t in scoring-v3 score-review rules cities tours colombia paraguay national outcomes page-copy view-export; do
  node "tests/$t.cjs"
done
python -m unittest discover -s tests -p 'test_*.py'
[ -n "$NO_BROWSER" ] || node tests/browser.cjs
