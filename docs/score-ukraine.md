# Ukraine method — Prozorro checks (v3.6 framework)

**Checks for the Prozorro cohort** (three buyers, tenders created 2024-09-01 → 2026-09-01). Same vigilance-index framework as [score-v3.md](score-v3.md): two families, family maxima, cap at 100, `null` = “Not assessed”, unknowns never counted as zero. Different checks and eligibility; French, Colombian and Paraguayan rules are not applied. Amounts stay in the published currency (UAH, sometimes EUR or USD) and are never converted.

An editorial sorting tool, not a probability, not a measure of legal gravity, not a certificate of regularity. Wartime rules allow procurement exceptions and withheld publications: a missing record or bid is not evidence of anything, and a zero is not clearance.

## Data

Records are the **official** tender records of the Prozorro public API (`public-api.prozorro.gov.ua/api/2.5`). The prozorro.gov.ua site search is used only to list each buyer's tender IDs; every row comes from the official record. One row is one signed contract (active or terminated) linked to an active award with exactly one supplier.

## How the checks were chosen

Written on 25 September 2026, before any record of this cohort was read. Procedure types are classified by their meaning in the Prozorro standard, not by results:

- **Competitive:** aboveThreshold (and EU/UA/defense variants), belowThreshold, competitiveDialogue (and stage 2), competitiveOrdering, esco, simple.defense, requestForProposal, priceQuotation, closeFrameworkAgreement(Selection)UA.
- **Without competition:** negotiation, negotiation.quick.
- **Offer/direct-award checks excluded:** reporting — a direct-contract report recorded without a procedure. Reporting alone adds no points; the concentration check still applies.

## The checks (twelve with the universal late-publication check)

| Check | ID | Family | Eligibility / trigger | Weight |
| --- | --- | --- | --- | --- |
| Single offer in a competitive procedure | `ua-single-offer` | Competition | Competitive type; offers on the awarded lot = 1 (bids whose lot values point to that lot, excluding deleted and draft bids) | **1** since v3.5 (was 12) |
| Award without competition | `ua-direct-award` | Competition | negotiation / negotiation.quick | **18** |
| Repeated single-offer awards | `ua-repeated-single-offer` | Competition | This award is single-offer; same buyer and supplier (EDRPOU or individual tax number) in ≥3 distinct tenders | **12 at 3 → 40 at 10** |
| Repeated awards without competition | `ua-repeated-direct` | Competition | This award is negotiated; same buyer and supplier in ≥3 distinct tenders | **18 at 3 → 60 at 10** |
| Concentrated awards | `ua-concentration` | Competition | Same buyer and main category (goods, works, services); ≥10 distinct procedures with identified suppliers, ≥80 % identification coverage, share ≥60 % | **12 at 60 % → 40 at 100 %** |
| Amount increase | `amount-increase` | Execution | **Out of scope**: three contract links checked, but no comparable dated amendment history | — |
| Better-ranked bidder disqualified | `ua-better-bid-disqualified` | Competition | Competitive type; on the awarded lot, at least one award to another bidder was declared unsuccessful before this award (added 2026-09-26) | **4**, flat (12 before v3.5) |
| Three or more contract amendments | `ua-contract-amendments` | Execution | Signed contract; retrieved integer count of active amendments ≥3 | **6** at 3–4, **10** at 5+, **+6** with a term extension (flat 8 in v3.4) |
| Contract term extended by amendment | `ua-term-extension` | Execution | Signed contract; an active amendment of type durationExtension or fiscalYearExtension | **4** (with 3+ amendments counted as +6 on the amendments check) |
| Large share of the buyer's yearly procurement | `ua-buyer-share` | Competition | Any procedure, UAH amount; this contract is ≥ 5 % of the buyer's UAH contract total for the tender's creation year, in a year the cohort covers completely (bundled cohort: 2025 only) | **30** since v3.6 |
| Long declared duration | `long-contract` | Execution | **Out of scope** | — |

