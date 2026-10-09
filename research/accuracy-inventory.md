# Published-data accuracy inventory

> **Snapshot note (2026-10-08):** counts below predate the DECP identifier splits and buyer-feed reconciliation of 2026-10-08 (French cohorts now 2,219 + 2,997 records; missing-amount gaps 1,092). See `research/decp-identifier-collisions.md` and `research/france-cross-dataset-check.md`.

## Scope and reproduction

This is an offline inventory of the current checkout's **14 published datasets / 18,501 normalized rows**, not validated contracts. Rows can represent notices, lots, awards or multi-order audit dossiers. Counts do not establish correctness, completeness, legality, actual payments or unique contracts. No published data, UI or existing code was changed for this inventory.

`script.js`'s explicit `const datasets` registry defines the inventory. `dataset-metadata.js` validates/formats collection and coverage metadata; it does not define the dataset list. The tool reads only non-null dataset paths in the registry, excluding the combined/local views, raw responses, coverage files, `data/dataset-metadata.json`, supplier identities and unrelated research outputs. Registry-format drift raises an error rather than falling back to a broad file glob.

Run from the repository root:

```sh
python tools/audit-data-quality.py
python -m unittest discover -s tests -p test_audit_data_quality.py -v
# Explicit opt-in aggregate export, outside the repository:
python tools/audit-data-quality.py --output /tmp/contract-signals-accuracy-aggregate.json
```

The actual audit and all **7 unit tests passed**. Tests cover absent versus null versus declared zero, booleans/non-finite values, invalid calendar dates and timestamps, duplicate IDs, conflict overlap and derived DECP identity ambiguity, conservative placeholder matching, metadata skipping, privacy, queue replacement and permissions. The default run does not write aggregate JSON. `--output -` explicitly prints the aggregate JSON instead.

The private queue is `~/.cache/contract-signals/accuracy-review/review.jsonl`, with directory mode **0700** and file mode **0600**. It contains only `id`, `dataset_path` and fixed reason codes, one entry per reviewable row, and is replaced atomically on rerun. IDs are exact published row IDs, not buyer/supplier identifiers. Missing/invalid row IDs would be represented as null (none occurred here). Keep this queue private; do not commit or publish it. `--review-dir` overrides its location. Public aggregates contain no row IDs, personal identifiers, names, descriptions, source URL values or arbitrary status/conflict text.

## Amounts, currency and dates

“Absent amount” below is explicit null. There were **0 missing amount keys**, **0 negative amounts**, and **0 non-numeric amounts** across the inventory. Booleans count as non-numeric in the tool, never as zero or one. A numeric zero is **declared zero**, not a claim that the contract was free or incorrectly reported.

| Dataset key | Published path | Rows | Amount null | Zero declared | Positive | Currency absent | `date` missing | `publicationDate` missing |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| tours | `data/tours-notices.json` | 66 | 66 | 0 | 0 | 66 | 66 | 0 |
| cities | `data/decp-cities.json` | 1,270 | 171 | 0 | 1,099 | 1,270 | 142 | 127 |
| consultations | `data/consultations.json` | 10 | 10 | 0 | 0 | 10 | 10 | 0 |
| decp | `data/decp-history.json` | 2,594 | 355 | 0 | 2,239 | 2,594 | 0 | 0 |
| boamp | `data/contracts.json` | 3,010 | 752 | 102 | 2,156 | 3,010 | 29 | 8 |
| colombia | `data/colombia-secop2.json` | 7,560 | 0 | 49 | 7,511 | 0 | 0 | 7,560 |
| paraguay | `data/paraguay-dncp.json` | 84 | 0 | 0 | 84 | 0 | 0 | 84 |
| paraguay3 | `data/paraguay-dncp-3buyers.json` | 293 | 0 | 0 | 293 | 0 | 1 | 293 |
| ukraine | `data/prozorro.json` | 488 | 0 | 0 | 488 | 0 | 0 | 488 |
| chile | `data/chile-mp.json` | 522 | 0 | 0 | 522 | 0 | 0 | 522 |
| uk | `data/uk-fts.json` | 1,081 | 9 | 0 | 1,072 | 9 | 0 | 0 |
| portugal | `data/ted-portugal.json` | 493 | 1 | 0 | 492 | 1 | 0 | 0 |
| czechia | `data/ted-czechia.json` | 674 | 19 | 3 | 652 | 19 | 2 | 0 |
| romania | `data/ted-romania.json` | 356 | 0 | 0 | 356 | 0 | 0 | 0 |
| **Total** | | **18,501** | **1,383** | **154** | **16,964** | **6,979** | **250** | **9,082** |

Currency is explicit on **11,522 rows**. The **6,979 absent currencies** also meet the current UI's legacy EUR-default condition (absent/falsy currency and no assessmentMode). The inventory does not apply that default or silently infer currency from country or amount. There were **0 invalid currency syntax values**. Validation checks uppercase three-letter syntax only, **not ISO membership**, and no currencies are converted or amounts summed.

