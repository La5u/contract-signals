# South Korea: checks against KONEPS tenders found rigged by the Fair Trade Commission — first results (2026-10-20, preparation run)

Plan and amendments: [korea-labels-plan.md](korea-labels-plan.md). Research only: no score, weight or dataset change without the owner.
Scripts: `tools/extract-korea-kftc-tenders.py` (tender tables read from decision images), `tools/match-korea-kftc-tenders.py`
(links to KONEPS notices), `tools/check-korea-kftc-finality.py` (court outcomes), `tools/korea-label-checks.py` (this table).

**Status: preparation, not a decision.** Decision rule as amended 2026-10-20 (owner: fewer, more lenient safeguards): all linked tenders, points from the LR we are 75 % sure of; see the plan. Collusion family only (court convictions not linked yet). G1 single offer not computed
(the bid-opening results per notice are not downloaded). Finality: law.go.kr publishes 100 court rulings on KFTC bid-rigging
orders, and only 2 of them cite one of the 124 cases with linked tenders (both upheld). The other cases count as "no challenge
found", weight 1.

Labels: 1,218 KFTC bid-rigging decisions → 12,534 tenders read → 6,480 public tenders → 1,087 linked to one KONEPS notice
(416 by winner + amount, 269 by notice number, 249 by amount + buyer, 153 by winner + buyer + name; 109 ambiguous,
5,284 unmatched, mostly buyers outside KONEPS: DAPA, KEPCO, the Korea Expressway Corporation, KORAIL) → 740 notices in 106 cases.

## Buyer = contracting office (plan)

    740 linked notices in 106 cases; 724 with a contract in the data; 230 buyer-years (buyer_code); 433395 contracts
    finality: {'none': 702, 'upheld': 22} 

### weighted, one per case, all contracts (decision basis until 2026-10-20): 105 labelled (52 buyers), 432515 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 14% (8/105, 52 buyers) | 63% (183435/432515, 135 buyers) | 0.342 [0.23, 0.47] | 0.387 / 0.487 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 29% (17/105, 52 buyers) | 20% (468/432515, 135 buyers) | 1.388 [0.89, 2.07] | 1.404 / 1.246 | 4.7 [0.0, 10.5] | 2.8 points |
| G4 concentration | 15% (8/94, 42 buyers) | 16% (12571/432097, 106 buyers) | 0.938 [0.48, 1.46] | 0.948 / 0.91 | 0.0 [0.0, 5.5] | no points |
| G5 3+ changes | 6% (4/85, 42 buyers) | 3% (16609/396824, 134 buyers) | 1.772 [0.34, 3.60] | 1.5 / 1.552 | 8.3 [0.0, 18.5] | 2 points |
| G6 amount increase > 20 % | 6% (4/85, 42 buyers) | 4% (26762/396672, 134 buyers) | 1.579 [0.32, 3.34] | 0.502 / 2.237 | 6.6 [0.0, 17.4] | 0.5 points |
| N1 December signature | 14% (18/105, 52 buyers) | 10% (52789/432515, 135 buyers) | 1.323 [0.64, 2.07] | 1.592 / 0.814 | 4.0 [0.0, 10.5] | 0.8 points |
| N2 weekend signature | 1% (1/105, 52 buyers) | 1% (2699/432515, 135 buyers) | 0.918 [0.14, 2.97] | 0.263 / 1.442 | 0.0 [0.0, 15.7] | no points |
| N4 supplier dependence >= 25 % | 22% (13/105, 52 buyers) | 22% (4839/432515, 135 buyers) | 0.996 [0.60, 1.44] | 1.035 / 0.942 | 0.0 [0.0, 5.3] | no points |
| N5 first-time supplier | 38% (16/58, 31 buyers) | 49% (89514/315190, 97 buyers) | 0.819 [0.57, 1.06] | 0.927 / 0.752 | 0.0 [0.0, 0.9] | no points |
| U2 repeated private contract | 6% (3/105, 52 buyers) | 28% (97521/432515, 135 buyers) | 0.332 [0.17, 0.53] | 0.351 / 0.512 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/105, 52 buyers) | 0% (2167/432515, 135 buyers) | 0.161 [0.14, 0.19] | 0.263 / 0.294 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/105, 52 buyers) | 2% (18683/432515, 135 buyers) | 0.161 [0.14, 0.20] | 0.263 / 0.294 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/105, 52 buyers) | 0% (348/432515, 135 buyers) | 0.161 [0.14, 0.20] | 0.263 / 0.294 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 2% (1/105, 52 buyers) | 1% (2242/432515, 135 buyers) | 1.182 [0.14, 3.59] | 0.263 / 1.945 | 2.4 [0.0, 18.4] | no points |
| K5 restricted competition | 47% (47/105, 52 buyers) | 27% (149483/432515, 135 buyers) | 1.622 [1.20, 2.06] | 1.436 / 1.623 | 7.0 [2.7, 10.4] | 5.5 points |
| K6 award >= 95 % of reserve | 64% (49/74, 33 buyers) | 26% (177837/313353, 130 buyers) | 2.072 [1.57, 2.62] | 1.878 / 1.838 | 10.5 [6.5, 13.9] | 9.2 points |

