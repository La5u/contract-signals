# Paraguay DNCP · bounded documentary pilot

> **Update, 25 September 2026:** these rows are now scored with Paraguayan checks ([score-paraguay.md](score-paraguay.md)), and a second, separately stored three-buyer cohort (MOPC, Gobierno Departamental de Central, Municipalidad de Asunción) was added. The two excluded entries turned out to be the separate `AC-…` entries the DNCP publishes for amount amendments (“Ampliación de Monto”, +20.0 % and +19.99 %). The amendments stay attached to their parent contracts. The “not assessed” statements below describe the pilot as first published.

The first Paraguayan pilot is **one municipality, not a national analysis**: Municipalidad de Fernando de la Mora (`DNCP-SICP-CODE-66`). Selected before downloading full contract records, by manageable process count and existing official sample availability, not by CPI or indicator results. The search fixes `parties.identifier.id=66` and `tipo_fecha=publicacion_llamado` from **2024-09-01 inclusive to 2025-09-01 exclusive**. This selects *call publications*, not signatures or spending during those dates. Contracts published subsequently in those processes can appear in the full records.

Source: official DNCP OCDS 1.1 API under `https://www.contrataciones.gov.py/datos/api/v3/doc`, anonymous at collection time; publisher DNCP, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), policy `https://www.contrataciones.gov.py/datos/legal`. The exact search URL, two raw search pages, and 88 full OCID record packages are preserved in `data/paraguay-dncp/raw/`. Reproduce the normalized extract offline with `python tools/import-paraguay-dncp.py --offline`. The download checks page totals/unique OCIDs, buyer ID, license, version, and unique normalized IDs; a new live run is **not** a fixed archival snapshot and should be stored separately, not silently merged with the retained pages.

| Published records | Count |
| --- | ---: |
| Search process records | 88 |
| Full records with an eligible linked contract | 84 |
| Contract entries in full records | 86 |
| Retained buyer/contract/award/single-identified-supplier/PYG links | 84 |
| Excluded contract entries (amendment-like entries without `awardID` or contract value) | 2 |
| Retained rows with a document *typed* `contractSigned` | 80 |
| Retained rows with published `dateSigned` | 0 |
| Releases in full record packages | 93 |
| Contract amendment entries in compiled releases | 2 |

One row means one published contract entry connected to an award by `awardID`, and one declared supplier ID. It does **not** mean we have read a signed contract document. The displayed row date is `contract.period.startDate`, **not** a signature date (`dateSigned` is absent from all retained entries); declared PYG amounts are not reconciled payments. A `contractSigned`-typed document link does not verify its contents. The 93 releases are not evidence of a complete change history, and the 2 amendment entries are context only. The 2 excluded entries (`AC-30173-25-252358` and `AC-30173-24-248077`) occur beside retained contracts and have no `awardID` or own contract value; they are not counted as new contract awards. The 4 search processes without eligible contracts are not counted as contracts.

**No Paraguayan index is computed.** Every row shows *Not assessed*, not zero. French and Colombian thresholds do not apply. Before scoring: manually review a sample of linked award and contract documents, investigate the two excluded entries, determine tender/offer semantics and cross-version completeness, validate procurement exceptions under Paraguayan rules, and pre-register locally meaningful checks and counterexamples. No CPI coefficient, country ranking, cross-currency total or implied probability.

Files: `tools/import-paraguay-dncp.py`, `data/paraguay-dncp.json`, `data/paraguay-dncp-coverage.json`, `tests/test_import_paraguay_dncp.py`, `tests/paraguay.cjs`. Run `node tests/paraguay.cjs` and `python -m unittest discover -s tests -p 'test_*.py'` after regeneration.