Date validation covers only top-level `date` (strict YYYY-MM-DD) and `publicationDate` (date or zoned ISO timestamp). There were **0 invalid values** in either field; **18,251** `date` values and **9,419** publication dates were structurally valid. This does not validate signature/notification/award/publication semantics, chronology or dates inside histories/notice chains. Missing publicationDate is a schema-presence observation, not proof that the source lacks a publication date.

## Text, provenance and exclusions

| Dataset key | Description placeholders | Empty suppliers | Identifier-only suppliers | Initial conflict rows | Modification conflict rows | Any conflict exclusion rows | Private review rows |
|---|---:|---:|---:|---:|---:|---:|---:|
| tours | 0 | 66 | 0 | 0 | 0 | 0 | 66 |
| cities | 139 | 151 | 1,119 | 172 | 7 | 172 | 1,270 |
| consultations | 0 | 10 | 0 | 0 | 0 | 0 | 10 |
| decp | 0 | 0 | 2,591 | 355 | 0 | 355 | 2,594 |
| boamp | 0 | 6 | 0 | 0 | 0 | 0 | 3,010 |
| colombia | 0 | 0 | 0 | 0 | 0 | 0 | 7,560 |
| paraguay | 0 | 0 | 0 | 0 | 0 | 0 | 84 |
| paraguay3 | 0 | 0 | 0 | 0 | 0 | 0 | 293 |
| ukraine | 0 | 0 | 0 | 0 | 0 | 0 | 488 |
| chile | 0 | 0 | 0 | 0 | 0 | 0 | 522 |
| uk | 1 | 0 | 0 | 0 | 0 | 0 | 10 |
| portugal | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| czechia | 0 | 0 | 0 | 0 | 0 | 0 | 24 |
| romania | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Total** | **140** | **233** | **3,710** | **527** | **7** | **527** | **15,932** |

- There were **0 empty descriptions**, **0 empty/placeholder buyers**, **0 exact-vocabulary supplier placeholders** and **0 non-text values** in these three fields. Identifier-only suppliers are reported separately from empty/placeholder values: they are not invented names, and retaining them can be intentional. Placeholder detection is conservative, using the tool's fixed exact vocabulary; it is not a semantic assessment of meaningful descriptions.
- All **18,501 rows** have `dataStatus: verified`; there were **0 unverified, synthetic, missing or other statuses**. This is the published provenance label, not independent validation by this audit.
- All **18,501 rows** have a structurally present HTTP(S) `source` URL; **0 missing** and **0 invalid** primary source URLs. No link was fetched, so reachability and exact-record relevance remain untested. Alternate verification links are not substituted for the primary source field.
- There were **0 missing/invalid record IDs**, **0 within-dataset duplicate record-ID groups**, and **0 duplicate rows/excess rows**. The tool does not deduplicate across datasets or equate different source identifiers.
- **527 rows** have initial conflict markers. All **7 modification-conflict rows** are already among those 527; exclusion columns must not be added. **0 identity-ambiguous rows** were found, including DECP ambiguity derived from repeated buyerSiret/contractId pairs as in `script.js`. These are normalized-row markers, not counts of raw duplicate source publications or a complete reproduction of indicator eligibility.
- The **15,932 review rows** are the union of all reason codes, not 15,932 alleged errors. Expected missing publication dates, legacy currency defaults, supplier identifiers and notice-only fields account for broad inclusion.

## Action priorities (review, not automatic corrections)

1. **Review the 154 declared zeros separately from the 1,383 null amounts.** Exact-ID triage: BOAMP 102, Colombia 49, Czechia 3. Compare declared source fields and amount basis before interpreting a zero. Do not replace zero with null, or null with zero, merely from this inventory.
2. **Keep the 527 conflict rows excluded where the existing UI rules require it.** Prioritize exact source-version review of 172 city rows (including 7 modification conflicts) and 355 history rows. Do not select a “correct” version by amount, date or plausibility without source evidence.
3. **Clarify explicit currency versus legacy EUR defaults.** Most absent currencies are on the five French datasets (6,950 rows); UK 9, Portugal 1 and Czechia 19 account for the remaining 29. Any future schema change should be supported by importer/source evidence rather than blanket country-based filling. No schema change is made here.
4. **Separate expected notice gaps and unmapped publication dates from actionable missing contract dates.** Tours and consultations contribute 76 missing dates and 76 empty suppliers on notice rows. The other 174 missing dates are cities 142, BOAMP 29, Paraguay three-buyer 1 and Czechia 2. PublicationDate absence spans whole international cohorts and must be investigated as mapping/semantics before attempting backfill.
5. **Review text usefulness without inferring names.** There are 139 city description placeholders and 1 UK placeholder; 157 empty suppliers outside the 76 notice rows (151 cities, 6 BOAMP). The 3,710 identifier-only supplier labels are a separate enrichment question, not a reason to fabricate a supplier name or publish personal identifiers in this report.
6. **Treat the clean structural checks narrowly.** No duplicate row IDs, malformed dates, missing primary source links, negative/non-numeric amounts or non-verified labels were found in this inventory. That is not evidence that contracts or source declarations are correct. Source-link checks, exact-record comparison, temporal semantics and coverage validation remain separate work.
