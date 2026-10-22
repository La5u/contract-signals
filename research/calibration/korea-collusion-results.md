# South Korea: checks against KONEPS tenders found rigged by the Fair Trade Commission — first results (2026-10-20, preparation run)

Plan and amendments: [korea-labels-plan.md](korea-labels-plan.md). Research only: no score, weight or dataset change without the owner.
Scripts: `tools/extract-korea-kftc-tenders.py` (tender tables read from decision images), `tools/match-korea-kftc-tenders.py`
(links to KONEPS notices), `tools/check-korea-kftc-finality.py` (court outcomes), `tools/korea-label-checks.py` (this table).

**Status: preparation, not a decision.** Decision rule as amended 2026-10-20 (owner: fewer, more lenient safeguards): all linked tenders, points from the LR we are 75 % sure of; see the plan. Collusion family only (court convictions not linked yet).
Finality: law.go.kr publishes 100 court rulings on KFTC bid-rigging
orders, and only 2 of them cite one of the 124 cases with linked tenders (both upheld). The other cases count as "no challenge
found", weight 1.

**Rerun 2026-10-22:** contracts whose original version (ord 0) is not in the data are no longer labels, comparisons or part of any total (their signing year and original amount are an amendment's); 3 linked notices drop out (721 with a contract; two have no original anywhere in the data), and comparisons fall from 432,515 to 409,522 (mostly contracts signed before the scan window, whose in-window changes had been taken for originals). Decision-rule points moved by at most 0.6 (G3 7.6 → 8.2, K5 3.5 → 3.7).
**Bid-level checks, 2026-10-22:** B1-B7 as fixed in the plan ("Bid-level checks"), from the KONEPS bid-opening results (`tools/fetch-korea-bid-results.py bids`, label days plus 24 sampled days per label year, 2010-2026; `tools/korea-bid-features.py`: 5,424 day files, 1,461,145 openings). A contract's B checks are unknown when its notice's opening is not in those days, so they are rated on 294 labelled tenders and 38,809 comparisons (buyer = contracting office). All other rows are unchanged. Under the decision rule B2 two or three bids earns 14.8 points, B5 large first gap 12.1 and B4 low bid dispersion 4.5; B1, B3, B6 and B7 earn none (B1 and B3 are rarer among rigged tenders than among comparisons; a cartel needs at least two bidders, so B1 cannot work on these labels, and G1 single offer stays uncomputed). The demanding-body sensitivity agrees (13.5, 12.0, 4.0). Size does not explain them: size-standardised, rigged values / 1.3, B2 16.2, B5 13.2, B4 4.7 ([korea-buyer-share-size-results.md](korea-buyer-share-size-results.md)); points use the lower, decision-rule values.


Labels: 1,218 KFTC bid-rigging decisions → 12,534 tenders read → 6,480 public tenders → 1,087 linked to one KONEPS notice
(416 by winner + amount, 269 by notice number, 249 by amount + buyer, 153 by winner + buyer + name; 109 ambiguous,
5,284 unmatched, mostly buyers outside KONEPS: DAPA, KEPCO, the Korea Expressway Corporation, KORAIL) → 740 notices in 106 cases.

## Buyer = contracting office (plan)

    740 linked notices in 106 cases; 721 with a contract in the data; 228 buyer-years (buyer_code); 432671 contracts
    finality: {'none': 699, 'upheld': 22} 

### weighted, one per case, all contracts (decision basis until 2026-10-20): 102 labelled (50 buyers), 409522 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 14% (8/102, 50 buyers) | 65% (180399/409522, 133 buyers) | 0.35 [0.23, 0.48] | 0.395 / 0.497 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 32% (18/102, 50 buyers) | 19% (514/409522, 133 buyers) | 1.551 [1.00, 2.37] | 1.43 / 1.488 | 6.3 [0.0, 12.4] | 4.2 points |
| G4 concentration | 15% (8/92, 41 buyers) | 16% (12570/409134, 105 buyers) | 0.949 [0.51, 1.47] | 0.966 / 0.909 | 0.0 [0.0, 5.5] | no points |
| G5 3+ changes | 7% (4/84, 41 buyers) | 3% (16401/385595, 133 buyers) | 1.861 [0.35, 3.91] | 1.589 / 1.598 | 9.0 [0.0, 19.7] | 2.6 points |
| G6 amount increase > 20 % | 7% (4/84, 41 buyers) | 3% (26557/385587, 133 buyers) | 1.621 [0.33, 3.28] | 0.507 / 2.304 | 7.0 [0.0, 17.2] | 0.6 points |
| N1 December signature | 12% (17/102, 50 buyers) | 10% (48275/409522, 133 buyers) | 1.204 [0.52, 1.97] | 1.402 / 0.836 | 2.7 [0.0, 9.7] | no points |
| N2 weekend signature | 1% (1/102, 50 buyers) | 1% (2460/409522, 133 buyers) | 0.948 [0.15, 3.22] | 0.27 / 1.467 | 0.0 [0.0, 16.9] | no points |
| N4 supplier dependence >= 25 % | 21% (12/102, 50 buyers) | 22% (4873/409522, 133 buyers) | 0.969 [0.59, 1.47] | 1.052 / 0.867 | 0.0 [0.0, 5.5] | no points |
| N5 first-time supplier | 38% (16/58, 31 buyers) | 49% (82443/296398, 97 buyers) | 0.818 [0.58, 1.08] | 0.927 / 0.752 | 0.0 [0.0, 1.2] | no points |
| U2 repeated private contract | 6% (3/102, 50 buyers) | 29% (96289/409522, 133 buyers) | 0.339 [0.17, 0.55] | 0.359 / 0.522 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/102, 50 buyers) | 0% (2167/409522, 133 buyers) | 0.167 [0.14, 0.20] | 0.27 / 0.303 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/102, 50 buyers) | 2% (18626/409522, 133 buyers) | 0.167 [0.14, 0.20] | 0.27 / 0.303 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/102, 50 buyers) | 0% (348/409522, 133 buyers) | 0.167 [0.14, 0.20] | 0.27 / 0.303 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 2% (1/102, 50 buyers) | 1% (2242/409522, 133 buyers) | 1.205 [0.15, 3.60] | 0.27 / 1.978 | 2.7 [0.0, 18.5] | no points |
| K5 restricted competition | 45% (45/102, 50 buyers) | 26% (137859/409522, 133 buyers) | 1.615 [1.17, 2.10] | 1.411 / 1.633 | 6.9 [2.3, 10.7] | 5.5 points |
| K6 award >= 95 % of reserve | 64% (49/73, 33 buyers) | 26% (175613/309409, 129 buyers) | 2.072 [1.57, 2.62] | 1.867 / 1.85 | 10.5 [6.5, 13.9] | 9.2 points |
| B1 single bid | 4% (1/51, 25 buyers) | 4% (11334/38809, 114 buyers) | 0.9 [0.24, 2.26] | 0.476 / 1.337 | 0.0 [0.0, 11.8] | no points |
| B2 two or three bids | 58% (37/51, 25 buyers) | 22% (10519/38809, 114 buyers) | 2.201 [1.57, 2.91] | 1.909 / 1.927 | 11.4 [6.5, 15.4] | 9.8 points |
| B3 just above the lower limit | 18% (11/49, 24 buyers) | 43% (8807/38647, 114 buyers) | 0.597 [0.38, 0.87] | 0.784 / 0.61 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 19% (3/15, 13 buyers) | 9% (1727/16642, 109 buyers) | 1.638 [0.50, 3.04] | 2.214 / 0.852 | 7.1 [0.0, 16.0] | 2.4 points |
| B5 large first gap | 31% (4/15, 13 buyers) | 10% (1903/16642, 109 buyers) | 2.132 [0.80, 3.99] | 1.703 / 1.829 | 10.9 [0.0, 20.0] | 6.8 points |
| B6 better bids disqualified | 0% (0/49, 24 buyers) | 2% (722/38569, 114 buyers) | 0.294 [0.23, 0.39] | 0.5 / 0.417 | 0.0 [0.0, 0.0] | no points |
| B7 same-minute bids | 14% (8/51, 25 buyers) | 5% (2115/38809, 114 buyers) | 2.163 [0.69, 4.33] | 1.272 / 2.303 | 11.1 [0.0, 21.1] | 6.1 points |

