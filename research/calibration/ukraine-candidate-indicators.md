# Ukrainian candidate indicators: results (2026-10-13)

Research only; no score changed. Fixed list and decision rule: [plan](ukraine-candidate-indicators-plan.md), written before the first run. Code: `tools/ukraine-candidate-indicators.py` (cache only, no requests). Per-row statuses: `research/labels/ukraine-candidate-features.json`; full numbers: [ukraine-candidate-indicators.json](ukraine-candidate-indicators.json).

Same cohort and method as the [v3.5 points](ukraine-verdict-sweep-points.md): 170 convicted competitive tenders (71 buyers) against 577 same-buyer comparisons, buyer-weighted, LR shrunk toward 1, 10 points per doubling. Learn half 63 positives / 36 buyers; check half 107 / 35.

## Result

**One candidate passes: C12, a term-extension amendment** (durationExtension or fiscalYearExtension). It fires on 30 % of convicted tenders (48 % of contractor-only fraud, 18 % of corruption) against 15 % of comparisons. LR 1.89 [1.28, 2.83]; learn half 1.80 [1.17, 2.77]; check half 1.76. Points from all data: 9.2 [3.5, 15.0].

**But it mostly duplicates the existing amendment check.** 59 of the 134 rows with a term extension also have 3+ amendments. Among contracts with fewer than 3 amendments, a term extension gives LR 1.24 [0.55, 2.26], about 3 points with an interval reaching 0. Widening the amendment check to "3+ amendments or a term extension" gives LR 1.62 [1.13, 2.36], about 7 points, against 1.92 for 3+ amendments alone. Because scores take the family maximum, the extension would only change contracts with 1–2 amendments, where its evidence is weak.

Everything else fails the rule. Notable:
- **Small price drop (award ≥ 98 % of expected value)** has the second-highest hit rate (46 %) but only LR 1.20 [0.94, 1.52].
- **Two bidders, short tendering period, December award and an individual supplier** are all *less* common on convicted tenders, like the single offer.
- **Fast signature (C8)** never fires: Prozorro itself blocks signing before the standstill period ends.
- **Just below the open-tender threshold (C10)** fires on 2 positives only: splitting below thresholds is not what these convictions are about.

| Candidate | Hit rate, convicted | Corruption | Fraud | Comparisons | LR+ all [95 %] | LR+ learn half [95 %] | LR+ check half | Points (all) [95 %] | Decision |
|---|---|---|---|---|---|---|---|---|---|
| C9 small-price-drop | 46% (86/170) | 47% (71/131) | 46% (15/39) | 38% (248/571) | 1.20 [0.94, 1.52] | 1.08 [0.75, 1.49] | 1.27 [0.97, 1.70] | 2.6 [0.0, 6.1] | fails rule |
| C4 short-tender-period | 46% (67/170) | 49% (55/131) | 39% (12/39) | 51% (299/577) | 0.91 [0.70, 1.16] | 0.99 [0.73, 1.30] | 0.86 [0.63, 1.13] | 0.0 [0.0, 2.2] | fails rule |
| C1 two-bidders | 31% (80/170) | 33% (68/131) | 27% (12/39) | 38% (263/577) | 0.83 [0.59, 1.12] | 0.99 [0.66, 1.45] | 0.73 [0.49, 1.01] | 0.0 [0.0, 1.7] | fails rule |
| C12 term-extension-amendment | 30% (40/170) | 18% (23/131) | 48% (17/39) | 15% (94/577) | 1.89 [1.28, 2.83] | 1.80 [1.17, 2.77] | 1.76 [0.72, 3.90] | 9.2 [3.5, 15.0] | proposal |
| C15 individual-supplier | 20% (24/170) | 29% (22/131) | 7% (2/39) | 24% (111/576) | 0.86 [0.55, 1.29] | 0.97 [0.54, 1.62] | 0.78 [0.45, 1.22] | 0.0 [0.0, 3.7] | fails rule |
| C13 quantity-cut-amendment | 18% (21/170) | 20% (17/131) | 14% (4/39) | 13% (61/577) | 1.25 [0.72, 2.00] | 1.09 [0.54, 1.96] | 1.36 [0.63, 2.63] | 3.2 [0.0, 10.0] | fails rule |
| C7 december-award | 16% (25/170) | 24% (24/131) | 4% (1/39) | 21% (146/577) | 0.80 [0.48, 1.22] | 0.74 [0.37, 1.30] | 0.89 [0.48, 1.47] | 0.0 [0.0, 2.9] | fails rule |
| C5 complaint | 15% (21/170) | 10% (13/131) | 23% (8/39) | 13% (48/577) | 1.09 [0.55, 1.91] | 1.33 [0.66, 2.96] | 0.78 [0.30, 1.63] | 1.3 [0.0, 9.3] | fails rule |
| C6 late-document-change | 14% (17/170) | 14% (10/131) | 14% (7/39) | 10% (55/577) | 1.36 [0.77, 2.36] | 1.50 [0.81, 2.84] | 0.91 [0.23, 2.10] | 4.4 [0.0, 12.4] | fails rule |
| C14 early-termination | 14% (69/170) | 13% (62/131) | 13% (7/39) | 15% (126/574) | 0.91 [0.51, 1.46] | 0.86 [0.40, 1.65] | 0.95 [0.48, 1.58] | 0.0 [0.0, 5.4] | fails rule |
| C2 only-qualified-bidder | 13% (20/170) | 13% (12/131) | 12% (8/39) | 11% (54/577) | 1.11 [0.57, 1.94] | 1.27 [0.57, 2.37] | 0.84 [0.33, 1.69] | 1.6 [0.0, 9.5] | fails rule |
| C11 price-change-amendment | 10% (20/170) | 14% (19/131) | 4% (1/39) | 9% (39/577) | 1.13 [0.55, 2.12] | 0.67 [0.23, 1.56] | 1.60 [0.66, 3.46] | 1.7 [0.0, 10.8] | fails rule |
| C3 two-plus-disqualified | 10% (13/170) | 10% (8/131) | 10% (5/39) | 6% (24/577) | 1.51 [0.61, 3.36] | 1.50 [0.50, 4.24] | 1.20 [0.29, 2.77] | 6.0 [0.0, 17.5] | fails rule |
| C10 just-below-threshold | 2% (2/170) | 1% (1/131) | 4% (1/39) | 3% (16/577) | 0.59 [0.12, 1.68] | 0.64 [0.20, 2.02] | 0.49 [0.21, 1.45] | 0.0 [0.0, 7.5] | fails rule |
| C8 fast-signature | 0% (0/161) | 0% (0/126) | 0% (0/35) | 0% (0/548) | 0.13 [0.12, 0.14] | 0.23 [0.20, 0.27] | 0.22 [0.20, 0.25] | 0.0 [0.0, 0.0] | fails rule |

