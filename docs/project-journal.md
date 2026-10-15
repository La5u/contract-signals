# Project journal

Delivery outcomes and historical counts. Current usage: [README](../README.md). Active methods: [score-v3.md](score-v3.md) and [score-colombia.md](score-colombia.md). Historical weights and counts do not describe the current engine. A signal is not proof of wrongdoing; the weights are editorial, not calibrated probabilities.

## Ukraine random-sample field check — 12 October 2026

- All 488 Prozorro rows × 20 fields match cached official records. A frozen 40-row random sample agrees with live records and separate contracting-module records, with no publisher changes or errors. No data changed. See `research/ukraine-random-sample.md`.

## Ukraine public-only accuracy audit — 11 October 2026

- Froze a 12-contract review sample (5 flagged, 7 zero-score) from the 488-contract cohort, plus 11 known contract/award amount differences.
- Seven amount differences have explicit net/VAT-excluded evidence. Four amount and fourteen VAT-only differences remain unresolved; no amount replaced.
- Three active changes corroborate the sole three-amendment flag. Six sampled modules omit `changes`; availability awaited schema verification. Vinnytsia discovery reports 506 entries with no observed 500 cap; historical completeness remains unproven. One HTTP 302 attachment was not followed.
- Audits replay offline. 500 system-Python tests pass (31 optional skips). The October evidence reviews left scores and index inputs unchanged and were not deployed.

## Supported link resolutions and durable correction log — 11 October 2026

- Original nine-pair artifact retained: seven active candidates, two dismissed leads, zero confirmed DECP links. Paris `2024S05079`↔LOT-0001 was dismissed because the long-reference pattern belongs to LOT-0003. Nantes `2025F00012`↔technical LOT-0003 was dismissed because that lot is printed Lot 2, LAVERIE, while DECP says CUISSON. Neither dismissal establishes a replacement link.
- `research/link-corrections-log.md` records decisions and 62 exact primary evidence scalars. Evidence artifacts use source/row hashes and offline validation to reject stale decisions.
- Explorer separates dismissed sources from active candidates, recomputes ambiguity and shows three verified TED notice/version links. Missing review artifacts show a fallback warning.
- JS/browser suites and 443 system-Python tests pass (30 optional skips). Score-review regenerated; optional scientific catalogue mismatch remains unresolved.

## Paris reference conventions and exact TED versions — 11 October 2026

- Paris publishes six long references as national-recensement numbers. Ministry schema and retained rows provide no crosswalk to short DECP IDs. Paris list is ODbL; catalogue reuse terms remain unspecified. Direct 12–13 MB Atexo exports were not downloaded.
- `checkQuerySyntax:true` validates syntax without searching. An executed exact UUID/procedure query found five award publication numbers; 723965-2024 is a predecessor.
- Three exact BOAMP/TED notice versions (`01`) verified in official XML. Two other XML attempts returned HTTP 429. Long/compound XML references establish no DECP links or field corrections. Raw XML stays outside the website; replay checks headers, not source authenticity or contract truth.
- JS/browser suites and 439 Python tests pass (30 optional skips).

## Public-only BOAMP↔DECP evidence review — 11 October 2026

- Reviewed nine pairs across six BOAMP notices/seven lots. Initial findings: five Paris reference-format leads, two lot-compatible Nantes candidates and two disfavored mappings. Holder/date joins are insufficient; ceilings, annual periods and joint-buyer scope do not establish identity or spend.
- Added 104 minimized live scalar extracts and offline evidence builder. Optional reacquisition stores raw replies outside the website. Attribution, privacy and reproduction: `public-evidence.md`. Invalid optional evidence leaves base candidates visible.
- Public-document benchmark: nine blocked pairs, zero eligible, no agreement rate. The freeze followed identifier investigation, so it is not retrospective preregistration.
- JS/browser suites and 425 system-Python tests pass (30 optional skips). Scientific environment: 437 tests with the existing 18-versus-19 calibration catalogue failure.

## Compact record panel, faster filters, Portugal BASE extraction — 1 October 2026

- Panels fell from 4,300–7,300 characters (roughly one sixth about the record) to about 1,200 on average. Dataset notes moved to “Scope and limits”; reasons shortened and check lists folded. Rows fell from about 165 px to 85 px. Header/footer text shortened; logo removed.
- Cached checks and on-demand search text cut filter/sort time from about 900 to 250 ms for “All countries” (18,501 rows), and about 400 to 160 ms for Colombia.
- Added 150+ Spanish/French strings. Checked 261 panels across 15 datasets, three languages, desktop and phone: no script errors, broken text or overflow. Ukraine whitespace cleanup changed 74 descriptions.
- Portugal BASE private candidate: 3,353 rows kept, 616 set aside, mostly holders without tax numbers. Publication remains pending.