### weighted, all linked tenders, all contracts (decision rule, amendment 2026-10-20): 721 labelled (139 buyers), 409522 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 29% (102/721, 139 buyers) | 65% (180399/409522, 133 buyers) | 0.483 [0.39, 0.58] | 0.463 / 0.581 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 38% (84/721, 139 buyers) | 19% (514/409522, 133 buyers) | 1.901 [1.55, 2.43] | 2.036 / 1.6 | 9.3 [6.3, 12.8] | 8.2 points |
| G4 concentration | 32% (66/659, 99 buyers) | 16% (12570/409134, 105 buyers) | 1.854 [1.47, 2.41] | 1.721 / 1.796 | 8.9 [5.6, 12.7] | 7.7 points |
| G5 3+ changes | 3% (21/679, 130 buyers) | 3% (16401/385595, 133 buyers) | 0.865 [0.20, 1.72] | 0.631 / 0.954 | 0.0 [0.0, 7.8] | no points |
| G6 amount increase > 20 % | 2% (21/679, 130 buyers) | 3% (26557/385587, 133 buyers) | 0.674 [0.21, 1.38] | 0.581 / 0.721 | 0.0 [0.0, 4.6] | no points |
| N1 December signature | 9% (80/721, 139 buyers) | 10% (48275/409522, 133 buyers) | 0.899 [0.53, 1.32] | 1.055 / 0.655 | 0.0 [0.0, 4.0] | no points |
| N2 weekend signature | 0% (7/721, 139 buyers) | 1% (2460/409522, 133 buyers) | 0.205 [0.07, 0.59] | 0.116 / 0.369 | 0.0 [0.0, 0.0] | no points |
| N4 supplier dependence >= 25 % | 35% (85/721, 139 buyers) | 22% (4873/409522, 133 buyers) | 1.563 [1.34, 1.87] | 1.642 / 1.356 | 6.4 [4.2, 9.0] | 5.6 points |
| N5 first-time supplier | 48% (141/550, 101 buyers) | 49% (82443/296398, 97 buyers) | 0.965 [0.84, 1.09] | 1.024 / 0.881 | 0.0 [0.0, 1.3] | no points |
| U2 repeated private contract | 15% (60/721, 139 buyers) | 29% (96289/409522, 133 buyers) | 0.558 [0.40, 0.70] | 0.544 / 0.633 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/721, 139 buyers) | 0% (2167/409522, 133 buyers) | 0.067 [0.07, 0.07] | 0.116 / 0.137 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (7/721, 139 buyers) | 2% (18626/409522, 133 buyers) | 0.286 [0.07, 0.71] | 0.415 / 0.143 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/721, 139 buyers) | 0% (348/409522, 133 buyers) | 0.067 [0.07, 0.07] | 0.116 / 0.137 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 1% (1/721, 139 buyers) | 1% (2242/409522, 133 buyers) | 0.485 [0.07, 1.50] | 0.116 / 0.894 | 0.0 [0.0, 5.8] | no points |
| K5 restricted competition | 37% (279/721, 139 buyers) | 26% (137859/409522, 133 buyers) | 1.391 [1.14, 1.70] | 1.394 / 1.32 | 4.8 [1.8, 7.6] | 3.7 points |
| K6 award >= 95 % of reserve | 67% (391/641, 119 buyers) | 26% (175613/309409, 129 buyers) | 2.389 [1.98, 2.90] | 2.195 / 2.371 | 12.6 [9.9, 15.3] | 11.6 points |
| B1 single bid | 1% (6/294, 84 buyers) | 4% (11334/38809, 114 buyers) | 0.278 [0.10, 0.52] | 0.319 / 0.355 | 0.0 [0.0, 0.0] | no points |
| B2 two or three bids | 71% (151/294, 84 buyers) | 22% (10519/38809, 114 buyers) | 3.028 [2.44, 3.80] | 2.737 / 2.877 | 16.0 [12.9, 19.3] | 14.8 points |
| B3 just above the lower limit | 8% (30/289, 84 buyers) | 43% (8807/38647, 114 buyers) | 0.266 [0.17, 0.38] | 0.323 / 0.35 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 18% (22/111, 31 buyers) | 9% (1727/16642, 109 buyers) | 1.728 [0.77, 2.86] | 2.483 / 0.834 | 7.9 [0.0, 15.1] | 4.5 points |
| B5 large first gap | 34% (36/111, 31 buyers) | 10% (1903/16642, 109 buyers) | 2.765 [1.54, 4.46] | 1.619 / 3.298 | 14.7 [6.3, 21.6] | 12.1 points |
| B6 better bids disqualified | 1% (1/289, 84 buyers) | 2% (722/38569, 114 buyers) | 0.645 [0.10, 1.15] | 0.185 / 0.843 | 0.0 [0.0, 2.0] | no points |
| B7 same-minute bids | 4% (29/294, 84 buyers) | 5% (2115/38809, 114 buyers) | 0.753 [0.29, 1.39] | 0.649 / 0.838 | 0.0 [0.0, 4.8] | no points |

