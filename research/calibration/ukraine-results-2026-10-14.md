# Ukrainian indicator tests, complete data (2026-10-14)

Research only; no score or weight changed (Ukraine stays on v3.5). Hit rate first, then the comparison rate and the likelihood ratio (LR, shrunk, buyer-resampled 95 % interval). A candidate *passes* when the learn half's LR interval is above 1 and the check half's LR is above 1 (rule fixed in [the candidate plan](ukraine-candidate-indicators-plan.md)).

## Label sets

| Set | Positive tenders in competitive procedures (buyers) | Comparisons | Files |
|---|---|---|---|
| Convictions quoting a tender ID | 178 (78) | 612 | `ukraine-verdict-sweep-*` |
| + verdicts linked by buyer, contract number, date ([plan](ukraine-verdict-linking-plan.md)) | 248 (141); one per court case 117 (109) | 874 | `ukraine-verdict-plus-linked-*` |
| AMCU bid rigging upheld in court | 2,714 (1,144); one per case 873 (556) | 8,675 | `ukraine-amcu-full-*`, `ukraine-amcu-one-per-case-*` |
| + 2 tenders linked by bidder codes | 2,716 (1,145) | 8,679 | `ukraine-amcu-plus-linked-*` (same results) |

Sensitivity check added after the first results (not in the plan): a cartel needs at least two bidders, so bid-rigging tenders almost never have a single offer (1 % vs 24 %). Bid-pattern checks can pass only because they need 2+ bids. Each set is therefore also compared among tenders with 2+ bids (`*-multibid*`).

## Current v3.5 checks

| Check (v3.5 points) | Convictions | + linked, one per case | Bid rigging | Bid rigging, 2+ bids, one per case |
|---|---|---|---|---|
| Single offer (3) | 24 % vs 31 %, LR 0.79 | 23 % vs 32 %, LR 0.75 | 1 % vs 24 % (structural) | n/a |
| Better bid disqualified (5) | 28 % vs 18 %, LR 1.46 [0.97, 2.12] | 31 % vs 20 %, LR 1.51 [1.08, 1.99] | 32 % vs 21 %, LR 1.53 [1.39, 1.69] | 34 % vs 28 %, LR 1.18 [1.04, 1.32] |
| 3+ amendments (6 / 11) | 26 % vs 15 %, LR 1.66 [1.04, 2.60] | 28 % vs 13 %, LR 2.05 [1.43, 2.92] | 20 % vs 16 %, LR 1.29 [1.14, 1.45] | 22 % vs 18 %, LR 1.24 [1.05, 1.44] |

## Candidates that pass in the strictest bid-rigging test (one per case, 2+ bids)

| Candidate | Bid rigging, strict | Convictions | + linked, one per case | + linked, 2+ bids |
|---|---|---|---|---|
| C12 term-extension amendment | 26 % vs 17 %, LR 1.52, passes | 29 % vs 15 %, LR 1.81, passes | 32 % vs 11 %, LR 2.61, passes | 35 % vs 13 %, LR 2.42, passes |
| C3 2+ better-ranked bidders disqualified | 16 % vs 8 %, LR 2.07, passes | 9 % vs 6 %, fails | 13 % vs 5 %, LR 2.44, passes | 16 % vs 7 %, LR 2.19, fails (learn half 0.97) |
| C9 small price drop | 48 % vs 32 %, LR 1.49, passes | 49 % vs 38 %, fails | 55 % vs 39 %, fails (learn half 0.93) | 46 % vs 28 %, LR 1.57, passes |
| C14 early termination | 22 % vs 14 %, LR 1.57, passes | fails | — | — |
| K7 all bids ≥ 97 % of expected value | 41 % vs 28 %, LR 1.48, passes | fails | fails | — |
| K5 tight bids (CV < 3 %) | 14 % vs 11 %, LR 1.33, passes | fails | fails | — |
| K3 shared document | 10 % vs 4 %, LR 2.11, passes (AMCU evidence: upper bound) | fails | — | — |
| K1 shared phone or e-mail | 8 % vs 1 %, LR 12.0, passes (AMCU evidence: upper bound) | fails | — | — |

Fail in the strict test: K2 shared address (2 %, too few buyers), K4 bids within 10 minutes and K6 close runner-up (pass only without the 2+ bid restriction), K8 thin cover bid, C5 complaint (also circular), C1, C2, C4, C6, C7, C8, C10, C11, C13, C15.

Only C12 (term extension) passes in every set. C3 and C9 pass in both sources under some but not all variants.

## Points adopted (owner, 2026-10-14)

The owner asked to add term extension (separately or as extra points on amendments), keep 3+ and 5+ amendments as separate bands, lower single offer and better bid disqualified, and set points from these results, Ukraine only. Amendment bands and the term-extension bonus within amended contracts: `tools/ukraine-execution-points.py`, tables `ukraine-*-execution-points*.md`. Points follow convictions, one per case; the other sets check direction.

| Check | Convictions, one per case | Tender IDs only | Bid rigging, 2+ offers, one per case | Adopted |
|---|---|---|---|---|
| Single offer | 0 | 0 | not comparable | 1 (owner) |
| Better bid disqualified | 5.9 | 5.4 | 2.4 | 4 |
| 3–4 amendments | 9.5 | 3.3 | 4.8 | 6 |
| 5+ amendments | 10.6 | 10.3 | 1.2 | 10 |
| Term extension, 0–2 amendments | 6.0 | 0.4 | 5.5 | 4 |
| Term extension within 3+ amendments (bonus) | 7.9 | 4.5 | 3.2 | +6 |

Bundled cohort: 48 → 50 contracts with a positive score.

The *Current points* column of the `ukraine-verdict-sweep`, `ukraine-verdict-plus-linked` and `ukraine-amcu-full` points tables shows the adopted points; other tables were generated before adoption and show the earlier 3.5 points (3 / 5 / 6–11). Evidence columns are unaffected.
