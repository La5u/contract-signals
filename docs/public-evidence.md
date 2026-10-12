# Public BOAMP–DECP evidence ledger

This is a transparent evidence inventory, **not a linking rule, reconciliation, adjudication or dataset correction**. Nine investigated pairs cover six distinct notices and seven notice/lots. There are **zero confirmed links and zero resolved amounts**. The explorer displays these reviewed annotations alongside the base candidate links, with links to this protocol and the public ledger. Contract fields and scoring are unchanged; a missing, invalid or stale ledger must not suppress base candidate links.

## Applied resolutions and correction history

The original nine heuristic pairs remain archived. The current reviewed overlay has **seven active candidates and two dismissed investigation leads**, with **zero confirmed DECP links**. Three BOAMP↔TED notice versions are verified; two XML-version checks remain unresolved after HTTP 429.

The dismissed mappings were:

1. **Paris `2024S05079` ↔ BOAMP 25-21317 LOT-0001:** the corresponding long-reference pattern is explicitly attached to sibling **LOT-0003**, not LOT-0001. No automatic replacement link is confirmed.
2. **Nantes `2025F00012` ↔ BOAMP 25-34782 LOT-0003:** that technical lot is printed **Lot 2, LAVERIE**, while the DECP record says **CUISSON**, the other notice-local scope. The identifiers remain unbridged; this dismisses the lead, not proof of different legal contracts.

[Correction history and future safeguards](../research/link-corrections-log.md), [hash-bound decisions](../data/boamp-decp-link-decisions.json), and [current resolution overlay](../data/public-link-resolutions.json) preserve exactly what was incorrect, why it was dismissed, the expected source fields, and what remains unknown. The explorer separates dismissed audit links from active candidates and explicitly distinguishes TED notice verification from DECP contract confirmation.

```sh
python tools/review-link-resolutions.py
```

Run the raw link builder before this review-overlay builder after any dataset rebuild. Changed source or row hashes require fresh review; dismissals must not silently carry over. The original public benchmark plan remains an immutable pre-disposition nine-pair snapshot, not the current active queue. Its agreement denominator remains zero; future agreement preparation must account for the review overlay in a newly versioned plan.

## Reproduce without a private cache or network

From the repository root, using Python 3.9+ (3.10+ recommended):

```sh
python tools/build-public-link-evidence.py
python -m unittest discover -s tests -p test_build_public_link_evidence.py -v
```

The default build reads only repository inputs, verifies exact source hashes, and writes `data/public-link-evidence.json`. It does not import the private investigation summary, open a private cache, or run curl. To compare without overwriting the published artifact:

```sh
python tools/build-public-link-evidence.py --output /tmp/public-link-evidence.json
cmp data/public-link-evidence.json /tmp/public-link-evidence.json
```

No wall-clock build timestamp is inserted: the output is deterministic. No raw live response needs to be published for this reproduction.

`research/public-link-observations.json` contains the nine reviewed public annotations and the fixed request inventory. Its initial locators came from the private investigation summary, but **every published BOAMP reference was checked against the decoded repository raw notice and every DECP ID against its public normalized record**. Conclusions and concise notes are manual-reviewed assertions tied to exact input hashes, not automatic identifier equivalence. See [the investigation](../research/public-boamp-decp-investigation.md) for the substantive review.

| Pair | BOAMP normalized ID | DECP normalized ID | Reviewed conclusion |
| --- | --- | --- | --- |
| 1 | boamp-25-21317-lot-0001 | decp-21750001600019-2024S05075 | reference-pattern-supported-unconfirmed |
| 2 | boamp-25-21317-lot-0001 | decp-21750001600019-2024S05079 | disfavored-notice-lot-mapping-not-proven-different-legal-contract |
| 3 | boamp-25-21329-lot-0001 | decp-21750001600019-2025S01590 | reference-pattern-supported-unconfirmed |
| 4 | boamp-25-34782-lot-0003 | decp-21440109300015-2025F00012 | disfavored-notice-lot-mapping-not-proven-different-legal-contract |
| 5 | boamp-25-34782-lot-0003 | decp-21440109300015-2025F00013 | lot-compatible-unconfirmed |
| 6 | boamp-25-34782-lot-0006 | decp-21440109300015-2025F00016-1 | lot-compatible-unconfirmed |
| 7 | boamp-25-37616-lot-0001 | decp-21750001600019-2025F02650 | reference-pattern-supported-unconfirmed |
| 8 | boamp-25-45958-lot-0005 | decp-21750001600019-2025S02915 | reference-pattern-supported-unconfirmed |
| 9 | boamp-25-47556-lot-0001 | decp-21750001600019-2025F02648 | reference-pattern-supported-unconfirmed |

Five Paris pairs have repeated-year, terminal-four-zero or compound-reference patterns, not an authoritative crosswalk. Two Nantes pairs are lot-compatible without any identifier bridge. Two mappings are disfavored by explicit notice-local lot/reference structure; neither establishes a different DECP legal contract. `-1` on the Nantes row is our local suffix, not an official contract reference. No normalization strips prefixes or suffixes, repairs digits, aggregates reused identifiers, or resolves monetary conflicts.

