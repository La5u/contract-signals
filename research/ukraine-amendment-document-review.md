# Ukraine supplemental primary-document review

## v2 follow-up: corrected official-publisher policy

**One supplementary HTTP request executed; overall total 29/30.** The first frozen document returned **HTTP 302**. The redirect was not followed, its destination was not published or requested, and the global failure policy stopped the sequence. The second document (PDF) was **not attempted**. One original supplementary slot remains unused, but this sequence is closed: no retry, replacement URL or replacement document is permitted.

The initial allowlist was unnecessarily narrow: `public-api.prozorro.gov.ua` is the **same official publisher**, not a different source. v1's zero-attempt plan, evidence and private freeze remain unchanged as a historical blocked diagnostic. The original host-policy rejection and missing `pdftotext` did **not** establish publisher/host inaccessibility. v2 observed a redirect from the published API link, not an unavailable host or unavailable PDF.

### Separate pre-attempt freeze and exact selection

- New plan: `data/ukraine-amendment-document-plan-v2.json`.
- New evidence: `data/ukraine-amendment-document-evidence-v2.json`.
- v2 freeze time: `2026-10-11T19:58:46.399156+00:00`.
- v2 plan SHA256: `30052ea378cf01d7b25fe04ea4a2c9499bd854346f209ee1e3e7776d29464b83`.
- v2 evidence SHA256: `523dc4011610c8eb593c2f92e01448271c478fe4af615cf64977708ae20d5f8d`.

The hash-verified **existing** module cache supplied exactly the same two documents, order, metadata pointers and published URLs as v1. Only the publisher policy changed. Both paths exactly match native `/api/2.5/contracts/{FULL frozen contractUUID}/documents/{docID}`, using contract UUID `3c4d872cb91c4af09e7486743fa8e025`; no path exception or URL guessing was required. The exact published URL strings—including any signed query—remain private, transmitted as published without signature acquisition or substitution. Public artifacts contain only their SHA256 and metadata bindings, not download URLs or redirect destinations.

| Order | Document ID | Exact published URL SHA256 | v2 outcome |
| --- | --- | --- | --- |
| 1 | `38728a86391e4a36b8a3eee93fe3cb86` | `91d709ca1af296b265afb455a71d56b1526e9b924582ee98cd52f29a0504847b` | HTTP 302; redirect not followed; global stop |
| 2 | `6c896cc6a2b64954a0100a2c6347a019` | `b279e15ca90b6ed4782e9f064e9308b943ec5e41552ab59a020345516052be9d` | Not attempted after global failure |

The single GET ran `2026-10-11T19:59:28.018056+00:00`–`2026-10-11T19:59:28.232177+00:00`, strictly after the public/private freeze and offline verification. It returned HTTP 302; no response body was read. The recorded zero bytes and empty-byte SHA256 describe the helper's captured bytes, **not a claim that the server's redirect body was empty**. The unattempted PDF retains null HTTP/body fields. No primary-document content or page fact was extracted. Legal basis and independent financial basis remain **unknown**; the reference `9185/25/39` is still module-only evidence.

### Bounded acquisition and reproduction

The helper permits at most two requests, a 15-second wall deadline per request, a 2 MiB body limit (one extra sentinel byte detects oversize), and one-second spacing after completion if a second request is eligible. It makes no retries, follows no redirects, rejects URL userinfo (including empty userinfo), disables proxies, and performs no authentication, login or challenge bypass. Any transport/HTTP/size/extraction failure stops the sequence; 302, 403 and 429 are failures. No publisher index, schema, metadata refetch or other request was made.

`pdftotext`, `pypdf` and PyMuPDF (`fitz`) were absent in the system/tool environment tested by the worker. A later check confirmed **pypdf 6.19.0 is already installed in the existing optional private venv**; claiming it was unavailable everywhere locally was too broad. No installation, network OCR or upload was performed, and no extraction was attempted because the redirect was not followed. If a PDF had been obtained, only already-installed local Python extraction would be eligible; the helper emits only an exact binder-reference match with a 1-based page anchor, never full page text or personal information. It does not infer independent legal or financial basis from metadata or a binder match.