### weighted, all linked tenders, all contracts (decision rule, amendment 2026-10-20): 724 labelled (141 buyers), 432515 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 28% (102/724, 141 buyers) | 63% (183435/432515, 135 buyers) | 0.486 [0.39, 0.59] | 0.464 / 0.583 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 37% (83/724, 141 buyers) | 20% (468/432515, 135 buyers) | 1.825 [1.48, 2.32] | 2.032 / 1.485 | 8.7 [5.7, 12.1] | 7.6 points |
| G4 concentration | 32% (66/661, 100 buyers) | 16% (12571/432097, 106 buyers) | 1.854 [1.49, 2.39] | 1.722 / 1.798 | 8.9 [5.8, 12.6] | 7.8 points |
| G5 3+ changes | 3% (21/680, 131 buyers) | 3% (16609/396824, 134 buyers) | 0.833 [0.21, 1.68] | 0.596 / 0.946 | 0.0 [0.0, 7.4] | no points |
| G6 amount increase > 20 % | 2% (21/680, 131 buyers) | 4% (26762/396672, 134 buyers) | 0.664 [0.21, 1.29] | 0.57 / 0.714 | 0.0 [0.0, 3.7] | no points |
| N1 December signature | 10% (81/724, 141 buyers) | 10% (52789/432515, 135 buyers) | 0.951 [0.58, 1.37] | 1.137 / 0.653 | 0.0 [0.0, 4.6] | no points |
| N2 weekend signature | 0% (7/724, 141 buyers) | 1% (2699/432515, 135 buyers) | 0.203 [0.07, 0.55] | 0.115 / 0.367 | 0.0 [0.0, 0.0] | no points |
| N4 supplier dependence >= 25 % | 35% (86/724, 141 buyers) | 22% (4839/432515, 135 buyers) | 1.545 [1.32, 1.85] | 1.644 / 1.332 | 6.3 [4.1, 8.9] | 5.5 points |
| N5 first-time supplier | 48% (141/550, 101 buyers) | 49% (89514/315190, 97 buyers) | 0.966 [0.84, 1.09] | 1.024 / 0.882 | 0.0 [0.0, 1.3] | no points |
| U2 repeated private contract | 15% (60/724, 141 buyers) | 28% (97521/432515, 135 buyers) | 0.562 [0.40, 0.71] | 0.547 / 0.636 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/724, 141 buyers) | 0% (2167/432515, 135 buyers) | 0.066 [0.07, 0.07] | 0.115 / 0.135 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (7/724, 141 buyers) | 2% (18683/432515, 135 buyers) | 0.292 [0.07, 0.71] | 0.423 / 0.141 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/724, 141 buyers) | 0% (348/432515, 135 buyers) | 0.066 [0.07, 0.07] | 0.115 / 0.135 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 1% (1/724, 141 buyers) | 1% (2242/432515, 135 buyers) | 0.485 [0.07, 1.40] | 0.115 / 0.894 | 0.0 [0.0, 4.8] | no points |
| K5 restricted competition | 38% (281/724, 141 buyers) | 27% (149483/432515, 135 buyers) | 1.367 [1.11, 1.65] | 1.379 / 1.293 | 4.5 [1.6, 7.3] | 3.5 points |
| K6 award >= 95 % of reserve | 67% (391/642, 119 buyers) | 26% (177837/313353, 130 buyers) | 2.392 [2.00, 2.91] | 2.209 / 2.358 | 12.6 [10.0, 15.4] | 11.6 points |