## Provenance and interpretation

The ledger publishes exact BOAMP notice and Ministry-query URLs. The acquisition inventory also gives the exact Nantes export URLs and TED search URL and bodies. A prior TED notice citation `723965-2024` in pair 8 is a retained scalar reference; its public locator is <https://ted.europa.eu/en/notice/-/detail/723965-2024>. This citation was **not fetched** and is not evidence of the candidate DECP link.

* `sourceHashes`: SHA-256 of exact repository file bytes, including the **compressed** gzip bytes. The investigation note is also bound by hash.
* `annotationSha256`: sorted-key compact UTF-8 JSON hash of the public annotation object.
* `rawRecordSha256`: sorted-key compact UTF-8 JSON hash of the selected raw BOAMP record. This is a record fingerprint, not a claim to hash a byte slice of the gzip source.
* `decodedStringSha256`: SHA-256 of UTF-8 `donnees` string bytes **before** JSON decoding.
* `fields[].scalarSha256`: sorted-key compact UTF-8 JSON hash of the original scalar, including JSON quotation for strings. `ensure_ascii=false` is used consistently.
* JSON pointers are literal RFC 6901 pointers, with zero-based array indices. `normalized*Pointer` and `rawNoticePointer` use `file#pointer`. A decoded field pointer is into the JSON object obtained by decoding the selected raw record's `donnees`. A raw field pointer is relative to that record; a normalized field pointer is relative to its specified normalized record. Lot relationships are explicit fields, not inferred neighboring array positions.

Only selected reference, relationship, lot-number, amount, currency, CPV, duration and date scalars are extracted. No holder/company names, supplier profiles, contact details, signatures, entire contract objects or live response bodies are copied. Amount narrative fields publish **reviewed exact excerpts**, omitting administrative contact/address prose. Their hash still fingerprints the full original source scalar; `excerpt` identifies the transformation, and `value` is the excerpt. Arbitrary recursive field extraction is prohibited.

Snapshot retrieval, live acquisition, and publication times are deliberately separate:

* The retained BOAMP snapshot's `retrievedAt` comes directly from its `/retrievedAt` metadata, not the notice dates.
* The normalized snapshots have **no inferred retrieval time**. Hashes identify the inspected versions; file modification time is not a retrieval timestamp.
* `dateparution`/`publicationDate` are publication dates. Notice issuance, contract conclusion, award decision and DECP notification have distinct pointers and meanings even when dates coincide.
* The 14 historical request times, status, response length and SHA-256 are copied as reviewed metadata assertions from the dated private manifest. `liveRequests[].recordedFields` additionally publishes **104 privacy-minimized scalar extracts**: all reviewed Ministry result identifiers/amounts/dates/CPVs and the four relevant Nantes 2025 row pointers. Each has an exact source pointer and scalar hash, verified against the acquired response's body hash during review. Other Nantes rows, descriptions, supplier names and contacts are not copied; TED publishes only search-result counts/timeout metadata. These are historical source assertions: a hash alone does not authenticate the publisher, and a fresh public request need not reproduce the old response byte-for-byte. Their label is **“recorded live acquisition; not required for offline reproduction”**. All recorded statuses are 200. **The three historical TED requests used `checkQuerySyntax:true`: they validated syntax without executing a search.** Their metadata now explicitly records `searchExecuted:false` and `syntaxOnly:true`; empty results cannot be interpreted as TED absence. These are not a claim that this build fetched anything or that current responses are identical.

BOAMP tender payable amounts, framework maximums, normalized DECP declared amounts and narrative HT ceilings are not interchangeable. The ledger does not claim payment, guaranteed expenditure, exercised renewals, chronology/supersession, or a placeholder correction. Missing payable fields remain missing; an adjacent lot's value is never substituted.

## Optional fixed acquisitions (not run for this change)

The earlier investigation already spent its 14-request ceiling. **No network requests were issued while building this ledger.** A user may explicitly authorize a separate reacquisition with curl installed:

```sh
mkdir -p "$HOME/.cache/contract-signals"
python tools/build-public-link-evidence.py --fetch \
  --private-dir "$HOME/.cache/contract-signals/public-link-rerun-UNIQUE"
```

The final directory **must not exist**, must have an existing parent, must be absolute, and must resolve outside the repository. Use a different new directory for every rerun. An existing directory or symlink is rejected. The directory is 0700 and artifacts are 0600. The command does not rewrite the public ledger or import fresh results into any dataset.

The opt-in script makes exactly the published historical inventory's **14 attempts**: nine Ministry GET queries, two Nantes GET exports, three TED POST **syntax checks**, not executed searches. It preserves those historical request bodies deliberately; corrected exact-identity searches use the separate TED investigation tool below. A request must match the fixed method, full URL (including query) and JSON body, not merely a domain. Only the exact HTTPS host/path endpoints in that inventory are allowed. There is no generic URL option, pagination, extra query, buyer contact, authentication, retry, or redirect following. Curl's user configuration is disabled; a redirect response is recorded as a failure and its destination is never requested.

