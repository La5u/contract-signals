# DECP six-city conflicts: the `id` field is often not a contract identifier

Date: 2026-10-08. Research only: **no data, scores or rules were changed** by this note. This is an assistant-led source review, not independent validation.

## Question

After the Dijon "Maison des Associations" splits (`research/decp-dijon-conflict-review.md`), 169 buyer + `id` groups in `data/decp-cities.json` remain conflicting and excluded. Are they caused by the same procedure-ID / lot pattern?

**No. That pattern explains only a handful.** Most conflicts come from `id` values that do not identify a single contract at all.

## Classification of the 169 groups (offline, mechanical)

| Groups | Pattern |
| ---: | --- |
| 135 | Same `id` on rows with different objects **and** different CPV: unrelated contracts |
| 20 | Same holder, different amounts (subsequent contracts under a framework agreement, or several lots won by one holder; unverified) |
| 6 | Lot-like: a distinct holder and amount on each row (the Dijon pattern) |
| 1 | Joint holders published one row each (`2024VDAO017006`) |
| 7 | Mixed |

By city, the 135 unrelated-contract groups are: Nantes 65, Rennes 25, Bordeaux 24, Dijon 12, Grenoble 9. Tours has none.

## Finding 1: truncated identifiers on the AWS platform (Dijon, Bordeaux, Grenoble)

- **Format.** For these buyers, conflicting `id`s are shorter than clean ones. Dijon's clean `id`s are 12–14 characters (`2024VDPA017116`); conflicting ones are typically 10 (`2024VDAO05`, `2025VDPA00`). For Bordeaux, clean `id`s have the shape `9999A9999A` and conflicting ones `9999A999` or `9999A9`.
- **National snapshot.** In the cached consolidated parquet (`~/.cache/contract-signals/decp-national/decp.parquet`), rows were matched on exact buyer, holder SIRET, amount and notification date. The `aws_marches-publics.info` feed, the source the Ministry rows declare (`source: AWS`), carries the **short** `id`. A second copy of the same buyer profile, `scrap_marches-publics.info`, often carries a **longer `id` with the short one as its prefix**: for example `2024VDAO05` → `2024VDAO0568` and `2024VDAO0550`, `2025VDPA00` → `2025VDPA0029`, `…0072`, `…0074`. Counts: Dijon 28, Bordeaux 91 and Grenoble 22 rows from the scraped source carry a longer `id`.
- **Interpretation.** The AWS DECP export appears to **truncate identifiers**, so different contracts collapse onto a shared prefix. This is strongly suggested but not confirmed with the publisher.
- **Not a mechanical fix.** The scraped `id`s give every row a distinct full `id` in only **2 of 63** conflicting AWS groups; 17 are partly resolved and 44 have none. The scraped source is incomplete, so re-keying on it alone would leave most groups ambiguous.

## Finding 2: Nantes and Rennes `id`s are not contract numbers

- **Not truncation.** Conflicting `id`s have the same shape as clean ones (`2024F00002`: year, letter, five digits), so a different cause is at work.
- **Within one buyer.** Nantes `2024F00002` covers four unrelated contracts notified between March and July 2024, under three different procedures (open call for tenders, adapted procedure, and no publicity or competition). In 65 of Nantes' 81 conflicting groups the objects differ.
- **One document check** (BOAMP award notice 24-24339, Ville de Rennes): the buyer prints **`Marché n° : 2410046`** for the contract that DECP files under **`2024S00004`**, together with an unrelated graffiti-cleaning contract. The notice also states 200,000 EUR HT, while the DECP row says 50,000. The notice describes a joint purchase by the city and Rennes Métropole, so the amounts may have different bases; this is unresolved.
- **Interpretation.** For these platforms (Atexo for Nantes, Mégalis for Rennes), DECP `id` looks like an internal or platform counter rather than the contract number. Only one document was checked, so this is **not established** for all rows.
- **Generic shape.** The same `id` shape appears under many unrelated buyers (CDC Habitat, Aix-Marseille, Ille-et-Vilaine), so cross-buyer reuse of a string is not evidence of anything.

## Consequences

- **Grouping.** Buyer + `id` is an unsafe key for these buyers, both for grouping and for "duplicate identifier" exclusion. The current behaviour of keeping conflicting groups unscored remains the correct conservative choice.
- **Clean groups may hide collisions too.** A clean-looking single-row group under a truncated or counter `id` might be one of several unrelated contracts, with the others missing from the snapshot. The national consolidator works around this itself: its `uid` appends the CPV code (`buyer + id + "_" + CPV`).
- **Any re-keying must be evidenced per row.** Splitting by distinct source row looks safe when objects, CPV and holders all differ, because those rows cannot be versions of one contract. It still needs an explicit owner decision and tests, and it must keep cross-row links rather than invent identifiers.

## Requests

- 1 Ministry exact query (lot 8, recorded in the Dijon report).
- 3 BOAMP searches (Nantes radio network: 0 results; Nantes modular buildings: no city match; Rennes financial rating: 3 notices).

Same bounded policy as before. Responses are private in `~/.cache/contract-signals/decp-id-shape-20261008/`.

