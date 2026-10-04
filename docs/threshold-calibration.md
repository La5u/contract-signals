# Threshold calibration

This offline study follows the proxy-outcome approach described by Fazekas &
Kocsis (2020) and the Government Transparency Institute CRI method. It is a
local implementation, not a replication of their published estimates. Single
bidding in an explicitly competitive procedure is a proxy for restricted
competition, not evidence of corruption. Countries are estimated separately.

## Rule declared before estimation

Use ordinary, low-input bins as references, chosen without inspecting outcomes:
the lowest bin for delay, duration, concentration and amount increase; the
longest bin for submission periods. Merge adjacent sparse bins deterministically
until each has at least 30 rows and 5 single-bid events (also 5 non-events for
estimability), or only one bin remains. Preserve original edges in the output.

A threshold is the lower edge of the first high-input bin whose adjusted odds
ratio (OR) has a lower 95% confidence limit above 1, with at least 30 rows and
5 events. Every bin above it must also meet these conditions and its OR must
not decrease. For short submission periods, reverse the ordering and use the
upper edge: flag values strictly below that edge. The primary model includes
buyer fixed effects, which are separate intercepts for buyers with at least 20
usable rows; smaller buyers share an "other" intercept. A recommendation also
requires an identifiable, converged, unpenalized model, at least 20 independent
buyer clusters and adequate residual degrees of freedom. These extra safeguards
prevent a handful of buyers or regularization from manufacturing a threshold.

Otherwise report "insufficient evidence: keep editorial threshold". If inference
is usable but no qualifying positive region exists, report "no association:
consider dropping/demoting in this jurisdiction"; this means no supported
association under this rule, not proof of independence. Estimates are exploratory
and confidence intervals are not adjusted for multiple comparisons.

## Estimation and reproduction

Run `PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python tools/calibrate-thresholds.py`
and `PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python -m unittest discover -s tests -p test_calibrate_thresholds.py`.
The tool writes only `research/thresholds/results.json` by default and prints a
compact table. `--generated-at TEXT` optionally records an explicit provenance
date; otherwise there is no timestamp. Input SHA-256 hashes, tool version and
dependency versions are recorded. No network is used and scoring is not changed.

Positive integer offers define the outcome: 1 means single bid, 2 or more means
multiple bids. Unknown competitiveness, unknown/zero/noninteger offers,
unverified or synthetic rows, conflicting histories, ambiguous DECP identities,
browse-only records and aggregate/documentary records are excluded. Duplicate
DECP buyer/contract identities are detected within each loaded cohort, as in
the site. France pools BOAMP and two DECP cohorts with cohort controls; Paraguay
pools its two disjoint buyer cohorts with cohort controls to retain information.
No countries are pooled.

Controls are log(amount), centered and scaled separately within each currency,
currency intercepts, CPV division (first two digits), year and cohort. Missing
amounts use the currency median plus a missingness indicator; unknown CPV/year
remain explicit categories. CPV/year levels with fewer than 20 rows or fewer
than 5 events/non-events are pooled to reduce separation. Both models with and
without buyer effects are reported; redundant columns are removed by an ordered
rank check, retaining input-bin terms first. No amount threshold is tested.

Logistic regression estimates the probability of a single bid. An OR above 1
means higher adjusted odds relative to the reference bin. Wald standard errors
come from the likelihood Hessian (curvature at the optimum). With at least 20
buyers, use a buyer-cluster sandwich covariance, allowing observations from the
same buyer to be correlated, with a finite-sample correction. With fewer buyers,
report Hessian intervals descriptively and withhold recommendations. If a
separated or unstable ordinary fit requires ridge regularization (a small
coefficient penalty), report penalized estimates and approximate Hessian
intervals, withhold recommendations, and omit AIC comparisons.

