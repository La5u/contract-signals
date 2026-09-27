# One indicator catalogue for every country

Every check in every dataset maps to one **universal kind**. The table, the *Indicator* filter, copied summaries and exports show the universal label; the row detail also shows the jurisdiction's own check and its reason. This lets the *All countries* view rank and filter every dataset together (owner's decision, 27 September 2026).

What stays local, and why: **eligibility and thresholds follow each jurisdiction's law and data.** A single offer means the same thing everywhere, but “without competition” is a different legal route in each country, and a long duration is 10 years in France and 3 years in the Colombian cohort because ordinary durations differ. Where a dataset cannot support a kind (no offer counts, no amendments), the check is out of scope with a reason, never zero. Weights are the same everywhere for the same kind, and the index is `min(100, max(competition) + max(execution/duration))` in every country.

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

“—” means the check does not exist for that dataset; “out of scope” means it is listed on every row with the reason. Details and thresholds: [score-v3.md](score-v3.md) (France), [score-colombia.md](score-colombia.md), [score-paraguay.md](score-paraguay.md), [score-ukraine.md](score-ukraine.md), [score-ted.md](score-ted.md), [score-uk.md](score-uk.md), [score-chile.md](score-chile.md).

## The All countries view

*All countries* loads every dataset, prepares each one on its own (repetition and concentration never cross cohorts) and lists the rows side by side with their country. It exists to find the strongest leads quickly across countries; the sort *Signals · newest first* puts the most recent flagged rows on top. Limits that do not go away:

- **Amounts are never converted or summed.** The amount sort groups rows by currency, then orders them within it.
- **Dates keep each source's meaning**: signature (France, Colombia, Ukraine, UK), award (Chile), contract-period start (Paraguay), contract conclusion (TED).
- **Coverage differs by dataset**: TED and Find a Tender hold above-threshold notices only; some cohorts cannot evaluate some kinds (see the table). A country with fewer evaluable kinds will score lower for reasons of data, not of conduct.
- A signal is a reason to read the source, not a finding of wrongdoing.