### weighted, one per case, competitive tenders with a notice: 79 labelled (39 buyers), 175433 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 0% (0/79, 39 buyers) | 0% (0/175433, 116 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 26% (12/79, 39 buyers) | 17% (307/175433, 116 buyers) | 1.4 [0.76, 2.23] | 1.236 / 1.443 | 4.9 [0.0, 11.6] | 2 points |
| G4 concentration | 16% (7/72, 33 buyers) | 16% (4049/175297, 102 buyers) | 0.981 [0.46, 1.58] | 1.103 / 0.769 | 0.0 [0.0, 6.6] | no points |
| G5 3+ changes | 6% (3/68, 35 buyers) | 8% (11679/160898, 116 buyers) | 0.816 [0.24, 1.66] | 0.909 / 0.777 | 0.0 [0.0, 7.3] | no points |
| G6 amount increase > 20 % | 5% (3/68, 35 buyers) | 6% (17005/160893, 116 buyers) | 0.835 [0.24, 1.82] | 0.475 / 1.181 | 0.0 [0.0, 8.7] | no points |
| N1 December signature | 14% (14/79, 39 buyers) | 11% (20551/175433, 116 buyers) | 1.171 [0.54, 1.90] | 1.265 / 0.944 | 2.3 [0.0, 9.3] | no points |
| N2 weekend signature | 1% (2/79, 39 buyers) | 0% (1242/175433, 116 buyers) | 1.836 [0.20, 5.50] | 0.312 / 2.112 | 8.8 [0.0, 24.6] | no points |
| N4 supplier dependence >= 25 % | 17% (8/79, 39 buyers) | 18% (1603/175433, 116 buyers) | 0.913 [0.48, 1.49] | 0.967 / 0.833 | 0.0 [0.0, 5.7] | no points |
| N5 first-time supplier | 28% (12/58, 27 buyers) | 50% (51986/168881, 80 buyers) | 0.686 [0.47, 0.92] | 0.82 / 0.648 | 0.0 [0.0, 0.0] | no points |
| U2 repeated private contract | 0% (0/79, 39 buyers) | 0% (0/175433, 116 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/79, 39 buyers) | 0% (0/175433, 116 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/79, 39 buyers) | 0% (0/175433, 116 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/79, 39 buyers) | 0% (0/175433, 116 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 0% (0/79, 39 buyers) | 0% (0/175433, 116 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| K5 restricted competition | 54% (37/79, 39 buyers) | 82% (111778/175433, 116 buyers) | 0.723 [0.58, 0.85] | 0.731 / 0.821 | 0.0 [0.0, 0.0] | no points |
| K6 award >= 95 % of reserve | 65% (41/60, 30 buyers) | 19% (30996/105033, 116 buyers) | 2.755 [2.01, 3.67] | 2.313 / 2.455 | 14.6 [10.1, 18.8] | 13.1 points |
| B1 single bid | 4% (1/54, 25 buyers) | 1% (678/21545, 105 buyers) | 2.067 [0.24, 4.96] | 0.435 / 2.706 | 10.5 [0.0, 23.1] | no points |
| B2 two or three bids | 64% (40/54, 25 buyers) | 21% (8465/21545, 105 buyers) | 2.41 [1.73, 3.20] | 2.333 / 1.83 | 12.7 [7.9, 16.8] | 11.1 points |
| B3 just above the lower limit | 23% (12/52, 24 buyers) | 46% (6215/21409, 104 buyers) | 0.641 [0.42, 0.91] | 0.698 / 0.744 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 18% (3/16, 13 buyers) | 7% (1242/12304, 99 buyers) | 1.727 [0.50, 3.19] | 2.275 / 0.803 | 7.9 [0.0, 16.7] | 2.9 points |
| B5 large first gap | 33% (5/16, 13 buyers) | 9% (1445/12304, 99 buyers) | 2.472 [0.97, 4.40] | 1.855 / 2.1 | 13.1 [0.0, 21.4] | 9 points |
| B6 better bids disqualified | 0% (0/52, 24 buyers) | 2% (718/21359, 104 buyers) | 0.294 [0.23, 0.39] | 0.455 / 0.455 | 0.0 [0.0, 0.0] | no points |
| B7 same-minute bids | 14% (8/54, 25 buyers) | 6% (1708/21545, 105 buyers) | 1.915 [0.61, 3.84] | 1.048 / 2.322 | 9.4 [0.0, 19.4] | 4.7 points |

### unweighted (court outcome ignored), one per case, all contracts: 102 labelled (50 buyers), 409522 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 14% (8/102, 50 buyers) | 65% (180399/409522, 133 buyers) | 0.35 [0.23, 0.48] | 0.395 / 0.497 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 32% (18/102, 50 buyers) | 19% (514/409522, 133 buyers) | 1.551 [1.00, 2.37] | 1.43 / 1.488 | 6.3 [0.0, 12.4] | 4.2 points |
| G4 concentration | 15% (8/92, 41 buyers) | 16% (12570/409134, 105 buyers) | 0.949 [0.51, 1.47] | 0.966 / 0.909 | 0.0 [0.0, 5.5] | no points |
| G5 3+ changes | 7% (4/84, 41 buyers) | 3% (16401/385595, 133 buyers) | 1.861 [0.35, 3.91] | 1.589 / 1.598 | 9.0 [0.0, 19.7] | 2.6 points |
| G6 amount increase > 20 % | 7% (4/84, 41 buyers) | 3% (26557/385587, 133 buyers) | 1.621 [0.33, 3.28] | 0.507 / 2.304 | 7.0 [0.0, 17.2] | 0.6 points |
| N1 December signature | 12% (17/102, 50 buyers) | 10% (48275/409522, 133 buyers) | 1.204 [0.52, 1.97] | 1.402 / 0.836 | 2.7 [0.0, 9.7] | no points |
| N2 weekend signature | 1% (1/102, 50 buyers) | 1% (2460/409522, 133 buyers) | 0.948 [0.15, 3.22] | 0.27 / 1.467 | 0.0 [0.0, 16.9] | no points |
| N4 supplier dependence >= 25 % | 21% (12/102, 50 buyers) | 22% (4873/409522, 133 buyers) | 0.969 [0.59, 1.47] | 1.052 / 0.867 | 0.0 [0.0, 5.5] | no points |
| N5 first-time supplier | 38% (16/58, 31 buyers) | 49% (82443/296398, 97 buyers) | 0.818 [0.58, 1.08] | 0.927 / 0.752 | 0.0 [0.0, 1.2] | no points |
| U2 repeated private contract | 6% (3/102, 50 buyers) | 29% (96289/409522, 133 buyers) | 0.339 [0.17, 0.55] | 0.359 / 0.522 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/102, 50 buyers) | 0% (2167/409522, 133 buyers) | 0.167 [0.14, 0.20] | 0.27 / 0.303 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/102, 50 buyers) | 2% (18626/409522, 133 buyers) | 0.167 [0.14, 0.20] | 0.27 / 0.303 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/102, 50 buyers) | 0% (348/409522, 133 buyers) | 0.167 [0.14, 0.20] | 0.27 / 0.303 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 2% (1/102, 50 buyers) | 1% (2242/409522, 133 buyers) | 1.205 [0.15, 3.60] | 0.27 / 1.978 | 2.7 [0.0, 18.5] | no points |
| K5 restricted competition | 45% (45/102, 50 buyers) | 26% (137859/409522, 133 buyers) | 1.615 [1.17, 2.10] | 1.411 / 1.633 | 6.9 [2.3, 10.7] | 5.5 points |
| K6 award >= 95 % of reserve | 64% (49/73, 33 buyers) | 26% (175613/309409, 129 buyers) | 2.072 [1.57, 2.62] | 1.867 / 1.85 | 10.5 [6.5, 13.9] | 9.2 points |
| B1 single bid | 4% (1/51, 25 buyers) | 4% (11334/38809, 114 buyers) | 0.9 [0.24, 2.26] | 0.476 / 1.337 | 0.0 [0.0, 11.8] | no points |
| B2 two or three bids | 58% (37/51, 25 buyers) | 22% (10519/38809, 114 buyers) | 2.201 [1.57, 2.91] | 1.909 / 1.927 | 11.4 [6.5, 15.4] | 9.8 points |
| B3 just above the lower limit | 18% (11/49, 24 buyers) | 43% (8807/38647, 114 buyers) | 0.597 [0.38, 0.87] | 0.784 / 0.61 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 19% (3/15, 13 buyers) | 9% (1727/16642, 109 buyers) | 1.638 [0.50, 3.04] | 2.214 / 0.852 | 7.1 [0.0, 16.0] | 2.4 points |
| B5 large first gap | 31% (4/15, 13 buyers) | 10% (1903/16642, 109 buyers) | 2.132 [0.80, 3.99] | 1.703 / 1.829 | 10.9 [0.0, 20.0] | 6.8 points |
| B6 better bids disqualified | 0% (0/49, 24 buyers) | 2% (722/38569, 114 buyers) | 0.294 [0.23, 0.39] | 0.5 / 0.417 | 0.0 [0.0, 0.0] | no points |
| B7 same-minute bids | 14% (8/51, 25 buyers) | 5% (2115/38809, 114 buyers) | 2.163 [0.69, 4.33] | 1.272 / 2.303 | 11.1 [0.0, 21.1] | 6.1 points |