## Audit fix and first commits of the pending work — 1 October 2026

- `bid_attrition` now attaches per-bid decisions only to conclusive results. Offline rebuild of `data/prozorro.json` corrected the four affected rows; regression test added.
- Full suite passed: 119 Python tests, JS suites and Chromium HTTP/file/mobile/CSP checks. Work committed in single-purpose commits; explorer-only change tested separately before the linked-check change.

## BASE name-retaining candidate importer — 30 September 2026

- `tools/import-portugal-base.py` defaults to a frozen plan. `--extract` verifies archive provenance, streams records and filters three exact buyer NIFs/publication dates into a private candidate. Parse failures abort; omissions and conflicts are reported.
- Keeps published supplier names, including individuals; omits NIF prefixes and competitor identities. Unknown currency, duration, offers and direct-award fields stay unknown. Publication review cannot change `assessmentMode=browse` or `dataStatus=unverified`.
- `--publish-reviewed` requires reviewer and exact candidate SHA-256, validates fields/provenance/counts and rejects empty or differing outputs. Reviewed JSON uses local import; no bundled selector yet.
- 36 synthetic importer/publication tests pass, including explorer validation, null scoring and name-preserving, ID-omitting exports.

## BASE format and rights inspection — 30 September 2026

- Bounded inspection reads at most 64 KiB/member; aggregates cover three records/year, nine total. Each ZIP holds one deflated JSON array: 384,159,940 / 437,904,158 / 320,855,087 uncompressed bytes.
- Nine samples share 39 fields. `dataPublicacao` is DD/MM/YYYY, separate from decision/signing/closure dates. Currency and duration unit unverified. `PrecoTotalEfetivo` is zero in 7/9, not evidence of no payments. Holder/competitor strings contain NIF/name forms; no verified offer counts inferred.
- `other-pd` means “Outra (Domínio Público)”, with no terms URL. It establishes neither CC0 nor privacy clearance. BASE guidance recommends dados.gov.pt downloads; current field-specific obligations for natural-person IDs remain unverified.
- Added `tools/inspect-base-archives.py`, `data/portugal-base-inspection.json`, `data/portugal-base-rights.json` and `docs/portugal-base.md`. Five synthetic-prefix tests and small evidence/link checks pass.

## Authorized Portuguese archive download — 30 September 2026

- Downloaded frozen IMPIC `contratos2024.zip`, `contratos2025.zip`, `contratos2026.zip`: 44,570,348 / 55,274,614 / 42,232,603 bytes; 142,077,565 total. HTTP 200, ZIP signatures and exact catalogue sizes confirmed.
- `tools/download-base-archives.py` defaults to a plan. `--download` allows only these URLs, serial/2s, no retries/redirects, 60 MiB/file, 160 MiB total. Interrupted downloads require manual review. Cache must be outside repository/web root, modes 0700/0600.
- Metadata: `data/portugal-base-download-plan.json`, `data/portugal-base-downloads.json`. Publication requires reuse-term and personal-field review.

## Bounded expansion research — 30 September 2026

- `data/expansion-plan.json` fixes scope: same six French buyer SIRETs for separate 2023 backfill; exact-ID TED evidence; same three Portugal buyer NIFs; then Indonesia/Russia feasibility gates.
- Located IMPIC 2012–2026 metadata in dados.gov.pt. Advertised 2026 ZIP/XLSX resources: ~42–49 MB. LKPP portal/API returned 200, but results were aggregate indicators with empty licences, not verified contracts. SIRUP/Russia failed at network level; permanent availability remains unknown.
- `tools/expansion-plan.py` defaults to a network-free plan; `--probe` uses cached metadata attempts, not advertised resources. Evidence: `data/expansion-source-checks.json`; gates: `docs/expansion.md`.
- Battery-limited metadata work: five offline helper tests and small JSON/link/whitespace checks pass. No procurement records added.

## Repository presentation — 29 September 2026

- Restored standard MIT `LICENSE`; moved third-party data notice to `data/LICENSE.md`. README opens with public explorer, prototype caveat and `images/explorer.png`.
- Handoff uses public repository URL; machine-specific hook details removed. GitHub licence detection awaits publication.

## Readiness polish — 29 September 2026

