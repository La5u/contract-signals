# Missing/zero amount evidence review — complete gap accounting, offline

> **Snapshot note (2026-10-08):** counts below predate the DECP identifier splits and buyer-feed reconciliation of 2026-10-08 (French cohorts now 2,219 + 2,997 records; missing-amount gaps 1,092). See `research/decp-identifier-collisions.md` and `research/france-cross-dataset-check.md`.

**Local review date:** 2026-10-08. **No network requests, importer rebuilds, source overwrites or published-data changes.** This is reconciliation against retained snapshots, not verification of signed documents, current upstream data, payments or legal compliance. Counts refer to normalized rows, not unique contracts.

## Inventory and scope

`tools/audit-data-quality.py` reproduces **154 numeric zeros and 1,383 null amounts** across the explicit `script.js` dataset registry. There are no absent `amount` keys, negative amounts or non-numeric normalized amounts in this inventory. “Missing” here therefore means **null**, not declared zero.

The extended real run accounts for **all 1,537 gap rows (154 zero + 1,383 null)** plus **all 488 Ukraine rows** for contract/award fallback provenance: **2,025 private evidence entries**. Accounting is not recovery: **526 DECP nulls remain unresolved conflicts** and **76 notice-only nulls are outside contract-amount scope**. The original 569-entry phase and its findings below are preserved; the French extension adds 1,456 entries. **Zero positive recovery candidates; zero unreviewed gap rows.**

| Published dataset | Zero | Null | Rows reconciled | Local result | Positive same-basis recovery candidates |
| --- | ---: | ---: | ---: | --- | ---: |
| Ukraine / Prozorro | 0 | 0 | 488 | 488 positive contract values retained | 0 |
| UK / Find a Tender | 0 | 9 | 9 | 9 source amounts absent | 0 |
| Colombia / SECOP II | 49 | 0 | 49 | 49 raw contract amounts explicitly zero | 0 |
| TED Portugal | 0 | 1 | 1 | Winning-tender PayableAmount absent | 0 |
| TED Czechia | 3 | 19 | 22 | 3 explicit CZK zeros; 19 PayableAmount absent | 0 |
| TED Romania | 0 | 0 | 0 | No zero/null rows; positive rows not reviewed | 0 |
| BOAMP / curated `contracts.json` | 102 | 752 | 854 | 102 payable zeros; 751 absent payables; 1 negative payable | 0 |
| DECP history | 0 | 355 | 355 | Unresolved initial-amount conflicts | 0 |
| DECP cities | 0 | 171 | 171 | Unresolved initial-amount conflicts | 0 |
| Tours notices | 0 | 66 | 66 | Not contract-amount scope | 0 |
| Consultations | 0 | 10 | 10 | Not contract-amount scope | 0 |
| **Gap subtotal (excludes Ukraine)** | **154** | **1,383** | **1,537** | **154 raw zeros; 780 absent source amounts; 1 negative source amount; 526 conflicts; 76 notice-only** | **0** |

Chile and the two Paraguay cohorts have no zero/null rows and were not reconciled. Positive French, UK, Colombia and TED rows remain outside scope. The inventory is not proof of importer error or of complete purchasing histories.

## Exact counterpart method and concrete findings

### Ukraine: no zero/null gaps; check the fallback risk instead

Source: Prozorro official tender API snapshots, `data/prozorro/raw/records/{tenderID}.json.gz`.

The helper matches `tenderID` and full `procedureId` against the tender, **full `contractInternalId`** against a contract, and `contractId`/`awardId` against its published references. It checks the importer row ID `prozorro-{tenderID}-{contractInternalId[:8]}` only after the full-ID match. Award counterpart(s) are found by full `awardID`, not by supplier identity, title or rounded amount. Private evidence points to `/data/contracts/{index}/value` and `/data/awards/{index}/value`, with the compressed snapshot SHA-256.

All **488** rows equal their exact embedded contract values: **478 UAH, 5 EUR, 5 USD**; all matched contracts are `active` in these snapshots. **0 observed award fallbacks** and **0 local lost contract values**. However, **11 contract/award amount disagreements** are recorded in private `basis_conflicts`. Those are not identity conflicts: contract values were retained and awards are not substituted. Differences are not interpreted as erroneous, amendments, misconduct or payments without further evidence.

Importer issue to keep visible: `tools/import-prozorro.py:contract_rows` uses `contract.get('value') or award.get('value') or {}` yet labels the result “Contract value as published”. The fallback could misstate provenance on other snapshots; it does not explain a missing amount in this cohort. This helper does not run that fallback or change the importer. Separate linked contract API snapshots/documents are not investigated here; this finding is limited to embedded tender contracts.