## Buyer = demanding body (sensitivity)

    740 linked notices in 106 cases; 738 with a contract in the data; 416 buyer-years (demand_code); 207486 contracts
    finality: {'none': 716, 'upheld': 22} 

### weighted, one per case, all contracts (decision basis until 2026-10-20): 104 labelled (76 buyers), 204999 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 9% (8/104, 76 buyers) | 63% (113995/204999, 269 buyers) | 0.248 [0.16, 0.34] | 0.268 / 0.406 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 32% (28/104, 76 buyers) | 15% (1122/204999, 269 buyers) | 1.921 [1.32, 2.61] | 2.152 / 1.369 | 9.4 [4.0, 13.9] | 7.5 points |
| G4 concentration | 10% (8/90, 63 buyers) | 14% (21456/204161, 230 buyers) | 0.763 [0.35, 1.21] | 0.831 / 0.734 | 0.0 [0.0, 2.8] | no points |
| G5 3+ changes | 4% (4/85, 68 buyers) | 3% (15527/196856, 269 buyers) | 1.302 [0.22, 2.81] | 0.976 / 1.46 | 3.8 [0.0, 14.9] | no points |
| G6 amount increase > 20 % | 2% (4/85, 68 buyers) | 3% (22183/196848, 269 buyers) | 0.812 [0.13, 1.87] | 0.2 / 1.39 | 0.0 [0.0, 9.0] | no points |
| N1 December signature | 18% (18/104, 76 buyers) | 12% (23703/204999, 269 buyers) | 1.469 [0.88, 2.13] | 1.941 / 0.72 | 5.6 [0.0, 10.9] | 3.2 points |
| N2 weekend signature | 1% (1/104, 76 buyers) | 1% (1467/204999, 269 buyers) | 1.671 [0.10, 5.29] | 2.025 / 0.244 | 7.4 [0.0, 24.0] | no points |
| N4 supplier dependence >= 25 % | 16% (14/104, 76 buyers) | 15% (5596/204999, 269 buyers) | 0.996 [0.57, 1.53] | 1.237 / 0.714 | 0.0 [0.0, 6.1] | no points |
| N5 first-time supplier | 47% (25/54, 45 buyers) | 49% (46580/151144, 189 buyers) | 0.97 [0.74, 1.21] | 0.992 / 0.943 | 0.0 [0.0, 2.8] | no points |
| U2 repeated private contract | 4% (3/104, 76 buyers) | 26% (57451/204999, 269 buyers) | 0.252 [0.12, 0.42] | 0.251 / 0.436 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/104, 76 buyers) | 0% (36/204999, 269 buyers) | 0.116 [0.10, 0.14] | 0.182 / 0.244 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/104, 76 buyers) | 2% (3024/204999, 269 buyers) | 0.116 [0.10, 0.14] | 0.182 / 0.244 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/104, 76 buyers) | 0% (477/204999, 269 buyers) | 0.116 [0.10, 0.14] | 0.182 / 0.244 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 1% (1/104, 76 buyers) | 1% (3638/204999, 269 buyers) | 0.981 [0.10, 3.02] | 0.182 / 2.066 | 0.0 [0.0, 15.9] | no points |
| K5 restricted competition | 46% (45/104, 76 buyers) | 26% (54321/204999, 269 buyers) | 1.654 [1.27, 2.06] | 1.777 / 1.346 | 7.3 [3.4, 10.4] | 6.1 points |
| K6 award >= 95 % of reserve | 67% (48/72, 57 buyers) | 30% (35356/107181, 264 buyers) | 2.046 [1.69, 2.45] | 2.147 / 1.641 | 10.3 [7.6, 12.9] | 9.4 points |
| B1 single bid | 2% (1/53, 40 buyers) | 8% (1838/16089, 240 buyers) | 0.459 [0.17, 1.00] | 0.323 / 0.758 | 0.0 [0.0, 0.1] | no points |
| B2 two or three bids | 72% (38/53, 40 buyers) | 24% (2770/16089, 240 buyers) | 2.575 [2.06, 3.12] | 2.24 / 2.364 | 13.6 [10.4, 16.4] | 12.6 points |
| B3 just above the lower limit | 22% (14/51, 38 buyers) | 41% (6476/15879, 239 buyers) | 0.638 [0.41, 0.91] | 0.642 / 0.768 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 19% (3/15, 12 buyers) | 10% (1110/10976, 222 buyers) | 1.52 [0.53, 2.80] | 1.895 / 0.908 | 6.0 [0.0, 14.8] | 1 points |
| B5 large first gap | 33% (4/15, 12 buyers) | 10% (1048/10976, 222 buyers) | 2.233 [0.87, 3.74] | 1.603 / 2.119 | 11.6 [0.0, 19.0] | 7.3 points |
| B6 better bids disqualified | 0% (0/51, 38 buyers) | 2% (444/15874, 239 buyers) | 0.208 [0.17, 0.27] | 0.333 / 0.357 | 0.0 [0.0, 0.0] | no points |
| B7 same-minute bids | 17% (11/53, 40 buyers) | 6% (759/16089, 240 buyers) | 2.573 [1.12, 4.44] | 1.744 / 3.036 | 13.6 [1.6, 21.5] | 10.2 points |

