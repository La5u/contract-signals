# France: unresolved evidence inventory and unsent buyer requests

## Scope and counts

Retained checkout **09561d498f6904af49ac5339724035424cb97c07**; no fresh source check. Findings describe snapshots, not today's publications. No requests sent or data changed. Personal evidence stays private.

| Issue | Verified in current checkout | Interpretation / exact blocker |
| --- | ---: | --- |
| Dijon notice versus Ministry offers | **7 records** | Linked notice and DECP declarations differ; correct received-offer count unknown. Lot 16's current-register holder linkage remains incomplete. |
| Buyer feed versus Ministry offers | **5 records**: Dijon 2, Bordeaux 2, Grenoble 1 | Exact retained source fields differ; no linked RAO or signed buyer confirmation of count semantics. |
| Possible duplicates | **25 records in 10 clusters**: Dijon 10/4, Bordeaux 4/2, Grenoble 11/4 | These are flagged records, not 25 proven duplicate contracts or 25 clusters. No safely evidenced merge identified. |
| Dijon lot 8 | **1 notice award**, no DECP row in the three retained inputs | Coverage/linkage gap, not a zero-offer contract or proof of cancellation/nonexistence. |

Cohorts: **2,289 cities + 2,997 history = 5,286**. All **12** offer conflicts and **25** possible-duplicate flags are in cities; conflicted offers are null. These are not additional missing contracts. Amount `verification.status` does not verify offers/identity.

In-memory Dijon rerun: **29 scoped rows, 26 paired, 22 holder-linked, 7 offer disagreements, 26 notice results**. Scope is **27 project rows + 2 unrelated 2024VDPA66 contracts**; unpaired are those two and **2024VDPN0137**, explaining the older 27-row denominator.

Inputs: `data/decp-cities.json`, `data/decp-history.json`, `data/decp-cities-raw.json`, `data/decp-feeds-raw.json.gz`, `data/city-portals-raw.json.gz`. Hashes were checked against retained manifests; drift needs a new inventory.

Private root: `~/.cache/contract-signals/decp-conflict-dijon/`. Checked evidence: `official-discovery-20261008/` (six Ministry rows, two reference results, partial project search: 15 total); `project-notices-20261008/` (24-73828, 24-77579, 24-78296; 24-79759 from reference response); `holder-registry-20261008/`, `project-registry-20261008/` (**25** responses); `project-reconciliation.json`; later-lot-12 `cached-boamp-25-33856.json`; `lot8-check-20261008/` (**0** results). Parse `eforms_results`, not adjacent text/technical lot numbers. Current registry state alone is not historical identity.

Context: `research/decp-dijon-conflict-review.md`, `research/decp-identifier-collisions.md`, `research/france-cross-dataset-check.md`. Missing signed contracts, notifications, opening registers, RAOs and certified identifier crosswalks block resolution.

## A. Seven Dijon notice/DECP offer disagreements

Buyer **21210231300013**. Amounts are initial EUR declarations/lookup aids, not verified tax/spend totals. Dates are notifications, numerically matching notice conclusions; printed lots come from titles/reference checks.

| Printed lot | DECP ID / normalized suffix if split | Exact notice contract reference | Award notice | Notification | Amount EUR | DECP / notice offers |
| ---: | --- | --- | --- | --- | ---: | ---: |
| 7 | `2023VDAO1642` / `lot-7` | `2023vdao164207` | 24-79759 | 2024-06-27 | 668,893.00 | **2 / 4** |
| 12 (original 2024 award) | `2023VDAO1642` / `lot-12` | `2023vdao164212` | 24-79759 | 2024-06-27 | 168,127.96 | **2 / 5** |
| 20 | `2023VDAO1642` / `lot-20` | `2023vdao164220` | 24-79759 | 2024-06-27 | 155,995.41 | **2 / 3** |
| 14 | `2024VDAO1642` | `2024vdao164214` | 24-79759 | 2024-06-27 | 57,000.00 | **1 / 2** |
| 9 | `2024VDAO017009` | `2024vdao017009` | 24-77579 | 2024-06-27 | 623,086.00 | **5 / 6** |
| 24 | `2024VDAO017024` | `2024vdao017024` | 24-77579 | 2024-06-27 | 115,555.60 | **6 / 4** |
| 16 | `2024VDPA017116` | `2024vdpa017116` | 24-73828 | 2024-06-24 | 44,150.00 | **3 / 2** |