### weighted, one per case, competitive tenders with a notice: 79 labelled (39 buyers), 192392 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 0% (0/79, 39 buyers) | 0% (0/192392, 117 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 23% (11/79, 39 buyers) | 17% (260/192392, 117 buyers) | 1.27 [0.67, 2.08] | 1.219 / 1.182 | 3.5 [0.0, 10.5] | 0.6 points |
| G4 concentration | 16% (7/72, 33 buyers) | 16% (4050/192247, 103 buyers) | 0.989 [0.48, 1.57] | 1.117 / 0.769 | 0.0 [0.0, 6.5] | no points |
| G5 3+ changes | 6% (3/68, 35 buyers) | 8% (11781/167396, 117 buyers) | 0.809 [0.22, 1.62] | 0.892 / 0.779 | 0.0 [0.0, 7.0] | no points |
| G6 amount increase > 20 % | 5% (3/68, 35 buyers) | 6% (17058/167382, 117 buyers) | 0.832 [0.24, 1.80] | 0.474 / 1.179 | 0.0 [0.0, 8.5] | no points |
| N1 December signature | 14% (14/79, 39 buyers) | 11% (24458/192392, 117 buyers) | 1.16 [0.53, 1.88] | 1.248 / 0.943 | 2.1 [0.0, 9.1] | no points |
| N2 weekend signature | 1% (2/79, 39 buyers) | 0% (1423/192392, 117 buyers) | 1.81 [0.20, 5.29] | 0.312 / 2.085 | 8.6 [0.0, 24.0] | no points |
| N4 supplier dependence >= 25 % | 17% (8/79, 39 buyers) | 18% (1601/192392, 117 buyers) | 0.919 [0.48, 1.52] | 0.977 / 0.834 | 0.0 [0.0, 6.1] | no points |
| N5 first-time supplier | 28% (12/58, 27 buyers) | 49% (57722/185173, 80 buyers) | 0.688 [0.47, 0.93] | 0.821 / 0.648 | 0.0 [0.0, 0.0] | no points |
| U2 repeated private contract | 0% (0/79, 39 buyers) | 0% (0/192392, 117 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/79, 39 buyers) | 0% (0/192392, 117 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/79, 39 buyers) | 0% (0/192392, 117 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/79, 39 buyers) | 0% (0/192392, 117 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 0% (0/79, 39 buyers) | 0% (0/192392, 117 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| K5 restricted competition | 54% (37/79, 39 buyers) | 82% (122115/192392, 117 buyers) | 0.725 [0.59, 0.86] | 0.732 / 0.821 | 0.0 [0.0, 0.0] | no points |
| K6 award >= 95 % of reserve | 65% (41/60, 30 buyers) | 20% (31112/105723, 117 buyers) | 2.721 [2.02, 3.60] | 2.299 / 2.416 | 14.4 [10.2, 18.5] | 12.9 points |

### unweighted (court outcome ignored), one per case, all contracts: 105 labelled (52 buyers), 432515 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 14% (8/105, 52 buyers) | 63% (183435/432515, 135 buyers) | 0.342 [0.23, 0.47] | 0.387 / 0.487 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 29% (17/105, 52 buyers) | 20% (468/432515, 135 buyers) | 1.388 [0.89, 2.07] | 1.404 / 1.246 | 4.7 [0.0, 10.5] | 2.8 points |
| G4 concentration | 15% (8/94, 42 buyers) | 16% (12571/432097, 106 buyers) | 0.938 [0.48, 1.46] | 0.948 / 0.91 | 0.0 [0.0, 5.5] | no points |
| G5 3+ changes | 6% (4/85, 42 buyers) | 3% (16609/396824, 134 buyers) | 1.772 [0.34, 3.60] | 1.5 / 1.552 | 8.3 [0.0, 18.5] | 2 points |
| G6 amount increase > 20 % | 6% (4/85, 42 buyers) | 4% (26762/396672, 134 buyers) | 1.579 [0.32, 3.34] | 0.502 / 2.237 | 6.6 [0.0, 17.4] | 0.5 points |
| N1 December signature | 14% (18/105, 52 buyers) | 10% (52789/432515, 135 buyers) | 1.323 [0.64, 2.07] | 1.592 / 0.814 | 4.0 [0.0, 10.5] | 0.8 points |
| N2 weekend signature | 1% (1/105, 52 buyers) | 1% (2699/432515, 135 buyers) | 0.918 [0.14, 2.97] | 0.263 / 1.442 | 0.0 [0.0, 15.7] | no points |
| N4 supplier dependence >= 25 % | 22% (13/105, 52 buyers) | 22% (4839/432515, 135 buyers) | 0.996 [0.60, 1.44] | 1.035 / 0.942 | 0.0 [0.0, 5.3] | no points |
| N5 first-time supplier | 38% (16/58, 31 buyers) | 49% (89514/315190, 97 buyers) | 0.819 [0.57, 1.06] | 0.927 / 0.752 | 0.0 [0.0, 0.9] | no points |
| U2 repeated private contract | 6% (3/105, 52 buyers) | 28% (97521/432515, 135 buyers) | 0.332 [0.17, 0.53] | 0.351 / 0.512 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/105, 52 buyers) | 0% (2167/432515, 135 buyers) | 0.161 [0.14, 0.19] | 0.263 / 0.294 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/105, 52 buyers) | 2% (18683/432515, 135 buyers) | 0.161 [0.14, 0.20] | 0.263 / 0.294 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/105, 52 buyers) | 0% (348/432515, 135 buyers) | 0.161 [0.14, 0.20] | 0.263 / 0.294 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 2% (1/105, 52 buyers) | 1% (2242/432515, 135 buyers) | 1.182 [0.14, 3.59] | 0.263 / 1.945 | 2.4 [0.0, 18.4] | no points |
| K5 restricted competition | 47% (47/105, 52 buyers) | 27% (149483/432515, 135 buyers) | 1.622 [1.20, 2.06] | 1.436 / 1.623 | 7.0 [2.7, 10.4] | 5.5 points |
| K6 award >= 95 % of reserve | 64% (49/74, 33 buyers) | 26% (177837/313353, 130 buyers) | 2.072 [1.57, 2.62] | 1.878 / 1.838 | 10.5 [6.5, 13.9] | 9.2 points |