### weighted, all linked tenders, all contracts (decision rule, amendment 2026-10-20): 738 labelled (275 buyers), 204999 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 26% (105/738, 275 buyers) | 63% (113995/204999, 269 buyers) | 0.431 [0.35, 0.51] | 0.436 / 0.469 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 27% (146/738, 275 buyers) | 15% (1122/204999, 269 buyers) | 1.722 [1.42, 2.08] | 1.956 / 1.37 | 7.8 [5.0, 10.6] | 6.9 points |
| G4 concentration | 12% (63/645, 214 buyers) | 14% (21456/204161, 230 buyers) | 0.904 [0.65, 1.16] | 1.0 / 0.789 | 0.0 [0.0, 2.1] | no points |
| G5 3+ changes | 2% (21/695, 267 buyers) | 3% (15527/196856, 269 buyers) | 0.623 [0.20, 1.18] | 0.585 / 0.619 | 0.0 [0.0, 2.3] | no points |
| G6 amount increase > 20 % | 2% (21/695, 267 buyers) | 3% (22183/196848, 269 buyers) | 0.513 [0.20, 0.96] | 0.292 / 0.689 | 0.0 [0.0, 0.0] | no points |
| N1 December signature | 10% (81/738, 275 buyers) | 12% (23703/204999, 269 buyers) | 0.883 [0.63, 1.14] | 1.108 / 0.613 | 0.0 [0.0, 1.8] | no points |
| N2 weekend signature | 1% (7/738, 275 buyers) | 1% (1467/204999, 269 buyers) | 1.254 [0.20, 2.85] | 1.273 / 0.672 | 3.3 [0.0, 15.1] | no points |
| N4 supplier dependence >= 25 % | 19% (90/738, 275 buyers) | 15% (5596/204999, 269 buyers) | 1.201 [0.98, 1.48] | 1.404 / 0.961 | 2.6 [0.0, 5.6] | 1.6 points |
| N5 first-time supplier | 55% (219/551, 194 buyers) | 49% (46580/151144, 189 buyers) | 1.109 [1.00, 1.22] | 1.092 / 1.118 | 1.5 [0.0, 2.8] | 0.9 points |
| U2 repeated private contract | 7% (36/738, 275 buyers) | 26% (57451/204999, 269 buyers) | 0.308 [0.21, 0.41] | 0.312 / 0.353 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/738, 275 buyers) | 0% (36/204999, 269 buyers) | 0.035 [0.04, 0.04] | 0.062 / 0.074 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 2% (7/738, 275 buyers) | 2% (3024/204999, 269 buyers) | 0.911 [0.28, 1.72] | 0.921 / 0.754 | 0.0 [0.0, 7.8] | no points |
| K3 just under small-value limit | 0% (0/738, 275 buyers) | 0% (477/204999, 269 buyers) | 0.035 [0.04, 0.04] | 0.062 / 0.074 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 0% (1/738, 275 buyers) | 1% (3638/204999, 269 buyers) | 0.296 [0.04, 0.92] | 0.062 / 0.627 | 0.0 [0.0, 0.0] | no points |
| K5 restricted competition | 38% (280/738, 275 buyers) | 26% (54321/204999, 269 buyers) | 1.413 [1.20, 1.64] | 1.569 / 1.205 | 5.0 [2.6, 7.1] | 4.3 points |
| K6 award >= 95 % of reserve | 66% (392/643, 233 buyers) | 30% (35356/107181, 264 buyers) | 2.14 [1.89, 2.42] | 2.166 / 2.009 | 11.0 [9.2, 12.7] | 10.3 points |
| B1 single bid | 3% (6/307, 143 buyers) | 8% (1838/16089, 240 buyers) | 0.376 [0.12, 0.75] | 0.372 / 0.447 | 0.0 [0.0, 0.0] | no points |
| B2 two or three bids | 69% (162/307, 143 buyers) | 24% (2770/16089, 240 buyers) | 2.704 [2.31, 3.15] | 2.542 / 2.639 | 14.4 [12.1, 16.6] | 13.5 points |
| B3 just above the lower limit | 16% (43/302, 143 buyers) | 41% (6476/15879, 239 buyers) | 0.438 [0.31, 0.58] | 0.448 / 0.502 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 17% (22/115, 49 buyers) | 10% (1110/10976, 222 buyers) | 1.614 [0.84, 2.52] | 2.016 / 1.083 | 6.9 [0.0, 13.4] | 4 points |
| B5 large first gap | 30% (36/115, 49 buyers) | 10% (1048/10976, 222 buyers) | 2.64 [1.61, 3.87] | 2.025 / 2.843 | 14.0 [6.9, 19.5] | 12 points |
| B6 better bids disqualified | 1% (1/302, 143 buyers) | 2% (444/15874, 239 buyers) | 0.447 [0.06, 1.02] | 0.115 / 0.762 | 0.0 [0.0, 0.3] | no points |
| B7 same-minute bids | 14% (42/307, 143 buyers) | 6% (759/16089, 240 buyers) | 2.291 [1.48, 3.38] | 2.067 / 2.27 | 12.0 [5.7, 17.6] | 9.9 points |

