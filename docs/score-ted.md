# Portugal, Romania and Czechia method — TED eForms checks (v3.0 framework)

**Checks for the TED cohorts of Portugal, Romania and Czechia.** Same vigilance-index framework as [score-v3.md](score-v3.md): three families (competition, execution/duration and transparency, the last through late publication), family maxima, cap at 100, `null` = “Not assessed”, unknowns never counted as zero. The checks read only fields that EU eForms defines the same way in every member state (procedure code, the per-lot `tenders` statistic, buyer and winner identifiers, CPV). The countries are **separate cohorts**: their counts are never pooled, ranked or compared, and amounts are never converted (EUR for Portugal, RON or EUR for Romania, as published).

An editorial sorting tool, not a probability, not a measure of legal gravity, not a certificate of regularity. A signal describes a published declaration; it is not a finding of irregularity.

## Scope: what TED is and is not

TED publishes procedures **above the EU thresholds** only. Most national procurement (below-threshold purchases, many direct awards) is not in TED, so these cohorts show a buyer's largest EU-advertised procedures, not its procurement. Portugal's own portal (BASE) and Romania's (SEAP/SICAP) were not imported.

## How the checks were chosen

Written on 25 September 2026, before any notice of these cohorts was downloaded, and before any row was read. Weights reuse the French v3 ones where the concept is the same (single offer 12, award without competition 18, repetition and concentration curves), so that none was tuned on these results. Buyers are matched by published identifier and its spelling variants, never by name.

## The eight checks

| Check | ID | Family | Eligibility / trigger | Weight |
| --- | --- | --- | --- | --- |
| Single offer in a competitive procedure | `ted-single-offer` | Competition | Procedure code open, restricted, comp-dial, neg-w-call, innovation or comp-tend; the lot's published `tenders` statistic = 1 | **12** |
| Award without competition | `ted-direct-award` | Competition | Procedure code `neg-wo-call` (negotiated without prior publication) | **18** |
| Repeated single-offer awards | `ted-repeated-single-offer` | Competition | This award is single-offer; same buyer and supplier (national number) in ≥3 distinct notices | **12 at 3 → 30 at 10** |
| Repeated awards without competition | `ted-repeated-direct` | Competition | This award is `neg-wo-call`; same buyer and supplier in ≥3 distinct notices | **18 at 3 → 30 at 10**; Romania **1** since v3.7 |
| Concentrated awards | `ted-concentration` | Competition | Same buyer and CPV division (2 digits); ≥10 distinct procedures with an identified winner, ≥80 % of procedures with a national supplier number, share ≥60 % | **12 at 60 % → 30 at 100 %**; Romania **1** since v3.7 |
| Amount increase | `amount-increase` | Execution | **Out of scope**: modification notices are separate and were not imported | — |
| Short bidding period | `short-bidding-period` | Competition | **Out of scope**: the contract-notice chain was not imported | — |
| Long declared duration | `long-contract` | Execution | **Out of scope**: no duration threshold validated for these jurisdictions | — |

`oth-single` / `oth-mult` and unknown codes are not classified: the competition checks stay unknown. Supplier identity uses the national number (Portuguese NIF, Romanian CUI, Czech IČO) only when the winner's address is in that country; foreign or free-text identifiers are kept but not used for repetition or concentration. Joint winners (several members) have no single identity.

## Results

### Portugal (reproduced by `tests/national.cjs`)

