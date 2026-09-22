# Contract signals

A minimalist static explorer, in English. No framework, no runtime remote service, no backend, no database, no dependency or build step. Source procurement documents, citations and quotations remain in their original language (mostly French).

## Run it

From this folder:

```sh
python -m http.server 8000
```

Then open **http://localhost:8000**. The browser loads the selected dataset with `fetch`: `data/decp-history.json` by default, `data/contracts.json` for the BOAMP sample and official findings, `data/consultations.json` for the initial notices and their documented links, **`data/decp-cities.json`** for the six additional municipalities, **`data/tours-notices.json`** for the full Tours notices with criteria, explanations and TED versions, or **`data/colombia-secop2.json`** for the SECOP II Colombia pilot.

You can also open `index.html` directly. Browsers generally block `fetch` under `file://`: in that case select **data/decp-history.json** or **data/contracts.json**, **data/consultations.json**, **data/decp-cities.json**, **data/tours-notices.json** or **data/colombia-secop2.json**, depending on the chosen dataset, with the displayed file picker. This mode requires no server and transmits no file. There is no second embedded copy of the dataset.

## Active version: index 3.0 (21 September 2026)

**The active method is now [the v3 index](docs/score-v3.md).** The dated deliveries and v2.x tables below keep the history of choices and counts; their old weights and signal numbers **no longer describe the active engine**. The source contracts, notices, identifiers, explanations and PDFs are preserved.

Effective changes:
- **Not assessed ≠ zero**, on all datasets. `getVigilanceScore` returns `null` if no check can be evaluated. A zero requires at least one evaluated check. Dedicated filters, and unknowns always last, in both sort directions.
- **Eight detailed checks**: signal, evaluated without a threshold crossed, not assessable, out of scope. The evaluated/established-applicable ratio is accompanied by the number of unknown applicabilities; these are neither hidden nor treated as negative. Conflicts in both DECP cohorts and duplicated identifiers are excluded.
- **Amounts outside the weighting**: no more monetary tiers. Direct/repeated awards cover all amounts; the comparable increase remains strictly >20 %, with no absolute €50k threshold. The amount and its scope remain a separate piece of financial information, not a proven expense.
- **Graduated heuristic intensity**: bounded linear progression for shares, repetition, duration, increase and period, after eligibility; thresholds and rounding to the tenth are explicit in the method. A single offer requires an explicitly competitive procedure; it no longer earns points when the procedure is direct or unknown.
- **Official findings separated**: the eight findings remain visible, sourced, filterable and have a dedicated sort, but no longer add 50 points. Aggregate audit groups have no contract score.

The score is `min(100, max(competition) + max(execution/duration))`, **without renormalization**, and with no target of showing more flagged contracts. The weights remain uncalibrated editorial choices. No country, CPI, company identity or R2122 citation adds points.

| Unchanged dataset | v3 signals | Zero after partial or full evaluation | Not assessed |
| --- | ---: | ---: | ---: |
| BOAMP/CRC (3,010) | 277 | 2,665 | 68 |
| Paris/Ardèche (2,594) | 404 | 1,835 | 355 |
| Six municipalities (1,270) | 124 | 974 | 172 |
| FNSimple consultations (10) | 0 | 0 | 10 |
| Tours version/lot rows (66) | 0 | 0 | 66 |

v2 flagged a single offer even when the competitive character remained undetermined: v3 therefore shows **fewer**, not more, flagged records. This is neither a measured improvement of regularity nor a percentage of “non-suspect” contracts. The eight findings are not included in these heuristic signal totals.

### Ranking review and tests

[`data/score-v3-review.json`](data/score-v3-review.json) compares v2.1/v3 on the same files, logs the transitions, and tests competition/execution ×0.8/1.2 then the reverse. Rankings are sensitive to these choices: positive-only correlation from 0.773 to 1 depending on dataset/scenario, many ties. **This diagnostic is not a validation of corruption detection.** The method also contains a limited review of six flagged/zero/excluded extracts, with counterexamples and benign explanations; no ground-truth labelling is derived from it.

```sh
node tests/scoring-v3.cjs        # 31,032 assertions of the active engine
node tests/rules.cjs             # 124 assertions of the frozen, non-active v2.1 reference
node tests/cities.cjs            # 4,835 assertions, score expectations migrated to v3
node tests/tours.cjs             # 831 assertions, documents without a calendar = null
node tests/colombia.cjs          # 181,492 assertions, SECOP II pilot: cohort, join, Colombian indicators
python -m unittest discover -s tests -p 'test_*.py'
node tools/review-score-v3.cjs    # report and currentIndex pointers of the coverages
# With HTTP server on 8765 and test-only Playwright outside the project:
node tests/browser.cjs
```

The 26 Python tests and the Chromium HTTP / `file://` checks pass, including assessment filters, eight detailed checks, findings outside the index and pagination without page shift. No preparation/test script is needed to browse the site.

### Countries: Colombia imported; Paraguay access validated; Brazil blocked

**Colombia is imported** (three pre-selected buyers over 24 months) with its own documented indicator set, [docs/score-colombia.md](docs/score-colombia.md): declared absence of supplier plurality or manifest urgency, its repetition, buyer/contract-type concentration and declared duration — never the bare direct modality, never French thresholds. **Paraguay: anonymous data access validated 22 September 2026** — record (example OCID), date-filtered search and parameters catalogue all HTTP 200 without a token, licence CC BY 4.0 in the payload (despite the Swagger’s global Bearer declaration); base path `/datos/api/v3/doc`. Probes logged in `data/international-access-checks.json`. Next for Paraguay: quotas/exhaustiveness, then one bounded buyer cohort — not yet imported. **Brazil as a more ambitious project**: the PNCP requests tested failed or timed out; do not announce demonstrated operational access. A small TED scope in another EU country is an alternative for technical reuse, not a guarantee of national exhaustiveness.

See [the detailed recommendation](docs/international-pilots.md) and [the timestamped HTTP checks](data/international-access-checks.json). The CPI figures and volumes of the proposed text were not taken over without verification. No score comparison between countries, no mixing of currencies, spending or grants.

## SECOP II pilot · Colombia — first international cohort (22 September 2026)

Implemented per the verified plan: a bounded, pre-announced cohort, original-language evidence, and **jurisdiction-specific scoring** ([docs/score-colombia.md](docs/score-colombia.md)). Selector entry: **“SECOP II · Colombia pilot · three buyers · 2024–2026”**, file `data/colombia-secop2.json`.

