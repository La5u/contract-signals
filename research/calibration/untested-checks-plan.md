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
