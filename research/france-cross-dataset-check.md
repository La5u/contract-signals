# France: cross-dataset consistency check

Date: 2026-10-08. **Read-only: no data, scores or code were changed.** This is an assistant-led comparison of published values across sources. Agreement between sources is not proof of truth, and disagreement is not proof of error.

## Sources compared

| Dataset | Our source | Snapshot |
| --- | --- | --- |
| `decp-cities.json` (six cities, 1,864 contracts) | Ministry API `decp-2022-marches-valides` | 2026-09-15 |
| `decp-history.json` (Paris/Ardèche, 2,594) | same Ministry API | 2026-09-25 |
| `contracts.json` (BOAMP sample, 3,002 lots + 8 audits) | BOAMP API | 2025 sample |
| National consolidated DECP (private cache, 3.3M rows) | data.gouv.fr / Colmo `decp.parquet` | 2026-10-04 |

The national file aggregates the buyers' own feeds: Paris = `atexo_maximilien`, Nantes = `atexo_nantes_metro`, Rennes = `megalis_bretagne`, AWS buyers = `aws_marches-publics.info` plus a scraped copy.

## 1. Our DECP cohorts versus the national file (same buyer, same `id`, same notification date)

**Amounts (one value on each side):**

| Cohort | Equal | Different |
| --- | ---: | ---: |
| Six cities | 1,043 | **51** (all Nantes) |
| Paris/Ardèche | 1,797 | **433** (427 Paris, 6 Ardèche) |

Patterns in the differences:

- **Paris: about 90 contracts are 10 EUR in our copy** where Paris's own feed has a substantial value, e.g. `2024F13023` 10 → 600,000; `2025F02650` 10 → 12,600,000; `2025S00769` 10 → 2,850,000. The 10 EUR is a placeholder, typically on framework agreements.
- **Exact multiples:** ×2 (32 Paris, 3 Nantes), ×4 (10), ×10, ×½ and ×¼. These are consistent with annual versus full-term amounts, or maximum versus estimate. Example: `2025S02911` is 5,400,000 in our copy, 21,600,000 in Paris's feed, and 21,600,000 as the maximum in BOAMP award notice 25-45958.
- **Single-digit differences** (28 Paris): `2024S13145` 1,399,840 vs 4,399,840; `2024S12679` 64,750 vs 124,750. They look like data-entry corrections on one side; the correct side is unknown.
- **National value 0 where ours is positive:** Nantes `2024F00005` (250,000 vs 0) and Paris `2024F04704` (39,900 vs 0).
- **Nantes:** mostly moderate differences, e.g. 142,232.40 vs 160,000, and estimates versus rounded maxima. Two are extreme: `2025S00179` 1 → 220,000 and `2025S00243` 65 → 130,000.

**Other fields, where the same contract is matched:**

- Six cities: offers 6 differ out of 1,621, duration 2, CPV 1. Procedure all equal.
- Paris/Ardèche: offers, CPV and procedure all equal; duration 1 differs.

**Paris "conflict" pairs (355, excluded today).** Every pair is two Ministry rows identical except the amount. Paris's own feed holds **one** value per contract: the higher of the pair for 278 and the lower for 77. Pair `2024S05075` (200,000 / 65,029) has a BOAMP award notice (25-21317) whose lot maximum value is **200,000**, matching Paris's feed. The pairs therefore look like two published versions of one contract's amount, of which Paris now publishes one. They are not separate contracts. This is not established for all 355.

**Contracts missing from our cohorts.** The national file has initial rows notified in 2024–2025 and published before our snapshot date that our raw Ministry data lacks entirely: **227 for the cities** (mostly Nantes, Rennes and the AWS scraped copy) and **387 for Paris** (`atexo_maximilien`). Our source is the Ministry's *valid* contracts dataset, which may exclude records failing validation. That is an unverified explanation. Further keys exist where the same `id` is present but with a different holder or value (298 cities, 464 Paris), and 325 city keys are scraped full-length `id`s of truncated ones we already hold (see `research/decp-identifier-collisions.md`).

## 2. BOAMP sample versus DECP

