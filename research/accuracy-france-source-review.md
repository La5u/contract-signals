# France source accuracy review — offline reconciliation

Review run: **2026-10-07 UTC**, repository HEAD `581fe2c98e64e66ed5fd3964f599115f8e42767f`, against the working-tree snapshots identified below. This is a **raw-snapshot-to-normalized fidelity review, not verification of real procurement facts**. No network requests, source downloads, published-data edits, or existing-code edits were made.

## Summary

- Six-city DECP: **1,865 raw rows → 1,270 contracts**. No regeneration or independent reviewed-field mismatches. The 171 null amounts, 132 null offers and 142 null dates are caused by conflicting initial variants, not missing raw values or zero conversion.
- Paris/Ardèche DECP: **2,949 raw rows → 2,594 contracts**. No regeneration or independent reviewed-field mismatches, after the explicitly separated three-row curated overlay. All 355 null amounts are conflict nulls. The 13 null offers come from the literal raw value `MQ NC`, not zero.
- BOAMP: **8,386 notices → 16,002 eligible candidate occurrences → 15,196 nonconflicting notice/lot IDs → 3,000 sampled lots**. The published sample exactly equals regeneration, including order. Independent checks of winning-tender amounts, offers, contract dates, winning-holder IDs/names and notice/lot/contract IDs found **zero mismatches across all 16,002 candidates**.
- BOAMP **102 published zero amounts remain zero**, distinct from 752 null amounts. There is one zero-offers candidate occurrence in the full candidate pool, but none in the published sample; this is not evidence that the parser converts zero offers to null.
- Several **latent BOAMP parser bugs** reproduce with synthetic changes to a saved notice. None of the corresponding problematic inputs was found among the eligible candidates in this snapshot. Recommendations and precise locations are below.
- Paris/Ardèche history deliberately omits known initial holder IDs in 2,563 history entries. Top-level `supplierIds` are faithful; history fidelity is narrower than the city importer. No conflicting same-modification-ID values were found in the Paris/Ardèche snapshot, but its importer does not explicitly flag them if they arise later.

## Scope, inputs and reproducibility

Read the full importers and their tests:

- `tools/import-decp-cities.py`, `tests/test_import_decp_cities.py`
- `tools/import-decp-paris-ardeche.py`, `tests/test_import_decp_paris_ardeche.py`
- `tools/import-boamp-sample.py`, `tests/test_import_boamp_sample.py`

Also inspected coverage mapping/rebuild notes in `data/decp-coverage.json` and `data/coverage.json`, and relevant conflict/validation references in `script.js`, `tests/cities.cjs`, and `tests/import.cjs`. Generic CSV/OCDS zero/date tests are **not** tests of the BOAMP eForms parser.

The standalone **read-only** helper is necessary to make the full reconciliation and synthetic probes rerunnable without invoking importers' write paths:

```sh
python research/accuracy-france-source-review.py > /tmp/accuracy-france-source-review.json
python -m unittest discover -s tests -p 'test_import_decp*.py'
python -m unittest discover -s tests -p 'test_import_boamp_sample.py'
```

Observed test results: **9 DECP tests passed; 4 BOAMP tests passed**. No full browser or full repository test suite was run. The helper prints hashes, counts, mismatch counters, field distributions and synthetic probe results. It calls only importers' pure normalization/build functions, never `main`, `offline`, or `download`. Its independent accessors/parsers do not call the importers' field/relationship helpers. It writes nothing itself; Python may create ordinary `__pycache__` files.

### Snapshot structure and retrieval accounting

| Snapshot | Recorded retrieval start | Raw rows | Recorded pages | Sum of page counts |
|---|---|---:|---:|---:|
| `decp-cities-raw.json` | 2026-09-15T22:52:17.880816+00:00 | 1,865 | 21 | 1,865 |
| `decp-history-raw.json.gz` | 2026-09-25T12:03:30.277162+00:00 | 2,949 | 30 | 2,949 |
| `boamp-raw.json.gz` | 2026-09-25T12:05:56.859285+00:00 | 8,386 | 84 | 8,386 |