- Simplified default view; advanced filters initially closed and remembered. `import.js` adds browser-local JSON/export-envelope, mapped CSV and OCDS import with validated preview. Browse-only default; French v3 opt-in. Compiled releases accepted, ambiguous histories rejected. Limits: 25 MiB, 20,000 records.
- Notes scoped by file content/settings; imports schema-checked. Notes remain plaintext. CSV formula guard handles leading whitespace/control characters. 72 Python tests, JS and Chromium HTTP/file/responsive/CSP/preview checks pass; Playwright pinned to 1.58.2.
- BOAMP and limited Annuaire enrichment reuse evidence in `source-rights-evidence.json`; attachment rights and personal-data questions remain separate. `personal-data.md` and `tools/audit-personal-data.py` inventory exposure without publishing values. SECOP account fields are placeholders; populated personal identity fields remain a concern. Raw assets still require review.
- `adoption.md` provides feedback exercises and outreach templates; no validation claimed.

## Active version: index 3.0 (21 September 2026)

- [v3](score-v3.md) separates not assessed (`null`) from zero (at least one evaluated check). Eight checks expose signal/evaluated/not assessable/out-of-scope states and unknown applicability. Conflicts and duplicate IDs excluded.
- Removed monetary tiers and the €50k increase threshold; retained strictly >20 %. Direct/repeated awards cover all amounts. Single offers require competitive procedures. Eight official findings remain separate from scoring; aggregate dossiers have no contract score.
- Index: `min(100, max(competition) + max(execution/duration))`, without renormalization. Graduated weights and tenth-point rounding documented in the method. Country, CPI, identities and R2122 citations add no points.
- [Ranking review](../data/score-v3-review.json): competition/execution weights ×0.8/1.2 and reverse give positive-only correlations 0.773–1, with many ties. Six flagged/zero/excluded extracts reviewed; no ground-truth labels. 26 Python tests and Chromium checks pass.

| Historical dataset | Signals | Evaluated zero | Not assessed |
| --- | ---: | ---: | ---: |
| BOAMP/CRC (3,010) | 277 | 2,665 | 68 |
| Paris/Ardèche (2,594) | 404 | 1,835 | 355 |
| Six municipalities (1,270) | 124 | 974 | 172 |
| Consultations (10) | 0 | 0 | 10 |
| Tours (66) | 0 | 0 | 66 |

### International access — 22 September 2026

- Colombia imported with [its own checks](score-colombia.md). Paraguay anonymous record/search/catalogue access returned HTTP 200; CC BY 4.0 in payload, base `/datos/api/v3/doc`. Brazil PNCP probes failed or timed out; operational access unproven. [Recommendations](international-pilots.md), [HTTP checks](../data/international-access-checks.json).

## Contract-linked adjudicated outcomes · separate from signals

- Final corruption labels require an official decision, finality, exact contract linkage and passage. Zero labels in provided French, Colombian and Paraguayan datasets. Station Nuage alone carries a September 2024 press lead about a search; it establishes neither guilt nor a continuing investigation. CRC observations are not convictions.
- [Criteria/schema](adjudicated-outcomes.md); regression: `node tests/outcomes.cjs`. Accuracy comparisons need independently reviewed positives and negatives; unlabelled rows are not negatives.

## DNCP OCDS pilot · Paraguay — documentary, not scored

- Fernando de la Mora (`DNCP-SICP-CODE-66`), calls published 2024-09-01 → 2025-09-01: 88 processes, 84 contracts joined by `awardID`. PYG only, CC BY 4.0. `data/paraguay-dncp.json`, `data/paraguay-dncp/raw/`, `data/paraguay-dncp-coverage.json`; [scope and reproduction](paraguay-pilot.md).
- All 84 rows initially not assessed pending local rules. Dates are period starts, not signatures. 80 signed-contract document links have not had their contents independently reviewed.

## SECOP II pilot · Colombia — first international cohort (22 September 2026)

- Preselected buyers: Ministerio de Educación Nacional (NIT `899999001`, 2,618), Gobernación de Caldas (`890801052`, 3,696), Usaquén (exact name; shared district NIT `899999061`, 1,246). Signature window 2024-09-01 → 2026-09-01: 7,560 contracts in `data/colombia-secop2.json`.
- All rows have process/contract/supplier fields and process URL; 7,553 usable typed supplier documents, seven placeholders. This checks source fields, not independent contract documents. Provenance: `data/colombia-secop2-coverage.json`; raw pages: `data/colombia-secop2/raw/` (~28 MB), normalized file ~15 MB.
- [Colombian method](score-colombia.md): absence of plurality/manifest urgency 176 signals; repetition 15; concentration 0 (max 31.3 % <60 %); duration ≥36 months 39. Total 215 flagged, 7,345 evaluated zero, 0 not assessed, 71 partial. French offer/timetable/history checks out of scope. Ordinary direct modality (~82 %) earns no points.
- Spanish source text preserved; COP never converted or summed with EUR. CC BY-SA 4.0 attribution retained.