- **Cohort announced before download** (2026-09-22), after volume-only count queries: Ministerio de Educación Nacional (national, NIT `899999001`, 2,618 contracts), Gobernación de Caldas (departmental, NIT `890801052`, 3,696), Alcaldía Local de Usaquén (municipal-local, matched by exact name because Bogotá’s alcaldías share the generic district NIT `899999061`, 1,246). **7,560 rows**, signature window 2024-09-01 → 2026-09-01 on `fecha_de_firma`.
- **Process–contract–supplier join verified on every row**: each SECOP II contract row carries its own `proceso_de_compra`, `id_contrato`, supplier name and typed supplier document (Cédula/NIT), plus the official process URL. Completeness is documented in `data/colombia-secop2-coverage.json` (`joinVerification`), not assumed.
- **Colombian indicators, not French ones**: four checks — declared absence of supplier plurality / manifest urgency (176 signals), repetition of such awards to the same buyer and supplier document (15), concentration within buyer and contract type (0; max observed share 31.3 % < 60 %), declared duration ≥ 36 months (39). The four French offer/timetable/history checks are out of scope with an explicit reason (no offers table, no chronology, no amendment history). Totals: **215 flagged, 7,345 zero after evaluation, 0 not assessed, 56 partial**. The declared modality “Contratación directa” covers ≈82 % of the cohort — ordinary legal context; the bare modality and ordinary justifications earn no points. Amounts in COP stay visible and sort only.
- **Language and currency**: every source field stays verbatim in Spanish (objects, modalities, justifications, statuses); amounts stay in COP, never converted or summed against EUR data.
- Licence **CC BY-SA 4.0** (Colombia Compra Eficiente) verified in the dataset metadata; attribution kept in the coverage file. Raw paginated responses are preserved under `data/colombia-secop2/raw/` (about 28 MB) with a URL manifest; the normalized extract is about 15 MB.

```sh
python tools/import-colombia-secop2.py --download  # new network snapshot of the announced cohort
python tools/import-colombia-secop2.py --offline   # deterministic re-normalization from the raw pages
node tests/colombia.cjs                            # 181,492 assertions: cohort, join, Colombian indicators
```

## Files

- `index.html`: page, disclaimers and controls.
- `style.css`: sober presentation, scrollable table on small screens.
- `script.js`: rules, validation, sorting, search and details.
- `data/contracts.json`: **3,010 real local records**, sources and context (about 6.7 MB after identifier enrichment).
- `data/coverage.json`: period, BOAMP query, import counts, transcription rules and exclusions.
- `data/decp-history.json`: **2,594 DECP contracts**, identifiers, initial values, variants and published modifications (about 7 MB).
- `data/decp-coverage.json`: scope, paginated queries, coverage and limits of the history.
- `data/decp-cities.json`: **1,270 buyer/identifier groups**, six additional municipalities, notifications 2024–2025, variants and current public profiles embedded for file mode.
- `data/decp-cities-raw.json` and `data/decp-cities-coverage.json`: **1,865 source rows**, exact queries, scope, exclusions and counts.
- `data/supplier-identities.json` and `data/supplier-identities-coverage.json`: minimized public snapshot of **100 SIRENs out of 703 identified**, sources and temporal limits; no network loading of these APIs while browsing the site.
- `data/colombia-secop2.json` and `data/colombia-secop2-coverage.json`: **7,560 SECOP II contracts** of the three announced Colombian buyers (2024–2026), Spanish preserved, COP only, provenance and join verification embedded; raw pages under `data/colombia-secop2/raw/` (about 28 MB); method in [`docs/score-colombia.md`](docs/score-colombia.md).

Search is insensitive to accents and case, over dossier/contract/lot/notice identifiers, buyer, supplier, SIRET/SIREN, CPV, subject and procedure. All searched words must be present. Unknown amounts are excluded when a positive minimum is requested. Available sorts: index, amount and date in both directions; CPV sector A–Z/Z–A; buyer and supplier A–Z; offer count ascending; analysable increase as a descending percentage. Unknown values are always last, even in ascending sort. Search, filters and sorting apply to **the whole dataset**, then the table displays 50 rows per page. Click a row or activate its subject button with Enter/Space to show the details.

## Precautions

> The indicators below flag anomalies or characteristics that may deserve review. They are not proof of irregularity, favoritism or corruption.

Public data can contain errors. These rules are heuristics, do not take account of all legal exceptions and do not allow a conclusion of illegal behavior. The absence of an indicator does not certify regularity. The index is only for sorting: it is not a probability, nor a measure of gravity. Bounded non-exhaustive sample, with no automatic refresh. Missing data triggers no rule; its frequency is displayed above the table.

## Navigation and documented projects

The table stays in a fixed-height area, with headers and the index column visible while scrolling. The pagination sits above this area: **Next/Previous does not move the browser page**; only the internal table scroll returns to the first row. The 50 contracts of a page can have different heights without moving the controls. Unknown data stays last in each sort direction.

The displayed sector is the **two-digit CPV division of the contract**, with a shortened label. It is not the supplier’s NAF activity. The statistical contexts continue to use the **three**-digit CPV.

Available groupings: documented project, CPV sector, buyer or supplier identified by SIREN. Multiple/foreign/unidentifiable suppliers are not merged on their name; buyers without a SIRET are matched by name with an explicit “to be verified” mention. Groups follow the order of their first contract in the chosen sort, then the contracts are sorted within. Navigation exception: the “No documented project” block comes after the documented projects, so as not to hide them. Groupings are formed **before pagination**; a group split across two pages carries a “continued” mention. Group counters describe the filtered results, not all of an organization’s purchases. No financial total or group score is computed.

### First project dossier: Paris commemoration of 13 November 2025

Three DECP contracts are explicitly linked:

- `2025S11106`: artistic direction — **TRE CONSEIL**, SIRET `94029483800013`. Documentary match with BOAMP `25-119743`, reference `2501435`; these identifiers are not substituted for one another.
- `2025F11832`: audiovisual — **SOC ACOUSTIQUE FRANCAISE (SAF)**, SIRET `33837878900048`, parent framework agreement cited `20212021F09371`.
- `2025F11638`: event equipment — **JAULIN**, SIRET `33518760500035`, parent framework agreement cited `20222022F03358`.

The matching rests on the DECP subjects explicitly mentioning the event, the same buyer and the same year, not on an automated word-similarity. The names were verified via the public Recherche d’entreprises API and their links are kept. The subjects, values and dates come from the official records. This proves neither an overlap of services nor an actual payment.

The “Project” selector or a row’s project link opens the dossier and its sources: RMC announcement of 26 July 2025, DECP notification of 16 October, coverage reported by Le Parisien on 17 October, then the two notifications of 3 November. The texts expose the difference between public declaration and contractual commitment. Steps resting on unrevised sources are not added. **The chronology adds no points** and never becomes an “official finding”.

The `project: { id, title, basis, source, evidence }` metadata is embedded in the three rows to keep file-mode loading self-contained. Each piece of evidence has a date, label, description, type and HTTP(S) URL. Incompatible metadata under the same project identifier is rejected. To add a dossier, its links must be documented explicitly; do not propagate a flag or an audit to the other contracts of the project. The user’s two PDFs were preserved unmodified and are not published as additional authority evidence.

## R2122 legal context — no additional points

The **“Legal context · no points”** filter distinguishes awards explicitly declared without competition (all amounts, including unknown), and the R2122, R2122-1 and R2122-3 citations. It is independent of the indicator filter. It modifies neither `directAward` nor the score.

`getLegalContext` spots only an explicit reference in the published **object/description** or **procedure** fields, with an HTTP(S) source. It notably accepts `R-2122-1`, `R. 2122-1` and `R2122-3- 3°`, keeps the exact citation, the field and the full text and displays the contract link. CPVs, names, editorial notes, projects, rejected variants and audit dossiers are not used to infer a basis. Automatic detection spots a mention: it does not demonstrate that the basis was legitimately invoked, nor even an affirmative invocation if the text disputes it. Read the extract.

