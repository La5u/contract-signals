# BOAMP–DECP link corrections: durable decision record

## Scope and status

Assistant-assisted offline review dismissed **exactly two investigation leads** in [`../data/boamp-decp-link-decisions.json`](../data/boamp-decp-link-decisions.json). The explorer overlay shows **seven active candidates, two dismissed leads, three verified TED notice versions and two unresolved HTTP-429 cases**. Dismissed sources remain under **Dismissed investigation leads**.

The nine-pair heuristic artifact is preserved. Neither dismissal proves different legal contracts or confirms a replacement. No other candidate, amount or date was changed.

## Evidence and replay

The decision artifact records exact pair IDs, disposition `dismissed-notice-lot-candidate`, reasons, source URLs, reviewer, complete expected scalars and hashes bound to `data/contracts.json`, `data/decp-history.json`, `data/decp-cities.json` and `data/boamp-raw.json.gz`; base links and observations are excluded to avoid circularity.

Pointers are zero-based. Gunzip raw BOAMP, then decode the specified `/donnees` JSON string before resolving evidence pointers; colons and `#text` are literal keys. Public observation pointers refer to retained extracts, not full live responses.

For the tables below, B = `/EFORMS/ContractAwardNotice`; N = `B/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/efext:EformsExtension/efac:NoticeResult`. The artifact expands every pointer.

## 1. Paris: wrong notice-local lot lead

Dismissed: `boamp-25-21317-lot-0001` ↔ `decp-21750001600019-2024S05079`.

- Rows: `data/contracts.json#/1679`, `data/decp-history.json#/583`; buyer `21750001600019`, DECP ID `2024S05079`.
- Raw notice: `data/boamp-raw.json.gz#/records/2322`, decode `/records/2322/donnees`; <https://www.boamp.fr/pages/avis/?q=idweb:25-21317>.
- Ministry acquisition: `research/public-link-observations.json#/liveRequests/1`, extracts under `/recordedFields`; previous assessment: `data/public-link-evidence.json#/pairs/1`.

| Explicit result chain | Published reference | Scope |
|---|---|---|
| LOT-0001 → CON-0001 → TEN-0001 | `20242024S05075` | Production-environment systems, including watering |
| LOT-0003 → CON-0003 → TEN-0003 | `20242024S05079` | Climate-management installations in horticultural greenhouses |

The sibling is printed **Lot 3**, at `B/cac:ProcurementProjectLot/2`. Its scope agrees with the DECP description. The explicit result/contract/tender IDs establish the notice-local relationship, rather than array adjacency, holder or date agreement.

**Reason:** the LOT-0001 lead ignored the distinct LOT-0003 chain carrying the `…S05079` pattern. But `20242024S05079` is not literally `2024S05079`. Dismiss LOT-0001 without moving DECP to LOT-0003 or stripping the repeated year.

## 2. Nantes: technical lot confused with printed lot/scope

Dismissed: `boamp-25-34782-lot-0003` ↔ `decp-21440109300015-2025F00012`.

- Rows: `data/contracts.json#/151`, `data/decp-cities.json#/1512`; buyer `21440109300015`, DECP ID `2025F00012`.
- Raw notice: `data/boamp-raw.json.gz#/records/5331`, decode `/records/5331/donnees`; <https://www.boamp.fr/pages/avis/?q=idweb:25-34782>.
- Ministry acquisition: `research/public-link-observations.json#/liveRequests/3`; buyer export: `/liveRequests/10`, <https://data.nantesmetropole.fr/api/explore/v2.1/catalog/datasets/244400404_marches-publics-conclus-2025-nantes/exports/json>; assessment: `data/public-link-evidence.json#/pairs/3`.

| Technical lot / printed lot | Title | Contract / tender | Reference |
|---|---|---|---|
| LOT-0003 / Lot 2 | `Matériel de cuisine " LAVERIE "` | CON-0002 / TEN-0002 | `2024-88480` |
| LOT-0002 / Lot 1 | `Matériel de cuisine " CUISSON"` | — | `2024-88470` |

The DECP description is `AC_Cuisine_blanchisserie - Matériel de cuisine « CUISSON»`. Technical LOT-0003 is printed Lot 2, LAVERIE, not printed Lot 3. The buyer export's `/321/reference_interne_du_contrat` is `2024_88478`; replacing its underscore would produce neither BOAMP reference.

