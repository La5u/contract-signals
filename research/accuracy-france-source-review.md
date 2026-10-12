# France source accuracy review — offline reconciliation

Review: **2026-10-07 UTC**, HEAD `581fe2c98e64e66ed5fd3964f599115f8e42767f`. This checks saved-source fidelity, not real procurement facts. Published data was unchanged.

## Results and reproduction

No regeneration/independent reviewed-field mismatches: cities **1,865 raw → 1,270 contracts**, history **2,949 → 2,594** (three curated rows separated), BOAMP **8,386 notices → 16,002 candidates → 15,196 nonconflicting IDs → 3,000 sample lots**. Sample order agrees; independent checks cover all candidates. DECP null amounts reflect conflicts; history null offers reflect `MQ NC`. BOAMP's **102 sample zeros/752 nulls** stay separate; one zero-offer candidate exists, none in sample. Synthetic parser bugs were not observed in eligible inputs.

```sh
python research/accuracy-france-source-review.py > /tmp/accuracy-france-source-review.json
python -m unittest discover -s tests -p 'test_import_decp*.py'
python -m unittest discover -s tests -p 'test_import_boamp_sample.py'
```

Initial tests: **9 DECP, 4 BOAMP passed**. Helper uses pure build functions and independent accessors, printing hashes/counts/probes without writes/downloads except possible `__pycache__`. No browser/full-suite check.

Inputs: `data/decp-cities-raw.json`, `data/decp-cities.json`, `data/decp-history-raw.json.gz`, `data/decp-history.json`, `data/decp-history-curated.json`, `data/boamp-raw.json.gz`, `data/contracts.json`. Importers/tests: `tools/import-decp-cities.py`, `tests/test_import_decp_cities.py`; `tools/import-decp-paris-ardeche.py`, `tests/test_import_decp_paris_ardeche.py`; `tools/import-boamp-sample.py`, `tests/test_import_boamp_sample.py`. Rules: `data/decp-coverage.json`, `data/coverage.json`, `script.js`, `tests/cities.cjs`, `tests/import.cjs`; generic CSV/OCDS tests do not cover eForms.

## Snapshot and field counts

DECP rows repeat initial columns across modifications; BOAMP `donnees` stores eForms relationships. Page sums match recorded totals but cannot verify pagination/completeness. DECP has zero exact raw duplicates or duplicate published IDs; reused IDs may still merge procurements.

| Snapshot | Retrieval start | Pages / rows | Buyer totals (SIRET: rows) |
| --- | --- | --- | --- |
| Cities | 2026-09-15T22:52:17.880816+00:00 | 21 / 1,865 | Rennes 21350238800019: 335; Nantes 21440109300015: 699; Bordeaux 21330063500017: 289; Grenoble 21380185500015: 113; Dijon 21210231300013: 273; Tours 21370261600011: 156 |
| History | 2026-09-25T12:03:30.277162+00:00 | 30 / 2,949 | Paris 21750001600019: 2,395; Ardèche 22070001700019: 554 |
| BOAMP | 2026-09-25T12:05:56.859285+00:00 | 84 / 8,386 | — |

Normalized **known/null/zero** counts; known includes zero:

| Field | Cities (1,270) | History (2,594) | BOAMP sample (3,000) |
| --- | --- | --- | --- |
| Amount | 1,099/171/0 | 2,239/355/0 | 2,248/752/102 |
| Offers | 1,138/132/0 | 2,581/13/0 | 1,188/1,812/0 |
| Notification / contract date | 1,128/142/0 | 2,594/0/0 | 2,978/22/0 |
| Publication date | 1,143/127/0 | 2,594/0/0 | — |
| Duration months | 1,136/134/0 | 2,594/0/0 | 979/2,021/0 |

## DECP reconciliation and history

- All **1,865** city raw amounts/offers/dates/durations parse; numeric values are nonzero. All **2,949** history amounts/durations/dates parse; **2,936** offers are positive and **13** unknown. Synthetic string `"0"` retains **0.0 amount/0 offers**; mixed with `INX`/`CDL`, both become null with `initialConflicts=["amount","offers"]`.
- Buyer+contract grouping agrees on five fields, conflict labels (Paris publication separate), typed holders/SIRENs, IDs and source predicates. Invalid raw strings may normalize to equal nulls.
- Cities: **172** groups with any initial conflict: amount **171**, offers **132**, notification **142**, publication **127**, duration **134**; counts overlap. History: **355** amount-conflict groups. Do not choose, sum or zero-fill variants.
- Modifications: cities **355 groups/365 events**, **7** same-ID conflicts (`decp-21330063500017-2024E000`, `decp-21330063500017-2024E005`, `decp-21350238800019-2025T00043`); history **277 groups/events**, zero conflicts. Events are alternatives; `script.js:7`/retrospective guards exclude ambiguity.
- History fields/events match raw values without addition. Units: **EUR/months**; modification `montant` is locally documented as **“Nouveau montant”**, revised total. Official schema/tax/spend basis unverified.