## Suggested next steps (not done)

1. Owner decision: should rows under one `id` whose objects **and** CPV differ be published as separate rows linked by a "shared identifier" group, as already done for `2024VDPA66`, instead of being excluded?
2. Ask the AWS platform or Etalab/DECP maintainers whether `id` truncation is known, and whether a corrected export exists.
3. Check two or three Nantes contracts against their BOAMP award notices or the Atexo profile, to confirm what the DECP `id` represents.

## Is there another identifier? (checked 2026-10-08)

**Not inside DECP.**

- **Ministry records.** All 55 fields of the Ministry rows were tested on the 169 conflict groups. Apart from `id`, the only identifier fields are `idaccordcadre` (the parent framework, present in 42 groups), `idmodification` (amendments) and `idactesoustraitance` (subcontracting). None of them identifies a contract. Rows are distinguishable only by content: amount is distinct on every row in 159 groups, holder in 117, object in 104, notification date in 100, CPV in 97.
- **National consolidated `uid`** (`buyer + id + "_" + CPV`) is derived, not published by the buyer. For the six buyers it repeats on 925 of 5,633 values, because it mixes amendments, co-holders and unrelated contracts with the same CPV. `sourceFile` names a download batch.
- **API record IDs.** The data.economie.gouv.fr platform has internal record IDs, but they are not publisher identifiers and are not stable across refreshes. They were not used.

**Outside DECP, partially:**

- **BOAMP/TED award notices** print the buyer's contract reference (e.g. `2023vdao164207`, Rennes `2410046`), and can be linked by amount, date and holder, as done for Dijon. Only contracts with an award notice have one; many adapted procedures (MAPA) and low-value contracts have none.
- **The AWS buyer-profile copy** (`scrap_marches-publics.info` in the national snapshot) has full `id`s for some Dijon, Bordeaux and Grenoble rows. Coverage is too thin for a key: only 2 of 63 groups are fully resolved.
- **Accounting contract numbers** (DGFiP/PES Marché, as used by Tours) are not public for the other buyers.

**Consequence for option 1.** The split key has to be the row's own content: holder SIRET, amount, notification date, object and CPV. These are stable only as long as the source rows are unchanged, so the importer must fail on drift as it does now. Where a notice or full `id` exists, it should be attached as a provenance reference, never as a replacement for DECP's `id`.

## Decision and implementation (2026-10-08, owner-approved: include every contract)

- **Owner decision:** include every contract. Score the uncertain ones and flag them, without double counting.
- **Rule** (`tools/import-decp-cities.py`, `partition_contracts`). Within one buyer + `id`:
  - rows whose declared initial fields are all equal are **one contract**; modification rows repeat those columns and stay with it;
  - a group that differs only in holders, where every row declares `Conjoint`/`Solidaire`, is **one joint contract** with the holders combined;
  - every other distinct set of declared fields is **its own contract**.
- **Records and links:**
  - new records are numbered `decp-{buyer}-{id}-{n}`, ordered by date, amount, holder, object and raw row; this is stable while the source rows are unchanged;
  - all records under one published `id` are linked by `procedureGroup` (kind `shared-identifier`). The three notice-evidenced Dijon groups keep their curated lot rows (kind `lots`).
- **Possible duplicates.** Records with the same holder set, object, notification date and framework are marked `possibleDuplicateOf` each other. The relation is symmetric and transitive. They are scored individually. In the buyer-level baselines (usual publication delay, repeated single offers, supplier concentration), each cluster counts **once**: its first record by ID contributes and the others only receive the context (`duplicateShadow` in `script.js`).
- **Result (cities cohort):**

  | | Before | After |
  | --- | ---: | ---: |
  | Records | 1,270 | 1,864 |
  | Excluded | 172 | 0 |
  | Flagged | 111 | 186 |

  - 168 identifier groups split (765 linked records including the curated ones); 1 joint contract merged (`2024VDAO017006`); 95 records in 45 possible-duplicate clusters.
  - Indicators: single-bid 52 → 82, direct award 31 → 53, late publication 22 → 44, long contract 4 → 5. Repeated single bid (11), amount increase (2) and repeated direct award (3) are unchanged.
  - Amounts: every city record now carries a declared amount (missing-amount inventory 1,537 → 1,366 overall).
  - All 365 modification events are preserved. The seven former "modification conflicts" were each two different contracts' own modification no. 1.
- **Largest case:** Bordeaux `2025E0` covers 75 unrelated contracts across 2025.
- **Limits:**
  - A split record's identity rests on its declared content, not a verified identifier.
  - A "possible duplicate" may be a genuine separate lot. A non-flagged record could still be a republication if the publisher also changed its object or holder.
  - The joint merge of `2024VDAO017006` follows DECP's own `Conjoint` declaration, although award notice 24-77579 names a single winner for lot 6.
- **Document-review freeze:** the frozen six-row plan's `initial-conflict` stratum no longer exists in live data. `tests/test_prepare_document_review.py` now re-derives the selection from the frozen-time city file, pinned to commit `581fe2c` and SHA-256 `d5126b07…`, and reproduces the frozen rows and scores exactly.
