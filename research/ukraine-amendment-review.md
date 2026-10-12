# Ukraine frozen amendment audit

## Protocol and replay

Owned outputs only: `tools/audit-ukraine-amendments.py`, `tests/test_audit_ukraine_amendments.py`, `data/ukraine-amendment-evidence.json`, and this review. No scoring, source snapshot, shared-file, commit or push changes.

Frozen plan SHA-256: `6e8d5583760933a7dff4a00e9419fcd0af3bb7577f63b78b078ca5b3ece9dcbf`. Both the public plan and the private read-only (0400) freeze were checked before acquisition. Default offline replay now needs only the public plan and repository inputs; the private freeze is required only for opt-in acquisition. Verification checks canonical plan hash, all five source file hashes, all 488 compressed tender hashes, the selection-helper hash, and a complete rebuild of the exact frozen round-robin selection. All full selected IDs, URLs and row hashes must match; there is no replacement after access outcomes.

Default, **offline** verification:

```sh
python tools/audit-ukraine-amendments.py
python -m unittest discover -s tests -p 'test_audit_ukraine_amendments.py' -v
```

`--fetch` is explicitly opt-in and refuses repeat acquisition when the evidence output exists. It was run **once** for this review. The subsequent scalar refinement and verification reused the same private response bytes, checked against the recorded hashes, with **no additional requests**.

## Acquisition ledger and privacy

Exactly **12 actual GET requests**, all to the twelve frozen contracting-module URLs, all **HTTP 200**, all complete and exact-identity verified. **0 supplementary requests** (neither schema nor documents). Total response bytes: **859,773**. Acquisition timestamps: **2026-10-11T19:41:45.589520+00:00** through **2026-10-11T19:41:57.435952+00:00**. The ledger in `data/ukraine-amendment-evidence.json` records every actual URL, method, start/finish time, HTTP status, transport completion, full response byte size/SHA-256, full frozen row binding and selected scalar JSON pointers.

The fetch uses a 15-second curl limit, 2 MiB body cap, at least one second between request starts, no redirects, retries, credentials, or authentication bypass, and a global stop on HTTP 403/429. No such stop occurred. This worker's 12 requests plus the five already-spent discovery requests and the separately reserved eleven amount-worker requests total 28, leaving the two supplementary slots unused (overall ceiling 30). The amount-worker requests are not this worker's observations or ledger entries.

Raw responses were exclusively created outside the repository in a new private 0700 run directory, with 0600 files and no symlink traversal. They are not published or added to git; no source personal information is printed. Public evidence contains full binding IDs, status/date/category metadata, allowlisted value scalars, and document IDs/MIME/published document-type categories, but no supplier/contact names, addresses, text titles, free-form rationale, document download URLs or tokens. Private response locations are not published, only local response basenames. Byte hashes are acquisition commitments; public minimized replay cannot independently reconstruct the withheld raw bodies or establish official signatures.

## Offline inventory: all 488 cohort rows

All 488 row identities are unique and fully bound to canonical row hashes, frozen compressed tender hashes, contract and award JSON pointers, buyer identifier and lot. Each cached tender has exactly one matching contract and award; buyer/tender/contract/award/lot identities and official tender endpoints match the row. Non-null lots map uniquely to the cached tender's lots. Complete minimized amendment-snapshot coverage and exact row count/type agreement were checked.

| Old minimized change count | Rows |
| --- | ---: |
| 0 | 469 |
| 1 | 13 |
| 2 | 5 |
| 3 | 1 |

Old module-status inventory: **256 active**, **232 terminated**. Snapshot rationale-type incidences across contracts: volumeCuts 2; fiscalYearExtension 4; qualityImprovement 7; priceReductionWithoutQuantity 5; taxRate 1; durationExtension 1. These are contract-level type incidences, not counts of individual amendments. The old snapshot has 26 counted amendments but does not preserve individual change IDs/statuses/dateSigned-presence. Stored change-date strings have **0 parse/timezone anomalies**. No unknown stored status/type categories were found.