## Navigation and documented projects

- Fixed-height table keeps pagination in place. CPV sector is two-digit contract division; statistical groups use CPV3. Grouping precedes pagination; counters cover filtered results, with no financial total or group score. Suppliers group by typed SIREN, not name; buyers without SIRET use names marked for verification.
- Paris 13 November 2025 dossier links `2025S11106` (TRE CONSEIL, `94029483800013`; BOAMP `25-119743`, reference `2501435`), `2025F11832` (SAF, `33837878900048`; parent `20212021F09371`) and `2025F11638` (JAULIN, `33518760500035`; parent `20222022F03358`). Matching uses explicit subjects, buyer and year.
- Chronology: RMC announcement 26 July, DECP notification 16 October, Le Parisien coverage 17 October, two notifications 3 November 2025. Project metadata stays embedded for file mode; incompatible metadata is rejected. [Two source PDFs](sources/paris-13-november-2025/) retained. Project links establish neither overlapping services nor payments.

## R2122 legal context — no additional points

- `getLegalContext` detects explicit citations in published object/description or procedure with HTTP(S) source. Keeps citation, field and full text. R2122-1 marks urgency; R2122-3 does not distinguish artistic/technical/exclusive-rights grounds. A mention requires reading; it is not legal validation.
- Paris/Ardèche: five citations, one R2122-1 and four R2122-3. Uncited direct awards say “justification unknown in this extract”. Legal context changes neither `directAward` nor index. 124 assertions and Chromium checks pass.

## DECP history 2024–2025 — active feature

The dataset selector opens by default the history of the **Ville de Paris** (SIRET `21750001600019`) and the **Département de l’Ardèche** (`22070001700019`). Paris was chosen for its purchase volume; Ardèche was added for the availability of published modifications. This selection is exploratory and biased by data availability, not representative of France nor of a buyer category.

The scope includes **every row returned by the source** for these SIRETs and the initial notifications from **1 January 2024 to 31 December 2025**. Published modifications may be later than 2025: this is not a snapshot frozen at 31 December 2025.

### Source and download

