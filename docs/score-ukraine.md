# Ukraine method — Prozorro checks (v3.0 framework)

**Checks for the Prozorro cohort** (three buyers, tenders created 2024-09-01 → 2026-09-01). Same vigilance-index framework as [score-v3.md](score-v3.md): two families, family maxima, cap at 100, `null` = “Not assessed”, unknowns never counted as zero. Different checks and eligibility; French, Colombian and Paraguayan rules are not applied. Amounts stay in the published currency (UAH, sometimes EUR or USD) and are never converted.

An editorial sorting tool, not a probability, not a measure of legal gravity, not a certificate of regularity. Wartime rules allow procurement exceptions and withheld publications: a missing record or bid is not evidence of anything, and a zero is not clearance.

## Data

Records are the **official** tender records of the Prozorro public API (`public-api.prozorro.gov.ua/api/2.5`). The prozorro.gov.ua site search is used only to list each buyer's tender IDs; every row comes from the official record. One row is one signed contract (active or terminated) linked to an active award with exactly one supplier.

## How the checks were chosen

Written on 25 September 2026, before any record of this cohort was read. Procedure types are classified by their meaning in the Prozorro standard, not by results:

- **Competitive:** aboveThreshold (and EU/UA/defense variants), belowThreshold, competitiveDialogue (and stage 2), competitiveOrdering, esco, simple.defense, requestForProposal, priceQuotation, closeFrameworkAgreement(Selection)UA.
- **Without competition:** negotiation, negotiation.quick.
- **Not scored:** reporting — a direct-contract report recorded without a procedure, mostly for low-value purchases; like the bare Colombian direct modality, its base rate makes it uninformative on its own.

## The eight checks

| Check | ID | Family | Eligibility / trigger | Weight |
| --- | --- | --- | --- | --- |
| Single offer in a competitive procedure | `ua-single-offer` | Competition | Competitive type; offers on the awarded lot = 1 (bids whose lot values point to that lot, excluding deleted and draft bids) | **12** |
| Award without competition | `ua-direct-award` | Competition | negotiation / negotiation.quick | **18** |
| Repeated single-offer awards | `ua-repeated-single-offer` | Competition | This award is single-offer; same buyer and supplier (EDRPOU or individual tax number) in ≥3 distinct tenders | **12 at 3 → 40 at 10** |
| Repeated awards without competition | `ua-repeated-direct` | Competition | This award is negotiated; same buyer and supplier in ≥3 distinct tenders | **18 at 3 → 60 at 10** |
| Concentrated awards | `ua-concentration` | Competition | Same buyer and main category (goods, works, services); ≥10 contracts, ≥80 % identified, share ≥60 % | **12 at 60 % → 40 at 100 %** |
| Amount increase | `amount-increase` | Execution | **Out of scope**: contract changes are in the separate contracting API, not imported | — |
| Better-ranked bidder disqualified | `ua-better-bid-disqualified` | Competition | Competitive type; on the awarded lot, at least one award to another bidder was declared unsuccessful before this award (added 2026-09-26) | **12**, flat |
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

## Licence

The publisher declares no licence for the data (the Open Contracting data registry lists none). Prozorro data are published as open data under Ukrainian procurement law; confirm the terms before redistribution. Listed in [data-sources.md](data-sources.md) as “to confirm”, like BOAMP.

## Reproduction

```sh
python tools/import-prozorro.py --offline
node tests/national.cjs
```
