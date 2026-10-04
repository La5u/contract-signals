# France national DECP: threshold research

Tool 1.1.0; offline snapshot SHA-256 `cf74340145074271320e8bc92de37711d4df0974844e635d87184217555784ee`. Dataset `608c055b35eb4e6ee20eb325`, licence `lov2`.

Source: 3,308,334 contract-version-holder rows. Clean initial-state context: 1,506,874 contracts. Outcome cohort: 210,018 contracts, 8,702 buyers, 43,694 single bids (20.8%).

## Method and deviations

One contract is buyer identifier + contract identifier. modification_id=0 is the initial state; positive indices are modifications. Null indices lack usable notification dates in this snapshot and are excluded. donneesActuelles marks the current/latest state, not initial eligibility: false initial states remain eligible. Exact procurement snapshots are deduplicated across sources, ignoring source metadata, uid, current-state and geographical enrichments. All differing procurement snapshots in an initial identity group are excluded; no arbitrary version is selected. Raw amounts, dates, description and holder identity participate in conflict checks. Differing holders are conservatively excluded too: flattened coholder rows cannot reliably be distinguished from changed-supplier versions. No amounts are summed.

Dates: initial notification 2019-01-01 through 2026-09-01 inclusive. Positive montant_rationalise (raw fallback only when missing) controls amount; all suspect/aberrant amounts are dropped, even when unchanged by rationalisation. Inspection found cleaned and raw amounts equal on all non-anomalous rows. Missing CPV2 is an explicit unknown category.

Outcome: offresRecues=1 versus integer offresRecues>=2 among procedures for which tools/import-decp-cities.py direct() is exactly false; tools/import-decp-paris-ardeche.py imports the same map. Exact supported labels: open/restricted calls for tender, Procédure avec négociation, Dialogue compétitif. MAPA/Procédure adaptée maps to unknown and is excluded, as are alternative spellings and other negotiated labels absent from the importer. This is a mapping limitation, not a claim those procedures lack competition. Formal calls are analysed separately; other explicitly competitive procedures are also reported. MAPA has coverage counts only, because it has no eligible outcome under the requested importer rule.

All context uses clean initial contracts before outcome/procedure filtering. Publication delay is publication minus notification; negative delays are missing for this input. Buyer-relative delay subtracts the exact leave-one-out buyer median, with at least 10 nonnegative dated contracts in the buyer group. Duration is nonnegative months. Concentration is the focal supplier's share in buyer × CPV3, leaving the focal contract out: at least 10 known-supplier peers and 80% known-supplier coverage, matching the calibration helper's conservative guard. Valid SIRETs collapse to SIREN; other identifiers retain type. The fine bins are [0,40), [40,50), [50,60), [60,70), [70,80), [80,90), [90,100]% (100% belongs to the last bin). This is a full-window retrospective context, not information available at award time.

tools/calibrate-thresholds.py is imported unchanged for binning, adjacent sparse-bin merges (n>=30, >=5 events and >=5 non-events), logistic fitting, buyer-cluster sandwich covariance with CR1 correction, and its predeclared monotone significant-tail recommendation rule. Odds ratios (ORs) compare each bin with the first supported bin; confidence intervals (CIs) are 95%. Controls: centered/scaled log(amount EUR), CPV2 and notification year. Constant currency/cohort controls drop out. CPV2/year levels need >=50 rows, >=5 events and >=5 non-events; every buyer meeting >=200 rows and the same outcome-support requirement receives a separate level, with no cap. Unsupported levels are pooled. If the pooled category itself lacks support, it absorbs the largest supported level; renaming a zero-event level alone would retain separation. All observations and buyer clusters remain. The legacy design retained zero-event buyer levels, producing separated coefficients and triggering L2 despite optimizer convergence. These are pooled buyer effects rather than full buyer adjustment; residual buyer differences may confound associations. Where no buyer meets these requirements, the primary specification has no separate buyer levels; inspect the reported FE coverage. An input-first Gram-matrix rank check using incremental Cholesky removes aliased controls while retaining input terms; fitted likelihood and covariance still use the imported functions. Non-intercept columns are globally centered to avoid a large-sample intercept-gradient stall. This is an equivalent intercept reparameterization: likelihood, bin odds ratios and their cluster intervals are preserved; it is not within-buyer demeaning. Per-row logistic losses and their reduction are calculated in extended precision to avoid cancellation of tiny Newton improvements in large samples. The imported gradient, Hessian, convergence/fallback checks, L2 penalty, recommendation rule and cluster covariance are unchanged. The model without buyer fixed effects is reported as sensitivity. Penalized or unstable fits cannot support recommendations. No supplier/buyer coefficient names or identifiers are exported.

