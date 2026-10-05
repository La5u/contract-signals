# Vigilance index 3.3 — active method

**An editorial sorting tool, not a probability, a measure of legal gravity or a certificate of regularity.** The existing data and PDFs are unchanged; the meaning of the score and some eligibility criteria deliberately change. A v2.1 30 must not be compared to a v3 30 as a real evolution of a contract.

## Three distinct pieces of information

1. **Heuristic index**: competition maximum + execution/duration maximum + transparency maximum (since v3.1), capped at 100. No summing of correlated signals within one family, no renormalization to the observed maximum or to coverage.
2. **Declared financial stake**: amount and scope remain visible, searchable and sortable. No weight depends on a monetary tier. A declared amount is not necessarily paid; ceilings, variants and amendments are not summed.
3. **Official finding**: badge, filter, dedicated sorting, source, scope and response remain accessible; **zero heuristic points for the finding itself**. A distinct fact explicitly recorded on the contract, such as a direct award, can still produce a signal. An aggregate audit dossier is not scored as an individual contract.

The citation of an R2122 article, the buyer’s explanations, the current names/statuses of companies and project membership remain context, not additional points. No CPI or country coefficient is used.

## Unknown, zero and coverage

`getAssessment` describes **eight local checks and the universal late-publication check, plus five evidence-based checks when present** (9 per record; the five evidence-based checks are described in [experimental-indicators.md](experimental-indicators.md) and are listed only on records carrying `indicatorEvidence`, otherwise omitted), plus a linked-notice check for Tours (10), with:

- `signal`: evaluable check and threshold crossed;
- `clear`: evaluable check, threshold not crossed — not a conclusion of regularity;
- `unknown`: insufficient data, with applicability either established or itself unknown;
- `not-applicable`: outside the known scope of the rule, with an explicit reason.

Display example: **“2 signals · 4/5 known-applicable checks evaluated; 2 additional unknown applicabilities”**. The denominator 5 does not make the two other unknowns disappear: they are always displayed separately. Out-of-scope checks complete the dataset's check count. This ratio describes our checks, **not the share of spending covered, nor a probability of detection**.

`getVigilanceScore` returns **`null`** when no check can be evaluated, and the interface displays **“Not assessed”**. `0` requires at least one evaluated check and no threshold crossed. Even a zero can be very partial; the check states and their reasons are detailed in each record. Unknowns come last in both sort directions. Filters: not assessed/excluded, partial coverage, zero after evaluation.

**Groups in initial or modification conflict**, DECP identifiers duplicated in the file and `unverified` records are excluded from all calculations. This now applies **to both DECP cohorts**, not only the six municipalities. Repetition contexts are recomputed before filters. No conflict is resolved by arbitrarily selecting one version.

For documentary notices without a normalized contract, the contract rules are out of scope; the timetable remains unknown if its chain is not reliable. An explicitly revisable price falls outside the conservative scope of the increase rule; an absent price type remains unknown. No modification published is **not** proof of the absence of an amendment.

## Weights and conditions

The progressions are linear after the entry threshold is crossed, bounded and rounded to the **tenth of a point**. This rounding makes the thresholds reproducible, without conferring statistical precision on the score. The size/coverage thresholds of groups remain editorial cutoffs: progressivity does not eliminate them.