- **Direct overlap with our DECP cohorts:** 9 lots (7 Paris, 2 Nantes).
  - One matches exactly (`boamp-25-47556-lot-0001`, 1,500,000).
  - Paris `25-45958` lot 5: BOAMP 13,200,000 vs our 3,300,000; Paris's feed says 13,200,000.
  - Paris `25-21329`: BOAMP 2,382,511 (maximum) vs our 155,200; Paris's feed says 2,155,200.
  - Paris `25-37616`: our DECP amount is 10 EUR.
  - The Nantes kitchen lots link to DECP rows that have amounts where BOAMP has none, including newly split row `2025F00016-1`.
- **BOAMP references embed the DECP `id`.** Paris notices print contract references such as `20242024S05075` (DECP `2024S05075`) and `2025S029110000` (DECP `2025S02911`), so exact linkage is possible for Paris.
- **Against the national file (all buyers):**
  - 1,242 BOAMP lots have no usable holder SIRET (placeholders) and cannot be linked; 675 have no national row for buyer + holder; 436 have buyer + holder but no same-date row; **649 match** on buyer, holder and date.
  - Amounts among the 649: 221 equal, 27 within 1%, **202 differ**, 199 missing in BOAMP but present in DECP. Where the match is unique: 175 equal, 72 DECP higher, 52 DECP lower. Differences run both ways, so there is no single basis rule (winning offer, maximum, annual, total).
  - Offers: 64 equal, **15 differ**, 564 missing in BOAMP.
- **No BOAMP amount should be filled from DECP**, or the reverse, without a basis check. The two often measure different things.

## 3. Not cross-checked

- `tours-notices.json` (66) and `consultations.json` (10) are pre-award notices. They have no awarded amount or holder to compare.
- Linking them to Tours DECP contracts would need procedure references that DECP does not carry.

## Consequences (for decision; nothing applied)

1. **Paris/Ardèche amounts are the largest accuracy risk found so far.**
   - About 19% of comparable Paris contracts disagree with Paris's own current feed.
   - About 90 carry a 10 EUR placeholder. These distort amount-based logic: French direct-award threshold eligibility, minimum-amount filters and amount sorting.
   - Choosing a value requires an explicit rule and evidence; Paris's own feed plus BOAMP maxima are the strongest candidates.
2. **The 355 Paris pairs** are probably one contract each with two amount versions, the opposite of the city ID collisions. They should not be split. They could be resolved per contract using Paris's feed and, where available, BOAMP.
3. **Coverage gaps:** about 600 contracts present in the buyers' own feeds are absent from our Ministry-based cohorts.
4. **BOAMP and DECP amounts** frequently measure different things; keep them separate and labelled.

Private analysis: scripts were run offline against the cached national parquet, plus 4 BOAMP exact-ID searches (no results: Paris does not print DECP `id`s in searchable text). Requests are frozen in `~/.cache/contract-signals/paris-pairs-20261008/`.

## Implementation (2026-10-08, owner-approved)

- **Feed snapshot.** `tools/extract-decp-feeds.py` writes `data/decp-feeds-raw.json.gz`: 7,333 rows of the eight buyers' contracts with an initial notification in 2024–2025, including their modifications, from the national file. Holder names are removed and the manifest hash is checked.
- **Reconciliation.** `tools/decp_feeds.py` runs inside both DECP importers. Each record gets `amountSources` (every published value with its source) and `verification.status`. Rules, in the module docstring:
  - amounts of 0.01–10 EUR are placeholders and are never used as money;
  - the amount shown is the buyer feed's single positive value, then the Ministry's;
  - a positive amount wins over a zero;
  - a disagreement keeps `amountRange`.
- **Paris.** All 355 pairs are resolved by Paris's feed, which confirms one of the two values in each. 92 placeholders are now unknown. Two contracts still conflict on price type.
- **Added contracts.** Contracts present in a buyer feed but absent from the Ministry snapshot were added as single-source records: 355 for the six cities and 403 for Paris/Ardèche, after deduplicating aws and scraped copies. Records sharing an identifier are linked.
- **App.**
  - A Verification filter and an amount-sources panel.
  - The French direct-award threshold is evaluated at both ends of `amountRange` and is "not assessed" if they disagree.
  - Amount increase is off where sources disagree on the initial amount, so bases are not mixed.
  - New strings are translated.