R2122-1 is presented as relating to imperative urgency; R2122-3 covers artistic, technical reasons or exclusive rights: its mere citation does not allow choosing between those grounds. A single offer received does not establish exclusivity. The headings are markers, not a legal validation or an analysis of the historical version of the law. For a direct award without a spotted citation, the detail states **“justification unknown in this extract”**, never “absence of justification”. Initial conflicts remain flagged.

In the provided Paris/Ardèche DECP dataset: **5 contracts with an explicit citation**, including **1 R2122-1** and **4 R2122-3**. No additional download and no modification of the source data for this feature. The scores remain identical. Verification: **124 rule/data assertions** and Chromium tests of the R2122 filters, the exact text and the absence of additional points, on top of the existing HTTP/file-picker and pagination tests.

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

The selector offers **“DECP history · six additional municipalities · 2024–2025”**. Rennes, Nantes, Bordeaux, Grenoble, Dijon and Tours were named **before any examination of the scores**, for geographic and urban-size diversity, not for their anomalies. This is neither a random sample, nor a ranking of municipalities. The SIRETs were matched exactly from the public Recherche d’entreprises API results: these are the **communes, not the métropoles**. The verifications are kept in the coverage and the raw data.

### Full cohort returned by the source, same 24-month window

Current source: **`decp-2022-marches-valides`**, never the old pre-2024 dataset. DECP retrieval start: **2026-09-15T22:52:17.880816+00:00**. For each of the six SIRETs:

```text
https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records
where: acheteur_id='SIRET' AND datenotification >= '2024-01-01' AND datenotification < '2026-01-01'
limit: 100
order_by: datenotification asc,id asc
offset: 0,100,200,… up to the buyer’s total_count
```

**21 pages**, **1,865 raw rows**, no selection by amount, offers or score. All `total_count`s were reached. The full URL of each page and the counts are in `data/decp-cities-coverage.json`. Limit: offset pagination, with no immutable API snapshot nor guarantee that all purchases were published; ex-æquo versions in the sort and updates can affect coverage. Published modifications are not limited to the end of 2025.

| Municipality | SIRET | Source rows | Buyer + identifier groups | Ambiguous groups excluded from calculations |
| --- | --- | ---: | ---: | ---: |
| Rennes | `21350238800019` | 335 | 303 | 25 |
| Nantes | `21440109300015` | 699 | 541 | 81 |
| Bordeaux | `21330063500017` | 289 | 88 | 29 |
| Grenoble | `21380185500015` | 113 | 22 | 14 |
| Dijon | `21210231300013` | 273 | 160 | 23 |
| Tours | `21370261600011` | 156 | 156 | 0 |
| **Total** | | **1,865** | **1,270** | **172** |

**1,270 is not a certified number of distinct contracts.** Some identifiers seem reused for diverging subjects, dates or holders. No arbitrary choice between these variants, no invented split into new contracts. All groups remain consultable; the **172 ambiguous groups are excluded from all indicators and from the statistical denominators of this new cohort**. Their grey zero means absence of calculation. The rules and results of the older datasets are not rewritten.

- Rows carrying a modification also contain the initial fields: they are included even if no row without modification exists. **None of the 1,270 source identifiers is lost**.
- **172 groups with initial conflicts**, including **7 with modification conflicts** (same modification identifier, diverging values). All diverging initial fields become `null`, with an unknown-subject label at display; `initialAlternatives` and `sourceRowVariants` keep the values. The visible variants detail amounts, subjects, dates and holders, without treating them as a succession of amendments.
- **355 groups with modifications**, **365 distinct published events**, contradictory versions included. Notification and publication dates separated, durations in months, amounts in EUR. The new amount is a **declared revised total**, not an increment to be summed. Zero strictly identical duplicates found; the differing variants are preserved.
- Known initial amounts: **1,099/1,270**; offers: **1,138/1,270**; dates: **1,128/1,270**. A known field in an ambiguous group does not make it computable. Framework-agreement references and execution modalities are preserved; an amount can be a ceiling and is never presented as an actual expense.
- Each source link filters **buyer SIRET + contract identifier + initial window**. No BOAMP merge, no transfer of an audit or a project signal.

The longitudinal calculations use the same thresholds, on each cohort separately, before filtering. In this new file: **6 analysable amount evolutions, none at the alert threshold**; **89 eligible competitive groups, 5 with sufficient coverage, 11 repeated-low-competition contracts**; no concentration or repeated direct award crosses the thresholds. The other rules trigger **228** “single offer”, **16** “direct award ≥ €100k” and **4** “duration ≥ 10 years”. These numbers overlap: **233 groups have at least one indicator**. Do not sum them as independent anomalies. Details are recomputable in the coverage.

### Current identities: 100 SIRENs, not a history of companies

In the normalized `supplierIds`, **703 distinct French SIRENs** are derivable from explicitly typed SIRET/SIREN identifiers. Contradictory holders are not arbitrarily assigned to a company. The **first 100 SIRENs after SHA-256 sorting of the SIREN** were chosen before reading the names or administrative states, independently of the scores. The **other 603 were not queried**.

Source: **public Recherche d’entreprises / Annuaire des entreprises API**. Exact queries `https://recherche-entreprises.api.gouv.fr/search?q=SIREN&per_page=25`. Extraction started **2026-09-15T23:01:36.676181Z**, last request at **23:02:12.152108Z**. `retrievedAt` designates the start of this snapshot (also copied into its entries); the individual request times are kept in the coverage.

**100 exact matches available**, **0 unavailable**, names present on **148 groups**. Only `statut_diffusion = O` allows keeping a name. Restricted diffusion, absent status, ambiguous result or different identifier: no name retained. Only the public name, SIREN, legal-unit state, date and provenance are kept; no addresses, executives, personal contact details or full API response. The `associatedSirets` of the reference file come from the DECP, not from a proof of historical establishment matching.

The names are displayed **under the supplier identifier**, searchable and detailed with the exact source. They do not replace the published holder and do not change the SIREN groupings. The “active/ceased” state is that of **the legal unit at retrieval time**, not that of each establishment nor that at the contract notification. The profiles are embedded in `decp-cities.json` so that the JSON picker under `file://` works without a second file. No API call at site load. No points for the name, the state, an address, the age or the existence of a company.

**Not done:** Sirene history at the contract dates, RNE enrichment, ownership or family links, historical establishments, names for the 603 non-selected SIRENs. These limits are not replaced by assumptions.

### Reproduce and verify

From the project folder, browsing remains `python -m http.server` or `file://`, with no compilation. Optional data preparation:

```sh
# From the extracts present, with no network:
python tools/enrich-city-suppliers.py --offline
python tools/import-decp-cities.py --offline
node tools/update-cities-coverage.cjs

# New network snapshot (only replaces the new datasets):
python tools/import-decp-cities.py
python tools/enrich-city-suppliers.py
python tools/import-decp-cities.py --offline  # integrate the current profiles
node tools/update-cities-coverage.cjs

# Verification:
node tests/rules.cjs
node tests/cities.cjs
python -m unittest discover -s tests -p 'test_*.py'
# After starting the HTTP server on 8765 and installing Playwright outside the project:
node tests/browser.cjs
```

After a new snapshot, update the descriptive counters of the interface and of the README if the source changed. The historical source files and the two PDFs are not replaced by these commands.