Each input is fitted separately on rows with that input; denominators differ. Candidate flag counts show both assessable and full eligible shares. The original statistical rule is preserved separately; a majority-flagging candidate is rejected as an outlier red flag, and >30% coverage requires policy review. Multiple inputs/bins are exploratory and are not corrected for multiple testing; no scoring thresholds or weights are changed.

Amount increases are validation only: firm-price initial contracts, published modifications, no conflicts, nondecreasing latest amount, valid dates and stable known supplier. Latest means highest published modification index, because the national table exposes states rather than a separate validated amendment date field. Revised amounts are new totals, never added. Absence of modification does not mean zero increase. Submission period is absent from DECP; award/publication dates cannot substitute for submission chronology.

## Exclusions and inspection

| Stage/count | Number |
|---|---:|
| amount_anomaly_groups_excluded | 26,513 |
| clean_context_contracts | 1,506,874 |
| conflicting_initial_groups_excluded | 149,632 |
| conflicting_unique_initial_snapshots_excluded | 489,137 |
| duplicate_initial_snapshots_removed | 0 |
| duplicate_modification_snapshots_removed | 0 |
| initial_contract_groups | 1,773,358 |
| initial_rows | 2,112,869 |
| missing_identity_rows | 6 |
| missing_or_nonpositive_amount_groups_excluded | 61,798 |
| modification_conflict_groups | 150,687 |
| modification_only_contract_groups | 0 |
| modification_rows | 1,163,609 |
| outside_date_window_groups_excluded | 28,541 |
| source_rows | 3,308,334 |
| unversioned_rows_excluded | 31,856 |
| outcome: not_explicitly_competitive | 995,157 |
| outcome: unusable_offer_count | 301,699 |

Counts are sequential within initial-group exclusions; raw duplicate/modification/uid diagnostics are separate, overlapping units and must not be added to contract exclusions.

### Initial/current state cross-tab

| State / donneesActuelles | Rows |
|---|---:|
| initial / False | 411,860 |
| initial / True | 1,701,009 |
| modification / False | 737,745 |
| modification / True | 425,864 |
| unversioned / None | 31,856 |

### Procedure labels (all source rows)

| Label | Rows |
|---|---:|
| (missing) | 153,435 |
| Appel d offres ouvert | 9,998 |
| Appel d offres restreint | 516 |
| Appel d'offres ouvert | 1,207,530 |
| Appel d'offres restreint | 36,240 |
| Appel d’offres ouvert | 292 |
| Appel d’offres restreint | 122 |
| Dialogue compétitif | 24,265 |
| Marché négocié sans publicité ni mise en concurrence préalable | 29,040 |
| Marché passé sans publicité ni mise en concurrence préalable | 84,893 |
| Marché public négocié sans publicité ni mise en concurrence préalable | 5,973 |
| Procedure concurrentielle avec negociation | 622 |
| Procédure adaptée | 1,663,265 |
| Procédure avec négociation | 61,686 |
| Procédure concurrentielle avec négociation | 15,235 |
| Procédure négociée avec mise en concurrence préalable | 15,221 |
| Procédure négociée restreinte | 1 |

### Procedure coverage

| Family | Clean contracts | Usable offers | Outcome eligible | Single bid |
|---|---:|---:|---:|---:|
| adapted | 809,839 | 296,126 | 0 | 0 |
| direct | 57,180 | 33,111 | 0 | 0 |
| formal_calls | 495,413 | 199,368 | 199,368 | 40,977 |
| other_competitive | 16,304 | 10,650 | 10,650 | 2,717 |
| unknown | 128,138 | 69,087 | 0 | 0 |

