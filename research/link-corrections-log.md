# BOAMP–DECP link corrections: durable decision record

## Scope and status

Reviewer: **assistant-assisted**. Offline review of the current repository snapshot, including `data/public-link-evidence.json`, `research/public-link-observations.json`, retained raw BOAMP, normalized datasets, Paris reference-convention evidence and exact TED-version evidence. No new network requests were made.

**Exactly two investigation leads are dismissed**, in [`../data/boamp-decp-link-decisions.json`](../data/boamp-decp-link-decisions.json). This resolves the supported notice-lot candidate errors, not the underlying legal-contract identity question. Neither dismissal proves that the BOAMP and DECP records are different legal contracts. **No replacement link is confirmed**, no other candidate is promoted, and no amount/date is corrected. The raw nine-pair heuristic artifact is preserved for audit. A separately generated review overlay now exposes **seven active candidates and two dismissed leads** in the explorer, plus three verified TED notice versions and two unresolved HTTP-429 cases. Dismissed sources remain accessible under **Dismissed investigation leads**, not presented as active recommendations.

## Decision format and replay

The additive artifact uses `schemaVersion: 1`, `inputHashes` and a `decisions` array. Each decision records `boampId`, `decpId`, `disposition: "dismissed-notice-lot-candidate"`, `reason`, `boampRowSha256`, `decpRowSha256`, reviewer, source URLs, `replacementLinkConfirmed: false`, and scalar `evidence` entries.

Each evidence entry has `source` (repository file), `path` (exact JSON Pointer), optional `decode`, and `expected` (complete source scalar, not an excerpt). Indices are zero-based. For `data/boamp-raw.json.gz`, gunzip and parse JSON; if `decode` is present, resolve its `path`, parse that JSON-encoded string, then resolve the evidence `path` in that decoded object. Colons and `#text` are literal keys. This explicit decoded context avoids treating `/donnees` as an already parsed object. Public ledger `recordedFields` entries retain both the original response pointer and value; a pointer into that ledger is not a claim to retain the full live response.

Hashes are SHA-256. Input hashes cover exact file bytes, including compressed bytes for raw BOAMP, and **only**:

| Input | SHA-256 |
|---|---|
| `data/contracts.json` | `a02b90a427d9310ec57b6b2a7b18c21d9c999f8ebba0542835c7161a6cdf6400` |
| `data/decp-history.json` | `80543b398f8d590157972eb52c0812ff483f13124e2fdf3d3c59120cbddee89e` |
| `data/decp-cities.json` | `6fad886084537beacf0be219c612a5ad704869a08ff7fc36d87abfc14fc66e04` |
| `data/boamp-raw.json.gz` | `e6839c41712d0001c33d200efc9fd31042b280a7dc5f1ac0601ca6acd1f66f9d` |

Base links and observations are intentionally **not** input-hash dependencies, avoiding circularity. Replayable decision evidence is restricted to those four hash-bound inputs. Context in this report may cite other public artifacts, but it is not silently used as unbound decision evidence. Row hashes cover the **complete normalized row**, serialized as UTF-8 `json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, with no trailing newline. They are not raw-notice hashes. Only minimal nonpersonal identity/scope scalars are exposed; no supplier/contact personal names are copied.

## 1. Paris: wrong notice-local lot lead

Dismissed pair: `boamp-25-21317-lot-0001` ↔ `decp-21750001600019-2024S05079`.

- Normalized rows: `data/contracts.json#/1679`, `data/decp-history.json#/583`. Buyer SIRET `21750001600019`; DECP contract ID `2024S05079`.
- BOAMP row: `data/boamp-raw.json.gz#/records/2322`; decode `/records/2322/donnees`.
- Public notice: <https://www.boamp.fr/pages/avis/?q=idweb:25-21317>.
- Exact Ministry URL and its retained acquisition status/time/body hash: `research/public-link-observations.json#/liveRequests/1`; ID and amount extracts are under `/recordedFields`. The same URL is retained in the decision's `sourceUrls.decp`.
- Existing public assessment: `data/public-link-evidence.json#/pairs/1`, checked against raw and normalized rows rather than treated as independent ground truth.

Let **N** denote the decoded prefix `/EFORMS/ContractAwardNotice/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/efext:EformsExtension/efac:NoticeResult`. The decision artifact expands this prefix in every pointer.