Publication delay is publication date minus contract date; negative delays are
dropped. Buyer-relative delay subtracts the median of the buyer's other clean,
nonnegative dated rows within the same cohort (at least 10 dated rows including
the focal row), including rows without usable outcomes. This keeps BOAMP
conclusion dates and DECP notification dates from sharing a baseline and matches
the site's per-dataset preparation. Raw and relative delay are compared on the
same rows using adjusted-model AIC: smaller is better in-sample fit after a
parameter-count penalty, not evidence of better future predictions. Differences
under 2 points are reported as indeterminate; penalized fits are not compared.

Concentration is the winning supplier's share among identified other rows in
the same cohort, buyer and CPV3 group. Require at least 10 identified *other*
rows and 80% identity coverage among other rows. Use identifiers only, French
SIREN where available, no supplier-name matching and no category substituted for
missing CPV. This is retrospective leave-one-row-out context; same-procedure
lots can still be dependent and future awards remain in the context.

French bidding periods must satisfy the site's complete linked initial/correction
notice chronology, open non-accelerated procedure and explicit deadline timezone.
The three selected French JSON files contain no such chronology. Paraguay has
`tenderPeriodDays`, used as published. Award dates or Ukraine's `tenderCreated`
alone cannot establish a submission period. DECP amount increases use the site's
fixed-firm-price, consistent initial/latest modification checks. No published
modification means unknown, not zero increase. This is post-award validation,
never a pre-award cause.

Weight hints use a separate adjusted binary-region fit to obtain the flagged
region's log-OR relative to the reference. Scale by the strongest supported
region log-OR within the country to the existing family's maximum *entry*
weight: competition 18, execution 8, transparency 8 (the first triggered weight,
not the maximum graduated weight). Unsupported or penalized fits have no hint.
Hints are not applied and cannot calibrate the single-offer check itself.

## Limitations

TED and UK cover above-threshold notices (UK also Procurement Act notices).
These selected cohorts are not national random samples. Missing offer counts,
limited buyers, rare flags and sparse merged bins limit power and precision.
Buyer clustering does not resolve all cross-buyer or duplicated-notice dependence.
UK dates can describe an original modified contract or admission to a purchasing
system, so UK delay estimates cannot establish a publication rule. Chile dates
are award dates; Paraguay dates are contract start dates without signatures.
Colombia SECOP II has no offer counts and is out of scope. Controls do not make
associations causal. Duration may correlate with procurement design; publication
delay and amount increase occur after bidding. Concentration is retrospective
and cannot yet support a prospective warning without a historical-only rerun.

## Results

The bundled data yields **no supported replacement threshold**. France has
estimable delay and duration contrasts, but no supported monotone positive
region. Every other country's candidates have insufficient evidence or missing
inputs. Nothing is applied to the site; every weight hint is null because no
flagged region qualifies. The full bin counts, ORs, confidence intervals, both
model specifications and file hashes are in
[`research/thresholds/results.json`](../research/thresholds/results.json).

"No association" below means no supported positive region under the declared
rule. "Insufficient" preserves an existing editorial threshold, if one exists,
and does not authorize adding a check currently out of scope. Bin intervals are
lower-inclusive and upper-exclusive; null JSON edges mean unbounded intervals.
The country denominator includes all usable outcomes, while each input uses
only rows where that input is available.

| Jurisdiction | Eligible rows | Single bids | Base rate | Recommended replacement |
| --- | ---: | ---: | ---: | --- |
| France | 2,189 | 412 | 18.8% | None; review/demote delay and duration, keep other editorial checks pending evidence |
| Portugal | 386 | 64 | 16.6% | None; insufficient |
| Romania | 341 | 132 | 38.7% | None; insufficient |
| Czechia | 372 | 92 | 24.7% | None; insufficient |
| UK | 1,051 | 20 | 1.9% | None; insufficient; delay dates not comparable |
| Chile | 519 | 71 | 13.7% | None; candidate inputs unavailable |
| Ukraine | 64 | 38 | 59.4% | None; insufficient |
| Paraguay | 263 | 85 | 32.3% | None; insufficient |
| Colombia | — | — | — | Out of scope: no offer counts |

