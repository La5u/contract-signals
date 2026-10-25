# Untested and new checks across Ukraine, Romania and Colombia — plan (fixed 2026-10-15, before any was computed)

Owner request (2026-10-15): test the checks that carry points but were never measured against labelled cases, and new candidates. Labels, comparisons and method as in the country plans: [Ukraine](ukraine-candidate-indicators-plan.md), [Romania](romania-bid-rigging-plan.md), [Colombia](colombia-convictions-plan.md) (buyer-weighted hit rates first, LR shrunk toward 1 by 10 buyers, buyer-resampled intervals, points = 10 × log2(LR), no proposal below 10 labelled buyers, buyer-half holdout). Research only.

## Existing checks, never measured

| ID | Rule (as scored in the explorer) | Where testable |
| --- | --- | --- |
| U1 repeated single offer | This award is a single offer in a competitive procedure, and the same buyer and supplier have ≥ 3 distinct single-offer procedures in the buyer's data for the award year and the years before and after. | Romania (offer counts in SEAP 2007–2022) |
| U2 repeated award without competition | This award is without competition (Romania: negotiation without prior publication; Colombia: Contratación Directa), and the same buyer and supplier have ≥ 3 distinct such awards in the same window (Colombia: the signing year, the only year downloaded per entity). | Romania, Colombia |

Concentration was measured (Romania RO3, Colombia CO5); direct award was measured in all three.

## New candidates

| ID | Rule | Where testable |
| --- | --- | --- |
| N1 December signature | The contract is signed in December (year-end spending). Already tested for Ukraine as C7. | Romania, Colombia |
| N2 weekend signature | The contract is signed on a Saturday or Sunday. | Ukraine, Romania, Colombia |
| N3 long duration | Declared duration ≥ 36 months (Ukraine `durationMonths`; Colombia `plazo_de_ejec_del_contrato` with its unit). | Ukraine, Colombia |
| N4 supplier dependence | The winner receives ≥ 25 % of the buyer's contract value for that year (value-based, all procedures). | Romania, Colombia |
| N5 first-time supplier | The winner has no contract with this buyer in the three preceding years of data (requires those years to be loaded). | Romania (SEAP from 2007; procedures from 2010 on) |

Expected, stated in advance: U1/U2 and N4 overlap with concentration and with buyer share (R1/RO2/CO4); N2 is rare and mostly reflects data-entry dates; N5 may favour cartels that rotate winners. Results are reported per country; points stay per jurisdiction and nothing changes without the owner.

## Round-number and digit checks (owner idea, added 2026-10-24; first tested in Korea)

Kept here to be tested in other countries and datasets: the owner has seen them work elsewhere, and Korea's prices
mostly come from formal cost calculations (원가계산, design estimates), which may hide the effect there. "A" = amounts.
Rules as implemented in `tools/korea-label-checks.py` (`round_checks`); a new country should first measure where its own
amounts heap (on all records, before looking at labels), as Korea did, and keep the same structure.

| ID | Rule | Data needed |
| --- | --- | --- |
| A1 round-percentage increase | A price increase between consecutive contract versions that is an exact whole percentage of the previous amount (e.g. +5 %, +15 %) and whose ratio new/old is not a fraction with denominator ≤ 9 (those heaps, +50 %, +33.3 %, +11.1 %, are quantity or period changes). Report also all whole-percent increases, and without +10 % where 10 % is a VAT rate. | Amount per amendment (Korea opnstd versions; Ukraine Prozorro contract changes; France DECP modifications; Paraguay DNCP amendments) |
| A2 same step repeated | Two or more increases of the same percentage (to 0.01, at least 1 %) in one contract. | as A1 |
| A3 / A4 round contract amount | The original contract amount has one (A3) or exactly two (A4) significant digits. | Contract amount |
| A5 / A6 round budget | The buyer's budget or estimated value has one (A5) or exactly two (A6) significant digits; tiny placeholder values (Korea: < 1M KRW, e.g. 10) are unknown. Variants worth reporting: multiple of 10M / 100M in local currency, "nice" values (1, 2, 2.5, 3, 5 × 10^k). | Budget / estimated value per notice (Korea asignBdgtAmt; Ukraine `value.amount`; Romania SEAP estimated value; Colombia SECOP II `valor estimado`) |
| A7 Benford deviation per supplier | Mean absolute deviation of the first two digits of a supplier's contract amounts from Benford's law (Nigrini MAD), as a percentile among suppliers with a similar number of contracts (≥ 50). A firm-level check: one amount cannot deviate. Better suited to invented numbers (invoice lines, unit prices, losing bids) than to awarded amounts. | ≥ 50 amounts per supplier |

Korea results (2026-10-24, `korea-collusion-results.md` "Round-number checks"; exploratory scripts `tools/korea-round-budget-test.py` and
`tools/korea-benford-test.py`): no
check earned points. A1/A2 are too rare among KONEPS-linked labels to rate (1–3 tenders). Rigged and convicted
contracts have fewer round amounts than others (≤ 2 significant digits: 6.7 % of 238 amounts printed in court
convictions vs 14.3 % of all contracts). Round budgets compared within the same buyer, year and business type:
cartel 60 cases, 1 digit ×1.07 once two artifact cases are removed (a 28-school robot purchase at exactly 40,000,000
and hospital drug tenders with a 10 KRW placeholder budget); court 10 cases ×0.2–0.5; audit pilot 10 cases ×0–0.8
(×100M ×3.8 on 2 hits). Benford: Korean amounts have too many leading 1s (34.9 % vs 30.1 %) and 9s (5.4 % vs 4.6 %)
from legal limits; labelled firms deviate less than other firms of their size (percentile 0.27 court-linked, 0.32
cartel winners, 0.41 fraud-type debarments, vs 0.50), because competitive bids give natural spreads while small direct
purchases cluster at limits. Next tests: Ukraine (court verdicts linked to Prozorro, expected values set by hand),
then Romania and Colombia; Benford on losing bids per firm.