## Results: overall

Eligible n=210,018; buyers=8,702; events=43,694.

### publication_delay_days

Recommendation: **no_association**. no association: consider dropping/demoting in this jurisdiction

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|
| [0, 31) | 102,114 | 21,035 | 20.6% | 1.00 [1.00, 1.00] |
| [31, 61) | 25,645 | 5,522 | 21.5% | 1.10 [1.01, 1.19] |
| [61, 121) | 22,882 | 5,184 | 22.7% | 1.16 [1.07, 1.25] |
| [121, 241) | 17,924 | 3,939 | 22.0% | 1.10 [1.01, 1.21] |
| [241, 731) | 19,210 | 4,271 | 22.2% | 1.09 [0.91, 1.31] |
| [731, +inf) | 15,171 | 2,079 | 13.7% | 1.14 [0.91, 1.44] |

without_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=202,946, parameters=58; FE levels=0, FE rows=0.

with_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=202,946, parameters=203; FE levels=145, FE rows=65,016.

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 31 | 100,832 | 49.7% | 48.0% | yes |
| 61 | 75,187 | 37.0% | 35.8% | yes |
| 121 | 52,305 | 25.8% | 24.9% | no |
| 241 | 34,381 | 16.9% | 16.4% | no |
| 731 | 15,171 | 7.5% | 7.2% | no |

- No supported monotone positive region; this is not proof of a null effect.

### buyer_relative_delay_days

Recommendation: **recommend**. candidate threshold buyer_relative_delay_days >= 241

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|
| [-inf, 0) | 84,345 | 18,249 | 21.6% | 1.00 [1.00, 1.00] |
| [0, 31) | 50,284 | 9,872 | 19.6% | 1.01 [0.94, 1.08] |
| [31, 61) | 13,555 | 2,711 | 20.0% | 1.03 [0.92, 1.16] |
| [61, 121) | 14,150 | 2,939 | 20.8% | 1.08 [0.96, 1.22] |
| [121, 241) | 12,046 | 2,700 | 22.4% | 1.16 [0.96, 1.41] |
| [241, 731) | 13,848 | 2,811 | 20.3% | 1.14 [1.01, 1.29] |
| [731, +inf) | 10,480 | 1,618 | 15.4% | 1.71 [1.32, 2.22] |

without_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=198,708, parameters=59; FE levels=0, FE rows=0.

with_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=198,708, parameters=204; FE levels=145, FE rows=65,016.

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 0 | 114,363 | 57.6% | 54.5% | yes |
| 31 | 64,079 | 32.2% | 30.5% | yes |
| 61 | 50,524 | 25.4% | 24.1% | no |
| 121 | 36,374 | 18.3% | 17.3% | no |
| 241 | 24,328 | 12.2% | 11.6% | no |
| 731 | 10,480 | 5.3% | 5.0% | no |


### duration_months

Recommendation: **no_association**. no association: consider dropping/demoting in this jurisdiction

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|
| [0, 12) | 18,874 | 4,751 | 25.2% | 1.00 [1.00, 1.00] |
| [12, 24) | 31,161 | 6,187 | 19.9% | 0.68 [0.59, 0.78] |
| [24, 48) | 41,715 | 8,679 | 20.8% | 0.67 [0.58, 0.77] |
| [48, 120) | 116,786 | 23,751 | 20.3% | 0.54 [0.47, 0.63] |
| [120, +inf) | 1,050 | 240 | 22.9% | 0.56 [0.43, 0.74] |

without_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=209,586, parameters=58; FE levels=0, FE rows=0.

with_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=209,586, parameters=216; FE levels=158, FE rows=69,662.

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 12 | 190,712 | 91.0% | 90.8% | yes |
| 24 | 159,551 | 76.1% | 76.0% | yes |
| 48 | 117,836 | 56.2% | 56.1% | yes |
| 120 | 1,050 | 0.5% | 0.5% | no |

- No supported monotone positive region; this is not proof of a null effect.

### submission_period_days

