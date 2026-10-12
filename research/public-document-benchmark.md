# Public-document agreement preparation (v1)

## Boundary and current finding

The current `data/boamp-decp-links.json` contains **9 candidate pairs**, not nine
verified contracts: all nine are blocked from factual agreement review. Four
pairs have multiple-match warnings; four have different-CPV warnings (overlap is
possible). Buyer/holder/date similarity is investigation evidence, not identity.
These pairs form a **candidate linkage investigation cohort**, not a representative
sample or measured accuracy result. The helper does not inspect documents or assess field agreement. Public identifier investigation has been performed separately in `research/public-boamp-decp-investigation.md`.

A separate **notice-linked agreement benchmark** may contain only confirmed,
uniquely linked pairs with exact identifiers revalidated in public rows. Its
current queue is empty; the factual agreement denominator is **0**, not nine.
Neither an empty queue nor blocked links supports an agreement percentage.

## Review-disposition follow-up

This immutable nine-pair preparation snapshot predates applied lead dismissals. `data/public-link-resolutions.json` now records **seven active candidates / two dismissed investigation leads**, with no confirmed DECP link. Keep this plan unchanged for audit; it is not the current active queue and must not reintroduce the two dismissed leads. Any future nonempty agreement preparation needs a new protocol/snapshot incorporating reviewed dispositions. The present agreement denominator remains zero.

## Reproduce and freeze the preparation snapshot

This preparation snapshot follows the existing candidate investigation: it is **not retrospective preregistration of those observed identifier findings**. A future nonempty agreement study must freeze its selection and protocol before reviewing agreement outcomes.

```sh
python -m unittest discover -s tests -p 'test_prepare_public_document_benchmark.py'
python tools/prepare-public-document-benchmark.py
# Optional: another private destination outside the repository
python tools/prepare-public-document-benchmark.py --plan /private/0700-directory/plan.json
```

Preparation is bounded and offline, reading only these public inputs:

- `data/boamp-decp-links.json`
- `data/contracts.json`
- `data/decp-history.json`
- `data/decp-cities.json`

No private cache, raw-document acquisition, network access, application scoring,
legal threshold rules or amount comparison is required. The private output is
not an input dependency. Link-artifact upstream hashes describe its creation;
the helper freezes **current input bytes**, without asserting that historical
upstream hashes still match. It does not rebuild links or inspect raw notices.

The default freeze is
`~/.cache/contract-signals/public-document-benchmark/v1/plan.json`.
The parent must be private (0700 or stricter); a new file is created exclusively
at 0400. Repository destinations and symlinked paths are rejected. Identical
reruns do not rewrite it; changed or invalid freezes fail. Use a new private path
for a new snapshot. SHA-256 and permissions are local tamper checks, not an
external timestamp, signature or protection from the owner replacing files.

The plan binds all four source byte hashes, helper hash, canonical pair/row
hashes, seed, eligibility and queues. Every pair is retained with explicit
`blocked` reasons or `eligible-not-reviewed` status. Ordering is ascending
SHA-256 of compact sorted-key UTF-8 JSON `[version, seed, boampId, decpId]`, then
exact pair IDs. All pairs are queued: no quota, replacement or readability-based
selection. No time or absolute machine path enters the hashed payload. IDs,
hashes and gate metadata are retained, not names, prose, amounts or raw records.

## Admission gate (fail closed)

1. Link status must be `confirmed`, with an exact basis:
   `buyer-published-contract-reference` or `buyer-exact-notice-lot`.
2. No `multiple-*` warning or unconfirmed-reference warning is allowed. The
   helper also detects repeated endpoints even if warnings are omitted.
3. Both public row identities must exist uniquely across their respective
   datasets. Buyer SIRETs must match exactly and a DECP contract ID must exist.
4. Revalidate either the BOAMP published contract reference against DECP's
   contract ID, or the exact notice-root **and** lot pair against DECP. A local
   `CON-0001` is not a published contract reference; `LOT-0001` alone is not a
   cross-notice identity. Raw-only confirmation is deliberately blocked if it
   cannot be revalidated from these public rows.

Different CPV remains a review warning, not proof of nonidentity or disagreement.
Gate success queues review only; it never creates an agreement outcome.

## Subsequent review protocol (not executed by this helper)

- Investigate blocked pairs separately. Preserve all alternatives; do not pick a
  convenient match. Record exact identifier evidence and notice/lot/version
  locators. Any promotion requires a separately reviewed public link artifact
  and a new freeze, never a private-cache override or editing this freeze.
- For eligible pairs, use separate review records bound to pair, row and plan
  hashes. Record official URL, access outcome, document checksum/version,
  correction history, exact buyer/contract/notice/lot matching evidence and
  page/field locators. Compare against the frozen version, not silently against
  a later correction. Unavailable, ambiguous and nonmatching documents remain
  explicit outcomes; never replace those pairs.
- Assess factual fields separately: `corroborated`, `contradicted`, `unresolved`,
  `unavailable` or `nonmatching`. Dates require event semantics; CPV requires
  lot/version scope. Monetary fields remain **unassessed** in this protocol:
  no numerical amount agreement, discrepancy, correction or inferred valuation.
- A future field-specific denominator may include only eligible pairs with
  uniquely matched evidence and a resolved, comparable field. Report exclusions
  and coverage separately; unconfirmed links never enter it. This preparation
  computes no such results. Official sources may share upstream errors, so
  document agreement is not independent ground truth.
- Seek a separate reviewer blinded to scores where feasible. Assistant-assisted
  preparation is not independent human validation. Use publicly accessible sources,
  keep unnecessary raw personal fields out of the website, and publish minimized
  evidence, source URLs, hashes, field locators and limitations. This purposive cohort cannot establish
  population accuracy, wrongdoing, legal notice obligations or threshold duties.
