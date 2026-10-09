# France 2023 backfill: availability check

Scope: the six municipal buyer SIRETs preregistered in `data/expansion-plan.json`, notification dates from 2023-01-01 inclusive to 2024-01-01 exclusive. This is an availability check, not a published dataset or completeness assessment.

| Municipality | Buyer SIRET | Ministry API source rows | Cached national source rows | Distinct national buyer + contract IDs |
| --- | --- | ---: | ---: | ---: |
| Dijon | 21210231300013 | 6 | 48 | 48 |
| Bordeaux | 21330063500017 | 35 | 92 | 44 |
| Rennes | 21350238800019 | 9 | 283 | 250 |
| Tours | 21370261600011 | 0 | 0 | 0 |
| Grenoble | 21380185500015 | 4 | 12 | 7 |
| Nantes | 21440109300015 | 38 | 177 | 142 |
| Total | | 92 | 612 | 491 |

## Sources and method

- Live Ministry API: `https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records`, six serial requests with `limit=0`, exact `acheteur_id` and the notification-date window. Only totals were requested; no contract records downloaded.
- Existing private national `decp.parquet` snapshot: data.gouv.fr dataset `608c055b35eb4e6ee20eb325`, retrieved previously on 2026-10-04. Its private cache manifest retains the fingerprint and retrieval provenance. Read only buyer ID, notification date, contract ID, source dataset and modification ID columns; no new national download.
- National source labels: Dijon/Grenoble `aws_marches-publics.info` and `scrap_marches-publics.info`; Bordeaux additionally `decp_colmo`; Rennes `megalis_bretagne`; Nantes `atexo_nantes_metro`.

## Interpretation and next gate

The current Ministry source alone is insufficient for the intended historical backfill. The national snapshot exposes 491 distinct buyer + contract identifiers, but these are candidate groups, **not 491 verified unique contracts**. Source rows may represent versions, holders or duplicated publications. Conflicts, original values, source semantics, subject-text privacy and provenance still require review.

Tours has zero matches in both sources. This does not establish zero procurement in 2023. Locate an official historical source and check identifier/window coverage before claiming a six-city backfill or year-to-year spending comparability.

Next: review historical source distribution and normalization for the five nonempty buyers, and investigate Tours' official historical publication. Keep any resulting cohort separate and browse-only; do not overwrite 2024–2025 snapshots or enable scoring. No dataset integration, publication or deployment has been performed.

## Follow-up: offline state and date-window audit

Reproducible command (requires the private cache and its PyArrow environment):

```sh
~/.cache/contract-signals/venv/bin/python tools/audit-france-2023-backfill.py
```

The aggregate report is written privately to `~/.cache/contract-signals/decp-national/france-2023-backfill-audit.json`, with the input snapshot's SHA-256. The audit selects groups with any notification in 2023, then inspects **all available rows** for those buyer/contract IDs, including other years. Initial states are rows with `modification_id=0`. Procurement-state differences, including holder identity, remain conflicts; publication-source labels alone do not define different states. No record IDs, subjects, supplier IDs or fingerprints are emitted.

| Municipality | 2023 candidate groups | Conflicting initial groups | Single initial state dated 2023 |
| --- | ---: | ---: | ---: |
| Dijon | 48 | 0 | 48 |
| Bordeaux | 44 | 14 | 29 |
| Rennes | 250 | 22 | 199 |
| Tours | 0 | 0 | 0 |
| Grenoble | 7 | 3 | 4 |
| Nantes | 142 | 37 | 105 |
| Total | 491 | 76 | 385 |

These columns are not a partition: some groups lack an initial state in the window. Across the candidates, 61 groups have an initial notification outside 2023. No identical initial states or missing contract IDs were found among these candidate groups. Grenoble's three conflicting groups differ only in holder identity, which may reflect coholders or supplier versions; they must not be resolved by selecting an arbitrary row. The 385 single-state groups are **not a validated publishable cohort**: missing fields, source semantics, rights and subject-text privacy still require review.

Tours' exact municipal SIRET has 383 source rows dated 2025 and 471 dated 2026 in the same snapshot, but none dated 2023. This indicates a historical coverage gap, not zero purchasing. No metropolitan buyer was substituted for the preregistered municipality.

### Tours metadata-only source check

Three bounded official metadata requests (no contract records or attachments downloaded):

1. data.gouv.fr catalogue query `Tours données essentielles marchés publics`: zero results.
2. Catalogue query `Tours marchés`: one result, [Les marchés - Tours Métropole Val de Loire](https://www.data.gouv.fr/datasets/les-marches-tours-metropole-val-de-loire).
3. Its [publisher dataset metadata](https://data.tours-metropole.fr/api/explore/v2.1/catalog/datasets/marches-tours-metropole-val-de-loire) exposes locations, opening hours and contact fields, not procurement contract/buyer/award fields. It is not a suitable DECP backfill source and concerns the metropolitan area rather than the exact municipal buyer.

Metadata responses are retained privately beside the audit (`tours-metadata-check.json`, `tours-metadata-broad-check.json`, `tours-dataset-metadata.json`). Catalogue keyword searches are not exhaustive; an official historical municipal procurement source remains unresolved. Next gate: locate the municipality's historical buyer-profile publication and verify exact buyer identity and date semantics before collecting records.

Five synthetic audit tests cover duplicate states, metadata-only differences, holder/amount conflicts, missing versus zero values, modifications, cross-year groups and Tours coverage. The complete non-browser suite passed with 234 Python tests. No existing dataset, score or deployed page was changed.