Recommendation: **insufficient_evidence**. insufficient evidence: keep editorial threshold

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 10 | 0 | unavailable | 0.0% | no |
| 15 | 0 | unavailable | 0.0% | no |
| 22 | 0 | unavailable | 0.0% | no |
| 31 | 0 | unavailable | 0.0% | no |
| 53 | 0 | unavailable | 0.0% | no |

- Input not reliably derivable in eligible bundled rows; no model fitted.
- DECP has no submission deadline or validated submission-period input.

### supplier_concentration_share

Recommendation: **recommend**. candidate threshold supplier_concentration_share >= 0.9

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|
| [0, 0.4) | 101,543 | 18,120 | 17.8% | 1.00 [1.00, 1.00] |
| [0.4, 0.5) | 2,479 | 743 | 30.0% | 1.56 [1.25, 1.95] |
| [0.5, 0.6) | 2,495 | 1,156 | 46.3% | 1.76 [1.31, 2.37] |
| [0.6, 0.7) | 1,072 | 296 | 27.6% | 1.34 [0.86, 2.10] |
| [0.7, 0.8) | 689 | 289 | 41.9% | 2.14 [1.29, 3.53] |
| [0.8, 0.9) | 634 | 312 | 49.2% | 3.68 [2.09, 6.49] |
| [0.9, +inf) | 821 | 408 | 49.7% | 2.30 [1.44, 3.68] |

without_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=109,733, parameters=55; FE levels=0, FE rows=0.

with_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=109,733, parameters=136; FE levels=81, FE rows=40,417.

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 0.4 | 8,190 | 7.5% | 3.9% | no |
| 0.5 | 5,711 | 5.2% | 2.7% | no |
| 0.6 | 3,216 | 2.9% | 1.5% | no |
| 0.7 | 2,144 | 2.0% | 1.0% | no |
| 0.8 | 1,455 | 1.3% | 0.7% | no |
| 0.9 | 821 | 0.7% | 0.4% | no |


### decp_amount_increase_percent

Recommendation: **no_association**. no association: consider dropping/demoting in this jurisdiction

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|
| [0, 10) | 4,080 | 1,266 | 31.0% | 1.00 [1.00, 1.00] |
| [10, 20) | 255 | 54 | 21.2% | 0.62 [0.45, 0.86] |
| [20, 40) | 188 | 41 | 21.8% | 0.63 [0.43, 0.91] |
| [40, 100) | 122 | 36 | 29.5% | 0.82 [0.54, 1.25] |
| [100, +inf) | 311 | 103 | 33.1% | 0.78 [0.56, 1.08] |

without_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=4,956, parameters=32; FE levels=0, FE rows=0.

with_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=4,956, parameters=32; FE levels=0, FE rows=0.

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 10 | 876 | 17.7% | 0.4% | no |
| 20 | 621 | 12.5% | 0.3% | no |
| 40 | 433 | 8.7% | 0.2% | no |
| 100 | 311 | 6.3% | 0.1% | no |

- No supported monotone positive region; this is not proof of a null effect.
- Post-award validation only: no modification is not zero increase; latest published positive modification index used, not inferred chronology.

## Results: formal_calls

Eligible n=199,368; buyers=8,361; events=40,977.

### publication_delay_days

Recommendation: **no_association**. no association: consider dropping/demoting in this jurisdiction

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|
| [0, 31) | 97,109 | 19,740 | 20.3% | 1.00 [1.00, 1.00] |
| [31, 61) | 24,378 | 5,244 | 21.5% | 1.12 [1.03, 1.22] |
| [61, 121) | 21,802 | 4,870 | 22.3% | 1.15 [1.06, 1.25] |
| [121, 241) | 16,958 | 3,705 | 21.8% | 1.11 [1.01, 1.22] |
| [241, 731) | 18,146 | 4,010 | 22.1% | 1.10 [0.91, 1.33] |
| [731, +inf) | 14,274 | 1,920 | 13.5% | 1.13 [0.88, 1.44] |

without_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=192,667, parameters=58; FE levels=0, FE rows=0.

with_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=192,667, parameters=194; FE levels=136, FE rows=61,048.

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 31 | 95,558 | 49.6% | 47.9% | yes |
| 61 | 71,180 | 36.9% | 35.7% | yes |
| 121 | 49,378 | 25.6% | 24.8% | no |
| 241 | 32,420 | 16.8% | 16.3% | no |
| 731 | 14,274 | 7.4% | 7.2% | no |