## Buyer = demanding body (sensitivity)

    740 linked notices in 106 cases; 740 with a contract in the data; 418 buyer-years (demand_code); 208417 contracts
    finality: {'none': 718, 'upheld': 22} 

### weighted, one per case, all contracts (decision basis until 2026-10-20): 106 labelled (78 buyers), 207521 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 9% (8/106, 78 buyers) | 62% (114350/207521, 270 buyers) | 0.244 [0.16, 0.34] | 0.264 / 0.398 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 29% (26/106, 78 buyers) | 15% (1188/207521, 270 buyers) | 1.767 [1.22, 2.43] | 1.935 / 1.34 | 8.2 [2.8, 12.8] | 6.4 points |
| G4 concentration | 10% (8/91, 64 buyers) | 14% (21447/206673, 230 buyers) | 0.756 [0.34, 1.23] | 0.817 / 0.736 | 0.0 [0.0, 2.9] | no points |
| G5 3+ changes | 4% (4/86, 69 buyers) | 3% (15670/198157, 270 buyers) | 1.288 [0.21, 2.84] | 0.978 / 1.427 | 3.7 [0.0, 15.1] | no points |
| G6 amount increase > 20 % | 2% (4/86, 69 buyers) | 3% (22260/198144, 270 buyers) | 0.806 [0.13, 1.87] | 0.2 / 1.363 | 0.0 [0.0, 9.0] | no points |
| N1 December signature | 19% (19/106, 78 buyers) | 11% (24035/207521, 270 buyers) | 1.538 [0.94, 2.23] | 2.066 / 0.704 | 6.2 [0.0, 11.6] | 3.9 points |
| N2 weekend signature | 1% (1/106, 78 buyers) | 1% (1503/207521, 270 buyers) | 1.616 [0.10, 5.43] | 1.952 / 0.238 | 6.9 [0.0, 24.4] | no points |
| N4 supplier dependence >= 25 % | 16% (15/106, 78 buyers) | 15% (5334/207521, 270 buyers) | 1.062 [0.63, 1.58] | 1.225 / 0.853 | 0.9 [0.0, 6.6] | no points |
| N5 first-time supplier | 47% (25/54, 45 buyers) | 49% (46861/151913, 189 buyers) | 0.969 [0.74, 1.21] | 0.994 / 0.94 | 0.0 [0.0, 2.7] | no points |
| U2 repeated private contract | 4% (3/106, 78 buyers) | 25% (57555/207521, 270 buyers) | 0.248 [0.12, 0.42] | 0.247 / 0.429 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/106, 78 buyers) | 0% (36/207521, 270 buyers) | 0.114 [0.10, 0.14] | 0.179 / 0.238 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/106, 78 buyers) | 2% (3036/207521, 270 buyers) | 0.114 [0.10, 0.13] | 0.179 / 0.238 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/106, 78 buyers) | 0% (477/207521, 270 buyers) | 0.114 [0.10, 0.14] | 0.179 / 0.238 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 1% (1/106, 78 buyers) | 1% (3638/207521, 270 buyers) | 0.967 [0.10, 3.16] | 0.179 / 2.042 | 0.0 [0.0, 16.6] | no points |
| K5 restricted competition | 47% (47/106, 78 buyers) | 26% (55663/207521, 270 buyers) | 1.681 [1.31, 2.09] | 1.8 / 1.379 | 7.5 [3.9, 10.7] | 6.4 points |
| K6 award >= 95 % of reserve | 67% (48/72, 57 buyers) | 30% (35662/108533, 265 buyers) | 2.042 [1.69, 2.41] | 2.149 / 1.633 | 10.3 [7.6, 12.7] | 9.4 points |