DECP snapshots wrap `records`, `queries`, `totals`, `source`, and `retrievedAt`. Cities additionally retains `buyerLookups` and a textual `fieldSchema` declaration. Records are flattened DECP columns; a modification row repeats initial columns and adds modification columns. A raw row is **not necessarily a separate contract**.

BOAMP wraps `records`, `queries`, `total`, `where`, `source`, and `retrievedAt`. Each record contains a `donnees` JSON string. Supported records descend through `EFORMS/ContractAwardNotice`, extension organizations and notice results. `LotResult` references a winning `LotTender`, a local lot ID, and optionally a `SettledContract`; the tender references a `TenderingParty`, whose organization references carry holder names/legal identifiers.

Raw DECP counts equal recorded per-buyer totals:

| Buyer SIRET | Buyer | Raw rows |
|---|---|---:|
| 21350238800019 | Rennes | 335 |
| 21440109300015 | Nantes | 699 |
| 21330063500017 | Bordeaux | 289 |
| 21380185500015 | Grenoble | 113 |
| 21210231300013 | Dijon | 273 |
| 21370261600011 | Tours | 156 |
| 21750001600019 | Paris | 2,395 |
| 22070001700019 | Ardèche | 554 |

These are **internal accounting checks only**: page-count sums and recorded totals cannot prove immutable pagination, absence of skipped/repeated distinct records, or completeness of real purchases. The helper does not independently certify pagination offsets/order, remote query execution or API totals. Both DECP cohorts have zero exactly identical raw-row duplicates and zero duplicate published IDs. Grouping can still merge reused buyer/contract identifiers; differing variants are not proof of the same procurement.

### Exact input fingerprints

SHA-256 is of the checked-in bytes (compressed bytes for `.gz`):

```text
0c708c533e8f5b95571ef17b5a9b65649a2af087d79ea6d6c76980e381dc59d7  data/decp-cities-raw.json
d5126b0742d27858d68acc4b63c7a967db9653fd7cfbd96e1bfef6c98cfd1184  data/decp-cities.json
d759bfaf97d468aa95fa15b4f0b7e657739ceb052b1b8f8afc731e1ad32b419e  data/decp-history-raw.json.gz
8f8837d8e9e72e9129b6688e12f615c4354475b0787ba65260b190430bf745c2  data/decp-history.json
a0bc06c624a4f054a77e9ac9baf636b6b126875e1f7b4c8173362e57a1f669d1  data/decp-history-curated.json
e6839c41712d0001c33d200efc9fd31042b280a7dc5f1ac0601ca6acd1f66f9d  data/boamp-raw.json.gz
a02b90a427d9310ec57b6b2a7b18c21d9c999f8ebba0542835c7161a6cdf6400  data/contracts.json
```

## Amount/date/offers reconciliation

Counts below are **normalized rows**, not raw occurrences. Known includes zero. All unlisted zero counts are zero.

| Dataset | Field | Known | Null | Zero |
|---|---|---:|---:|---:|
| Cities (1,270) | amount | 1,099 | 171 | 0 |
| Cities | offers | 1,138 | 132 | 0 |
| Cities | notification date | 1,128 | 142 | 0 |
| Cities | publication date | 1,143 | 127 | 0 |
| Cities | duration months | 1,136 | 134 | 0 |
| Paris/Ardèche (2,594) | amount | 2,239 | 355 | 0 |
| Paris/Ardèche | offers | 2,581 | 13 | 0 |
| Paris/Ardèche | notification date | 2,594 | 0 | 0 |
| Paris/Ardèche | publication date | 2,594 | 0 | 0 |
| Paris/Ardèche | duration months | 2,594 | 0 | 0 |
| BOAMP sample (3,000) | amount | 2,248 | 752 | 102 |
| BOAMP sample | offers | 1,188 | 1,812 | 0 |
| BOAMP sample | contract date | 2,978 | 22 | 0 |
| BOAMP sample | duration months | 979 | 2,021 | 0 |

### DECP: nulls mean conflict or unknown, never assumed zero

All 1,865 city raw values for each of `montant`, `offresrecues`, `datenotification`, `datepublicationdonnees`, and `dureemois` are parseable and nonzero where numeric. All 2,949 Paris/Ardèche raw amounts/durations/dates are valid; 2,936 offers parse as positive integers and **13 are `MQ NC`**, conservatively unknown. No actual zero initial amount/offers exists in these two DECP snapshots, so observed rows alone cannot establish zero handling.