## Corrections

A code review after the first run found nine implementation errors (listed in the plan). The decision did not change. The largest effect: C6 counted documents dated after the deadline, which gave it 133/170 positives and 391/577 comparisons instead of 17 and 55.

## Limits

Convictions over-represent what gets prosecuted. Comparisons are unlabelled, not proven clean. Fifteen candidates were tested; the check half guards against one passing by chance, but it is small (35 buyers). C4 cut-offs use comparisons from both halves.

## Part 2: direct contracts against a census (2026-10-13)

`tools/ukraine-direct-contract-census.py` listed every completed tender of the 102 buyer-years with an eligible convicted tender (placeholder buyer code 00000000 left out): 9,176 competitive, 21,431 direct-contract reports and 679 negotiated procedures, all listings complete (2,250 requests). Convicted tenders here include direct contracts (208 positives).

| Candidate | Hit rate, convicted | Comparisons (census) | LR+ all [95 %] | Learn half | Check half | Decision |
| --- | ---: | ---: | --- | --- | --- | --- |
| D1 direct contract, any value | 21 % | 74 % | 0.35 [0.26, 0.46] | 0.47 | 0.35 | fails |
| D2 direct contract ≥ UAH 200,000 | 14 % | 9 % | 1.34 [0.76, 2.09] | 1.40 | 1.07 | fails |
| D3 direct contract ≥ UAH 1.5 million | 6 % | 2 % | 2.46 [0.84, 4.68] | 2.44 | 1.44 | fails |

Direct contracting as such is far *less* common on convicted tenders: most direct contracts are small purchases nobody prosecutes. Large direct contracts lean the other way (D3 is 2.5 times as frequent), which supports the existing editorial choice to leave reporting procedures unscored but suggests a size-gated check is worth retesting when more convictions arrive. The negotiated-procedure check (`ua-direct-award`) cannot be measured: only 4 convicted tenders used one.

### Repeat on the conviction cohort with linked tenders (2026-10-14)

Pre-registered addition in the [plan](ukraine-candidate-indicators-plan.md#part-2-direct-contracts-fixed-2026-10-13-before-any-listing-was-downloaded): same census on `ukraine-verdict-plus-linked-cohort.json.gz` (203 buyer-years, 12,217 competitive, 45,058 direct-contract reports, 1,315 negotiated procedures; all listings complete, 2,131 new requests), plus D4, the scored `ua-direct-award` rule. Results: [`ukraine-direct-contract-census-plus-linked-results.json`](ukraine-direct-contract-census-plus-linked-results.json); census `research/labels/ukraine-direct-contract-census-plus-linked.json.gz`. The census was drawn from the cohort as it stood before the two tenders that became final on 14 October were added.

| Candidate | Hit rate, convicted | Comparisons (census) | LR+ all [95 %] | Learn half [95 %] | Check half | Points (all) [95 %] | Decision |
| --- | ---: | ---: | --- | --- | --- | --- | --- |
| D1 direct contract, any value | 26 % (72/320) | 80 % | 0.35 [0.29, 0.43] | 0.40 [0.31, 0.51] | 0.38 | 0 | fails |
| D2 direct contract ≥ UAH 200,000 | 17 % (39/320) | 8 % | 2.18 [1.52, 3.00] | 1.76 [1.06, 2.82] | 2.43 | 11.2 [6.0, 15.8] | **passes** |
| D3 direct contract ≥ UAH 1.5 million | 5 % (12/320) | 1 % | 2.79 [1.24, 4.82] | 2.39 [0.62, 4.87] | 2.33 | 14.8 [3.1, 22.7] | fails (learn interval) |
| D4 negotiated procedure (`ua-direct-award`) | 8 % (15/320) | 4 % | 1.94 [1.05, 3.13] | 1.27 [0.35, 2.74] | 2.29 | 9.6 [0.8, 16.5] | fails (learn interval) |

With the linked convictions, a direct contract of at least UAH 200,000 (the open-tender threshold for goods and services) passes the holdout rule: it is twice as frequent on convicted tenders as among the same buyers' other completed tenders. D4 is the first measurement of `ua-direct-award`: the direction supports the check, but its indicated points (about 10, interval 1–17) are below the editorial 18 and the learn half does not exclude 1. Fifteen convicted negotiated tenders are still few. **Nothing adopted**; both are for the owner to decide. Caveats: listings are the site search's completed tenders only, and the size gate may still partly measure size (prosecutions favour large amounts).