## BOAMP relationships and selection

Follow `LotResult → LotTender → LegalMonetaryTotal/PayableAmount` for finite nonnegative EUR, and `SettledContract/IssueDate` for date; do not substitute notice totals, ceilings or publication dates.

Full eligible candidate occurrences before conflict exclusion/sampling:

| Field | Known | Null | Zero |
|---|---:|---:|---:|
| amount | 11,887 | 4,115 | 600 |
| offers | 6,104 | 9,898 | 1 |
| contract date | 15,890 | 112 | 0 |
| duration months | 5,312 | 10,690 | 0 |

- Nodes: **11,890 EUR, 4,111 currency absent, 1 CHF**; three EUR negatives: **-134112.00** (`25-14404`), **-57112.20/-350531.80** (`25-14631`); CHF **3948380** (`25-47950`). Reproduce with recursive `json.loads(record['donnees'])` walk selecting `cbc:PayableAmount` whose `@currencyID != 'EUR'` or `#text` is negative.
- Offer codes: **6,104 tenders**, **11,649 t-esubm**, **1,129 t-sme**, **446 t-oth-eea**, **444 t-no-eea**, **317 part-req**; only `tenders` supplies totals. No conflicting totals/dict `StatisticsNumeric`. Only `MONTH` duration maps; every node was not independently validated. Payable tax/spend basis remains unverified.
- IDs `boamp-{idweb}-{lowercase lot ID}` are notice-scoped; local `CON/LOT/ORG` references are not DECP IDs. Holder chains agree. **32 foreign holder-ID occurrences** have 9/14 digits, **8** in sample candidates; they remain foreign IDs (`boamp-25-12219-lot-0001`, `boamp-25-12459-lot-0001`, `boamp-25-15221-lot-0002`). No unresolved winning-holder reference occurred.
- Exclusions: **2,153 unsupported notices**, **1,366 winning results** failing importer criteria. **16,002** eligible occurrences span **15,432 IDs**; **236 conflicting IDs** are excluded, zero identical normalized duplicates. Order remaining **15,196** by SHA-256 of ID, take **3,000**. Independent checks cover eligible relationships, not all exclusion decisions.

Three history rows have a curated overlay; its PDFs/web evidence was not reverified. `supplierProfiles` are current-name enrichment, excluded from regeneration. Sample equality excludes two Mauges `boamp-25-846-*` lots; CRC/non-sample dossiers, Tours, national DECP and cross-source joins were outside scope.

## Findings and follow-up

**BOAMP findings 1–4 fixed** in `tools/import-boamp-sample.py`, adding ten tests (**14 total**). Before/after saved-snapshot builds were identical; no published BOAMP rebuild.

1. **Nonfinite amount/duration:** former lines **140–145/156–160** accepted synthetic EUR `Infinity` and lacked finite/nonnegative duration guards (`data/coverage.json:42`). Zero observed candidate nonfinite values/mismatches; now guarded, with zero/negative/NaN/infinity/malformed tests.
2. **Calendar dates:** former **151–152,182** sliced synthetic `2025-02-30`; zero observed invalid dates/mismatches. Now validates dates; missing remains null (**22 sample rows**).
3. **Offers:** former **146–149** chose last of conflicting `1/2` totals and ignored `{"#text":"0"}`. Neither occurred in candidates; now unwraps nodes and nulls conflicting totals.
4. **Holder reference pairing:** former **133–134** zipped filtered organizations with unfiltered IDs, mislabelling a synthetic missing-first `ORG-MISSING`. Zero observed unresolved refs; now filters paired references/organizations.
5. **Open history fidelity gap:** `tools/import-decp-paris-ardeche.py:104–115` omits known single initial holders in **2,563** history entries. Top-level holders remain faithful; no saved modification omits a known raw modification holder. Preserve typed raw holders and add city-style same-ID modification alternatives/conflicts. Publication dates are separately null-safe at **103** but lack conflict provenance. Current modification/publication conflicts: **0/0**.

Regeneration cannot certify importer correctness; independent checks cannot certify legal accuracy, upstream completeness, historical names, buyer identity, SIRET checksums, link health, tax treatment or actual received offers. Earlier coverage/rebuild claims were not independently reconstructed.
