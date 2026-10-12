# Ukraine supplemental primary-document review

## Result

**v2: first document returned HTTP 302; redirect not followed, second document not attempted.** Overall audit total: **29/30 requests**. The sequence is closed; no retry or replacement. No document content was extracted, so legal and independent financial basis remain unknown. Zero captured bytes describe unread redirect bytes, not an empty server response; the unattempted PDF has null HTTP/body fields.

v1 made **zero requests** (overall total then **28/30**). Its allowlist wrongly excluded the official publisher `public-api.prozorro.gov.ua`, admitting only `public-docs.prozorro.gov.ua` and `publisherdocservice.prozorro.gov.ua`. This local restriction did not establish publisher or PDF inaccessibility. v2 retained the same selection and admitted exact native `/api/2.5/contracts/{FULL frozen contractUUID}/documents/{docID}` paths. Historical JSON and private freezes remain unchanged.

## Selection and evidence

Only the sole three-change contract in the frozen 12-row sample was considered:

- Row `prozorro-UA-2025-01-14-015633-a-3c4d872c`, cohort pointer `/96`; contract `UA-2025-01-14-015633-a-c1`.
- Module-only contract reference `9185/25/39`, `/data/contractNumber`; exact buyer linkage `/data/buyer/identifier/id`, plus tender/contract/award identities.
- Endpoint: `https://public-api.prozorro.gov.ua/api/2.5/contracts/3c4d872cb91c4af09e7486743fa8e025`.
- Existing module: **88,856 bytes**, HTTP 200, retrieved `2026-10-11T19:41:50.222688+00:00`–`2026-10-11T19:41:50.478622+00:00`.

Selection ranked canonical `[rowId, docId]` by ascending SHA256, requiring unique IDs/URLs, `documentOf=change` and `relatedItem` matching an active change. All formats were eligible. Both selected documents bind to change `35f8a1f8d8bb4fb48572f92755518450`; v2 preserved their order, metadata pointers and exact published URLs. Public hashes bind plans, cached bodies and URL strings; exact omitted URL linkage requires private bytes and does not establish remote authenticity.

| Order | Document ID | Metadata pointer | Format | v2 outcome |
| --- | --- | --- | --- | --- |
| 1 | `38728a86391e4a36b8a3eee93fe3cb86` | `/data/documents/6` | application/pkcs7-signature | 302; stop |
| 2 | `6c896cc6a2b64954a0100a2c6347a019` | `/data/documents/5` | application/pdf | Not attempted |

- v1: `data/ukraine-amendment-document-plan.json`, `data/ukraine-amendment-document-evidence.json`; frozen **2026-10-11T19:52:43.725439+00:00**, after metadata inspection and before body requests.
- v2: `data/ukraine-amendment-document-plan-v2.json`, `data/ukraine-amendment-document-evidence-v2.json`; frozen **2026-10-11T19:58:46.399156+00:00**. GET: **2026-10-11T19:59:28.018056+00:00–2026-10-11T19:59:28.232177+00:00**.

## What the indicator means

| Active change anchor | Signed timestamp | Category |
| --- | --- | --- |
| `/data/changes/0` | 2025-02-05T15:00:00+02:00 | qualityImprovement |
| `/data/changes/1` | 2025-12-31T11:24:00+02:00 | fiscalYearExtension |
| `/data/changes/2` | 2026-02-26T15:00:00+02:00 | fiscalYearExtension |

`script.js`'s `ua-contract-amendments` tests integer `contractChanges >= 3` and assigns **eight points**. It counts active records, not proven increases or unlawful amendments. Terminated contract status does not change active amendment status. Metadata categories, dates, filenames and the UI's generic article-41 explanation cannot replace explicit document provisions or verify the body reference and buyer linkage.

## Reproduction and acquisition limits

```sh
python3 tools/review-ukraine-amendment-documents.py
python3 tools/review-ukraine-amendment-documents.py --version 1
python3 -m unittest discover -s tests -p test_review_ukraine_amendment_documents.py -v
```

Default replay verifies v2 offline without private caches; `--version 1` verifies history. Checks cover sources, cohort bindings, ordered selection, policy, timing, budget and outcomes. Freeze (`--freeze-from-cache PATH`) and attempt (`--attempt-frozen`) are separate; exclusive private reservation prevents repeat attempts after interruption. Limits: two requests, 15-second wall deadline, 2 MiB cap plus sentinel, one-second spacing after completion, no redirects/retries/proxies/authentication; reject URL userinfo and stop on transport, HTTP, size or extraction failure, including 302/403/429. Signed URLs and redirect destinations remain private.

System/tool checks found no `pdftotext`, `pypdf` or PyMuPDF (`fitz`), but **pypdf 6.19.0** was already installed in the optional private venv. Local Python extraction would emit only an exact binder-reference match with a 1-based page anchor; that match alone cannot establish legal or financial basis. No body was obtained or extraction attempted.

Private paths: `/home/lasu/.cache/contract-signals/ukraine-amendments/run-uwylob7h/response-04.bin`; `/home/lasu/.cache/contract-signals/ukraine-amendment-documents/v1/plan.json`; `/home/lasu/.cache/contract-signals/ukraine-amendment-documents/v2` (0700), with `plan.json` (0400), `attempt-ledger.json` and `request-1.json` (0600). Neither version has a document body cache. Local verification compares module size/hash, pointers, URL hashes, IDs, related changes, publication timestamps and ranks against the private plan. This metadata-selected follow-up is not a representative legality or accuracy benchmark.
