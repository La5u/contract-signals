# Offline weighting-method comparison

**Synthetic only. Verified real-world corruption labels in this experiment: zero.** Nothing here measures actual corruption-detection accuracy, validates the live index or establishes justified new point values. No website weights were changed.

## Reproduce

```sh
python -m unittest discover -s tests -p 'test_calibrate_indicators.py'
python tools/calibrate-indicators.py --output /tmp/contract-calibration-results.json
```

The offline tool requires optional NumPy, SciPy and scikit-learn, not website dependencies. Its tests skip when these libraries are unavailable. It never reads procurement datasets or changes the website. The output contains design assumptions, per-seed weights, metrics, discovery diagnostics and paired synthetic-seed bootstrap intervals.

## Design

Compared five fitted ranking pipelines across all 18 indicator kinds. Each of seven synthetic scenarios uses five deterministic seeds, 4,000 rows and 100 buyer groups, split into 60 training, 20 validation and 20 test groups. Training estimates weights; validation selects candidate settings; held-out test labels are never used for fitting. Buyer-level effects introduce grouped dependence.

- **Signal count:** simple unweighted reference.
- **Fixed family-max proxy:** representative constant/maximal graduated weights, not the actual scores of real contracts. New-check weights were 20/10/5/3/1 in this experiment; the website now uses a uniform 8-point placeholder (v3.2).
- **Nonnegative likelihood-ratio weights:** smoothed relative signal frequencies in positive/comparison training cases; select smoothing on validation.
- **Nonnegative regularized logistic ranking:** jointly estimates weights; selects regularization on validation. Outputs are uncalibrated rankings, not corruption probabilities.
- **Learned family-max:** searches bounded weights on training data, selects a candidate on validation; preserves competition/execution/transparency maxima and total cap.

AP (average precision) assesses ranking across retrieval depths; higher is better. AP and ROC AUC use raw scores and respect ties. Top-5% precision/recall gives fractional inclusion to tied boundary records. Five-seed standard deviations and bootstrap differences are simulation variability, not confidence in real-world detection.

## Results: mean held-out AP

| Invented scenario | Count | Fixed proxy | Likelihood ratio | Logistic | Learned family-max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Independent signals | .587 | .402 | .698 | .698 | .537 |
| Correlated signals | .456 | .348 | .535 | .560 | .441 |
| Family-max mechanism | .393 | .500 | .493 | .495 | .498 |
| Pair-interaction mechanism | .512 | .414 | .553 | .565 | .463 |
| Outcome-dependent missingness | .190 | .193 | .242 | .421 | .251 |
| Sector/population drift | .365 | .265 | .372 | .363 | .257 |
| Biased case discovery | .587 | .402 | .675 | .683 | .479 |

These compare particular pipelines, not proof that a general model class is superior. Logistic/LR were useful challengers in several invented scenarios; no method dominates. Simple count remained competitive under drift. Family-max performs best when the assumed data-generating mechanism itself uses the fixed family-max proxy: this is a deliberately disclosed built-in advantage, not validation of its points.

### Important limitations

- Rates, outcomes and distributions are invented. A method can exploit the simulation's assumptions.
- Missing-data preprocessing differs: logistic imputes training assessed means; LR estimates rates among assessed checks; count/family-max add no contribution for unknown checks. Logistic's missingness performance partly reflects its imputation advantage. **Do not display imputed signals or award contract-level points for absent evidence.**
- The high-coverage subset is selected by evidence availability and may have different outcome prevalence; it is a diagnostic, not an unbiased test population.
- Biased discovery is a narrow positive-unlabeled simulation: undiscovered synthetic positives are wrongly treated as negative training cases. It does not solve real investigative selection bias.
- Nonnegative coefficients cannot capture protective or complex nonlinear relationships; coefficients are conditional model effects, not causal importance.
- Regularized additive weights cannot simply be inserted into the current family-max formula and retain the same performance.
- Graduated checks need real threshold magnitudes and eligibility, not just invented binary flags. Actual contracts can also have different applicable checks.

## Follow-up: fairer likelihood-ratio versus logistic comparison

The initial comparison used different missing-data treatment, so its missingness result cannot establish a logistic advantage. A second tool gives **both** methods the same training-mean imputation, validates hyperparameters on the same buyers, and evaluates untouched test groups across seven scenarios and **ten seeds**.

```sh
python tools/compare-calibration-methods.py --method both
# Both alternatives remain available individually:
python tools/compare-calibration-methods.py --method lr
python tools/compare-calibration-methods.py --method logistic
python -m unittest discover -s tests -p 'test_compare_calibration_methods.py'
```

Output defaults to `/tmp/contract-head-to-head.json`. The method switch filters results only; it does not change fitting or paired comparisons. These are offline options, not website score modes.

| Synthetic scenario | LR mean AP | Logistic mean AP |
| --- | ---: | ---: |
| Independent | .718 | .716 |
| Correlated | .521 | .542 |
| Family-max mechanism | .486 | .485 |
| Pair interaction | .541 | .553 |
| Missingness | .426 | .419 |
| Population drift | .367 | .363 |
| Biased discovery | .691 | .684 |

Logistic retains a modest directional advantage for correlated signals and pair interactions in these invented scenarios. Other mean differences are small; some top-5% metric winners differ from overall AP winners. Paired bootstrap intervals over ten synthetic seeds are descriptive, not real-world confidence statements.

Arbitrary practical comparison tolerances were set to .02 AP and .05 top-5% precision. No scenario's entire interval exceeds those tolerances in either direction. Intervals crossing zero are inconclusive, **not proof of equivalence**. Keep both methods as candidates. LR is a useful transparent starting point; logistic is a joint-weight challenger. Neither yields defensible real-contract weights until independently reviewed labels exist. Mean imputation is for latent ranking experiments only, never a basis for inventing signals or points for absent facts.

## Best options to pursue with real evidence

1. **Nonnegative regularized logistic ranking as an offline challenger.** Promising for jointly handling overlapping signals; needs representative labels, coverage controls and held-out validation. Changing the website to this additive model would be a separate methodology decision.
2. **Smoothed likelihood-ratio weights as the transparent baseline.** Closest to the proposed 'common in corruption, uncommon in ordinary cases' idea. Publish sample sizes and uncertainty, shrink sparse estimates, and do not assume independence.
3. **Learned family-max if preserving current architecture is a requirement.** Calibrate the formula actually deployed instead of borrowing additive coefficients. It loses information when many distinct signals occupy one family; the synthetic tests demonstrate that trade-off.

Next: assemble independently reviewed, exact-contract-linked outcomes in one jurisdiction; separate final corruption findings, audit irregularities, investigation-only evidence and unknowns. Never label an unaudited/uninvestigated record clean. Predeclare evaluation target, buyer/time splits, selection strategy and metrics, then rerun these pipelines. Until then the points remain editorial hypotheses, not empirically optimized corruption weights.