The helper separately probes the shared DECP implementation: string `"0"` gives amount **0.0**, offers **0**; mixing that row with amount `INX` and offers `CDL` gives **null/null**, with `initialConflicts = ["amount", "offers"]`. This is a synthetic regression check, not a source record.

For every published DECP row the helper independently groups raw rows by exact buyer SIRET + contract ID, parses the five reviewed fields, and nulls any differing parsed alternatives, including known-versus-unknown. It checks conflict labels (except Paris publication date, which has separate handling), typed supplier IDs/SIRENs, exact normalized IDs and source URL buyer/contract predicates. All checks agree. Parsed equality can collapse distinct invalid raw strings to the same null; this is equality of normalized knowledge, not raw textual equality.

Cities have **172 groups with any initial conflict**; reviewed-field conflicts are amount 171, offers 132, notification date 142, publication date 127, duration 134. These overlap and must not be summed. Paris/Ardèche has **355 initial-conflict groups**, all conflicting on amount among the five fields reviewed here. Do not select the first raw amount, coerce null to zero, or sum variants to repair these rows.

### History and amount basis

- Cities: **355 groups with modifications, 365 distinct published modification events**. Seven raw groups contain differing values under the same modification ID; the city importer additionally reports `modificationConflicts`. Examples include `decp-21330063500017-2024E000`, `decp-21330063500017-2024E005`, and `decp-21350238800019-2025T00043`. Events remain source alternatives, not a definitive chronological sequence. `script.js:7` excludes ambiguous city groups from calculations; retrospective guards also inspect conflicts.
- Paris/Ardèche: **277 groups with modifications, 277 events**, zero same-modification-ID conflicting-value groups in the saved raw snapshot.
- Independent checks confirm initial history amount/date/publication/duration equals the conflict-safe top level and every modification event has a matching raw modification ID, amount, duration and dates. No amount addition occurs in normalization.
- `montant` is retained in declared **EUR**, `dureemois` in **months**. DECP coverage documents modification `montant` as **“Nouveau montant”**, i.e. revised declared total, not an increment to add to the initial amount. This review did **not** fetch or validate the linked official schema. Paris amount-basis text says initial HT forfaitaire/estimated; the raw snapshot itself does not independently establish tax treatment or whether each declaration is an estimate, ceiling, actual spend or correctly completed total. Those are source/documentation claims, not verified financial truth.

### BOAMP: winning tender, not notice total

The independent traversal follows `LotResult → LotTender → LegalMonetaryTotal/PayableAmount`, accepts nonnegative finite **EUR** for the independent expected amount, and follows the result's `SettledContract/IssueDate` for date. It never substitutes a notice total, framework ceiling, publication date or another tenderer's value.

Full eligible-candidate occurrence counts (before ID conflicts/sampling):

| Field | Known | Null | Zero |
|---|---:|---:|---:|
| amount | 11,887 | 4,115 | 600 |
| offers | 6,104 | 9,898 | 1 |
| contract date | 15,890 | 112 | 0 |
| duration months | 5,312 | 10,690 | 0 |

Amount nodes: **11,890 EUR**, **4,111 with no currency found**, **1 CHF**. Three EUR nodes fail nonnegative parsing. An additional recursive inspection of all saved notice `PayableAmount` nodes found `-134112.00` in notice `25-14404`, `-57112.20` and `-350531.80` in `25-14631`, and CHF `3948380` in `25-47950`. They are not silently turned into positive EUR values. Reproduce that supplemental inspection with a recursive walk of dictionaries/lists in `json.loads(record['donnees'])`, selecting keys `cbc:PayableAmount` whose `@currencyID != 'EUR'` or `#text` starts with `-`. The helper's currency/known/null totals independently reproduce the aggregate effect.

