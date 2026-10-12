# France 2023 backfill: availability check

Scope: six municipal SIRETs in `data/expansion-plan.json`, notification dates **2023-01-01 inclusive to 2024-01-01 exclusive**. This checks availability, not completeness.

| Municipality | Buyer SIRET | Ministry API source rows | Cached national source rows | Distinct national buyer + contract IDs |
| --- | --- | ---: | ---: | ---: |
| Dijon | 21210231300013 | 6 | 48 | 48 |
| Bordeaux | 21330063500017 | 35 | 92 | 44 |
| Rennes | 21350238800019 | 9 | 283 | 250 |
| Tours | 21370261600011 | 0 | 0 | 0 |
| Grenoble | 21380185500015 | 4 | 12 | 7 |
| Nantes | 21440109300015 | 38 | 177 | 142 |
| Total | | 92 | 612 | 491 |

## Sources and audit

- Ministry `https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records`: exact buyer/date filters, `limit=0`, totals only.
- Private national `decp.parquet`: data.gouv.fr dataset `608c055b35eb4e6ee20eb325`, retrieved **2026-10-04**. Sources: Dijon/Grenoble AWS and scraped AWS; Bordeaux also `decp_colmo`; Rennes Mégalis; Nantes Atexo.
- Audit all years for IDs notified in 2023. Initial states use `modification_id=0`; holder/state differences conflict, source labels alone do not.

```sh
~/.cache/contract-signals/venv/bin/python tools/audit-france-2023-backfill.py
```

Private aggregate: `~/.cache/contract-signals/decp-national/france-2023-backfill-audit.json`, with input hash.

| Municipality | 2023 candidate groups | Conflicting initial groups | Single initial state dated 2023 |
| --- | ---: | ---: | ---: |
| Dijon | 48 | 0 | 48 |
| Bordeaux | 44 | 14 | 29 |
| Rennes | 250 | 22 | 199 |
| Tours | 0 | 0 | 0 |
| Grenoble | 7 | 3 | 4 |
| Nantes | 142 | 37 | 105 |
| Total | 491 | 76 | 385 |

Not a partition: some groups lack an initial state in-window; **61** have initial dates outside 2023. No identical initial states or missing IDs. Grenoble conflicts differ only by holder; do not pick one. The **385** single-state groups still need field/source/rights/privacy review.

Tours: **383** rows in 2025, **471** in 2026, none in 2023. Coverage gap, not zero purchasing; no Métropole substitution.

- Catalogue query `Tours données essentielles marchés publics`: no result; `Tours marchés`: [Les marchés - Tours Métropole Val de Loire](https://www.data.gouv.fr/datasets/les-marches-tours-metropole-val-de-loire).
- [Publisher metadata](https://data.tours-metropole.fr/api/explore/v2.1/catalog/datasets/marches-tours-metropole-val-de-loire) describes locations, hours and contacts, not procurement. Private responses: `tours-metadata-check.json`, `tours-metadata-broad-check.json`, `tours-dataset-metadata.json` beside the audit. Searches are not exhaustive.

Next: review five nonempty buyers and locate Tours' municipal historical source with exact buyer/date semantics. Keep backfill separate, browse-only; preserve 2024–2025 and scores.

Five synthetic audit tests and the complete non-browser suite (**234 Python tests**) passed. No dataset, score or deployed page changed.
