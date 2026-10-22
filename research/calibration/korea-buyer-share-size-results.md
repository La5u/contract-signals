# South Korea: size control for G3, N4, K6 and the bid-level checks B2, B4, B5 (2026-10-20, rerun 2026-10-22 without amendment-only records and with bid checks)

Method and fixed bands: `tools/korea-buyer-share-size.py` docstring and [bias-controls-plan.md](bias-controls-plan.md). Decision rule set of [korea-collusion-results.md](korea-collusion-results.md) (buyer = contracting office). Points basis: size-standardised, rigged values / 1.3. K6 and B2/B4/B5 are sensitivities: their points come from the decision rule (lower than the size-standardised values here). B checks are known only for contracts whose opening is in the downloaded bid days (294 rigged, about 38,800 comparisons).

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
| B2 two or three bids unadjusted | 71% (151/294, 84 buyers) | 21.6% | 3.028 [2.44, 3.80] | 2.798 | 14.8 |
| B2 two or three bids size-standardised | 71% (151/294, 84.0 buyers) | 19.4% | 3.34 [2.73, 4.13] | 3.114 | 16.4 |
| B2 two or three bids size-standardised, rigged values / 1.3 (points basis) | 71% (151/294, 84.0 buyers) | 19.8% | 3.285 [2.71, 4.03] | 3.063 | 16.2 |
| B2 two or three bids within <p50 | 61/87 (54 buyers) | 22.4% | 3.016 | | |
| B2 two or three bids within p50-80 | 40/87 (21 buyers) | 15.6% | 2.939 | | |
| B2 two or three bids within p80-90 | 23/46 (15 buyers) | 9.9% | 4.093 | | |
| B2 two or three bids within p90-95 | 9/21 (9 buyers) | 16.5% | 1.936 | | |
| B2 two or three bids within p95-98 | 3/14 (7 buyers) | 23.2% | 1.076 | | |
| B2 two or three bids within p98-99 | 5/19 (5 buyers) | 17.8% | 1.743 | | |
| B2 two or three bids within >=p99 | 10/20 (7 buyers) | 20.7% | 1.159 | | |
| B4 low bid dispersion unadjusted | 18% (22/111, 31 buyers) | 8.7% | 1.728 [0.77, 2.86] | 1.368 | 4.5 |
| B4 low bid dispersion size-standardised | 18% (22/111, 31.0 buyers) | 8.9% | 1.695 [0.79, 2.88] | 1.355 | 4.4 |
| B4 low bid dispersion size-standardised, rigged values / 1.3 (points basis) | 18% (22/111, 31.0 buyers) | 8.6% | 1.736 [0.79, 2.94] | 1.383 | 4.7 |
| B4 low bid dispersion within <p50 | 1/20 (14 buyers) | 9.1% | 0.855 | | |
| B4 low bid dispersion within p50-80 | 11/42 (11 buyers) | 9.6% | 1.527 | | |
| B4 low bid dispersion within p80-90 | 3/19 (5 buyers) | 3.2% | 1.324 | | |
| B4 low bid dispersion within p90-95 | 5/11 (6 buyers) | 1.0% | 9.167 | | |
| B4 low bid dispersion within p95-98 | 1/3 (3 buyers) | 12.9% | 1.301 | | |
| B4 low bid dispersion within p98-99 | 0/12 (1 buyers) | 11.2% | 0.909 | | |
| B4 low bid dispersion within >=p99 | 1/4 (4 buyers) | 19.0% | 1.054 | | |
| B5 large first gap unadjusted | 34% (36/111, 31 buyers) | 9.9% | 2.765 [1.54, 4.46] | 2.312 | 12.1 |
| B5 large first gap size-standardised | 34% (36/111, 31.0 buyers) | 8.7% | 3.092 [1.75, 4.66] | 2.546 | 13.5 |
| B5 large first gap size-standardised, rigged values / 1.3 (points basis) | 34% (36/111, 31.0 buyers) | 8.9% | 3.022 [1.70, 4.62] | 2.493 | 13.2 |
| B5 large first gap within <p50 | 7/20 (14 buyers) | 10.3% | 2.505 | | |
| B5 large first gap within p50-80 | 7/42 (11 buyers) | 8.6% | 2.014 | | |
| B5 large first gap within p80-90 | 5/19 (5 buyers) | 6.2% | 2.872 | | |
| B5 large first gap within p90-95 | 4/11 (6 buyers) | 5.7% | 2.401 | | |
| B5 large first gap within p95-98 | 1/3 (3 buyers) | 2.8% | 2.375 | | |
| B5 large first gap within p98-99 | 12/12 (1 buyers) | 8.3% | 1.766 | | |
| B5 large first gap within >=p99 | 0/4 (4 buyers) | 11.8% | 0.714 | | |
