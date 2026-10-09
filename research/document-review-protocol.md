# Small document-review freeze (v1)

## Purpose and boundary

This is the next accuracy **preparation** step: a deterministic reading queue from
actual published application datasets. It is not completed document verification,
a corruption label set, or an estimate of precision/recall. The preparation script
reads local published JSON and `script.js` only. It neither fetches URLs nor edits,
reimports, enriches, or corrects published data.

Run:

```sh
python tools/prepare-document-review.py
python -m unittest discover -s tests -p 'test_prepare_document_review.py'
```

The default output is private:
`~/.cache/contract-signals/document-review/plan.json`. Do not commit it or acquired
documents. The destination directory is mode 0700 and a newly created plan is
0400. The script creates the file exclusively; an identical rerun leaves it
untouched. A different or hash-invalid existing freeze causes an error, not an
overwrite. An explicitly different `--plan` path is required for another freeze.
File permissions and SHA-256 provide local protection/tamper detection, not an
external timestamp, signature, or protection against the file owner replacing it.

## Selection fixed before reading

Exactly these strata, in this order, at most one row each:

| Stratum | Fixed candidate scope (application dataset keys) | Eligibility |
| --- | --- | --- |
| scored-flagged-positive | `boamp` (`contracts.json`) | Published amount > 0 and actual app score > 0 |
| scored-zero-positive | `boamp` | Published amount > 0, actual score = 0, not excluded |
| declared-zero | `boamp`, `colombia` | Numeric published amount = 0 and published official verification URL |
| missing-amount | `boamp`, `uk` | Missing/null amount, BOAMP or Find a Tender family (not numeric zero) |
| initial-conflict | `cities` | Nonempty published `initialConflicts` |
| published-contractSigned | `paraguay`, `paraguay3` | Published `signedDocumentUrls` entry on the DNCP official host |

Within each scope choose the lexicographically smallest **(dataset key, exact row
ID)**, using ordinary string ordering, not locale ordering or numeric ID parsing.
Skip already selected exact dataset/row identities. Empty strata are recorded,
not filled from another scope. This deliberately gives BOAMP and the first
Paraguay cohort precedence over later dataset keys. There is no severity ranking,
manual cherry-picking, document-readability selection, or replacement after
opening documents. A document that is unavailable or fails matching remains a
review result for the frozen row. This small purposive sample is not representative.

The six candidate datasets are prepared **independently and in full** through
`prepareContracts` in a Node `vm`, as the app does when loading individual datasets
(and before combining them). Selection happens afterwards. The script calls the
actual `getVigilanceScore` and `getAssessment` from `script.js`; it does not
reimplement thresholds or prepare only the selected rows. Thus supplier context
and buyer publication baselines stay in their original cohorts. Score null means
unevaluated/excluded, not zero. A zero score can coexist with a missing amount if
other checks are evaluated; a declared zero is not proof of a free contract.

## Freeze contents and privacy

The canonical hash is SHA-256 of UTF-8, sorted-key, compact JSON with
`planSha256` removed. It covers the fixed protocol/scopes, all six published-file
byte hashes, script/helper hashes, score version, exact selections, minimized
matching IDs, published values, verification URLs and assessment states. There
is no wall-clock timestamp or machine-specific path in the hashed payload.
Whitespace changes in source snapshots still produce a new source hash.

Only allowlisted notice/lot/contract/folder/process/procedure/award/OCID and buyer
identifiers are retained, together with dataset and row IDs. BOAMP lot and contract
IDs are local to the notice: never match `LOT-0001` or `CON-0001` alone, and never
assume they equal DECP identifiers. DECP requires exact buyer SIRET + contract ID;
DNCP requires OCID + contract ID + linked award ID. SECOP requires exact contract
and process IDs (the generic API URL alone is not an exact match).

The plan retains published amount, currency, amount basis, date/date note and
selected published chronology fields; absent currency remains null, not an
invented EUR assumption. It includes initial-conflict **field names**, not raw
alternative records, and assessment counts/check IDs/states, not free-text
assessment explanations. No supplier names or identifiers, buyer names,
descriptions, source-reference prose, raw records, document filenames, supplier
profiles or source histories are copied. URLs come only from published schema
fields and are restricted to official source hosts. No guessed document URLs,
search-generated matches, third-party links or newly fetched evidence are added.
The Paraguay importer publishes `signedDocumentUrls` from OCDS `contractSigned`
documents; the presence of that metadata does not verify the file or signatures.

## Subsequent document verification criteria

For each frozen row, keep a separate private review record. Record access outcome,
document checksum/version, exact matching evidence and page/section references.
Do not modify the freeze to record outcomes. Do not publish personal information
from documents. A review must establish all of the following before declaring a
field corroborated:

1. **Identity and version:** match the full composite identifiers, buyer and lot,
   including notice root/version, correction history, contract/award linkage and
   annex scope. Similar titles, suppliers or amounts do not establish a match.
   Record both the snapshot version and the version available at review time.
   A later corrected notice is not silently substituted for the frozen version.
2. **Amount basis and currency:** distinguish contract value, winning tender
   payable amount, award value, framework ceiling, lot value, estimated budget,
   unit price, amendment/new total and actual payments. Do not sum versions,
   amendments or currencies; do not replace a contract amount with an award or
   procedure-wide amount. Check decimals, thousands separators and units. A
   missing/zero amount may reflect an omitted field, genuine zero/free-use
   arrangement or a source problem; do not infer which without exact evidence.
3. **Tax:** explicitly establish HT/excluding tax versus TTC/including tax,
   applicable tax rate and whether the compared figures have the same basis.
   Do not assume that an eForms payable field or an unspecified currency implies
   the same tax treatment. If tax/basis is unresolved, classify comparability as
   unresolved rather than manufacture a discrepancy or correction.
4. **Date and chronology:** distinguish signature/conclusion, notification,
   award, period start, publication, correction and amendment dates. Paraguay's
   displayed period start is not signature proof; inspect the signed document
   instead. Preserve stated date notes and timezone ambiguities. Check ordering
   against the matched version; unexpected ordering prompts investigation, not
   an automatic finding. Missing chronology stays unknown.
5. **Conflicts and outcomes:** for the DECP city conflict, retain all incompatible
   initial values as unresolved unless a uniquely matched authoritative version
   establishes precedence. Do not pick the highest/lowest amount or score a
   conflicting row. Classify outcomes as corroborated, contradicted,
   ambiguous/unresolved, unavailable, or nonmatching, separately for each field.
   Failure to access a document is not corroboration and not an adverse finding.

A `contractSigned` document requires checking the actual contract, parties,
lot/award scope, signature pages, dates and monetary clauses. Metadata category,
filename or download URL alone cannot establish signing, authenticity or payment.
Document corroboration of imported fields also does not establish that the
heuristic score identifies wrongdoing. Any score change needs a separate,
versioned investigation and must never feed back into this sample selection.

## Independence limits

Assistant preparation and assistant-assisted reading are **not independent human
review**. The same assistant/toolchain can repeat importer assumptions, miss
source defects, or misread language and legal context. Official documents may
share the very source errors under review. Keep access/matching evidence and
uncertainty explicit, and require a separate qualified reviewer blinded to scores
where feasible before claiming independent validation. No document inspection
has been performed by this preparation step. Six rows cannot support country
comparisons, calibrated probabilities, population accuracy or corruption claims.