Notice totals use `tenders`, not subsets; all offers were electronic. AWS routes are not independent, so no chronology/majority/size tie-break. Six holders link; lot 16 lacks strict name/postcode linkage. Need its notification identity plus lot-specific RAO/opening totals/definitions, award/CAO extracts if applicable, corrections and original exports. Count populations are unknown; keep lot 12 separate from **2025** notice **25-33856**.

## B. Five feed/Ministry offer disagreements

These are content-linked fields, not independently verified contract references. Match buyer, retained holder, date, amount and normalized object; supplier IDs stay private.

| Buyer (municipal SIRET) | Normalized record ID | Date | Amount EUR | Ministry / feed offers | Retained feed ID; row index |
| --- | --- | --- | ---: | ---: | --- |
| Dijon (21210231300013) | `decp-21210231300013-2024VDPA02` | 2025-01-22 | 30,000.00 | **2 / 4** | `2024VDPA02`; 120–122 (three co-holder rows, not three count conflicts) |
| Dijon (21210231300013) | `decp-21210231300013-2025VDPA02-4` | 2025-09-16 | 549,260.60 | **4 / 3** | `2025VDPA02`; 211 |
| Bordeaux (21330063500017) | `decp-21330063500017-2024E004-3` | 2024-04-08 | 23,773.66 | **3 / 1** | AWS `2024E0`; 568; consolidator `2024E004`; 775 |
| Bordeaux (21330063500017) | `decp-21330063500017-2024E010-3` | 2024-08-19 | 184,818.20 | **3 / 5** | AWS `2024E0`; 506; consolidator `2024E010`; 780 |
| Grenoble (21380185500015) | `decp-21380185500015-2025A-5` | 2025-10-10 | 2,650.00 | **4 / 2** | `2025A`; 2251 |

Indices are zero-based in `data/decp-feeds-raw.json.gz` `records`. Route: AWS; Bordeaux `decp_colmo` agrees but is not documentary adjudication. Request full contract/lot references and crosswalk first, then RAO/count definitions. Normalized IDs are internal lookup aids, not buyer contract numbers; amount alone cannot establish linkage.

## C. Complete possible-duplicate inventory

IDs use `decp-{buyer}-{DECP ID}-{suffix}`. Equal holder/object/date/framework is a candidate heuristic, not proof of duplicate or separate contracts.

| Cluster | Buyer; DECP ID; record suffixes | Notification; amounts EUR in suffix order | Retained reference evidence / exact blocker |
| --- | --- | --- | --- |
| D1 | Dijon; `2024VDPA0464`; **1,2,3,4** | 2024-12-13; 3,500,000 / 4,000,000 / 5,500,000 / 7,000,000 | Scraped full refs `2024VDPA046404`, `…403`, `…402`, `…401` respectively; strong separate-lot candidate but holderless route linkage (see below). |
| D2 | Dijon; `2025VDAO04`; **3,4** | 2025-12-31; 63,900 / 231,700 | Ministry only for both; no buyer contract/lot references. Offers 4/5 do not settle identity. |
| D3 | Dijon; `2025VDPA02`; **2,3** | 2025-09-16; 39,666.66 / 111,282.94 | Ministry only; separate lot versus alternative amount unknown. |
| D4 | Dijon; `2025VDPA02`; **5,7** | 2025-09-16; 141,265 / 217,737.98 | Ministry only; same unresolved reference problem. Not the offer-conflict row `-4` in B. |
| B1 | Bordeaux; `2025E0`; **32,33** | 2025-06-25; 25,806.01 / 27,827.58 | Both map to portal ref `2025E008`; higher row also has that scraped ref. Same full reference supports possible versions, but offers 2/4 and amount differ; no version chronology or signed amount basis. |
| B2 | Bordeaux; `2025E0`; **36,37** | 2025-06-25; 44,339.76 / 56,500 | Both map to portal ref `2025E007`; offers 4/8. Route itself publishes two alternatives; cannot vote/select/merge by majority. |
| G1 | Grenoble; `23ASB2`; **5,6** | 2024-04-10; 240,000 / 320,000 | Scraped `23ASB248` and `23ASB249`; row `-5` also attaches `23ASB250` at 240,000 with a **different framework ID**. Holderless matching; verify whether multiple contracts collapsed into `-5`. |
| G2 | Grenoble; `25A`; **27,28,29** | 2025-10-22; 25,588.55 / 29,444.87 / 30,776.51 | Ministry only; lot/reference crosswalk missing; offers 6/8/4. |
| G3 | Grenoble; `25A`; **34,35** | 2025-12-16; 97,373.23 / 142,541.92 | Ministry only; durations 15/36 months and offers 5/6 differ, but versions versus separate contracts remains unknown. |
| G4 | Grenoble; `25A`; **36,37,38,39** | 2025-12-18; 48,000 / 100,000 / 480,000 / 2,800,000 | Ministry only; offers 5/5/7/8. Do not treat maximum/annual-looking ratios as documentary proof. |

