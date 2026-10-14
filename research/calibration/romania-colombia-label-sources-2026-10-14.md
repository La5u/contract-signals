# Romania and Colombia: label sources for indicator points (2026-10-14)

Research only; no score, weight or dataset changed. Goal: repeat the Ukrainian method ([results](ukraine-results-2026-10-14.md)): final convictions or upheld bid-rigging decisions linked to one procedure, against the same buyers' other procedures. Web research by two model subagents (Sol was out of quota); claims marked *verified* were checked by hand on 2026-10-14, everything else is as reported and unverified.

## Verified on 2026-10-14

- **Colombia, SECOP II starts in practice in 2018.** Contracts by signing year in `jbjy-vk9h`: 2015 10, 2016 1,340, 2017 22,224, 2018 142,586, 2019 142,090, 2020 356,623 (Socrata aggregate on `fecha_de_firma`). Convictions found so far concern contracts of 2007–2015 (SECOP I or earlier).
- **Romania, SEAP/SICAP open data:** data.gov.ro "Achizitii publice 2024", licence **CC BY 4.0**, quarterly files per resource (direct purchases, initiation notices, award notices without prior notice, published contracts, contract modifications). The contracts file (Q1 2024, 9.6 MB, UTF-8 CSV) has: buyer, buyer CUI, buyer type, procedure type, legislation, CPV, initiation notice number (`CN…`), award notice number (`CAN…`), lot, contract date and number, value in RON, winner and winner CUI. **No number of offers.** Raw file in `~/.cache/contract-signals/romania-seap/2024/`.
- **Romanian Competition Council decision PDFs** answer automated requests with a JavaScript browser check; not bypassed.

## Romania (subagent report, unverified unless above)

- Court portals: ReJust (CSM; registration, anonymised, full-text search claimed), ROLII (status unclear), portal.just.ro (case search by number or party). No API, bulk export or reuse terms found; no conviction quoting a SEAP/SICAP or TED identifier was found. Judgments tend to describe the procedure by subject, buyer and date.
- DNA press releases: monthly counts of final convictions (about 19 rulings / 27 defendants a month in a 2022 sample), no procedure numbers.
- Competition Council bid-rigging decisions: press releases name the buyer and the number of procedures (e.g. 12 procedures for Complexul Energetic Oltenia and Govora); some are challenged in court. A handful of decisions a year. Closest analogue to the Ukrainian AMCU label, which worked well.
- Verdict: comparison data good (SEAP, CC BY 4.0); labels are the weak point.

## Colombia (subagent report, unverified unless above)

- Corte Suprema casación rulings and press items name contract numbers (e.g. contract 137 of 2007, TransMilenio), but the facts are 2005–2015. Relatoría search returned HTTP 403 to automated access.
- Fiscalía press releases: entity, offence, sentence; no contract numbers in the items read. 3,579 corruption convictions in four years to December 2023 (all offences).
- Monitor Ciudadano 2016–2022 (1,243 cases, CC BY-SA): schema not checked; many cases are investigations.
- No conviction resolved to a SECOP II record. Expected yield of final, SECOP II-linkable convictions now: under 10; 20–50 unlikely before about 2028–2030.
- Finality: second-instance decision and casación status, or a constancia de ejecutoria; PACO's penal indicator counts convictions in sentence execution.

## Options

1. **Romania, bid-rigging decisions (recommended first):** read the Competition Council's bid-rigging decisions 2018–2025 (browser access), list buyers and procedures, check court outcomes, and resolve each procedure in the SEAP exports by buyer CUI, CPV, date and value; comparisons from the same buyers' SEAP contracts. Testable checks: direct award, concentration, buyer share (R1), amendments; not single offer (no offer counts in SEAP).
2. **Colombia via SECOP I:** link the 2011–2015 convictions to SECOP I records instead of SECOP II; needs a separate SECOP I import and only the checks SECOP I supports.
3. **Colombia, wait:** collect leads from Fiscalía and Corte Suprema press now, revisit when 2018+ contracts reach final convictions.

## Colombia, SECOP I and leads (later on 2026-10-14, verified unless noted)

- **Historical SECOP I is open:** datos.gov.co `x6v4-i8gf` (CC BY-SA 4.0), records by upload year 2004–2022 (2011: 264,696; 2013: 654,721; 2015: 1,046,640). Fields include entity NIT, process type (modalidad), contract number, signing year, contract value, object, contractor ID. The newer `f789-7hwg` holds mostly 2018+ signatures. Also `tauh-5jvn` (bidders per process: offer counts) and `7fix-nd37` (additions). Queries by NIT take about a minute; name `LIKE` queries time out.
- **Linkage works in principle:** Alcaldía de Bucaramanga (NIT 890201222) contract **114 of 2014**, licitación pública, COP 795,556,188, "cuadrilla de poda para el despeje de luminarias", matches the tree-pruning/lighting contracts of the Bohórquez (Manantial de Amor) case. Numbers repeat across years and dependencies (`114` exists in 2013 and 2014), so a match needs NIT + number + year + object.
- **Leads:** 61 conviction leads from press, Corte Suprema and Fiscalía summaries (subagent; `~/.cache/contract-signals/colombia-leads/leads.jsonl`, no private names): 34 first instance, 15 plea agreements, 5 casación, 5 confirmed on appeal, 2 unknown; contract years ≤ 2015: 38, 2016–2017: 3, 2018+: 7, not stated: 13; 21 print a contract number, mostly 2007 or earlier. fiscalia.gov.co refused automated access. Explicit finality language in a handful only (all contracts ≤ 2013).
- **Yield estimate:** perhaps 10–20 final, linkable convictions from current leads, below the 30 used in Ukraine. Getting numbers for the rest needs the judgments themselves (Corte Suprema PDFs are fetchable; tribunal files are not in bulk).
