# Ukraine public-only accuracy audit — 11 October 2026

## Result

Review of the existing **488-contract cohort**. Source records, website inputs, weights and scores are unchanged. This is not independent expert validation.

- All 488 cached tender/contract/award/buyer/lot mappings and normalized amount/currency sources verified.
- **7 of 11 amount differences** have explicit contract `amountNet` equal to the VAT-excluded award amount in the same currency. All 11 fresh tender responses retain cached financial fields. **4 amount differences and 14 VAT-only differences remain unexplained.** No amount replacements are justified; matching tuples in the other 463 rows do not prove accuracy.
- All **12 sampled module links and stored counts agree**: six nonempty arrays contain **10 active changes** with unique IDs and dated signatures; six omitted arrays mean zero under the publisher's serializer ([correction log](ukraine-corrections-log.md)). This does not re-verify all 469 stored zeros; preserve snapshot/module provenance.
- The sole three-amendment case has one quality-improvement and two fiscal-year-extension categories. Their legal and monetary basis remains unknown.
- Current Vinnytsia discovery reports **506 entries**, 20/page; pages 25/26/27 contain **20/6/0**. No current 500 cap was observed. Historical completeness and portal date-filter semantics remain unknown; intermediate pages were not queried.
- The first attachment returned **HTTP 302**, not followed; the second was not attempted. Contents, authenticity and statutory/financial basis remain unknown.

`tools/prepare-ukraine-public-audit.py` reproduces `data/ukraine-public-audit-plan.json`: round-robin selection across procedure class, amendment-count band and existing-score strata, ranked by SHA256 within strata. **12 rows: 5 flagged, 7 zero-score**, covering reporting/competitive procedures and counts 0, 1–2 and 3+. Selection preceded fresh retrieval but followed snapshot inspection; it is neither blinded nor representative. Zero-score rows are not reviewed negatives. All 11 known amount differences form a separate diagnostic queue.

Frozen plan: `6e8d5583760933a7dff4a00e9419fcd0af3bb7577f63b78b078ca5b3ece9dcbf`; private read-only copy: `~/.cache/contract-signals/ukraine-public-audit/v1/plan.json` (0400). Attachment v2 kept v1's document order/URLs and corrected its host policy. **29/30 attempts** were used; the stopped attachment sequence is closed. Requests had 2 MiB caps and one-second start spacing; discovery used a 15-second socket timeout, later acquisitions a 15-second wall limit, with no redirects or retries. Private responses stay outside Git; minimized public hashes/pointers support local integrity, not remote authentication or reconstruction of full bodies.

## Reproduction and next steps

```sh
python tools/audit-ukraine-discovery.py
python tools/audit-ukraine-amendments.py
python tools/audit-ukraine-amount-bases.py
python tools/review-ukraine-amendment-documents.py
python tools/review-ukraine-amendment-documents.py --version 1
python tools/prepare-ukraine-public-audit.py
```

The first five commands need only repository evidence. Preparation requires private storage and an immutable freeze. Stale inputs fail closed; do not overwrite v1 or carry conclusions into rebuilt inputs without review.
See [correction log](ukraine-corrections-log.md), [amendment review](ukraine-amendment-review.md), [financial review](ukraine-amount-basis-review.md), [discovery review](ukraine-discovery-review.md), and [attachment history](ukraine-amendment-document-review.md).

- Attachment acquisition needs a separately reviewed redirect plan with host, bounds and privacy checks. Rationale categories alone cannot establish legality.
- Seek historical versions or explicit documents for the 4 amount and 14 VAT-only cases; do not substitute awards, infer ratios or convert currencies.
- Verify date-filter semantics and complete fixed-window discovery before expansion. Current 506 versus historical 500 may reflect time drift. All 16 buyer-association mismatches remain excluded.
- DASU/court follow-up needs exact tender/contract linkage, outcome scope and dated finality. Absent matches remain unknown; same-buyer comparisons and zero scores are not corruption-negative labels. Outcome cohorts stay separate from the source audit and website index.
Attribution: **Prozorro, Ministry of Economy of Ukraine / State enterprise Prozorro**. Reuse terms require attribution but name no standard API-data licence; attachment redistribution permission and privacy clearance are not established. No attachment contents are redistributed.
