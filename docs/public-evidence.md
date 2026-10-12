# Public BOAMP–DECP evidence ledger

Nine reviewed pairs cover six notices and seven notice/lots: **seven active candidates, two dismissed leads, zero confirmed DECP links and zero resolved amounts**. Three BOAMP↔TED notice versions are verified; two XML checks remain unresolved after HTTP 429. Contract fields and scoring are unchanged; a missing, invalid or stale ledger must not suppress base candidate links.

## Applied resolutions and correction history

- Paris `2024S05079` ↔ BOAMP 25-21317 LOT-0001 dismissed: the long-reference pattern belongs to **LOT-0003**; no replacement is confirmed.
- Nantes `2025F00012` ↔ BOAMP 25-34782 LOT-0003 dismissed: the notice says **Lot 2, LAVERIE**, while DECP says **CUISSON**. Identifiers remain unbridged; dismissal does not prove different legal contracts.
- [Correction history](../research/link-corrections-log.md), [decisions](../data/boamp-decp-link-decisions.json) and [resolution overlay](../data/public-link-resolutions.json) retain reasons and unresolved questions. Run the raw link builder before the overlay after dataset rebuilds; changed source/row hashes require fresh review.

## Reproduce without a private cache or network

From the repository root with Python 3.9+ (3.10+ recommended):

```sh
python tools/build-public-link-evidence.py
python tools/review-link-resolutions.py
python -m unittest discover -s tests -p test_build_public_link_evidence.py -v
python tools/build-public-link-evidence.py --output /tmp/public-link-evidence.json
cmp data/public-link-evidence.json /tmp/public-link-evidence.json
```

The deterministic build writes `data/public-link-evidence.json` from repository snapshots and `research/public-link-observations.json`; hashes bind reviewed annotations and source fields to exact inputs, with JSON pointers locating the evidence. Every published BOAMP reference and DECP ID was checked against repository records; see [the investigation](../research/public-boamp-decp-investigation.md).

## Provenance and interpretation

- Five Paris pairs have reference patterns without an authoritative crosswalk; two Nantes pairs are lot-compatible without an identifier bridge. Nantes’s `-1` is a local suffix. Do not strip references, repair digits or combine reused IDs to infer identity.
- Exact BOAMP, Ministry, Nantes and TED URLs/bodies are in the ledger/inventory. Pair 8’s prior citation <https://ted.europa.eu/en/notice/-/detail/723965-2024> was not fetched and does not support a DECP link.
- The ledger retains 104 minimized historical scalars, including four Nantes 2025 row pointers. Historical responses were HTTP 200; TED’s three `checkQuerySyntax:true` requests were syntax checks, not searches, so empty results do not establish absence. Fresh requests need not reproduce historical responses; independent verification needs the recorded full body.
- Retrieval, publication, award, conclusion and notification dates remain distinct; normalized snapshots have no inferred retrieval time. Payable amounts, framework maximums, DECP declarations and HT ceilings are distinct; missing values stay missing, with no adjacent-lot substitution.

## Optional fixed acquisitions

With explicit authorization and curl installed, run `mkdir -p "$HOME/.cache/contract-signals"`, then `python tools/build-public-link-evidence.py --fetch --private-dir "$HOME/.cache/contract-signals/public-link-rerun-UNIQUE"`.

The absolute directory must be new, outside the repository, with an existing parent; symlinks/existing directories are rejected (directory 0700, files 0600). The fixed inventory makes 14 attempts with exact methods, URLs and bodies, including TED syntax checks; no retries or redirects. Limits: 5-second connection, 15-second total deadline, 2 MiB body. Raw/partial bodies and failure records stay private; review minimized outputs before publication. Fetching does not rewrite the ledger or datasets; tests use mocks.

## Paris identifier and exact TED follow-up

[Paris review](../research/paris-identifier-convention.md) and [source evidence](../data/paris-reference-convention-evidence.json): six long references are national-recensement numbers, without a verified mapping to short DECP IDs. Paris data is **ODbL**; direct Atexo exports exceed the acquisition bound and have no specified licence. [TED review](../research/paris-ted-link-review.md), [discovery evidence](../data/paris-ted-link-evidence.json) and [XML evidence](../data/paris-ted-version-evidence.json): five exact publication numbers found; three XMLs match notice UUID, procedure UUID and version `01`. This verifies notice/version identity only. Replay checks retained evidence, not source authenticity:

```sh
python tools/review-paris-reference-conventions.py
python tools/investigate-paris-ted.py --replay-public data/paris-ted-version-evidence.json
```

## Agreement-benchmark boundary

`data/public-document-benchmark-plan.json`, produced by `tools/prepare-public-document-benchmark.py`, retains nine blocked pairs and an empty agreement queue. It was prepared after the identifier investigation, not preregistered; it is an immutable pre-disposition snapshot, with zero agreement denominator. Future plans must account for the overlay; see [the protocol](../research/public-document-benchmark.md).

Reproduce: `python tools/prepare-public-document-benchmark.py --public-output data/public-document-benchmark-plan.json`.

## Accessibility, storage and reuse

Public evidence contains selected procurement scalars and reviewed amount excerpts; raw live responses stay outside Git/the website, and names, contacts and signatures are omitted from the public evidence. Public access does not clear privacy or attachment rights. Attribution and reuse follow [data-sources.md](data-sources.md): DILA/BOAMP, Ministère de l’Économie/DECP and Ville de Nantes/data.nantesmetropole.fr use **Licence Ouverte 2.0**; TED/Publications Office of the EU permits free reuse under its legal notice / Commission Decision 2011/833/EU.