- No supported monotone positive region; this is not proof of a null effect.

### buyer_relative_delay_days

Recommendation: **recommend**. candidate threshold buyer_relative_delay_days >= 241

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|
| [-inf, 0) | 80,225 | 17,248 | 21.5% | 1.00 [1.00, 1.00] |
| [0, 31) | 47,938 | 9,246 | 19.3% | 1.00 [0.93, 1.08] |
| [31, 61) | 12,834 | 2,526 | 19.7% | 1.03 [0.91, 1.17] |
| [61, 121) | 13,492 | 2,760 | 20.5% | 1.09 [0.96, 1.23] |
| [121, 241) | 11,382 | 2,540 | 22.3% | 1.16 [0.95, 1.43] |
| [241, 731) | 12,985 | 2,616 | 20.1% | 1.15 [1.02, 1.30] |
| [731, +inf) | 9,881 | 1,502 | 15.2% | 1.69 [1.28, 2.23] |

without_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=188,737, parameters=59; FE levels=0, FE rows=0.

with_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=188,737, parameters=195; FE levels=136, FE rows=61,048.

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 0 | 108,512 | 57.5% | 54.4% | yes |
| 31 | 60,574 | 32.1% | 30.4% | yes |
| 61 | 47,740 | 25.3% | 23.9% | no |
| 121 | 34,248 | 18.1% | 17.2% | no |
| 241 | 22,866 | 12.1% | 11.5% | no |
| 731 | 9,881 | 5.2% | 5.0% | no |


### duration_months

Recommendation: **no_association**. no association: consider dropping/demoting in this jurisdiction

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|
| [0, 12) | 17,360 | 4,311 | 24.8% | 1.00 [1.00, 1.00] |
| [12, 24) | 29,061 | 5,661 | 19.5% | 0.68 [0.59, 0.78] |
| [24, 48) | 39,383 | 8,102 | 20.6% | 0.68 [0.59, 0.78] |
| [48, 120) | 112,249 | 22,615 | 20.1% | 0.56 [0.48, 0.65] |
| [120, +inf) | 911 | 209 | 22.9% | 0.57 [0.42, 0.76] |

without_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=198,964, parameters=58; FE levels=0, FE rows=0.

with_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=198,964, parameters=205; FE levels=147, FE rows=65,091.

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 12 | 181,604 | 91.3% | 91.1% | yes |
| 24 | 152,543 | 76.7% | 76.5% | yes |
| 48 | 113,160 | 56.9% | 56.8% | yes |
| 120 | 911 | 0.5% | 0.5% | no |

- No supported monotone positive region; this is not proof of a null effect.

### submission_period_days

Recommendation: **insufficient_evidence**. insufficient evidence: keep editorial threshold

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 10 | 0 | unavailable | 0.0% | no |
| 15 | 0 | unavailable | 0.0% | no |
| 22 | 0 | unavailable | 0.0% | no |
| 31 | 0 | unavailable | 0.0% | no |
| 53 | 0 | unavailable | 0.0% | no |

- Input not reliably derivable in eligible bundled rows; no model fitted.
- DECP has no submission deadline or validated submission-period input.

### supplier_concentration_share

Recommendation: **recommend**. candidate threshold supplier_concentration_share >= 0.9

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|
| [0, 0.4) | 96,327 | 16,814 | 17.5% | 1.00 [1.00, 1.00] |
| [0.4, 0.5) | 2,386 | 702 | 29.4% | 1.52 [1.22, 1.90] |
| [0.5, 0.6) | 2,453 | 1,150 | 46.9% | 1.84 [1.36, 2.51] |
| [0.6, 0.7) | 953 | 253 | 26.5% | 1.28 [0.86, 1.92] |
| [0.7, 0.8) | 686 | 288 | 42.0% | 2.16 [1.31, 3.55] |
| [0.8, 0.9) | 608 | 301 | 49.5% | 3.71 [2.07, 6.67] |
| [0.9, +inf) | 789 | 384 | 48.7% | 2.21 [1.38, 3.55] |

