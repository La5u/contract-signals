# Ukrainian related-party candidates: results (2026-10-17)

Plan fixed before any computation: [part 5 of the candidate plan](ukraine-candidate-indicators-plan.md#part-5-related-parties-from-the-company-register-fixed-2026-10-17-before-any-was-computed). Tool: `tools/ukraine-related-parties.py` (`ids`, `extract`, `run`); tables in `ukraine-*-related-parties.{txt,json}`. Research only: no score, weight or dataset changed.

Register: ЄДР legal entities, open data (data.gov.ua dataset a1799820-195b-4982-8141-6e84f58103e7, `UO.zip` of 2026-10-13, CC BY). 10,293 companies bid or won in the two cohorts; 10,227 (99.4 %) are in the snapshot, 9,898 with at least one named founder, beneficial owner or signer. The extract stays in the private cache.

## Results (hit rate among labelled tenders first)

| Candidate | Convictions + linked | Convictions, one per case | Collusion (AMCU upheld) | Collusion, one per case |
|---|---|---|---|---|
| R1 shared owner or manager between bidders | 3 % (3/213) vs 1 %; LR 2.83 [0.08, 12.56]; fails | 4 % (3/86) vs 1 %; fails | **12 % (187/1,959) vs 2 %; LR 6.78 [4.93, 9.96]; passes** (learn half 5.92 [3.75, 10.33], check half 7.27) | **11 % (59/643) vs 2 %; LR 5.78 [3.86, 8.87]; passes** |
| R2 buyer's contact person owns or runs the winner | 0 % (0/124) | 0 % (0/48) | 0 % (0/1,360) | 0 % (0/441) |
| R3 winner registered < 1 year before the tender | 6 % (10/207) vs 7 %; LR 0.80; fails | 8 % vs 7 %; fails | 6 % vs 6 %; fails | 9 % vs 6 %; LR 1.38 [0.99, 1.84]; fails |

Comparisons are the same buyers' other competitive tenders. Points that would follow from the collusion sets (10 × log2 LR): about 25–28.

## Reading

- **R1 is a collusion signal, not a corruption signal.** Among bid-rigging cases upheld in court, one in nine rigged tenders had two bidders sharing an owner or manager, against one in fifty ordinary tenders, consistently in both buyer halves. Among convictions (bribery, embezzlement, fraud) it is as rare as K1 shared contact: 3 of 213 tenders. As stated in the plan, the AMCU hit rate is an upper bound, since the Committee finds cartels through such links; the conviction cohort does not support it.
- **R2 never fires.** 703 of 1,204 buyer contact names in the conviction cohort are full three-part names; exactly one of them appears among the people of any of the 10,227 companies. Officials do not appear in the register as owners or managers of the suppliers under their own name; family members and nominees cannot be seen with a name match.
- **R3 does not separate** labelled from ordinary tenders.
- **Snapshot bias.** Coverage of R1 is 86 % among convicted tenders and 76 % among comparisons (9.7 points, under the plan's 10-point limit); one per case 73 % vs 76 %; collusion 72 % vs 76 %. Today's owners are not those at the time of the tender, so links are undercounted on both sides.

## Proposal for the owner

R1 passes the decision rule on the collusion evidence only, like K1 shared contact. Options: (a) leave both out of the index (the conviction labels do not support them); (b) show R1 as context in the record panel, never scored ("two bidders share an owner or manager in today's company register"), as for joint offers; (c) score R1 in a separate collusion family with points from the collusion sets (about 25), stating that those are an upper bound. Showing it needs every bid of the explorer's Ukrainian rows (the shipped tender records carry them where the procedure had bids; most of the explorer's Ukrainian rows are direct-contract reports without bids) and the register lookups for those bidders; no names would be published, only the yes/no and the register as source.
