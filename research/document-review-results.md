# Frozen document review: first bounded pass

Review date: 2026-10-08 UTC. This is assistant-assisted document reading, **not independent expert validation**. Six purposively selected rows cannot estimate dataset accuracy, validate corruption predictions, or clear a whole cohort. Selection was frozen before reading under `document-review-protocol.md`; no row was substituted when access failed. No published record, amount, date or score was changed.

Frozen plan SHA-256: `6533cc7c41384b2e7d33fd6c06e8f0fd5d6409634b236e56901ef481a1609b03`.

## Outcomes

| Frozen stratum / record | Evidence read | Outcome |
| --- | --- | --- |
| Flagged positive: BOAMP `25-11411`, `LOT-0001` | Official 11-page notice PDF; result pp. 5–6, notice UUID/version p. 11 | Result value **138,555 EUR**, conclusion **2024-09-09**, and **one offer** agree with imported fields. Same procedure UUID, notice UUID/version 01, exact lot, and printed contract reference established. Tax basis remains unresolved; this is a rendered notice, not the signed insurance contract. |
| Zero score, positive amount: BOAMP `25-11426`, `LOT-0001` | Initial official-template PDF endpoint returned 404 | **Not document-verified.** The schema-specific endpoint was established later, but the eight-request BOAMP budget was exhausted before fetching this fourth document. No claim of corroboration from the failed request. |
| Declared zero: BOAMP `25-11531`, `LOT-0005` | Official 16-page notice PDF; result pp. 10–11, UUID/version p. 16 | Exact result states **0 EUR**, conclusion **2024-12-23**, two offers. Retaining zero accurately reproduces the notice. This does **not** show the insurance service was free or that the declaration is economically correct. The positive whole-notice total must not be allocated to this lot. Tax basis unresolved. |
| Missing amount: BOAMP `25-11359`, `LOT-0001` | Official 7-page notice PDF; result pp. 4–5, UUID/version p. 7 | No winning-result amount appears in the selected result. It states a **1,000,000 EUR lot framework ceiling**, distinct from the **1,240,000 EUR procedure ceiling**. Neither is a replacement for winning-tender PayableAmount. Conclusion **2024-12-27** agrees. Electronic-submission count is not substituted for total tenders. |
| DECP initial conflict: buyer `21210231300013`, contract `2023VDAO1642` | Six retained Ministry records, plus exact buyer/contract match across all years in private national parquet | Six distinct Ministry amounts remain unresolved. The national snapshot contains one initial row at **456,516.27 EUR**, corresponding to one existing alternative; it does not establish authoritative precedence or disprove the other variants. No original buyer contract was acquired. Keep the row excluded and its amount null. |
| Paraguay published contractSigned: OCID `ocds-03ad3f-452188-1`, contract `MN-30173-24-244215` | Official five-page scanned contract linked by the exact retained contract/award/document URL; all page images inspected | Page 1 identifies procurement **452188**. Page 4 states total **252,144,563 guaraníes**, explicitly **IVA incluido**, agreeing numerically with the normalized amount. Page 5 has signature marks and a handwritten subscription date read as **2024-10-21**. That date is a **private review candidate**, not a filled published signature date. Full OCDS contract ID is not printed; canonical contract linkage rests on metadata. Handwritten local contract number remains unresolved. Signature authenticity and payment are unverified. |

## New context, not silent repairs

- **Framework ceiling:** the missing BOAMP amount has separately typed monetary context, not a recovered comparable amount. Amount remains null.
- **Signature-date candidate:** the Paraguay scan supplies documentary evidence beyond the API's absent `dateSigned`. The normalized `date` remains the source period start; the candidate must not silently change that field's meaning. The handwritten date requires independent checking before integration, with exact document linkage and provenance.
- **Tax evidence:** the Paraguayan total explicitly includes VAT. It must not be compared with an assumed tax-exclusive amount. No global currency/tax schema change is justified by one document.
- **Duration:** the Paraguayan document describes 120 calendar days **from a start order**, not 120 days from signature. No end date is inferred.

## Acquisition and matching