Offers are counted per lot, which Prozorro publishes (unlike the Paraguayan data). When a record publishes no bids, offers are unknown, never zero. Complaints are shown as context outside the index.

## Results

Reproduced by `tests/national.cjs`. Ministry of Health (national, EDRPOU 00012925), Vinnytsia Oblast State Administration (regional, 20089290), Dnipro City Council (municipal, 26510514). The site search listed 689, 500 and 869 tenders of all years; the tender ID's creation date kept 247, 134 and 161 in the window; 16 records name another procuring entity and are excluded. 526 tenders: reporting 424, aboveThreshold 44, requestForProposal 31, belowThreshold 17, priceQuotation 9, aboveThresholdEU 1. 488 signed contracts retained (8 cancelled or pending excluded). Every competitive contract has a per-lot offer count.

| Check | Signals | Clear | Unknown | Out of scope |
| --- | ---: | ---: | ---: | ---: |
| `ua-single-offer` | 38 | 26 | 0 | 424 |
| `ua-direct-award` | 0 | 64 | 0 | 424 |
| `ua-repeated-single-offer` | 10 | 28 | 0 | 450 |
| `ua-repeated-direct` | 0 | 0 | 0 | 488 |
| `ua-concentration` | 0 | 483 | 5 | 0 |
| `ua-better-bid-disqualified` | 9 | 55 | 0 | 424 |
| `ua-buyer-share` (v3.6) | 11 | 231 | 246 | 0 |

47 contracts with a signal, 441 zero, 0 not assessed (38 before the disqualification check). 424 of 488 contracts are direct-contract reports (reporting), out of scope; they score zero only through the concentration check. 38 of the 64 competitive contracts had a single offer. Example lead: one company won the Ministry of Health's commemorative award items repeatedly, each time as the only bidder. No negotiated procedure appears in this cohort.

The first run counted concentration in lots rather than procedures; this was corrected for both engines (see [score-ted.md](score-ted.md)). Ukrainian counts did not change.

## Points from court verdicts and bid-rigging decisions (v3.5)

Approved by the owner on 2026-10-13 (first table) and revised on 2026-10-14 after the complete data ([results](../research/calibration/ukraine-results-2026-10-14.md)). Points are Ukrainian only: other countries keep their own points, because procedures, data and enforcement differ.

Labels:

- **Convictions:** every criminal verdict 2017–2026 in the court decisions register under the official-crime articles (191, 364, 364-1, 365-2, 366, 367, 368, 369-2, 354) that convicts through a Prozorro tender (`tools/sweep-ukraine-verdicts.py`): 178 tenders quoting a tender ID (78 buyers), plus 70 linked by buyer, contract number and date ([plan](../research/calibration/ukraine-verdict-linking-plan.md); 20 of 20 spot-checked links correct). One supplier's case alone gives 47 tenders, so the main set counts **one tender per court case: 117 tenders (109 buyers)**.
- **Bid rigging:** decisions of the competition authority (AMCU) upheld in court: 873 tenders, one per case (556 buyers). A cartel needs two bidders, so these are compared only among tenders with 2+ offers.

Comparison: other tenders of the same buyers (874 for convictions, 6,878 with 2+ offers for bid rigging). Competitive procedures only. Rates count each buyer once; the likelihood ratio is shrunk toward 1 by a prior worth 10 buyers, with 95 % intervals from resampling buyers. Indicated points = 10 × log2(LR), floored at 0 (10 points each time the odds double). Points follow the convictions, one per case; the other sets check the direction ([tables](../research/calibration/ukraine-verdict-plus-linked-one-per-case-execution-points.md), `tools/ukraine-execution-points.py`).

