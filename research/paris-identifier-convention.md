# Paris identifier convention — public-only investigation

## Finding and decision

**An authoritative Paris export publishes the exact long references, but an authoritative long-reference ↔ DECP-ID crosswalk or stripping specification was not obtained. No candidate has sufficient new linkage evidence.** This is a narrower and more informative finding than “only a visible formatting pattern”: the Ville de Paris itself publishes the same long references found in BOAMP. It still does not say which shortened DECP IDs they identify.

The Ministry's published **version 2.0.2 identifier specification** defines a buyer-internal string of 1–16 characters, not a rule to remove a repeated year or terminal `0000`. Both the 14-character long Paris references and 10-character DECP IDs meet those length constraints; validity is not equivalence. The compound BOAMP reference is a multi-reference declaration, not one DECP identifier. Its CASVP component must not be silently assigned to the Paris buyer.

Only new research files were created. No link artifact, dataset used by the explorer, UI, HANDOFF, common file, commit or push was changed by this investigation. Neither amount, date, holder/name, prefix/suffix nor broad similarity was used to establish identity.

## Reproduction and evidence boundaries

- Minimized ledger: [`../data/paris-reference-convention-evidence.json`](../data/paris-reference-convention-evidence.json). `repositorySnapshot` is reproducible; `liveRequests`, `liveScalars`, and `liveDocumentFindings` are dated acquisition assertions, not a claim of continuing endpoint contents.
- Offline inventory: `python tools/review-paris-reference-conventions.py` prints JSON, reads only public repository files, performs no network, writes no dataset, requires no private cache.
- Tests: `python -m unittest discover -s tests -p 'test_review_paris_reference_conventions.py' -v` (three passing tests).
- Raw newly acquired bodies, headers and acquisition helper are private local material outside the repository at `/tmp/paris-convention-work/` (directory 0700; acquisition bodies/headers/manifest 0600). Temporary local material is not a permanent archive. No contacts or raw source bodies were published.
- Exactly **8 new HTTP attempts**, all HTTP 200 and complete within bounds, no transport/HTTP failures. Each used HTTPS, 5-second connect timeout, 15-second total timeout, 2 MiB maximum body size, no redirects/retries, no authentication, contact or challenge bypass. The previous investigation's requests are not counted as new acquisitions here. No requests followed this task's eighth attempt.
- Response hashes describe exact saved response bytes. Attempt 2 was served gzip-encoded; its field pointers refer to JSON after gzip decoding, not compressed byte offsets. Scalar hashes use UTF-8 compact sorted-key JSON with `ensure_ascii=False`.

### Retained public snapshot provenance

| Input | Retrieval time in snapshot | SHA-256 of file bytes |
|---|---|---|
| `data/decp-feeds-raw.json.gz` | 2026-10-04T12:23:23+00:00 | `58a17d104540b29e734052dfdb1e9f12afd1bc6fa914e2852a9b76b0cfcda922` |
| `data/decp-history-raw.json.gz` | 2026-09-25T12:03:30.277162+00:00 | `d759bfaf97d468aa95fa15b4f0b7e657739ceb052b1b8f8afc731e1ad32b419e` |
| `data/boamp-raw.json.gz` | 2026-09-25T12:05:56.859285+00:00 | `e6839c41712d0001c33d200efc9fd31042b280a7dc5f1ac0601ca6acd1f66f9d` |
| `research/public-link-observations.json` | No retrieval time inferred; locator/assertion input | `a32df914852eb743533ba078e2ed9dd65a51c89794fa4a901a0d98f4c94ccf25` |

The feed is a **Colmo/decp.info third-party consolidation**, not a directly inspected Atexo buyer file. `/source/resource_url` identifies the public national parquet, `/source/sha256` its recorded acquisition hash, and `/source/retrieved_at` its acquisition time. The public extracted rows retain `id`, `uid`, `sourceDataset`, `sourceFile` and `acheteur_id`; those were inspected before relying on normalized IDs. A UID concatenating buyer+short ID+CPV is not a crosswalk to a BOAMP long reference. The ledger retains the exact source metadata and relevant Ministry pagination URLs under `repositorySnapshot`. After the TED syntax-only correction, this offline inventory was regenerated against the updated public observations file; all literal-reference findings remain unchanged.

## Retained row results (exact buyer `21750001600019`)

All row indices are zero-based. The following pointers are relative to `/records` in each named raw file; append `/id` and `/acheteur_id` for the exact DECP ID and buyer. Feed rows additionally preserve `/uid`, `/sourceDataset` = `atexo_maximilien`, and `/sourceFile`.