[DECP — arrêté du 22 décembre 2022, marchés valides, Ministry of Economy](https://data.economie.gouv.fr/explore/dataset/decp-2022-marches-valides/).

```text
API: https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records
where: acheteur_id='21750001600019' AND datenotification >= '2024-01-01' AND datenotification < '2026-01-01'
```

Same query for `22070001700019`. You must **paginate**: `limit=100`, `offset=0,100,200,…` up to the `total_count`, with a stable order by date and identifier. A first-page URL is not the whole extraction. Parameters, dates and counts are documented in `data/decp-coverage.json`. The `decp-v3-marches-valides` source falls under the old 2019 arrêté and does not fit this 2024–2025 history; it is not used here. “Valides” designates the dataset produced by the producer’s data checks, not a certification of the contracts’ regularity. The rows of the “invalides” dataset are not included.

| Scope | Source rows | Buyer SIRET + identifier groups |
| --- | ---: | ---: |
| Paris | 2,395 | 2,040 |
| Ardèche | 554 | 554 |
| Total | **2,949** | **2,594** |

- **355 groups** have diverging initial values (notably the amount). The affected field becomes `null`; the published values remain in `initialAlternatives`. They are not artificially ordered to invent an amendment chronology. These groups are excluded from the two new indicators.
- **276 contracts** have a published modification in the extract; the source exposes one modification per contract here. This does not prove there was only one: the index may contain only the last.
- **2,239 initial amounts** are usable; 355 are unknown because of the divergences. **2,581 offer counts** are provided; 13 are unknown. SIRETs, contract identifiers, CPVs and initial dates are kept.
- The supplier is displayed by **SIRET identifier**, with a derived SIREN when it is indeed a French SIRET. No company name is invented. The sentinel values `CDL`/`INX` become neither zero nor a fictional company.
- `history` contains an initial entry and the available modifications, with distinct notification/publication dates. Each source link filters **the buyer SIRET and the contract identifier**, not only the local authority.

### Two indicators added

**Declared amount increase**: last newly published total amount > initial amount × 1.20 **and** increase > €50,000, price exclusively declared `Définitif ferme`, no initial divergence, usable dates and no identified change of holder. The calculation compares two declared amounts of the same identifier; it does not guarantee that the quantities or services stayed identical. It measures neither a unit price, nor an unjustified overrun, nor a final expense.

The [official DECP schema v2.0.4](https://github.com/139bercy/decp-arr2022/blob/main/schemes/schema_decp_v2.0.4.json) titles `definitions/marche/definitions/Modification/properties/montant` **“Nouveau montant”** (“new amount”). It is therefore treated as a revised total, **never added to the initial one**. Some entries may nevertheless be wrong: if the declared amount looks like a decrease/increment, if it is missing, if the chronology is inconsistent or if the price is revisable/updatable, the automatic calculation is disabled and the reason is displayed. A firm price does not exclude legitimate additional services. The 20 % and €50,000 thresholds are editorial, not legal. Comparisons use rounded euro cents, to prevent a floating-point error from turning exactly €50,000 into a threshold overrun.

In this file: **104 analysable evolutions**, of which **13 trigger** the signal. The other cases must not be considered as zero evolutions: some are unknown, not comparable or without a published modification.

**Repeated low competition**: retrospective context of the same buyer SIRET and the **three-digit CPV** group, over the 2024–2025 notifications. Only explicitly competitive procedures, without version conflicts, are included. Adapted procedures are not automatically presumed competitive. A missing or repeated contract identifier in the file, or a generic `000` CPV, also excludes the group calculation. Known offer counts must be strictly positive integers.

Exploratory thresholds: **at least 10 contracts with a known offer count**, **80 % coverage** of the group’s eligible contracts and **60 % at a single offer**. The signal is displayed only on contracts that themselves received a single offer, not on all the buyer’s contracts. The numerator, denominator, coverage and period are displayed in the details. The calculation uses the whole loaded cohort **before** search, filtering or pagination: it does not change with the filters.

In this file: 127 eligible buyer/CPV groups, 14 with sufficient coverage thresholds; **9 flagged contracts** in the Paris / CPV 798 group (12 known observations, of which 9 at a single offer). This is competition observed in the published contracts of this cohort, not a conclusion about a company nor a national rate. A group of 10 observations remains small: this threshold is a reading rule to be tested, not a statistical guarantee.

### Identifiers and dataset separation

The existing **3,002 BOAMP lots** were enriched with notice, lot, local per-notice contract identifiers, CPV, publication date and available organization identifiers. A buyer SIRET was identified for 1,858 lots; the others remain unknown. An eForms identifier `CON-0001` is **not** a DECP identifier. Local references must always be interpreted with the notice identifier.

The two files are **not merged**: purchases can appear in both. No matching is asserted from the name alone, a close amount or `CON-0001`. Do not sum the amounts of the two files, nor present their row sum as a number of unique purchases. Longitudinal statistics are not computed on the BOAMP sample. The eight official findings stay in the BOAMP/CRC dataset, without propagation to DECP contracts of the same local authority.

The `getAmountEvolution`, `prepareContracts` and `getIndicators` functions are separated in `script.js`. `prepareContracts` builds the groups before display; a context present in an imported file is recomputed rather than taken at face value. Importing a subset does not give it the exhaustiveness of the provided dataset: the page then states that it describes the loaded file.

## Six additional municipalities and public identities — delivery of 15 September 2026

- Rennes, Nantes, Bordeaux, Grenoble, Dijon and Tours chosen before scores for geographic/size diversity. Exact commune SIRETs, not métropoles. Same DECP source/window as above: 21 pages, 1,865 rows, 1,270 groups. Offset pagination cannot guarantee immutable coverage or all purchases. Files: `data/decp-cities.json`, `data/decp-cities-raw.json`, `data/decp-cities-coverage.json`.
- Historical extract: 172 initial-conflict groups (seven modification conflicts); 355 groups with 365 modification events, zero exact duplicates. Known amounts 1,099/1,270; offers 1,138/1,270; dates 1,128/1,270. Revised amounts are totals. Six analysable increases, zero signals; 89 competitive groups, five sufficiently covered, 11 repeated-low-competition contracts. Single offer 228; direct award ≥€100k 16; duration ≥10 years 4; 233 groups flagged overall. Counts overlap.
- Current-name sample: first 100 of 703 typed SIRENs after SHA-256 sorting, selected before names/states; 603 unqueried. 100 exact matches, names on 148 groups. Retain only public name/SIREN/legal-unit state/date/provenance with `statut_diffusion=O`. No historical Sirene/RNE/establishment verification. `data/supplier-identities.json`, `data/supplier-identities-coverage.json`; API `https://recherche-entreprises.api.gouv.fr/search?q=SIREN&per_page=25`. Profiles embedded for file mode.
- 124 historical assertions, 4,835 cohort assertions, nine Python tests and Chromium checks pass.

| Municipality | SIRET | Source rows | Historical groups | Historical conflicts |
| --- | --- | ---: | ---: | ---: |
| Rennes | `21350238800019` | 335 | 303 | 25 |
| Nantes | `21440109300015` | 699 | 541 | 81 |
| Bordeaux | `21330063500017` | 289 | 88 | 29 |
| Grenoble | `21380185500015` | 113 | 22 | 14 |
| Dijon | `21210231300013` | 273 | 160 | 23 |
| Tours | `21370261600011` | 156 | 156 | 0 |
| Total | | 1,865 | 1,270 | 172 |

### Identifier collisions — 8 October 2026 update

- Owner chose to include every contract: rows sharing a DECP `id` but differing in declared fields are separate linked contracts. Possible same-contract pairs are flagged and counted once in buyer baselines. Cohort: 1,864 contracts, none excluded (`research/decp-identifier-collisions.md`).
- Earlier evidenced Dijon splits covered `2023VDAO1642`, `2024VDPA0121`, `2024VDPA66`: 13 linked rows in `data/decp-cities-curated.json`; seven conflicting offer counts became unknown. Evidence/limits: `research/decp-dijon-conflict-review.md`.

## Tours full BOAMP/TED notices — delivery of 16 September 2026

- Tours SIRET `21370261600011`, BOAMP publications in 2025, chosen before scoring. 23 candidates; 27 raw notices; 25 qualified (22 in year, three linked outside). Excluded `25-102354` and `24-42098`: buyer is Syndicat des mobilités de Touraine (`20008510800013`). 66 notice/lot versions: 55 initial, six correction, five result; ten joint-purchase rows.
- Downloaded 28 TED XMLs: 27 exact UUID matches plus cited predecessor `461026-2023`. UUID/version/lot verified separately; buyer name/date only discover candidates. Files: `data/tours-notices.json`, `data/tours-notices-coverage.json`, `data/tours-notices/raw/api-records.json`, `manifest.json`, `ted-*.xml`, `ted-manifest.json`, `ted-api-search-*.json`. Empty/HTML HTTP 200 is not XML.
- Procedure text on 13 rows; criteria on 25 rows, 68 entries, numeric parameters on 24 rows. `25-127301`: quality/price/deadlines/environment-social values 40/30/20/10, `per-exa`/`number-weight`. `25-4887` cites R2122-8 for other lots, not its open lots 1/2/5. Corrections `25-117276`→`25-127197` (five lots, 24→27 November 2025) and `25-119055`→`25-127301` (24 November→1 December), 12:00 `+02:00`. Nine explicit notice/lot links transfer no holder or amount.
- Zero periods evaluated: complete chains/initial publications unproven. Buyer documents linked, not downloaded; textual search may miss other SIRETs/formats/spellings. 831 documentary, 124 historical, 4,835 city assertions, 17 Python tests and Chromium checks pass. Dates/time zones kept as published.

## Provenance of the BOAMP / CRC dataset

- `data/contracts.json`: 3,000 imported lots, two Mauges lots, eight CRC dossiers. `data/coverage.json` records provenance. `verified` means supported by public source and transcription checks, not independent review of every notice.
- BOAMP publication window 1 February–30 April 2025: 8,386 notices downloaded; 2,153 non-eForms notices unmapped. 16,002 usable rows, 15,432 notice/lot IDs; 236 conflicting IDs set aside. First 3,000 of 15,196 unambiguous IDs selected by SHA-256 ordering, independent of score/amount/offers.
- Mapping uses total offers (`tenders`, never electronic subset), EUR `LotTender/LegalMonetaryTotal/PayableAmount`, all identified winning members, and `DurationMeasure` in `MONTH` without renewals. Ambiguous winning references excluded. `neg-wo-call` means direct; recognized competitive codes false; otherwise unknown. No audit matching to new lots.

| Field in 3,000 imported lots | Provided | Unknown |
| --- | ---: | ---: |
| Conclusion date | 2,978 | 22 |
| Offer amount EUR | 2,248 | 752 |
| Total offers | 1,188 | 1,812 |
| Initial duration months | 979 | 2,021 |
| Procedure classification | 2,926 | 74 |

### Documented dossiers

- **Mauges:** [BOAMP 25-846](https://www.boamp.fr/pages/avis/?q=idweb:25-846), [JSON](https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records?where=idweb%3D%2225-846%22&limit=1), published 7 January 2025. Stockmeier France €548,100; Lhoist France Ouest €183,648. One offer each, open procedure, concluded 19 December 2024. Initial 36 months; two renewals of unknown duration. Winning offers, not payments; no official finding.
- **Rognac Christmas market:** [Publication/responses](https://www.ccomptes.fr/fr/publications/commune-de-rognac-bouches-du-rhone-1), [PAR2025-0792](https://www.ccomptes.fr/sites/default/files/2025-08/PAR2025-0792.pdf), p. 16. €140,362 excl. tax across several entertainment contracts. CRC criticizes threshold calculation and procurement procedure; individual suppliers/dates unknown, `directAward=null`.
- **Station Nuage:** [CRC report/response](https://www.ccomptes.fr/fr/publications/commune-de-saint-sebastien-sur-loire-loire-atlantique-1), 29 June 2022. Design-build forecast €167,000 excl. tax, no negotiation/tendering. CRC also notes procurement professionalization and good management of other procedures. Supplier/signature unknown.
- **La Gandonnière:** [Publication/responses](https://www.ccomptes.fr/fr/publications/commune-de-la-chapelle-sur-erdre-loire-atlantique-1), [report 2025-225](https://www.ccomptes.fr/sites/default/files/2025-06/ROD%202025-225%20Cne%20La%20Chapelle-sur-Erdre.pdf), §2.4.2, pp. 33–37, p. 36 notes 56/63. Signed 26 May 2021; initial order €289,263 excl. tax (commune €226,513, SPL fees €62,750), not final cost. CRC disputes artistic exception/procedure; response in report.
- **Cressonnière stadium:** [Publication](https://www.ccomptes.fr/fr/publications/commune-de-saint-andre-la-reunion-cahier-ndeg-2-la-situation-financiere-la-gestion-des), [RER2021532](https://www.ccomptes.fr/sites/default/files/2023-10/RER2021532.pdf), p. 40 §3.3.1.1, [response](https://www.ccomptes.fr/sites/default/files/2023-10/REO2021532.pdf). Prestige Construction replaced terminated holder; CRC says new competition required. Offer €339,258 excl. tax, 33 % higher. New notification unknown; 10 May 2017 belongs to previous contract. `directAward` unknown.
- **Mamoudzou:** [Publication](https://www.ccomptes.fr/fr/publications/commune-de-mamoudzou-mayotte-cahier-ndeg2-la-commande-publique), [report](https://www.ccomptes.fr/sites/default/files/2024-08/ROD2-MDZ-cahier2-et-sa-r--ponse.pdf), [response](https://www.ccomptes.fr/sites/default/files/2024-08/Mamoudzou_r--ponse_ordonnateur.pdf). Four aggregates, unnamed suppliers, `directAward=null`. Response cites cleaning continuity, consultation of three travel agencies and better monitoring.

| Mamoudzou dossier | Passage/finding | Amount scope |
| --- | --- | --- |
| Travel | p. 15 §2.1.1; >300 payment orders without framework | ≥€760,000, 2018–October 2023 |
| Cleaning | pp. 15–16 §2.1.2; competition rules unmet | >€200,000 paid in 2023 |
| Guarding lots 1/3 | pp. 17–18 §2.2; offer substantially modified, award judged irregular | ≈€500,000; 19 invoices, November 2022–August 2023; initial 12 months plus two renewals |
| Snacks | pp. 19–21 §2.3.1; continued orders without competition | ≥€10.38m, September 2019–April 2023; several suppliers |

Eight findings from five publications: three contract dossiers, five aggregates. Five new dossiers have no certain BOAMP match. `findingScope` separates contract/aggregate; `amountQualifier` keeps bounds/rounding. Findings stay with their exact dossier, not other purchases of buyer/supplier.

## BOAMP consultations — delivery of 15 September 2026 (score 2.1)

- `data/consultations.json`: first ten identifiers of 200 initial calls published 3 February 2025, selected before scoring. FNSimple notices, not contracts; amounts/holders/offers unknown. IDs: `25-12212`, `25-12213`, `25-12214`, `25-12216`, `25-12217`, `25-12218`, `25-12220`, `25-12226`, `25-12228`, `25-12229`. `data/consultations-raw.json` holds 14 notices, one correction and three results; queries/exclusions in `data/consultations-coverage.json`.
- `25-12214`→`25-22678`: 27 February correction moves deadline 7→14 March 2025, 12:00, time zone unknown. Results: `25-12212`→`25-50122`, `25-12213`→`25-36651`, `25-12226`→`25-31439`; notice links only. `25-12220` describes 16 lots. Procedure UUID/version unknown; adapted procedure not assumed open; eight-digit CPVs retained.
- Historical `getBiddingPeriod`: complete chain, same identified procedure/lot, one initial, ordered versions/corrections, HTTP(S), open procedure, acceleration explicitly false, zoned deadlines and consistent chronology required. Signal strictly <15 days from midnight UTC of initial BOAMP publication to final extended deadline; weight 12, competition maximum. Missing/conflicting/shortened/late-corrected/ambiguous chronology disables calculation; award notice never starts it.
- 0/10 periods evaluable, ten excluded, zero signals; chain completeness, acceleration and versions unknown. 107 assertions and Chromium checks pass. Historical counts: 3,010/2,594 rows, eight findings, 13 increases, nine repeated-low-competition and eight concentration flags. Complete chains and historical Sirene/RNE remain open work.

## Reproduction commands

Current serving, browser setup, full-suite tests and standard offline rebuilds are in the [README](../README.md). `node tests/browser.cjs` now starts its own server. Current supplier names use `tools/enrich-suppliers.py`. Historical commands below may predate later changes.

- Index review: `node tools/review-score-v3.cjs`; checks: `node tests/scoring-v3.cjs` (31,032 assertions), `node tests/rules.cjs` (124), `node tests/cities.cjs` (4,835), `node tests/tours.cjs` (831), `node tests/colombia.cjs` (181,492), `node tests/paraguay.cjs`, `node tests/outcomes.cjs`.
- Python: `python -m unittest discover -s tests -p 'test_*.py'`.
- Historical city profiles (the tool is now `tools/enrich-suppliers.py`, renamed in `97ca65f`): `python tools/enrich-city-suppliers.py --offline`, then `python tools/import-decp-cities.py --offline`, then `node tools/update-cities-coverage.cjs`. For a network refresh, run `python tools/import-decp-cities.py`, then `python tools/enrich-city-suppliers.py`, then the offline import and coverage update.
- Tours refresh: `python tools/import-tours-notices.py`, then `python tools/download-tours-ted.py`, then `python tools/import-tours-notices.py --offline`.
- Colombia refresh: `python tools/import-colombia-secop2.py --download`. Consultations refresh: `python tools/import-consultations.py`.

BOAMP API: `https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records`.

- Award sample: `nature='ATTRIBUTION' AND dateparution >= '2025-02-01' AND dateparution < '2025-05-01'`; pages of 100, offsets 0–8,300.
- Consultations: `dateparution = date'2025-02-03' AND nature = 'APPEL_OFFRE' AND etat = 'INITIAL'`, `limit=10`, `order_by=idweb ASC`. Links: `annonce_lie = 'IDENTIFIER'`, `limit=100`, `dateparution ASC, idweb ASC`, then follow correction ID.
- Tours: `dateparution >= date'2025-01-01' AND dateparution < date'2026-01-01' AND donnees LIKE '%21370261600011%'`, `limit=100`, `dateparution ASC, idweb ASC`. Exact `annonce_lie`/`contractfolderid` follow-ups have no date restriction. TED search: POST `https://api.ted.europa.eu/v3/notices/search`, name and ±45 days for discovery only.
- Six cities: DECP endpoint/window above; `limit=100`, `order_by=datenotification asc,id asc`, offsets through each `total_count`. Refresh descriptive counters when sources change.

## Remaining enrichment questions

- Verify modification completeness, exact BOAMP/TED/DECP links and complete bidding calendars. Extend buyer history with selection independent of signals. Missing small purchases limit threshold/splitting analysis; unit-price comparisons need quantities, scope, taxes and dates.
- Historical Sirene/RNE and buyer documents could clarify identity, scope and chronology. Company age, workforce, address, NAF, financial difficulty and interest declarations remain context, not automatic points. Comparable CPV/procedure/year groups need adequate size (example 30 observations, threshold untested). Review flagged and unflagged samples and ranking stability.
- Source leads: [DECP consolidated](https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-fichiers-consolides), [Colmo tabular consolidation](https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-consolidees-format-tabulaire) (third-party; API announced subscription-based), [BOAMP](https://www.boamp.fr/), [TED](https://ted.europa.eu/en/simap/developers-corner-for-reusers), [Sirene](https://www.data.gouv.fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret), [BODACC](https://www.data.gouv.fr/datasets/bodacc), [CRC](https://www.ccomptes.fr/fr/publications), [Légifrance](https://www.legifrance.gouv.fr/), [administrative justice](https://opendata.justice-administrative.fr/), [HATVP](https://www.hatvp.fr/open-data/). Joins require exact identifiers, dates and scope; respect diffusion/reuse limits.
- Grants remain a separate future module. Legacy engine `tools/legacy/scoring-v2.1.js` is frozen for comparisons/tests; active extensions use `getAssessment` with applicability, evaluation state, family and documented weight.
