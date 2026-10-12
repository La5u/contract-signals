# Paris identifier convention — public-only investigation

## Finding and decision

Ville de Paris publishes the exact long references found in BOAMP. No authoritative link to the shortened DECP IDs, or specification for shortening them, was obtained. **No candidate can be promoted or generally normalized.**

The Ministry's version **2.0.2** defines a buyer-internal ID of **1–16 characters**. Both the 14-character Paris references and 10-character DECP IDs fit, but that does not make them equivalent. The compound Paris/CASVP reference must retain both buyer scopes.

## Reproduction and evidence

- Evidence: [`../data/paris-reference-convention-evidence.json`](../data/paris-reference-convention-evidence.json). It records snapshot provenance, dated acquisitions, pointers and hashes.
- Offline inventory: `python tools/review-paris-reference-conventions.py`; reads public files and prints JSON without network or dataset writes.
- Tests: `python -m unittest discover -s tests -p 'test_review_paris_reference_conventions.py' -v` (three passed).
- Private acquisition material: `/tmp/paris-convention-work/`, directory 0700 and files 0600; temporary, not a permanent archive.
- Eight HTTP attempts succeeded. Bounds: HTTPS, 5-second connect timeout, 15-second total timeout, 2 MiB body limit, no redirects or retries.

Inputs: `data/decp-feeds-raw.json.gz` (2026-10-04T12:23:23+00:00), `data/decp-history-raw.json.gz` (2026-09-25T12:03:30.277162+00:00), `data/boamp-raw.json.gz` (2026-09-25T12:05:56.859285+00:00), and `research/public-link-observations.json`.

The feed is a **Colmo/decp.info consolidation**, not an inspected direct Atexo export. Rows retain `id`, `uid`, `sourceDataset`, `sourceFile` and `acheteur_id`. A buyer+short-ID+CPV UID does not link to a BOAMP long reference.

## Retained rows: buyer `21750001600019`

Indices are zero-based under `/records`. Feed `sourceDataset` is `atexo_maximilien`. None supplies sufficient linkage.

| Candidate | Notice / technical lot | BOAMP reference | DECP ID | Feed row | Ministry rows |
|---:|---|---|---|---:|---|
| 1 | 25-21317 / LOT-0001 | `20242024S05075` | `2024S05075` | 4139 | 634, 635 |
| 2 | 25-21317 / LOT-0001 | `20242024S05075` | `2024S05079` | 4141 | 638, 639 |
| 3 | 25-21329 / LOT-0001 | `2025S015900000 / 2025HA0001GR` | `2025S01590` | 5139 | 1464 |
| 7 | 25-37616 / LOT-0001 | `2025F026500000` | `2025F02650` | 4909 | 1589 |
| 8 | 25-45958 / LOT-0005 | `2025S029150000` | `2025S02915` | 5197 | 1615 |
| 9 | 25-47556 / LOT-0001 | `2025F026480000` | `2025F02648` | 4907 | 1689 |

No scalar in the retained feed or Ministry rows for this buyer contains any of the six long Paris references or `2025HA0001GR`. This does not cover omitted parquet fields, other buyers, historical versions or direct publisher files. Repeated Ministry IDs do not establish one unique contract.

Decode `/records/{i}/donnees` first. BOAMP references are under `/EFORMS/ContractAwardNotice/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/efext:EformsExtension/efac:NoticeResult/efac:SettledContract[/{i}]/efac:ContractReference/cbc:ID`; all nine candidate pointers are in `repositorySnapshot/pairs`.

See [`public-boamp-decp-investigation.md`](public-boamp-decp-investigation.md) for singleton/list handling and contract–tender–lot chains. Candidate 2's sibling LOT-0003 carries `20242024S05079`; do not reassign it automatically. Paris-compatible candidates remain 1, 3, 7, 8, 9. Nantes candidates 4–6 are outside this search: 4 remains disfavored, 5–6 lot-compatible but unbridged.

## Published sources and gaps

- **Atexo / GIP Maximilien:** <https://www.data.gouv.fr/api/1/datasets/67272093922b37b9b2f1b653/> names `ATEXO - DECP`; dataset/resource schemas are null and give no crosswalk. Resources `ed3d8ced-fdb6-41e1-933d-c0a15984ad16` (`decp-2024.json`, **13,098,029 bytes**) and `ef2d35a1-a6d6-4301-badf-bd7f59ee0e0b` (`decp-2025.json`, **12,373,486 bytes**) exceeded the 2 MiB limit and remain uninspected. They may differ from the October 4 consolidation versions.
  - <https://static.data.gouv.fr/resources/donnees-essentielles-du-profil-acheteur-gip-maximilien/20261010-230446/decp-2024.json>
  - <https://static.data.gouv.fr/resources/donnees-essentielles-du-profil-acheteur-gip-maximilien/20261011-000449/decp-2025.json>
- **Ministry:** <https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides> links <https://schema.data.gouv.fr/139bercy/format-commande-publique/>. Release 2.0.2 applies from January 1, 2024. Documentation <https://raw.githubusercontent.com/139bercy/format-commande-publique/2.0.2/_index.md> (line 9) and schema <https://raw.githubusercontent.com/139bercy/format-commande-publique/2.0.2/schema_decp_v2.0.2.json> (`/definitions/marche/definitions/IdentifiantMarche`) specify a buyer-internal string, not repeated-year removal, zero stripping or compound splitting. File discovery: <https://api.github.com/repos/139bercy/format-commande-publique/git/trees/2.0.2?recursive=1>.
- **Paris catalogue:** <https://opendata.paris.fr/api/explore/v2.1/catalog/datasets?where=search%28%22march%C3%A9s%22%29&limit=20> returned 20 entries. Entry 5, `liste-des-marches-de-la-collectivite-parisienne`, defines `num_marche` as “Numéro national de recensement du marché”, with no buyer-SIRET/DECP-ID crosswalk fields.
- **Paris records:** <https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/liste-des-marches-de-la-collectivite-parisienne/records>. An exact query for six long references, six short counterparts and `2025HA0001GR` selected `num_marche,annee_de_notification`, limit 100; encoded URL is `liveRequests[6].url`. It returned **six** long references: `20242024S05079`, `20242024S05075` (2024), then `2025S029150000`, `2025F026480000`, `2025S015900000`, `2025F026500000` (2025). No queried short ID or CASVP component appeared. The list covers markets since 2013 above €25,000 HT; that scope does not establish linkage or wider uniqueness.

## Rights and next evidence needed

Per [`../docs/data-sources.md`](../docs/data-sources.md), Ministry DECP is Licence Ouverte v2.0 (Ministère de l’Économie), BOAMP is Licence Ouverte 2.0 (DILA/BOAMP), and consolidated feeds are `lov2` (Colmo/decp.info and underlying publishers). Direct Atexo metadata says `notspecified`; that licence is not established by the consolidation label.

Paris metadata declares **ODbL**. Attribute Ville de Paris / Paris Open Data; retain that declaration for the scalar extract. Database reuse may carry attribution/share-alike obligations. These labels do not clear personal data or third-party content, or establish the schema repository's licence.

Promotion requires an authoritative exact full-reference + DECP-ID + buyer link with an unambiguous lot/contract, or a publisher specification defining the transformation and scope. A full reference in a feed could suffice without a global stripping rule. Direct Atexo files remain the main inspection gap.
