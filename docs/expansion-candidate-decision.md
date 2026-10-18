# Ukraine / Romania second-dataset decision

## Decision

**Do not register either current candidate as a general explorer dataset yet.**
This is a scope/publication decision, not an importer-test failure. Existing
Ukraine Prozorro and Romania TED remain unchanged; no deployment is performed.

- **Ukraine:** prefer a systematically collected expansion of Prozorro, using
  frozen buyer/date discovery rules. The new research-cache extract is useful for
  research and local review, not an adequate general second collection.
- **Romania:** a separate national-source SEAP dataset is worthwhile in principle
  because it differs from TED's scope. This one-quarter candidate is not ready:
  identity/granularity, meaningful descriptive coverage and publication fields
  need review. Do not merge it into TED or describe it as 149 additional contracts.

The aggregate machine-readable findings are in
[`../data/expansion-candidate-audit.json`](../data/expansion-candidate-audit.json).
The audit uses existing frozen caches only; it makes **zero network requests**.
Hashes establish replay consistency, not independent authentication of source
truth, present-day status, completeness or legal correctness.

## Ukraine verification

- Replayed all 100 configured tenders from their official-response cache entries.
  The importer checks URL, HTTP metadata, original body hashes, retrieval times,
  tender/buyer identities and creation-date window.
- Both `contracts.json` and `coverage.json` replay **byte-for-byte**.
- 106 retained rows / 96 buyers; **91 buyers have exactly one retained row**.
- Zero intersections with the original pilot for normalized row ID, tender internal
  ID, contract internal ID and buyer ID. This confirms separation under these keys,
  not a representative or complete sample.
- Offers are unknown on 22 rows. Amendment enrichment is absent on all 106 rows;
  absence must not become zero amendments.
- Source retrievals are from 2026-10-04, not a fresh API refresh.
- Selection inherits the audit/label-research cache's bias. Hash ranking does not
  cure that bias. Do not infer country prevalence or complete buyer histories.

### Scoring integration test

Naively registering the raw `dataFamily: prozorro` array routes **all 106 rows**
through Ukrainian scoring (74 have a positive score under the current engine).
This is not evidence that those per-record signals are wrong; it demonstrates
that a raw registry entry is **not browse-only**, and incomplete-history context
must be explicitly handled before any scored integration.

Through the generic browse-only importer, all 106 rows load with **null scores
and no indicators**. This is suitable for local research review. A future optional
research collection would need prominent convenience-sample disclosure and
explicit routing, rather than inheriting pilot context unnoticed.

## Romania verification and new overlap evidence

- Rebuilt the selected records from the frozen, bounded normalized quarter input.
  Input hash, stored candidate hash/byte size and parsed rebuilt records match.
- 149 rows / three exact organizational buyer IDs. All 149 descriptions are
  explicitly generated because the export has no contract subject column.
- **114 rows carry a framework-agreement conclusion label.** Amounts and currency
  remain unadopted on every row; no spending totals or TED scoring are introduced.
- Dates range from **2020-12-31 to 2025-03-27**; **99 rows are outside Q1 2025**.
  Q1 names the source export, not a contract-date window.
- Winner IDs are absent. Supplier legal form is unknown on all 149 rows. Dataset
  CC BY 4.0 evidence exists, but it is not content/privacy clearance.

### Bounded TED comparison

Parsed **162 cached XML notices**, 5,694,112 decoded bytes, covering the existing
321 retained TED Romania rows. Recovered native `ContractReference/ID` values
from `NoticeResult/SettledContract`, rather than comparing SEAP contract numbers
with TED's local `CON-*` identifiers.

The comparison uses:

1. exact buyer ID;
2. native contract reference, normalizing whitespace/case only;
3. exact contract date.

Punctuation, prefixes and leading zeros are retained. Nested local contract
references are not treated as native contract numbers.

Result: **26 shared buyer/reference/date keys**, touching **38 SEAP rows and
35 TED rows**. SEAP also has **11 repeated buyer/reference/date keys** internally.
These are **candidate links**, not adjudicated duplicate contracts: lots,
suppliers, framework/call-off relationships and repeated declarations still
need checking. Non-matching rows are not proven additional contracts. The audit
keeps `confirmedContractLinks: null`, not zero.

All 149 private records pass the actual generic browse/import engine path with
null scores and no indicators. Source links survive. No adopted amount/currency
or winner IDs enter the retained candidate. This establishes technical loading,
not public-release readiness.

## What would change the decision?

### Ukraine

1. Announce a buyer/time expansion before retrieving indicator results.
2. Validate discovery pagination, date semantics and buyer association exclusions.
3. Record all discovered tenders and exclusions, not just convenient cached ones.
4. Preserve unknowns; validate amendment and complete-history contexts separately.
5. Choose a versioned expansion of the existing source or a genuinely distinct
   cohort with a clear user-facing reason for remaining separate.

### Romania

1. Adjudicate the 26 shared candidate keys by lot/supplier/native references and
   inspect repeated SEAP keys; preserve ambiguous cases.
2. Review a bounded sample against the original quarter export, not solely the
   normalized derivative, including the ambiguous publication-date headers.
3. Define framework versus call-off versus contract units. Do not infer amounts
   or adopt totals simply because the source has a numeric value.
4. Review supplier/free-text publication and export treatment, preserving unknown
   legal form instead of inventing organizational status.
5. Publish only a reviewed, attributed browse-only snapshot with its exact scope
   and overlap warnings; keep the TED collection intact.

## Reproduction and tests

```sh
python tools/audit-expansion-candidates.py --output data/expansion-candidate-audit.json
python -m unittest tests.test_audit_expansion_candidates \
  tests.test_import_romania_seap tests.test_import_prozorro_expansion \
  tests.test_import_national.ProzorroTests
node tests/candidate-readiness.cjs --private-seap
node tests/import-engine.cjs
```

**Passed:** 23 targeted Python tests, actual-candidate JS readiness checks and
existing generic-import engine checks. Synthetic matching tests cover native
versus local IDs, conservative normalization, duplicate keys, buyer/date/reference
mismatches, conflicting native IDs and fail-closed missing XML. No national scan,
full suite, deployment, new download or independent legal clearance was done.
The full offline audit requires the pre-existing external source caches; the
synthetic tests do not establish live source availability.
