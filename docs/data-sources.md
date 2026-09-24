# Data sources and licences

The project's code and documentation are MIT-licensed (see `LICENSE`). Files under `data/` are extracts of third-party public data and keep their original licences. Reusing them means attributing the publisher. For CC BY-SA data, anything derived from it must be shared under the same licence.

| Dataset in the explorer | Files | Publisher / source | Licence |
| --- | --- | --- | --- |
| France · Paris & Ardèche — DECP | `decp-history.json`, `decp-coverage.json` | Ministère de l’Économie, `decp-2022-marches-valides` on data.economie.gouv.fr | Licence Ouverte v2.0 (Etalab) — stated in the portal metadata |
| France · six cities — DECP | `decp-cities*.json` | same | Licence Ouverte v2.0 (Etalab) |
| Current supplier names (both DECP cohorts) | `supplier-identities*.json`, `supplierProfiles` in the DECP files | API Recherche d’entreprises / Annuaire des entreprises | To confirm on the source; only companies whose register status is fully public (`statut_diffusion = O`) are named |
| France · Tours notices, 3 Feb 2025 consultations, nationwide BOAMP sample | `tours-notices*.json`, `consultations*.json`, `contracts.json`, `coverage.json` | BOAMP (DILA), boamp.fr open-data API; TED XML for Tours | To confirm: the BOAMP API metadata states no licence |
| Eight CRC audit dossiers (inside `contracts.json`) | `contracts.json` | Chambres régionales des comptes reports, quoted with links | Short quotations with source; read the full report |
| Colombia · SECOP II | `colombia-secop2*.json`, `colombia-secop2/raw/` | Colombia Compra Eficiente, datos.gov.co `jbjy-vk9h` | **CC BY-SA 4.0** — recorded in the coverage file |
| Paraguay · DNCP OCDS | `paraguay-dncp*.json`, `paraguay-dncp/raw/` | Dirección Nacional de Contrataciones Públicas, contrataciones.gov.py | **CC BY 4.0** — recorded in the coverage file |

Each `*-coverage.json` file records the exact queries, retrieval dates, selection rules and known gaps of its dataset. Source PDFs for the Paris 13 November 2025 dossier are in [`sources/paris-13-november-2025/`](sources/paris-13-november-2025/).
