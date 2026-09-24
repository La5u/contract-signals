# Opening your own file

**Open your own JSON file** (under the filters) reads a file in your browser. Nothing is uploaded; the page makes no network request for it, and closing the tab discards it. Filters, sorting, CSV/JSON export and the page summary work as with the built-in datasets.

The file must be a JSON array of records. It is validated before anything is shown; the first invalid record stops the load with its `id` and the reason.

## Minimal record

```json
[
  {
    "id": "my-city-2025-001",
    "buyer": "Commune de Exemple",
    "description": "Entretien des espaces verts",
    "dataStatus": "verified",
    "source": "https://example.org/notice/2025-001",
    "supplier": "ACME Paysage",
    "date": "2025-03-14",
    "amount": 48000,
    "currency": "EUR",
    "procedure": "Procédure adaptée",
    "directAward": false,
    "offers": 1,
    "durationMonths": 24,
    "cpv": "77310000-6"
  }
]
```

| Field | Required | Type | Notes |
| --- | --- | --- | --- |
| `id` | yes | text, unique | Stable identifier; it is searchable and appears in exports and shared links. |
| `buyer`, `description` | yes | non-empty text | Keep the source wording and language. |
| `dataStatus` | yes | `verified` · `unverified` · `synthetic` | `unverified` rows are shown but excluded from calculations. |
| `source` | no | http(s) URL | Link to the published record. Strongly recommended. |
| `supplier`, `procedure`, `cpv`, `contractId`, `buyerSiret` | no | text | `cpv` as `12345678-9` gives the sector column; `buyerSiret` must be 14 digits. |
| `date` | no | `YYYY-MM-DD` or `null` | A real calendar date. |
| `amount`, `offers`, `durationMonths` | no | number ≥ 0 or `null` | `offers` must be an integer. `null` means unknown, never zero. |
| `currency` | no | ISO 4217 code | Defaults to EUR. Amounts are never converted between currencies. |
| `directAward` | no | `true` · `false` · `null` | `true` = declared without competition; `null` = unknown. |
| `supplierIds` | no | `[{ "id", "identifierType" }]` | `SIRET`/`SIREN` enable French identity grouping. |

Other fields accepted by the built-in datasets (histories, notice evidence, audit findings, projects) have stricter rules; see `validateContracts` in `script.js`.

## How your rows are scored

Rows without a recognised `dataFamily` go through the **French v3 checks** ([score-v3.md](score-v3.md)): award declared without competition, single offer in an explicitly competitive procedure, declared duration ≥ 10 years, and declared increase > 20 % (only with a published history and a firm price). These thresholds are editorial and designed for French data; they are **not validated for other jurisdictions**. The repetition and concentration checks run only on the two built-in DECP cohorts, so they stay “Not assessed” for your file.

Unknown values are never scored as zero. A record with no evaluable check shows **Not assessed**. A flag is a reason to read the source, not a finding.