| Decoded pointer suffix after N | Expected scalar |
|---|---|
| `/efac:SettledContract/0/efac:ContractReference/cbc:ID` | `20242024S05075` |
| `/efac:LotResult/0/efac:TenderLot/cbc:ID` | `LOT-0001` |
| `/efac:LotResult/0/efac:SettledContract/cbc:ID` | `CON-0001` |
| `/efac:LotResult/0/efac:LotTender/cbc:ID` | `TEN-0001` |
| `/efac:SettledContract/1/efac:ContractReference/cbc:ID` | `20242024S05079` |
| `/efac:SettledContract/1/cbc:ID/#text` | `CON-0003` |
| `/efac:SettledContract/1/efac:LotTender/cbc:ID` | `TEN-0003` |
| `/efac:LotResult/1/efac:TenderLot/cbc:ID` | `LOT-0003` |
| `/efac:LotResult/1/efac:SettledContract/cbc:ID` | `CON-0003` |
| `/efac:LotTender/1/efac:TenderLot/cbc:ID` | `LOT-0003` |

Decoded `/EFORMS/ContractAwardNotice/cac:ProcurementProjectLot/2/cbc:ID/#text` is `LOT-0003`; its `/cac:ProcurementProject/cbc:ID` is `Lot 3`. The title describes climate-management installations in horticultural greenhouses, also the scope of the normalized DECP description. LOT-0001 instead describes production-environment systems including watering. These explicit relationship fields, not neighboring array positions or equal dates/holders, identify the sibling reference.

**Incorrect/why:** the heuristic LOT-0001 lead ignored that the `…S05079` pattern is attached to a distinct notice-local LOT-0003/CON-0003/TEN-0003 chain. `20242024S05079` is nevertheless not literally `2024S05079`. This supports dismissing the LOT-0001 lead, **not** automatically assigning DECP to LOT-0003 or declaring legal-contract nonidentity. Removing the repeated year remains an unapproved transform.

Canonical row hashes:

- BOAMP normalized row: `c7c1b8560648a6bfd541af9bcd913a2c1dbec0ed1ac92d5b0f22d7875addf216`.
- DECP normalized row: `1ac797a8b732650df4154d0a8107e698206c3356b27f817536a6d0ecd49e20f8`.

## 2. Nantes: technical lot confused with printed lot/scope

Dismissed pair: `boamp-25-34782-lot-0003` ↔ `decp-21440109300015-2025F00012`.

- Normalized rows: `data/contracts.json#/151`, `data/decp-cities.json#/1512`. Buyer SIRET `21440109300015`; DECP contract ID `2025F00012`.
- BOAMP row: `data/boamp-raw.json.gz#/records/5331`; decode `/records/5331/donnees`.
- Public notice: <https://www.boamp.fr/pages/avis/?q=idweb:25-34782>.
- Exact Ministry URL/acquisition metadata: `research/public-link-observations.json#/liveRequests/3`.
- Buyer export URL/acquisition metadata: `research/public-link-observations.json#/liveRequests/10`, the official Nantes 2025 export at <https://data.nantesmetropole.fr/api/explore/v2.1/catalog/datasets/244400404_marches-publics-conclus-2025-nantes/exports/json>.
- Existing public assessment: `data/public-link-evidence.json#/pairs/3`.

In the decoded notice, **B** is `/EFORMS/ContractAwardNotice` and N is the same extension prefix as above. Full expanded pointers and expected title scalars are in the artifact.

| Decoded pointer | Expected scalar |
|---|---|
| B + `/cac:ProcurementProjectLot/1/cbc:ID/#text` | `LOT-0003` (technical lot) |
| B + `/cac:ProcurementProjectLot/1/cac:ProcurementProject/cbc:ID` | `Lot 2` (printed lot) |
| B + `/cac:ProcurementProjectLot/1/cac:ProcurementProject/cbc:Name/#text` | `Matériel de cuisine " LAVERIE "` |
| N + `/efac:LotResult/1/efac:TenderLot/cbc:ID` | `LOT-0003` |
| N + `/efac:LotResult/1/efac:SettledContract/cbc:ID` | `CON-0002` |
| N + `/efac:LotResult/1/efac:LotTender/cbc:ID` | `TEN-0002` |
| N + `/efac:SettledContract/1/efac:ContractReference/cbc:ID` | `2024-88480` |
| B + `/cac:ProcurementProjectLot/0/cbc:ID/#text` | `LOT-0002` |
| B + `/cac:ProcurementProjectLot/0/cac:ProcurementProject/cbc:ID` | `Lot 1` |
| B + `/cac:ProcurementProjectLot/0/cac:ProcurementProject/cbc:Name/#text` | `Matériel de cuisine " CUISSON"` |
| N + `/efac:SettledContract/0/efac:ContractReference/cbc:ID` | `2024-88470` |

