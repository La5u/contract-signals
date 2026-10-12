# Ukraine frozen amendment audit

## Protocol and replay

Frozen plan: `6e8d5583760933a7dff4a00e9419fcd0af3bb7577f63b78b078ca5b3ece9dcbf`. Offline replay checks the public plan, five source files, all 488 compressed tenders and the exact round-robin selection; only acquisition requires the private 0400 freeze. Full IDs, URLs and rows must match, with no replacements after access outcomes.

```sh
python tools/audit-ukraine-amendments.py
python -m unittest discover -s tests -p 'test_audit_ukraine_amendments.py' -v
```

Evidence: `data/ukraine-amendment-evidence.json`; tests: `tests/test_audit_ukraine_amendments.py`. `--fetch` was run once and refuses acquisition when evidence exists. **12 GETs**, all complete **HTTP 200**, yielded **859,773 bytes** on 11 October 2026. Requests used a 15-second limit, 2 MiB cap, one-second start spacing, no redirects/retries and a stop on 403/429. Raw bodies remain outside Git in 0700 directories/0600 files; public evidence excludes personal details, free text and download URLs. Hashes bind local evidence but cannot reconstruct withheld bodies or establish official signatures.

## All 488 cohort rows
All row identities, tender/contract/award/buyer/lot mappings, source pointers and amendment-summary coverage agree; matching contracts, awards and non-null lots are unique.

Stored change counts: **469 zero, 13 one, 5 two, 1 three**.

Module statuses: **256 active, 232 terminated**. Contract-level rationale incidences: volumeCuts 2; fiscalYearExtension 4; qualityImprovement 7; priceReductionWithoutQuantity 5; taxRate 1; durationExtension 1. The snapshot counts **26 amendments**, but lacks individual IDs/statuses/signature-date presence and full module hashes/links. Stored date strings have **0 parse/timezone anomalies**; no unknown stored status/type categories. Cached tender mappings and three earlier hashed module-link records cannot prove all 488 historical module links.

## Twelve retrieved modules

- Every `id`, `contractID`, `tender_id` and `awardID` matches its frozen row and cached tender.
- Six nonempty arrays have sizes **1, 2, 3, 1, 1, 2**: **10 active changes**, unique IDs within each module, parseable timezone-bearing `date` and `dateSigned`, and counts matching the snapshot.
- Six omitted arrays remain recorded as `unavailable` with null counts in raw evidence. Publisher code later confirmed omission means zero ([correction log](ukraine-corrections-log.md)); all 12 counts agree.
- Module statuses: **4 active, 8 terminated**. Change categories: **volumeCuts 1, fiscalYearExtension 6, qualityImprovement 3**. A terminated contract can retain active change records.
- **66 document metadata records** were retained; legal and financial basis remain unknown for every module.

| Row ID | Module dateSigned | Tender-ID date |
| --- | --- | --- |
| `prozorro-UA-2024-09-17-013954-a-9e43a93d` | `2024-09-13T17:34:00+03:00` | 2024-09-17 |
| `prozorro-UA-2025-04-08-002179-a-39c07eef` | `2025-04-07T09:00:00+03:00` | 2025-04-08 |
| `prozorro-UA-2025-12-23-021689-a-04e0f9f5` | `2025-12-22T20:00:00+02:00` | 2025-12-23 |
All three are reporting procedures, where signing can precede report creation. The extractor's `anomalies` field describes this comparison; it does not establish a date error or illegality. No retrieved ID mismatches, duplicate change IDs or missing signature dates were found in nonempty arrays.

**11 tests passed**, covering offline replay without a private freeze, stale inputs and incomplete links, selection, field states, counts/dates/categories, privacy, request bounds and private storage. Historical full module provenance and independently inspected legal/financial documents remain missing. This strata sample provides no representative accuracy rate. The attachment follow-up returned 302 and stopped: see [attachment history](ukraine-amendment-document-review.md) and [overall audit](ukraine-public-audit.md), **29/30 attempts** overall. Scores, weights and source data are unchanged.