### weighted, all linked tenders, all contracts (decision rule, amendment 2026-10-20): 740 labelled (276 buyers), 207521 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 26% (105/740, 276 buyers) | 62% (114350/207521, 270 buyers) | 0.433 [0.36, 0.50] | 0.437 / 0.47 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 26% (138/740, 276 buyers) | 15% (1188/207521, 270 buyers) | 1.675 [1.39, 2.02] | 1.891 / 1.348 | 7.4 [4.7, 10.1] | 6.5 points |
| G4 concentration | 12% (63/646, 214 buyers) | 14% (21447/206673, 230 buyers) | 0.908 [0.66, 1.17] | 1.004 / 0.792 | 0.0 [0.0, 2.3] | no points |
| G5 3+ changes | 2% (21/696, 268 buyers) | 3% (15670/198157, 270 buyers) | 0.622 [0.19, 1.21] | 0.586 / 0.616 | 0.0 [0.0, 2.8] | no points |
| G6 amount increase > 20 % | 2% (21/696, 268 buyers) | 3% (22260/198144, 270 buyers) | 0.515 [0.18, 0.95] | 0.294 / 0.689 | 0.0 [0.0, 0.0] | no points |
| N1 December signature | 10% (82/740, 276 buyers) | 11% (24035/207521, 270 buyers) | 0.882 [0.63, 1.13] | 1.111 / 0.611 | 0.0 [0.0, 1.8] | no points |
| N2 weekend signature | 1% (7/740, 276 buyers) | 1% (1503/207521, 270 buyers) | 1.237 [0.22, 2.93] | 1.248 / 0.666 | 3.1 [0.0, 15.5] | no points |
| N4 supplier dependence >= 25 % | 19% (88/740, 276 buyers) | 15% (5334/207521, 270 buyers) | 1.208 [0.98, 1.50] | 1.394 / 0.981 | 2.7 [0.0, 5.9] | 1.7 points |
| N5 first-time supplier | 55% (219/551, 194 buyers) | 49% (46861/151913, 189 buyers) | 1.107 [1.00, 1.22] | 1.094 / 1.113 | 1.5 [0.0, 2.8] | 0.9 points |
| U2 repeated private contract | 7% (36/740, 276 buyers) | 25% (57555/207521, 270 buyers) | 0.309 [0.21, 0.41] | 0.313 / 0.355 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/740, 276 buyers) | 0% (36/207521, 270 buyers) | 0.035 [0.04, 0.04] | 0.062 / 0.074 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 2% (7/740, 276 buyers) | 2% (3036/207521, 270 buyers) | 0.89 [0.27, 1.75] | 0.883 / 0.759 | 0.0 [0.0, 8.0] | no points |
| K3 just under small-value limit | 0% (0/740, 276 buyers) | 0% (477/207521, 270 buyers) | 0.035 [0.04, 0.04] | 0.062 / 0.074 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 0% (1/740, 276 buyers) | 1% (3638/207521, 270 buyers) | 0.297 [0.04, 0.94] | 0.062 / 0.631 | 0.0 [0.0, 0.0] | no points |
| K5 restricted competition | 38% (282/740, 276 buyers) | 26% (55663/207521, 270 buyers) | 1.406 [1.20, 1.62] | 1.56 / 1.201 | 4.9 [2.6, 7.0] | 4.2 points |
| K6 award >= 95 % of reserve | 66% (392/643, 233 buyers) | 30% (35662/108533, 265 buyers) | 2.135 [1.89, 2.41] | 2.168 / 1.998 | 10.9 [9.1, 12.7] | 10.3 points |

