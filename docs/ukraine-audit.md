# Prozorro cohort audit (bounded, no score changes)

Reproduce the read-only snapshot audit and its tests:

```sh
python tools/audit-prozorro.py
python -m unittest tests/test_audit_prozorro.py
```

`--live` makes at most seven GET requests to the official public API (four-second timeout each), for seven unique deterministic sample tenders. `--write path.json` saves the report. The recorded run is `data/prozorro-audit.json`; it records each request's timestamp, API/portal URLs, checked fields, and per-field match or unavailability. No discovery, attachment retrieval, cohort downloads, or score/index changes occur.

## Snapshot findings

The audit checked the manifest, all 542 raw tender files, the extract, coverage counts, and importer rules. The three recorded search totals (689, 500, 869) match their listing counts. There are 542 unique manifest IDs and corresponding unique, parseable raw records; no missing/unlisted records, cross-buyer duplicate IDs, or filename/ID inconsistencies.

Of the 542 records, 16 are outside the official buyer attribution for the buyer whose search listed them. These are excluded before subsequent buyer-matched checks; coverage records 16 such cases. The remaining **526** are within the date window and buyer-matched, and their procedure counts agree with coverage. Tender-ID date versus record `dateCreated` was compared only on those 526 buyer-matched records (no mismatches); it was **not checked for the 16 buyer-mismatched records**. The cohort has 488 retained contract/award/supplier joins and eight excluded contracts (3 cancelled, 5 pending), matching coverage and the 488 extract rows. No duplicate join keys, unmatched contract awards, output-row mismatches, or offer-count differences were found. Recomputed competitive offer counts cover 64 rows; none are unknown in the snapshot.

The recorded live sample ran on **2026-09-28**: all seven requests returned HTTP 200 and tender identity, buyer, selected contract/award IDs, and supplier IDs matched. Offer counts matched on five records; the two reporting records had unavailable offer counts (no count assessed), not mismatches. All sampled records reported status `complete`. Individual timestamps and URLs are in the JSON report. This sample does not establish full-record equality at download time, bid/signature or legal validity, or search completeness.

## Limitations

This is a contract-oriented snapshot of three buyers, not a tender census or nationally representative sample. Tenders without contracts do not produce rows; only active awards with one supplier and signed/terminated contracts are retained. Search pagination was not independently re-queried; the recorded Vinnytsia search total is 500. Published bids can omit unfinished-stage bids. Contract changes and supplier identity beyond the published identifier are not validated. The 16 search-association mismatches remain excluded under the official buyer-field rule and should be resolved or documented before any expansion. No additional cohort downloads were made.

## Next: expand Ukraine

Expansion is agreed, but the buyer list is not yet fixed. First test discovery pagination, especially the 500-result Vinnytsia listing, and retain page counts/IDs so truncation is detectable. Then publish the additional buyer identifiers and a fixed date window before fetching their tender records. Select by administrative level and manageable volume, not by scores. Keep the current snapshot separate, use the official buyer-field inclusion rule, and record no-contract tenders and all exclusions. Re-run this audit plus a flagged/unflagged live sample before publishing the new cohort.
