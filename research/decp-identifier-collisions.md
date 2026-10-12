# DECP six-city identifier collisions

Review: **2026-10-08**. After the Dijon splits (`research/decp-dijon-conflict-review.md`), **169** buyer + `id` groups remained excluded. Only a few followed the procedure/lot pattern.

## Findings

| Groups | Pattern |
| ---: | --- |
| 135 | Same `id` on rows with different objects **and** different CPV: unrelated contracts |
| 20 | Same holder, different amounts (subsequent contracts under a framework agreement, or several lots won by one holder; unverified) |
| 6 | Lot-like: a distinct holder and amount on each row (the Dijon pattern) |
| 1 | Joint holders published one row each (`2024VDAO017006`) |
| 7 | Mixed |

The **135 unrelated-contract groups** comprise Nantes 65, Rennes 25, Bordeaux 24, Dijon 12, Grenoble 9; none in Tours.

- **AWS truncation likely, not publisher-confirmed.** Dijon clean IDs have 12–14 characters (`2024VDPA017116`), conflicts typically 10 (`2024VDAO05`). Bordeaux clean IDs resemble `9999A9999A`, conflicts `9999A999`/`9999A9`. Exact buyer/holder/amount/date matches in `~/.cache/contract-signals/decp-national/decp.parquet` show short IDs in `aws_marches-publics.info` and longer prefixes in `scrap_marches-publics.info`: `2024VDAO05` → `2024VDAO0568`/`2024VDAO0550`; `2025VDPA00` → `…0029`/`…0072`/`…0074`. Longer IDs exist for **28 Dijon, 91 Bordeaux, 22 Grenoble rows**. Only **2 of 63** AWS groups fully resolve, **17** partly, **44** not at all.
- **Nantes/Rennes IDs may be platform counters.** Clean and conflicting IDs have the same shape. Nantes `2024F00002` covers four unrelated contracts, March–July 2024, under three procedures; **65 of 81** Nantes conflicts differ in object. Rennes notice **24-24339** prints contract **2410046**, filed under DECP **2024S00004** with an unrelated graffiti contract. Its **200,000 EUR HT** versus DECP **50,000** may reflect joint city/Métropole purchase scope; unresolved. One document does not establish the pattern for all rows.
- **No alternative DECP contract identifier.** All **55 fields** were checked: `idaccordcadre` (42 groups), `idmodification`, `idactesoustraitance` identify other things. Rows differ by amount in **159** groups, holder **117**, object **104**, date **100**, CPV **97**.
- National `uid` (`buyer + id + "_" + CPV`) is derived and repeats on **925 of 5,633** values; `sourceFile` is a batch. API record IDs are unstable. Cross-buyer ID reuse proves nothing. Even clean single-row groups may hide missing collisions.
- BOAMP/TED can supply buyer contract references where award notices exist. Scraped AWS coverage is too thin for a universal key; accounting numbers such as Tours' DGFiP/PES Marché are not public for the other buyers.

Private responses: `~/.cache/contract-signals/decp-id-shape-20261008/`. Open follow-ups: ask AWS/Etalab about truncation and check more Nantes notice/profile references.

## Decision and implementation (2026-10-08, owner-approved: include every contract)

**Include and score every contract, flag uncertainty, and avoid double counting.** `tools/import-decp-cities.py`, `partition_contracts`, partitions within buyer + `id`:

- Equal declared initial fields form one contract; modifications stay with it.
- Holder-only differences with every row `Conjoint`/`Solidaire` form one joint contract.
- Every other distinct declared-field set forms a separate contract.

Records use `decp-{buyer}-{id}-{n}`, ordered by date, amount, holder, object and raw row; stable only while source rows are unchanged. Keep published IDs and cross-links in `procedureGroup` (`shared-identifier`); three evidenced Dijon groups retain curated `lots`. Notice/full IDs are provenance, not replacements. Content-based curated splits must fail on source drift.

`possibleDuplicateOf` links equal holder/object/date/framework records symmetrically and transitively. Each scores individually, but buyer baselines count a cluster once: first ID contributes, others receive context (`duplicateShadow` in `script.js`).

| | Before | After |
| --- | ---: | ---: |
| Records | 1,270 | 1,864 |
| Excluded | 172 | 0 |
| Flagged | 111 | 186 |

- 168 identifier groups split (765 linked records including the curated ones); 1 joint contract merged (`2024VDAO017006`); 95 records in 45 possible-duplicate clusters.
- Indicators: single-bid 52 → 82, direct award 31 → 53, late publication 22 → 44, long contract 4 → 5. Repeated single bid (11), amount increase (2) and repeated direct award (3) are unchanged.
- Amounts: every city record now carries a declared amount (missing-amount inventory 1,537 → 1,366 overall).
- All 365 modification events are preserved. The seven former "modification conflicts" were each two different contracts' own modification no. 1.
- Largest collision: Bordeaux **2025E0**, **75** unrelated 2025 contracts.
- Identity rests on declared content. Possible duplicates may be separate lots; changed objects/holders can hide republications. The lot-6 joint merge follows DECP's `Conjoint` although notice **24-77579** names one winner.
- Frozen document review no longer has a live `initial-conflict` stratum. `tests/test_prepare_document_review.py` re-derives it from city data at commit **581fe2c**, SHA-256 **d5126b07…**, reproducing frozen rows/scores.