Results: **124 historical assertions + 4,835 cohort assertions + 9 Python tests**, passed. Checks: coverage of all source keys, exact matches, conflicts, modification-only rows, deduplication, thresholds and denominators, score equality with/without names, restricted/unknown diffusion, filters, sorts, groupings and no mixing of cohorts. Chromium HTTP and `file://` picker tests passed for the new dataset with its embedded profiles; pagination without page shift. The two previous datasets keep their reference counts and results.

Grants remain a **future separate module**: no grant data is added or summed with the contracts in this delivery.

## Tours full BOAMP/TED notices — delivery of 16 September 2026

New dataset: **“Tours · full BOAMP/TED notices · 2025 and linked references”**, file `data/tours-notices.json`. These are **66 notice/lot versions, not 66 unique awarded contracts**. The dates displayed in their column are explicitly BOAMP publications; contract notification dates are not invented. Two “Notice publication” sorts and a “Notice content” filter find the procedure texts, criteria, corrections and TED XML. The same functions work over HTTP and with the `file://` JSON picker.

### Selection before examining the indicators, and real downloads

Buyer chosen before examination: **Commune de Tours, SIRET `21370261600011`**, BOAMP publications from **1 January to 31 December 2025**. BOAMP retrieval start: **2026-09-16T08:52:08.735633+00:00**.

```text
API: https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records
where: dateparution >= date'2025-01-01' AND dateparution < date'2026-01-01' AND donnees LIKE '%21370261600011%'
limit: 100
order_by: dateparution ASC, idweb ASC
```

**23 candidates in the year**, then exact `annonce_lie` and `contractfolderid` searches with no date restriction: **27 raw BOAMP notices**, **45 logged queries**. The SIRET in the text is only a candidate discovery: the import follows **ContractingParty → PartyIdentification → Organizations/Company → CompanyID** to confirm the buyer role. Joint purchases are kept with all their buyers and an explicit mention; none of their spending is attributed wholly to Tours.

**25 qualified notices**, of which **22 in 2025** and **3 linked references outside the period**. Two notices are excluded from normalization: `25-102354` and `24-42098`, whose resolved buyer is the **Syndicat des mobilités de Touraine (`20008510800013`)**, not the commune. They remain in the raw data, with the exclusion reason. The version/lot rows comprise **55 initial rows, 6 correction rows and 5 result rows**; 10 rows belong to joint purchases.

Independent TED search via **POST `https://api.ted.europa.eu/v3/notices/search`**: published buyer names and a ±45-day window around the BOAMP publication serve only to discover candidates. The request bodies, responses and errors are kept in `data/tours-notices/raw/ted-api-search-*.json` and `ted-manifest.json`. **The join is never made by name/date**: each XML must contain the exact notice UUID; its version number and the lot are verified separately. All the searches that actually returned fit in their page of 100 results; these searches are not an exhaustive review of every version of a procedure.

Successful TED downloads: **28 XML**, of which **27 UUIDs match the 27 raw notices** plus the old notice **`461026-2023`**, explicitly cited by `25-20885`. Among them, the **25 qualified notices** all have a matching XML; the 66 normalized rows have a UUID/version/lot match. Final TED download start: **2026-09-16T09:12:09.130796+00:00**; last logged download: **09:16:32.873486+00:00**. Candidates outside the scope and first unsuccessful attempts were also logged: an empty or HTML HTTP 200 does not count as an XML download. The current manifest is authoritative; `ted-manifest-initial.json` keeps an earlier, superseded attempt.

Files:
- `data/tours-notices/raw/api-records.json`: the 27 complete BOAMP records, including eForms `donnees`.
- `data/tours-notices/raw/manifest.json`: BOAMP queries and retrieval timestamps.
- `data/tours-notices/raw/ted-*.xml`: downloaded XML; “Official XML” and “Downloaded local XML” links in the details.
- `data/tours-notices/raw/ted-manifest.json`: provenance, UUID check, TED publications and download errors.
- `data/tours-notices.json`: self-contained normalized extract for the interface and file mode.
- `data/tours-notices-coverage.json`: counts, scope, exclusions, mapping and limits.

### Information actually usable

**Buyer explanations.** The structured fields `TenderingProcess/Description` and `ProcessJustification` are reproduced without paraphrase, with code, code list, path and source. **13 rows** carry a procedure text. The scope is **the whole procedure**, not necessarily the displayed lot. The `RegulatoryDomain` framework designates a directive/general basis, not an R2122 justification. The `false` code of the `accelerated-procedure` list is a declaration of absence of acceleration, not a justification of exclusivity. This scope provides no new evidence of an exclusive or urgent award.

Important example: `25-4887` announces an open call for local lots **1, 2 and 5**, while citing **R2122-8 for other lots**. The text is visible and searchable, but **does not make the three published lots “without competition”**. The eForms identifier `LOT-0003` and the local reference `5` are kept separately. The existing contract-level R2122 citation filter does not extend this global declaration to DECP contracts.

**Award criteria.** **25 rows with criteria**, **68 criterion/method entries**, of which **24 rows with numeric parameters**. Only the `TenderingTerms/AwardingTerms` of the relevant lot is read; `SelectionCriteria` (candidate conditions) is excluded. The labels, descriptions, formulas, raw values and parameter codes are kept. The absence of a weight remains unknown, even if the text says “Cf. RC”. No percentage is invented from a unitless interpreted number. Example: `25-127301` publishes the values **40, 30, 20 and 10**, code **`per-exa`**, list **`number-weight`**, for quality, price, deadlines and environmental/social performance. These weights are displayed as context, with no additional vigilance points.

**Corrections and partial chronologies.** The eForms `ChangedNoticeIdentifier` fields reveal **two corrections**, although the BOAMP index marks them `etat=INITIAL`:
- `25-117276` → `25-127197`: five lots, deadline moved from **24 to 27 November 2025**, 12:00, published time zone `+02:00`.
- `25-119055` → `25-127301`: deadline moved from **24 November to 1 December 2025**, 12:00, published time zone `+02:00`.

**Nine notice/lot links** are documented by an explicit reference, a same procedure UUID and a same lot identifier. The sources and previous deadlines appear in a partial-chronology panel. The other notices sharing only a procedure UUID are presented separately as documentary leads, not as proof of an award to the lot. No financial value nor holder identity is transferred by these links. The old TED notice is kept without fabricating a match between its lots and later eForms identifiers.

BOAMP dates, TED publications and **dispatch** dates/times are separated. Only the lot’s bid deadline is used: an application or bid-opening date does not replace it. Time zones are kept as published, even if they surprise; no silent correction to Europe/Paris. Different versions and conflicts between sources are excluded from the calculation.

### What is not yet established

**0 period evaluated, 0 new indicator triggered.** Having the matching XML does not prove that the correction chain is complete, nor that the relevant initial publication was recovered, notably in case of a relaunch. The short-period rule therefore stays disabled on this dataset. To avoid confusing this absence of calculation with a reassuring result, these rows display **“Not assessed · documentary context”**, not `0/100`. The explanations and criteria change no score of the existing datasets.

The buyer-profile documents are **linked but not downloaded**. Publications under another establishment SIRET, a non-indexed format or a spaced spelling can escape the initial textual search. No exhaustiveness of all of Tours’ purchases, no DECP merge, no sum of ceilings or expenses, no legal validation of the buyer’s explanations.

### Reproduction and tests