### UK FTS: nine genuinely absent local amounts

Sources: **9 distinct** `data/uk-fts/raw/notices/{noticeId}.json.gz` snapshots. Exact `release.id` + `ocid` + full `awardId`, with related-lot checking and the importer ID `fts-{release.id}-{award.id final hyphen component}`. Each matched award has exactly one contract linked by `awardID`; evidence includes the award index and contract value pointer in the same release.

In all nine, the **contract, award and tender value amounts are absent**; neither contract nor award supplies a currency. Matched contracts and awards are `active`. **No local positive recovery, no multiple-contract ambiguity, no importer-lost amount found.** `tools/import-find-a-tender.py:notice_rows` has the same contract-or-award fallback risk and a last-contract-per-award dictionary; the helper enumerates all counterparts instead of silently choosing one. No duplicate counterpart occurs in this reviewed set. Missing currency is not filled with GBP.

### TED: distinguish winning-tender amounts from notice/framework totals

Sources: **1 Portugal and 20 Czechia distinct XML snapshots**, `data/ted-{country}/raw/notices/{noticeId}.xml.gz`. Match `resultId` to `NoticeResult/LotResult/ID`, check `lotId` and settled-contract reference(s), follow the exact `LotTender/ID` reference, and read **that winning tender's** `LegalMonetaryTotal/PayableAmount`. Duplicate results, tender references or monetary nodes are ambiguous, not first/last-match recovery. Normalized IDs must equal `ted-{noticeId}-{lotId.lower()}`. The notice ID identifies the retained filename; this helper does not independently validate an XML publication-number field.

**19 Czechia + 1 Portugal** selected winning tenders have no PayableAmount; the **3 Czechia zeros** are explicitly published PayableAmount `0` in **CZK**. All reviewed lot results use `selec-w`. The retained missing/zero amounts are not importer loss.

Every reviewed TED gap row has positive **excluded context** somewhere in its whole notice. Portugal includes `MaximumValueAmount`, `ReestimatedValueAmount`, `FrameworkMaximumAmount` and overall framework amounts (EUR). Czechia includes estimated overall contract, framework maximum, total, term, reestimated and maximum amounts (CZK). Those are recorded as **whole-notice context only**, not mapped replacements: multi-lot totals, framework ceilings and other monetary bases cannot be allocated to an individual row by title, bidder or arithmetic. Context counts can repeat the same notice for different rows and are not unique monetary facts.

TED's normalized amount basis is explicitly **winning-tender PayableAmount**, not a signed-contract amount. The helper may flag a positive exact same-basis PayableAmount as a candidate on future inputs, but it never relabels it as a contract value. **0 such candidates in these snapshots.** Romania has no gap rows; its positive rows were not checked.

### Colombia: 49 declared contract zeros, not lost values

Sources: **7 distinct** raw pages in `data/colombia-secop2/raw/`, restricted to files listed in `manifest.json`. Reconstruct the importer ID with the manifest buyer selection rule and `id_contrato` (the importer’s process fallback is also supported), then check full `contractId` and `processId`. Exact array index, filename and SHA-256 are kept privately. Duplicate reconstructed IDs are ambiguous, even if their amounts agree.

All **49** reviewed normalized zeros equal raw **`valor_del_contrato = 0`**, in **COP** per the importer/source convention (not a per-row currency field). Raw statuses: **28 En ejecución, 10 Cerrado, 8 Modificado, 3 Aprobado**. No normalized null amounts exist in this cohort. **No positive local contract amount to recover.** Context fields `valor_pagado`, `valor_facturado` and `valor_pendiente_de_ejecucion` are also zero in these reviewed rows; those execution fields are not eligible replacements regardless of their values. Source status does not validate the zero or establish that a contract had no economic value.

### French extension: independent exact references, no value selection

The independent field/relationship findings in `research/accuracy-france-source-review.py` informed this extension, **not its importer-regeneration results**. That research script was read, not executed: it imports normalization/build helpers. This review imports only the read-only audit helper, never an importer, and does not rebuild any dataset.

**BOAMP:** index every retained `data/boamp-raw.json.gz` record by exact `idweb`; decode its eForms award notice and match the exact `TenderLot/ID` within `NoticeResult/LotResult`. Require one result, `TenderResultCode = selec-w`, the published settled-contract reference, the importer row ID, and exactly one referenced `LotTender/ID`. Read only that tender's `cac:LegalMonetaryTotal/cbc:PayableAmount`. Duplicate notices, results, tender references or payable nodes block recovery, even if equal. Amounts on other tenders, whole-notice totals and framework ceilings are never replacements. The private paths into `donnees` describe decoded eForms relationships, not pointers into the outer encoded JSON string.