without_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=104,202, parameters=54; FE levels=0, FE rows=0.

with_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=104,202, parameters=129; FE levels=75, FE rows=37,781.

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 0.4 | 7,875 | 7.6% | 3.9% | no |
| 0.5 | 5,489 | 5.3% | 2.8% | no |
| 0.6 | 3,036 | 2.9% | 1.5% | no |
| 0.7 | 2,083 | 2.0% | 1.0% | no |
| 0.8 | 1,397 | 1.3% | 0.7% | no |
| 0.9 | 789 | 0.8% | 0.4% | no |


### decp_amount_increase_percent

Recommendation: **no_association**. no association: consider dropping/demoting in this jurisdiction

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|
| [0, 10) | 3,828 | 1,167 | 30.5% | 1.00 [1.00, 1.00] |
| [10, 20) | 236 | 50 | 21.2% | 0.62 [0.45, 0.86] |
| [20, 40) | 176 | 38 | 21.6% | 0.62 [0.42, 0.91] |
| [40, 100) | 107 | 31 | 29.0% | 0.81 [0.52, 1.26] |
| [100, +inf) | 298 | 99 | 33.2% | 0.79 [0.57, 1.10] |

without_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=4,645, parameters=30; FE levels=0, FE rows=0.

with_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=4,645, parameters=30; FE levels=0, FE rows=0.

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 10 | 817 | 17.6% | 0.4% | no |
| 20 | 581 | 12.5% | 0.3% | no |
| 40 | 405 | 8.7% | 0.2% | no |
| 100 | 298 | 6.4% | 0.1% | no |

- No supported monotone positive region; this is not proof of a null effect.
- Post-award validation only: no modification is not zero increase; latest published positive modification index used, not inferred chronology.

## Results: other_competitive

Eligible n=10,650; buyers=1,912; events=2,717.

### publication_delay_days

Recommendation: **no_association**. no association: consider dropping/demoting in this jurisdiction

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|
| [0, 31) | 5,005 | 1,295 | 25.9% | 1.00 [1.00, 1.00] |
| [31, 61) | 1,267 | 278 | 21.9% | 0.83 [0.65, 1.08] |
| [61, 121) | 1,080 | 314 | 29.1% | 1.22 [0.94, 1.59] |
| [121, 241) | 966 | 234 | 24.2% | 0.98 [0.76, 1.26] |
| [241, 731) | 1,064 | 261 | 24.5% | 1.06 [0.79, 1.43] |
| [731, +inf) | 897 | 159 | 17.7% | 1.12 [0.69, 1.80] |

without_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=10,279, parameters=39; FE levels=0, FE rows=0.

with_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=10,279, parameters=40; FE levels=1, FE rows=297.

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 31 | 5,274 | 51.3% | 49.5% | yes |
| 61 | 4,007 | 39.0% | 37.6% | yes |
| 121 | 2,927 | 28.5% | 27.5% | no |
| 241 | 1,961 | 19.1% | 18.4% | no |
| 731 | 897 | 8.7% | 8.4% | no |

- No supported monotone positive region; this is not proof of a null effect.

### buyer_relative_delay_days

Recommendation: **recommend**. candidate threshold buyer_relative_delay_days >= 731

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|
| [-inf, 0) | 4,120 | 1,001 | 24.3% | 1.00 [1.00, 1.00] |
| [0, 31) | 2,346 | 626 | 26.7% | 1.06 [0.82, 1.36] |
| [31, 61) | 721 | 185 | 25.7% | 1.06 [0.70, 1.61] |
| [61, 121) | 658 | 179 | 27.2% | 1.16 [0.86, 1.54] |
| [121, 241) | 664 | 160 | 24.1% | 1.02 [0.74, 1.39] |
| [241, 731) | 863 | 195 | 22.6% | 1.23 [0.86, 1.76] |
| [731, +inf) | 599 | 116 | 19.4% | 1.70 [1.06, 2.73] |

without_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=9,971, parameters=40; FE levels=0, FE rows=0.