```sh
# Deterministic regeneration from the logged sources, with no network:
python tools/import-tours-notices.py --offline

# New network snapshot (does not touch the earlier datasets):
python tools/import-tours-notices.py
python tools/download-tours-ted.py
python tools/import-tours-notices.py --offline

# Tests:
node tests/tours.cjs
node tests/rules.cjs
node tests/cities.cjs
python -m unittest discover -s tests -p 'test_*.py'
# HTTP server on 8765 + test-only Playwright installed outside the project:
node tests/browser.cjs
```

The new importer handles BOAMP pagination and explicit UUID references; a new snapshot can therefore broaden the links found. Do not keep the descriptive counters of this snapshot if the sources change. No preparation script is needed to serve the static site.

Verified: **831 documentary assertions**, **124 historical assertions**, **4,835 six-municipality assertions** and **17 Python tests**, passed. Coverage: buyer versus mere mention, joint purchases, lot and version, selection criteria excluded, unknown/zero weights, citations without propagation, explicit extensions, sources and safe local paths. Chromium HTTP and `file://` tests, content filters, R2122-8 search, criteria/TED panels, sorting and pagination without page shift: passed. The earlier data and the two PDFs are preserved.

## Provenance of the BOAMP / CRC dataset

The dataset contains 3,000 lots imported from BOAMP, the two Mauges lots and the eight CRC dossiers documented below. The five additions come from two additional reports, not from five independent authorities. **All fictional examples have been removed.** `verified` means documented in a public source: automated transcription with schema checks and spot checks for the import, reading of the cited passages for the CRC dossiers. This is not a human review of every notice, an independent fact-checking, nor a legal certification.

### BOAMP download: February–April 2025

**8,386 award notices downloaded** through the official API, covering the publications from **1 February to 30 April 2025 inclusive**. The window is on the publication, not the contract signing. The retrieval date is in `data/coverage.json`.

Endpoint: `https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records`

Exact query (`where`):

```text
nature='ATTRIBUTION' AND dateparution >= '2025-02-01' AND dateparution < '2025-05-01'
```

Paginated download of 100 notices, offsets 0 to 8,300, with retries on temporary errors. The 2,153 notices outside the expected eForms structure, notably FNSimple, are not mapped. The import follows the result, lot, winning offer, contract and organization identifiers to avoid attributing a global amount to the wrong holder.

After excluding results without an identified holder and ambiguous multi-awardee references, 16,002 rows were usable, corresponding to 15,432 notice/lot identifiers. **236 identifiers with contradictory variants** (notably different holders or amounts) were set aside rather than arbitrarily choosing a winner. Among the **15,196 unambiguous identifiers**, the first 3,000 after SHA-256 sorting of the `boamp-{idweb}-{lot-id lowercased}` identifier were kept. No selection by score, amount or offer count. This choice bounds the local file and stays deterministic; it does not make the sample representative of all public procurement.

Availability in the **3,000 new lots**:

| Field | Provided | Unknown |
| --- | ---: | ---: |
| Conclusion date | 2,978 | 22 |
| Offer amount in EUR | 2,248 | 752 |
| Total number of offers | 1,188 | 1,812 |
| Initial duration in months | 979 | 2,021 |
| Procedure classification | 2,926 | 74 |

**Transcription precautions:**

- Offers: only the eForms code `tenders`. The number of electronic offers (`t-esubm`) is a subset and is never substituted for the total; same for applications and SME offers.
- Amount: only `LotTender/LegalMonetaryTotal/PayableAmount` in EUR, finite and non-negative. No ceiling or notice total used instead. Consult the notice for its tax regime and scope.
- Supplier: all identified members of the winning group are gathered. Results with several winning offer or contract references are excluded from this conservative import.
- Duration: only `DurationMeasure` in `MONTH`, without truncating decimals. Durations in other units or expressed as dates remain unknown; renewals are not added.
- Award without competition: `true` only for `neg-wo-call`, `false` for the explicitly recognized competitive codes, `null` otherwise.
- Official finding: **`null` for all new lots**. No automatic matching with the audits and no claim of absence of irregularity.

Each row preserves the BOAMP notice link and its internal references. The dataset can still contain distinct notices about the same purchase (corrections notably): **do not sum the amounts as national spending**. The raw download data is not embedded: the site stays self-contained with the structured extracts and source links.

### Mauges Communauté — two reagent lots

