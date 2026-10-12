# France: unresolved evidence inventory and unsent buyer requests

## Scope, checkout and verified counts

Read-only investigation against checkout `09561d498f6904af49ac5339724035424cb97c07` (initial working tree clean). This note is the only file created by this task. No dataset, importer, score, HANDOFF or common file changed; no external request, sending, commit or push. Findings describe retained snapshots, **not today's remote publication state**. Personal evidence stays outside the repository. This is assistant documentary review, not expert validation or a finding of wrongdoing.

| Issue | Verified in current checkout | Interpretation / exact blocker |
| --- | ---: | --- |
| Dijon notice versus Ministry offers | **7 records** | Linked notice and DECP declarations differ; correct received-offer count unknown. Lot 16's current-register holder linkage remains incomplete. |
| Buyer feed versus Ministry offers | **5 records**: Dijon 2, Bordeaux 2, Grenoble 1 | Exact retained source fields differ; no linked RAO or signed buyer confirmation of count semantics. |
| Possible duplicates | **25 records in 10 clusters**: Dijon 10/4, Bordeaux 4/2, Grenoble 11/4 | These are flagged records, not 25 proven duplicate contracts or 25 clusters. No safely evidenced merge identified. |
| Dijon lot 8 | **1 notice award**, no DECP row in the three retained inputs | Coverage/linkage gap, not a zero-offer contract or proof of cancellation/nonexistence. |

Current normalized cohorts: cities **2,289**, Paris/Ardèche **2,997**, combined **5,286**. Cities carry all 12 `offersConflict` fields and all 25 `possibleDuplicateOf` flags; history carries neither. **Every conflicted offer count is null.** Do not add the seven and five to missing/unknown counts as if they were additional contracts. `verification.status` describes amount/source agreement, not the truth of an offer count or identity.

The private Dijon reconciliation was independently rerun **in memory** using existing functions and saved inputs (no reconciler main/output write): **29 scoped rows, 26 uniquely paired, 22 holder-linked, 7 offer disagreements, 26 notice results**. The 29 comprise 27 project rows plus two unrelated contracts reusing `2024VDPA66`; the three unpaired entries are those two and project `2024VDPN0137`. This explains the older note's 27-row denominator; it is not a new contradiction.

## Evidence examined and provenance

Repository inputs and SHA-256 of exact bytes:

| Path | SHA-256 |
| --- | --- |
| `data/decp-cities.json` | `7a85985ea87fe363a1ecf5e00d8da4e9d2d2f2bfde30525e21bad8b614074c6d` |
| `data/decp-history.json` | `26b3fedc2daa5f504f1c472b60e6f17204c84a88413a2d24aa11612a6b0d3ef9` |
| `data/decp-cities-raw.json` | `0c708c533e8f5b95571ef17b5a9b65649a2af087d79ea6d6c76980e381dc59d7` |
| `data/decp-feeds-raw.json.gz` | `58a17d104540b29e734052dfdb1e9f12afd1bc6fa914e2852a9b76b0cfcda922` |
| `data/city-portals-raw.json.gz` | `886c14b864ebca15630b6ec7d0c524d2e073b098e79904084133b6fd6c96a5d7` |

Private evidence root: `~/.cache/contract-signals/decp-conflict-dijon/`. Do not attach its raw contents to public issues, outgoing drafts or exports.

- `official-discovery-20261008/`: saved Ministry exact query (six results), BOAMP procedure-reference search (two results), bounded project discovery (15 total; discovery not exhaustive). All three response hashes matched their manifest, status 200.
- `project-notices-20261008/`: exact responses for awards **24-73828, 24-77579, 24-78296**; each status 200, one result, hash matched. Original award **24-79759** comes from the exact procedure-reference response. Relationships were parsed with `eforms_results`, not guessed from adjacent text or technical lot numbers.
- `holder-registry-20261008/` and `project-registry-20261008/`: **25** saved registry responses checked against hashes/status and used for in-memory linkage. Current register state does not establish historic notification identity by itself.
- `project-reconciliation.json`: retained minimized pairing inventory; its counts agree with the in-memory reconstruction. `cached-boamp-25-33856.json` supplies the later lot-12 award, not a correction to the original award.
- `lot8-check-20261008/`: retained exact Ministry query response, status 200, manifest hash matched, **total_count 0**. No fresh API query made.
- Existing contextual notes: `research/decp-dijon-conflict-review.md`, `research/decp-identifier-collisions.md`, `research/france-cross-dataset-check.md`. Older integration-stage counts in those notes are historical, not current inventory totals.