Only statistics code **`tenders`** supplies offers. Among candidate result statistics, there are 6,104 `tenders` entries versus **11,649 `t-esubm`**, 1,129 `t-sme`, 446 `t-oth-eea`, 444 `t-no-eea`, 317 `part-req`, and small other categories. Electronic submissions, participation requests and subsets are not substituted for total offers. The helper found no conflicting repeated valid `tenders` values or dict-shaped `StatisticsNumeric` values among eligible candidates.

`PayableAmount` is the saved winning-offer monetary element; this does **not** independently establish a uniform HT/TTC basis, payment amount, per-unit price, final spend or scope across notices. Preserve the published amount-basis warning. Only `MONTH` duration is mapped, without converting days/years or inferring renewals. Duration regeneration was checked, but independent semantic validation of every duration node was not performed.

## Identity/source matching and selection

DECP keys and source predicates match exact buyer + contract IDs; top-level holder IDs/types and derived SIRENs match the raw columns. The city importer retains raw variants. Paris/Ardèche retains initial alternatives only for conflict groups and an external raw snapshot; three dossier rows get curated supplier/name-source/project/framework fields. The overlay is not treated as raw DECP evidence, and its PDFs/web sources were not reverified. `supplierProfiles` are excluded from regeneration comparison because they are separate current-name enrichment, not historical contract facts; this review does not audit the identity snapshot or remote buyer lookup truth.

BOAMP IDs are notice-scoped: `boamp-{idweb}-{lowercase lot ID}`; `CON-*`, `LOT-*`, `ORG-*` and tender IDs are local to the notice, not DECP identifiers. Every candidate's published notice/lot/contract ID and winning holder name/legal identifier agrees with the saved result/tender/party/organization chain. **32 foreign holder ID occurrences** have 9 or 14 digits after whitespace removal, **8 in sample candidate occurrences**; these remain published identifiers, not French SIRENs/SIRETs. Examples include `boamp-25-12219-lot-0001`, `boamp-25-12459-lot-0001`, and `boamp-25-15221-lot-0002`. No missing winning-tenderer organization reference was found among eligible candidates. These are occurrence counts, not distinct suppliers.

BOAMP build accounting:

- Unsupported schema: **2,153 notices**, not inferred to be empty or award-free.
- Excluded winning-result occurrences: **1,366** (importer criteria, e.g. ambiguous/missing winner/contract references or no identified holder).
- Eligible occurrences: **16,002**, spanning **15,432 notice/lot IDs**.
- **236 conflicting notice/lot IDs excluded entirely**; zero identical normalized duplicate occurrences. The resulting **15,196** unique eligible IDs are ordered by SHA-256 of ID and first 3,000 selected.

Thus conflict IDs are excluded, not resolved by choosing the first source version, and no multiwinner sums are fabricated. Build counts/exclusions rely on the importer and existing count tests; the helper independently checks field relationships on eligible candidates, **not every exclusion decision or unsupported schema**. No independent source-link HTTP resolution or BOAMP buyer-ID/naming certification was done.

The sample equality check excludes the two hand-documented `boamp-25-846-*` Mauges lots. CRC dossiers and other non-sample rows in `contracts.json`, Tours notice datasets, national DECP and cross-source joins are out of scope. No BOAMP/DECP ID equality is assumed.

## Findings and recommendations (initial review, before fixes)

**Follow-up:** the BOAMP robustness findings 1–4 below have now been corrected in `tools/import-boamp-sample.py`, with ten additional regression tests (14 BOAMP tests total). Finite/nonnegative amounts and durations, calendar dates, conflicting offer totals, numeric text nodes and holder-reference pairing are guarded. A read-only before/after comparison found the complete saved-snapshot build unchanged, and the independent helper remains runnable with the corrected parser. No published BOAMP data was rebuilt. The descriptions below preserve the original findings; they are not claims that those bugs remain. Finding 5 (Paris/Ardèche history fidelity) is still open.

### 1. BOAMP non-finite amounts accepted — reproduced, not observed in eligible raw candidates

**Location:** `tools/import-boamp-sample.py:140–145`, especially line 143. It checks `value >= 0` without `math.isfinite(value)`, contrary to the “fini” mapping in `data/coverage.json:42`. The synthetic EUR `Infinity` probe is retained as positive infinity. Current candidate independent amount mismatches and non-finite amounts: **0**.