Default verification is v2, entirely offline and independent of private cache availability. Historical replay remains explicit:

```sh
python3 tools/review-ukraine-amendment-documents.py
python3 tools/review-ukraine-amendment-documents.py --version 1
python3 -m unittest discover -s tests -p test_review_ukraine_amendment_documents.py -v
```

Freeze and attempt are deliberately separate commands (`--freeze-from-cache PATH`, then `--attempt-frozen`); **do not rerun acquisition for this completed sequence**. Exclusive private reservation prevents replay even following an interruption. The v2 directory is `/home/lasu/.cache/contract-signals/ukraine-amendment-documents/v2` (0700), containing immutable `plan.json` (0400), `attempt-ledger.json` and `request-1.json` (0600). No document byte file exists because the redirect body was not read; any captured bytes would be stored 0600 outside Git. The v1 private freeze remains 0400 and unchanged. Public offline checks verify source/history hashes, same ordered selection, policy, request bindings, timing, spacing, budget, and attempted/unattempted document outcomes; exact URL-to-module comparison additionally requires the private cache.

## Historical v1 report (preserved below)

The following sections describe **v1 only**, including its original overly narrow host-policy conclusion and zero-attempt total. Its reproduction command without `--version 1` now verifies v2; use the explicit historical command above for v1 replay. No historical JSON or private freeze was rewritten.

## Result and scope

**Additional HTTP requests executed: 0. Overall requests remain 28/30.** The two supplementary slots remain unused. No contract-module refetch, discovery, schema, index, source or document request was made during this inspection. Primary-document contents were not inspected; legal basis and independent financial basis remain **unknown**. This is a metadata-selected supplemental diagnostic, not an attachment preregistration in the original frozen protocol, representative accuracy exercise or legality benchmark.

Only the sole three-change contract in the original frozen 12-contract sample was considered:

- Row: `prozorro-UA-2025-01-14-015633-a-3c4d872c` (cohort pointer `/96`).
- Full public contract ID: `UA-2025-01-14-015633-a-c1`.
- Exact buyer-side contract reference in module metadata: `9185/25/39`, `/data/contractNumber`. This is **not** a reference independently verified in a document body.
- Buyer linkage: `/data/buyer/identifier/id`, bound to the original selected buyer ID; contract, tender and award identities also checked exactly.
- Public endpoint: `https://public-api.prozorro.gov.ua/api/2.5/contracts/3c4d872cb91c4af09e7486743fa8e025`.
- Existing module response: 88,856 bytes, SHA256 `8f1be160935bc96f267539aff0111c321cfce18d08d41c5372d452564e243bae`; retrieved `2026-10-11T19:41:50.222688+00:00`–`2026-10-11T19:41:50.478622+00:00`, HTTP 200. These are inherited module acquisition times, **not** document-request times.

## Frozen supplemental selection

Original plan hash: `6e8d5583760933a7dff4a00e9419fcd0af3bb7577f63b78b078ca5b3ece9dcbf`.
Supplemental plan hash: `52d6e3744e7e3f1be1f7d08cc782777f80b50e42c054e57ca32f3962848a8fb7`.
Supplemental freeze time: `2026-10-11T19:52:43.725439+00:00`, after metadata inspection and before any possible new body request. The private freeze was written exclusively with mode 0400 outside Git, with a minimized public plan written before any new request. The original protocol and other workers' files were not modified.

Selection used ascending SHA256 of canonical JSON `[rowId, docId]` over documents explicitly marked `documentOf=change` whose `relatedItem` equals one of the three active change IDs. Unique document IDs and exact URLs were required. All linked formats were eligible: no PDF, title, date or host substitution was used to change the ranking. Both selected records bind to change `35f8a1f8d8bb4fb48572f92755518450`.

