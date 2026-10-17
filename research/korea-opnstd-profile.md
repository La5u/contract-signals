# South Korea: national open-standard contracts, first profile (2026-10-16)

Source: PPS open-standard contracts (data.go.kr 15058815, licence 제한 없음), every contract version signed 2024-09-01..2026-09-01, downloaded by `tools/fetch-korea-opnstd-contracts.py` in 105 weekly files (each matched a fresh `totalCount`, shortfall 0 everywhere; 2,700-odd calls). Organised by `tools/normalize-korea-opnstd.py` into `~/.cache/contract-signals/korea/opnstd.sqlite` (5.1 GB, private cache, not bundled). Snapshot dates (`dataBssDate`) 2026-10-16 and 2026-10-17.

## Structure

- **One row is a contract version**, not a contract: `cntrctOrd` 00 is the original, 01, 02, … later changes, each dated by its own signature date (so each week holds the changes made that week). 3,743,496 versions; 2,725,329 contract numbers; **2,526,389 contracts originally signed in the period**. The rest are older contracts seen only through a change in the period.
- Changes are right-censored at 2026-09-01: a contract signed late in the period has had less time to be changed. Among originals: 0 changes 1,906,201; 1: 450,929; 2: 120,412; 3+: 48,847.
- `prvtcntrctRsn` is filled on every row, competitive or not: it is the **legal basis**, ending in a bracketed statute reference (as cited by the source; extracted to `legal_ref`, 261 distinct, missing on 2,499 originals).
- Only the representative firm of a joint contract is named (`cmmnCntrctYn` = Y on 5,659 contracts). The supplier changes between versions on 2,751.
- Unit-price contracts (제3자단가계약, 일반단가계약; about 3 % of rows) carry ceilings or unit terms, not a total spend.
- 612 originals have no or zero amount. Some reserve prices have decimals (kept as numbers).

## Contracts signed in the period

| Method | Contracts | Amount (trillion KRW) | With a bid notice |
| --- | ---: | ---: | ---: |
| 수의계약 (private contract) | 2,237,285 | 102.95 | 17.3 % |
| 제한경쟁 (restricted competition) | 208,260 | 149.53 | 88.1 % |
| 일반경쟁 (open competition) | 69,748 | 103.30 | 70.6 % |
| 지명경쟁 (nominated competition) | 10,794 | 5.46 | 68.4 % |
| 기타 / missing | 302 | 0.09 | — |

Private contracts are 89 % of contracts but 28 % of value: 1,571,089 are under KRW 20 million, 7,977 at KRW 1 billion or more. The commonest grounds are the small-value thresholds (local: 지방계약법 제25조제1항5호나목 1,023,516 and 가목 515,832; national: 국가계약법 제26조제1항5호가2목 141,558), then set-asides for women-owned, disabled-owned and social enterprises, small businesses and research work. **A private contract after a competition with a single bidder** is its own ground (국가계약법 제27조제3항, 16,760) next to re-tendering (제27조제1항, 14,135): a candidate for the single-offer check.

By business type: services 1,227,406, works 806,844, goods 490,965, foreign purchases 1,174. By buyer type: local governments 1,260,355, education 600,037, national bodies 192,496, others below. 25,495 buyers (contracting-institution codes) and 246,285 suppliers (registration numbers).

## Privacy

Dropped at load: names, phones and e-mails of buyer officials, the supplier's representative (CEO) and contact, and the supplier's street address (province and district kept). Kept: company name and business registration number. **81,488 suppliers (531,353 contracts) are individual businesses** by the registration number's middle digits (01–79, 90–99): their trade name can be a person's name. Owner decision 2026-10-16: show these names as published, flagged `supplierIndividual` and left out of exports only ([rule](../docs/personal-data.md#individual-suppliers-project-wide-rule-2026-10-16)).

## Next

1. Choose the explorer buyers (national, regional, municipal) from `contracts` by count.
2. Write the Korean check rules and thresholds from the statute text before computing (plan step 3), using `legal_ref` for the private-contract grounds.
3. Offer counts are not in this source: they need the bid-opening results (`getOpengResultListInfo*`, 1,000 calls/day) for competitive contracts with a `notice_no`.