### weighted, one per case, competitive tenders with a notice: 80 labelled (59 buyers), 82313 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 0% (0/80, 59 buyers) | 0% (0/82313, 248 buyers) | 0.145 [0.12, 0.17] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 23% (17/80, 59 buyers) | 14% (621/82313, 248 buyers) | 1.581 [0.94, 2.37] | 1.891 / 0.643 | 6.6 [0.0, 12.4] | 4.3 points |
| G4 concentration | 11% (7/69, 49 buyers) | 11% (5828/81887, 224 buyers) | 0.942 [0.40, 1.58] | 1.094 / 0.732 | 0.0 [0.0, 6.6] | no points |
| G5 3+ changes | 4% (3/69, 55 buyers) | 8% (12179/77902, 248 buyers) | 0.587 [0.16, 1.16] | 0.538 / 0.762 | 0.0 [0.0, 2.2] | no points |
| G6 amount increase > 20 % | 2% (3/69, 55 buyers) | 5% (16544/77900, 248 buyers) | 0.58 [0.14, 1.37] | 0.227 / 1.09 | 0.0 [0.0, 4.6] | no points |
| N1 December signature | 18% (15/80, 59 buyers) | 12% (8619/82313, 248 buyers) | 1.421 [0.78, 2.11] | 1.738 / 0.878 | 5.1 [0.0, 10.8] | 2.5 points |
| N2 weekend signature | 3% (2/80, 59 buyers) | 0% (820/82313, 248 buyers) | 5.491 [0.14, 14.91] | 5.661 / 0.312 | 24.6 [0.0, 39.0] | 14.9 points |
| N4 supplier dependence >= 25 % | 15% (11/80, 59 buyers) | 12% (1842/82313, 248 buyers) | 1.206 [0.62, 1.87] | 1.534 / 0.634 | 2.7 [0.0, 9.0] | no points |
| N5 first-time supplier | 41% (22/53, 44 buyers) | 55% (23429/70738, 171 buyers) | 0.795 [0.60, 1.00] | 0.824 / 0.828 | 0.0 [0.0, 0.0] | no points |
| U2 repeated private contract | 0% (0/80, 59 buyers) | 0% (0/82313, 248 buyers) | 0.145 [0.12, 0.18] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/80, 59 buyers) | 0% (0/82313, 248 buyers) | 0.145 [0.12, 0.18] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/80, 59 buyers) | 0% (0/82313, 248 buyers) | 0.145 [0.12, 0.18] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/80, 59 buyers) | 0% (0/82313, 248 buyers) | 0.145 [0.12, 0.18] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 0% (0/80, 59 buyers) | 0% (0/82313, 248 buyers) | 0.145 [0.12, 0.18] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| K5 restricted competition | 48% (37/80, 59 buyers) | 78% (51276/82313, 248 buyers) | 0.675 [0.54, 0.80] | 0.763 / 0.652 | 0.0 [0.0, 0.0] | no points |
| K6 award >= 95 % of reserve | 72% (41/58, 46 buyers) | 20% (12080/43552, 240 buyers) | 3.067 [2.46, 3.74] | 3.298 / 1.997 | 16.2 [13.0, 19.0] | 15.1 points |
| B1 single bid | 2% (1/55, 42 buyers) | 2% (103/8067, 227 buyers) | 1.113 [0.17, 2.72] | 0.286 / 1.704 | 1.6 [0.0, 14.4] | no points |
| B2 two or three bids | 76% (41/55, 42 buyers) | 26% (1781/8067, 227 buyers) | 2.539 [2.06, 3.05] | 2.309 / 2.264 | 13.4 [10.5, 16.1] | 12.5 points |
| B3 just above the lower limit | 24% (15/53, 40 buyers) | 45% (3195/7932, 226 buyers) | 0.621 [0.42, 0.87] | 0.539 / 0.888 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 19% (3/15, 12 buyers) | 8% (556/6064, 205 buyers) | 1.711 [0.53, 3.33] | 2.153 / 0.937 | 7.8 [0.0, 17.3] | 2.5 points |
| B5 large first gap | 33% (4/15, 12 buyers) | 8% (478/6064, 205 buyers) | 2.695 [0.91, 4.82] | 1.782 / 2.63 | 14.3 [0.0, 22.7] | 9.7 points |
| B6 better bids disqualified | 0% (0/53, 40 buyers) | 2% (441/7931, 226 buyers) | 0.2 [0.16, 0.26] | 0.294 / 0.385 | 0.0 [0.0, 0.0] | no points |
| B7 same-minute bids | 16% (11/55, 42 buyers) | 6% (534/8067, 227 buyers) | 2.219 [1.02, 3.63] | 1.389 / 3.002 | 11.5 [0.3, 18.6] | 8.2 points |