| Check | Eligibility / triggering | Raw v3 weight | Family |
| --- | --- | --- | --- |
| Single offer | Explicitly competitive procedure (`directAward=false`), positive number of offers known and equal to 1 | **12** | Competition |
| Award without competition | `directAward=true` and a declared amount **at or above the legal no-publicity threshold in force on the contract date** (v3.2: not applicable below it, unknown without an amount) | **18** | Competition |
| Repeated low competition | Contract itself competitive at a single offer; same buyer/CPV3/cohort, ≥10 known offers, coverage ≥80 %, rate ≥60 % | **12 at 60 % → 40 at 100 %**, linear | Competition |
| Concentration | Single identified holder, same buyer/CPV3/cohort, ≥10 known holders, coverage ≥80 %, share ≥60 % | **12 at 60 % → 40 at 100 %**, linear | Competition |
| Repeated direct awards | Same buyer/CPV3/SIREN, ≥3 distinct explicitly direct awards, contract itself direct; all amounts | **18 at 3 contracts → 60 at 10**, cap 60 | Competition |
| Short bidding period | Reliable chronology as defined in the README; explicitly open non-accelerated procedure; period strictly <15 days | **8 near 15 days → 40 at 3 days**, cap 40 | Competition |
| Long declared duration | Known duration ≥120 months, without invented renewals | **8 at 120 months → 16 at 360 months**, cap 16 (40 before v3.3) | Execution/duration |
| Declared relative increase | Same comparable history, price exclusively firm, without conflicts or identified change of holder; increase strictly >20 % | **8 near +20 % → 40 at +100 %**, cap 40 | Execution/duration |

Examples: a concentration of 61 % is worth 12.7 points, 80 % is worth 26 and 95 % is worth 36.5; all else equal, going from 79 % to 80 % no longer adds an arbitrary tier. Three direct awards are worth 18, four are worth 24, ten are worth 60. A comparable increase of 21 % is worth 8.4, whether it is €100 → €121 or €1m → €1.21m.

**Explicit eligibility changes:** removal of the €100k threshold for direct awards and their repetition (the legal threshold of v3.2 below decides eligibility, not a weight), removal of the absolute €50k threshold for the increase, and non-evaluation of a single offer when the competitive character is unknown. An offer expected in a direct award no longer adds 5 points. In direct repetition, fewer than three known awards does not become an absence of repetition if other procedures of the holder are unknown; three identified facts are enough to document a minimum of three, even if others remain unknown.

**Limits:** a small-amount direct award can be perfectly ordinary and lawful. The rule describes an award modality, not an offence. A small relative increase can have a minimal financial stake; consult the amount column. Durations, shares and evolutions are not yet compared to a sufficiently large and validated sectoral sample. Neither a legitimate specialisation nor a legal exception is automatically recognized by the code.

## Transparency family (v3.1, 27 September 2026; made buyer-relative in v3.2)

*Historical v3.1 description and counts below. Current v3.3 requires delay >120 days and buyer-relative excess >240 days for DECP with an established baseline, >120 days for BOAMP/TED; without a baseline, whole delay >120 days. These editorial cutoffs are not legal deadlines.*

A third family, the same for every country ([indicators.md](indicators.md)): **published more than 120 days after the contract**. The delay runs from the contract date (French notification date in the DECP, declared conclusion date in BOAMP and TED notices) to the publication of the award (DECP essential data on the buyer profile, BOAMP or TED award notice). 120 days exceeds every legal deadline of the regimes covered: EU award notices within 30 days of conclusion, or grouped per quarter and published within 30 days of its end for framework and dynamic-purchasing call-offs (Directive 2014/24/EU, Art. 50); French essential data within two months of notification. **8 points just above 120 days, linear to 16 at two years**, in its own family, so the index becomes `min(100, max(competition) + max(execution/duration) + max(transparency))`. A negative delay (publication before the contract date) is inconsistent and stays unknown.

- **Out of scope** where the source publishes no comparable dates: SECOP II, DNCP, Prozorro (no contract publication date in the record) and Mercado Público. **Find a Tender is out of scope too**: its award notices can carry the signature date of a contract concluded years earlier (modification notices under PCR 2015 Regulation 72, for example FCDO extensions of 2017–2021 contracts) or a dynamic purchasing system admission date, so the delay would not measure late publication.
- **Results**: BOAMP 287 late of 2,980 dated awards, Paris & Ardèche 133, six municipalities 144; TED Portugal 12, Romania 26, Czechia 45.
- **What it measures, and what it does not.** In the DECP, late publication is mostly a buyer's batch practice: 131 of Paris & Ardèche's late rows are the Ville de Paris, published in weekly batches (for example 32 on 13 October 2024) months after notification, and 108 of the six-city rows are Nantes. It compares buyers well and single contracts poorly, which is why its weight stays low. A very long delay in a TED notice (a 2015 contract published in 2026) may also concern an old contract being modified or re-announced: read the notice.
- Withheld fields (eForms `FieldsPrivacy`, the explicit mark of information kept unpublished) were looked for and appear in none of the three TED cohorts; no check was built on them.