**No safely evidenced merge or flag clearing.** Priority linkage gaps:

- **D1:** feed rows **368–371** carry **2024VDPA046401–404**, amounts **7M/5.5M/4M/3.5M**, same date/object, no framework, modification 0, but no holder IDs. `decp_feeds.Index.match` uses `amount-date-no-holder`. `resolve_duplicate_clusters` also requires one `(source,id)` pair per member; the 5.5M member has two. Removing that mechanical obstacle would not fix holder linkage.
- **G1:** holderless rows **2326–2328** carry `23ASB248`/`23ASB249` under framework `23ASB248`, and `23ASB250` under framework `23ASB250`. Amount/date matching attaches both 240,000 rows to `-5` without framework discrimination. Need contract/framework crosswalk; do not invent a third record.
- **B1/B2:** same-reference candidates need evidence of supersession and monetary basis before folding. Six other clusters lack non-Ministry references.

## D. Missing Dijon lot 8 / lot 6

Notice **24-77579** awards lot **8**, **2024vdao017008**, **559,742.62 EUR**, **6 offers**; case-insensitive ID/exact-amount checks find no row in the three raw inputs. This is bounded absence, not cancellation/nonexistence. Lot 6 **2024VDAO017006** has one confirmed supplier and an `unconfirmedHolders` entry associated with lot 8's winner; notice/feed support one winner. Mix-up is unproved.

Need both lots' signed/notification extracts, reference/holder-role crosswalk, lot-8 export/status and lot-6 corrections; termination/replacement only if it exists. Acceptance requires exact buyer/lot/reference/date/value-basis and private holder-role review. Do not synthesize DECP rows or an operation total.

## Action and resolution

- Owner verifies recipient/channel and requester details. Dijon: A, its two B rows, D, D1–D4; prioritize lot 14's 1/2 count, lot 16 identity, lot 8 and D1. Bordeaux: B rows 3–4/B1–B2. Grenoble: B row 5/G1–G4, especially framework mismatch.
- Store replies privately (**0700/0600**) with channel/date/version/locator/hash/scope. Refusal/absence is a blocker, not zero. Send no raw responses, registry files, supplier/personal identifiers or unredacted RAOs.
- Offers require exact identity and documented count/definition. Different populations stay separately labelled; corrections retain prior declarations. An unsupported assertion is not document confirmation.
- Duplicates need per-member crosswalk: distinct signed lots clear flags; explicit supersession permits a proposed fold preserving history; ambiguous parent refs retain flags. Dataset changes need a separate report/owner approval.

## UNSENT request drafts (French)

Owner adds identity/contact privately and verifies channel. Send only the commune's annex rows; normalized IDs are « repère interne de comparaison ». Common closing: « Des extraits occultés limités aux références, dates, totaux et définitions suffisent. Aucun nom de candidat non retenu, note, prix détaillé, solution technique ni dossier complet d'offre n'est demandé. Merci d'indiquer les documents indisponibles, motifs d'occultation/refus ou service détenteur. Cordialement, [Identité et coordonnées hors dépôt]. »

