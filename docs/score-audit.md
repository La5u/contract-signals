# Local scoring audit corrections

These are correctness fixes to the v3.3 engine, not new weights, new legal verification, or calibration against contract outcomes. No deployment is implied.

## Corrections

- Correct the odd/even leave-one-out publication-delay median. Regression fixtures cover nonuniform observations, both parities, duplicates, each removal position, and a threshold crossing.
- Require a real, complete ISO calendar date before selecting a French direct-award threshold. Invalid months, days, leap days and trailing text remain unknown, not scored.
- Consider every encoded legal regime intersecting the 180-day possible-consultation window. Two works-threshold changes in 2020 can overlap; checking only the immediately preceding regime incorrectly cleared some uncertain awards. The 180-day window remains an editorial uncertainty guard, not proof of the actual consultation date.

## Impact on bundled records

Baseline: commit `5f94c8e75dfe309caa763b75a8db873389304df5` (unchanged v3.3 scoring from `1fdac98`). Same input files are independently prepared by both engines. The report records SHA-256 hashes of both engines and every input: [score-audit-impact.json](../data/score-audit-impact.json).

Across **18,501 prepared rows in 14 datasets**, **21 scores increase**, two rows gain a late-publication signal, and no signals are removed. Positive-score totals change only in Portugal TED; zero and unknown scores remain distinct. The French date/transition fixes do not change these bundled records.

| Dataset | Changed scores | Newly added signals | Positive before → after | Zero before → after | Unknown before → after | Changed positive ranks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BOAMP | 17 | 1 | 432 → 432 | 2,566 → 2,566 | 12 → 12 | 197 |
| Portugal TED | 4 | 1 | 137 → 138 | 356 → 355 | 0 → 0 | 1 |
| Other 12 datasets | 0 | 0 | unchanged | unchanged | unchanged | 0 |

- BOAMP `boamp-25-30125-lot-0000`: **12 → 20**, positive rank **190 → 20**, gaining late publication. It replaces `boamp-25-31158-lot-0001` in the top 20 (unchanged score 18.3, rank 20 → 21).
- Portugal TED `ted-226852-2025-lot-0006`: **0 → 8**, gaining late publication, new positive rank 138; the top 20 is unchanged.
- The other 19 changes are increases of 0.1–0.2 points. All top-20 lists except BOAMP retain their membership and order.

Ranks use the actual engine's `selectContracts(..., {sort: 'score'})`, including its tie-breaks, with zero/null excluded. The **198 changed ranks include displacement effects**, not 198 changed scores. This is a revision-impact comparison, not an assessment of whether any contract is irregular.

## Documentation reconciliation

Country and shared docs now distinguish statutory rules, provisional legal references, exploratory single-bid associations, and editorial weights. The duration maximum is 16 in France and Colombia by owner decision, not empirical calibration; the DECP 240-day excess is not a legal deadline. Paraguay's 20% reference remains provisional pending review of the complete legal text and exceptions. Historical release counts are labelled as history. The review generator now reads the engine's score version rather than labelling v3.3 output as v3.2.

## Reproduction and checks

```sh
git show 5f94c8e:script.js > /tmp/contract-signals-before-audit.js
node tools/compare-score-revisions.cjs /tmp/contract-signals-before-audit.js data/score-audit-impact.json
node tools/review-score-v3.cjs
sh tests/run-all.sh
```

The browser suite requires Playwright (test-only) and Chromium; see `tests/browser.cjs` for dependency paths. Non-browser JS suites and 225 Python tests pass (11 skipped for optional dependencies). Browser HTTP, file-picker, filters, record panels, review notes, theme and mobile checks pass using isolated headless Chromium. Comparison-tool tests cover identical engines and deliberately changed scores/signals/top-20 displacement. Source cohorts are unchanged. No push or deployment performed.