**Reason:** titles, printed/technical lot mapping and reference chains oppose the CUISSON candidate for LAVERIE. No authoritative bridge joins `2025F00012` or `2024_88478` to either BOAMP reference. Do not move the record to CUISSON or promote the more compatible `2025F00013` candidate.

## Other findings

- **TED:** `data/paris-ted-version-evidence.json` verifies notice UUID, procedure UUID and version `01` for 25-21317, 25-21329 and 25-47556 (`/discoveries/5`, `/6`, `/9`). XMLs: <https://ted.europa.eu/en/notice/126421-2025/xml>, <https://ted.europa.eu/en/notice/129139-2025/xml>, <https://ted.europa.eu/en/notice/277338-2025/xml>. 25-37616 and 25-45958 remain unresolved after HTTP 429: <https://ted.europa.eu/en/notice/218409-2025/xml>, <https://ted.europa.eu/en/notice/264382-2025/xml>. Three verified notice versions yield **zero verified DECP links**; failure bodies are not notice evidence.
- **Search correction:** `research/public-link-observations.json#/liveRequests/11`, `/12`, `/13` and five early follow-up queries used `checkQuerySyntax:true`: syntax-only, not zero-result searches. Official evidence: `data/paris-ted-version-evidence.json#/requests/10`, <https://api.ted.europa.eu/api-v3.yaml>, `/components/schemas/PublicExpertSearchRequestV1/properties/checkQuerySyntax/description`. Executed discovery uses false at `/requests/11/requestBody/checkQuerySyntax`.
- **Paris references:** `data/paris-reference-convention-evidence.json` and `research/paris-identifier-convention.md` corroborate six long references in the buyer's list. `num_marche` means national-recensement number. Ministry 2.0.2 allows buyer-internal IDs of 1–16 characters but defines no stripping/splitting rule: <https://raw.githubusercontent.com/139bercy/format-commande-publique/2.0.2/schema_decp_v2.0.2.json>, `/definitions/marche/definitions/IdentifiantMarche`. Retain `20242024S05075`, `20242024S05079`, `2025F026500000`, `2025S029150000`, `2025F026480000` and `2025S015900000 / 2025HA0001GR` verbatim as unconfirmed leads. Direct Atexo exports exceeded the 2 MiB limit and remain uninspected.
- **Paris amounts:** rejected DECP row 150,000; Ministry alternatives 86,636 and 150,000; LOT-0001 has no PayableAmount and a 200,000 ceiling, sibling LOT-0003 a 150,000 ceiling. These establish neither supersession nor identity.
- **Nantes amounts:** LOT-0003 has no PayableAmount and a 565,000 ceiling; normalized DECP and buyer export are 370,000, Ministry 466,339. Dismissal supplies no replacement value.
- Other unresolved bases remain: 3.3M annual maximum versus 13.2M four-ceiling comparison; compound Paris/CASVP perimeter; 10/12.6M/13.22M; duplicated 2M result maximum. Keep maxima, PayableAmount, fixed components, declared amounts and paid expenditure separate.

## Future safeguards and validation

1. Replay unique IDs, input/row checks and all expected scalars before applying decisions; changed evidence requires review.
2. Follow explicit result→contract→tender→technical-lot IDs. Preserve singleton/list distinctions and printed lot labels.
3. Keep notice/version identity separate from contract identity. Replacement needs an authoritative buyer+full-reference+DECP-ID+unique-lot bridge; check reused IDs and nonunique portal references.
4. Keep syntax-only checks, 429 failures and oversized unfetched files explicit. Preserve monetary basis, currency/tax, buyer perimeter and date-event meaning.
5. Bind the consumer overlay separately to heuristic links, decisions and TED evidence. Recompute ambiguity among active leads; retain historical warnings. Missing/stale overlays must warn that fallback leads may include dismissed candidates.

The two decisions contain **62 primary scalar evidence pointers**. Replay fails closed on stale inputs. `data/public-link-resolutions.json` deterministically partitions all nine pairs and rechecks TED headers against BOAMP without a private cache.

```sh
python tools/review-link-resolutions.py
python -m unittest discover -s tests -p test_review_link_resolutions.py
```

UI regressions cover dismissed-lead exclusion, TED/DECP distinction and missing/stale overlays.