### unweighted (court outcome ignored), one per case, all contracts: 104 labelled (76 buyers), 204999 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 9% (8/104, 76 buyers) | 63% (113995/204999, 269 buyers) | 0.248 [0.16, 0.34] | 0.268 / 0.406 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 32% (28/104, 76 buyers) | 15% (1122/204999, 269 buyers) | 1.921 [1.32, 2.61] | 2.152 / 1.369 | 9.4 [4.0, 13.9] | 7.5 points |
| G4 concentration | 10% (8/90, 63 buyers) | 14% (21456/204161, 230 buyers) | 0.763 [0.35, 1.21] | 0.831 / 0.734 | 0.0 [0.0, 2.8] | no points |
| G5 3+ changes | 4% (4/85, 68 buyers) | 3% (15527/196856, 269 buyers) | 1.302 [0.22, 2.81] | 0.976 / 1.46 | 3.8 [0.0, 14.9] | no points |
| G6 amount increase > 20 % | 2% (4/85, 68 buyers) | 3% (22183/196848, 269 buyers) | 0.812 [0.13, 1.87] | 0.2 / 1.39 | 0.0 [0.0, 9.0] | no points |
| N1 December signature | 18% (18/104, 76 buyers) | 12% (23703/204999, 269 buyers) | 1.469 [0.88, 2.13] | 1.941 / 0.72 | 5.6 [0.0, 10.9] | 3.2 points |
| N2 weekend signature | 1% (1/104, 76 buyers) | 1% (1467/204999, 269 buyers) | 1.671 [0.10, 5.29] | 2.025 / 0.244 | 7.4 [0.0, 24.0] | no points |
| N4 supplier dependence >= 25 % | 16% (14/104, 76 buyers) | 15% (5596/204999, 269 buyers) | 0.996 [0.57, 1.53] | 1.237 / 0.714 | 0.0 [0.0, 6.1] | no points |
| N5 first-time supplier | 47% (25/54, 45 buyers) | 49% (46580/151144, 189 buyers) | 0.97 [0.74, 1.21] | 0.992 / 0.943 | 0.0 [0.0, 2.8] | no points |
| U2 repeated private contract | 4% (3/104, 76 buyers) | 26% (57451/204999, 269 buyers) | 0.252 [0.12, 0.42] | 0.251 / 0.436 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/104, 76 buyers) | 0% (36/204999, 269 buyers) | 0.116 [0.10, 0.14] | 0.182 / 0.244 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/104, 76 buyers) | 2% (3024/204999, 269 buyers) | 0.116 [0.10, 0.14] | 0.182 / 0.244 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/104, 76 buyers) | 0% (477/204999, 269 buyers) | 0.116 [0.10, 0.14] | 0.182 / 0.244 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 1% (1/104, 76 buyers) | 1% (3638/204999, 269 buyers) | 0.981 [0.10, 3.02] | 0.182 / 2.066 | 0.0 [0.0, 15.9] | no points |
| K5 restricted competition | 46% (45/104, 76 buyers) | 26% (54321/204999, 269 buyers) | 1.654 [1.27, 2.06] | 1.777 / 1.346 | 7.3 [3.4, 10.4] | 6.1 points |
| K6 award >= 95 % of reserve | 67% (48/72, 57 buyers) | 30% (35356/107181, 264 buyers) | 2.046 [1.69, 2.45] | 2.147 / 1.641 | 10.3 [7.6, 12.9] | 9.4 points |
| B1 single bid | 2% (1/53, 40 buyers) | 8% (1838/16089, 240 buyers) | 0.459 [0.17, 1.00] | 0.323 / 0.758 | 0.0 [0.0, 0.1] | no points |
| B2 two or three bids | 72% (38/53, 40 buyers) | 24% (2770/16089, 240 buyers) | 2.575 [2.06, 3.12] | 2.24 / 2.364 | 13.6 [10.4, 16.4] | 12.6 points |
| B3 just above the lower limit | 22% (14/51, 38 buyers) | 41% (6476/15879, 239 buyers) | 0.638 [0.41, 0.91] | 0.642 / 0.768 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 19% (3/15, 12 buyers) | 10% (1110/10976, 222 buyers) | 1.52 [0.53, 2.80] | 1.895 / 0.908 | 6.0 [0.0, 14.8] | 1 points |
| B5 large first gap | 33% (4/15, 12 buyers) | 10% (1048/10976, 222 buyers) | 2.233 [0.87, 3.74] | 1.603 / 2.119 | 11.6 [0.0, 19.0] | 7.3 points |
| B6 better bids disqualified | 0% (0/51, 38 buyers) | 2% (444/15874, 239 buyers) | 0.208 [0.17, 0.27] | 0.333 / 0.357 | 0.0 [0.0, 0.0] | no points |
| B7 same-minute bids | 17% (11/53, 40 buyers) | 6% (759/16089, 240 buyers) | 2.573 [1.12, 4.44] | 1.744 / 3.036 | 13.6 [1.6, 21.5] | 10.2 points |
