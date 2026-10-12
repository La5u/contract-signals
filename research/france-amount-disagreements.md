# French amount disagreements: offline review queue

## Result

The published files contain **885 `sources-disagree` records; zero resolved**.

| Current cohort | Population | Disagreements | Declared max/min > 2× |
|---|---:|---:|---:|
| Paris/Ardèche | 2,997 | 788 | 486 |
| Six cities | 2,289 | 97 | 33 |
| Total | 5,286 | **885** | **519** |

Paris/Ardèche: **782 Paris, 6 Ardèche**. Cities: **91 Nantes, 4 Grenoble, 1 Dijon, 1 Bordeaux**; none in Rennes/Tours. Cities contain **2,289**, not HANDOFF's older 2,299.

All 885 have exact buyer-SIRET/contract-ID declarations in raw snapshots. Only **one** has an additional exact portal declaration. These are not signed documents or independent votes.

BOAMP searches yield lot candidates for **25** records (19 Paris/Ardèche, 6 cities). **Zero** meet the tool's strict buyer-ID plus complete equal settled-contract-reference rule. Incomplete caches and different/placeholder references prevent interpreting this as absence of notices. Candidate fragments contain **329 payable, 376 maximum, 57 other amount fields**, no estimates: occurrences across possibly unrelated/repeated lots, not resolutions. Annual/full-term equivalence and the claim “mostly basis differences” remain unestablished.

## Reproduction and inputs

```sh
python tools/review-france-amount-disagreements.py
python -m unittest discover -s tests -p test_review_france_amount_disagreements.py -v
```

Private `~/.cache/contract-signals/france-amount-disagreements/run-*/` contains `queue.jsonl` (all 885, existing order, raw pointers and basis/linkage unknowns), `provenance.json` (input/response hashes and retrieval metadata), `summary.json`. Directories/files use **0700/0600**. The tool is offline and makes no replacements or sorting changes.

Inputs:

- `data/decp-history.json`, `data/decp-cities.json`: reviewed before CPV corrections; regenerated after **165 CPV-only corrections**, with counts/outcomes unchanged.
- `data/decp-history-raw.json.gz` (**2026-09-25**), `data/decp-cities-raw.json` (**2026-09-15**): initial and modification amounts stay separate; modifications are revised totals, not increments.
- `data/decp-feeds-raw.json.gz` (**2026-10-04**): exact buyer/contract joins, retaining sourceDataset/sourceFile and current/modification flags; no silent truncated-ID joins.
- `data/city-portals-raw.json.gz` (**2026-10-08**): Nantes/Bordeaux, retaining the documented Nantes 2024 buyer-SIRET correction.
- `data/boamp-raw.json.gz`; private `accuracy-sample-20261008/responses*`, `paris-pairs-20261008`, `decp-conflict-dijon/project-notices-20261008`. Accept only manifested, complete HTTP-200 responses; **one truncated response excluded**, its resumed response considered separately.

## Resolution policy and next step

- Require exact buyer/contract/lot linkage. Name similarity, substring references, equal amounts and `tools/accuracy-sample.py`'s “any printed amount matches” rule are insufficient.
- Annual/full-term scope needs explicit period/renewal evidence; ratios or duration alone do not justify multiplying, annualizing or summing co-holders.
- Keep maximum, estimate, payable and unknown fields separate, with currency/pointers. Exclude procedure totals from lot comparisons and reject ambiguous tender links.
- Align tax, period, amendments and version. Current register names do not establish historical identity.
- The parser supports the retained eForms shape, not all legacy/list layouts; unsupported layouts fail closed. Repeated notices are not independent corroboration.

Review search candidates for exact linkage and the **519 >2×** cases for explicit basis definitions. Acquire a small exact-document set only after identifying contract/lot; retain URL, date, hash, page, currency, tax, period and renewals. Otherwise leave unresolved.

**9 focused tests passed**, including basis separation, exact references, ambiguity/unsupported-layout rejection, zero/nonfinite handling and repeatable read-only builds.
