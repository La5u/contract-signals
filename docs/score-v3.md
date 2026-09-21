# Vigilance index 3.0 — active method

**An editorial sorting tool, not a probability, a measure of legal gravity or a certificate of regularity.** The existing data and PDFs are unchanged; the meaning of the score and some eligibility criteria deliberately change. A v2.1 30 must not be compared to a v3 30 as a real evolution of a contract.

## Three distinct pieces of information

1. **Heuristic index**: competition maximum + execution/duration maximum, capped at 100. No summing of correlated signals within one family, no renormalization to the observed maximum or to coverage.
2. **Declared financial stake**: amount and scope remain visible, searchable and sortable. No weight depends on a monetary tier. A declared amount is not necessarily paid; ceilings, variants and amendments are not summed.
3. **Official finding**: badge, filter, dedicated sorting, source, scope and response remain accessible; **zero heuristic points for the finding itself**. A distinct fact explicitly recorded on the contract, such as a direct award, can still produce a signal. An aggregate audit dossier is not scored as an individual contract.

The citation of an R2122 article, the buyer’s explanations, the current names/statuses of companies and project membership remain context, not additional points. No CPI or country coefficient is used.

## Unknown, zero and coverage

`getAssessment` describes **eight checks** with:

- `signal`: evaluable check and threshold crossed;
- `clear`: evaluable check, threshold not crossed — not a conclusion of regularity;
- `unknown`: insufficient data, with applicability either established or itself unknown;
- `not-applicable`: outside the known scope of the rule, with an explicit reason.

Display example: **“2 signals · 4/5 known-applicable checks evaluated; 2 additional unknown applicabilities”**. The denominator 5 does not make the two other unknowns disappear: they are always displayed separately. Out-of-scope checks complete the total of eight. This ratio describes our checks, **not the share of spending covered, nor a probability of detection**.

`getVigilanceScore` returns **`null`** when no check can be evaluated, and the interface displays **“Not assessed”**. `0` requires at least one evaluated check and no threshold crossed. Even a zero can be very partial; the eight states and their reasons are detailed in each record. Unknowns come last in both sort directions. Filters: not assessed/excluded, partial coverage, zero after evaluation.

**Groups in initial or modification conflict**, DECP identifiers duplicated in the file and `unverified` records are excluded from all calculations. This now applies **to both DECP cohorts**, not only the six municipalities. Repetition contexts are recomputed before filters. No conflict is resolved by arbitrarily selecting one version.

For documentary notices without a normalized contract, the contract rules are out of scope; the timetable remains unknown if its chain is not reliable. An explicitly revisable price falls outside the conservative scope of the increase rule; an absent price type remains unknown. No modification published is **not** proof of the absence of an amendment.

## Weights and conditions

The progressions are linear after the entry threshold is crossed, bounded and rounded to the **tenth of a point**. This rounding makes the thresholds reproducible, without conferring statistical precision on the score. The size/coverage thresholds of groups remain editorial cutoffs: progressivity does not eliminate them.

| Check | Eligibility / triggering | Raw v3 weight | Family |
| --- | --- | --- | --- |
| Single offer | Explicitly competitive procedure (`directAward=false`), positive number of offers known and equal to 1 | **12** | Competition |
| Award without competition | `directAward=true`, whatever the amount, even unknown | **18** | Competition |
| Repeated low competition | Contract itself competitive at a single offer; same buyer/CPV3/cohort, ≥10 known offers, coverage ≥80 %, rate ≥60 % | **12 at 60 % → 40 at 100 %**, linear | Competition |
| Concentration | Single identified holder, same buyer/CPV3/cohort, ≥10 known holders, coverage ≥80 %, share ≥60 % | **12 at 60 % → 40 at 100 %**, linear | Competition |
| Repeated direct awards | Same buyer/CPV3/SIREN, ≥3 distinct explicitly direct awards, contract itself direct; all amounts | **18 at 3 contracts → 60 at 10**, cap 60 | Competition |
| Short bidding period | Reliable chronology as defined in the README; explicitly open non-accelerated procedure; period strictly <15 days | **8 near 15 days → 40 at 3 days**, cap 40 | Competition |
| Long declared duration | Known duration ≥120 months, without invented renewals | **8 at 120 months → 40 at 360 months**, cap 40 | Execution/duration |
| Declared relative increase | Same comparable history, price exclusively firm, without conflicts or identified change of holder; increase strictly >20 % | **8 near +20 % → 40 at +100 %**, cap 40 | Execution/duration |

Examples: a concentration of 61 % is worth 12.7 points, 80 % is worth 26 and 95 % is worth 36.5; all else equal, going from 79 % to 80 % no longer adds an arbitrary tier. Three direct awards are worth 18, four are worth 24, ten are worth 60. A comparable increase of 21 % is worth 8.4, whether it is €100 → €121 or €1m → €1.21m.

**Explicit eligibility changes:** removal of the €100k threshold for direct awards and their repetition, removal of the absolute €50k threshold for the increase, and non-evaluation of a single offer when the competitive character is unknown. An offer expected in a direct award no longer adds 5 points. In direct repetition, fewer than three known awards does not become an absence of repetition if other procedures of the holder are unknown; three identified facts are enough to document a minimum of three, even if others remain unknown.