with_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=9,971, parameters=41; FE levels=1, FE rows=297.

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 0 | 5,851 | 58.7% | 54.9% | yes |
| 31 | 3,505 | 35.2% | 32.9% | yes |
| 61 | 2,784 | 27.9% | 26.1% | no |
| 121 | 2,126 | 21.3% | 20.0% | no |
| 241 | 1,462 | 14.7% | 13.7% | no |
| 731 | 599 | 6.0% | 5.6% | no |


### duration_months

Recommendation: **no_association**. no association: consider dropping/demoting in this jurisdiction

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|
| [0, 12) | 1,514 | 440 | 29.1% | 1.00 [1.00, 1.00] |
| [12, 24) | 2,100 | 526 | 25.0% | 0.73 [0.49, 1.07] |
| [24, 48) | 2,332 | 577 | 24.7% | 0.72 [0.52, 1.00] |
| [48, 120) | 4,537 | 1,136 | 25.0% | 0.52 [0.35, 0.77] |
| [120, +inf) | 139 | 31 | 22.3% | 0.38 [0.19, 0.73] |

without_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=10,622, parameters=38; FE levels=0, FE rows=0.

with_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=10,622, parameters=39; FE levels=1, FE rows=297.

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 12 | 9,108 | 85.7% | 85.5% | yes |
| 24 | 7,008 | 66.0% | 65.8% | yes |
| 48 | 4,676 | 44.0% | 43.9% | yes |
| 120 | 139 | 1.3% | 1.3% | no |

- No supported monotone positive region; this is not proof of a null effect.

### submission_period_days

Recommendation: **insufficient_evidence**. insufficient evidence: keep editorial threshold

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 10 | 0 | unavailable | 0.0% | no |
| 15 | 0 | unavailable | 0.0% | no |
| 22 | 0 | unavailable | 0.0% | no |
| 31 | 0 | unavailable | 0.0% | no |
| 53 | 0 | unavailable | 0.0% | no |

- Input not reliably derivable in eligible bundled rows; no model fitted.
- DECP has no submission deadline or validated submission-period input.

### supplier_concentration_share

Recommendation: **recommend**. candidate threshold supplier_concentration_share >= 0.7

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|
| [0, 0.4) | 5,216 | 1,306 | 25.0% | 1.00 [1.00, 1.00] |
| [0.4, 0.5) | 93 | 41 | 44.1% | 3.16 [0.85, 11.73] |
| [0.5, 0.6) | 42 | 6 | 14.3% | 0.30 [0.06, 1.46] |
| [0.6, 0.7) | 119 | 43 | 36.1% | 1.77 [0.55, 5.69] |
| [0.7, +inf) | 61 | 36 | 59.0% | 2.84 [1.16, 6.97] |

without_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=5,531, parameters=26; FE levels=0, FE rows=0.

with_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=5,531, parameters=27; FE levels=1, FE rows=285.

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 0.4 | 315 | 5.7% | 3.0% | no |
| 0.5 | 222 | 4.0% | 2.1% | no |
| 0.6 | 180 | 3.3% | 1.7% | no |
| 0.7 | 61 | 1.1% | 0.6% | no |
| 0.8 | 58 | 1.0% | 0.5% | no |
| 0.9 | 32 | 0.6% | 0.3% | no |

- Adjacent sparse/empty bins merged; resolution is coarser than initial edges.

### decp_amount_increase_percent

Recommendation: **no_association**. no association: consider dropping/demoting in this jurisdiction

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|
| [0, 10) | 252 | 99 | 39.3% | 1.00 [1.00, 1.00] |
| [10, +inf) | 59 | 16 | 27.1% | 0.44 [0.20, 0.94] |

without_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=311, parameters=6; FE levels=0, FE rows=0.

with_buyer_fe: ok; buyer-cluster sandwich, CR1 finite-sample correction; n=311, parameters=6; FE levels=0, FE rows=0.

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 10 | 59 | 19.0% | 0.6% | no |
| 20 | 40 | 12.9% | 0.4% | no |
| 40 | 28 | 9.0% | 0.3% | no |
| 100 | 13 | 4.2% | 0.1% | no |