- **Result:**

  | | Records | Agree | Disagree | Single source | Notice-checked |
  | --- | ---: | ---: | ---: | ---: | ---: |
  | Cities | 2,219 | 1,614 | 80 | 515 | 10 |
  | Paris/Ardèche | 2,997 | 1,797 | 788 | 412 | — |

  Score changes on existing Paris records: 11 new direct-award signals, where real amounts above the threshold had been hidden by placeholders or pairs; amount increase 24 → 19. Two city direct-award signals were dropped because the sources fall on both sides of the threshold.

## Random-sample accuracy check (step 4)

- **Protocol.** `tools/accuracy-sample.py`, preregistered: seed 20261008, frozen sample of 30 per verification status (all 10 notice-checked), and one bounded BOAMP award-notice query per contract (buyer, 10 days before to 400 days after notification, two title keywords).
- **Linking** requires the contract reference to contain the DECP id (exact reference for notice-checked lots, and the holder too when several lots contain it), or the winner's SIRET plus the same date. The amount is never a link key.
- **Deviations, disclosed:**
  1. Three test queries were run outside the sample to fix query syntax (keywords from the title part, full-text search).
  2. The first fetch stopped at a response over the 2 MiB cap; the remaining and truncated queries were rerun with a 12 MiB cap, and complete responses were not re-requested.
  3. After seeing that notices often carry placeholder SIRETs (coverage), but before seeing those outcomes, a third link was added: the winner's name agrees with the holder's current register name, on the same date.

| Status (n) | Linked notice | Amount confirmed | Contradicted | Notice gives no amount |
| --- | ---: | ---: | ---: | ---: |
| Checked against notice (10) | 10 | 10 | 0 | 0 |
| Sources agree (30) | **0** | — | — | — |
| Sources disagree (30) | 8 | 2 | 5 | 1 |
| Single source (30) | 6 | 4 | 1 | 1 |

**What this does and does not show:**

- **The notice-checked confirmations are not independent:** those lots were linked using the same notice.
- **No usable accuracy rate.** The sample cannot yield an overall rate: 76 of 90 non-curated contracts have no linkable award notice. Many are adapted-procedure or direct awards with no notice, and notices often carry placeholder SIRETs and references unrelated to the DECP id. The "sources agree" stratum is entirely unmeasured.
- **Disagreeing amounts.** The notice supports the amount we show in only 2 of 7 cases with a printed amount. In one (`2024S11872`), it supports the Ministry's value (10M) over Paris's feed (5M), so the feed-first rule chose wrong there. Others look like basis differences (lot shares, annual vs total) or scale errors (23,000,000 vs notice 23,000 and 95,000).
  - **Consequence:** an amount marked "sources disagree" should be treated as unreliable whichever value is shown. The app already stops amount-based checks from relying on either value unless all agree.
- **Single-source records** with a notice: 4 confirmed, 1 contradicted (Ardèche `2025SMG10`: 375,861.56 vs notice 725,689.88).
- **Next step for a real rate:** document review of a sample drawn only from contracts that must have an award notice (open procedures above EU thresholds), or buyer documents for MAPA contracts.

Private: `~/.cache/contract-signals/accuracy-sample-20261008/` (plan, responses, results).

## More sources, co-holders and ranges (2026-10-08, later)

**Buyers' own open-data contract lists.** These were found through the data.gouv.fr catalogue API, with one bounded query per buyer.

| Buyer | Source | Used | Why |
| --- | --- | --- | --- |
| Nantes | "Marchés publics conclus en 2024 / 2025 par la Ville de Nantes" (data.nantesmetropole.fr, LO 2.0): 387 + 442 rows with the buyer's own contract reference, amount, holder SIRET and name, date | **yes** | The 2024 file gives buyer SIRET `59840109300015`, which is absent from the register; its rows are City services and the title is "Ville de Nantes", so it is mapped to `21440109300015` and the published value kept |
| Bordeaux | Bordeaux Métropole datahub, "marchés publics … depuis 2024" (LO 2.0), restricted to the City: 362 contracts with full-length ids (e.g. `2024E0150M`), all holders, offers and amount | **yes** | — |
| Rennes | "marche-conclu" (ODbL) | no | Ends in 2022, has no amounts, and the licence is share-alike |
| Paris, Grenoble, Dijon, Tours, Ardèche | — | no | No current list found (searched data.gouv.fr and the web) |

