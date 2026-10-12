# France: cross-dataset consistency check

Review/implementation: **2026-10-08**. Source agreement is corroboration, not proof; differences require identity/basis checks. Earlier counts below describe the review stage, followed by final integration.

## Initial comparison

| Dataset | Our source | Snapshot |
| --- | --- | --- |
| `decp-cities.json` (six cities, 1,864 contracts) | Ministry API `decp-2022-marches-valides` | 2026-09-15 |
| `decp-history.json` (Paris/Ardèche, 2,594) | same Ministry API | 2026-09-25 |
| `contracts.json` (BOAMP sample, 3,002 lots + 8 audits) | BOAMP API | 2025 sample |
| National consolidated DECP (private cache, 3.3M rows) | data.gouv.fr / Colmo `decp.parquet` | 2026-10-04 |

The private national file aggregates buyer feeds: Paris Atexo Maximilien, Nantes Atexo Métro, Rennes Mégalis, AWS profiles and scraped copies. Match DECP on buyer, ID and notification date, with one amount each:

| Cohort | Equal | Different |
| --- | ---: | ---: |
| Six cities | 1,043 | **51** (all Nantes) |
| Paris/Ardèche | 1,797 | **433** (427 Paris, 6 Ardèche) |

- Paris: about **90** Ministry amounts of **10 EUR**, usually framework placeholders (`2024F13023`: 10/600,000; `2025F02650`: 10/12,600,000; `2025S00769`: 10/2,850,000).
- Multiples include **×2 (32 Paris, 3 Nantes), ×4 (10)**, ×10, ×½, ×¼. Annual/full-term or maximum/estimate differences are possible, not established. `2025S02911`: **5.4M/21.6M**, BOAMP **25-45958** maximum **21.6M**.
- **28 Paris single-digit differences**, e.g. `2024S13145` **1,399,840/4,399,840**, `2024S12679` **64,750/124,750**; correct side unknown.
- National zero versus positive: Nantes `2024F00005` **250,000/0**, Paris `2024F04704` **39,900/0**. Nantes extremes: `2025S00179` **1/220,000**, `2025S00243` **65/130,000**; other differences include **142,232.40/160,000**.
- Other fields: cities offers **6/1,621** differ, duration **2**, CPV **1**, procedure equal. History: offers/CPV/procedure equal, duration **1** difference.
- **355 Paris pairs** differ only by amount; Paris feed chooses higher **278**, lower **77**. `2024S05075`: **200,000/65,029**, notice **25-21317** maximum/feed **200,000**. These look like versions, not separate contracts; initially not established for all.
- Missing raw Ministry initial keys: **227 cities, 387 Paris**, notified 2024–2025 and published before snapshots. Validation exclusion is an unverified explanation. Further differing-holder/value keys: **298 cities, 464 Paris**; **325** city full-length scraped IDs correspond to truncated IDs (`research/decp-identifier-collisions.md`).

## BOAMP comparison and coverage limits

- Direct cohort overlap: **9 lots (7 Paris, 2 Nantes)**. `boamp-25-47556-lot-0001` equals **1.5M**; **25-45958** lot 5 **13.2M/3.3M** (Paris feed 13.2M); **25-21329** maximum **2,382,511** versus Ministry **155,200**, feed **2,155,200**; **25-37616** DECP **10 EUR**. Nantes kitchen DECP amounts exist where BOAMP lacks them, including `2025F00016-1`.
- Paris printed references embed IDs, e.g. **20242024S05075**, **2025S029110000**. Text searches did not find them; private requests: `~/.cache/contract-signals/paris-pairs-20261008/`.
- National matching: **1,242** lots lack usable holder SIRET, **675** lack buyer/holder row, **436** lack same-date row, **649** match buyer/holder/date. Amounts: **221 equal, 27 within 1%, 202 different, 199 BOAMP-missing**. Unique matches: **175 equal, 72 DECP higher, 52 lower**. Offers: **64 equal, 15 different, 564 missing**.
- No universal amount-basis rule or safe cross-fill. Pre-award `tours-notices.json` (**66**) and `consultations.json` (**10**) have no award/holder counterpart; Tours linkage needs references absent from DECP.

## Owner-approved reconciliation

`tools/extract-decp-feeds.py` writes **7,333** 2024–2025 initial/modification rows for eight buyers to `data/decp-feeds-raw.json.gz`, stripping names and checking the manifest hash. `tools/decp_feeds.py` applies in both importers:

- `amountSources` retains all declarations; `verification.status` records agreement.
- **0.01–10 EUR** are placeholders, never money. Display buyer feed's single positive value, then Ministry; positive wins over zero. Keep `amountRange` on disagreement.
- Paris feed confirms one alternative in every **355** pair; **92** placeholders become unknown. Two price-type conflicts initially remain.
- Add feed-only contracts after AWS/scraped deduplication: **355 cities, 403 history**, linking shared IDs.
- UI adds verification filtering/source panel/translations; direct-award checks evaluate both range ends, “not assessed” if they disagree. Disable amount increase when initial sources disagree.

