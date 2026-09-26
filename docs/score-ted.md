# Portugal and Romania method — TED eForms checks (v3.0 framework)

**Checks for the TED cohorts of Portugal and Romania.** Same vigilance-index framework as [score-v3.md](score-v3.md): two families, family maxima, cap at 100, `null` = “Not assessed”, unknowns never counted as zero. The checks read only fields that EU eForms defines the same way in every member state (procedure code, the per-lot `tenders` statistic, buyer and winner identifiers, CPV). The two countries are **separate cohorts**: their counts are never pooled, ranked or compared, and amounts are never converted (EUR for Portugal, RON or EUR for Romania, as published).

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
| Repeated single-offer awards | `ted-repeated-single-offer` | Competition | This award is single-offer; same buyer and supplier (national number) in ≥3 distinct notices | **12 at 3 → 40 at 10** |
| Repeated awards without competition | `ted-repeated-direct` | Competition | This award is `neg-wo-call`; same buyer and supplier in ≥3 distinct notices | **18 at 3 → 60 at 10** |
| Concentrated awards | `ted-concentration` | Competition | Same buyer and CPV division (2 digits); ≥10 lots, ≥80 % with a national supplier number, share ≥60 % | **12 at 60 % → 40 at 100 %** |
| Amount increase | `amount-increase` | Execution | **Out of scope**: modification notices are separate and were not imported | — |
| Short bidding period | `short-bidding-period` | Competition | **Out of scope**: the contract-notice chain was not imported | — |
| Long declared duration | `long-contract` | Execution | **Out of scope**: no duration threshold validated for these jurisdictions | — |

`oth-single` / `oth-mult` and unknown codes are not classified: the competition checks stay unknown. Supplier identity uses the national number (Portuguese NIF, Romanian CUI) only when the winner's address is in that country; foreign or free-text identifiers are kept but not used for repetition or concentration. Joint winners (several members) have no single identity.

## Results

### Portugal (reproduced by `tests/national.cjs`)

Infraestruturas de Portugal (national, NIF 503933813), Comunidade Intermunicipal do Cávado (regional, 508779472), Município de Lisboa (municipal, 500051070). 442 award notices, 493 awarded lots retained; 137 winning results excluded because they name several winners (framework agreements: no single holder). **The 36 Cávado notices link no winning tender to their results, so the regional level yields one row**; the cohort was kept as announced rather than replaced after seeing data. One Infraestruturas de Portugal notice filed under another tax number (505065630) is outside the identifier match and not included.

| Check | Signals | Clear | Unknown | Out of scope |
| --- | ---: | ---: | ---: | ---: |
| `ted-single-offer` | 64 | 322 | 43 | 64 |
| `ted-direct-award` | 64 | 416 | 13 | 0 |
| `ted-repeated-single-offer` | 20 | 43 | 44 | 386 |
| `ted-repeated-direct` | 36 | 25 | 16 | 416 |
| `ted-concentration` | 0 | 237 | 256 | 0 |

128 lots with a signal, 359 zero, 6 not assessed. The top of the ranking is Infraestruturas de Portugal's repeated negotiated awards without publication, for example railway signalling services from Siemens Mobility and vehicle leasing from LeasePlan: signalling maintenance on proprietary systems is a likely lawful exclusivity case, comparable to the proprietary-software maintenance at the top of the French ranking. Read the notice before drawing conclusions.

### Romania (reproduced by `tests/national.cjs`)

Ministerul Finanțelor (national, CUI 4221306), Județul Cluj (regional, 4288110), Municipiul Cluj-Napoca (municipal, 4305857). 299 award notices, 356 awarded lots; 289 multi-winner framework results excluded. Amounts in RON or EUR as published.

| Check | Signals | Clear | Unknown | Out of scope |
| --- | ---: | ---: | ---: | ---: |
| `ted-single-offer` | 132 | 209 | 11 | 4 |
| `ted-direct-award` | 4 | 352 | 0 | 0 |
| `ted-repeated-single-offer` | 42 | 77 | 24 | 213 |
| `ted-repeated-direct` | 0 | 0 | 4 | 352 |
| `ted-concentration` | 0 | 70 | 286 | 0 |

136 lots with a signal, 220 zero, 0 not assessed. 132 of 341 lots with a published offer count had a single offer. Example lead: one supplier won outdoor fitness equipment in several separate Cluj-Napoca notices, each with one offer.

### Correction after the first run

The first computation counted concentration in **lots**, so one notice with 24 lots won by one supplier counted as 24 wins; it produced 69 Romanian concentration signals, all from multi-lot notices. Concentration now counts **distinct procedures**, like the repetition checks (Romania: 0 signals). No threshold was changed.

## Framework agreements longer than four years: examined, not added (2026-09-26)

The EU directive caps framework agreements at four years except in justified cases, so a longer declared framework duration would be a legal-threshold check rather than an editorial one. The raw notices were read for it: no framework lot declares more than 48 months (Romania 458 lots, all at most 48 months; Portugal 4 lots at most 48 months and 120 with no duration). A check that cannot fire here, and would leave 120 Portuguese lots unknown, was not added; the `long-contract` slot stays out of scope. Most framework results are also excluded from the rows because they name several winners.

## Reproduction

```sh
python tools/import-ted-cohorts.py --cohort portugal --offline
python tools/import-ted-cohorts.py --cohort romania --offline
node tests/national.cjs
```