**Recommendation:** require finite, nonnegative numbers before retaining amount; use a shared validated parser or Decimal with explicit finite checks. Add zero, negative, NaN, ±Infinity and malformed value tests. Prevent nonstandard JSON `Infinity` serialization. Similarly `:156–160` parses MONTH duration without finite/nonnegative validation; harden it, though this review has not established an actual bad duration record.

### 2. BOAMP date slicing does not validate calendar dates — reproduced, not observed

**Location:** `tools/import-boamp-sample.py:151–152,182`. `issue[:10]` retains synthetic `2025-02-30`. Eligible candidate invalid calendar dates and independent date mismatches: **0**. Missing date remains null (22 sample rows); publication is not substituted.

**Recommendation:** validate ISO calendar date before returning its date component; preserve missing/invalid as null with provenance. Test impossible dates, timestamps and nonstring nodes separately.

### 3. BOAMP conflicting offers statistics are last-wins; dict text nodes ignored — reproduced, not observed

**Location:** `tools/import-boamp-sample.py:146–149`. Two `tenders` statistics `1` then `2` produce **2**, not a conflict null. A text-node dict `{"#text":"0"}` becomes null rather than zero. Neither problematic shape/conflict was observed among the eligible candidate statistics.

**Recommendation:** unwrap numeric text nodes, parse strictly nonnegative integer totals, collect all `tenders` alternatives, null conflicting totals and expose alternatives. Test genuine zero, unknown, subset-only codes, malformed values and repeated conflicting/identical totals. Do not claim these missing regression cases corrupt this published sample.

### 4. BOAMP missing organization references can misattribute source-reference IDs — reproduced, not observed

**Location:** `tools/import-boamp-sample.py:133–134`. It filters missing organizations before zipping members with the **unfiltered** reference list. Inserting an unresolved `ORG-MISSING` before a valid holder makes `sourceReference` label the valid company's data as `ORG-MISSING`. Actual eligible candidates with unresolved holder refs: **0**.

**Recommendation:** construct `(reference, organization)` pairs together and filter pairs, not values separately; explicitly retain/report missing-reference ambiguity. Add a missing-first/middle-organization regression case. This is an identifier provenance bug, not proof of currently wrong legal holder IDs.

### 5. Paris/Ardèche history loses holder detail and lacks city-style modification conflicts

**Location:** `tools/import-decp-paris-ardeche.py:104–115`, especially the unconditional `supplierId: None` at lines 107 and 113. **2,563** published initial history entries omit the single known initial holder available at top level. No saved modification event has a nonmissing raw modification holder that is omitted, so the modification-holder issue is currently latent.

**Recommendation:** preserve typed raw modification holder identifiers and a single known initial holder in history, without inventing names or assuming unchanged identity. Follow the city's conflict-safe approach and add same-modification-ID alternative/conflict reporting. Current Paris raw conflicting modification groups: **0**. Publication differences are null-safe via a separate set at line 103 but not included in `initialConflicts`/alternatives; add explicit provenance if consistency across cohorts is desired. Current publication conflicts: **0**. These are fidelity/robustness gaps, not a demonstrated wrong Paris amount.

## Limits on conclusions

1. Exact regeneration alone is not correctness: importer bugs can reproduce published bugs. Independent raw field/relationship checks and synthetic edge probes are intentionally separate from regeneration counts.
2. Saved API output is not necessarily legally accurate, exhaustive, unaltered by the upstream publisher, or the latest source. `dataStatus: verified` must not be read as verified payment, tax regime, legal regularity, competition or complete amendment history.
3. Modification amounts that resemble increments were **not** reinterpreted. Source schema interpretation is documented locally, not independently reverified remotely. No amount was summed across variants, cotitularies or datasets.
4. Historical retrieval/rebuild claims in coverage (including earlier lost importer behavior and changes since 2026-09-13) were read but not independently established from an earlier snapshot in this review.
5. No assertion of historical supplier names, SIRET checksum validity, precise buyer legal identity, remote link health, full eForms schema compliance, correct tax treatment or genuinely received/valid offers is made.
6. Existing user modifications were left untouched. Only this report and the standalone review helper were added; no importer, existing test, published data, coverage, or UI file was changed.
