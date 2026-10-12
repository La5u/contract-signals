# Missing/zero amount evidence review

> Historical snapshot, reviewed **2026-10-08**, before DECP splits/reconciliation. The update then reported French cohorts **2,219 + 2,997**, with **1,092** amount gaps. See `research/decp-identifier-collisions.md` and `research/france-cross-dataset-check.md`.

## Result and inventory

Offline reconciliation found **zero positive same-basis recovery candidates** across **1,537 gaps: 154 zeros + 1,383 nulls**. All gaps were reviewed, plus **488 Ukraine** provenance checks: **2,025 private entries**. No absent amount keys, negative or non-numeric normalized amounts occurred. Counts describe normalized rows, not unique contracts or verified purchasing facts.

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

Chile and both Paraguay cohorts have no gaps. Positive rows outside Ukraine were out of scope. **526 conflicts** remain unresolved; **76 notice-only rows** have no contract-amount scope.

## Exact-source findings

- **Ukraine:** `data/prozorro/raw/records/{tenderID}.json.gz`. Match tender/full procedure, full `contractInternalId`, contract/award references, then `prozorro-{tenderID}-{contractInternalId[:8]}`. All **488 active** contracts retain embedded values: **478 UAH, 5 EUR, 5 USD**; no observed fallback/lost value. **11 contract/award disagreements** remain in private `basis_conflicts`. `tools/import-prozorro.py:contract_rows` uses `contract.get('value') or award.get('value') or {}` while labelling “Contract value as published”; fallback provenance remains a risk on other snapshots. Separate linked-contract documents were not reviewed.
- **UK:** nine `data/uk-fts/raw/notices/{noticeId}.json.gz` snapshots. Exact release/ocid/award/related-lot match, then `fts-{release.id}-{award.id final hyphen component}`. Each active award has one active contract; contract, award and tender amounts/currencies are absent. `tools/import-find-a-tender.py:notice_rows` has contract/award fallback and last-contract-per-award risks, but no duplicate counterpart occurred here. Do not infer GBP.
- **TED:** one Portugal and **20 Czechia** XML snapshots in `data/ted-{country}/raw/notices/{noticeId}.xml.gz`. Follow exact result/lot/settled-contract/tender references to winning `LegalMonetaryTotal/PayableAmount`; require `ted-{noticeId}-{lotId.lower()}`. **19 Czechia + 1 Portugal** payables absent; **3 Czechia** payables explicitly **0 CZK**; all results `selec-w`. Publication-number fields were not independently checked. Positive notice/framework/estimated/maximum totals exist in every gap notice but cannot replace lot payables or be allocated arithmetically. Romania has no gaps.
- **Colombia:** seven manifest-listed pages in `data/colombia-secop2/raw/`. Reconstruct IDs using buyer selection and `id_contrato` (process fallback supported); check full contract/process IDs. All **49** equal `valor_del_contrato=0`, in COP by source/importer convention. Statuses: **28 En ejecución, 10 Cerrado, 8 Modificado, 3 Aprobado**. Paid/invoiced/pending-execution fields also equal zero but are ineligible replacements. Duplicate reconstructed IDs would block recovery.
- **BOAMP:** `data/boamp-raw.json.gz`, exact `idweb`, lot/result/settled-contract and unique winning tender, `selec-w`; read only `cac:LegalMonetaryTotal/cbc:PayableAmount`. All **854** gaps have unique chains: **102 EUR zeros, 751 absent amount/currency, one negative EUR payable -57112.20** normalized to null. Thus 752 nulls are not 752 missing raw values. Duplicate notices/results/tenders/payables block recovery even when equal. Curated lots/audit dossiers have no gaps.
- **DECP:** exact raw `(acheteur_id,id)` to published `(buyerSiret,contractId)` and normalized ID. Cities: **765 counterparts/171 groups**; history: **710/355**. All **526** have differing parsed initial amounts and amount-conflict markers. Blank/CDL/INX, invalid, negative and nonfinite values are unknown; zero stays distinct. No alternative or modification is selected, even for unanimous sets. Conflict may reflect ambiguity/co-holder representation, not error.
- **Tours/consultations:** exact notice and row IDs in `data/tours-notices/raw/api-records.json` and `data/consultations-raw.json`. All **66 + 10** have one counterpart and classify `not_contract_amount_scope`; they are notice versions/lots/calls, not awards. No linked-award amount is extracted; not every version/lot relationship was validated.

French methods used independent relationships from `research/accuracy-france-source-review.py`, not regeneration. The review invokes only the read-only audit helper, not importers.

## Helper, policy and reproduction

`tools/review-missing-amounts.py` is offline, standard-library-only. Private queue: `~/.cache/contract-signals/missing-amounts-review/review.jsonl`, **2,025 entries**, zero `recovery_candidate: true`. It retains procurement IDs, numeric/basis/status fields, exact counterparts and raw pointers, but no names, personal buyer/supplier fields or notice text. Directory/file modes **0700/0600**; atomic replacement; `--review-dir` rejects repository paths. Input and raw byte hashes are retained in manifests/entries, including compressed bytes.

```sh
# Audit baseline: aggregate stdout, separate private inventory queue
python tools/audit-data-quality.py --output -

# Bounded reconciliation: stdout is public-safe; exact evidence stays private
python tools/review-missing-amounts.py

# Synthetic offline tests (no network or published output writes)
python -m unittest discover -s tests -p 'test_review_missing_amounts.py'
```

Aggregate paths: `/tmp/missing-amounts-aggregate.json`, `/tmp/amount-audit.json`; separate audit queue: `~/.cache/contract-signals/accuracy-review/review.jsonl`. French inputs also include `script.js`, `data/contracts.json`, `data/decp-cities.json`, `data/decp-cities-raw.json`, `data/decp-history.json`, `data/decp-history-raw.json.gz`, `data/tours-notices.json`, `data/consultations.json`.

Classifications:

- `importer_lost_value`: one unconflicted positive same-basis source value differs, explicit three-letter currency, no currency conflict. Candidate only; snapshot differences may explain it.
- `raw_source_missing/zero/non_numeric/negative`: keep separate; infer nothing.
- `ambiguous_mapping`: non-unique/missing counterpart, inconsistent IDs, conflict flags or duplicate references; no name/amount-similarity selection.
- `unresolved_initial_conflict`: independently differing DECP initial amounts plus published marker.
- `not_contract_amount_scope`: exact notice-only counterpart.
- `source_positive_currency_unresolved` / `currency_conflict`: unresolved denomination blocks recovery.
- `retained_positive`: Ukraine provenance check, not payment validation.

**11 helper and 7 audit tests passed**, covering exact links, ambiguous references, basis/currency and zero/negative/nonfinite handling, privacy and immutable inputs. Hashes of all **4,786 data files** stayed unchanged; synthetic tests do not establish exhaustive schema coverage.

## Rights and next step

References: `docs/data-sources.md`, `docs/personal-data.md`, `data/LICENSE.md`, `docs/source-rights-evidence.json`. Prozorro requires attribution (no named API licence inferred); FTS is OGL v3.0; TED permits free reuse; SECOP II is **CC BY-SA 4.0**, including private evidence if redistributed. Terms do not clear privacy or attachments.

Prioritize the negative BOAMP payable, then a small zero/conflict cohort under a separately approved exact-ID fetch plan. Recovery needs same-basis evidence/provenance; conversion, ceiling allocation, award substitution and choosing DECP alternatives are unsupported.