No signed contracts, notification letters, opening registers, RAOs (*rapports d'analyse des offres*) or buyer-certified identifier crosswalk were acquired. Those are the substantive blockers, not missing software tests.

## A. Seven Dijon notice-versus-DECP offer disagreements

Exact municipal buyer: **Commune de Dijon, SIRET 21210231300013**. All amounts below are retained DECP initial declarations in EUR, locating aids only; they do not prove a universal HT/TTC or final-spend basis. Dates are DECP notification dates (notice conclusion dates agree numerically but are a different concept). Printed lot numbers are from titles/reference checks, **not** eForms technical IDs.

| Printed lot | DECP ID / normalized suffix if split | Exact notice contract reference | Award notice | Notification | Amount EUR | DECP / notice offers |
| ---: | --- | --- | --- | --- | ---: | ---: |
| 7 | `2023VDAO1642` / `lot-7` | `2023vdao164207` | 24-79759 | 2024-06-27 | 668,893.00 | **2 / 4** |
| 12 (original 2024 award) | `2023VDAO1642` / `lot-12` | `2023vdao164212` | 24-79759 | 2024-06-27 | 168,127.96 | **2 / 5** |
| 20 | `2023VDAO1642` / `lot-20` | `2023vdao164220` | 24-79759 | 2024-06-27 | 155,995.41 | **2 / 3** |
| 14 | `2024VDAO1642` | `2024vdao164214` | 24-79759 | 2024-06-27 | 57,000.00 | **1 / 2** |
| 9 | `2024VDAO017009` | `2024vdao017009` | 24-77579 | 2024-06-27 | 623,086.00 | **5 / 6** |
| 24 | `2024VDAO017024` | `2024vdao017024` | 24-77579 | 2024-06-27 | 115,555.60 | **6 / 4** |
| 16 | `2024VDPA017116` | `2024vdpa017116` | 24-73828 | 2024-06-24 | 44,150.00 | **3 / 2** |

**Established:** under these pairings the retained numerical declarations conflict. The notice total is `tenders`, not `t-esubm`, requests to participate or an SME subset. The retained review reports all offers electronic. AWS DECP and AWS eSender publication routes are not independent witnesses; chronology, majority, larger count or smaller count is not a safe tie-break.

**Unknown:** whether the fields count submissions, tenderers, admissible offers, variants, replacements, withdrawn/late offers or offers after negotiation; which published value needs correction. Six of these seven rows are register holder-linked; lot 16 is paired by reference/amount/date but lacks the strict current-register name/postcode link (closed establishment/different postcode in earlier review). Request notification/award identity for lot 16 alongside the RAO; do not present its cross-source identity as fully verified.

**Required evidence:** lot-specific RAO and opening/submission-register extract preserving aggregate counts and definitions; award decision or CAO extract if applicable; any existing correction and original DECP export/version. Original lot 12 must remain distinct from the **2025** relaunch in notice 25-33856.

## B. Five feed-versus-Ministry offer disagreements

Normalized IDs here identify our rows, **not** authoritative contract numbers. Feed references may also be truncated. Each feed comparison below was checked against retained initial rows on exact buyer, a retained holder identifier, date, initial amount and normalized object equality. Supplier identifiers were used locally only and are intentionally not reproduced.

| Buyer (municipal SIRET) | Normalized record ID | Date | Amount EUR | Ministry / feed offers | Retained feed ID; row index |
| --- | --- | --- | ---: | ---: | --- |
| Dijon (21210231300013) | `decp-21210231300013-2024VDPA02` | 2025-01-22 | 30,000.00 | **2 / 4** | `2024VDPA02`; 120–122 (three co-holder rows, not three count conflicts) |
| Dijon (21210231300013) | `decp-21210231300013-2025VDPA02-4` | 2025-09-16 | 549,260.60 | **4 / 3** | `2025VDPA02`; 211 |
| Bordeaux (21330063500017) | `decp-21330063500017-2024E004-3` | 2024-04-08 | 23,773.66 | **3 / 1** | AWS `2024E0`; 568; consolidator `2024E004`; 775 |
| Bordeaux (21330063500017) | `decp-21330063500017-2024E010-3` | 2024-08-19 | 184,818.20 | **3 / 5** | AWS `2024E0`; 506; consolidator `2024E010`; 780 |
| Grenoble (21380185500015) | `decp-21380185500015-2025A-5` | 2025-10-10 | 2,650.00 | **4 / 2** | `2025A`; 2251 |

Indices are **zero-based** in the pinned `data/decp-feeds-raw.json.gz` `records` array. Main feed route is `aws_marches-publics.info`; extra Bordeaux rows are `decp_colmo` and agree with the feed counts, but are not independent documentary adjudication. These are field contradictions within the retained content-based linkage, not five independently verified contract-reference links.

**Required evidence:** buyer's full contract/lot reference and crosswalk to the listed DECP ID/content, then the same aggregate RAO/opening-register evidence requested for A. Do not use amount alone to acquire a link or prefer the one-offer declaration for Bordeaux. Missing precise contract numbers are a blocker to treating this as an authoritative identity match.

## C. Complete possible-duplicate inventory

Notation: record IDs are `decp-{buyer SIRET}-{DECP ID}-{suffix}`. The suffixes below enumerate every flagged record exactly; buyer SIRETs are in B. Dates/amounts are lookup aids. Each cluster has equal holder set, object, notification date and framework under the importer's normalized candidate rule; differences in other fields **do not establish** distinct contracts or republications.

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

### Safely resolvable duplicates: none established; two prioritized linkage candidates

**No merge, deletion or flag clearing is authorized by this review.** Exact signed/notification evidence distinguishing contracts was not found for these ten clusters. A repeated amount/date/holder/object is only the candidate heuristic.

D1 has four distinct full references in exact retained documentary rows, but the references **are not yet exact holder-linked contract evidence**:

- Feed rows **368–371** (zero-based) publish `2024VDPA046401` through `…404`, with respective amounts **7M, 5.5M, 4M, 3.5M**, date 2024-12-13, equal normalized object, no framework and initial modification ID 0.
- Their holder identifiers are absent. `decp_feeds.Index.match` links them as **`amount-date-no-holder`**, not an exact contract reference or holder link. Buyer confirmation of four contract/lot identities or notification extracts is the next gate.
- Current `resolve_duplicate_clusters` also leaves D1 flagged because the 5.5M member has both AWS short and scraped full route references: its implementation requires exactly one `(source, id)` pair per member. This mechanical obstacle is distinct from the substantive holder-linkage gap; removing the mechanical obstacle alone would not establish identity.

G1 likewise has disjoint-looking full references, but all three scraped rows **2326–2328** are holderless. `23ASB248` (240,000) and `23ASB249` (320,000) use framework `23ASB248`; `23ASB250` (240,000) uses framework **`23ASB250`**. The matcher nevertheless attaches `23ASB250` to `-5` on amount/date without framework discrimination. Thus even that member's two references are not evidence of a single uniquely resolved contract. Request both the contract/framework crosswalk and the buyer notification documents; do not clear G1 or invent a third record from this observation.

B1/B2 are **same-reference candidates**, not safely proven duplicates. Need buyer documents identifying whether the two rows are versions, lots/subcontracts sharing a parent reference, or publication errors. A corrected export alone must specify supersession and monetary basis before anything is folded. Six other clusters lack any non-Ministry reference evidence for their members.

## D. Missing Dijon lot 8 and lot 6 linkage

- Award notice **24-77579**, printed lot **8**, reference **`2024vdao017008`**, winning-tender value **559,742.62 EUR**, notice total **6 offers**. The notice describes an award; it is not a payment or execution record.
- Retained Ministry query has zero results; offline exact buyer checks by case-insensitive ID **or exact amount** also found zero rows in `decp-cities-raw.json`, `decp-feeds-raw.json.gz` and `city-portals-raw.json.gz`. This is bounded snapshot absence, not an exhaustive search of every possible ID, buyer or publication date.
- Lot 6 `2024VDAO017006` currently has **one confirmed supplier identifier and one `unconfirmedHolders` entry**, not two confirmed holders. Earlier review relates the extra Ministry holder to the notice's lot-8 winner. The buyer feed and notice support one lot-6 winner; a data-entry mix-up is a hypothesis, not established fact.
- **Request:** redacted signed acte d'engagement / notification extract for **both lots 6 and 8**, official lot-to-contract reference/holder-role crosswalk, original buyer-profile DECP export with lot 8 or explanation of its publication identifier/status, and any correction of lot 6. Request any existing cancellation/termination/replacement decision only conditionally; do not assume one exists.
- **Acceptance gate:** exact municipal buyer + lot + contract reference and notification/date/value basis, independent holder/consortium role linkage reviewed privately, and publication-status evidence. Do not move the unconfirmed lot-6 holder into an invented lot-8 DECP contract, synthesize a Ministry record from the notice, or use the lot-8 value as an operation total.

## Action order and resolution protocol

1. Owner reviews these drafts and identifies the verified municipal procurement/administrative-document access channel. No contact addresses or claimed legal deadlines have been invented.
2. Dijon: send A plus B's two Dijon rows, D and D1–D4 as separate, bounded annexes. Priority: lot 14 (1/2 changes single-offer interpretation), lot 16 identity, missing lot 8, D1 full references.
3. Bordeaux: B's two rows plus B1/B2. Ask full references first, then aggregate RAO/row-version documents. Shared references are not enough to pick one value.
4. Grenoble: B's one row plus G1–G4. G1's framework mismatch needs priority; keep the full-contract and parent-framework identifiers separate.
5. Store any incoming evidence privately (directory 0700, files 0600), with date, source/channel, precise document/version/section, hash and request scope. Redact before producing a public extract; record refusals and absent documents as blockers, not numerical zeros.
6. Offer resolution requires exact lot/contract identity plus documentary aggregate count **and definition**. If sources count different populations, preserve separately labelled values rather than declaring one false. If a correction exists, retain old declaration and correction provenance. An unsupported buyer assertion can be recorded but is not the same as a document-confirmed count.
7. Duplicate resolution requires a per-member crosswalk: distinct signed references/lots => clear candidate flag without merging; explicit superseded version of the same contract => propose a fold preserving all alternatives/history; ambiguous parent reference => retain flags. Review holder identities privately, not in this note. Propose dataset changes in a separate report and obtain owner approval before applying.

## Privacy-safe, UNSENT buyer request drafts (French)

These drafts contain procurement references and aggregate data only. The owner must add an appropriate requester identity/contact privately and verify recipient/channel. **Do not attach raw DECP responses, registry files, supplier identifiers/names, personal contacts or unredacted RAOs.** No request for losing bidders' names, individual scores, detailed pricing or technical secrets is needed.

### Draft 1 — Dijon: RAO and lot-specific publication linkage

**Objet : Demande de documents administratifs — Maison des Associations, nombres d'offres et correspondance des lots 6 et 8**

Madame, Monsieur,

Nous comparons des déclarations publiques relatives aux marchés de la Commune de Dijon (SIRET acheteur 21210231300013), sans présumer d'une erreur ou d'une irrégularité. Pour les sept lignes de l'annexe A ci-dessus, les nombres publiés dans les DECP et les avis BOAMP diffèrent. Nous souhaiterions recevoir, dans leur partie communicable, les rapports d'analyse des offres et/ou extraits du registre d'ouverture permettant d'établir, pour chaque lot, le nombre total d'offres reçues et la définition du décompte (offres, soumissionnaires, variantes, remplacements, offres tardives ou retirées, offres recevables, phase de négociation). Un extrait limité aux références, dates, totaux et définitions serait suffisant. Nous ne demandons ni l'identité des candidats non retenus ni leurs notes ou prix détaillés.

La demande concernant le lot 12 vise l'attribution de 2024, référence `2023vdao164212` dans l'avis 24-79759, et non sa relance de 2025. Pour le lot 16, référence `2024vdpa017116` (avis 24-73828), merci de joindre un extrait communicable de la notification ou de la décision d'attribution confirmant la correspondance avec l'identifiant DECP `2024VDPA017116`.

L'avis 24-77579 mentionne également le lot 8, référence `2024vdao017008`, valeur publiée 559 742,62 EUR et six offres. Nous n'avons pas retrouvé sa ligne dans nos copies DECP. Merci de nous communiquer les extraits communicables des actes d'engagement/notifications des lots 6 (`2024vdao017006`) et 8, ainsi que tout document existant précisant leurs références de marché, dates, base des montants et rôles des titulaires/groupements. Une table de correspondance existante ou l'export DECP original du profil acheteur serait utile. Nous cherchons notamment à vérifier si la seconde qualité de titulaire déclarée au lot 6 relève de ce lot ou d'une autre référence ; nous ne présumons pas d'une confusion.

Si la publication du lot 8 utilise un autre identifiant, ou si une décision de correction, annulation, résiliation ou remplacement existe, merci d'indiquer la référence et de communiquer la partie accessible du document concerné. À défaut, l'absence de document ou de correspondance pourra simplement être précisée.

Nous acceptons l'occultation des données personnelles et secrets protégés. Merci de transmettre les documents par voie électronique ou d'indiquer leur lien officiel ; si seule une partie est communicable, cette partie suffit. Si un autre service détient ces documents, merci de nous orienter vers lui. Pour toute impossibilité de communication, merci de préciser le document concerné et le motif.

Cordialement,
[Identité et coordonnées à ajouter hors dépôt]

### Draft 2 — Each municipality: feed/Ministry counts and full contract numbers

**Objet : Demande de documents — correspondance des références DECP et décompte des offres**

Madame, Monsieur,

Pour les seules lignes de votre commune figurant à l'annexe B, nos copies des DECP du Ministère et du profil acheteur publient des nombres d'offres différents. Les identifiants peuvent être abrégés ou réutilisés ; les dates et montants joints servent uniquement à retrouver les lignes, pas à conclure qu'il s'agit d'un marché unique.

Pour chaque ligne, pourriez-vous communiquer tout document ou export existant donnant le numéro complet de marché, le lot éventuel, l'identifiant de procédure et la correspondance avec l'identifiant DECP ? Une fois cette correspondance précisée, nous sollicitons la partie communicable du rapport d'analyse des offres ou du registre d'ouverture indiquant le total reçu et son périmètre : offres versus soumissionnaires, recevabilité, variantes, remplacement/retrait et négociation. Tout document de correction des déclarations ou export daté permettant de comprendre la différence serait également utile.

Nous ne demandons pas les identités des candidats non retenus, leurs notes, leurs prix détaillés ou leurs solutions techniques. Des extraits occultés limités aux références et décomptes agrégés conviennent. Si les deux publications mesurent des populations différentes, merci d'indiquer les définitions plutôt que de choisir simplement l'un des deux nombres.

Merci d'indiquer les liens officiels ou de transmettre les extraits électroniquement, et de préciser les documents indisponibles ou les motifs d'une communication partielle/refus. La demande ne suppose ni anomalie ni irrégularité.

Cordialement,
[Identité et coordonnées à ajouter hors dépôt]

**Annex selection:** Dijon: B rows 1–2; Bordeaux: B rows 3–4; Grenoble: B row 5. Exclude our normalized ID from the buyer's authoritative-number field; label it « repère interne de comparaison » if retained.

### Draft 3 — Each municipality: duplicate/version/lot distinction

**Objet : Demande ciblée de documents — références de marchés, lots et versions des déclarations DECP**

Madame, Monsieur,

Pour les groupes de votre commune listés à l'annexe C, plusieurs lignes de nos copies publiques partagent un identifiant abrégé et une date mais présentent des montants ou d'autres champs différents. Nous ne savons pas s'il s'agit de marchés/lots distincts ou de versions successives d'une déclaration.

Pour chaque groupe, nous sollicitons les documents existants permettant la correspondance ligne par ligne : numéro complet de marché et de lot, référence de procédure, référence d'accord-cadre parent le cas échéant, date de notification, base du montant (HT/TTC, initial/maximum/annuel, durée et reconductions), et version/date d'export. Les extraits communicables de l'acte d'engagement ou de la notification, une table de correspondance existante, ou un export DECP daté conviendraient. En cas de correction ou de republication, merci de joindre le document existant indiquant quelle déclaration remplace laquelle, sans effacer les valeurs antérieurement publiées.

[Pour Dijon D1 : les références candidates du profil sont `2024VDPA046401` à `2024VDPA046404`, notification publiée le 13 décembre 2024. Merci de confirmer leur correspondance avec les quatre lignes, ou d'indiquer une autre correspondance.]

[Pour Bordeaux B1/B2 : le portail reprend respectivement `2025E008` et `2025E007` pour deux valeurs chacun. Merci de préciser si ces références désignent un marché unique, plusieurs lots ou des versions.]

[Pour Grenoble G1 : merci de distinguer les références `23ASB248`, `23ASB249`, `23ASB250` de leurs accords-cadres parents ; une valeur de 240 000 EUR apparaît pour deux références avec des parents différents.]

Des extraits occultant données personnelles et secrets protégés suffisent. Aucun dossier complet d'offre ni identité des candidats non retenus n'est demandé. Merci d'indiquer le service détenteur si nécessaire et les motifs concernant tout document non communicable.

Cordialement,
[Identité et coordonnées à ajouter hors dépôt]

**Annex selection:** Dijon D1–D4, Bordeaux B1–B2, Grenoble G1–G4. Delete the other municipalities' bracketed paragraphs before sending. No draft has been sent.

## Reproduction and validation

No tool added, so no focused tool-test suite is applicable. Verification consisted of read-only Python JSON/gzip inspection, symmetric cluster membership/count checks, manifest hash checks, feed-field/object/holder comparisons and the in-memory Dijon reconciliation described above. Existing `tools/reconcile-dijon-project.py` **main writes private output even without `--write-curated`**; do not run it as a read-only check. Import its functions and call `project_rows`, `eforms_results`, `simple_results`, `reconcile` without main, supplying verified private responses.

Minimal current-count check (no network, no output file, no supplier fields emitted):

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

Dataset hashes above pin the findings. Recheck them before action; drift requires a new inventory, not silent application of these conclusions.
