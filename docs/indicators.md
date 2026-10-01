# One indicator catalogue for every country

Every check in every dataset maps to one **universal kind**. The table, the *Indicator* filter, copied summaries and exports show the universal label; the row detail also shows the jurisdiction's own check and its reason. This lets the *All countries* view rank and filter every dataset together (owner's decision, 27 September 2026).

What stays local, and why: **eligibility and thresholds follow each jurisdiction's law and data.** A single offer means the same thing everywhere, but “without competition” is a different legal route in each country, and a long duration is 10 years in France and 3 years in the Colombian cohort because ordinary durations differ. Where a dataset cannot support a kind (no offer counts, no amendments), the check is out of scope with a reason, never zero. Weights are the same everywhere for the same kind, and the index is `min(100, max(competition) + max(execution/duration) + max(transparency))` in every country (v3.1). The transparency check is the same code everywhere: `late-publication`, described in [score-v3.md](score-v3.md#transparency-family-v31-27-september-2026).

| Universal kind | Family | France (DECP, BOAMP) | Colombia (SECOP II) | Paraguay (DNCP) | Ukraine (Prozorro) | TED: Portugal, Romania, Czechia | United Kingdom (Find a Tender) | Chile (Mercado Público) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single offer in a competitive procedure | competition | `single-bid` | out of scope (no offers table) | `dncp-single-tenderer` | `ua-single-offer` | `ted-single-offer` | `uk-single-offer` | `cl-single-offer` (per tender) |
| Award without competition | competition | `direct-award` | `secop2-plurality-award` (declared no plurality / urgency only; the bare direct modality is not a signal) | `dncp-exception-award` | `ua-direct-award` | `ted-direct-award` | `uk-direct-award` | out of scope (direct deals are purchase orders, not in this source) |
| Repeated single-offer wins by the same supplier | competition | — | — | `dncp-repeated-single-tenderer` | `ua-repeated-single-offer` | `ted-repeated-single-offer` | `uk-repeated-single-offer` | `cl-repeated-single-offer` |
| Repeated awards without competition to the same supplier | competition | `repeated-direct-award` | `secop2-repeated-plurality` | `dncp-repeated-exception` | `ua-repeated-direct` (no negotiated procedure in this cohort) | `ted-repeated-direct` | `uk-repeated-direct` | out of scope |
| Buyer with repeated low competition | competition | `repeated-single-bid` (share of single offers in a buyer/CPV group) | out of scope (no offers table) | — | — | — | — | — |
| Concentrated awards | competition | `supplier-concentration` | `secop2-concentration` | `dncp-concentration` | `ua-concentration` | `ted-concentration` | `uk-concentration` | `cl-concentration` |
| Better-ranked bidder disqualified | competition | — | — | — | `ua-better-bid-disqualified` | — (TED publishes no award sequence) | — | — |
| Short bidding period | competition | `short-bidding-period` (reliable chronology only) | out of scope | out of scope | — | out of scope | out of scope | out of scope |
| Long declared duration | execution | `long-contract` (≥ 120 months) | `secop2-long-duration` (≥ 36 months) | out of scope | out of scope | out of scope | out of scope | out of scope |
| Amount increase after award | execution | `amount-increase` (> 20 %, firm price) | out of scope | `dncp-amount-increase` (> 20 %) | out of scope | out of scope | out of scope | out of scope |
| Term extended after award | execution | — | `secop2-term-extension` (> +100 % of the declared term) | — | — | — | — | — |
| Published long after the contract | transparency | `late-publication` (> 120 days) | out of scope | out of scope | out of scope | `late-publication` (> 120 days) | out of scope (contract dates not comparable) | out of scope |

“—” means the check does not exist for that dataset; “out of scope” means it is listed on every row with the reason. Details and thresholds: [score-v3.md](score-v3.md) (France), [score-colombia.md](score-colombia.md), [score-paraguay.md](score-paraguay.md), [score-ukraine.md](score-ukraine.md), [score-ted.md](score-ted.md), [score-uk.md](score-uk.md), [score-chile.md](score-chile.md).

## Equivalents in frameworks auditors already use

So that a flag can be cited by the name an auditor knows. “Equivalent” means the same test; “related” means an overlapping but different test, never a claim that the two agree. Checked on 27 September 2026 against the sources linked.

| Universal kind | Framework flag | Relation |
| --- | --- | --- |
| Single offer in a competitive procedure | OCP Cardinal **R018** Single bid received | equivalent |
| Single offer in a competitive procedure | Fazekas Corruption Risk Index: single bidding | equivalent |
| Short bidding period | OCP Cardinal **R003** Short submission period | equivalent (our threshold is local, see score-v3.md) |
| Award without competition | Fazekas Corruption Risk Index: non-open procedure / no call for tender published | related (our eligibility follows each country's law) |
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