| Candidate | Notice / technical lot | BOAMP exact reference | DECP ID | Feed row | Ministry rows | New sufficient linkage? |
|---:|---|---|---|---:|---|---|
| 1 | 25-21317 / LOT-0001 | `20242024S05075` | `2024S05075` | 4139 | 634, 635 | No |
| 2 | 25-21317 / LOT-0001 | `20242024S05075` | `2024S05079` | 4141 | 638, 639 | No; sibling LOT-0003 carries `20242024S05079` |
| 3 | 25-21329 / LOT-0001 | `2025S015900000 / 2025HA0001GR` | `2025S01590` | 5139 | 1464 | No; buyer component unresolved |
| 7 | 25-37616 / LOT-0001 | `2025F026500000` | `2025F02650` | 4909 | 1589 | No |
| 8 | 25-45958 / LOT-0005 | `2025S029150000` | `2025S02915` | 5197 | 1615 | No |
| 9 | 25-47556 / LOT-0001 | `2025F026480000` | `2025F02648` | 4907 | 1689 | No |

**No exact long-reference scalar occurs in any retained feed or Ministry row for this buyer**, scanning all scalar fields, not just `/id`, for the six long Paris references plus `2025HA0001GR`. This bounded snapshot result does not prove absence in national parquet fields omitted from the public extraction, other buyers, historical versions or the direct publisher files. Multiple Ministry rows for the repeated-year candidates are retained, not treated as one unique contract merely because IDs match.

BOAMP exact decoded reference and notice-row pointers for all nine candidates are included in `repositorySnapshot/pairs`. Decode `/records/{i}/donnees` as JSON first. The published contract reference is under:

`/EFORMS/ContractAwardNotice/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/efext:EformsExtension/efac:NoticeResult/efac:SettledContract[/{i}]/efac:ContractReference/cbc:ID`.

The singleton/array distinction and explicit contract–tender–lot chains are documented in [`public-boamp-decp-investigation.md`](public-boamp-decp-investigation.md). Candidate 2 must not be reassigned automatically to the sibling lot. Candidates 4–6 are Nantes, outside the Paris convention search: candidate 4 remains disfavored, 5–6 remain lot-compatible but unbridged; no new Nantes finding or promotion is asserted. The five Paris-compatible candidates remain 1, 3, 7, 8, 9.

## Authoritative published sources

### 1. Atexo / GIP Maximilien direct resource catalogue

GET <https://www.data.gouv.fr/api/1/datasets/67272093922b37b9b2f1b653/>.

The exact dataset retained in feed `/sourceFile` pointers describes “Données essentielles du profil acheteur GIP Maximilien”; live `/organization/name` = `ATEXO - DECP`. `/schema` and relevant resource `/schema` fields are null. No convention/crosswalk specification is provided by this metadata.

The current catalogue resolves the two retained resource IDs:

- `/resources/4/id` = `ed3d8ced-fdb6-41e1-933d-c0a15984ad16`, title `decp-2024.json`, `/filesize` = **13,098,029**; `/url` = <https://static.data.gouv.fr/resources/donnees-essentielles-du-profil-acheteur-gip-maximilien/20261010-230446/decp-2024.json>.
- `/resources/6/id` = `ef2d35a1-a6d6-4301-badf-bd7f59ee0e0b`, title `decp-2025.json`, `/filesize` = **12,373,486**; `/url` = <https://static.data.gouv.fr/resources/donnees-essentielles-du-profil-acheteur-gip-maximilien/20261011-000449/decp-2025.json>.

**Not fetched:** both exceed the 2 MiB ceiling. No range slicing, compressed-download workaround or incomplete-export identity claim was attempted. These are live catalogue targets, not necessarily the same resource versions underlying the retained October 4 consolidation. Their content remains an explicit evidence gap, not a negative search result.

### 2. Ministry specification (not a Paris-specific normalization rule)

GET <https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides>. Decoded `/fields/0` describes `id` as “Numéro d'identification unique de marché public”. Dataset description links the official schema publication.

GET <https://schema.data.gouv.fr/139bercy/format-commande-publique/> links the technical **2.0.2** release for publication from January 1, 2024. Followed published links:

- <https://raw.githubusercontent.com/139bercy/format-commande-publique/2.0.2/_index.md>, line 9 (`Les marchés publics / id`): buyer-system internal number, 1–16 characters.
- <https://api.github.com/repos/139bercy/format-commande-publique/git/trees/2.0.2?recursive=1>, used to locate the exact schema filename, not as identifier evidence.
- <https://raw.githubusercontent.com/139bercy/format-commande-publique/2.0.2/schema_decp_v2.0.2.json>, `/definitions/marche/definitions/IdentifiantMarche`: string, `minLength:1`, `maxLength:16`, buyer-internal order number; warns against certain special characters. It specifies **no repeated-year / terminal-zero / compound-reference-to-DECP transformation**. Version 2.0.2 is pinned by tag and acquired body hash; tags are not claimed immutable.

### 3. Ville de Paris published national-recensement references

GET <https://opendata.paris.fr/api/explore/v2.1/catalog/datasets?where=search%28%22march%C3%A9s%22%29&limit=20> returned `/total_count:20`. The catalogue's `/results/5/dataset_id` = `liste-des-marches-de-la-collectivite-parisienne`. Its `/metas/default/description` labels “N° Marché” as **“Numéro national de recensement du marché”**. Its fields contain `num_marche`, but no exact buyer-SIRET/DECP-ID crosswalk fields. This is published field meaning, not an inferred padding convention.

