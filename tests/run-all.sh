#!/bin/sh
# Every suite in one command: each tests/*.cjs, then the Python tests, then the suites that start
# Chromium (BROWSER below); skip those with NO_BROWSER=1.
set -e
cd "$(dirname "$0")/.."
BROWSER="browser korea-global"
for f in tests/*.cjs; do
  t=$(basename "$f" .cjs)
  case " $BROWSER " in *" $t "*) continue ;; esac
  node "$f"
done
python -m unittest discover -s tests -p 'test_*.py'
[ -n "$NO_BROWSER" ] || for t in $BROWSER; do node "tests/$t.cjs"; done