| Check | Hit rate, convictions (one per case) | Comparisons | LR+ [95 %] | Indicated points: one per case / tender ID only / bid rigging | Points |
| --- | ---: | ---: | --- | --- | --- |
| Single offer | 23 % | 32 % | 0.75 [0.54, 0.99] | 0 / 0 / not comparable | 12 → 3 → **1** (owner decision) |
| Better-ranked bidder disqualified | 31 % | 20 % | 1.51 [1.08, 1.99] | 5.9 / 5.4 / 2.4 | 12 → 5 → **4** |
| 3–4 contract amendments | 13 % | 6 % | 1.93 [1.07, 3.37] | 9.5 / 3.3 / 4.8 | 8 → **6** |
| 5+ contract amendments | 15 % | 7 % | 2.08 [1.16, 3.53] | 10.6 / 10.3 / 1.2 | 8 → 11 → **10** |
| Term extension, any amendment count | 32 % | 11 % | 2.61 [1.87, 3.68] | 13.8 / 8.6 / 6.1 | new |
| Term extension with 0–2 amendments | 9 % | 6 % | 1.51 [0.77, 2.57] | 6.0 / 0.4 / 5.5 | **4** |
| Term extension added to 3+ amendments | 78 % of amended | 40 % of amended | 1.73 [1.34, 2.31] | 7.9 / 4.5 / 3.2 | **+6** |

- **Term extension** (`ua-term-extension`): an active contract amendment with rationale type `durationExtension` or `fiscalYearExtension`. It passed every test in both sources and is the strongest single execution signal. It is shown as its own check, but because the execution family counts only its maximum, with three or more amendments it adds its points to `ua-contract-amendments` (6 + 6 = 12 at 3–4, 10 + 6 = 16 at 5+); with fewer it scores 4 alone. The bonus is the extension's evidence *among amended contracts*, so it is not counted twice.
- **Single offer** is less frequent on convicted tenders than on the same buyers' other tenders: most of these schemes ran through competitive tenders and took the money at execution. The data give it 0 points; the owner kept **1 point** (2026-10-14) so it stays visible and filterable.
- **Better-ranked bidder disqualified:** on bid rigging most of its first strength came from bid count alone; among tenders with 2+ offers the LR is 1.18.
- Repeated single offers, concentration and direct awards keep their points: too few cases (9 repeated-single-offer tenders), or (direct award) no comparison sample with direct-award reports yet.

Robustness ([table](../research/calibration/ukraine-verdict-plus-linked-robustness.txt), `tools/ukraine-points-robustness.py`): 3+ amendments stay at LR 1.5–2.1 (6–10 points) with all linked tenders, confirmed finality only, without the largest split scheme or before 2022. A disqualified better bid ranges from LR 1.1 to 1.5 (1–6 points). A single offer depends on the 47-tender case: counting every linked tender gives LR 1.25–1.5 (3–6 points), one per case or tender IDs only give below 1. Tenders from 2022 on are too few to tell (64 positives, 37 buyers). Term extension was tested per set, not in this table. Other pre-registered candidates were tested and not added ([results](../research/calibration/ukraine-results-2026-10-14.md)); two or more disqualified bidders, a small price drop, early termination and several bid-pattern checks pass in some sets but not all.

Limits: convictions over-represent what gets prosecuted; comparisons are unlabelled, not proven clean; verdicts under appeal are not counted. In the bundled cohort contracts with a positive score go from 48 (v3.4) to 50: 38 single offers score 1, 9 disqualifications 4, the amended contract (3 amendments, one a fiscal-year extension) 12, and 5 contracts are newly flagged by a term extension.

## Large share of the buyer's yearly procurement (v3.6, approved 2026-10-14)