| Order | Document ID | API JSON pointer | Published format | Outcome |
| --- | --- | --- | --- | --- |
| 1 | `38728a86391e4a36b8a3eee93fe3cb86` | `/data/documents/6` | application/pkcs7-signature | Not attempted: host policy |
| 2 | `6c896cc6a2b64954a0100a2c6347a019` | `/data/documents/5` | application/pdf | Not attempted: host policy |

The **exact published URLs** for both records are on `public-api.prozorro.gov.ua`, not the allowed `public-docs.prozorro.gov.ua` or `publisherdocservice.prozorro.gov.ua`. Requesting the API links to discover a redirect would itself violate the host constraint. No host rewriting, signature derivation, redirect resolution, login, token acquisition or replacement-document selection was attempted. Exact URLs are omitted from public artifacts, not replaced with fabricated download URLs. The public plan/evidence retain document IDs, API metadata pointers and SHA256 of each exact URL; the private ledger retains the original URLs as published.

`pdftotext` is not installed locally. No installation, external OCR or upload was attempted. No body was obtained, PDF recognition is unobserved (null), extraction method is `none`, and no page/paragraph facts, financial values, statutory provisions or addendum ordinals are claimed. Null HTTP/body hashes and sizes mean **not attempted**, not failed downloads or empty responses.

## What the three-change indicator represents

The hash-matched module has exactly three `/data/changes` records, each explicitly `active`:

| Metadata anchor | Signed timestamp | Published rationale category |
| --- | --- | --- |
| `/data/changes/0` | 2025-02-05T15:00:00+02:00 | qualityImprovement |
| `/data/changes/1` | 2025-12-31T11:24:00+02:00 | fiscalYearExtension |
| `/data/changes/2` | 2026-02-26T15:00:00+02:00 | fiscalYearExtension |

These are source metadata anchors, **not document-content anchors**. In the frozen source, `script.js`'s `ua-contract-amendments` assessment tests integer `contractChanges >= 3` and assigns eight points when met. It represents a count threshold on active amendment records, not three proven price increases, three illegal changes, three independent financial events, or a lawfulness finding. The published rationale categories alone do not independently establish a statutory basis, explain a monetary increase, or prove that a particular document contains a lawful extension. The module's overall contract status being terminated does not change its change records' explicit active statuses.

The exact body reference and buyer/contract linkage required for a substantive document conclusion cannot be verified here. Neither dates, filenames, metadata similarity nor the generic article-41 explanation in application UI substitutes for an explicit document provision. No legality certification or increase-basis inference is made.

## Reproduction and private local checks

Public minimized offline verification (no network or private-cache dependency):

```sh
python3 tools/review-ukraine-amendment-documents.py
python3 -m unittest discover -s tests -p test_review_ukraine_amendment_documents.py -v
```

The offline verifier checks original frozen source hashes/current cohort bindings, module-ledger integrity, supplemental plan/evidence hashes, document IDs/pointers/formats, active-change identities/statuses, dates, selection-rank bindings and attempt counts. Public hashes cannot recreate omitted raw bytes or independently reproduce exact omitted URL linkage; those require private local checks. The tool intentionally exposes no live acquisition CLI for this blocked selection. Its bounded GET primitive rejects unapproved hosts before constructing a request, disables redirects/proxies, has a 15-second wall deadline, reads at most 2 MiB plus one byte, and makes one attempt without retries. There was no request sequence requiring one-second spacing in this run.

Private paths (do not publish their contents):

- Existing raw module: `/home/lasu/.cache/contract-signals/ukraine-amendments/run-uwylob7h/response-04.bin`.
- Supplementary private selection ledger: `/home/lasu/.cache/contract-signals/ukraine-amendment-documents/v1/plan.json` (directory 0700, ledger 0400).
- No supplementary raw body cache exists because no downloads occurred.

For local verification, compare the module bytes/hash/size with the inherited request entry; resolve each frozen pointer in that module and compare exact URL SHA256, document ID, related change, publication timestamps and selection rank with the public plan. The private ledger embeds that same public plan and the two exact original URLs. Nothing was committed or pushed, and unrelated dirty files were preserved.