The exact normalized `data/decp-cities.json#/1512/description` is `AC_Cuisine_blanchisserie - Matériel de cuisine « CUISSON»`. It has no personal names. Technical LOT-0003 is **not printed Lot 3**: it is printed Lot 2, LAVERIE. CUISSON belongs to technical LOT-0002, printed Lot 1. The buyer-export retained extract of original response `/321/reference_interne_du_contrat` is `2024_88478`; replacing underscore with hyphen would still not produce either `2024-88470` or `2024-88480`.

**Incorrect/why:** notice-local title, technical/printed lot mapping and reference chains oppose the CUISSON DECP candidate for LAVERIE. There is no authoritative public bridge from `2025F00012` or `2024_88478` to either BOAMP reference. Description compatibility is contextual evidence, not legal-contract identity proof. Do not automatically move this record to CUISSON, or promote the more lot-compatible `2025F00013` candidate.

Canonical row hashes:

- BOAMP normalized row: `c8366073b8199fb2cd4140e20a6f16a1715280425c2725b68336ab139ae5cfdc`.
- DECP normalized row: `0213e11210f095f1b4c023889532508b459d398e071f12fafdfa0845aae9de68`.

## Other findings retained without promotion

### TED: three exact notice versions, zero verified DECP links

`data/paris-ted-version-evidence.json` retains the bounded historical acquisition, not new requests from this task:

| BOAMP | TED award XML | Ledger pointer | Outcome |
|---|---|---|---|
| 25-21317 | <https://ted.europa.eu/en/notice/126421-2025/xml> | `/requests/12` | HTTP `200`, exact version `01` verified |
| 25-21329 | <https://ted.europa.eu/en/notice/129139-2025/xml> | `/requests/13` | HTTP `200`, exact version `01` verified |
| 25-37616 | <https://ted.europa.eu/en/notice/218409-2025/xml> | `/requests/14` | HTTP `429`, unresolved version |
| 25-45958 | <https://ted.europa.eu/en/notice/264382-2025/xml> | `/requests/15` | HTTP `429`, unresolved version |
| 25-47556 | <https://ted.europa.eu/en/notice/277338-2025/xml> | `/requests/16` | HTTP `200`, exact version `01` verified |

`/discoveries/5`, `/discoveries/6`, `/discoveries/9` each have `/tedVersionVerified: true`, `/expectedBOAMPVersion: "01"`, and `/exactCrosswalkForReview: false`. Their request `/evidence/exactAwardVersion` values are true. Notice UUID, procedure UUID and version were verified, not just a similar title or predecessor publication number. For Paris 25-21317 the exact notice UUID is `e1636ae4-00b5-4953-bb91-1326562ab9b2` and procedure UUID `7db0640e-05cd-480c-9b82-27190ec82767`. The three XMLs repeat long/compound references but furnish no long-to-short DECP crosswalk. **Three verified BOAMP–TED notice versions therefore yield zero verified BOAMP–DECP links.** The two 429 bodies are not notice evidence and remain unresolved; no retries or bypass are claimed.

### Corrected historical TED search interpretation

The original three FT requests in `research/public-link-observations.json#/liveRequests/11`, `/12`, `/13` used `/requestBody/checkQuerySyntax: true`. They were **syntax-only checks, not executed searches**. `/searchExecuted: false` and `/syntaxOnly: true` preserve that correction. Empty `/notices` cannot be interpreted as zero search results or evidence of TED absence. The official OpenAPI evidence is `data/paris-ted-version-evidence.json#/requests/10`, source <https://api.ted.europa.eu/api-v3.yaml>; its semantic locator is `/components/schemas/PublicExpertSearchRequestV1/properties/checkQuerySyntax/description`. Subsequent exact discovery used `checkQuerySyntax: false` at `/requests/11/requestBody/checkQuerySyntax`. The earlier five follow-up syntax queries also did not execute searches.