Each attempt has a 5-second connect timeout and a **15-second total process/transfer deadline**, a streaming **2 MiB body limit** (also passed to curl), no redirects and no retries. Timeout, body-limit, HTTP and acquisition failures are recorded without echoing raw error text. Partial bodies remain private and are hashed as partial retained bytes, not mistaken for successful responses. The private manifest records method, URL, request body, actual acquisition time, status when available, retained length/hash and failure category. Successful JSON is separately minimized to allowlisted reference/amount/CPV/date/duration scalars with row pointers; TED records only counts/timeout metadata, not notice titles or objects. Invalid JSON/schema produces a minimization failure. This private rerun manifest is **not automatically suitable for publication**: review any source scalar before exposing it.

Curl stdout bodies and status/error artifacts remain solely in the new external private directory. Network tests substitute local processes and mocks; they do not contact endpoints. Tests cover offline determinism, exact hashes and pointers, ID/reference mismatch, minimal field selection with synthetic personal/company/signature canaries, request ceiling and allowlist, private external storage, exclusive directory creation, redirect refusal, body limits and both curl and enclosing-process timeouts.

## Paris identifier and exact TED follow-up

The subsequent bounded investigation found five exact TED award publication numbers and verified **three** downloaded XMLs against the BOAMP notice UUID, procedure UUID and version `01`. Two XML requests returned HTTP 429 and were not retried. **This confirms notice/version identity only; it does not confirm a DECP contract crosswalk.** All nine original candidate pairs remain unconfirmed.

- [Paris identifier investigation](../research/paris-identifier-convention.md) and [minimized source evidence](../data/paris-reference-convention-evidence.json): Paris itself publishes the six long references as national-recensement numbers, but no authoritative mapping to short DECP IDs was acquired. The new Paris extract's source is **ODbL**, not Licence Ouverte or MIT. Direct Atexo exports were identified but not fetched because they exceed the acquisition bound; their catalogue has no specified data licence.
- [Exact TED investigation and request accounting](../research/paris-ted-link-review.md), [initial discovery ledger](../data/paris-ted-link-evidence.json), and [XML-version evidence](../data/paris-ted-version-evidence.json). The initial discovery stage made 12 attempts (including documentation and syntax checks); its separately bounded follow-up added five XML attempts. Combined with eight convention requests, this follow-up used **25 attempts** in total. Failures remain public metadata, raw bodies remain outside Git.

Offline reproduction/replay, without private caches or new requests:

```sh
python tools/review-paris-reference-conventions.py
python tools/investigate-paris-ted.py --replay-public data/paris-ted-version-evidence.json
```

The Paris offline inventory reproduces repository evidence; its live excerpts are recorded historical assertions with pointers and hashes. TED public replay recomputes discovery/version flags from the minimized record, not a new acquisition or independent authenticity check. No universal prefix/suffix stripping, amount matching or candidate promotion follows from these results.

## Agreement-benchmark boundary

`data/public-document-benchmark-plan.json` is a public, privacy-minimized copy of the local exclusive freeze produced by `tools/prepare-public-document-benchmark.py`. It contains nine blocked investigation pairs and an empty agreement queue—not nine verified contracts or an accuracy estimate. The plan was prepared **after** the identifier investigation and is not retrospective preregistration of those findings. See [the protocol](../research/public-document-benchmark.md).

```sh
python tools/prepare-public-document-benchmark.py \
  --public-output data/public-document-benchmark-plan.json
```

## Accessibility, storage and reuse

The endpoints and citations are publicly accessible source locators; **private local storage does not mean the source was confidential or privately obtained**. Conversely, a public endpoint does not require publishing all its response fields. The original raw live responses remain outside Git/the website; the reviewed request metadata and minimized historical scalar extracts expose what was requested and observed, while existing repository snapshots reproduce the BOAMP evidence and the curated public annotation file reproduces the historical live excerpts. Independently checking those historical excerpts against the complete response requires the exact body with the recorded hash; the opt-in fetch instead checks what the endpoint currently publishes. No claim of byte-identical historical reacquisition is made.

Attribution and reuse follow [data-sources.md](data-sources.md), rather than the code's MIT licence:

* BOAMP: DILA, **Licence Ouverte 2.0**, subject to its attribution/terms and caveats about incorporated third-party content and personal data.
* DECP: Ministère de l’Économie, **Licence Ouverte 2.0**; retained consolidator/buyer-feed scopes are documented separately there.
* Nantes buyer contract lists: Ville de Nantes / data.nantesmetropole.fr, **Licence Ouverte 2.0**.
* TED: Publications Office of the EU, **free reuse under the TED legal notice / Commission Decision 2011/833/EU**, a separate basis, not a transferred French LO 2.0 label.

Licence permissions do not remove privacy obligations. Public evidence annotations intentionally minimize fields; no raw response publication, contact republication or signature republication is necessary.