**Limits:** a small-amount direct award can be perfectly ordinary and lawful. The rule describes an award modality, not an offence. A small relative increase can have a minimal financial stake; consult the amount column. Durations, shares and evolutions are not yet compared to a sufficiently large and validated sectoral sample. Neither a legitimate specialisation nor a legal exception is automatically recognized by the code.

## Results on the same data, with no inflation target

| Dataset | v2.1 flagged | v3 flagged | v3 zero (at least one check) | v3 not assessed |
| --- | ---: | ---: | ---: | ---: |
| BOAMP / CRC, 3,010 records | 284 | 277 | 2,665 | 68 |
| Paris / Ardèche, 2,594 groups | 734 | 404 | 1,835 | 355 |
| Six municipalities, 1,270 groups | 233 | 124 | 974 | 172 |
| 10 FNSimple consultations | 0 | 0 | 0 | 10 |
| 66 Tours version/lot rows | 0 | 0 | 0 | 66 |

The number of flags **decreases**, notably because undetermined adapted procedures are no longer presumed competitive for scoring a single offer. This is neither a presumed improvement of regularity, nor a result to be corrected to obtain more red. Official findings remain **eight**, outside this flag column.

Full results: [`score-v3-review.json`](../data/score-v3-review.json). This file contains the category changes, per-indicator counts, data/code fingerprints and review queues. The old counters in the historical coverages are kept with their version; `currentIndex` points to the active method.

## Sensitivity and review: what has been verified, and what has not

The script [`review-score-v3.cjs`](../tools/review-score-v3.cjs) compares the frozen v2.1 to v3 and two perturbations: competition ×0.8 / execution ×1.2, then the reverse. Same eligibility, same family maxima and cap; **these variants are not used in the interface**. Spearman correlation with average ranks for ties, on positive v3 scores only:

- BOAMP: **0.773 / 1.000**; part of the ranking therefore depends noticeably on the balance of the families.
- Paris/Ardèche: **0.9791 / 0.9822**; top-20 rows overlap: **18/20 / 17/20**.
- Six municipalities: **0.9578 / 0.9863**; overlap **18/20 / 20/20**.

Ties are numerous: in the six municipalities, **66 rows** share the top-20 cutoff score. Tie-breaking by identifier ensures only reproducibility, not an order of suspicion between these rows. Good rank stability does not validate the weights against facts of irregularity. No labelled ground truth, no precision/recall or probabilistic calibration is claimed.

### Limited review of six already-downloaded DECP extracts

Reproducible selection: the first two identifiers sorted by SHA-256 in each v3 stratum **signal / zero / not assessed**, for the six municipalities. The subjects, initial fields and `sourceRowVariants` were reviewed by the assistant; **this is not an independent human review, nor a legal qualification**. The other entries of the report remain a review queue, not validated cases.

| Dossier | Result and observation of the extract | Explanation / limit |
| --- | --- | --- |
| Nantes `2025S00012` | Direct declared, one offer, fountain sculpture, €40,000, 9 months; v3 18 | Specialised restoration and/or a lawful exception possible; the source does not allow the basis to be judged. A direct single offer no longer receives distinct points. |
| Rennes `2024S00060` | Acoustic measurements, €1,600, 3 months, direct declared; v3 18 | Important counterexample to an accusatory reading: small amount and potentially routine purchase. The financial stake remains to be read separately. |
| Nantes `2025T00219` | Adapted procedure, 27 offers declared, €38,845.73 → €39,735.73, 7 months; v3 0, only 2/3 established-applicable checks evaluated and 3 unknown applicabilities | The two evaluated checks are duration and concentration (1/24 contracts to the holder). Declared price revisable: the increase is out of scope of our rule, not assessed as negative. The declared 27 verifies neither the admissibility of the offers nor their scope. |
| Dijon `2024DMPA06` | Second-hand piano, adapted procedure, 3 offers, €25,000, 5 months; v3 0, only 1/4 established checks evaluated and 3 unknown applicabilities | The zero comes essentially from the duration below threshold. Competition and history insufficiently characterized; do not conclude “no risk”. |
| Nantes `2024F00023` | Same identifier and object of memorial plaques, initial amounts **€20,000 / €6,392**; v3 null | No invented order of amendments nor amount chosen at random. |
| Bordeaux `2025G0` | The same identifier covers natural gas at **€33m** and modular buildings at **€30m**, with divergent dates/procedures; v3 null | Impossible to make a coherent contract or an increase of it. The variants are kept and excluded. |

This review highlights limits and counterexamples; it justifies no tuning to favor a Parisian dossier or a country.

## Reproduction

```sh
node tests/rules.cjs             # frozen v2.1: historical reference, not the active engine
node tests/scoring-v3.cjs        # active engine, thresholds, coverage and independence
node tests/cities.cjs
node tests/tours.cjs
python -m unittest discover -s tests -p 'test_*.py'
node tools/review-score-v3.cjs   # diagnostics and currentIndex pointers of the coverages
# Server on 8765, test-only Playwright outside the project:
node tests/browser.cjs
```

The archive `tools/legacy/scoring-v2.1.js` is never loaded by the site. No international download or test/preparation script is required to open the static explorer. French rules do not automatically apply to another country: see [the proposed international pilots](international-pilots.md).