## v3.2 (4 October 2026): historical transition — buyer-relative publication, legal direct-award threshold, tie-breaks, placeholder weights

Approved by the owner. Why: the v3.1 flags were dominated by two effects the data cannot separate from a contract's own behaviour (late publication measured buyer batch habits; small direct awards below the legal threshold are the lawful default).

**A. Late publication is relative to the buyer.** During preparation, for each buyer (SIRET, else buyer id, else name) within one dataset, the median publication delay of the buyer's *other* dated rows is computed (leave-one-out), only for buyers with at least 10 dated rows; excluded, unverified and conflicting rows never enter it, filters never change it (computed on the whole cohort, like the repetition contexts). The check is a signal only when the delay exceeds 120 days **and** exceeds that baseline by more than 120 days (baseline 0 for a buyer with fewer than 10 dated rows, which the reason states). Points: 8 just above 120 days of excess, linear to 16 at 730 days (`LATE_PUBLICATION_DAYS`, `LATE_PUBLICATION_MAX_DAYS`, `LATE_PUBLICATION_DEFAULTS`; per-country or per-family overrides go in `LATE_PUBLICATION_OVERRIDES`, empty in v3.2; current v3.3 overrides DECP established-baseline excess to 240 days). A delay beyond 120 days within the buyer's habit evaluates *clear* with the reason "a buyer-level publication practice, not specific to this contract". Negative delays stay unknown; out-of-scope datasets are unchanged.

**B. French direct award needs the legal threshold.** Below the threshold in force on the contract date, an award without publicity or competition is the legal default (Code de la commande publique, art. R2122-8): `direct-award` is *not applicable* with the threshold in the reason; with no usable amount it is *unknown* (it used to score). Amounts are taken as excluding tax. `repeated-direct-award` is unchanged and still counts every direct award (splitting is exactly a repetition of small awards). Other countries are unchanged.

| Period | Supplies and services | Works (CPV 45) | Source |
| --- | ---: | ---: | --- |
| 1 Oct 2015 – 31 Dec 2019 | €25,000 | €25,000 | décret n° 2015-1163 |
| 1 Jan 2020 – 31 Mar 2026 | €40,000 | €40,000 | décret n° 2019-1344 |
| 24 Jul – 7 Dec 2020 | €40,000 | €70,000 | décret n° 2020-893 (to 10 Jul 2021, overtaken by the ASAP law) |
| 8 Dec 2020 – 31 Dec 2022 | €40,000 | €100,000 | loi n° 2020-1525 (ASAP), art. 142 |
| 2023 – 31 Dec 2025 | €40,000 | €100,000 | extended by décret n° 2022-1683 (to 31 Dec 2024) and décret n° 2024-1217 (to 31 Dec 2025) |
| from 1 Jan 2026 | €40,000 to 31 Mar 2026, then **€60,000** | €100,000, now permanent | décret n° 2025-1386 of 29 Dec 2025 (works 1 Jan 2026, supplies and services 1 Apr 2026) |