### France

6,874 source rows; 527 conflicting histories, 5 aggregate/documentary rows,
2,413 noncompetitive/unknown-procedure rows and 1,740 unusable offer counts
excluded. Five further rows have negative publication delay.

| Input | n / events | Merged bins | Finding |
| --- | ---: | ---: | --- |
| Publication delay | 2,184 / 412 | 5 | No association; consider demotion |
| Buyer-relative delay | 1,285 / 234 | 5 | No association; consider demotion |
| Duration | 1,340 / 244 | 4 | No association; consider demotion |
| Submission period | 0 / 0 | 0 | Insufficient; linked chronology absent |
| Concentration | 714 / 125 | 2 | Insufficient; 14 buyers, regularization required |
| DECP amount increase | 22 / 4 | 1 | Insufficient; validation only |

With buyer effects and clustered intervals, raw delay of 121–240 days has OR
0.93 (95% CI 0.53–1.63), and 241+ days OR 0.58 (0.26–1.29), relative to 0–30
days. Relative excess of 121+ days has OR 0.99 (0.48–2.04), relative to negative
excess. Duration 48+ months has OR 0.51 (0.08–3.21), relative to under 12
months: its wide interval and merging of 120+ months into 48+ prevent a precise
test of the existing ten-year cutoff.

On the same 1,285 rows, raw-delay AIC is **1063.28**, versus **1071.03** for
relative delay (difference 7.76 in favor of raw delay). Both are ordinary fits
with buyer effects and 27 buyer clusters. This does **not support the proposed
buyer-relative switch** on the single-bid proxy. It also does not validate the
absolute 120-day threshold: neither measure yields a supported positive region.
Transparency may have a purpose separate from predicting restricted competition.

Concentration at 40%+ has descriptive penalized OR 3.70 (1.90–7.18), but
regularization and only 14 buyers prohibit a threshold. It should not be
presented as a calibrated 40% entry rule.

### Portugal

| Input | n / events | Merged bins | Finding |
| --- | ---: | ---: | --- |
| Publication delay | 386 / 64 | 1 | Insufficient; sparse tail merged into reference |
| Buyer-relative delay | 386 / 64 | 2 | Insufficient; 2 buyers |
| Duration | 21 / 8 | 1 | Insufficient |
| Concentration | 255 / 37 | 1 | Insufficient |

Submission period and DECP increase are unavailable. Relative-delay OR is 1.30
(0.72–2.38) for nonnegative versus negative excess, descriptively. Raw delay
has no identifiable contrast, so the raw/relative comparison is indeterminate.

### Romania

| Input | n / events | Merged bins | Finding |
| --- | ---: | ---: | --- |
| Publication delay | 341 / 132 | 2 | Insufficient; 3 buyers |
| Buyer-relative delay | 341 / 132 | 3 | Insufficient; 3 buyers |
| Duration | 269 / 93 | 3 | Insufficient; 3 buyers |
| Concentration | 209 / 87 | 2 | Insufficient; 2 buyers |

Submission period and DECP increase are unavailable. Shared-row AIC is 430.22
for raw delay and 428.76 for relative delay: difference 1.47, below the declared
2-point comparison margin. No preference is established and no rule is supported.

### Czechia

| Input | n / events | Merged bins | Finding |
| --- | ---: | ---: | --- |
| Publication delay | 372 / 92 | 2 | Insufficient; 3 buyers |
| Buyer-relative delay | 372 / 92 | 3 | Insufficient; 3 buyers |
| Duration | 102 / 32 | 2 | Insufficient; 3 buyers |
| Concentration | 184 / 41 | 3 | Insufficient; 3 buyers and regularization |

