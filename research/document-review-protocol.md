# Small document-review freeze (v1)

## Purpose and reproduction

This prepares a deterministic reading queue from published app datasets. It does not verify documents, estimate precision/recall or label corruption. The script reads local JSON and `script.js` without fetching or changing data.

```sh
python tools/prepare-document-review.py
python -m unittest discover -s tests -p 'test_prepare_document_review.py'
```

Private default: `~/.cache/contract-signals/document-review/plan.json`; do not commit the plan or documents. Directory 0700, new plan 0400, exclusive creation. Identical reruns leave it intact; different/hash-invalid freezes fail. Use another `--plan` path for a new freeze. Hashes and permissions give local tamper detection, not an external timestamp or protection against owner replacement.

## Selection fixed before reading

Select at most one row per stratum, in this order:

| Stratum | Dataset scope | Eligibility |
|---|---|---|
| scored-flagged-positive | `boamp` (`contracts.json`) | Published amount > 0, actual app score > 0 |
| scored-zero-positive | `boamp` | Amount > 0, score = 0, not excluded |
| declared-zero | `boamp`, `colombia` | Numeric amount = 0, published official verification URL |
| missing-amount | `boamp`, `uk` | Missing/null amount in BOAMP or Find a Tender, not numeric zero |
| initial-conflict | `cities` | Nonempty `initialConflicts` |
| published-contractSigned | `paraguay`, `paraguay3` | Published `signedDocumentUrls` entry on the official DNCP host |

Choose the lexicographically smallest **(dataset key, exact row ID)** by ordinary string ordering. Skip already selected identities; record empty strata without filling from another scope. BOAMP and the first Paraguay cohort therefore take precedence. No severity/readability selection or replacement after opening documents; access or matching failures remain outcomes. This sample is purposive, not representative.

Prepare all six datasets independently and in full through `prepareContracts` in a Node `vm` before selection. Call the app's `getVigilanceScore` and `getAssessment` from `script.js`, preserving supplier context and buyer baselines. Null score means excluded/unevaluated, not zero. A zero score may coexist with a missing amount; a declared zero does not establish a free contract.

## Freeze and matching data

The hash binds protocol/scopes, all six file bytes, script/helper, score version, selections, matching IDs, published values, URLs and assessment states; it excludes `planSha256`, time and machine paths.

- Retain allowlisted notice/lot/contract/folder/process/procedure/award/OCID/buyer IDs plus dataset/row IDs. BOAMP `LOT-0001`/`CON-0001` need the notice root and are not DECP IDs.
- DECP needs buyer SIRET + contract ID; DNCP needs OCID + contract ID + linked award; SECOP needs contract + process IDs, not its generic API URL.
- Retain published amount, currency, basis, date/note and selected chronology; absent currency stays null. Include conflict field names and assessment counts/check IDs/states, without raw alternatives or explanations.
- Exclude names, supplier IDs, descriptions, raw records, document filenames, profiles and histories. URLs must be published schema fields on official hosts; no guessed or search-derived links.
- Paraguay's `signedDocumentUrls` comes from OCDS `contractSigned` metadata; that category does not verify the file or signatures.

## Document verification criteria

Keep outcomes in separate private review records with access status, checksum/version, exact matching evidence and page/section locators. Preserve the freeze and keep personal information out of published evidence.

1. **Identity/version:** establish composite IDs, buyer, lot, root/version, correction history, contract/award links and annex scope. Titles, suppliers and amounts do not establish identity. Record frozen and reviewed versions; do not silently substitute a later correction.
2. **Amount/currency:** distinguish contract, winning-tender PayableAmount, award, framework ceiling, lot, budget, unit price, amendment/new total and payments. Check separators and units. Do not sum versions/amendments/currencies or substitute award/procedure amounts. Missing/zero may reflect omission, genuine zero/free use or source error; exact evidence must distinguish them.
3. **Tax:** establish HT/excluding versus TTC/including tax, applicable rate and comparable basis. Do not infer tax treatment from eForms fields or unspecified currency. Unresolved tax/basis means unresolved comparability.
4. **Date/chronology:** distinguish signature/conclusion, notification, award, period start, publication, correction and amendment. Paraguay's displayed period start is not signature proof. Preserve notes/timezone uncertainty; investigate unexpected ordering against the matched version. Missing chronology stays unknown.
5. **Conflicts/outcomes:** retain incompatible DECP initial values until a uniquely matched authoritative version establishes precedence. Do not pick the highest/lowest or score the conflict. Classify each field as corroborated, contradicted, ambiguous/unresolved, unavailable or nonmatching. Access failure is neither corroboration nor an adverse finding.

For `contractSigned`, inspect the actual contract, parties, lot/award scope, signature pages, dates and monetary clauses. Category, filename or URL cannot establish signing, authenticity or payment. Score changes require a separate versioned investigation and must not affect selection.

## Independence limits

Assistant preparation/reading is not independent human review. The toolchain can repeat importer assumptions or misread source/legal context; official documents can share source errors. Seek a separate qualified reviewer blinded to scores where feasible. Preparation itself inspects no documents, and six rows cannot support country comparisons, calibrated probabilities, population accuracy or corruption claims.
