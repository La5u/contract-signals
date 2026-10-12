# Ukraine random-sample field accuracy check — 12 October 2026

## Result

**No errors found.** Every published field of the Prozorro cohort matches the official record it came from, and the official records have not changed since import.

| Check | Scope | Mismatches |
| --- | --- | --- |
| Published row vs cached official tender record | **All 488 rows × 20 fields** (9,760 comparisons) | 0 |
| Cached record vs fresh live tender record | Random sample, 40 rows × 20 fields (800) | 0 (none of the 40 tenders modified since the snapshot) |
| Published row vs separate contracting-module record | 40 rows: identity, amount + currency, supplier, active amendment count (160) | 0 |

Fields: tender/procedure/contract/award/lot identifiers, lot count, buyer name and code, supplier name and (masked) identifier, signature date, amount, currency, procedure type, category, CPV, description, offers, complaint count, tender creation date.

## Method

- `python tools/check-ukraine-random-sample.py --plan` froze a simple random sample before any request: row ids ranked by `sha256("ukraine-random-sample-2026-10-12:" + id)`, first 40 (`data/ukraine-random-sample-plan.json`, bound to the `data/prozorro.json` hash). Composition follows the cohort: 37 reporting, 2 above-threshold, 1 price quotation; 16/16/8 across the three buyers.
- `--fetch` made **80 GETs** (40 tender + 40 contracting-module), one second apart, no retries; all HTTP 200. Full responses stay in `~/.cache/contract-signals/ukraine-random-sample/v1/` (0700), not in Git.
- Default mode writes `data/ukraine-random-sample-results.json`: per-row, per-field match flags plus response hashes; values are recorded only for mismatches (none).
- Expected values are re-derived from the Prozorro record by the checker, not by calling the importer. It is not fully independent: it follows the same documented field definitions, so it catches processing, mapping and staleness errors, not a wrong definition. A deliberate corruption of each of the 20 fields is detected (regression test).
- `tests/test_check_ukraine_random_sample.py` re-runs the full 488-row comparison offline on every test run.

## Limits

- This verifies that the explorer faithfully reproduces Prozorro. It does not verify Prozorro against signed paper contracts, payments or reality.
- Only 3 sampled rows are competitive, so offer counts are tested lightly by the live sample (the offline check covers all 64 competitive rows). One sampled contract has an amendment; the rest have none.
- Earlier amount-basis findings still stand: 4 contract/award amount differences and 14 VAT-flag differences are faithful copies of what Prozorro publishes, with the basis unexplained ([audit](ukraine-public-audit.md)).
