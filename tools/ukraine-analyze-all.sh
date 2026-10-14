#!/bin/sh
# Run every indicator test on one cohort.
# usage: tools/ukraine-analyze-all.sh NAME COHORT CHANGES [POSITIVE_LABELS]
# Writes research/calibration/ukraine-NAME-{results.txt,points.md,points.json,candidate-indicators.txt,candidate-indicators.json}.
set -e
cd "$(dirname "$0")/.."
name=$1 cohort=$2 changes=$3 labels=$4
out=research/calibration/ukraine-$name
rows=research/labels/ukraine-$name-rows.json
opt=; [ -n "$labels" ] && opt="--positive-labels $labels"
node tools/analyze-ukraine-verdict-cohort.cjs "$cohort" "$rows" > "$out-results.txt"
python3 tools/propose-indicator-points.py "$rows" --changes "$changes" --json "$out-points.json" $opt > "$out-points.md"
python3 tools/ukraine-candidate-indicators.py --cohort "$cohort" --features research/labels/ukraine-$name-candidate-features.json \
  --json "$out-candidate-indicators.json" $opt > "$out-candidate-indicators.txt"
if [ -z "$labels" ]; then
  python3 tools/ukraine-points-robustness.py "$rows" --changes "$changes" --json "$out-robustness.json" > "$out-robustness.txt"
fi
echo "== $name done"
