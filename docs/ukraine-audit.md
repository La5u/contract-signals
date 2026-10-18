# Prozorro cohort audit (bounded, no score changes)

A separate [bounded cached expansion](ukraine-expansion.md) now provides 100 explicitly frozen tenders outside the pilot buyers (106 retained contracts). It does not change this pilot or resolve its discovery/completeness limitations.

Reproduce with `python tools/audit-prozorro.py`; test with `python -m unittest tests/test_audit_prozorro.py`.

`--live` checks seven deterministic sample tenders through at most seven official API GETs (four-second timeout each); `--write path.json` saves the report. `data/prozorro-audit.json` records timestamps, API/portal URLs and field matches or unavailability.

## Snapshot findings

- Manifest and all 542 raw files checked; search totals 689, 500 and 869 match listings. IDs/files are unique and parseable, with no missing records, cross-buyer duplicates or filename/ID inconsistencies.
- Excluded 16 buyer-association mismatches. The remaining 526 match buyers/date window and coverage procedure counts; tender-ID dates match `dateCreated` on these 526 only.
- Retained 488 contract/award/supplier joins; excluded eight contracts (3 cancelled, 5 pending). No duplicate joins, unmatched awards, output mismatches or offer-count differences. Competitive offer counts are known for all 64 applicable rows.
- On **2026-09-28**, seven live responses returned HTTP 200 and matched tender, buyer, selected contract/award and supplier IDs; all had status `complete`. Five offer counts matched; two reporting records had no assessable count. This does not establish full-record equality at download, legal validity or search completeness.

## Accuracy follow-up — 11 October 2026

The [public-only audit](../research/ukraine-public-audit.md) froze twelve contracts (five flagged/seven zero-score) and eleven amount-difference tenders.

- All 488 cached mappings and financial provenance checked. Seven differences have explicit matching contract-net/award-excluding-VAT evidence; four amount cases and fourteen VAT-only cases remain unresolved. Fresh tender financial fields match the cache.
- Twelve module identities verified. Six nonempty arrays corroborate ten active changes, including the sole three-change flag; six omitted `changes` lists mean zero changes, confirmed from the API serializer ([source check](../research/ukraine-corrections-log.md)).
- Current Vinnytsia total is 506; pages 25/26/27 return 20/6/0. No current 500 cap observed; historical completeness remains unknown. The date-filter probe returned six results versus the historical creation-window 134; equivalence is unverified. No attachment body was inspected, and amendment categories do not establish legality or financial effect.

Offline replay:

```sh
python tools/audit-ukraine-discovery.py
python tools/audit-ukraine-amendments.py
python tools/audit-ukraine-amount-bases.py
python tools/review-ukraine-amendment-documents.py
```

[Correction history](../research/ukraine-corrections-log.md) covers omitted-list interpretation, financial-basis wording and document-host policy. This three-buyer contract snapshot is not a tender census: only active single-supplier awards and signed/terminated contracts produce rows. Historical pagination was not independently re-queried; bids may omit unfinished stages, and supplier identity beyond published IDs remains unvalidated. Resolve/document the 16 exclusions and verify document redirects and discovery dates/pagination before expansion. Then freeze buyer IDs/date window, select by administrative level and manageable volume, keep snapshots separate, apply official buyer attribution, and record no-contract tenders and exclusions.
