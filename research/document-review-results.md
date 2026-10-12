# Frozen document review: first bounded pass

Reviewed 2026-10-08 UTC under `document-review-protocol.md`: six purposive rows, no replacements after access failure. Assistant-assisted reading is not independent expert validation or a dataset-accuracy estimate. No published record, amount, date or score changed. Frozen plan and acquisition hashes bind the private evidence.

## Outcomes

| Frozen record | Evidence and finding |
|---|---|
| Flagged positive: BOAMP `25-11411`, `LOT-0001` | 11-page official notice, result pp. 5–6, UUID/version p. 11. **138,555 EUR**, conclusion **2024-09-09**, **one offer** agree. Procedure UUID, notice UUID/version 01, lot and printed reference match. Tax unresolved; rendered notice, not signed insurance contract. |
| Zero score, positive amount: `25-11426`, `LOT-0001` | Initial PDF endpoint returned 404. The correct schema-specific endpoint was found later, but the eight-request budget ran out before fetching this fourth document. **Not document-verified.** |
| Declared zero: `25-11531`, `LOT-0005` | 16-page notice, result pp. 10–11, UUID/version p. 16: **0 EUR**, conclusion **2024-12-23**, **two offers**. Zero reproduces the notice, without establishing free service or economic correctness. Do not allocate the positive notice total to this lot. Tax unresolved. |
| Missing amount: `25-11359`, `LOT-0001` | 7-page notice, result pp. 4–5, UUID/version p. 7: no winning-result amount. **1,000,000 EUR lot ceiling** and **1,240,000 EUR procedure ceiling** cannot replace PayableAmount; amount stays null. Conclusion **2024-12-27** agrees. Electronic submissions are not total tenders. |
| DECP: buyer `21210231300013`, `2023VDAO1642` | Six Ministry amounts unresolved. Exact all-years national-parquet match has one initial row at **456,516.27 EUR**, an existing alternative without authority over the others. No original buyer contract acquired; keep excluded with null amount. |
| Paraguay: OCID `ocds-03ad3f-452188-1`, contract `MN-30173-24-244215` | Five-page linked scan, all pages inspected. P. 1: procurement **452188**. P. 4: **252,144,563 guaraníes**, **IVA incluido**, numerically agrees. P. 5: signature marks and handwritten **2024-10-21**, a private signature-date candidate needing independent review. Full OCDS ID is not printed; linkage rests on contract/award/document metadata. Local handwritten number, authenticity and payment remain unresolved. |

Paraguay's normalized date remains period start, not the handwritten signature candidate. Its VAT-inclusive total cannot be compared to an assumed tax-exclusive amount. Duration is **120 calendar days from a start order**; no end date follows from signature.

## Evidence and reproduction

- Private root: `~/.cache/contract-signals/document-review/`. Do not commit or serve PDFs/scans/text containing personal identifiers, signatures or contacts.
- BOAMP used **eight requests**: four initial 404s, source-page template HTML and three successful PDFs. Template inspection and retained `source_schema=3.2.5` identified `/telechargements/FILES/PDF/{year}/{month}/{idweb}.pdf`. Bounds: 15 seconds, 5 MiB, at least two seconds between requests, stop on refusal/rate-limit/server failure. DNCP's one exact request returned HTTP 200, **1,692,537 bytes**; empty text extraction required private image inspection.
- Match notice UUID/version and procedure UUID to eForms, then exact lot and `CON-*` → `ContractReference` to the printed reference. Other notice amounts do not corroborate the selected row. The three inspected result amounts/dates did not disagree; tax and underlying contract truth remain unresolved.

```sh
~/.cache/contract-signals/venv/bin/python tools/review-boamp-documents.py
python -m unittest discover -s tests -p 'test_review_boamp_documents.py'
```

The offline helper checks acquired-PDF and frozen-snapshot hashes and extracts exact lot-result sections. It needs private-environment `pypdf`; image extraction used Pillow. Six synthetic tests passed; the historical full suite passed **291 Python tests**, all JavaScript suites and the browser test. Private `paraguay-document-result.json` records visual interpretation; text extraction cannot reproduce the handwriting.

## Follow-up and remaining gates

`decp-dijon-conflict-review.md` later found that BOAMP **24-79759** uses `2023VDAO1642` as a procedure ID, with distinct lot contracts corresponding to all six amounts. Three candidate lot pairings disagree on offer counts. The grouped row stays excluded; holder/tax comparability remains unresolved. The lone national amount is not preferred.

- Obtain a separate qualified review of the signature-date candidate and scanned identity.
- Fetch the frozen zero-score BOAMP document in a separately bounded follow-up.
- Establish authoritative buyer-profile contract/lot/version evidence for the DECP conflict.
- Complete legal verification and schema/basis review before integrating evidence or changing scores.