All **854** BOAMP gaps have unique unconflicted reference chains. **102** have explicit EUR payable zeros; **751** have no payable amount/currency; **one normalized null** has a negative EUR payable (`-57112.20`). The negative value is classified `raw_source_negative`, not changed to zero, made positive or recovered. This explains why “752 nulls” is not synonymous with “752 missing raw values”. No local positive same-basis values were found. The hand-curated lots/audit dossiers in `contracts.json` contribute no gaps in this run; they were not mapped by this eForms method.

**DECP:** group every retained raw row by exact `(acheteur_id, id)` and look up the published `(buyerSiret, contractId)` pair, checking the normalized procurement ID. The cities gaps cover **765 raw counterparts in 171 groups**; history covers **710 counterparts in 355 groups**. Every gap has differing parsed initial `montant` values, independently confirming its published `initialConflicts` amount marker. Parsing follows the independent research semantics: blank/CDL/INX, invalid, negative and nonfinite values are unknown; zero remains distinct. **All 526 are `unresolved_initial_conflict`**, not recoveries. Every counterpart amount is retained privately as amount-only evidence; no first/last/maximum, sum, supplier match, latest date or modification amount is selected. Published alternatives, subjects, names and holder identifiers are not copied. A conflict can reflect source ambiguity or cotitular representation, not necessarily an error. Even unanimous DECP sets are not eligible for value selection by this tool.

**Tours / consultations:** use the dataset registry's source semantics: Tours rows represent notice versions/lots, consultations represent initial calls and linked notice chains, **not awarded contracts**. Confirm exact `noticeId` in retained `api-records.json` / `consultations-raw.json` and the dataset-specific row ID. All **66 + 10** have one notice counterpart and classify `not_contract_amount_scope`. This is a dataset-scope decision, not validation of every notice version/lot relationship. No notice estimate, linked award amount or inferred EUR amount is extracted. Their raw pointers and hashes support traceability without copying notice text.

## Helper, private queue and reproduction

New helper: **`tools/review-missing-amounts.py`**, standard-library-only, no network imports/calls. It reads the audit registry and raw snapshots without invoking importers. It writes only a private minimized queue outside the repository and prints a **counts-only aggregate**; no participant names, buyer/supplier personal IDs or free-text notices are copied into its outputs.

Default private evidence/candidate queue:

**`~/.cache/contract-signals/missing-amounts-review/review.jsonl`**

It currently contains **2,025 evidence entries** and **0 entries with `recovery_candidate: true`**. It includes exact procurement IDs, current amount/category/currency/data status, source status, exact counterpart count, raw filename/hash/pointer, source amount/currency/basis/VAT flag where supplied, mapping conflicts and contract/award basis disagreements. Private directory mode **0700**, queue mode **0600**, atomic replacement. Do not commit or serve it. `--review-dir` refuses paths inside the repository. Aggregate output contains no row values, names, subjects or personal identifiers. Its `input_sha256` manifest lists the registry, all published inputs and consumed raw snapshots (including procurement-ID filenames); private entries also retain each raw hash. SHA-256 is over original bytes, including compressed bytes, not decompressed JSON. No DECP buyer identifier is copied as a separate queue field; normalized procurement IDs retain their existing exact identity scope.

```sh
# Audit baseline: aggregate stdout, separate private inventory queue
python tools/audit-data-quality.py --output -

# Bounded reconciliation: stdout is public-safe; exact evidence stays private
python tools/review-missing-amounts.py

# Synthetic offline tests (no network or published output writes)
python -m unittest discover -s tests -p 'test_review_missing_amounts.py'
```

Observed aggregate also retained locally at **`/tmp/missing-amounts-aggregate.json`** (counts only; temporary, not a durable project artifact). Baseline audit aggregate: `/tmp/amount-audit.json`. Default audit inventory queue remains separately at `~/.cache/contract-signals/accuracy-review/review.jsonl`.

### Input hashes for the French extension

The aggregate JSON contains the full manifest for all reviewed cohorts. These SHA-256 values pin the registry and new French inputs used by the real run:

| Input | SHA-256 (original file bytes) |
| --- | --- |
| `script.js` | `ba99530e33bfa65c0daf3f76ae1013a26f4766bb77c1ce7e5dfb6269908872a1` |
| `data/contracts.json` | `a02b90a427d9310ec57b6b2a7b18c21d9c999f8ebba0542835c7161a6cdf6400` |
| `data/boamp-raw.json.gz` | `e6839c41712d0001c33d200efc9fd31042b280a7dc5f1ac0601ca6acd1f66f9d` |
| `data/decp-cities.json` | `d5126b0742d27858d68acc4b63c7a967db9653fd7cfbd96e1bfef6c98cfd1184` |
| `data/decp-cities-raw.json` | `0c708c533e8f5b95571ef17b5a9b65649a2af087d79ea6d6c76980e381dc59d7` |
| `data/decp-history.json` | `8f8837d8e9e72e9129b6688e12f615c4354475b0787ba65260b190430bf745c2` |
| `data/decp-history-raw.json.gz` | `d759bfaf97d468aa95fa15b4f0b7e657739ceb052b1b8f8afc731e1ad32b419e` |
| `data/tours-notices.json` | `a029071945d3a7928afc7a02fc479f039f0deb84c584464a6f884e448e48c294` |
| `data/tours-notices/raw/api-records.json` | `a1843c23e4c5123f210df9d6bcbd7a0a1c60f6375dcd2088e0671f55a2e56b17` |
| `data/consultations.json` | `3bacd53cad545018ca51720273f639f535fdc7951059ee05d9b7fbf8231c3680` |
| `data/consultations-raw.json` | `9e5c1a890d0da62256e01e759a7d25aa1bd541a238b64de115edeec031fcbe8a` |

Classification policy:

- `importer_lost_value`: exactly one unconflicted same-basis positive source amount differs from the current amount, with an explicit three-letter currency and no current currency conflict. **Candidate only**, never automatic recovery or a finding of actual importer fault (different snapshots could explain it).
- `raw_source_missing`, `raw_source_zero`, `raw_source_non_numeric`, `raw_source_negative`: preserve the distinction; no inferred value.
- `ambiguous_mapping`: missing/non-unique counterpart, inconsistent IDs, published conflict flags, or duplicate references. No selection by names or amount similarity.
- `unresolved_initial_conflict`: exact DECP buyer/contract set independently contains differing initial amounts and the published amount-conflict marker; never choose a value.
- `not_contract_amount_scope`: exact source notice counterpart within the explicitly notice-only Tours/consultations datasets; no amount inference.
- `source_positive_currency_unresolved` / `currency_conflict`: no recovery until denomination/provenance is resolved.
- `retained_positive`: used for Ukraine provenance checks; not evidence of payment or document accuracy.

**11 helper tests and 7 existing audit tests passed** on the extended run. Added BOAMP singleton/list and duplicate-reference, missing/zero/negative/nonfinite/currencyless evidence probes; DECP exact-set conflicts (including zero versus unknown), duplicate/unanimous sets and excluded modifications; notice-only linked-award exclusion; real inventory totals, source hashes and immutable-data checks. Preserved prior probes: decision/basis/currency handling; UK exact-release matching and multiple-contract ambiguity; Ukraine award-only fallback; TED currencyless payable versus excluded totals; Colombia exact IDs/duplicate ambiguity and person-field minimization; repository-output rejection; private output permissions. Tests use synthetic fixtures, not a claim of exhaustive schema validation. A reconciliation rerun compared SHA-256 hashes before/after for **all 4,786 existing files under `data/`**: unchanged.

## Rights, privacy and next phase

Read `docs/data-sources.md`, `docs/personal-data.md` and `data/LICENSE.md` before investigation. Existing retained rights register: `docs/source-rights-evidence.json`. Sources remain third-party data: Prozorro reuse terms require attribution (no named API licence inferred); Cabinet Office Find a Tender is OGL v3.0; Publications Office TED notices permit free reuse; Colombia Compra Eficiente SECOP II is **CC BY-SA 4.0**. The private Colombian evidence remains subject to attribution/share-alike when redistributed; this original aggregate methodology document does not relicense source records. Reuse terms do not provide blanket privacy or attachment clearance. This phase made no new legal-source fetches.

**Concrete recovery result: zero supported positive-value recoveries across all 1,537 accounted gaps.** No new official fetch was needed for this offline classification, and no fetch plan or bulk retrieval was executed. Accounted does not mean resolved: DECP alternatives remain unresolved, BOAMP zeros/missing/negative values remain as declared, and notice-only amounts stay out of scope. Any later investigation needs a separately approved, bounded exact-ID plan (prioritize the negative BOAMP payable, then a small zero/conflict cohort), not a bulk crawl. Repair/publication requires new same-basis evidence and retained provenance; conversion, ceiling allocation, award substitution or selecting DECP alternatives is unsupported.