[BOAMP, award notice 25-846](https://www.boamp.fr/pages/avis/?q=idweb:25-846), published on 7 January 2025. [Official JSON record](https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records?where=idweb%3D%2225-846%22&limit=1).

Lot 1, Stockmeier France, €548,100; lot 2, Lhoist France Ouest, €183,648. The eForms results indicate one offer received per lot, a conclusion on 19 December 2024 and an open procedure. The amounts are those of the winning offers, not framework-agreement ceilings nor observed payments. The published initial duration is **36 months**, with two renewals whose duration is not specified in the reproduced fields: we did not take over the 60 months of the initial example without evidence. No official finding about these lots is documented (`officialFinding: null`). An offer received is not necessarily an admissible offer: the detail respects that distinction.

### Rognac — 2024 Christmas market

[CRC Provence-Alpes-Côte d’Azur, publication of 25 August 2025 and responses](https://www.ccomptes.fr/fr/publications/commune-de-rognac-bouches-du-rhone-1).
[Original report PAR2025-0792](https://www.ccomptes.fr/sites/default/files/2025-08/PAR2025-0792.pdf), p. 16.

€140,362 excl. tax is the **total of several** entertainment contracts. The CRC notes a failure to compute the thresholds and spending outside the public-procurement procedure. This aggregate dossier does not allow claiming that an individual award exceeds €100,000: `directAward` stays `null`; only the official finding triggers. Individual dates and suppliers are not invented.

### Saint-Sébastien-sur-Loire — Station Nuage

[CRC Pays de la Loire, publication of 29 June 2022, report and response](https://www.ccomptes.fr/fr/publications/commune-de-saint-sebastien-sur-loire-loire-atlantique-1).

The official summary cites a design-build contract, **€167,000 excl. tax forecast**, with no negotiation or competitive tendering. It also highlights the professionalization of public procurement and the good management of the other procedures examined. The partner Le Voyage à Nantes is not arbitrarily filled in as the supplier. Signature date unknown in the reproduced extract.

### La Chapelle-sur-Erdre — installation at la Gandonnière

[CRC Pays de la Loire, report 2025-225 and responses](https://www.ccomptes.fr/fr/publications/commune-de-la-chapelle-sur-erdre-loire-atlantique-1).
[Original report](https://www.ccomptes.fr/sites/default/files/2025-06/ROD%202025-225%20Cne%20La%20Chapelle-sur-Erdre.pdf), section 2.4.2, pp. 33–37, in particular p. 36, notes 56 and 63.

Signature on 26 May 2021; **€289,263 excl. tax of initial order**, phases 1 and 2: €226,513 excl. tax of realization for the commune and €62,750 excl. tax of fees for the SPL. This is not the final cost of the realized phase. The CRC criticizes the invoked artistic exception and the procedure; the response arguments appear in the report. Consulting several artists is not equated with a compliant competitive procedure, nor with a single offer.

### Saint-André (Réunion) — stade de la Cressonnière

[Official publication, report and response](https://www.ccomptes.fr/fr/publications/commune-de-saint-andre-la-reunion-cahier-ndeg-2-la-situation-financiere-la-gestion-des).
[Report RER2021532](https://www.ccomptes.fr/sites/default/files/2023-10/RER2021532.pdf), p. 40, § 3.3.1.1.
[Official response](https://www.ccomptes.fr/sites/default/files/2023-10/REO2021532.pdf).

Lot 2 was entrusted to Prestige Construction after termination of the contract of the initially selected candidate. The CRC states that a new competitive process should have been organized, the initial procedure being completed. It cites an offer of **€339,258 excl. tax**, 33 % above that of the first holder. The notification date to Prestige is unknown: 10 May 2017 concerns the start of the previous holder’s contract and is not used as the date of the new contract. The initial award was competitive: the `directAward` field stays unknown rather than summarizing the whole process abusively.

### Mamoudzou (Mayotte) — four distinct dossiers from the same report

[Official publication — cahier n° 2, public procurement](https://www.ccomptes.fr/fr/publications/commune-de-mamoudzou-mayotte-cahier-ndeg2-la-commande-publique).
[Original report](https://www.ccomptes.fr/sites/default/files/2024-08/ROD2-MDZ-cahier2-et-sa-r--ponse.pdf).
[Official response](https://www.ccomptes.fr/sites/default/files/2024-08/Mamoudzou_r--ponse_ordonnateur.pdf).

| Dossier | Report passage | Amount scope |
| --- | --- | --- |
| Travel and trips | p. 15, § 2.1.1: more than 300 payment orders to the same provider outside a framework agreement | **At least €760,000**, 2018–October 2023; aggregate |
| School cleaning | pp. 15–16, § 2.1.2: interventions without respecting competition rules | **More than €200,000** paid in 2023; aggregate, not an exact amount |
| School guarding, lots 1 and 3 | pp. 17–18, § 2.2: substantial modification of the offer during the procedure, award judged irregular | **About €500,000**, total of the 19 invoices outside a framework agreement from November 2022 to August 2023, not the initial award amount |
| School snacks | pp. 19–21, § 2.3.1: orders continued outside competition | **At least €10.38m**, September 2019–April 2023; several providers |

The providers not named in the passages remain unknown. The four dossiers are sets of orders/services, not four individual awards exceeding a threshold: `directAward` stays `null`. For the guarding, 12 months designates the initial duration; two renewals are specified in a note.

The report presents the commune’s responses, notably the continuity constraints of cleaning, the claimed consultation of three agencies for the travel and the commitment to improve contract monitoring. These explanations remain accessible with the finding. These are CRC observations, not claims of criminal conviction.

**None of these five new dossiers was matched with certainty to one of the 2025 BOAMP lots.** They are added as self-contained audit dossiers; no flag is propagated to other purchases of the commune or the supplier. In total: three dossiers about an identified contract and five about sets of orders/services. The eight findings come from five different publications, over distinct periods. This selection does not allow comparing the regularity of local authorities or territories.

The **“Show only official findings”** filter isolates the eight dossiers. Each detail keeps the source publication, the original report, the passages and, for the new dossiers, a direct link to the response. `findingScope` distinguishes `contract` and `aggregate`. `amountQualifier` keeps the bounds (`at-least`, `more-than`) and the roundings (`approximate`) displayed ≥, > or ≈. The amount filter and sort use the cited value: a bound is not turned into an estimate of the exact amount.

### Real comparisons

The comparison contracts now come from the same public import, with no prior filtering on anomalies. Unchecking “Show only flagged contracts” allows comparing them. A zero index can also result from unknown fields: the table shows “Partial data” when information needed by the rules is missing. An unflagged contract is not certified regular.

The links to the audit publications give access to the original documents and the responses. Keep these links and the precise passages in any enrichment. Never pass off a simulation or an unverified lead as a finding of an authority.

## BOAMP consultations — delivery of 15 September 2026 (score 2.1)

Third active dataset in the selector: `data/consultations.json`. It uses the same search, CPV filters, sorts, groupings and `file://` JSON picker. The rows are **consultation notices, not awarded contracts**: contract date, holder, amount and offers remain unknown. Publication dates and deadlines appear in the details. No merge with the two previous datasets.

### Download actually performed

Retrieval: **2026-09-15T06:14:08.554906+00:00**. Source: the already-cited BOAMP/DILA API. Exact query:

```text
where=dateparution = date'2025-02-03' AND nature = 'APPEL_OFFRE' AND etat = 'INITIAL'
limit=10
order_by=idweb ASC
```

**200** notices match; the scope is deliberately bounded to the **first 10 identifiers**, fixed before examining the scores. All are FNSimple (not eForms). The retained references are `25-12212`, `25-12213`, `25-12214`, `25-12216`, `25-12217`, `25-12218`, `25-12220`, `25-12226`, `25-12228`, `25-12229`. This choice reduces the volume but is not representative.

Link search: `where=annonce_lie = 'IDENTIFIER'`, `limit=100`, order `dateparution ASC, idweb ASC`, then continuation by the correction identifier. **12 documented queries**, **14 raw notices kept**, of which **one correction** and **three results**. The exact URLs, dates, counts and exclusions are in `data/consultations-coverage.json`; the structured responses are in `data/consultations-raw.json`.

- `25-12214` → **25-22678**, published on 27 February: the text moves the deadline from 7 March to **14 March 2025 at 12:00**. Exact text visible in the panel; time zone not specified in that text, no invented conversion.
- `25-12212` → result `25-50122`; `25-12213` → `25-36651`; `25-12226` → `25-31439`. Explicit `annonce_lie` links, **at the notice level only**: no holder nor amount transferred to a lot, no DECP matching.
- **16 lots described** in `25-12220`: identifiers transcribed from the explicit prefixes of the descriptions, CPVs and raw deadlines preserved and displayed. No artificial splitting of an amount.
- Internal consultation references kept separately from the unknown procedure UUIDs. FNSimple provides no version number here: `version: null`, state `INITIAL`/`RECTIFICATIF` kept in `publicationState`. The adapted procedure is read in `procedureAdapteeO`, not equated with an open call from the API label “OUVERT”.
- The eight-digit CPVs are displayed without fabricating a check digit. The original values, notably the times without a time zone, remain in the raw data.

### Ninth rule, deliberately not triggered in this extract

`getBiddingPeriod` is a separate, testable function. Cumulative conditions: explicitly verified complete chain, identified procedure and lot, a single initial notice, distinct orderable versions and linked corrections, HTTP(S) sources, procedure `open` and acceleration **explicitly false** in each version, deadlines with a time zone and a consistent chronology. Missing information, contradictory versions, shortened period, correction after the old deadline or ambiguous simultaneous publications: calculation unavailable. An award notice is never a consultation start.

Signal if the upper bound of the period is **strictly below 15 calendar days**, from **midnight UTC on the day of the initial BOAMP publication** to the last explicit deadline after extensions. This convention prudently overestimates the duration relative to the unknown actual publication time. Fixed weight **12**, competition family: **maximum**, never a sum with a single offer or a direct award. Editorial thresholds, neither a legal minimum nor a statistical comparison between similar contracts. The BOAMP publication can be later than a TED publication: completeness and the choice of the relevant publication require documentary verification before activation.

**Coverage: 0/10 chronologies evaluable, 10 excluded, 0 signal.** The `annonce_lie` searches do not demonstrate that all corrections were published or correctly linked. Acceleration and version numbers are unknown. The rule is therefore not artificially activated to produce results. The absence of signal remains an absence of calculation, explicitly visible. The eight previous rules and their results are unchanged; their “Score 2.0” table below remains the basis of version 2.1, completed only by this rule.

### Reproduction and tests

```sh
python tools/import-consultations.py --offline  # regenerate from the local raw data
python tools/import-consultations.py            # new network snapshot, replaces this third dataset
node tests/rules.cjs
python -m http.server 8765
# In another terminal, test-only dependency, outside the site:
npm install --prefix /tmp/procurement-browser playwright
node tests/browser.cjs
```

The import script uses only the Python standard library; it is not a build step nor a browsing dependency of the site. The browser tests use Chromium `/usr/bin/chromium` and Playwright outside the project (path customizable via `PLAYWRIGHT_PATH`).

Verified: **107 rule/data assertions** (15-day threshold, unknowns, conflicts/duplicates, source links, extension, accelerated procedures, family maximum, filters, 12 sorts, four groupings, historical counts). Chromium HTTP and `file://` tests with JSON selection, deadline-shift display, period filter, sorting/grouping and pagination: passed. The vertical position of the page and the table height are identical before/after “Next”. The historical files keep **3,010 / 2,594** rows, **8** findings, **13** increases, **9** repeated low competitions and **8** concentrations. The two PDFs were not modified.

**Still to do for the consultations:** complete verification of a chain enabling a first actually evaluable observation; historical Sirene/RNE enrichment. The new Tours dataset described above now provides independent TED downloads and eForms lots, without certifying the completeness of the calendars. The six-municipality DECP cohort over 24 months and the current public names are now added in the dedicated section above; they do not constitute a historical verification. This delivery provides the downloads, the chronological navigation and the conservative rule, not yet a reliable set of comparable periods.

## Improvement leads — history of the v2.x proposals

The separation of findings and coverage proposed in this section has since been implemented in v3; the weight proposals below remain an archive. Refer to [the active method](docs/score-v3.md).

The conservative variants **declared amount increase**, **repeated low competition**, **concentration by award count** and **repeated direct awards** are active on the DECP history. Concentration by value and the other proposals below remain unactivated. None of these choices is statistically or legally validated; the current ranking is described at the end of the document.

### Indicators to prioritize

| Priority | Proposed signal | Calculation / data needed | Limit to display |
| --- | --- | --- | --- |
| 1 | Large increase after award | Initial amount and modified amount of the **same contract and same scope**; exploratory example: increase > 20 % and > €50,000, excluding an identified indexation | Amendments and scope changes can be legitimate; the proposed thresholds are not legal thresholds |
| 1 | Repeated low competition | Share of competitive calls at a single offer for a buyer and a CPV family over 24–36 months; denominator = contracts whose total offer count is known | Do not count electronic offers only as the offers; a specialized sector can be structurally not very competitive |
| 1 | Unusually short bidding period | Publication date of the initial notice to the last deadline, compared to comparable procedures and subjects | Corrections, accelerated procedure and urgency can explain the period; do not use the award notice as the start |
| 2 | Concentration of awards | Share in count and value of one holder (SIREN) at a buyer, by CPV and period; documented minimum of observations | Framework agreement, central purchasing body, consortium or specialized operator; our three-month sample is not enough |
| 2 | Orders close to a threshold | Repetition of orders of the same need, buyer and period close to the **threshold applicable at the date and type of purchase** | Aggregation index to examine, not proof of splitting; small purchases absent from publications create a major bias |
| 2 | Atypical duration in its category | Known maximum duration, renewals included, compared to the contract type and the CPV | Preferable to a single ten-year threshold; do not mix initial, maximum and effective durations |
| 3 | Atypical unit price | Price per unit and comparable quantities, technical characteristics, delivery, taxes, date and inflation | A high total amount or an amount/CPV is not enough to conclude an overrun |

For statistical comparisons, start with sufficiently large CPV, contract/procedure type and year groups (for example 30 comparable observations, threshold to be tested). Publish the group and the number of comparables; otherwise display “comparison unavailable”. No indicator may be inferred from an aggregate CRC amount as if it were an individual award.

Do not automatically assign points to the youth of a company, its small workforce, a shared address, a different NAF code, financial difficulty or a declared HATVP link. These are contextual elements that can have ordinary explanations, not proofs of illegal conduct.

### Better ranking: separate signals, official elements and coverage

A later lead, **not activated in score 2.0**, is to completely separate authority findings and heuristics. One could then present three independent elements:

1. **Documented official finding**: authority, report date, passage, scope, response, possible remedy or follow-up. An audit and a judgment are not equivalent. Keep it as an explicit filter or sort, without automatically adding 50 points to the heuristics.
2. **Heuristic vigilance index**, used only to prioritize a reading. Illustrative proposal: competition 0–40, evolution/execution 0–40, repetitions/concentration 0–20. Within each family, take the **maximum** of the correlated rules rather than summing them (a single offer, repeated low competition and a direct award can tell the same story). Total capped at 100. The weights are editorial choices to be tested, not a probability.
3. **Data coverage**: number of applicable rules actually evaluable, for example “3/7”. Unknown ≠ negative. Do not artificially multiply the score to compensate missing fields; display “insufficient data” and avoid a misleading global ranking if the coverage is too low. Data quality must stay separate from the characteristics of the contract.

A first version could even drop the composite score and offer three explicit sorts: number of flagged families, amount and date, with the official-findings filter. A family count is often more readable than a falsely precise 73/100.

Before adoption: have a flagged **and an unflagged** sample reviewed, test the rank stability when the weights change, publish the rule version and the precise reasons. The audited dossiers are selected, not an exhaustive ground truth: do not treat all contracts without an audit as negative cases to train a model.

### Priorities for the next enrichment

1. **Initial BOAMP/TED notices and corrections**: deadlines and calendar changes, for an indicator of an unusual bidding period in a comparable procedure. Do not take the award notice as the consultation start.
2. **DECP history extended to buyers chosen before examining the scores**: better coverage of the same CPVs and contracts, to validate concentration/repetition and examine recurring purchases close to thresholds. Small purchases absent from publications prevent any automatic conclusion of splitting.
3. **Historical Sirene and RNE/INPI within diffusion limits**: names, establishments, successions and identifiers, to make the groupings reliable. Age, a shared address or workforce do not become automatic suspicion points.
4. **Buyer-profile documents, deliberations and communicable pieces**: specifications, justification of the derogation, price breakdowns, amendments and service-done elements. They allow a scope and chronology review, or even comparable unit prices. A non-accessible piece is “to be obtained”, not a proof of a failure.

The explanations and counterexamples must be searched for at the same time as the signals. The notices and the raw data alone do not allow proving that a service was invoiced twice, that a remuneration preceded the notification or that an artistic price is excessive.

### Other useful public data

| Source | Usefulness | Join and precautions |
| --- | --- | --- |
| [DECP — consolidated files, Ministry of Economy](https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-fichiers-consolides) | Amount, procedure, CPV, duration, holders and modifications depending on version and coverage | Buyer SIRET + contract identifier + lot; keep the versions. Do not sum the same amounts for each co-holder or amendment |
| [Tabular consolidated DECP — Colmo](https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-consolidees-format-tabulaire) | Easier-to-cross CSV/Parquet, modification history | **Third-party consolidation**, not a control authority; preserve the original sources and check the transformations. Public downloads, this service’s API announced as subscription-based |
| [BOAMP / DILA](https://www.boamp.fr/) and [TED / EU Publications Office](https://ted.europa.eu/en/simap/developers-corner-for-reusers) | Initial notices, corrections, awards, CPVs, offers and deadlines depending on availability | Chain the notices and the lots; a BOAMP notice and a TED notice can describe the same purchase. No double counting |
| [Sirene / Insee](https://www.data.gouv.fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret) | Normalize the companies, SIREN/SIRET, creation dates, activity and administrative state | Use the history at the contract date; respect the diffusion statuses and the restrictions on personal data |
| [BODACC / DILA](https://www.data.gouv.fr/datasets/bodacc) | Transfers, changes and collective procedures: execution context and continuity of the holder | SIREN and dates. A collective procedure is an economic context, not an indicator of corruption |
| [Cour des comptes and CRC](https://www.ccomptes.fr/fr/publications), [Légifrance](https://www.legifrance.gouv.fr/) and [administrative-justice open data](https://opendata.justice-administrative.fr/) | Reports, decisions and documented follow-ups | Manual matching to the exact contract; read scope, date, anonymization, response and possible cancellation/remedy. Do not extrapolate from a commune name |
| [HATVP — open data](https://www.hatvp.fr/open-data/) | Publishable interest declarations, to contextualize a precisely documented dossier | Partial coverage and changes over time; the name alone is insufficient to identify someone, no personal link inferred nor automatic score |
| Deliberations, budgets and public-procurement documents published by the local authorities / buyer profiles | Authorizations, consultation pieces, amendments and explanations sometimes absent from the notices | Dispersed formats; documents communicable subject to protected secrets, not always available as open data. An access request may be necessary |

**Recommended next work:** extend the history to more buyers with a selection independent of the signals, verify the completeness of the modifications, then establish really documented BOAMP/TED/DECP matchings. Keeping the deadlines and corrections will make it possible to test the bidding periods. The identifiers, the 24-month cohort, the new signals and a first documented project are present, but not the cross-source merge nor the guarantee of coverage of all spending.

All this can stay static: downloads and matchings performed occasionally offline, then publication of small local JSONs. No application server nor database is needed to browse the results. Data requiring authentication or restricted access must not be embedded without redistribution rights.

## Rules and extension — archive of the 2.0 scale

**Archive, unused by the site since v3.** For a new active rule, use `getAssessment` with an applicability state, an evaluation state, a family and a documented weight; do not modify the historical formulas below. The earlier engine is frozen in `tools/legacy/scoring-v2.1.js` only for comparisons and tests.

### Score 2.0 — old variable, transparent and bounded levels

The score is on **0–100**, with no renormalization by dataset or filter. 100 represents the configured maximum vigilance; the first result of a dataset is not artificially raised to 100. Zero indicates the absence of triggered rules, never a certification of regularity. An expensive contract without a signal gets **no points for its amount alone**.

`T(m)` designates the number of thresholds reached by a known amount in euros: **100,000, 500,000, 1 million, 5 million, 10 million**. Below €100k or if the amount is unknown, T = 0; T is capped at 5. Unknown values remain explicitly flagged as partial data, with no extrapolation nor artificial compensation.

| Indicator and condition | Raw weight | Family |
| --- | --- | --- |
| Single declared offer | `8 + 3 × T(amount)`; **5 only if direct award**, where an offer is expected | Competition |
| Direct award ≥ €100k | `25 + 5 × T(amount)`: 30 to 50 | Competition |
| Repeated low competition, thresholds documented above | `20 + 2 × T(amount)`, base 30 if share ≥ 80 %, cap 40 | Competition |
| Concentration: same SIREN with ≥ 60 % of contracts to the single known holder, ≥ 10 observations and ≥ 80 % coverage, same buyer/CPV3/period | Base 12; 20 if share ≥ 80 %; 25 if ≥ 95 %; + T(amount), cap 30 | Competition |
| At least 3 distinct contracts without competition ≥ €100k, same SIREN/buyer/CPV3/period; applied only to contracts that themselves satisfy these criteria | `25 + 5 × T(amount) + min(10, 2 × (count − 3))`, cap 55 | Competition |
| Declared duration ≥ 120 months | `8 + 5 × floor((months − 120)/60) + T(amount)`, cap 25 | Execution/duration |
| Analysable increase > 20 % AND > €50k | `15 + 5 × T(increase in euros)`; +5 if increase ≥ 50 %, +5 if ≥ 100 %, cap 40 | Execution/duration |
| Documented official finding | 50, independent of the amount and of the legal gravity | Finding |

**Score = min(100, competition maximum + execution/duration maximum + finding).** All badges remain visible, but correlated signals of the same family are not summed. The detail displays the raw weights and the retained family calculation. The requested label “> €100k” does include the exact €100,000 threshold.

Example: a direct award of €120k is worth 30 points; €1.4m is worth 40; €12m is worth 50. A single offer in these awards is worth 5 but is **not added** to the stronger signal. The TRE contract is thus at 40/100, not arbitrarily at 100. Membership of the Paris project changes no score of its providers.

Badge levels (raw weight): low < 12; moderate 12–24; high 25–39; very high ≥ 40. These are vigilance levels, not legal gravity. Score colors: 0 green, 1–19 light green, 20–39 yellow, 40–69 orange, 70–100 red. **Zero with partial data is grey**. Numbers, labels and explanations always double the color.

Concentration counts contracts, not a sum of amounts. It excludes groups with contradictory initials, duplicated identifiers and unmatched holders. A SIREN is only derived from an explicitly typed 14-digit SIRET or a typed SIREN; consortia are not arbitrarily attributed to their first member. The coverage concerns the eligible published contracts of the cohort, not all actual purchases. Framework agreements, specialized operators and legal exceptions can explain concentration and repetition.

In the historical v2.0 snapshot: **8 contracts trigger the concentration**; **none crosses the repeated-direct-award criteria**. The rule exists, but no result is invented to fill it. The 13 increases and 9 repeated-low-competition cases remain detected. The score remains an editorial weighting not statistically validated. To add a rule, use `add(id, label, weight, family, explanation)` in `getIndicators`, then document thresholds, exclusions and family; no hidden weighting by the reputation of a person or a local authority.

Each record carries the requested fields, with `null` for the unknowns. Amounts are numbers in euros, without separators; dates are `YYYY-MM-DD` strings or `null`. Do not replace an unknown contract date with a report date. `dataStatus` is `verified`, `unverified` or `synthetic`. The additional fields `sourceReference`, `amountBasis`, `dateNote` and `notes` explain the context and scope. For an official finding, the loader requires `verified`, an HTTP(S) URL and `sourceReference`: **this does not automatically verify the authority’s reliability**, which remains to be checked by humans. Support of the `synthetic` and `unverified` statuses remains available for personal files, but no record of the provided dataset uses these statuses.

JSON strings are inserted as text, never as HTML. URLs other than HTTP(S) are refused. An invalid dataset displays an explicit error without keeping a stale table. No browser storage, tracker or data transmission; only voluntarily opened source links leave the site.