### Paris long references: temporary possible leads, not normalization

`data/paris-reference-convention-evidence.json` and `research/paris-identifier-convention.md` document buyer-list corroboration of six long references, with no authoritative DECP equivalence rule. The published Paris field `num_marche` means national-recensement number; it is not an explicit DECP ID. The Ministry 2.0.2 identifier schema describes a buyer-internal identifier of 1–16 characters but does not define repeated-year removal, terminal-zero removal or compound-reference splitting. Source schema: <https://raw.githubusercontent.com/139bercy/format-commande-publique/2.0.2/schema_decp_v2.0.2.json>, `/definitions/marche/definitions/IdentifiantMarche`.

Retain long identifiers verbatim as **temporary possible / unconfirmed** investigation leads: `20242024S05075`, `20242024S05079`, `2025F026500000`, `2025S029150000`, `2025F026480000`, and compound `2025S015900000 / 2025HA0001GR`. Do not auto-normalize their padding, strip the repeated year, collapse two buyer scopes, or silently reassign the rejected Paris pair. Direct Atexo resources remain unfetched because they exceeded the existing 2 MiB ceiling; their absence from inspection is not negative evidence.

### Amount semantics not corrected

The Paris rejected pair's normalized DECP amount is 150,000, while retained Ministry rows declare 86,636 and 150,000. LOT-0001 has no PayableAmount and a 200,000 framework ceiling; sibling LOT-0003 has a 150,000 ceiling. That does not establish DECP supersession or identity. Nantes LOT-0003 has no PayableAmount and a 565,000 ceiling; normalized DECP is 370,000, Ministry 466,339, and buyer export 370,000. No replacement value follows from the dismissal.

Elsewhere, the 3.3M annual maximum versus 13.2M four-ceiling comparison, the compound Paris/CASVP amount perimeter, 10/12.6M/13.22M unresolved bases and duplicated 2M result maximum remain explanations or discrepancies, not corrected amounts or proven spend. Framework maxima, winning-tender PayableAmount, fixed components, declared contract amounts and paid expenditure must remain separate.

## Future safeguards

1. Replay exact input hashes, unique normalized IDs, complete-row hashes and every expected scalar before using these decisions. If anything changes, require review; do not silently apply stale dismissals.
2. Follow explicit result→contract→tender→technical-lot IDs, not array positions or numeric similarity. Preserve singleton/list distinctions and technical versus printed lot labels.
3. Keep notice identity/version verification separate from legal-contract identity and DECP crosswalk verification. Reject predecessor substitution, fuzzy references, padding rules and amount/date/holder agreement as identity proof.
4. Require an authoritative public buyer+full-reference+DECP-ID+unique-lot bridge before any replacement or promotion. Check reused DECP IDs and nonunique buyer-portal references; do not aggregate alternatives or arbitrarily select the first returned row.
5. Record syntax-only checks separately from executed searches. Keep 429, unfetched oversized resources and other acquisition gaps unresolved rather than inferring absence or bypassing limits.
6. Preserve amount basis, tax/currency scope, buyer perimeter and date-event meaning. Identity review never authorizes changing amounts, dates or spend claims.
7. Keep the dismissal decision ledger independent of base-link/observation hashes. Its consumer overlay separately binds the raw heuristic artifact, the decision file and TED version evidence. Recompute ambiguity only among active leads; preserve the original warnings in the historical heuristic artifact. If a review overlay is missing/stale, the explorer warns that fallback heuristic leads may include dismissed candidates.

## Offline validation

The two decisions contain **62 primary scalar evidence pointers**, replayable against the four hash-bound public files. Input hashes and complete canonical row hashes are checked before dismissal; stale values fail closed. No network, commit or push was performed.

```sh
python tools/review-link-resolutions.py
python -m unittest discover -s tests -p test_review_link_resolutions.py
```

The generated `data/public-link-resolutions.json` is deterministic and requires no private cache. It keeps all nine original pair identities partitioned into active/dismissed sets, and revalidates TED header identities against the public BOAMP snapshot. UI regression tests ensure the dismissed leads are not reintroduced into the active display, verified TED notices are not presented as DECP confirmation, and unavailable/stale review artifacts do not silently hide leads.
