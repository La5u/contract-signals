# Importing your own data

**Import a dataset** reads a file locally in your browser. It is never uploaded, and the import makes no request to an external service. The currently selected built-in dataset stays in place until you explicitly load the preview. Closing the tab discards the imported records; reviewer notes are separate and may be saved locally.

## Import workflow

1. Click **Import a dataset** next to search (or use **Advanced filters → Import a dataset**), then choose a JSON or CSV file (maximum **25 MiB**). Imports are limited to **20,000 normalized records**.
2. For CSV, review the detected headers and map columns where needed. Required fields are `id`, `buyer`, and `description`; the import offers explicit mapping for the common fields. Auto-detection recognises aliases, but verify it. CSV headers must be unique and no more than 1,000 columns.
3. Choose an import method. **Browse only · no scoring** is the default. **French v3 checks** is an explicit opt-in; it applies a French method to your selected rows and does not verify they are French or that the method is suitable.
4. Click **Preview import**. Validation, record count, format, warnings, and up to three sample rows appear. Nothing has been loaded yet.
5. Check the preview and warnings, then click **Load previewed records** to replace the current view with this local file. Changing the file, method or mapping invalidates the preview; preview again before loading.

The importer accepts simple JSON record arrays and the explorer's JSON export envelope (`records` array). It also accepts OCDS JSON when releases are actually present: an array of compiled/single releases, a release, package `releases`, or `records` entries containing `compiledRelease` or `releases`. OCDS is reduced to award rows (`ocid/awardId`); it does not establish that an award became a signed contract. Multiple releases for the same OCID are rejected rather than silently choosing a version. Incomplete record references that have only a URL are rejected; fetch and provide the compiled release first.

## Simple JSON records

```json
[
  {
    "id": "city-2025-001",
    "buyer": "Example municipality",
    "description": "Maintenance of public gardens",
    "dataStatus": "verified",
    "source": "https://example.org/notice/2025-001",
    "supplier": "Example Landscapes Ltd",
    "date": "2025-03-14",
    "amount": 48000,
    "currency": "EUR",
    "procedure": "Open procedure",
    "directAward": false,
    "offers": 1,
    "durationMonths": 24,
    "cpv": "77310000-6"
  }
]
```

| Field | Required | Type | Notes |
| --- | --- | --- | --- |
| `id` | yes | text | Stable identifier; required and searchable. |
| `buyer`, `description` | yes | non-empty text | Preserve source wording and language. |
| `dataStatus` | no | text | Missing status is set to `unverified` with a warning, and unverified rows are excluded from calculations. This default is not verification. |
| `source` | no | text | A supplied value is retained; no source URL is invented when absent. Use an http(s) source link where possible. |
| `supplier`, `procedure`, `cpv`, `buyerSiret`, `contractId` | no | text | Optional published details; `buyerSiret`, when supplied, must be 14 digits. |
| `date` | no | date text | A supplied date is retained; absent dates remain unknown. |
| `amount`, `offers`, `durationMonths` | no | number or `null` | Numeric values are checked; blank/missing values remain unknown, never zero. |
| `currency` | no | ISO 4217 code or `null` | No currency is inferred. Missing currency stays missing; amounts are **not assumed to be EUR or converted**. Unrecognized codes are discarded with a warning. |
| `directAward` | no | `true`, `false`, or `null` | `null`/missing means unknown. An OCDS method label alone does not set this flag. |
| `supplierIds` | no | array of identifier objects | Supplied identifiers are retained; do not add personal or sensitive identifiers without a clear lawful purpose. |

For CSV, the first row is a header. Comma and semicolon delimiters, quoted fields, doubled quotes, and multiline quoted cells are supported. Numeric values must use a plain decimal point (no thousands separators or locale decimal comma). Required columns can be explicitly mapped; other fields without a mapping or recognised header stay absent. Duplicate headers and rows missing required values are errors.

## What the import method means

- **Browse only (default):** imports are not scored. The table, search, filters and exports can be used to inspect the records; score-dependent results remain **Not assessed**. No jurisdiction is inferred.
- **French v3 (opt-in):** explicitly runs the French v3 checks. For generic imports, the method is still not validated for the source jurisdiction or dataset. Missing `dataStatus` becomes `unverified`, which excludes such records from calculations, so opting in does not override the unverified default. Do not set `verified` unless you have actually checked the source.

No cohort completeness, provenance, source licence, or independent verification is established by importing. Repetition and concentration checks depend on vetted built-in cohorts and are not enabled for generic imports.

## Local identity and notes

The review marks for an imported file are scoped to its SHA-256 fingerprint. The fingerprint includes the exact file text, selected method, and CSV column mapping; changing any of these creates a distinct notes scope. The fingerprint is a local identifier, not a signature or proof of provenance.

Review notes are working notes, not source publications or findings. Exported note files are **plaintext** and may contain sensitive information; do not put protected casework, personal data or confidential details in them. Notes never change the index.

Treat raw source files carefully: contact details, identity/document numbers, and bank/account fields can be personal or otherwise sensitive even when present in a public extract. Minimise them; do not publish or share them just because the importer accepts a JSON object. The repository's `python tools/audit-personal-data.py` reports heuristic field-presence indicators for repository datasets without printing values; it is not a validator or privacy clearance for an imported file. See [personal-data inventory](personal-data.md).

JSON exports from the explorer use an envelope with `tool`, `scoreVersion`, `dataset`, `view`, `exportedAt`, `caveat`, `count`, and `records`. You can import that envelope directly. The export may represent only the currently filtered records, not a complete source dataset.

A signal is a reason to inspect the publication, not an allegation. A zero or “Not assessed” result is not a clean bill of health. See [French v3 method](score-v3.md) and [data sources and licences](data-sources.md). BOAMP-published dataset content is supported as Licence Ouverte 2.0 by DILA's legal notice and official data.gouv.fr dataset records; null API catalogue fields do not leave that dataset licence unresolved. Scope for third-party attachments/content and related privacy questions remains open. The documented Annuaire dataset supports LO 2.0 for the project's limited supplier name/status/identifier enrichment, not every API field. See [retained source-rights evidence](source-rights-evidence.json) and [personal-data inventory](personal-data.md).
