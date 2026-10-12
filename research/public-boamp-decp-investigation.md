# Public-only investigation of nine BOAMP ↔ DECP candidates

## Scope and outcome

Reviewed `data/boamp-decp-links.json`, current normalized records, and exact retained BOAMP eForms bodies. **The supplied nine pairs contain six distinct notices and seven notice/lots, not seven distinct notices.** All six occur exactly once in the retained raw file; all seven lots were inspected. No seventh notice was invented or substituted.

**No exact-reference link confirmed.** Five pairs now have explicit Paris reference-pattern evidence beyond the original holder/date heuristic; two Nantes pairs remain lot-compatible but have no identifier bridge; two mappings are disfavored by explicit notice lot/reference evidence. Neither disfavored mapping is declared a proven different legal contract. No dataset edits or new normalization rule are authorized by this report.

The substantive progress is identifying repeated-year and terminal-`0000` Paris reference patterns, a compound two-buyer reference, and Nantes' actual technical-to-printed-lot mapping. These are not permission to strip prefixes/suffixes globally or to equate differently formatted references without an authoritative crosswalk. BOAMP local `CON`, `TEN`, `RES`, and `LOT` identifiers do not equal DECP contract identifiers. Equal holder, date, description, CPV or amount is never sufficient proof.

The investigation did not modify normalized records or scoring, and sent no buyer requests. Its findings were subsequently exposed through the public evidence ledger and explorer annotations, without promoting any link or resolving an amount. Contacts, raw live bodies and incidental personal information remain outside the repository; minimized scalar extracts and acquisition metadata are documented in `docs/public-evidence.md`.

## Snapshot provenance