**Important historical limitation:** the old 488-contract minimized amendment snapshot lacks full module-body hashes and module identity/link fields. Cached tenders independently support row-to-tender contract/award/buyer/lot mapping, but cannot retrospectively independently prove that all 488 old contracting-module responses linked correctly, nor that old zero counts represented retrieved empty arrays rather than omitted `changes`. Old counts are snapshot claims, not new independent module-link proofs. The three earlier minimized link records have source hashes but do not cure coverage for all 488; their presence is not promoted into universal proof.

## Twelve retrieved modules

Each retrieved module passed exact checks of `id`, `contractID`, `tender_id`, and `awardID` against its frozen selected row and cached tender before amendment assessment.

- **6 modules contain a nonempty `changes` array**, with sizes **1, 2, 3, 1, 1, 2** (10 changes total). Counts agree with their six frozen nonzero counts. Every one of the **10 change IDs is unique within its module**, every change status is **active**, and all 10 have parseable timezone-bearing `date` and `dateSigned` values. This checks published metadata, not the legality of an amendment.
- **6 modules omit `changes` entirely**. Their old snapshot counts are zero, but current evidence explicitly records **unavailable**, `changeCount: null`, and `activeChangeCount: null`. **No retrieved empty array was observed.** No published schema default was validated at the time, so omission was **not** treated as zero. **Resolved later the same day:** the publisher's API source omits empty lists and creates `changes` only on the first change, so these six are zero changes ([correction log](ukraine-corrections-log.md)).
- Retrieved module statuses: **4 active**, **8 terminated**. Contract status is separate from change status; terminated contracts can have active change records.
- Change rationale categories: **volumeCuts 1**, **fiscalYearExtension 6**, **qualityImprovement 3**. Quality improvement and fiscal-year extension are published categories only, **not legal findings**, financial substantiation, or evidence of misconduct.
- **66 document metadata records** were minimized. No document bodies were requested or interpreted. No independent legal or financial basis was established; both remain **unknown** for every reviewed module. No OCR, inferred amounts, or third-party download/token bypass was used.

### Calendar-date observations, not proven errors

The following module `dateSigned` values precede the calendar date embedded in the tender's public ID. They are retained as descriptive timing observations, not repaired or labelled illegal:

| Full row ID | Module dateSigned | Tender-ID calendar date |
| --- | --- | --- |
| `prozorro-UA-2024-09-17-013954-a-9e43a93d` | `2024-09-13T17:34:00+03:00` | 2024-09-17 |
| `prozorro-UA-2025-04-08-002179-a-39c07eef` | `2025-04-07T09:00:00+03:00` | 2025-04-08 |
| `prozorro-UA-2025-12-23-021689-a-04e0f9f5` | `2025-12-22T20:00:00+02:00` | 2025-12-23 |

All three are reporting procedures: contract signing can precede creation of its report. The comparison is to a tender-ID calendar date, not an independently determined legal publication/signature chronology. The extractor's descriptive `anomalies` field is not a finding that these dates are erroneous. There were no retrieved module-ID mismatches, duplicate change IDs, malformed stored change dates, or missing change dateSigned fields in the six nonempty arrays. Omitted arrays prevent assessment in the other six.

## Tests and limitations

**11 tests pass** (including the added no-private-freeze offline check), including full-population offline replay/source immutability; stale source/hash and incomplete row binding rejection; duplicate selection/wrong full IDs/endpoints; missing versus empty versus zero; actual active-change counts, duplicate-ID/date/type anomalies; scalar privacy and duplicate/unsafe pointers; request count/body/spacing/stop bounds; no redirect/retry fetch configuration; exclusive 0600 files and external 0700 directory checks. Replay re-applies the allowlist, identity, count, status, date and anomaly checks from the minimized scalar pointers and rejects unexpected ledger fields.

No legal or accuracy rate is inferred. The twelve-row selection is the exact frozen strata sample, not an independent representative accuracy sample. Outstanding blockers are missing historical full module/link provenance, and lack of independently inspected legal/financial documentation. A separately frozen attachment follow-up subsequently attempted one public API document URL (HTTP 302, not followed), stopping before its second document; [attachment history](ukraine-amendment-document-review.md) and [overall audit](ukraine-public-audit.md) preserve the total **29/30** attempts. This does not alter the twelve module acquisitions recorded here. No score, weight, source data or dashboard field is changed by these observations.
