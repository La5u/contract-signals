# Bounded current official-source amount recheck

## Scope and preregistration

The offline accuracy review was followed by an explicitly authorized, bounded
current-source check on 2026-10-07 UTC. Before any request, a private plan froze
exactly three rows, selected deterministically from the private review queue:

- First BOAMP `raw_source_missing` row, sorted by full published ID: **1**.
- First BOAMP `raw_source_zero` row, sorted by full published ID: **1**.
- First Colombia `raw_source_zero` row, sorted by full published ID: **1**.

Full IDs, original evidence, input hashes and exact request URLs are held only in
`~/.cache/contract-signals/current-amount-recheck/`. Each run has a durable
`plan.json` written before fetching. The default command freezes a plan without
network activity; only `--fetch` enables requests. No published data was changed.

## Counts-only findings

| Preregistered stratum | Planned | HTTP 200 / compared | Current missing | Current zero | Positive candidates | Identity conflicts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BOAMP: retained source missing | 1 | 1 | 1 | 0 | 0 | 0 |
| BOAMP: retained source zero | 1 | 1 | 0 | 1 | 0 | 0 |
| Colombia: retained source zero | 1 | 1 | 0 | 1 | 0 | 0 |
| **Total** | **3** | **3** | **1** | **2** | **0** | **0** |

Requests attempted: **3**. Failures: **0**. Unattempted planned rows: **0**.
No recovery candidates were found in these three current responses.

## Method and safeguards

`tools/recheck-amount-gaps.py` uses only two explicit official API endpoints:

- BOAMP Explore records API: exact `idweb` filter, limit **2**. Its response is
  checked against the exact notice, lot, contract, result and original winning
  tender references. The existing offline review matcher extracts only the
  winning tender's original `PayableAmount` basis; aggregate notice, award and
  estimated values cannot substitute for it.
- Colombia datos.gov.co Socrata dataset `jbjy-vk9h`: exact full `contractId`
  filter, limit **2**, selecting only `id_contrato`, `proceso_de_compra`,
  `valor_del_contrato`, and `estado_contrato`. Full contract and process IDs must
  match the unique normalized row. The basis remains SECOP contract value in COP.

Requests are serial, with at least **2 seconds** between completed attempts,
**15-second** request timeout, at most **3** requests, and a **2 MiB** response
read cap. A response reaching the cap is rejected as potentially truncated.
There are no redirects, retries, bulk exports, attachment downloads or tokens.
Any non-200 response (including 403, 429 and 5xx), transport/parsing failure or
identity ambiguity stops the run without replacing the selected row.

Private response bytes, retrieval UTC, requested URL, byte count, SHA-256,
comparison and summary are recorded outside the repository and served files.
Output directories use **0700**, files **0600**; these permissions were checked
for the fetched run. Only aggregate counts are printed. Existing source IDs,
amount bases and currencies are preserved; a future positive result would be a
research candidate only, never an automatic update or an importer-loss finding.

Source/reuse constraints were reviewed in `docs/data-sources.md`: BOAMP's
published dataset has Licence Ouverte 2.0 evidence and Colombia SECOP II is
CC BY-SA 4.0. Neither label clears all personal-data or incorporated-content
issues. No response text, names, contacts, full IDs or individual amounts are
published in this report.

## Limitations and validation

This is a deterministic three-row case check, not a representative sample,
full-source audit or coverage estimate. Current responses need not reconstruct
historical publication state. A missing value and a declared zero remain
separate categories; neither proves an actual zero-value procurement. BOAMP's
winning-tender payable basis is not independently verified signed-contract
value. Colombia's current contract value is not payment or execution value.
No linked notices, amendments, attachments or alternate sources were explored.

Validation: **7** small recheck tests and **11** existing offline-review tests
passed. Tests cover deterministic selection, minimized exact queries,
contract/process matching, original BOAMP winning identity and currency checks,
candidate-only behavior, stop-on-error, private file modes, serial delay,
response cap and disabled redirects. The no-network plan run and the authorized
bounded live run both completed; the latter made exactly **3** requests.
