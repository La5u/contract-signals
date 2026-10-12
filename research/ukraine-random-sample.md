# Ukraine random-sample field accuracy check — 12 October 2026

**No errors found in the checked fields.** All **488 rows × 20 fields (9,760 comparisons)** match cached official tenders; **40 sampled rows × 20 fields (800)** match fresh tenders, none modified since import; **40 module checks × 4 groups (160)** match identity, amount/currency, supplier and active amendment count. All mismatches: **0**.

Fields: tender/procedure/contract/award/lot IDs, lot count, buyer name/code, supplier name/masked ID, signature date, amount, currency, procedure type, category, CPV, description, offers, complaints and tender creation date.

- `python tools/check-ukraine-random-sample.py --plan` froze the first 40 rows ranked by `sha256("ukraine-random-sample-2026-10-12:" + id)` before requests. `data/ukraine-random-sample-plan.json` binds `data/prozorro.json`; composition: **37 reporting, 2 above-threshold, 1 price quotation; 16/16/8 across buyers**.
- `--fetch`: **80 GETs** (40 tender + 40 module), one second apart, no retries, all HTTP 200. Private responses: `~/.cache/contract-signals/ukraine-random-sample/v1/` (0700).
- Default mode writes `data/ukraine-random-sample-results.json`: match flags and response hashes, values only for mismatches (none). `tests/test_check_ukraine_random_sample.py` checks all 488 rows offline and detects deliberate corruption of each of the 20 fields.
- The checker derives expected values without calling the importer but shares its documented definitions; it detects processing, mapping and staleness errors, not wrong definitions. It verifies copying from Prozorro, not signed contracts, payments or reality.
- Only **3** sampled rows are competitive (offline checks cover all **64**); only **1** sampled contract has an amendment. Offer and amendment checks have limited live coverage.
- **4 amount differences and 14 VAT-flag differences** remain unexplained faithful copies of published values ([audit](ukraine-public-audit.md)).
