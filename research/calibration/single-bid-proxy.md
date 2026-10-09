# Single bidding as a stand-in outcome (2026-10-09)

Research only. No score, weight or dataset changed.

## Question

Other platforms (Government Transparency Institute / Opentender / ProACT) keep a red flag only if it predicts single bidding, holding market, sector and buyer constant. Can the bundled cohorts calibrate our non-competition checks the same way?

## Method

`node tools/single-bid-proxy.cjs .` runs the live engine (`script.js`) on each bundled cohort. The outcome is the cohort's single-offer check (signal vs clear). Each other check that is evaluated (signal vs clear) on the same row gives a 2×2 table and an odds ratio with a 0.5 continuity correction and a 95 % Wald interval. Checks built on single bidding (repeated single offer, single tenderer, better bid disqualified) are excluded as circular. Rows where either check is unknown or out of scope are left out. No controls for buyer, sector or year.

## Results

| Cohort | Check | Flag & single / flag & several | OR [95 % CI] |
| --- | --- | --- | --- |
| BOAMP | late publication | 15 / 42 | 1.42 [0.78, 2.58] |
| BOAMP | long duration | 0 / 5 | 0.30 [0.02, 5.42] |
| Paris & Ardèche DECP | late publication | 1 / 17 | 0.61 [0.11, 3.28] |
| Paris & Ardèche DECP | amount increase | 1 / 4 | 0.90 [0.10, 8.31] |
| Six cities DECP | late publication | 1 / 15 | 0.50 [0.09, 2.73] |
| TED Czechia | late publication | 2 / 27 | **0.25 [0.07, 0.95]** |
| TED Czechia | concentration | 1 / 30 | **0.15 [0.03, 0.82]** |
| TED Portugal | late publication | 1 / 3 | 2.16 [0.31, 14.88] |
| TED Romania | late publication | 3 / 22 | **0.23 [0.07, 0.71]** |
| Paraguay 3 buyers | amount increase | 2 / 5 | 1.17 [0.25, 5.41] |

Direct award never co-occurs with a known single offer (the single-offer check needs a competitive procedure), and most other checks fire too rarely on rows with a known offer count to estimate anything.

## Reading

- **The bundled cohorts are too small for this method.** Only late publication has enough flags, and every interval for it either spans 1 or lies below 1.
- Where the result is clear, **late publication is associated with *less* single bidding** (Czechia, Romania). This does not support giving it more points; it is consistent with the 8–16 point ceiling being, if anything, too high as a competition-risk proxy. Single bidding measures restricted competition, not late reporting, so a low ratio does not by itself prove the check useless.
- The Czech concentration result is likely mechanical: concentration needs a dominant holder across ≥10 contracts with known holders, which favours markets where several firms bid.
- Using the 0/1 flag throws away the continuous values (days of delay, months of duration, percentage increase). The earlier national DECP analysis (`research/thresholds/france-national.md`) used continuous values on a much larger file and found that single-bid odds fall with duration.

## Next steps, not done

1. Rerun on the large national files (full DECP; full TED for Portugal, Romania and Czechia) with continuous values and buyer/CPV/year controls (conditional logistic regression). Heavier on CPU and disk.
2. Validate against real labels (Ukrainian court judgments that cite a tender ID), as proposed on 2026-10-09.