- **Snapshot.** `tools/extract-city-portals.py` writes `data/city-portals-raw.json.gz`: 1,294 rows, holder names dropped, hashes in the private manifest.
- **Integration.** The rows join the buyer feeds as further routes, filtered to the cohort window. They are matched **after** the feeds, against the Ministry records and the feed-only contracts, so they confirm rather than duplicate them.
- **Result (cities):**
  - **Confirmations.** 1,792 records now have agreeing sources (was 1,614). Where they match, portal amounts agree with every agreeing or single source, with no contradictions in that set.
  - **New disagreements.** 7 previously single-source Nantes amounts now disagree, e.g. 0 vs 428,208.28; 269,738 vs 219,738; 1,000,000 vs 500,000.
  - **Added contracts.** 78 contracts appear only in the portals.
- **Majority (tie-break).** When strictly more publication routes give one positive amount than any other, with at least two routes, that amount is shown and recorded as `verification.majority`. An AWS profile and its scraped copy count as one route. This settles 64 city disagreements: mostly Nantes, where the portal sides with the Atexo feed, plus Bordeaux `2024E005-1`, where the Ministry and the portal (27,659.11) outvote the AWS profile (670,000).
  - All routes are the buyer's own declarations and may come from one internal system, so a majority is corroboration, not proof.
  - Amount-based checks still use the full range.
- **Ranges.** Every disagreement is displayed and exported as the range of published amounts (`amountLow`/`amountHigh`), never a single pick. The single value used for sorting is labelled as such in the record panel.
- **Co-holders.** The Ministry's flat table holds at most three holders per contract (`titulaire_id_1..3`). 67 of the 71 feed rows that shared an identifier with one of our records but named another holder were extra co-holders of that same contract (same amount and object). They were added with their source tagged; Dijon `2024VDPAO04` now lists 26 holders instead of 3. The other 4 rows were distinct contracts under truncated ids (Bordeaux `2024E0`, `2024S010`, `2024E010`; Grenoble `25A`); after deduplication they were added.

## Merged France DECP dataset and issues settled with the new sources (2026-10-08, later)

**Merge.** The explorer shows one dataset, "France · eight buyers — contracts · DECP" (5,286 contracts). It loads `data/decp-history.json` (Ville de Paris, Ardèche) and `data/decp-cities.json` (six municipalities) as one list.
- **Imports.** The two imports stay separate because they have different raw snapshots and rebuild commands. The buyers do not overlap and scores compare each buyer only with itself, so the merge changes no score.
- **Coverage index.** `data/decp-france-coverage.json` (`tools/build-decp-france-coverage.py`) summarises both parts.
- **Old links.** Links using `dataset=cities` open the merged dataset.
- **Tools.** The score-revision and data-quality tools read the registry's new list form.

**Issues settled:**

| Issue | Evidence | Result |
| --- | --- | --- |
| 2 Paris contracts excluded for conflicting price types | Both rows list the same three price types in a different order | Multi-valued price types are compared as sets. **Paris has no excluded contracts left.** |
| 45 "possibly the same contract" city clusters | Route references | 25 clusters (50 records): every member carries its own, different reference in another route (e.g. scraped full ids `2024VDPA031402` / `…03`), so they are separate contracts and the flag is cleared. 10 clusters: one member is confirmed by the buyer's own route and the others by none — the Paris-pair pattern (e.g. Nantes `2023S00165`: 1,550,497 and 3,100,994, the feed confirms 3,100,994) — so they are folded into one contract with both amounts kept. 10 clusters (25 records) stay flagged. |
| Majority votes by a self-contradicting route | — | A route that publishes two amounts for one contract no longer votes (e.g. the Ministry's pairs), so the majority note never counts it. |
| Dijon lot 6 (`2024VDAO017006`) holders | The award notice names one winner, register-linked; the buyer feed lists that same single holder; only the Ministry adds a second holder (the lot-8 winner) | The second holder moves to `unconfirmedHolders`, visible with the reason and not used by indicators |
| Dijon lot 8 (`2024vdao017008`) missing | — | Absent from every source (Ministry, feeds, portals). Not settled. |

Remaining open: 885 amount disagreements (788 Paris, 97 cities). These are shown as ranges; amount checks use the whole range. Also 25 possible duplicates and the offer-count disagreements, which need the buyers' offer-analysis reports.
