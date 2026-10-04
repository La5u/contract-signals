# Local-only indicator experiment

These five checks are now integrated into the normal local explorer: the indicator filter, record assessments, signals and exports; a record lists each check only when `indicatorEvidence` has that id, otherwise it is omitted. `indicator-evidence.js` supplies the shared browser/Node evidence engine; `tools/experimental-indicators.cjs` remains a CLI runner. Existing live deployment is unchanged. Do not push or deploy without an explicit release decision.

## Trial settings

| Check | Points | Experimental trigger |
| --- | ---: | --- |
| Monetary modifications near an applicable cap | 8 | Cumulative additions use 95–100% of a **verified applicable** cap, on the same valuation basis. Above-cap amounts are reported separately, with no near-cap points. |
| Fully paid, execution incomplete | 8 | Verified net payments reach 99% of payable value while independently documented physical completion is at most 80%, at the same snapshot date. Advances/refunds are excluded; elapsed time is not progress. |
| Legal ground incompatible with purchase | 8 | An explicitly reviewed jurisdiction/classification/legal-ground mapping says incompatible and is valid on the relevant date. No keyword inference. |
| Comparable year-over-year unit-price jump | 8 | Real unit price rises at least 30% after inflation adjustment; buyer, supplier, item, specification, quantity, unit, currency, tax and delivery terms are explicitly matched. |
| Claimed exclusivity versus comparable competitive wins | 8 | Verified supplier identity, documented claim, at least two offers in a documented competitive win, and explicitly comparable market, territory, time and rights context. This is a review prompt, **not a refutation** of exclusivity. |

**All five checks carry the same 8 points (since score v3.2).** The earlier 20/10/5/3/1 were arbitrary; 8 is the lowest entry weight of the existing graduated checks and is an *uncalibrated placeholder* pending a reviewed public-evidence sample. Weights and thresholds are uncalibrated editorial hypotheses, not measured importance, likelihoods or legal tests. The CLI's separate diagnostic sum has a maximum of **40** (5 × 8), not a score out of 100. The normal website retains family maxima: cap, payment/progress and unit price belong to execution; legal-ground mismatch and exclusivity context belong to competition. Thus these five checks alone contribute at most 8 execution + 8 competition = **16**, not 40, to the normal index. Assessment coverage is returned alongside points. Do not compare totals across records with different assessed checks.

A confirmed monetary cap must be supplied for the particular contract; country defaults such as Colombia 50% or Paraguay 20% are not automatically applied. Legal regimes, exemptions, dates and valuation bases need review.

## Run locally

```sh
node tests/experimental-indicators.cjs
node tools/experimental-indicators.cjs tests/fixtures/experimental-indicators-positive.json
```

The fixture is entirely **synthetic**: all five checks trigger for a total of 40. Its references and legal mapping are fictional test inputs, not published evidence or laws. Tests also cover missing evidence, inapplicability, negative cases, boundary values, malformed fields, currency/basis mismatch, dated execution snapshots, comparability and CLI behavior.

For your own inputs, copy the shape of the fixture and replace its assertions with reviewed evidence. The header of `indicator-evidence.js` documents every required field and the API's configurable thresholds/weights. Normalized contract records supply this evidence in `indicatorEvidence`; all five checks appear as unknown when the required evidence is absent. CLI input can be one object or an array of objects. Missing, conflicting or unsupported evidence returns `not-assessed` with null points; an assessed check below threshold returns zero. If nothing is assessed, the total is null.

`sourceRefs` identifies the documents supporting each check. The engine checks that references are present, **not that a URL exists or the assertion is true**. Fields named `Verified`, `Confirmed` or `Reviewed` are caller-supplied assertions; supplying true is not independent verification. Keep personal, confidential and live-case information out of inputs and outputs.

## What is not implemented

- No automatic conversion of existing procurement extracts into verified evidence.
- No country legal-applicability library or independently reviewed category mapping.
- No payment/progress auditing, unit-price matching, inflation-data acquisition, or cross-country supplier resolution.
- No OCP-equivalence claim, empirical validation, public ranking or allegation.

The current extracts do not establish all of these prerequisites. Synthetic success does **not** mean the checks can validly score existing contracts. Next, prepare a small manually verified public-record sample and record both failures and non-assessable cases before considering integration.