**Draft 1 — Dijon. Objet : Maison des Associations — offres et correspondance des lots 6 et 8**

Madame, Monsieur, pour la Commune de Dijon (SIRET 21210231300013), merci de communiquer les RAO/registres des sept lignes de l'annexe A, avec totaux et définitions (offres/soumissionnaires, variantes, remplacements, retraits/retards, recevabilité, négociation). Le lot 12 vise l'attribution 2024 (`2023vdao164212`, 24-79759), pas la relance 2025. Pour le lot 16, joindre une notification/décision confirmant `2024vdpa017116` (24-73828) ↔ DECP `2024VDPA017116`.

Pour les lots 6 (`2024vdao017006`) et 8 (`2024vdao017008`, 24-77579, 559 742,62 EUR, six offres), merci de fournir actes/notifications occultés, correspondance lots/références/rôles des titulaires, export DECP d'origine ou statut de publication du lot 8, et corrections du lot 6. Joindre les documents de fin/remplacement seulement s'ils existent; l'absence de ligne ne présume aucune annulation.

**Draft 2 — Commune concernée, annexe B. Objet : Références DECP et décompte des offres**

Madame, Monsieur, les lignes de votre commune en annexe B portent des nombres différents dans nos copies du Ministère et du profil acheteur. Les IDs pouvant être abrégés/réutilisés, merci de fournir un document/export liant marché complet, lot, procédure et DECP; dates/montants sont des repères. Après identification, fournir RAO/registres avec total et périmètre (offres/soumissionnaires, recevabilité, variantes, remplacement/retrait, négociation), corrections/exports datés et liens/extraits électroniques. Si les populations diffèrent, préciser leurs définitions.

**Draft 3 — Commune concernée, annexe C. Objet : Marchés, lots et versions DECP**

Madame, Monsieur, merci de fournir les documents existants distinguant marchés/lots et versions de l'annexe C : références complètes de marché, lot, procédure et accord-cadre parent, notification, base du montant (HT/TTC, initial/maximum/annuel, durée/reconductions), version/date d'export. Actes/notifications occultés, table de correspondance ou export daté conviennent. Pour une republication, préciser quelle déclaration remplace laquelle. Conserver seulement la précision de votre commune :

- Dijon D1–D4 : D1, confirmer les quatre lignes ↔ `2024VDPA046401–404`, notification du 13 décembre 2024.
- Bordeaux B1–B2 : `2025E008`/`2025E007` désignent-ils un marché, plusieurs lots ou des versions ?
- Grenoble G1–G4 : distinguer `23ASB248`, `23ASB249`, `23ASB250` de leurs accords-cadres; deux références à 240 000 EUR ont des parents différents.

## Reproduction

Read-only JSON/gzip, symmetric cluster, manifest and feed checks support this inventory. `tools/reconcile-dijon-project.py` main writes private output even without `--write-curated`; for read-only use import `project_rows`, `eforms_results`, `simple_results`, `reconcile` with verified saved responses.

```sh
python - <<'PY'
import json
from collections import Counter
for path in ('data/decp-cities.json', 'data/decp-history.json'):
    rows = json.load(open(path))
    by_id = {r['id']: r for r in rows}
    seen, clusters = set(), []
    for r in rows:
        if not r.get('possibleDuplicateOf') or r['id'] in seen:
            continue
        members = {r['id'], *r['possibleDuplicateOf']}
        for member in members:
            assert {member, *by_id[member]['possibleDuplicateOf']} == members
        assert not (members & seen)
        seen |= members
        clusters.append(members)
    conflicts = [r for r in rows if r.get('offersConflict')]
    assert all(r['offers'] is None for r in conflicts)
    print(path, 'rows', len(rows), 'offer conflicts', len(conflicts),
          'types', dict(Counter('notice' if 'notice' in r['offersConflict']
                                else 'feed' for r in conflicts)),
          'duplicate records', len(seen), 'clusters', len(clusters))
PY
```