Private evidence root: `~/.cache/contract-signals/document-review/`. Do not commit or serve PDFs, scans or extracted text, which contain personal identifiers, signatures and contact details. Private review findings minimize those fields.

BOAMP requests: **eight total**, including the official source-page HTML fetched before interruption. The HTML was a JavaScript template, not a populated notice. Its documented PDF endpoint switches on `source_schema`: the initial four requests used the non-eForms branch and returned 404. Inspection of the template and retained `source_schema=3.2.5` established the correct official eForms branch, `/telechargements/FILES/PDF/{year}/{month}/{idweb}.pdf`; three PDFs were then fetched successfully within the budget. Failures are retained, not hidden. No retries of the same endpoint, redirects, proxy bypass, attachment crawl or additional requests were performed. Bounds: 15-second timeout, 5 MiB body limit, at least two seconds between BOAMP requests, stop on refusal/rate limit/server failure.

DNCP: **one exact frozen document request**, HTTP 200, 1,692,537 bytes; no redirects/retries. Response is a PDF despite generic octet-stream content type. Text extraction was empty; embedded page images were extracted privately and visually inspected. A page image crop assisted reading the procurement number and subscription date. PDF signature marks are not a cryptographic/authenticity check.

Official document SHA-256:

```text
466ec777514814dad932da6d60b0e9ea9cd27a26954fb9b2a4027b27145bad55  BOAMP 25-11411 PDF
107b82dd521a5fdb4a438b77ebde3f27dee51d96d29ddad93e2ea705b4e7ecf5  BOAMP 25-11531 PDF
ae7d7fc34cb76e2d018814d3a446fb66b616f5059af23f9d1a651140db5d3d6b  BOAMP 25-11359 PDF
2c6c496b2f24599e1b96f0ac8fa46c1616536dcd49be3f21543c74de87875793  DNCP linked scan
```

Exact notice UUID/version and procedure UUID are matched to the retained eForms root, and result sections are matched by the exact lot. The internal `CON-*` identifier is mapped through its retained `ContractReference` to the printable contract reference; it is not expected to appear verbatim in the rendered PDF. An amount appearing elsewhere in a notice does not corroborate the selected row. None of the three inspected notice result amounts/dates disagreed with the imported fields, but tax and underlying contract truth remain unresolved.

## Reproduction and tests

The new offline helper reads already acquired PDFs only, verifies acquisition hashes and frozen published snapshot hashes, and scopes extraction to exact lot-result sections:

```sh
~/.cache/contract-signals/venv/bin/python tools/review-boamp-documents.py
python -m unittest discover -s tests -p 'test_review_boamp_documents.py'
```

It requires private-environment `pypdf`; page-image extraction additionally used Pillow. Six synthetic tests cover lot scoping, zero versus missing, ceilings, electronic-submission counts, ambiguous fields, invalid dates and monetary formatting. These tests do not validate document truth. The full repository suite passed after this pass: 291 Python tests, all JavaScript suites, and the browser test. The Paraguayan visual interpretation is recorded separately in private `paraguay-document-result.json`; automated text extraction cannot reproduce the handwritten interpretation.

## Subsequent Dijon investigation

The later bounded follow-up in `decp-dijon-conflict-review.md` supplies an explanation beyond this initial pass: exact BOAMP notice 24-79759 treats `2023VDAO1642` as a procedure ID and has distinct lot contracts corresponding to all six DECP amounts. Three candidate lot pairings disagree on offer counts. The grouped published row remains excluded; no amount or score was filled and individual holder/tax comparability is still unresolved. The older national-snapshot observation above must not be read as a reason to choose its lone amount.

## Remaining gates

1. Review the signature-date candidate and scanned identity with a separate qualified reviewer; no independent reviewer has been obtained.
2. Acquire the unreviewed BOAMP zero-score document in a separately bounded follow-up without replacing the frozen row.
3. Locate authoritative buyer-profile contract/lot/version evidence for the unresolved DECP conflict; do not prefer the national row solely because it is unique there.
4. Continue primary legal verification and schema/basis review before changing scores or integrating new evidence.
