# Which country to add after France?

**Recommendation: Colombia first; Paraguay after access validation; Brazil later as a more ambitious project.** No CPI ranking and no country bonus in the index.

> **Status update (22 September 2026): the Colombia/SECOP II pilot is implemented** as a bounded, pre-announced cohort — three buyers (MEN, Gobernación de Caldas, Alcaldía Local de Usaquén), 7,560 contracts signed 2024-09-01 → 2026-09-01, process–contract–supplier join verified on every row, Spanish preserved, COP only, licence CC BY-SA 4.0. **No heuristic indicator exists for Colombia yet: every row stays “Not assessed”.** The declared “Contratación directa” modality (≈82 % of the pilot cohort) is legal context, never a signal. See `data/colombia-secop2-coverage.json`, `tools/import-colombia-secop2.py`, `tests/colombia.cjs` and the README section. The rest of this document keeps the original recommendation, of which the parts below about Paraguay, Brazil and the general rules still apply.

The CPI figures, national volumes and exhaustiveness claims from the text proposed by the user were not taken as facts. The checks below are small anonymous HTTP tests, carried out on **21 September 2026**, not procurement imports. Sources, parameters, statuses, failures and UTC times: [`international-access-checks.json`](../data/international-access-checks.json). No foreign row containing personal data was retained.

| Candidate | Verification performed | Practical decision |
| --- | --- | --- |
| **Colombia — SECOP II** | Official metadata of “Contratos Electrónicos” and a request limited to one row: HTTP 200 JSON, without a token. The dataset sheet announces the `CC_40_BY_SA` licence. | **Pilot implemented (see status update above); the offers/proposals and payment-reconciliation verification remains open before any attrition or payment indicator.** |
| **Paraguay — DNCP/OCDS** | Portal and Swagger v3: HTTP 200. The schema exposes 30 routes, including OCDS records/releases, but declares global Bearer security. No real OCDS record was retrieved in this test. | Good conceptual candidate for versions and modifications, **subject to authorized access, licence and a verified real OCID**. An accessible Swagger is not an anonymously accessible data API. |
| **Brazil — PNCP** | A request with page size 1 responded 400; two other variants timed out, including a size 10 on a single day. | High enrichment potential, but **operational access not established here**. Repeat a consultation attempt before announcing a ready pilot. Compras, PNCP and Transparência must not be treated as an already-linked base. |
| **Ukraine — Prozorro** | Public index of tenders, `limit=1`: HTTP 200 JSON, one entry, without a token. | Promising technical access; wartime regime, exceptions and publication restrictions require specific local handling. Not the first scoring pilot. |
| **Moldova — MTender** | Official open-data page accessible, HTTP 200 HTML. | To explore next; this test verifies neither a records API nor the completeness of its releases. |
| **Another EU country via TED** | Official XML of a notice already matched by UUID: HTTP 200 without a token. The project has already tested anonymous TED search and downloaded the Tours XMLs. | Least expensive variant technically: a small TED scope in **Portugal or Romania**, for example. The national systems of these two countries were not tested here; TED does not cover all their purchases or payments. |

## Official sources and exact limits

- **Colombia**: [SECOP II metadata](https://www.datos.gov.co/api/views/jbjy-vk9h), [one-row API](https://www.datos.gov.co/resource/jbjy-vk9h.json?$limit=1). The tested dataset is the electronic-contracts one; the other candidate tables or payment plans were not verified in this work. An updated sheet is not an immutable version history. Check attribution, licence and sharing obligations before redistribution/enrichment.
- **Paraguay**: [DNCP portal](https://www.contrataciones.gov.py/datos/), [Swagger v3](https://www.contrataciones.gov.py/datos/api/v3/doc/swagger.json), [documentation interface](https://www.contrataciones.gov.py/datos/api/v3/doc/). Documented routes `/ocds/record/{ocid}` and `/ocds/releases/ocid/{ocid}`: the name of a route does not demonstrate that the whole national history is available. The actual per-route need for a token, obtaining it, quotas and the licence remain to be verified.
- **Brazil**: [PNCP portal](https://www.gov.br/pncp/pt-br), tested endpoint `https://pncp.gov.br/api/consulta/v1/contratos`. The exact parameters and errors are in the log. Timeouts do not prove an access ban. The modalities of the federal transparency portal, CNPJ/partner data, redistribution rights and join keys **were not verified here**.
- **Ukraine**: [Prozorro API index limited to one entry](https://public.api.openprocurement.org/api/2.5/tenders?limit=1). A readable index does not demonstrate that all documents of each tender are available or redistributable.
- **Moldova**: [MTender page](https://mtender.gov.md/public/open-data). No cohort download in this check.
- **TED**: [verified official XML](https://ted.europa.eu/en/notice/8206-2025/xml), [legal notice](https://ted.europa.eu/en/legal-notice). Do not confuse observed anonymous access with unconditional authorization for all European content or services.

## Proposed pilot: small, reproducible, not “the whole country”

1. **Colombia: pre-select 3 buyers**, by administrative level and documented availability, without consulting their scores. Common window of **24 months**; announce the identifiers before downloading.
2. Download all pages of this cohort, keep the versions and conflicts. Verify the process–contract–supplier join before adding proposals or payments.
3. Verify dates, amounts and original currencies, cancelled contracts, amendments, coverage of each field and diffusion rights. Do not automatically convert all amounts into euros.
4. Publish a small static JSON, with **jurisdiction-specific** parameters/rules. Start with coverage and sources; do not copy the French thresholds as Colombian legal thresholds.
5. Examine flagged **and unflagged** examples, then only decide whether to extend to more buyers or to Paraguay.

No global spending total or country league table: coverage and publication obligations differ too much. Grants remain a separate module. Payments must match the same contract, scope, currency and period before comparison; a difference is not automatically a diversion. A sanction must be relevant to the entity, the dates, the jurisdiction, the remedies and the applicable prohibition. Sharing a name, an address or an administrator is not enough to add points or infer a control relationship. Document requests and their access conditions are to be verified country by country.

These recommendations concern the **order of work**, not a presumed rate of corruption. No new country is imported into the explorer yet.