The owner asked for measures relative to the buyer rather than fixed amounts, so that a check can carry over to other countries. Pre-registered as R1 ([plan, part 4](../research/calibration/ukraine-candidate-indicators-plan.md#part-4-relative-size-and-closeness-to-legal-ceilings-fixed-2026-10-14-before-any-was-computed)) and tested against a census of every completed tender of the convicted buyers' years ([results](../research/calibration/ukraine-candidate-indicators.md#part-4-relative-size-and-closeness-to-legal-ceilings-2026-10-14), `tools/ukraine-relative-candidates.py`):

| Set | Hit rate, convictions | Comparisons (census) | LR+ [95 %] | Learn / check half | Indicated points |
| --- | ---: | ---: | --- | --- | --- |
| One tender per case (points basis) | 49 % (73/153) | 6 % | 8.01 [5.88, 11.21] | 6.55 / 8.15 | **30.0** [25.6, 34.9] |
| All convicted tenders | 40 % (86/320) | 6 % | 6.50 [4.79, 9.14] | 5.59 / 6.46 | 27.0 |
| Buyer-years with ≥ 20 tenders (post hoc) | 36 % | 3 % | 11.1 [8.8, 14.3] | 8.3 / 11.7 | 34.7 |

The share grows with the evidence (LR 4.8 at ≥ 1 %, 9.0 at ≥ 10 %), and the check is not driven by small buyers. It is in the competition family, so it is not added to a single offer or a disqualification on the same contract; it applies to every procedure, direct-contract reports included. **In the explorer:** the share is the contract's UAH amount over the buyer's UAH contract total for the tender's creation year in the same cohort (no currency conversion; other currencies are unknown). It is assessed only where the cohort covers the buyer's whole year: the bundled cohort runs 1 September 2024 → 1 September 2026, so only 2025 counts and the other 246 contracts are not assessed. Local imports are not assessed, because their coverage of a buyer's year is not established. The calibration counted tender values over all completed tenders; the explorer counts signed contracts, the closest measure in this cohort.

Limits: prosecutions favour large amounts, so part of the ratio reflects what gets prosecuted; large purchases are usually lawful. Two related candidates were not adopted: an amount increase close to the legal ceiling (R2) did not separate convicted tenders in Ukraine, where the total may not rise at all, and stays a candidate for countries with a numeric ceiling; a direct contract just under the open-tender threshold (R3) is being retested with complete category data.

## Better-ranked bidder disqualified (added 2026-09-26)

Prozorro opens awards one at a time in ranking order (after the e-auction, or by the evaluated price): when the top-ranked bid is rejected, its award is marked `unsuccessful` and the next bidder is considered. The importer counts, on the awarded lot, the other bidders whose award was declared unsuccessful on or before the winning award's date (`disqualifiedBefore`). One or more gives 4 points in the competition family (12 before v3.5), so it is not added to a single-offer signal on the same row. The short-bidding-period slot, out of scope here, is used for it.

- **Bid values are not compared.** Initial bid values in the record predate the e-auction, so “the lowest bid did not win” cannot be read from them reliably; the award sequence can.
- **Result:** 9 of 64 competitive contracts (8 with one bidder set aside, 1 with two), all newly flagged: Ministry of Health equipment, lift and document-system purchases under the HEAL project, polyclinic and primary-care refurbishment works, rehabilitation vehicles, road maintenance services and linoleum.
- Disqualification is often lawful (missing documents, a non-compliant or abnormally low offer). The reasons are in the award decisions on the Prozorro page, linked from each row.

On 2026-09-28 a stricter bid-attrition rule (every other bid explicitly rejected as unqualified) and a three-record contract-link sample were added on a separate branch. When the branches were merged on 2026-10-01, the disqualification check above was kept as the scored rule. The per-bid decisions (`bidAttrition`) and linked contract records are shown as context only, with no points. See [linked evidence](linked-evidence.md).

## Three or more contract amendments (v3.4, approved 2026-10-09)

**Accuracy checkpoint (11 October 2026):** a [bounded public source audit](../research/ukraine-public-audit.md) corroborated the sole three-change case and five other nonzero counts. Six sampled zero-count modules omitted `changes`. Prozorro's API source shows the serializer drops empty lists and creates `changes` only on the first posted change, so omission means zero changes and the importer's zero default is correct. The old full-cohort snapshot remains unchanged. No scores/weights were changed. [Correction log](../research/ukraine-corrections-log.md) preserves the limitation and future enrichment gate.

`ua-contract-amendments` applies to every retained signed contract, including reporting and terminated contracts. A retrieved integer `contractChanges` count of **at least 3 active changes** gives **8 points** in the execution family, combined by the family maximum rather than summed with other execution signals. Two or fewer evaluates clear. An absent contract record stays unknown: “Contract record not retrieved: amendments not assessable.” Rationale types are shown as published; this check does not assess the legality, value or duration of any amendment.

Source: the official contracting-module API, `https://public-api.prozorro.gov.ua/api/2.5/contracts/{id}`. The importer matches the row's published `contractID` to exactly one internal `contracts[].id` in its cached tender. It counts only changes with `status=active`, keeping sorted unique rationale types and sorted published `dateSigned` values. The threshold follows **StateWatch/Prozorro risk indicator ARI 1-1**. Amendments are often lawful: Law on Public Procurement art. 41 permits listed changes. Three amendments is a review threshold, not a statutory limit or evidence of an offence.

Evidence: the [2026-10-09 verdict pilot](../research/calibration/label-calibration-plan.md#results-2026-10-09-preliminary), computed by [fetch-verdict-contract-changes.py](../tools/fetch-verdict-contract-changes.py), found **4/13 corruption tenders**, **0/8 procurement-fraud tenders**, and **4/65 same-buyer, same-year comparisons** at the threshold. All-positive LR+ is about 3 with a confidence interval reaching 1. These are tender-level pilot rates, whereas the engine assesses each signed contract. The 8 points remain a uniform entry placeholder: small counts, verdict-search selection bias, 17/21 positives with presumed finality, intervals ignoring buyer matching, and unlabelled comparisons prevent stronger calibration. Payment-stage fraud may leave no amendment signal.

Collection is serial at no more than one request per second, retries 429/503 with backoff, stops on 403, and skips already retrieved ids. Only `data/prozorro-contract-changes.json` is saved: retrieval metadata, counts, rationale types, dates, status and failed ids; no names, contact points or documents. Offline rebuild merges this snapshot and records retrieved/missing row coverage. **Result (snapshot of 9 October 2026):** all 488 contract records retrieved. 469 contracts have no active amendment, 13 one, 5 two and **1 three** (an above-threshold purchase whose amendments cite fiscal-year extension and quality improvement), so **one contract is newly flagged** (0 → 8); flagged rows 47 → 48, no other score changes. The three buyers' contracts are mostly direct-contract reports, which are rarely amended.

## Licence

[Prozorro’s developer page](https://prozorro.gov.ua/openprocurement) expressly permits copying, publishing, distributing and commercial reuse of its public procurement open data, with a required reference to the source. It does not name a standard licence for the API records. A separate procurement dataset on data.gov.ua is labelled Creative Commons Attribution; we do **not** assume that catalogue label applies to this API snapshot. Source attribution and tender links are retained here; see [data-sources.md](data-sources.md).

## Audit

The [snapshot and sampled live audit](ukraine-audit.md) reconciles 542 discovered records, 526 buyer-matched tenders and 488 retained contracts. The 16 buyer-search mismatches are excluded. Offer counts agree for all 64 competitive rows. Search completeness remains unverified; do not read this as all procurement by these buyers.

## Legal anchoring (v3.3)

Reviewed 4 October 2026; no check changed. The raw tender records carry `tenderPeriod`; open tenders mostly last about 7 days, which would make a flat "short period" flag the norm. A check anchored to the legal minimum (Law 922-VIII art. 21 and the martial-law Resolution 1178 rules) needs the primary text, which was not verified (search results only), so it is a follow-up. Reporting (below-threshold direct contracts) already skips offer and direct-award checks. Counts unchanged (47 / 441 / 0).

## Reproduction

```sh
# Owner: collect once (requires network); rerun to resume
python tools/import-prozorro.py --contract-changes
python tools/import-prozorro.py --offline
node tests/national.cjs
```
