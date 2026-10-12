# Public-document agreement preparation (v1)

## Finding and current status

The frozen `data/boamp-decp-links.json` preparation has **9 candidate pairs**, all blocked from factual agreement review: **4** have multiple-match warnings and **4** different-CPV warnings, possibly overlapping. These are investigation leads, not verified contracts or a representative accuracy sample. Identifier review is in `research/public-boamp-decp-investigation.md`.

The confirmed, uniquely linked agreement queue is empty: **denominator 0**, with no agreement percentage. The helper prepares queues; it reads no documents and assesses no agreement.

This historical snapshot predates `data/public-link-resolutions.json`: **seven active candidates / two dismissed leads**, still no confirmed DECP link. Preserve the freeze for audit without reintroducing dismissed leads. A future study needs a new snapshot incorporating decisions, frozen before reading agreement outcomes; this preparation is not retrospective preregistration.

## Reproduce and freeze

```sh
python -m unittest discover -s tests -p 'test_prepare_public_document_benchmark.py'
python tools/prepare-public-document-benchmark.py
# Optional private destination outside the repository
python tools/prepare-public-document-benchmark.py --plan /private/0700-directory/plan.json
```

Offline inputs: `data/boamp-decp-links.json`, `data/contracts.json`, `data/decp-history.json`, `data/decp-cities.json`. The helper freezes current bytes without claiming upstream hashes still match; it does not rebuild links or inspect raw notices.

Default: `~/.cache/contract-signals/public-document-benchmark/v1/plan.json`. Parent permissions must be 0700 or stricter; a new plan is exclusively created at 0400. Repository/symlink destinations are rejected. Identical reruns leave it intact; changed/invalid freezes fail. Use a new private path for another snapshot.

The plan binds input/helper/pair/row hashes, seed, eligibility and queues; local hashes/permissions are not external timestamps or owner-proof protection. All pairs remain queued as `blocked` with reasons or `eligible-not-reviewed`. Ordering is ascending SHA-256 of compact sorted-key UTF-8 JSON `[version, seed, boampId, decpId]`, then pair IDs. No quotas, replacements or readability selection; no names, amounts, prose, raw records, time or machine paths in the payload.

## Admission gate

1. Require `confirmed` status with basis `buyer-published-contract-reference` or `buyer-exact-notice-lot`.
2. Reject multiple-match/unconfirmed-reference warnings and repeated endpoints, even if warnings were omitted.
3. Require unique public row identities, matching buyer SIRETs and a DECP contract ID.
4. Revalidate the BOAMP published reference against DECP's ID, or the exact notice-root **and** lot pair. Local `CON-0001` and standalone `LOT-0001` do not suffice. Block raw-only confirmation that public rows cannot revalidate.

Different CPV stays a warning. Passing the gate queues review, not an agreement outcome.

## Subsequent review

- Investigate blocked pairs separately, retaining alternatives and exact notice/lot/version evidence. Promotion requires a reviewed public link artifact and a new freeze.
- Keep separate pair/row/plan-bound review records: official URL, access outcome, checksum/version, correction history, exact identifiers and page/field locators. Compare to the frozen version. Retain unavailable, ambiguous and nonmatching outcomes without replacements.
- Classify each factual field as `corroborated`, `contradicted`, `unresolved`, `unavailable` or `nonmatching`. Dates need event semantics; CPV needs lot/version scope. **Monetary fields remain unassessed:** no amount agreement, discrepancy, correction or inferred valuation.
- Field denominators include only eligible, uniquely matched evidence with a resolved comparable field; report exclusions and coverage separately. Official sources may share upstream errors.
- Seek a separate reviewer blinded to scores where feasible. Assistant preparation is not independent human validation. Use public sources and minimized evidence, URLs and locators; keep unnecessary personal fields off the website. This purposive cohort cannot establish population accuracy, wrongdoing or legal notice/threshold duties.