One bounded records query selected **only** `num_marche,annee_de_notification`, with exact OR equality predicates for all six long Paris references, their six short counterparts and `2025HA0001GR`, limit 100. The complete encoded URL is `liveRequests[6].url` in the ledger; no broad text/name search was substituted. Endpoint:

<https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/liste-des-marches-de-la-collectivite-parisienne/records>.

| Response pointer | `num_marche` | `annee_de_notification` |
|---|---|---|
| `/results/0` | `20242024S05079` | `2024` |
| `/results/1` | `20242024S05075` | `2024` |
| `/results/2` | `2025S029150000` | `2025` |
| `/results/3` | `2025F026480000` | `2025` |
| `/results/4` | `2025S015900000` | `2025` |
| `/results/5` | `2025F026500000` | `2025` |

`/total_count:6`, all returned rows retained as minimized scalars. None of the queried short IDs or CASVP component was returned. This is an exact-reference corroboration of BOAMP by the buyer's published list, **not** an exact buyer+DECP-ID+unique-lot crosswalk. No guarantee of uniqueness outside this query or other catalogue datasets is inferred. Paris' published list covers markets since 2013 and describes publication above €25,000 HT; that selection threshold is not linkage evidence.

## New acquisition log

Exact URLs, UTC start/end times, HTTP status, curl exit, body byte count, failure fields and hashes are in `liveRequests`. All failure fields are null; no omitted failed attempts.

| Attempt | UTC start on 2026-10-11 | Source | Body bytes | SHA-256 |
|---:|---|---|---:|---|
| 1 | 10:09:03.841282 | Atexo dataset catalogue | 14,444 | `90cfa6e6a83224b3e6bba2a6900a9c6e90650670f08da106049671492eb0fd71` |
| 2 | 10:09:03.986520 | Ministry dataset metadata | 3,827 | `bac1a8af30c690894920984b6f9eb770e1437765711c1a072b2fd9e98fcb15cf` |
| 3 | 10:09:20.917023 | Paris catalogue | 256,400 | `8ac504cc0ce1a9f80b7d711fd26eddafa00ba570e674eb0b9d64a314652ffc8d` |
| 4 | 10:09:33.475225 | Official schema publication | 117,362 | `94f52a7224b4789583a3c212f23bba11bfd82f97f4cff34a13c4c299cb6d175b` |
| 5 | 10:09:52.599943 | Ministry 2.0.2 documentation | 15,930 | `235037781166d88256095f6b531161c9cb1544405f2585c1e4daf7b49fdb13da` |
| 6 | 10:09:52.874299 | Ministry schema tree | 6,589 | `68b7a41fed7ee993c9fd4c3828321071d57a5a7bf6a392ff258ef7e28e19edf7` |
| 7 | 10:09:53.250577 | Paris exact-reference records | 433 | `dbebb02945f3dabf3977757cf6777003b6f577d998e8b12bc84afb2b72570442` |
| 8 | 10:09:58.607917 | Ministry 2.0.2 JSON schema | 51,194 | `7e04e0bf1818befabd5d17c8b0078063bc7d03e3fcf5c464b3f7d6e68d85f9bd` |

## Rights, attribution and caveats

Per [`../docs/data-sources.md`](../docs/data-sources.md), retained Ministry DECP is **Licence Ouverte v2.0**, attributed to Ministère de l’Économie; retained BOAMP is **Licence Ouverte 2.0**, attributed to DILA/BOAMP, with incorporated third-party attachment and personal-data caveats; retained Colmo consolidated buyer feeds are **`lov2`**, attributed to Colmo/decp.info and the underlying publication routes. That consolidation label does **not** establish the licence of direct Atexo files: newly inspected Atexo `/license` is **`notspecified`**. Its raws are not republished.

New Paris catalogue metadata explicitly labels this list **Open Database License (ODbL)** at `/results/5/metas/default/license`. This was not an existing source-rights row in `docs/data-sources.md`; it is separately recorded live evidence. Attribute Ville de Paris / Paris Open Data. The tiny Paris-derived scalar extract retains that ODbL source declaration; it must not be represented as MIT or Licence Ouverte data, and ODbL attribution/share-alike obligations may apply to database reuse. No licence determination for the entire schema repository is inferred from a website footer; documentation/schema quotations here are minimized and source-linked. These labels do not clear privacy, third-party attachments or all incorporated-content rights.

## Remaining evidentiary gate

Sufficient evidence would be a published authoritative row/document linking the **exact** full reference to the **exact** DECP ID and buyer with an unambiguous lot/contract, or a publisher specification expressly documenting this transformation and its scope. An exact full reference in a retained or acquired feed may satisfy that gate without any global stripping rule, but none was recovered within this task's inspected evidence. Direct Atexo exports remain uninspected because of size. The Paris list now confirms what the long reference means; it does not finish the DECP bridge. **No promotion or general normalization is authorized.**