- Adjacent sparse/empty bins merged; resolution is coarser than initial edges.
- No supported monotone positive region; this is not proof of a null effect.
- Post-award validation only: no modification is not zero increase; latest published positive modification index used, not inferred chronology.

## Results: adapted

Eligible n=0; buyers=0; events=0.

### publication_delay_days

Recommendation: **insufficient_evidence**. insufficient evidence: keep editorial threshold

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 31 | 0 | unavailable | n/a | no |
| 61 | 0 | unavailable | n/a | no |
| 121 | 0 | unavailable | n/a | no |
| 241 | 0 | unavailable | n/a | no |
| 731 | 0 | unavailable | n/a | no |

- Input not reliably derivable in eligible bundled rows; no model fitted.

### buyer_relative_delay_days

Recommendation: **insufficient_evidence**. insufficient evidence: keep editorial threshold

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 0 | 0 | unavailable | n/a | no |
| 31 | 0 | unavailable | n/a | no |
| 61 | 0 | unavailable | n/a | no |
| 121 | 0 | unavailable | n/a | no |
| 241 | 0 | unavailable | n/a | no |
| 731 | 0 | unavailable | n/a | no |

- Input not reliably derivable in eligible bundled rows; no model fitted.

### duration_months

Recommendation: **insufficient_evidence**. insufficient evidence: keep editorial threshold

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 12 | 0 | unavailable | n/a | no |
| 24 | 0 | unavailable | n/a | no |
| 48 | 0 | unavailable | n/a | no |
| 120 | 0 | unavailable | n/a | no |

- Input not reliably derivable in eligible bundled rows; no model fitted.

### submission_period_days

Recommendation: **insufficient_evidence**. insufficient evidence: keep editorial threshold

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 10 | 0 | unavailable | n/a | no |
| 15 | 0 | unavailable | n/a | no |
| 22 | 0 | unavailable | n/a | no |
| 31 | 0 | unavailable | n/a | no |
| 53 | 0 | unavailable | n/a | no |

- Input not reliably derivable in eligible bundled rows; no model fitted.
- DECP has no submission deadline or validated submission-period input.

### supplier_concentration_share

Recommendation: **insufficient_evidence**. insufficient evidence: keep editorial threshold

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 0.4 | 0 | unavailable | n/a | no |
| 0.5 | 0 | unavailable | n/a | no |
| 0.6 | 0 | unavailable | n/a | no |
| 0.7 | 0 | unavailable | n/a | no |
| 0.8 | 0 | unavailable | n/a | no |
| 0.9 | 0 | unavailable | n/a | no |

- Input not reliably derivable in eligible bundled rows; no model fitted.

### decp_amount_increase_percent

Recommendation: **insufficient_evidence**. insufficient evidence: keep editorial threshold

| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |
|---|---:|---:|---:|---|

| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |
|---|---:|---:|---:|---|
| 10 | 0 | unavailable | n/a | no |
| 20 | 0 | unavailable | n/a | no |
| 40 | 0 | unavailable | n/a | no |
| 100 | 0 | unavailable | n/a | no |

- Input not reliably derivable in eligible bundled rows; no model fitted.
- Post-award validation only: no modification is not zero increase; latest published positive modification index used, not inferred chronology.

Analysis runtime: 460.4 seconds (including staging).

## Conclusions and limits

Single bid is a proxy for restricted competition, not corruption. National publication coverage is not a census of purchasing; offer-count reporting is selective and excludes many otherwise competitive records. Lots, framework contracts and reused contract IDs can affect units; conservative conflict exclusions reduce coverage. Full-window supplier shares and buyer medians use later contracts and should not be interpreted as prospective predictions. Publication delays can reflect batching, backfills or data correction. Long duration can be normal for the purchased service. No causal claim, legal-compliance finding or automatic site threshold change follows from these estimates.

A fine concentration curve should be assessed across all bins and procedure families, rather than selecting an isolated significant interval. The monotone-tail rule can yield a high threshold even when middle-bin risk starts increasing earlier, or no recommendation when the curve is nonmonotone. A >30% flag share describes a common pattern requiring review; a majority threshold is unsuitable for an outlier red flag. MAPA-specific thresholds cannot be learned without an explicit, validated change to the site's procedure/outcome mapping.
