# South Korea: size control for G3, N4 and K6 (2026-10-20, rerun 2026-10-22 without amendment-only records)

Method and fixed bands: `tools/korea-buyer-share-size.py` docstring and [bias-controls-plan.md](bias-controls-plan.md). Decision rule set of [korea-collusion-results.md](korea-collusion-results.md) (buyer = contracting office). Points basis: size-standardised, rigged values / 1.3.

721 rigged rows, 409522 comparisons
Comparison value edges (KRW) at (0.5, 0.8, 0.9, 0.95, 0.98, 0.99): ['139,871,600', '746,800,000', '1,870,000,000', '3,453,626,000', '7,150,000,000', '12,859,458,600']
Rigged band mix: Counter({'p50-80': 250, '<p50': 234, 'p80-90': 102, '>=p99': 40, 'p90-95': 37, 'p98-99': 30, 'p95-98': 28})

| Basis | Hit rate, rigged | Comparisons | LR shrunk [95 %] | LR at 25th pct | Decision points |
|---|---|---|---|---|---|
| G3 buyer share >= 5 % unadjusted | 38% (84/721, 139 buyers) | 19.0% | 1.901 [1.55, 2.43] | 1.768 | 8.2 |
| G3 buyer share >= 5 % size-standardised | 38% (84/721, 139.0 buyers) | 19.3% | 1.877 [1.61, 2.18] | 1.769 | 8.2 |
| G3 buyer share >= 5 % size-standardised, rigged values / 1.3 (points basis) | 38% (84/721, 139.0 buyers) | 19.0% | 1.9 [1.62, 2.24] | 1.789 | 8.4 |
| G3 buyer share >= 5 % within <p50 | 37/234 (97 buyers) | 17.5% | 1.934 | | |
| G3 buyer share >= 5 % within p50-80 | 6/250 (40 buyers) | 8.5% | 0.563 | | |
| G3 buyer share >= 5 % within p80-90 | 11/102 (21 buyers) | 14.4% | 0.759 | | |
| G3 buyer share >= 5 % within p90-95 | 14/37 (14 buyers) | 22.9% | 1.853 | | |
| G3 buyer share >= 5 % within p95-98 | 3/28 (9 buyers) | 41.3% | 0.908 | | |
| G3 buyer share >= 5 % within p98-99 | 3/30 (6 buyers) | 44.4% | 1.046 | | |
| G3 buyer share >= 5 % within >=p99 | 10/40 (14 buyers) | 55.0% | 1.081 | | |
| N4 supplier dependence >= 25 % unadjusted | 35% (85/721, 139 buyers) | 21.6% | 1.563 [1.34, 1.87] | 1.473 | 5.6 |
| N4 supplier dependence >= 25 % size-standardised | 35% (85/721, 139.0 buyers) | 15.8% | 2.096 [1.74, 2.59] | 1.956 | 9.7 |
| N4 supplier dependence >= 25 % size-standardised, rigged values / 1.3 (points basis) | 35% (85/721, 139.0 buyers) | 16.5% | 2.017 [1.68, 2.48] | 1.886 | 9.2 |
| N4 supplier dependence >= 25 % within <p50 | 47/234 (97 buyers) | 21.1% | 1.764 | | |
| N4 supplier dependence >= 25 % within p50-80 | 13/250 (40 buyers) | 9.9% | 1.163 | | |
| N4 supplier dependence >= 25 % within p80-90 | 9/102 (21 buyers) | 3.5% | 2.359 | | |
| N4 supplier dependence >= 25 % within p90-95 | 9/37 (14 buyers) | 2.9% | 6.918 | | |
| N4 supplier dependence >= 25 % within p95-98 | 2/28 (9 buyers) | 5.7% | 2.164 | | |
| N4 supplier dependence >= 25 % within p98-99 | 2/30 (6 buyers) | 4.9% | 2.725 | | |
| N4 supplier dependence >= 25 % within >=p99 | 3/40 (14 buyers) | 10.1% | 1.511 | | |
| K6 award >= 95 % of reserve unadjusted | 67% (391/641, 119 buyers) | 26.4% | 2.389 [1.98, 2.90] | 2.241 | 11.6 |
| K6 award >= 95 % of reserve size-standardised | 67% (391/641, 119.0 buyers) | 24.4% | 2.579 [2.17, 3.14] | 2.438 | 12.9 |
| K6 award >= 95 % of reserve size-standardised, rigged values / 1.3 (points basis) | 67% (391/641, 119.0 buyers) | 24.7% | 2.547 [2.16, 3.09] | 2.41 | 12.7 |
| K6 award >= 95 % of reserve within <p50 | 122/211 (88 buyers) | 27.3% | 2.311 | | |
| K6 award >= 95 % of reserve within p50-80 | 134/242 (39 buyers) | 17.1% | 2.489 | | |
| K6 award >= 95 % of reserve within p80-90 | 61/96 (19 buyers) | 18.3% | 2.269 | | |
| K6 award >= 95 % of reserve within p90-95 | 20/34 (12 buyers) | 18.9% | 2.263 | | |
| K6 award >= 95 % of reserve within p95-98 | 18/19 (6 buyers) | 32.6% | 1.574 | | |
| K6 award >= 95 % of reserve within p98-99 | 13/13 (2 buyers) | 37.7% | 1.271 | | |
| K6 award >= 95 % of reserve within >=p99 | 23/26 (6 buyers) | 43.5% | 1.429 | | |