SHA-256 of exact input bytes at inspection (matching the link artifact's normalized/raw input hashes):

| File | SHA-256 |
|---|---|
| `data/boamp-decp-links.json` | `a950c17bc95f368731aa1eea8cdb3d4dac8cf4a9ed5c33a0a2bb62e42ff4e8a4` |
| `data/contracts.json` | `a02b90a427d9310ec57b6b2a7b18c21d9c999f8ebba0542835c7161a6cdf6400` |
| `data/decp-history.json` | `80543b398f8d590157972eb52c0812ff483f13124e2fdf3d3c59120cbddee89e` |
| `data/decp-cities.json` | `6fad886084537beacf0be219c612a5ad704869a08ff7fc36d87abfc14fc66e04` |
| `data/boamp-raw.json.gz` | `e6839c41712d0001c33d200efc9fd31042b280a7dc5f1ac0601ca6acd1f66f9d` |

## Public fetch protocol and limits

**14 requests total:** nine exact Ministry queries, two Nantes buyer open-data exports, three TED exact-string searches. Each returned HTTP 200. Each transfer used HTTPS only, a 5-second connection timeout, 15-second total transfer timeout, 2 MiB body limit, no redirects, no retries, and an 18-second enclosing process deadline. No challenges were bypassed, authentication used or requests sent to buyers. No additional network requests were made after the ceiling.

Private evidence directory: `~/.cache/contract-signals/public-boamp-decp-investigation/` (0700; evidence files 0600). `manifest.json` preserves exact URLs, UTC retrieval times, status, body length and SHA-256; the dated manifest, not an inferred wall-clock date, timestamps the live evidence. `summary.json` is the machine-readable minimized pairing inventory. BOAMP statements below describe the retained snapshot, not a newly fetched notice version.

Nantes exports fetched:

- 2024: <https://data.nantesmetropole.fr/api/explore/v2.1/catalog/datasets/244400404_marches-publics-conclus-2024-nantes/exports/json> — 387 rows, no exact target notice reference recovered.
- 2025: <https://data.nantesmetropole.fr/api/explore/v2.1/catalog/datasets/244400404_marches-publics-conclus-2025-nantes/exports/json> — 442 rows. Relevant rows detailed below. These are buyer-published data, **not signed contract documents or an explicit BOAMP↔DECP crosswalk**.

TED searches: POST <https://api.ted.europa.eu/v3/notices/search>, with `limit:10`, `fields:["publication-number","notice-title","notice-identifier"]`, `scope:"ALL"`, `checkQuerySyntax:true`, and respective `query` values `FT ~ "2024-88480"`, `FT ~ "20242024S05075"`, `FT ~ "2025F026500000"`. All responses had `/notices:[]`, `/totalNoticeCount:null`, `/timedOut:false`. **Correction from the subsequent official OpenAPI review:** `checkQuerySyntax:true` checks syntax without executing the query. These were syntax checks, not executed full-text searches or zero-hit results, and provide no evidence of TED absence. No TED version or signed public document was acquired in this initial pass. The later exact-identity investigation is documented in `paris-ted-link-review.md`. Generic Paris buyer-profile URI <https://marches.maximilien.fr> appears in retained notices; no exact downloadable document URL was available from those fields, and generic/challenge-prone browsing was not pursued.

## Field locators and semantic rules

All array indices below are zero-based JSON pointers. In `data/boamp-raw.json.gz`, `/records/{i}/donnees` is a JSON-encoded **string**. Decode it first; the following aliases are exact JSON pointer prefixes into that decoded object:

- **B** = `/EFORMS/ContractAwardNotice`
- **N** = `/EFORMS/ContractAwardNotice/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/efext:EformsExtension/efac:NoticeResult`

`B`/`N` notation is concatenation, not a literal JSON pointer or wildcard. Singleton objects have no `/0`; arrays do. The mappings below were resolved through `LotResult → TenderLot / SettledContract / LotTender` IDs, not neighboring array positions.

| Notice | Raw row | Normalized `data/contracts.json` row | LotProject pointer after B | SettledContract / LotResult / LotTender pointers after N |
|---|---:|---:|---|---|
| 25-21317 LOT-0001 | 2322 | 1679 | `/cac:ProcurementProjectLot/0` | `/efac:SettledContract/0`, `/efac:LotResult/0`, `/efac:LotTender/0` |
| 25-21329 LOT-0001 | 2325 | 1091 | `/cac:ProcurementProjectLot` | `/efac:SettledContract`, `/efac:LotResult`, `/efac:LotTender` |
| 25-34782 LOT-0003 | 5331 | 151 | `/cac:ProcurementProjectLot/1` | `/efac:SettledContract/1`, `/efac:LotResult/1`, `/efac:LotTender/1` |
| 25-34782 LOT-0006 | 5331 | 1749 | `/cac:ProcurementProjectLot/4` | `/efac:SettledContract/4`, `/efac:LotResult/4`, `/efac:LotTender/4` |
| 25-37616 LOT-0001 | 5981 | 2626 | `/cac:ProcurementProjectLot` | `/efac:SettledContract`, `/efac:LotResult`, `/efac:LotTender` |
| 25-45958 LOT-0005 | 7653 | 528 | `/cac:ProcurementProjectLot/4` | `/efac:SettledContract/4`, `/efac:LotResult/4`, `/efac:LotTender/4` |
| 25-47556 LOT-0001 | 8022 | 1418 | `/cac:ProcurementProjectLot/0` | `/efac:SettledContract/0`, `/efac:LotResult/0`, `/efac:LotTender/0` |

Append these exact suffixes to the relevant pointer:

- SettledContract: `/efac:ContractReference/cbc:ID` = published reference; `/cbc:ID/#text` = notice-local CON ID; `/cbc:IssueDate` = contract conclusion date; `/cbc:AwardDate` = award decision date when present; `/efac:LotTender/cbc:ID` = tender relationship.
- LotResult: `/efac:TenderLot/cbc:ID`, `/efac:SettledContract/cbc:ID`, `/efac:LotTender/cbc:ID` = explicit relationship fields; `/efac:FrameworkAgreementValues/cbc:MaximumValueAmount/#text` = framework maximum, **not PayableAmount**.
- LotTender: `/cac:LegalMonetaryTotal/cbc:PayableAmount/#text`, sibling `/@currencyID` = retained winning-tender amount if present, not necessarily a paid invoice or guaranteed spend.
- LotProject: `/cbc:ID/#text` = technical LOT ID; `/cac:ProcurementProject/cbc:ID` = printed/internal lot number; `/cac:ProcurementProject/cbc:Note/#text` = amount narrative; `/cac:ProcurementProject/cac:MainCommodityClassification/cbc:ItemClassificationCode/#text` = lot CPV; `/cac:ProcurementProject/cac:PlannedPeriod/cbc:DurationMeasure/#text` with `/@unitCode` = initial period.
- Notice: `B/cbc:IssueDate` is notice issuance, **not** contract conclusion; `/records/{i}/dateparution` is BOAMP publication; `B/cbc:ContractFolderID` is procedure UUID, not contract number.

For each fetched Ministry response, `/results/{i}/id`, `/acheteur_id`, `/objet`, `/codecpv`, `/datenotification`, `/datepublicationdonnees`, `/montant`, `/dureemois`, `/formeprix`, `/source` are the exact fields. Notification, award, conclusion, notice issuance and publication are separate events even where their calendar dates coincide. Ministry `montant` is a declared contract amount, not demonstrated expenditure; price form and framework context can make flat comparisons misleading. Do not add co-holder or alternative rows. All amounts below are EUR. Narrative `HT` means excluding tax; no tax basis is inferred merely from PayableAmount. CPVs compare eight-digit codes, not the DECP check digit.

## Pair 1 — 25-21317 LOT-0001 ↔ Paris 2024S05075

- Buyer SIRET: `21750001600019`.
- BOAMP: <https://www.boamp.fr/pages/avis/?q=idweb:25-21317>.
- Exact Ministry URL: <https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records?where=acheteur_id%3D%2721750001600019%27+AND+id%3D%272024S05075%27&limit=100>.
- Normalized pointers: `data/contracts.json /1679`; `data/decp-history.json /581` (`/contractId`, `/cpv`, `/amount`, `/amountSources`, `/initialAlternatives`).
- Notice chain: LOT-0001 → RES-0001 → CON-0001 / TEN-0001. Published reference `20242024S05075` at `N/efac:SettledContract/0/efac:ContractReference/cbc:ID`, versus live `/results/0/id` and `/results/1/id` = `2024S05075`. Literal equality fails; removing one leading `2024` would recover the DECP ID, but that is an observed pattern, not a documented identifier rule.
- Dates: award `2024-06-13+02:00`; conclusion `2024-07-10+02:00`; Ministry notification `2024-07-10`; BOAMP publication `2025-02-26`; Ministry data publication `2024-11-24` (both live rows).
- CPV: BOAMP `50530000`, DECP `50530000-9` (repair/maintenance machinery family).
- Amount: BOAMP PayableAmount absent, normalized amount null. `N/efac:LotResult/0/efac:FrameworkAgreementValues/cbc:MaximumValueAmount/#text` = 200,000. Lot note explicitly gives 20,000 HT minimum / 200,000 HT maximum over a firm 48 months. Live Ministry `/results/0/montant` = 65,029 and `/results/1/montant` = 200,000; both same reference/date. Current normalized amount 200,000. No chronology/supersession establishes that 65,029 is wrong; it must not be compared to a nonexistent BOAMP tender amount.
- **Conclusion: identifier-supported, unconfirmed.** Explicit reference and lot evidence supports this candidate more than pair 2; no authoritative repeated-year crosswalk or exact equality obtained.

## Pair 2 — 25-21317 LOT-0001 ↔ Paris 2024S05079

- BOAMP URL and buyer as pair 1.
- Exact Ministry URL: <https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records?where=acheteur_id%3D%2721750001600019%27+AND+id%3D%272024S05079%27&limit=100>.
- Normalized pointers: `data/contracts.json /1679`; `data/decp-history.json /583`.
- LOT-0001 explicitly declares `20242024S05075`, **not** `20242024S05079`. Within the same notice, `N/efac:LotResult/1/efac:TenderLot/cbc:ID` = LOT-0003 and `/efac:SettledContract/cbc:ID` = CON-0003. `N/efac:SettledContract/1/efac:ContractReference/cbc:ID` = `20242024S05079`, with `/efac:LotTender/cbc:ID` = TEN-0003. `B/cac:ProcurementProjectLot/2/cac:ProcurementProject/cbc:ID` = `Lot 3`. Thus the candidate points to a different notice-local award than the one carrying its reference pattern.
- Dates equal pair 1: award June 13; conclusion/notification July 10, 2024; notice publication February 26, 2025; Ministry publication November 24, 2024. Equality cannot overcome the lot/reference distinction.
- CPVs also equal pair 1. Live `/results/0/montant` = 86,636; `/results/1/montant` = 150,000. Current normalized amount 150,000. BOAMP LOT-0001 has no PayableAmount and a 200,000 ceiling; LOT-0003 explicitly has 30,000 HT minimum / 150,000 HT maximum over firm 48 months at `B/cac:ProcurementProjectLot/2/cac:ProcurementProject/cbc:Note/#text` and maximum at `N/efac:LotResult/1/efac:FrameworkAgreementValues/cbc:MaximumValueAmount/#text`.
- **Conclusion: disfavored/wrong notice-lot candidate.** Explicit notice structure directs the `…S05079` pattern to LOT-0003, not LOT-0001. This establishes distinct notice-local contracts/references, **not yet a proven legal-contract distinction between the differently formatted BOAMP and DECP identifiers**. A global strip-prefix rule or automatic reassignment is not justified.

## Pair 3 — 25-21329 LOT-0001 ↔ Paris 2025S01590

- Buyer `21750001600019`; BOAMP <https://www.boamp.fr/pages/avis/?q=idweb:25-21329>.
- Ministry: <https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records?where=acheteur_id%3D%2721750001600019%27+AND+id%3D%272025S01590%27&limit=100>.
- Normalized pointers: `data/contracts.json /1091`; `data/decp-history.json /1567`.
- LOT-0001 → RES-0001 → CON-0001 / TEN-0001. Singleton `N/efac:SettledContract/efac:ContractReference/cbc:ID` = **`2025S015900000 / 2025HA0001GR`**, not `2025S01590`. The first component contains DECP ID plus `0000`; the second is a separate published CASVP-related reference. Do not collapse both into the Paris contract.
- Dates: award `2025-02-05+02:00`; conclusion `2025-02-14+02:00`; notification February 14; BOAMP publication February 26; Ministry publication March 2.
- CPVs differ: BOAMP `50324100` (system maintenance), DECP `72267000-4` (software maintenance/repair). This may reflect scope/classification differences, not proof of different contract.
- `N/efac:LotTender/cac:LegalMonetaryTotal/cbc:PayableAmount/#text` = 2,382,511, also framework maximum. Lot note provides Paris fixed part **155,200 HT**, purchase-order ceiling **2,000,000 HT**, no minimum; CASVP fixed part **27,311 HT**, purchase-order ceiling **200,000 HT**, no minimum. Sum of the four declared components is 2,382,511. Paris alone is 2,155,200, the normalized DECP `/1567/amount` and retained buyer-feed amount; live Ministry `/results/0/montant` is 155,200, the Paris fixed component. These are directly narrative-supported monetary scopes, not a numeric match used to prove identity.
- **Conclusion: identifier-supported compound-reference candidate, unconfirmed.** Public text substantially explains the cross-source amount gap and two-buyer perimeter. No exact reference/crosswalk proves the shortened first component equals the DECP contract.

## Pair 4 — 25-34782 LOT-0003 ↔ Nantes 2025F00012

- Buyer `21440109300015`; BOAMP <https://www.boamp.fr/pages/avis/?q=idweb:25-34782>.
- Ministry: <https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records?where=acheteur_id%3D%2721440109300015%27+AND+datenotification+%3E%3D+%272024-01-01%27+AND+datenotification+%3C+%272026-01-01%27+AND+id%3D%272025F00012%27&limit=100&order_by=datenotification+asc%2Cid+asc>.
- Normalized pointers: `data/contracts.json /151`; `data/decp-cities.json /1512`, including `/procedureGroup` (identifier reused by another normalized member), `/sourceRowVariants/0/id` and `/amountSources`.
- **Technical LOT-0003 is printed Lot 2, LAVERIE**, at `B/cac:ProcurementProjectLot/1/cac:ProcurementProject/cbc:ID` and `/cbc:Name/#text`. It resolves to RES-0002 / CON-0002 / TEN-0002 and published reference `2024-88480` at `N/efac:SettledContract/1/efac:ContractReference/cbc:ID`. It is not technical LOT-0002 (printed Lot 1, CUISSON), whose `N/efac:SettledContract/0/efac:ContractReference/cbc:ID` = `2024-88470`.
- Live Ministry `/results/0/id` = `2025F00012`; `/objet` expressly says CUISSON. CPVs: BOAMP LOT-0003 `39710000` (electrical domestic appliances), DECP `39141000-2` (kitchen furniture/equipment).
- Dates: notice conclusion `2025-02-06+01:00`; notification February 6; BOAMP publication March 28; Ministry data publication February 23. AwardDate absent in retained Nantes contracts.
- BOAMP PayableAmount absent; result framework maximum **565,000**. Current DECP amount **370,000**, live Ministry **466,339**. Nantes 2025 export `/321/reference_interne_du_contrat` = `2024_88478`, `/321/objet_du_marche` = CUISSON, `/321/montant_du_contrat_attribue` = 370,000, `/321/date_de_notification` = February 6; `/321/cpv_principal` lists `39710000,39713200,39141000`, `/321/duree_maximale_du_marche` = 48 and `/321/type_de_contrat` says framework with subsequent contracts. The portal reference is neither notice `2024-88470` nor notice `2024-88480`; punctuation normalization does not remove the differing digits.
- **Conclusion: disfavored/wrong notice-lot candidate, not proven different legal contract.** Notice-local LAVERIE versus CUISSON distinction and published references oppose this lot pairing. No public document ties the DECP ID or portal `2024_88478` authoritatively to either notice reference. Description/amount are context, not a replacement identity proof.

## Pair 5 — 25-34782 LOT-0003 ↔ Nantes 2025F00013

- Buyer and BOAMP as pair 4.
- Ministry: <https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records?where=acheteur_id%3D%2721440109300015%27+AND+datenotification+%3E%3D+%272024-01-01%27+AND+datenotification+%3C+%272026-01-01%27+AND+id%3D%272025F00013%27&limit=100&order_by=datenotification+asc%2Cid+asc>.
- Normalized pointers: `data/contracts.json /151`; `data/decp-cities.json /1513`.
- Same explicit LAVERIE printed Lot 2 / technical LOT-0003 chain and reference **`2024-88480`** as pair 4. Live `/results/0/id` = **`2025F00013`**, with no exact or structurally matching reference supplied. DECP object says LAVERIE, compatible with the notice lot but not enough to confirm identity.
- Dates: conclusion/notification February 6, 2025; BOAMP publication March 28; Ministry publication February 23. CPVs differ: BOAMP `39710000`; DECP `39713200-5` (washing/drying machines).
- BOAMP has no PayableAmount, framework ceiling 565,000. Normalized amount 415,000; live Ministry `/results/0/montant` = 479,757.40. Nantes 2025 `/434/reference_interne_du_contrat` = `20245012AC_CUISINE_BLANCHISSERIE`, `/434/objet_du_marche` = LAVERIE, `/434/montant_du_contrat_attribue` = 415,000; `/434/date_de_notification` = February 6; `/434/cpv_principal` = `39710000,39713200,39141000`; `/434/duree_maximale_du_marche` = 48; `/434/type_de_contrat` = framework with purchase orders. **The same portal reference also appears at `/323/reference_interne_du_contrat` for FROID**, notification February 5, amount 190,000. The portal reference is therefore not a unique lot identifier.
- **Conclusion: unconfirmed, better lot-compatible candidate than pair 4 but still missing an identifier bridge.** Public reference investigation narrows the right notice lot and exposes a nonunique portal reference; it does not establish `2024-88480 = 2025F00013`. No amount reconciliation or record reassignment warranted.

## Pair 6 — 25-34782 LOT-0006 ↔ Nantes 2025F00016-1

- Buyer `21440109300015`; BOAMP <https://www.boamp.fr/pages/avis/?q=idweb:25-34782>.
- Ministry: <https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records?where=acheteur_id%3D%2721440109300015%27+AND+datenotification+%3E%3D+%272024-01-01%27+AND+datenotification+%3C+%272026-01-01%27+AND+id%3D%272025F00016%27&limit=100&order_by=datenotification+asc%2Cid+asc>.
- Normalized pointers: `data/contracts.json /1749`; `data/decp-cities.json /1516`. **`-1` is our row suffix**, not part of official `2025F00016`.
- Technical LOT-0006 is **printed Lot 5, BLANCHISSERIE**, not Lot 6, at `B/cac:ProcurementProjectLot/4/cac:ProcurementProject/cbc:ID`. Chain RES-0005 / CON-0005 / TEN-0005; reference `2024-88486` at `N/efac:SettledContract/4/efac:ContractReference/cbc:ID` differs literally from DECP ID.
- Dates: conclusion `2025-02-05+01:00`, notification February 5, BOAMP publication March 28, Ministry publication February 23. CPVs: BOAMP `39710000`; DECP `39713200-5`.
- BOAMP PayableAmount absent, framework maximum 325,000. Normalized DECP amount 250,000; live `/results/0/montant` = 670,560. Nantes 2025 `/100/reference_interne_du_contrat` = `2024_8846`, `/100/montant_du_contrat_attribue` = 250,000, `/100/date_de_notification` = February 5, `/100/objet_du_marche` = BLANCHISSERIE, `/100/cpv_principal` = `39713200`, `/100/duree_maximale_du_marche` = 48. **`2024_8846` is not `2024-88486`**, even after replacing underscore with hyphen; inferring a missing digit is not exact evidence.
- Live exact DECP query returns two rows. `/results/1/id` also equals `2025F00016`, but `/objet` is printing a neighborhood journal, `/datenotification` = May 20, `/montant` = 2,724, `/codecpv` = `79810000-5`, duration 1 month. The endpoint selects the reused ID, not our uniquely identified `-1` row. No aggregation or arbitrary first-result assumption should be built into future matching.
- **Conclusion: unconfirmed lot-compatible candidate; identifiers remain unbridged.** Printed-lot mapping and nonmatching buyer portal identifier are now explicit. Neither truncated-looking portal reference nor equal holder/date/object proves this contract link.

## Pair 7 — 25-37616 LOT-0001 ↔ Paris 2025F02650

- Buyer `21750001600019`; BOAMP <https://www.boamp.fr/pages/avis/?q=idweb:25-37616>.
- Ministry: <https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records?where=acheteur_id%3D%2721750001600019%27+AND+id%3D%272025F02650%27&limit=100>.
- Normalized pointers: `data/contracts.json /2626`; `data/decp-history.json /1337`.
- LOT-0001 → RES-0001 → CON-0001 / TEN-0001. Singleton `N/efac:SettledContract/efac:ContractReference/cbc:ID` = **`2025F026500000`**; live `/results/0/id` = `2025F02650`. Four terminal zeros distinguish literal references; suffix removal not authoritatively documented.
- Dates: award `2025-03-18+02:00`; conclusion `2025-03-31+02:00`; notification March 31; BOAMP publication April 4; Ministry data publication April 6. CPVs BOAMP `22200000` / DECP `22200000-2` (newspapers/journals).
- BOAMP PayableAmount absent; singleton result framework maximum **13,220,000**. Note explicitly states firm 48 months: Paris 2,900,000 HT minimum / 13,220,000 HT maximum; EPPM 30,000 / 250,000 HT; CASVP 60,000 / 370,000 HT. Do not assume the displayed 13,220,000 encompasses all three buyers. Live Ministry `/results/0/montant` = **10**. Current normalized DECP amount **12,600,000**, also retained buyer-feed amount flagged `aberrant` at `/1337/amountSources/1/consolidatorFlag`; it does **not** equal notice Paris ceiling 13,220,000. The normalized `/verification/placeholder:true` is a processing assessment, not source-document proof that 10 is a placeholder. The notice supplies the ceiling, not a paid total or evidence to overwrite either DECP value.
- **Conclusion: identifier-supported suffix-pattern candidate, unconfirmed.** Public narrative improves amount/perimeter understanding but leaves both identity crosswalk and 12.6M-versus-13.22M discrepancy unresolved.

## Pair 8 — 25-45958 LOT-0005 ↔ Paris 2025S02915

- Buyer `21750001600019`; BOAMP <https://www.boamp.fr/pages/avis/?q=idweb:25-45958>.
- Ministry: <https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records?where=acheteur_id%3D%2721750001600019%27+AND+id%3D%272025S02915%27&limit=100>.
- Normalized pointers: `data/contracts.json /528`; `data/decp-history.json /1625`.
- LOT-0005 → RES-0005 → CON-0005 / **TEN-0006**, not TEN-0005. `N/efac:SettledContract/4/efac:ContractReference/cbc:ID` = `2025S029150000`; live `/results/0/id` = `2025S02915`. The exact chain prevents a neighboring-tender error. Four-zero suffix remains undocumented.
- Dates: award `2025-03-18+02:00`; conclusion `2025-04-09+02:00`; notification April 9; BOAMP publication April 24; Ministry data publication April 20. CPVs `90911200` / `90911200-8` (building cleaning).
- `N/efac:LotTender/4/cac:LegalMonetaryTotal/cbc:PayableAmount/#text` = **13,200,000**, current normalized amount in both sources. Live Ministry `/results/0/montant` = **3,300,000**. Lot note explicitly states **600,000 HT minimum / 3,300,000 HT maximum for 12 months**; `B/cac:ProcurementProjectLot/4/cac:ProcurementProject/cac:PlannedPeriod/cbc:DurationMeasure/#text` = 12, unit MONTH. DECP duration is 48 months. Thus 3.3M has explicit annual-maximum support and 13.2M equals four annual ceilings; that arithmetic is not itself evidence of renewal exercise or spend. Result maximum field is **absent** for this lot; do not substitute another lot's value or notice-wide 90,400,000 total.
- Prior notice citation at `N/efac:SettledContract/4/cac:NoticeDocumentReference/cbc:ID` = `723965-2024`. Public locator <https://ted.europa.eu/en/notice/-/detail/723965-2024> is a **retained citation, not fetched evidence of the award or its DECP crosswalk**.
- **Conclusion: identifier-supported suffix-pattern candidate, unconfirmed.** Annual versus four-year monetary scope is strongly supported as an explanation, not a final-spend or exact-link finding.

## Pair 9 — 25-47556 LOT-0001 ↔ Paris 2025F02648

- Buyer `21750001600019`; BOAMP <https://www.boamp.fr/pages/avis/?q=idweb:25-47556>.
- Ministry: <https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records?where=acheteur_id%3D%2721750001600019%27+AND+id%3D%272025F02648%27&limit=100>.
- Normalized pointers: `data/contracts.json /1418`; `data/decp-history.json /1335`.
- LOT-0001 → RES-0001 → CON-0001 / TEN-0001. `N/efac:SettledContract/0/efac:ContractReference/cbc:ID` = **`2025F026480000`**, live `/results/0/id` = `2025F02648`. Other notice lot has `2025F026490000` at settled-contract index 1; distinct published references prevent treating notice total as this lot's value.
- Dates: award `2025-04-07+02:00`; conclusion `2025-04-24+02:00`; notification April 24; BOAMP publication April 27; Ministry data publication May 4. CPVs `39370000` / `39370000-6` (water installations).
- PayableAmount at `N/efac:LotTender/0/cac:LegalMonetaryTotal/cbc:PayableAmount/#text` = **1,500,000**, also live Ministry amount and both normalized amounts. Lot note expressly states **100,000 HT minimum / 1,500,000 HT maximum over firm 48 months**. This demonstrates maximum basis rather than guaranteed purchasing/payment. In contrast `N/efac:LotResult/0/efac:FrameworkAgreementValues/cbc:MaximumValueAmount/#text` is **2,000,000**, identical to notice-wide overall maximum and repeated in the second lot result. Lot 2 PayableAmount is 500,000, and its note says 500,000 HT maximum. The duplicated 2M result field must not silently replace the lot-specific 1.5M; its scope is inconsistent with lot narrative.
- **Conclusion: identifier-supported suffix-pattern candidate, unconfirmed.** Amount semantics are explicit; numeric agreement is not used to prove the cross-source link.

## Consolidated conclusions and public-only remaining gates

| Pair | Public identifier finding | Conclusion |
|---:|---|---|
| 1 | Notice `20242024S05075`; DECP `2024S05075` | Repeated-year pattern; unconfirmed |
| 2 | Candidate LOT-0001 says `…S05075`; `…S05079` is explicitly LOT-0003 | Disfavored lot mapping; not proven different DECP legal contract |
| 3 | `2025S015900000 / 2025HA0001GR` versus `2025S01590` | Compound references / buyer scopes; unconfirmed |
| 4 | Candidate technical LOT-0003 is printed Lot 2, `2024-88480`; CUISSON is printed Lot 1, `2024-88470` | Disfavored lot mapping; no DECP crosswalk |
| 5 | LAVERIE `2024-88480` versus `2025F00013`; buyer portal parent/reference reused for FROID | Compatible lot, no identifier bridge |
| 6 | BLANCHISSERIE `2024-88486` versus `2025F00016`; portal `2024_8846` | Compatible lot, no identifier bridge; DECP ID reused |
| 7 | `2025F026500000` versus `2025F02650` | Suffix pattern; unconfirmed; 10/12.6M/13.22M bases unresolved |
| 8 | `2025S029150000` versus `2025S02915` | Suffix pattern; unconfirmed; annual maximum explicit |
| 9 | `2025F026480000` versus `2025F02648` | Suffix pattern; unconfirmed; firm-term lot maximum explicit |

The seven nondisfavored candidates are **not seven exact-reference confirmations**: only five have a visible Paris prefix/suffix/component relationship; Nantes pairs 5–6 remain merely lot-compatible after identifier investigation. Repeated formatting patterns are useful leads, but no publisher specification or exact document crosswalk was found to justify automatic equivalence. The two disfavored pairs should be reviewed separately from compatible candidates; a nonmatching declared reference is not automatically proof of another legal contract.

Further public-only progress would require an already published full-reference export, award decision/contract extract, profile metadata crosswalk, or exact TED version explicitly connecting each declared reference to its DECP ID and buyer/lot. Nantes particularly needs a public bridge between `2024-88480` / `2024-88486` and `2025F00013` / `2025F00016`; generic portal references cannot supply it. Paris needs an authoritative account of repeated-year / four-zero conventions and the compound-reference buyer scope. The request ceiling is exhausted; no further fetch is suggested as having occurred, and no buyer-contact workflow is substituted for documentary evidence.
