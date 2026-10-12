# Published-data accuracy inventory

> Historical snapshot: before the **2026-10-08** DECP splits/reconciliation. The update then reported **2,219 + 2,997** French rows and **1,092** amount gaps. See `research/decp-identifier-collisions.md` and `research/france-cross-dataset-check.md`.

## Scope and reproduction

Offline: **14 datasets/18,501 rows**, including notices/lots/awards/audit dossiers; structural checks do not verify procurement facts. No data changed. `script.js`'s `const datasets` supplies non-null paths; drift fails. `dataset-metadata.js` only formats metadata. Exclude raw/coverage/combined views, `data/dataset-metadata.json` and identities.

```sh
python tools/audit-data-quality.py
python -m unittest discover -s tests -p test_audit_data_quality.py -v
# Optional aggregate export outside the repository:
python tools/audit-data-quality.py --output /tmp/contract-signals-accuracy-aggregate.json
```

**7 tests passed.** `--output -` prints JSON. Queue: `~/.cache/contract-signals/accuracy-review/review.jsonl` (`--review-dir`), **0700/0600**, atomically replaced, only ID/path/fixed reasons. Public aggregates omit identities/text/URL values. Null and declared zero stay separate; zero missing amount keys, negative/non-numeric amounts (booleans are non-numeric).

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

Currency is explicit on **11,522** rows; **6,979** meet the UI's legacy EUR-default condition, which the audit does not apply. No invalid uppercase three-letter syntax was found; ISO membership is untested. Of absent currencies, **6,950** are French and **29** are UK 9, Portugal 1, Czechia 19.

Dates: **18,251** valid top-level `date` values (YYYY-MM-DD), **9,419** valid `publicationDate` values (date/zoned timestamp), **0 invalid**. Semantics, chronology and history dates are untested; an absent mapped publication date need not be absent upstream.

## Text, provenance and review priorities

- Description placeholders: **139 cities/1 UK**; empty suppliers: **66 Tours, 151 cities, 10 consultations, 6 BOAMP**; identifier-only: **1,119 cities/2,591 history**. Totals **140/233/3,710**. All other datasets zero. No empty descriptions/buyers, exact-vocabulary supplier placeholders or non-text values; vocabulary checks are not semantic review.
- Initial/modification/any conflicts: cities **172/7/172**, history **355/0/355**, total **527/7/527**, others zero. Counts overlap; no derived identity-ambiguous rows. Review source versions before choosing alternatives.
- Queue counts: Tours **66**, cities **1,270**, consultations **10**, history **2,594**, BOAMP **3,010**, Colombia **7,560**, Paraguay **84/293**, Ukraine **488**, Chile **522**, UK **10**, Portugal **1**, Czechia **24**, Romania **0**; union **15,932**, not alleged errors.
- All **18,501** rows have `dataStatus: verified` and structurally valid HTTP(S) `source`; zero missing/other statuses or invalid/missing URLs. No missing/invalid IDs, within-dataset duplicate-ID groups or duplicate/excess rows. Links/facts and cross-dataset duplication were not checked.
- Review **154 zeros** separately from **1,383 nulls**, by exact source/basis. Clarify currency defaults from importer evidence, not country-based filling.
- Tours/consultations account for **76** missing dates/empty suppliers. Other missing dates **174**: cities 142, BOAMP 29, Paraguay three-buyer 1, Czechia 2. Review publication-date semantics before backfill.
- Review text usefulness and **157** empty suppliers outside notices (151 cities/6 BOAMP); identifier-only labels need enrichment, not invented names.
