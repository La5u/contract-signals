# Ukraine method — Prozorro checks (v3.4 framework)

**Checks for the Prozorro cohort** (three buyers, tenders created 2024-09-01 → 2026-09-01). Same vigilance-index framework as [score-v3.md](score-v3.md): two families, family maxima, cap at 100, `null` = “Not assessed”, unknowns never counted as zero. Different checks and eligibility; French, Colombian and Paraguayan rules are not applied. Amounts stay in the published currency (UAH, sometimes EUR or USD) and are never converted.

An editorial sorting tool, not a probability, not a measure of legal gravity, not a certificate of regularity. Wartime rules allow procurement exceptions and withheld publications: a missing record or bid is not evidence of anything, and a zero is not clearance.

## Data

Records are the **official** tender records of the Prozorro public API (`public-api.prozorro.gov.ua/api/2.5`). The prozorro.gov.ua site search is used only to list each buyer's tender IDs; every row comes from the official record. One row is one signed contract (active or terminated) linked to an active award with exactly one supplier.

## How the checks were chosen

Written on 25 September 2026, before any record of this cohort was read. Procedure types are classified by their meaning in the Prozorro standard, not by results:

- **Competitive:** aboveThreshold (and EU/UA/defense variants), belowThreshold, competitiveDialogue (and stage 2), competitiveOrdering, esco, simple.defense, requestForProposal, priceQuotation, closeFrameworkAgreement(Selection)UA.
- **Without competition:** negotiation, negotiation.quick.
- **Offer/direct-award checks excluded:** reporting — a direct-contract report recorded without a procedure. Reporting alone adds no points; the concentration check still applies.

## The checks (ten with the universal late-publication check)

| Check | ID | Family | Eligibility / trigger | Weight |
| --- | --- | --- | --- | --- |
| Single offer in a competitive procedure | `ua-single-offer` | Competition | Competitive type; offers on the awarded lot = 1 (bids whose lot values point to that lot, excluding deleted and draft bids) | **12** |
| Award without competition | `ua-direct-award` | Competition | negotiation / negotiation.quick | **18** |
| Repeated single-offer awards | `ua-repeated-single-offer` | Competition | This award is single-offer; same buyer and supplier (EDRPOU or individual tax number) in ≥3 distinct tenders | **12 at 3 → 40 at 10** |
| Repeated awards without competition | `ua-repeated-direct` | Competition | This award is negotiated; same buyer and supplier in ≥3 distinct tenders | **18 at 3 → 60 at 10** |
| Concentrated awards | `ua-concentration` | Competition | Same buyer and main category (goods, works, services); ≥10 distinct procedures with identified suppliers, ≥80 % identification coverage, share ≥60 % | **12 at 60 % → 40 at 100 %** |
| Amount increase | `amount-increase` | Execution | **Out of scope**: three contract links checked, but no comparable dated amendment history | — |
| Better-ranked bidder disqualified | `ua-better-bid-disqualified` | Competition | Competitive type; on the awarded lot, at least one award to another bidder was declared unsuccessful before this award (added 2026-09-26) | **12**, flat |
| Three or more contract amendments | `ua-contract-amendments` | Execution | Signed contract; retrieved integer count of active amendments ≥3 | **8**, flat |
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

47 contracts with a signal, 441 zero, 0 not assessed (38 before the disqualification check). 424 of 488 contracts are direct-contract reports (reporting), out of scope; they score zero only through the concentration check. 38 of the 64 competitive contracts had a single offer. Example lead: one company won the Ministry of Health's commemorative award items repeatedly, each time as the only bidder. No negotiated procedure appears in this cohort.

The first run counted concentration in lots rather than procedures; this was corrected for both engines (see [score-ted.md](score-ted.md)). Ukrainian counts did not change.

## Better-ranked bidder disqualified (added 2026-09-26)

Prozorro opens awards one at a time in ranking order (after the e-auction, or by the evaluated price): when the top-ranked bid is rejected, its award is marked `unsuccessful` and the next bidder is considered. The importer counts, on the awarded lot, the other bidders whose award was declared unsuccessful on or before the winning award's date (`disqualifiedBefore`). One or more gives 12 points in the competition family, so it is not added to a single-offer signal on the same row. The short-bidding-period slot, out of scope here, is used for it.

- **Bid values are not compared.** Initial bid values in the record predate the e-auction, so “the lowest bid did not win” cannot be read from them reliably; the award sequence can.
- **Result:** 9 of 64 competitive contracts (8 with one bidder set aside, 1 with two), all newly flagged: Ministry of Health equipment, lift and document-system purchases under the HEAL project, polyclinic and primary-care refurbishment works, rehabilitation vehicles, road maintenance services and linoleum.
- Disqualification is often lawful (missing documents, a non-compliant or abnormally low offer). The reasons are in the award decisions on the Prozorro page, linked from each row.

On 2026-09-28 a stricter bid-attrition rule (every other bid explicitly rejected as unqualified) and a three-record contract-link sample were added on a separate branch. When the branches were merged on 2026-10-01, the disqualification check above was kept as the scored rule. The per-bid decisions (`bidAttrition`) and linked contract records are shown as context only, with no points. See [linked evidence](linked-evidence.md).

## Three or more contract amendments (v3.4, approved 2026-10-09)

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