### weighted, one per case, competitive tenders with a notice: 80 labelled (59 buyers), 83725 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 0% (0/80, 59 buyers) | 0% (0/83725, 249 buyers) | 0.145 [0.12, 0.18] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 19% (14/80, 59 buyers) | 14% (667/83725, 249 buyers) | 1.321 [0.75, 1.99] | 1.676 / 0.38 | 4.0 [0.0, 9.9] | 1.5 points |
| G4 concentration | 11% (7/69, 49 buyers) | 11% (5828/83281, 224 buyers) | 0.953 [0.40, 1.59] | 1.105 / 0.738 | 0.0 [0.0, 6.7] | no points |
| G5 3+ changes | 4% (3/69, 55 buyers) | 8% (12301/78655, 249 buyers) | 0.589 [0.16, 1.20] | 0.541 / 0.763 | 0.0 [0.0, 2.6] | no points |
| G6 amount increase > 20 % | 2% (3/69, 55 buyers) | 5% (16601/78652, 249 buyers) | 0.585 [0.14, 1.37] | 0.227 / 1.103 | 0.0 [0.0, 4.5] | no points |
| N1 December signature | 18% (15/80, 59 buyers) | 12% (8814/83725, 249 buyers) | 1.429 [0.81, 2.12] | 1.739 / 0.885 | 5.1 [0.0, 10.8] | 2.8 points |
| N2 weekend signature | 3% (2/80, 59 buyers) | 0% (837/83725, 249 buyers) | 5.284 [0.14, 14.33] | 5.372 / 0.312 | 24.0 [0.0, 38.4] | 14.2 points |
| N4 supplier dependence >= 25 % | 15% (11/80, 59 buyers) | 12% (1740/83725, 249 buyers) | 1.235 [0.67, 1.89] | 1.534 / 0.655 | 3.1 [0.0, 9.2] | 0.2 points |
| N5 first-time supplier | 41% (22/53, 44 buyers) | 55% (23694/71396, 171 buyers) | 0.795 [0.59, 0.99] | 0.828 / 0.825 | 0.0 [0.0, 0.0] | no points |
| U2 repeated private contract | 0% (0/80, 59 buyers) | 0% (0/83725, 249 buyers) | 0.145 [0.12, 0.18] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/80, 59 buyers) | 0% (0/83725, 249 buyers) | 0.145 [0.12, 0.17] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/80, 59 buyers) | 0% (0/83725, 249 buyers) | 0.145 [0.12, 0.17] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/80, 59 buyers) | 0% (0/83725, 249 buyers) | 0.145 [0.12, 0.18] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 0% (0/80, 59 buyers) | 0% (0/83725, 249 buyers) | 0.145 [0.12, 0.18] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| K5 restricted competition | 48% (37/80, 59 buyers) | 78% (52168/83725, 249 buyers) | 0.679 [0.55, 0.81] | 0.765 / 0.657 | 0.0 [0.0, 0.0] | no points |
| K6 award >= 95 % of reserve | 72% (41/58, 46 buyers) | 20% (12188/44299, 241 buyers) | 3.057 [2.46, 3.71] | 3.282 / 1.996 | 16.1 [13.0, 18.9] | 15.1 points |

