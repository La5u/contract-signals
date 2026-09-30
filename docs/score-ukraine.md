# Ukraine method — Prozorro checks (v3.0 framework)

**Checks for the Prozorro cohort** (three buyers, tenders created 2024-09-01 → 2026-09-01). Same vigilance-index framework as [score-v3.md](score-v3.md): two families, family maxima, cap at 100, `null` = “Not assessed”, unknowns never counted as zero. Different checks and eligibility; French, Colombian and Paraguayan rules are not applied. Amounts stay in the published currency (UAH, sometimes EUR or USD) and are never converted.

An editorial sorting tool, not a probability, not a measure of legal gravity, not a certificate of regularity. Wartime rules allow procurement exceptions and withheld publications: a missing record or bid is not evidence of anything, and a zero is not clearance.

## Data

Records are the **official** tender records of the Prozorro public API (`public-api.prozorro.gov.ua/api/2.5`). The prozorro.gov.ua site search is used only to list each buyer's tender IDs; every row comes from the official record. One row is one signed contract (active or terminated) linked to an active award with exactly one supplier.

## How the checks were chosen

Written on 25 September 2026, before any record of this cohort was read. Procedure types are classified by their meaning in the Prozorro standard, not by results:

- **Competitive:** aboveThreshold (and EU/UA/defense variants), belowThreshold, competitiveDialogue (and stage 2), competitiveOrdering, esco, simple.defense, requestForProposal, priceQuotation, closeFrameworkAgreement(Selection)UA.
- **Without competition:** negotiation, negotiation.quick.
- **Offer/direct-award checks excluded:** reporting — a direct-contract report recorded without a procedure. Reporting alone adds no points; the concentration check still applies.

## The checks (nine with linked bid attrition)

| Check | ID | Family | Eligibility / trigger | Weight |
| --- | --- | --- | --- | --- |
| Single offer in a competitive procedure | `ua-single-offer` | Competition | Competitive type; offers on the awarded lot = 1 (bids whose lot values point to that lot, excluding deleted and draft bids) | **12** |
| Award without competition | `ua-direct-award` | Competition | negotiation / negotiation.quick | **18** |
| Repeated single-offer awards | `ua-repeated-single-offer` | Competition | This award is single-offer; same buyer and supplier (EDRPOU or individual tax number) in ≥3 distinct tenders | **12 at 3 → 40 at 10** |
| Repeated awards without competition | `ua-repeated-direct` | Competition | This award is negotiated; same buyer and supplier in ≥3 distinct tenders | **18 at 3 → 60 at 10** |
| Concentrated awards | `ua-concentration` | Competition | Same buyer and main category (goods, works, services); ≥10 distinct procedures with identified suppliers, ≥80 % identification coverage, share ≥60 % | **12 at 60 % → 40 at 100 %** |
| Other submitted bids explicitly disqualified | `ua-bid-attrition` | Competition | Completed competitive tender; ≥2 bids; every bid uniquely linked to a lot award decision; winner explicitly qualified/eligible, every other bid explicitly unqualified | **5** |
| Amount increase | `amount-increase` | Execution | **Out of scope**: three contract links checked, but no comparable dated amendment history | — |
| Short bidding period | `short-bidding-period` | Competition | **Out of scope** | — |
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
| `ua-bid-attrition` | 0 | 0 | 26 | 462 |

38 contracts with a signal, 450 zero, 0 not assessed. 424 of 488 contracts are direct-contract reports (reporting). Their offer/direct-award checks are out of scope; their zeros come from the concentration check. 38 of the 64 competitive contracts had a single offer. Example lead: one company won the Ministry of Health's commemorative award items repeatedly, each time as the only bidder. No negotiated procedure appears in this cohort.

The first run counted concentration in lots rather than procedures; this was corrected for both engines (see [score-ted.md](score-ted.md)). Ukrainian counts did not change.

The bid-attrition rule and three-record contract-link sample were added on 2026-09-28 after inspecting existing fields. See [linked evidence](linked-evidence.md) for eligibility, unknown states, collection limits and why amendments still earn no points.

## Licence

[Prozorro’s developer page](https://prozorro.gov.ua/openprocurement) expressly permits copying, publishing, distributing and commercial reuse of its public procurement open data, with a required reference to the source. It does not name a standard licence for the API records. A separate procurement dataset on data.gov.ua is labelled Creative Commons Attribution; we do **not** assume that catalogue label applies to this API snapshot. Source attribution and tender links are retained here; see [data-sources.md](data-sources.md).

## Audit

The [snapshot and sampled live audit](ukraine-audit.md) reconciles 542 discovered records, 526 buyer-matched tenders and 488 retained contracts. The 16 buyer-search mismatches are excluded. Offer counts agree for all 64 competitive rows. Search completeness remains unverified; do not read this as all procurement by these buyers.

## Reproduction

```sh
python tools/import-prozorro.py --offline
node tests/national.cjs
```