Submission period and DECP increase are unavailable. Duration 24+ months has
descriptive OR 129.88 (3.84–4396.86). The enormous interval and three buyers
prevent treating it as a validated threshold. Raw/relative AIC differs by only
0.30 (387.72 versus 387.42), so the comparison is indeterminate.

### UK

| Input | n / events | Merged bins | Finding |
| --- | ---: | ---: | --- |
| Publication delay | 1,051 / 20 | 1 | Insufficient; contract date meaning unreliable |
| Buyer-relative delay | 1,051 / 20 | 1 | Insufficient; contract date meaning unreliable |
| Concentration | 1,005 / 17 | 1 | Insufficient; sparse bins collapse |

Duration, submission period and DECP increase are unavailable. Only 20 single-bid
outcomes remain; no bin contrast survives the declared minimum counts. No AIC
comparison is possible. Delay must remain descriptive even with more rows.

### Chile

| Input | n / events | Finding |
| --- | ---: | --- |
| All six candidates | 0 / 0 | Insufficient: required input fields absent |

The 519 usable outcomes do not supply publication dates, duration or submission
chronology. Supplier categories are UNSPSC, not CPV; substituting them would
change the specified concentration input. No threshold can be estimated.

### Ukraine

| Input | n / events | Merged bins | Finding |
| --- | ---: | ---: | --- |
| Concentration | 5 / 4 | 1 | Insufficient |
| Other five candidates | 0 / 0 | 0 | Required fields absent |

424 reporting records have unknown competitiveness and are excluded. Only 64
competitive rows remain. `tenderCreated` plus contract date describes the whole
procurement timeline, not the time available to submit bids; it is not used.

### Paraguay

| Input | n / events | Merged bins | Finding |
| --- | ---: | ---: | --- |
| Submission period | 263 / 85 | 4 | Insufficient; 4 buyers |
| Other five candidates | 0 / 0 | 0 | Required fields absent |

The two cohorts cover different buyers and are pooled with a cohort control.
The site-equivalent count checks exclude mismatched tenderer lists and
multi-lot counts that cannot determine single bidding per lot: 111 unusable
counts and 3 noncompetitive/unknown procedures are excluded. Under 15 days has
descriptive OR 1.78 (0.49–6.43) versus 31+ days. No supported short-period
threshold exists. Call publication before contract start is not contract
publication and is not substituted into publication delay. No CPV concentration
is calculated from the national goods/works/services categories.

### National DECP (2026-10-04)

Source: [france-national.md](../research/thresholds/france-national.md) (national DECP, 210,018 competitive contracts, 8,702 buyers).

- **Buyer-relative publication delay**: the excess over the buyer's usual delay is first reliably associated with single bidding from 241 days (OR 1.14 [1.01, 1.29]), 1.71 [1.32, 2.22] beyond 730 days; the raw delay shows no association. Recommended entry at 241 days or more; applied in score 3.3 for the DECP family (excess above 240 days).
- **Concentration risk**: elevated from 40 % (OR 1.56 [1.25, 1.95]), rising to 3.68 at 80-90 %. The predeclared monotone rule yields only 90 % or more because the 60-70 % bin dips (OR 1.34 [0.86, 2.10]). The editorial 60 % entry is kept pending an owner decision.
- **Duration**: inversely associated (OR about 0.54-0.68 for 12 months or more), so not evidence for the long-duration check.
- **Amount increase**: no association.
- **MAPA**: no eligible outcomes.
- **Separation fix**: one buyer with 913 rows and zero single bids caused a separation issue in the model; handled in the analysis.

## Validation

13 unittest cases passed. Synthetic data recovers a known adjusted jump at
121 days with buyer clustering; a null input yields no recommendation; a short
submission-period jump uses the correct upper edge. Tests also cover sparse-bin
merging, outcome exclusions, DNCP lot normalization, duplicate DECP identities,
leave-one-out concentration and median baselines, cohort isolation, post-award
amount checks, few-buyer suppression and deterministic serialization. A complete
second run was compared byte-for-byte with the generated results.