### unweighted (court outcome ignored), one per case, all contracts: 106 labelled (78 buyers), 207521 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 9% (8/106, 78 buyers) | 62% (114350/207521, 270 buyers) | 0.244 [0.16, 0.34] | 0.264 / 0.398 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 29% (26/106, 78 buyers) | 15% (1188/207521, 270 buyers) | 1.767 [1.22, 2.43] | 1.935 / 1.34 | 8.2 [2.8, 12.8] | 6.4 points |
| G4 concentration | 10% (8/91, 64 buyers) | 14% (21447/206673, 230 buyers) | 0.756 [0.34, 1.23] | 0.817 / 0.736 | 0.0 [0.0, 2.9] | no points |
| G5 3+ changes | 4% (4/86, 69 buyers) | 3% (15670/198157, 270 buyers) | 1.288 [0.21, 2.84] | 0.978 / 1.427 | 3.7 [0.0, 15.1] | no points |
| G6 amount increase > 20 % | 2% (4/86, 69 buyers) | 3% (22260/198144, 270 buyers) | 0.806 [0.13, 1.87] | 0.2 / 1.363 | 0.0 [0.0, 9.0] | no points |
| N1 December signature | 19% (19/106, 78 buyers) | 11% (24035/207521, 270 buyers) | 1.538 [0.94, 2.23] | 2.066 / 0.704 | 6.2 [0.0, 11.6] | 3.9 points |
| N2 weekend signature | 1% (1/106, 78 buyers) | 1% (1503/207521, 270 buyers) | 1.616 [0.10, 5.43] | 1.952 / 0.238 | 6.9 [0.0, 24.4] | no points |
| N4 supplier dependence >= 25 % | 16% (15/106, 78 buyers) | 15% (5334/207521, 270 buyers) | 1.062 [0.63, 1.58] | 1.225 / 0.853 | 0.9 [0.0, 6.6] | no points |
| N5 first-time supplier | 47% (25/54, 45 buyers) | 49% (46861/151913, 189 buyers) | 0.969 [0.74, 1.21] | 0.994 / 0.94 | 0.0 [0.0, 2.7] | no points |
| U2 repeated private contract | 4% (3/106, 78 buyers) | 25% (57555/207521, 270 buyers) | 0.248 [0.12, 0.42] | 0.247 / 0.429 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/106, 78 buyers) | 0% (36/207521, 270 buyers) | 0.114 [0.10, 0.14] | 0.179 / 0.238 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/106, 78 buyers) | 2% (3036/207521, 270 buyers) | 0.114 [0.10, 0.13] | 0.179 / 0.238 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/106, 78 buyers) | 0% (477/207521, 270 buyers) | 0.114 [0.10, 0.14] | 0.179 / 0.238 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 1% (1/106, 78 buyers) | 1% (3638/207521, 270 buyers) | 0.967 [0.10, 3.16] | 0.179 / 2.042 | 0.0 [0.0, 16.6] | no points |
| K5 restricted competition | 47% (47/106, 78 buyers) | 26% (55663/207521, 270 buyers) | 1.681 [1.31, 2.09] | 1.8 / 1.379 | 7.5 [3.9, 10.7] | 6.4 points |
| K6 award >= 95 % of reserve | 67% (48/72, 57 buyers) | 30% (35662/108533, 265 buyers) | 2.042 [1.69, 2.41] | 2.149 / 1.633 | 10.3 [7.6, 12.7] | 9.4 points |
