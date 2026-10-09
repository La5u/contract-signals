# One indicator catalogue for every country

Every check in every dataset maps to one **universal kind**. The table, the *Indicator* filter, copied summaries and exports show the universal label; the row detail also shows the jurisdiction's own check and its reason. This lets the *All countries* view rank and filter every dataset together (owner's decision, 27 September 2026).

What stays local, and why: **eligibility and thresholds follow each jurisdiction's law and data.** A single offer means the same thing everywhere, but “without competition” is a different legal route in each country, and a long duration is 10 years in France and 3 years in the Colombian cohort because ordinary durations differ. Where a dataset cannot support a kind (no offer counts, no amendments), the check is out of scope with a reason, never zero. Weights are the same everywhere for the same kind, and the index is `min(100, max(competition) + max(execution/duration) + max(transparency))` in every country (v3.1). The transparency check is the same code everywhere: `late-publication`, described in [score-v3.md](score-v3.md#transparency-family-v31-27-september-2026).

| Universal kind | Family | France (DECP, BOAMP) | Colombia (SECOP II) | Paraguay (DNCP) | Ukraine (Prozorro) | TED: Portugal, Romania, Czechia | United Kingdom (Find a Tender) | Chile (Mercado Público) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single offer in a competitive procedure | competition | `single-bid` | out of scope (no offers table) | `dncp-single-tenderer` | `ua-single-offer` | `ted-single-offer` | `uk-single-offer` | `cl-single-offer` (per tender) |
| Award without competition | competition | `direct-award` (only from the legal no-publicity threshold; see score-v3.md) | `secop2-plurality-award` (declared no plurality / urgency only; the bare direct modality is not a signal) | `dncp-exception-award` | `ua-direct-award` | `ted-direct-award` | `uk-direct-award` | out of scope (direct deals are purchase orders, not in this source) |
| Repeated single-offer wins by the same supplier | competition | — | — | `dncp-repeated-single-tenderer` | `ua-repeated-single-offer` | `ted-repeated-single-offer` | `uk-repeated-single-offer` | `cl-repeated-single-offer` |
| Repeated awards without competition to the same supplier | competition | `repeated-direct-award` | `secop2-repeated-plurality` | `dncp-repeated-exception` | `ua-repeated-direct` (no negotiated procedure in this cohort) | `ted-repeated-direct` | `uk-repeated-direct` | out of scope |
| Buyer with repeated low competition | competition | `repeated-single-bid` (share of single offers in a buyer/CPV group) | out of scope (no offers table) | — | — | — | — | — |
| Concentrated awards | competition | `supplier-concentration` | `secop2-concentration` | `dncp-concentration` | `ua-concentration` | `ted-concentration` | `uk-concentration` | `cl-concentration` |
| Better-ranked bidder disqualified | competition | — | — | — | `ua-better-bid-disqualified` | — (TED publishes no award sequence) | — | — |
| Short bidding period | competition | `short-bidding-period` (reliable chronology only) | out of scope | out of scope | — | out of scope | out of scope | out of scope |
| Long declared duration | execution | `long-contract` (≥ 120 months) | `secop2-long-duration` (≥ 36 months) | out of scope | out of scope | out of scope | out of scope | out of scope |
| Amount increase after award | execution | `amount-increase` (> 20 %, firm price) | out of scope | `dncp-amount-increase` (from 19 % to the provisional 20 % reference ceiling: 8; beyond it: 16 → 40) | out of scope | out of scope | out of scope | out of scope |
| Three or more contract amendments | execution | — | — | — | `ua-contract-amendments` (≥3 active changes; 8 points) | — | — | — |
| Term extended after award | execution | — | `secop2-term-extension` (> +100 % of the declared term) | — | — | — | — | — |
| Published long after the contract | transparency | `late-publication` (delay > 120 days; DECP excess > 240 days with an established buyer baseline, otherwise whole delay > 120 days; BOAMP excess > 120 days) | out of scope | out of scope | out of scope | `late-publication` (delay > 120 days and excess > 120 days; whole delay > 120 days without a buyer baseline) | out of scope (contract dates not comparable) | out of scope |

“—” means the check does not exist for that dataset; “out of scope” means it is listed on every row with the reason. Details and thresholds: [score-v3.md](score-v3.md) (France), [score-colombia.md](score-colombia.md), [score-paraguay.md](score-paraguay.md), [score-ukraine.md](score-ukraine.md), [score-ted.md](score-ted.md), [score-uk.md](score-uk.md), [score-chile.md](score-chile.md).

## Legal anchor of each check (v3.3, 4 October 2026)

Anchored means the eligibility or threshold follows a legal text, subject to the verification limits below. Weights are editorial, not empirically calibrated; v3.3 reduces the France and Colombia long-duration maximum from 40 to 16 by owner decision. French single-bid associations do not justify a Colombian execution-risk weight. “Editorial” means no legal anchor was found that the data can test.