Infraestruturas de Portugal (national, NIF 503933813), Comunidade Intermunicipal do Cávado (regional, 508779472), Município de Lisboa (municipal, 500051070). 442 award notices, 488 awarded lots retained (5 republished lots counted once, see [Republished lots](#republished-lots-counted-once-2026-10-15)); 137 winning results excluded because they name several winners (framework agreements: no single holder). **The 36 Cávado notices link no winning tender to their results, so the regional level yields one row**; the cohort was kept as announced rather than replaced after seeing data. One Infraestruturas de Portugal notice filed under another tax number (505065630) is outside the identifier match and not included.

| Check | Signals | Clear | Unknown | Out of scope |
| --- | ---: | ---: | ---: | ---: |
| `ted-single-offer` | 63 | 319 | 43 | 63 |
| `ted-direct-award` | 63 | 412 | 13 | 0 |
| `ted-repeated-single-offer` | 20 | 42 | 44 | 382 |
| `ted-repeated-direct` | 35 | 25 | 16 | 412 |
| `ted-concentration` | 0 | 234 | 254 | 0 |

126 lots with a signal, 356 zero, 6 not assessed before v3.1; with the late-publication check (11 lots), 136 / 352 / 0. The top of the ranking is Infraestruturas de Portugal's repeated negotiated awards without publication, for example railway signalling services from Siemens Mobility and vehicle leasing from LeasePlan: signalling maintenance on proprietary systems is a likely lawful exclusivity case, comparable to the proprietary-software maintenance at the top of the French ranking. Read the notice before drawing conclusions.

### Romania (reproduced by `tests/national.cjs`)

Ministerul Finanțelor (national, CUI 4221306), Județul Cluj (regional, 4288110), Municipiul Cluj-Napoca (municipal, 4305857). 299 award notices, 321 awarded lots (35 republished lots counted once); 289 multi-winner framework results excluded. Amounts in RON or EUR as published.

| Check | Signals | Clear | Unknown | Out of scope |
| --- | ---: | ---: | ---: | ---: |
| `ted-single-offer` | 125 | 186 | 6 | 4 |
| `ted-direct-award` | 4 | 317 | 0 | 0 |
| `ted-repeated-single-offer` | 42 | 70 | 19 | 190 |
| `ted-repeated-direct` | 0 | 0 | 4 | 317 |
| `ted-concentration` | 0 | 43 | 278 | 0 |

**v3.7 (approved 2026-10-15):** on Romanian rows, repeated awards without competition and concentration score 1 point each. In Competition Council bid-rigging decisions (20 decisions, 17 buyers, one procedure per decision) repeated awards without competition were rarer than among the same buyers' other contracts (LR 0.38) and concentration barely more frequent (6 % vs 3 %, LR 1.09, fails the holdout); see [the results](../research/calibration/romania-colombia-results-2026-10-15-audit.md). Neither check fires in this cohort, so no score changes. Portugal and Czechia keep the editorial points.

**Correction (2026-10-20):** the research script counted a contract as clear when its buyer/year/CPV group had fewer than 10 contracts with an identified winner; the plan's rule (the explorer's) makes it unknown. Recomputed (`tools/romania-bid-rigging-checks.py`, [results](../research/calibration/romania-bid-rigging-results.md)): one procedure per decision, weighted by appeal outcome, 9 % vs 6 %, LR 1.02 (was 1.09); all procedures, the current decision rule, 1 % vs 6 %, LR 0.49 (was 0.32). Still no points from labels: the 1 point stands.

129 lots with a signal, 192 zero, 0 not assessed before v3.1; with the late-publication check (12 lots), 138 / 183 / 0. 128 of 314 lots with a published offer count had a single offer. Example lead: one supplier won outdoor fitness equipment in several separate Cluj-Napoca notices, each with one offer.

### Czechia (added 2026-09-26; reproduced by `tests/national.cjs`)

Announced on 26 September 2026 before any notice XML was downloaded, from TED search totals of a candidate list (Ministries of the Interior, Defence, Health, Justice and Finance; the South Moravian, Moravian-Silesian, Vysočina, Olomouc and Plzeň regions; Brno, Ostrava, Plzeň, Olomouc and Prague): per level the largest at most 500 notices. Set aside for volume: the Ministry of the Interior (2,048) and the Ministry of Defence (1,843); Prague (493) was left out because it is both a region and a municipality. Chosen: **Ministerstvo financí** (national, IČO 00006947, 257 notices), **Moravskoslezský kraj** (regional, 70890692, 195), **Statutární město Ostrava** (municipal, 00845451, 214; its city districts publish under the same IČO and are included). 661 award notices, 630 awarded lots (44 republished lots counted once); 122 results with several or no winning references excluded (mostly multi-winner frameworks); 11 lots led by another buyer in joint procurement are not attributed. CZK and EUR as published. TED sometimes answers an empty HTTP 202 to fast clients (bot protection); the importer waits 2 seconds between notices and retries.

| Check | Signals | Clear | Unknown | Out of scope |
| --- | ---: | ---: | ---: | ---: |
| `ted-single-offer` | 89 | 254 | 267 | 20 |
| `ted-direct-award` | 20 | 344 | 266 | 0 |
| `ted-repeated-single-offer` | 12 | 74 | 270 | 274 |
| `ted-repeated-direct` | 7 | 13 | 266 | 344 |
| `ted-concentration` | 14 | 393 | 223 | 0 |

122 lots with a signal, 455 zero, 53 not assessed before v3.1; with the late-publication check (15 lots, 2 unknown), 135 / 495 / 0. By buyer: Ministry of Finance 66 of 284, Moravian-Silesian Region 24 of 118, Ostrava 45 of 228.

- **266 lots use the eForms code `oth-single`** (other single-stage procedure, common in Czech notices for simplified below-threshold and framework procedures): their competitive character is not classified, so the single-offer and direct-award checks stay unknown; 53 of them had no other evaluable check before the late-publication check; none is not assessed now.
- **Concentration fires here, unlike Portugal and Romania**: INTERIER TECH s.r.o. won six separate Ministry of Finance office-furniture framework procedures, each with one offer (14 lots). Counted in distinct procedures, so the lots of one notice count once. Before republished lots were counted once (2026-10-15) it fired on 70 lots, also for CSF s.r.o. (regional IT equipment), VYKRUT zahradní služby (Ostrava landscaping) and an Ostrava transport operator: their wins were the same contracts listed again in later notices.
- **Awards without prior publication**: 20 lots. Eight are repairs to Ostrava's wastewater treatment plant after the September 2024 floods, a textbook urgency case; seven are electricity and gas purchases by the region and the ministry (commodity purchases, often made on an exchange); the rest are Ostrava district building and design contracts (a park, a town-hall extension, a science education centre), which deserve a reading of the stated ground. Repetition: Škoda Auto won the ministry's central car purchase in several categories as the only bidder (9 lots); KYOCERA supplies printers (3 lots).

### Correction after the first run

The first computation counted concentration in **lots**, so one notice with 24 lots won by one supplier counted as 24 wins; it produced 69 Romanian concentration signals, all from multi-lot notices. Concentration now counts **distinct procedures**, like the repetition checks (Romania: 0 signals). No threshold was changed.

### Republished lots counted once (2026-10-15)

A reviewer flagged three Romanian false positives; the raw notices explain them.

- **Republished award notices.** Buyers publish later award notices for the same procedure (eForms `ContractFolderID`) that list again lots already awarded, under the same contract reference and conclusion date. Cluj-Napoca's 575056-2026 (18 August 2026) relists the four lots of 13780-2026 (8 January 2026) with **0.01 RON** placeholder amounts; the notice is a `can-standard` award notice, not a declared correction. Each relisting was a new row, published months after the contract, so it fired the late-publication check (Romanian late-publication signals 25 → 12). The importer now keeps a lot once, from its first publication, keyed by procedure, contract reference, lot and conclusion date; later listings are dropped and counted in the coverage file (`relistedLotsExcluded`), with the fields that changed (`relistedLotsWithChangedValues`), never merged into the first. Romania 35 lots, Portugal 5, Czechia 44. The conclusion date is part of the key because Czech call-offs under one framework or dynamic purchasing system share a contract reference while being separate contracts (without it, 189 Czech lots would have been dropped, most with other dates and amounts).
- **Eco Garden, 31438-2026 (Cluj-Napoca green spaces, EST and VEST lots), both 64,456,577.20 RON.** Not changed. The notice gives each lot its own framework maximum of 64,456,577.20 RON and an overall maximum of 128,913,154.40 RON, exactly twice that, so the figure is per lot, not the total repeated. The two lots also publish identical highest tenders (116,815,298.48 RON) and subcontracting values, which suggests copied lot data or an equal split; TED alone cannot tell which. No check uses TED amounts for scoring, so these rows score 0 either way.

## Framework agreements longer than four years: examined, not added (2026-09-26)

The EU directive caps framework agreements at four years except in justified cases, so a longer declared framework duration would be a legal-threshold check rather than an editorial one. The raw notices were read for it: no framework lot declares more than 48 months (Romania 458 lots, all at most 48 months; Portugal 4 lots at most 48 months and 120 with no duration). A check that cannot fire here, and would leave 120 Portuguese lots unknown, was not added; the `long-contract` slot stays out of scope. Most framework results are also excluded from the rows because they name several winners.

## Legal anchoring (v3.3)

Reviewed 4 October 2026; no check changed. TED notices are above the EU thresholds by construction, so no amount eligibility applies to `neg-wo-call`; its legal basis is the directive's grounds (Directive 2014/24/EU art. 32), not an amount. Directive minimum periods (35/30/15 days) need the contract-notice chain, which is not imported: follow-up. Counts unchanged.

## Local correctness correction after v3.3

The corrected leave-one-out publication median changes four Portugal scores and adds one late-publication signal: **138 positive / 355 zero / 0 not assessed**, with 11 late-publication signals. Portugal's top 20, Czechia and Romania are unchanged. Earlier release counts above are historical. See [score-audit.md](score-audit.md) for the before/after comparison and reproduction.

## Reproduction

```sh
python tools/import-ted-cohorts.py --cohort portugal --offline
python tools/import-ted-cohorts.py --cohort romania --offline
node tests/national.cjs
```