Sources: [marche-public.fr threshold chronology](https://www.marche-public.fr/Marches-publics/Definitions/Entrees/Seuil-dispense-publicite.htm), [décret 2020-893 on Légifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000042138128), [extensions to 2025](https://www.marche-public.fr/contrats-publics/Decret-2024-1217-seuil-travaux-ECOM2434725D.htm), [analysis of décret 2025-1386](https://blog.landot-avocats.net/2025/12/30/rehaussement-des-seuils-de-dispense-de-publicite-et-de-mise-en-concurrence-decryptage-du-decret-n-2025-1386-du-29-decembre-2025-modifiant-certains-seuils-relatifs-aux-marches-publics/). These were read from secondary legal-news pages; the decree texts themselves were not re-read on Légifrance, except the 2020 decree link. The law applies by the date the consultation is launched, which the data never gives. A valid calendar contract date is used instead. Every encoded regime intersecting the preceding 180-day possible-consultation window is considered, including overlapping changes; an amount with conflicting eligibility across those regimes is *unknown*, never a signal. This window is an editorial uncertainty guard, not a verified consultation date. A row without CPV whose amount lies between the supplies and the works threshold is *unknown* too (works are CPV 45; the DECP `nature` field is "Marché" for every row and does not identify works). The €100,000 works exemption also covers lots under 100,000 provided they stay under 20 % of the whole; lots are not analysed.

**C. Tie-breaking.** Equal scores are ordered by the number of families with a signal (descending), then the strongest single signal weight (descending), then the identifier. Unknown scores stay last in both directions; the sort names in the URL are unchanged.

**D. The five evidence-based checks carry a uniform 8 points** (previously 20/10/5/3/1, which were arbitrary): the lowest entry weight of the existing graduated checks. It is an uncalibrated placeholder pending a reviewed public-evidence sample. Their contribution to the normal index is at most 8 (execution) + 8 (competition) = 16; the CLI diagnostic sum is at most 40.

**Effect on the bundled French datasets** (`score-v3-review.json`):

| Dataset | Flagged v3.1 → v3.2 | Zero | Not assessed | Late publication signals | Direct-award signals |
| --- | ---: | ---: | ---: | ---: | ---: |
| BOAMP / CRC, 3,010 | 535 → 432 | 2,466 → 2,566 | 9 → 12 | 287 → 184 | 28 → 19 |
| Paris / Ardèche, 2,594 | 492 → 358 | 1,747 → 1,881 | 355 → 355 | 133 → 121 | 262 → 86 |
| Six municipalities, 1,270 | 263 → 149 | 835 → 949 | 172 → 172 | 144 → 62 | 66 → 31 |

TED: late publication 12 → 10 (Portugal), 26 → 25 (Romania), 45 → 40 (Czechia). Direct-award rows that stopped scoring: BOAMP 9 (1 not applicable below the threshold, 8 unknown for lack of an amount), Paris / Ardèche 176 and six municipalities 35 (all not applicable below the threshold). Late publication changed from signal to clear in 103 BOAMP rows, 12 Paris / Ardèche rows and 82 municipal rows. Three BOAMP rows whose only evaluable check was a direct award with no amount are now not assessed. As before, none of this is calibration against irregularity.

## v3.3 (4 October 2026): legal anchoring

**Long declared duration, maximum 16 (was 40), owner decision of 5 October 2026.** On the national DECP, single-bid odds fall as duration rises (OR 0.54–0.68 from 12 months; 0.56 [0.43, 0.74] from 120 months). This is exploratory competition-proxy evidence, not empirical calibration of execution risk. It neither justifies the Colombian execution-risk weight nor calibrates the maximum of 16: that maximum is an editorial owner decision for both countries. France: 8 at 120 months → 16 at 360 months. Colombia: 8 at 36 months → 16 at 120 months.

Approved by the owner. Eligibility and thresholds follow each jurisdiction's law wherever the law gives an anchor and the data can test it, subject to the verification limits below. Weights remain editorial; the duration maximum changes from 40 to 16. The full per-check table is in [indicators.md](indicators.md#legal-anchor-of-each-check-v33-4-october-2026).

- **Paraguay amount increase**: the reported 20 % reference in Ley 7021/22 art. 67 is a provisional legal basis. The full text and type-specific exceptions remain unverified; it is not a universally verified legal cap. Entry moves from "above 20 %" to "from 19 % up to the ceiling" (8 points, a review prompt, because reaching the ceiling is lawful) and "beyond the ceiling" (16 points just above, linear to 40 at +100 %); only processes launched from 19 Feb 2024 (an earlier call is out of scope, a missing date unknown). Pilot 35 → 36 flagged, three-buyer cohort 53 → 58; the 10 at-ceiling rows (previously a no-points context label, now removed) are the new signals; none is beyond the ceiling. See [score-paraguay.md](score-paraguay.md).
- **Eligibility unchanged, with reasons (duration weight changed above).** Colombia: Ley 80 art. 40 caps value additions (not terms), and the extract has no addition value, so term extension and duration stay editorial. Chile: no direct deals, tender periods or modifications in the source. Ukraine, TED, UK: no amount-eligibility threshold applies (TED and Find a Tender hold above-threshold notices by construction); Ukrainian and French minimum bidding periods and the French modification caps depend on facts the data lacks (procedure ground, EU threshold) or on legal text not verified: follow-ups.
- **French DECP late publication (buyer-relative excess)**: for the DECP data family only, a buyer with an established usual delay is flagged when the excess over that usual delay exceeds **240 days** (was 120). Buyers without an established usual delay still use the editorial 120-day cutoff on the whole delay; BOAMP and TED are unchanged. Evidence ([france-national.md](../research/thresholds/france-national.md)): national DECP, 210,018 competitive contracts, 8,702 buyers; the buyer-relative excess is first reliably associated with single bidding from 241 days (OR 1.14 [1.01, 1.29]) and 1.71 [1.32, 2.22] beyond 730 days; the raw delay shows no association. This is exploratory single-bid proxy evidence, not a legal deadline or calibration against corruption outcomes. Historical v3.3 transition counts: Paris and Ardeche 355 not assessed / 1,966 zero / 273 flagged (was 1,881 zero / 358 flagged; late-publication signals 121 to 22); six municipalities 172 / 987 / 111 (was 949 zero / 149 flagged; late-publication signals 62 to 22); BOAMP unchanged (12 / 2,566 / 432).
- TED, UK, Ukraine, Chile and Colombia: before and after counts are identical (score-v3-review.json regenerated).

## Local correctness corrections after v3.3

The leave-one-out median parity, invalid-calendar-date handling and overlapping legal transitions are corrected locally. Across 14 bundled datasets, 21 scores change and Portugal TED gains one flagged row (137 → 138); the BOAMP top 20 gains one record. Weights and source cohorts are unchanged. Full before/after results, caveats and reproduction: [score-audit.md](score-audit.md).

## Results on the same data, with no inflation target

| Dataset | v2.1 flagged | v3.0 flagged | v3.1 flagged | v3.1 zero (at least one check) | v3.1 not assessed |
| --- | ---: | ---: | ---: | ---: | ---: |
| BOAMP / CRC, 3,010 records | 284 | 277 | 535 | 2,466 | 9 |
| Paris / Ardèche, 2,594 groups | 734 | 404 | 492 | 1,747 | 355 |
| Six municipalities, 1,270 groups | 233 | 124 | 263 | 835 | 172 |
| 10 FNSimple consultations | 0 | 0 | 0 | 0 | 10 |
| 66 Tours version/lot rows | 0 | 0 | 0 | 6 | 60 |

v3.0 zero / not assessed were 2,665 / 68 (BOAMP), 1,835 / 355 (Paris / Ardèche) and 974 / 172 (six municipalities). The v3.1 increase comes from the transparency family (below): 258, 88 and 139 rows are flagged by late publication alone, and 59 BOAMP rows with no other evaluable check are now assessed.

The number of flags **decreases**, notably because undetermined adapted procedures are no longer presumed competitive for scoring a single offer. This is neither a presumed improvement of regularity, nor a result to be corrected to obtain more red. Official findings remain **eight**, outside this flag column.

Full results: [`score-v3-review.json`](../data/score-v3-review.json). This file contains the category changes, per-indicator counts, data/code fingerprints and review queues. The old counters in the historical coverages are kept with their version; `currentIndex` points to the active method.

### Linked-notice extension (2026-09-28)

Tours now checks exact correction/predecessor lot pairs for a late title/criteria change without deadline extension (5 competition points). Six linked corrections extend the deadline and evaluate clear; the other 60 rows remain not assessed. This does not establish a complete original bidding chronology. No new positives. See [linked evidence](linked-evidence.md) for the rule and source requirements; the original eight French checks are unchanged.

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

## Context outside the index: single-vendor software maintenance

`softwareMaintenanceContext` (filter *Legal context → France · single-vendor software maintenance*, row note “Context · single-vendor software maintenance · no points”) marks the maintenance, support or licences of an existing software product placed with one vendor. **No points are added or removed and no row is excluded**; the label explains why such rows sit at the top of the ranking (a direct award, often repeated every year to the same publisher).

A BOAMP or DECP row is labelled when all three conditions hold:

1. **Software**: CPV starting with `48` (software packages), `7221`, `7225` or `7226` (software services), or the object names software explicitly (`progiciel`, `licences logicielles`, or a maintenance word followed within four words by `du/des/de la logiciel(s)`).
2. **Maintenance**: CPV `72267…` (software maintenance) or the object contains `maintenance`/`maint`, `support`, `assistance`, `mise(s) à jour`, `TMA`, `MCO`, `licence(s)`, `abonnement`, `souscription` or `droit de suivi`.
3. **One vendor**: award declared without competition (`directAward = true`), article R2122-3 cited, or procedure not classified with exactly one offer. A competitive procedure with a single offer is **not** labelled: competition was opened, and the single-offer check remains informative there.

Proprietary status and exclusive rights are not verified; the text in the row says so. Source text is matched as published, in French.

**Result**: 30 rows labelled — BOAMP 4 (all positive), Paris & Ardèche 25 (16 positive, including five of the top six rows: Ardèche maintenance of IXBUS, AIDEN, ETEMPTATION, Covadis and its deliberations software), six municipalities 1 (positive). Review of all 30 (assistant's reading, not an independent review): 28 are maintenance, licences or support of a named software product with its vendor (Planisware, Axelnet, Vivaticket, One2Team, eSirius, E-SEDIT…); 2 are doubtful because the software may be bespoke rather than a vendor's product (maintenance of the *Parcours Révolution* application and of the Fonds d'art contemporain website).

**Near-misses, not labelled** (reviewed): Ardèche ZENworks supply and maintenance (52 points; competitive, one offer), Paris TIGRE 7 and application-integration maintenance (competitive, one offer), competitive BOAMP lots for Alfresco/i-Parapheur/Pastell (open-source tools) and SAP BusinessObjects; two Paris Trimble surveying stations with bundled software (equipment, not software maintenance: CPV 50324200 and 38295000); Bordeaux *Logiciel LOGUS* and Tours *Logiciel modernisation de la gestion de surveillance interne* (software purchases with no maintenance wording). A Tours works contract for automatic gates carries the software CPV 48921000: it is not labelled only because its object has no maintenance wording, which shows the limit of a CPV-based rule.

## Threshold splitting: examined, not added (2026-09-26)

A check for direct awards split below the €40,000 no-publicity threshold was prototyped on both DECP cohorts: same buyer, same CPV group (3 digits) and calendar year, at least three direct awards each under €40,000, together above it. Paris & Ardèche gives 14 groups (78 rows), the six cities 2 groups (7 rows). Read row by row, the groups are not one need split in pieces: under CPV 454 in 2024 Paris combines a church repair, summer cleaning of squares and crèche blinds, with 4 to 9 different suppliers per group. For a buyer of that size a CPV group is far coarser than the legal notion of a homogeneous need, and the published data do not say which department or operation placed each order. The same-supplier version of the pattern is already covered by *Repeated direct awards*. Not added; it would need the buyer's operation or budget line, which the DECP does not publish.

## Reproduction

```sh
node tests/rules.cjs             # frozen v2.1: historical reference, not the active engine
node tests/scoring-v3.cjs        # active engine, thresholds, coverage and independence
node tests/cities.cjs
node tests/tours.cjs
python -m unittest discover -s tests -p 'test_*.py'
node tools/review-score-v3.cjs   # diagnostics and currentIndex pointers of the coverages
# Starts its own server on a free port; test-only Playwright outside the project:
node tests/browser.cjs
```

The archive `tools/legacy/scoring-v2.1.js` is never loaded by the site. No international download or test/preparation script is required to open the static explorer. French rules do not automatically apply to another country: see [the proposed international pilots](international-pilots.md).