Initial integrated result: cities **2,219** (1,614 agree, 80 disagree, 515 single-source, 10 notice-checked); history **2,997** (1,797 agree, 788 disagree, 412 single-source). Existing Paris scores: **11** new direct-award signals, amount increase **24 → 19**; two city direct-award signals dropped where ranges cross the threshold.

## Random-sample check

`tools/accuracy-sample.py`: seed **20261008**, **30 per status**, all **10 notice-checked**; bounded buyer/keyword query from **10 days before to 400 after** notification. Link by embedded DECP reference (holder too for multi-lot references), or holder SIRET/date; amount is not a key.

Deviations: query-syntax tests outside sample; response cap **2 → 12 MiB** after truncation, preserving complete responses; added current-register winner-name/date linkage after discovering placeholder-SIRET coverage but before those outcomes.

| Status (n) | Linked notice | Amount confirmed | Contradicted | Notice gives no amount |
| --- | ---: | ---: | ---: | ---: |
| Checked against notice (10) | 10 | 10 | 0 | 0 |
| Sources agree (30) | **0** | — | — | — |
| Sources disagree (30) | 8 | 2 | 5 | 1 |
| Single source (30) | 6 | 4 | 1 | 1 |

No overall accuracy rate: **76 of 90** non-curated rows have no linkable notice; “sources agree” is unmeasured. Notice-checked confirmations reuse the linking notice, so are not independent. Of seven disagreeing cases with amounts, only **2** support the displayed value; `2024S11872` supports Ministry **10M** over feed **5M**, exposing a wrong feed-first choice. Other cases suggest basis/scale differences (**23,000,000** versus **23,000/95,000**) without resolving them. Single-source contradiction: Ardèche **2025SMG10**, **375,861.56/725,689.88**.

Treat disagreements as unreliable whichever value is displayed; amount checks use the whole range. A real rate needs notice-required contracts or buyer MAPA documents. Private plan/responses/results: `~/.cache/contract-signals/accuracy-sample-20261008/`.

## Portal sources, ranges and co-holders

- Nantes 2024/2025 city lists: **387 + 442** rows, LO 2.0. Map invalid published 2024 SIRET **59840109300015** to **21440109300015** based on city title/services, retaining original.
- Bordeaux city subset: **362** contracts, LO 2.0, full IDs (`2024E0150M`), holders/offers/amounts. Rennes list ends 2022, lacks amounts and is ODbL; not used. No current Paris/Grenoble/Dijon/Tours/Ardèche list found.
- `tools/extract-city-portals.py` writes `data/city-portals-raw.json.gz`: **1,294** rows, names removed, private manifest hashes. Match after feeds to confirm existing records before adding.
- Cities agreeing: **1,614 → 1,792**; no contradiction with agreeing/single-source matches. **7** Nantes single-source rows newly disagree (**0/428,208.28; 269,738/219,738; 1M/500,000**). Add **78** portal-only contracts.
- Majority display needs at least two routes and strictly more votes; AWS/scraped count once. It settles display choice for **64** disagreements, including Bordeaux `2024E005-1` **27,659.11/670,000**. Routes may share one system; checks still use full range, exported as `amountLow/amountHigh`; sorting's chosen value is labelled.
- **67 of 71** differing-holder feed rows are co-holders with equal amount/object, added with source; Dijon `2024VDPAO04` grows **3 → 26** holders. Other **4** are separate truncated-ID contracts (Bordeaux `2024E0`, `2024S010`, `2024E010`; Grenoble `25A`), added after deduplication.

## Final merged dataset and remaining issues

Explorer: **“France · eight buyers — contracts · DECP”, 5,286 rows**, loading `data/decp-history.json` and `data/decp-cities.json`. Separate raw snapshots/rebuilds stay separate; buyers do not overlap, so merging changes no score. Coverage: `data/decp-france-coverage.json`, `tools/build-decp-france-coverage.py`. Old `dataset=cities` links open the merge; score/data-quality tools accept registry lists.

- Two Paris price-type conflicts resolve by comparing sets: no Paris exclusions remain.
- Of **45** possible-duplicate city clusters: **25/50 records** clear via different route references (`2024VDPA031402`/`…03`); **10** fold because one member alone has feed confirmation (Nantes `2023S00165`, **1,550,497/3,100,994**, feed higher). **10/25 records** remain flagged.
- Self-contradicting routes cannot cast majority votes.
- Dijon lot 6 `2024VDAO017006`: notice/register/feed confirm one winner; Ministry's extra lot-8 winner moves to `unconfirmedHolders`, visible but unused by indicators. Lot 8 **2024vdao017008** remains absent from all three source sets.

Open: **885 amount disagreements (788 history, 97 cities)**, shown/checked as ranges; **25 possible-duplicate records** and offer counts need buyer documents/offer-analysis reports.