| Country | Check | Legal anchor and source | Status |
| --- | --- | --- | --- |
| France | direct award | CCP art. R2122-8, dated thresholds ([score-v3.md](score-v3.md)) | anchored (v3.2) |
| France | late publication | EU award notice 30 days (Directive 2014/24/EU art. 50), essential data 2 months; scoring cutoffs are not legal deadlines | editorial: DECP excess > 240 days is exploratory single-bid proxy evidence, not corruption calibration; fallback and BOAMP 120 days |
| France | short bidding period | EU/French minimums per procedure (CCP R2161-2 to R2161-5: 35 days, 30 with e-submission, 15 in urgency) apply only above EU thresholds, which the data does not give; the 15-day cut is the lowest legal minimum | follow-up |
| France | amount increase (> 20 %) | R2194-5 (50 % per modification, unforeseeable circumstances only), R2194-8 (10 % services/supplies, 15 % works, below EU thresholds only). The applicable cap depends on the modification's ground, not in the data | editorial; follow-up |
| France | long duration, single offer, repetition, concentration | none | editorial, no legal anchor |
| Paraguay | amount increase | Ley 7021/22 art. 67, reported 20 % of amount and term; processes from 19 Feb 2024 ([score-paraguay.md](score-paraguay.md)) | provisional legal basis: full text and exceptions unverified, not a universally verified cap; at reference ceiling 8, beyond 16 → 40 |
| Paraguay | exception award (CVE) | grounds, not an amount | no amount anchor |
| Paraguay | short bidding period | decree 2264/24 minimums not verified | out of scope |
| Paraguay | single tenderer, repetition, concentration | none | editorial, no legal anchor |
| Colombia | amount additions | Ley 80/1993 art. 40 parágrafo: additions at most 50 % of initial value in SMMLV ([Función Pública](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=304)). The extract has no addition value | not testable |
| Colombia | term extension, long duration | no statutory cap on term (art. 40 caps value only) | editorial, no legal anchor |
| Colombia | plurality / urgency awards | Ley 1150/2007 art. 2 num. 4 causales (grounds, no amount threshold) | no amount anchor |
| Chile | direct deal, short period, increase | Ley 19.886: trato directo is outside this source; no tender-period or modification data | out of scope |
| Chile, Ukraine, TED, UK | single offer, repetition, concentration | none | editorial, no legal anchor |
| Ukraine | contract amendments | Law on Public Procurement art. 41 permits listed changes; StateWatch/Prozorro ARI 1-1 sets the three-amendment review threshold | risk-indicator threshold, not a legal cap; 8-point placeholder supported cautiously by the small verdict pilot ([score-ukraine.md](score-ukraine.md)) |
| Ukraine | short bidding period | Law 922-VIII art. 21 and martial-law Resolution 1178 minimums: not verified; raw `tenderPeriod` shows most open tenders near 7 days | follow-up (primary text needed) |
| TED countries | direct award | eForms `neg-wo-call`; notices are above EU thresholds by construction, so no amount eligibility applies | no amount anchor |
| UK | direct award | Procurement Act 2023 direct-award grounds; notices are above threshold by construction | no amount anchor |
| TED, UK, Ukraine, Chile | late publication | TED 30 days; others out of scope | anchored where in scope |

## Equivalents in frameworks auditors already use

So that a flag can be cited by the name an auditor knows. “Equivalent” means the same test; “related” means an overlapping but different test, never a claim that the two agree. Checked on 27 September 2026 against the sources linked.

| Universal kind | Framework flag | Relation |
| --- | --- | --- |
| Single offer in a competitive procedure | OCP Cardinal **R018** Single bid received | equivalent |
| Single offer in a competitive procedure | Fazekas Corruption Risk Index: single bidding | equivalent |
| Short bidding period | OCP Cardinal **R003** Short submission period | equivalent (our threshold is local, see score-v3.md) |
| Award without competition | Fazekas Corruption Risk Index: non-open procedure / no call for tender published | related (our eligibility follows each country's law) |
| Three or more contract amendments | StateWatch/Prozorro **ARI 1-1** | same count threshold (active published contract changes); not a finding of unlawful amendment |
| Better-ranked bidder disqualified | OCP Cardinal **R036** Lowest bid disqualified | related: R036 requires price-only award criteria; ours reads Prozorro's award sequence |
| Better-ranked bidder disqualified | OCP Cardinal **R035** All except winning bid disqualified; Ukraine State Audit Service **sas-3-2** (same), **sas-3-5** (at least two bidders rejected) | related: ours fires from one better-ranked bidder set aside |
| Repeated awards without competition / Concentrated awards | Ukraine State Audit Service **sas-3-3** (one supplier across four or more purchase codes of a buyer) | related |
| Concentrated awards | OCP Cardinal **R048** Heterogeneous supplier | related |

Sources: [OCP Cardinal indicator list](https://github.com/open-contracting/cardinal-rs/blob/main/docs/cli/indicators/index.md); [Prozorro risk rules of the State Audit Service](https://github.com/ProzorroUKR/prozorro-risks/tree/master/src/prozorro/risks/rules); Fazekas, M. and Kocsis, G. (2020), *Uncovering high-level corruption: cross-national objective corruption risk indicators using public procurement data*, British Journal of Political Science 50(1). Cardinal flags we do not compute yet, because they need every bid's price: R024 price close to winning bid, R028 identical bid prices, R058 heavily discounted bid. Prozorro, TED (partly) and Mercado Público publish bids; these are candidates.

## The All countries view

*All countries* loads every dataset, prepares each one on its own (repetition and concentration never cross cohorts) and lists the rows side by side with their country. It exists to find the strongest leads quickly across countries; the sort *Signals · newest first* puts the most recent flagged rows on top. Limits that do not go away:

- **Amounts are never converted or summed.** The amount sort groups rows by currency, then orders them within it.
- **Dates keep each source's meaning**: signature (France, Colombia, Ukraine, UK), award (Chile), contract-period start (Paraguay), contract conclusion (TED).
- **Coverage differs by dataset**: TED and Find a Tender hold above-threshold notices only; some cohorts cannot evaluate some kinds (see the table). A country with fewer evaluable kinds will score lower for reasons of data, not of conduct.
- A signal is a reason to read the source, not a finding of wrongdoing.
