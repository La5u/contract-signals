# United Kingdom method — Find a Tender checks (v3.0 framework)

**Checks for the Find a Tender cohort** (three buyer accounts, award releases 2024-09-01 → 2026-09-01). Same vigilance-index framework as [score-v3.md](score-v3.md): two families, family maxima, cap at 100, `null` = “Not assessed”, unknowns never counted as zero. The checks are those of the shared national engine used for Ukraine and TED ([score-ukraine.md](score-ukraine.md), [score-ted.md](score-ted.md)), read from the OCDS fields Find a Tender publishes. French, Colombian and Paraguayan rules are not applied. Amounts stay in the published currency (mostly GBP; embassies abroad also contract in EUR, USD, CHF, JPY and BGN) and are never converted.

An editorial sorting tool, not a probability, not a measure of legal gravity, not a certificate of regularity.

## Data and selection

Find a Tender publishes above-threshold notices and, since the Procurement Act 2023 came into force on 24 February 2025, the notices of that regime; smaller contracts are not covered. Records come from the official OCDS API (`/api/1.0/ocdsReleasePackages`, Open Government Licence v3.0).

The API cannot filter by buyer, so the cohort was chosen in two steps:

1. **Index** (`--discover`): every award release of the window, in one-day windows, keeping only the notice id, release date, buyer party ids, names and TED buyer type: **33,457 award releases, 6,993 buyer ids**. The API cursor repeats releases across pages and, over month-long windows, skips some (September 2024: 366 unique releases by month against 1,759 by day); one-day windows deduplicated by notice id matched 24 one-hour windows exactly on a test day.
2. **Announcement, 26 September 2026, before any notice was downloaded or read.** Rule applied to the index only (volume and buyer type): per level, the buyer id with the most award notices in the window, leaving out ids above 500 notices so the cohort stays reviewable.
   - national (central government ministry): **Foreign, Commonwealth and Development Office**, `GB-FTS-131`, 87 notices;
   - regional (county council): **Lincolnshire County Council**, `GB-FTS-39`, 141 notices (Surrey County Council, 1,841, is above the cap);
   - municipal (city or borough council): **Milton Keynes Council**, `GB-FTS-289`, 288 notices (the London Borough of Merton, 1,033, is above the cap; the Sutton–Kingston joint account is not a single council).

One id is one buyer: an organisation often has several Find a Tender accounts (the Ministry of Defence has at least six), and they are **not merged by name**. The 516 notices of the three ids were then downloaded in full (`--download`).

One row is one **active award to exactly one supplier, on one lot**: 1,081 awards. Excluded: 147 unsuccessful awards and 5 multi-supplier awards (frameworks, dynamic purchasing systems: no single holder). Contact points (names, emails, telephones) are never imported.

## The eight checks

| Check | ID | Family | Eligibility / trigger | Weight |
| --- | --- | --- | --- | --- |
| Single offer in a competitive procedure | `uk-single-offer` | Competition | `procurementMethod` open or selective; the `bids` statistic of the awarded lot = 1 | **12** |
| Award without prior publication | `uk-direct-award` | Competition | `procurementMethod` limited (award without prior publication, negotiated without publication, Procurement Act direct award) | **18** |
| Repeated single-offer awards | `uk-repeated-single-offer` | Competition | This award is single-offer; same buyer and supplier id in ≥3 distinct procedures (OCIDs) | **12 at 3 → 40 at 10** |
| Repeated awards without publication | `uk-repeated-direct` | Competition | This award is limited; same buyer and supplier id in ≥3 distinct procedures | **18 at 3 → 60 at 10** |
| Concentrated awards | `uk-concentration` | Competition | Same buyer and CPV division; ≥10 procedures, ≥80 % with an identified winner, share ≥60 % | **12 at 60 % → 40 at 100 %** |
| Amount increase | `amount-increase` | Execution | **Out of scope**: contract change notices are separate, not imported | — |
| Short bidding period | `short-bidding-period` | Competition | **Out of scope** | — |
| Long declared duration | `long-contract` | Execution | **Out of scope** | — |

- **Offers** come from the notice's `bids` statistic for the awarded lot (or the notice-level statistic when there is one lot); missing means unknown, never zero. In some multi-lot dynamic-purchasing notices every lot carries the same count, which may be a notice total: it is used as published.
- **Supplier identity** is the Find a Tender party id (`GB-FTS-…`). In this cohort an id is never shared by two different supplier names, but one company can have several ids (24x7 Ltd has eight), so repetition and concentration can only be **undercounted**. No Companies House number is published for any supplier of these three buyers.
- **Procurement method missing** on 6 notices (5 rows): unknown, never inferred from a title, even one that says “Direct Award”.

## Results

Reproduced by `tests/national.cjs`.

| Check | Signals | Clear | Unknown | Out of scope |
| --- | ---: | ---: | ---: | ---: |
| `uk-single-offer` | 20 | 1,031 | 7 | 23 |
| `uk-direct-award` | 23 | 1,053 | 5 | 0 |
| `uk-repeated-single-offer` | 4 | 16 | 7 | 1,054 |
| `uk-repeated-direct` | 0 | 23 | 5 | 1,053 |
| `uk-concentration` | 0 | 359 | 722 | 0 |

**43 awards with a signal, 1,036 zero, 2 not assessed.** By buyer: FCDO 26 of 87, Milton Keynes 13 of 288, Lincolnshire 4 of 706 (mostly school and SEND transport lots of a dynamic purchasing system, with many offers).

- **Examples read.** Awards without prior publication are all FCDO: energy supply for a mission abroad, patrol vessels for Montserrat and the Turks and Caicos Islands, stabilisation and sanctions-implementation programmes, legal advice: often lawful routes (urgency, overseas security, extension of an incumbent), not assessed here. Single offers: Milton Keynes home-care lots by age band (one provider, Chiltern Healthcare, won four 0–15 years lots alone, hence the repetition signal), embassy medical insurance, office supplies and guarding, a Lincolnshire NHS health-check area.
- **Unflagged near-misses:** 1,031 competitive awards had two offers or more (764 had ten or more). Concentration is mostly unknown (722): few buyer/CPV-division groups reach ten distinct procedures.

## Reproduction

```sh
python tools/import-find-a-tender.py --offline               # rebuild from the raw notices
python tools/import-find-a-tender.py --discover --download   # new index and notices (network, about 40 minutes)
node tests/national.cjs
```
