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

## Accuracy follow-up — 11 October 2026

The owner subsequently prioritized accuracy of the existing cohort before expansion. The earlier findings/limitations above describe the original snapshot audit, not the following additional review.

A [public-only audit](../research/ukraine-public-audit.md) freezes twelve contracts (five flagged/seven zero-score) and the eleven known amount-difference tenders. **29 requests total:** five discovery, twelve module, eleven tender and one attachment. The first 28 returned HTTP 200; the attachment returned 302 and was not followed. No cohort, source field or score was changed.

- All 488 cached exact mappings and financial provenance checked. Seven amount differences have explicit matching contract-net/award-excluding-VAT evidence; four amount differences and fourteen VAT-only differences remain unresolved. Fresh tender financial fields match the cached snapshot.
- Twelve module identities verified. Six nonempty arrays corroborate ten active changes, including the sole three-change threshold case. Six omitted `changes` fields mean **zero changes**: Prozorro's API serializer drops empty lists and creates `changes` only on the first posted change ([source check](../research/ukraine-corrections-log.md)).
- Current Vinnytsia search total 506, boundary pages 25/26/27 return 20/6/0. No current 500 cap observed, but historical completeness remains unknown. The portal date-filter probe returned six results, not the historical creation-window 134; its semantics are not certified.
- No attachment body was inspected. Amendment rationale categories do not certify legality or financial effect. All 16 buyer-association mismatches remain excluded.

Offline replay (no private cache/freeze or network):

```sh
python tools/audit-ukraine-discovery.py
python tools/audit-ukraine-amendments.py
python tools/audit-ukraine-amount-bases.py
python tools/review-ukraine-amendment-documents.py
```

[Correction history](../research/ukraine-corrections-log.md) records the unsupported omitted-list-as-zero interpretation, overbroad financial-basis wording, and corrected overly narrow document-host policy. Source rights, privacy, raw-body/hash limits, exact selection and acquisition accounting are in the overall review.

## Gates before any future expansion

Omitted-list semantics are now verified (omission = no changes). Verify document redirect policy and discovery date/pagination completeness first. Only then publish any additional buyer identifiers and a fixed date window before fetching their tender records. Select by administrative level and manageable volume, not by scores. Keep the current snapshot separate, use the official buyer-field inclusion rule, and record no-contract tenders and all exclusions. No expansion was performed or authorized by this accuracy follow-up.
