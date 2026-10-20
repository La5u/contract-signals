# Romania: indicator points from bid-rigging decisions — plan (fixed 2026-10-14, before any rate was computed)

Owner request (2026-10-14): repeat the Ukrainian label method for Romania. Sources and access: [romania-colombia-label-sources-2026-10-14.md](romania-colombia-label-sources-2026-10-14.md). Research only; no score, weight or dataset changes without the owner.

## Labels

- **Collusion (Romania):** a procurement procedure that a Competition Council decision finds rigged (infringement of art. 5(1) of Law 21/1996 and/or art. 101 TFEU concerning public procurement). Sources: the decisions on the Council's bid-rigging list (blacklist of 8 June 2026, 22 decisions 2017–2025) and older infringement decisions with the same finding. Procedures only *mentioned* in a decision are not labels.
- **Linking to a contract:** exact SEAP/SICAP notice number (CN, SCN, CAN, DA, ADV or the older numeric announcement number) in the SEAP exports; otherwise buyer CUI + subject + year, accepted only when it leaves one procedure (lot-level when the decision names the lot). Unresolved procedures are listed, not guessed.
- **Finality** (court portal web service, party search on the sanctioned companies and the Council): *confirmed* when a challenge was rejected by a final ruling, or when the companies admitted the facts (recunoaștere) and no challenge is found; *presumed* when no challenge is found and the decision is at least 6 months old; *pending* when a challenge is undecided; *annulled* when a court annulled the finding (excluded). Pending and annulled are reported, not used.

## Comparison

Contracts of the same buyer (CUI) awarded in the same year, from the SEAP contract exports (data.gov.ro, CC BY 4.0 from 2021, UK OGL before), excluding labelled procedures. Comparisons are unlabelled, not proven clean. Each buyer counts once (buyer-weighted rates), as in Ukraine.

## Checks tested (data available in SEAP exports)

| ID | Rule |
| --- | --- |
| RO1 direct award | Procedure type negotiated without prior publication. |
| RO2 buyer share | Contract value ≥ 5 % of the buyer's SEAP contract total (RON) for the award year (the Ukrainian R1 rule). |
| RO3 concentration | Same buyer and CPV division: the winner holds ≥ 60 % of ≥ 10 contracts with an identified winner (the existing rule). |
| RO4 amendments | Three or more published contract modifications, where the modification files can be linked to the contract. |
| RO5 framework / subsequent | Contract awarded as a subsequent contract under a framework agreement (descriptive; tested, no prior expectation). |
| RO0 single offer | A competitive procedure (not negotiated without publication, not a direct purchase) whose contract record publishes 1 offer received. Unknown where the year's export has no offer count. |

Amendment (2026-10-14, still before any rate was computed): the 2017 and 2021 export headers include the number of offers received (`NumarOfertePrimite`, `NUMAR_OFERTE`), so RO0 is added. The 2024 export has no such column; years without it leave RO0 unknown. Bid rigging needs at least two bidders, so, as for the Ukrainian AMCU labels, RO1–RO5 are also reported among procedures with 2+ offers where offers are known (sensitivity, not a decision).

## Method and decision rule

Same as Ukraine: buyer-weighted hit rates (reported first), LR shrunk toward 1 by a prior worth 10 buyers, 95 % intervals from resampling buyers, points = 10 × log2(LR) floored at 0, no proposal below 10 labelled buyers. Holdout: buyers split in halves by hash; a check passes when the learn-half interval is above 1 and the check-half LR is above 1. Points basis: **one procedure per decision** (the largest scheme could otherwise dominate); all procedures reported as a robustness set. Points are Romanian only.

Expected biases, stated in advance: the Council builds cases on bid evidence and on complaints, so its cases over-represent detectable cartels in competitive procedures; RO1 (direct award) is therefore expected to be rare among labels, which says little about direct awards as such.

## Amendment (2026-10-15, before any weighted rate was computed): weighting challenged decisions

Owner request: instead of dropping decisions under appeal, weight them by the chance that they are upheld, using only cases verified to be still open. Source of the chance: the Council's annual reports, share of High Court rulings in the Council's favour in competition cases — 89 % (2023), 94 % (2024), 90 % (2025); mean **p = 0.91**. (Court of Appeal first instance: 79 %, 73 %, 81 %.)

| Decision status (court portal and press, `research/labels/romania-cc-court-outcomes.jsonl`) | Weight |
| --- | --- |
| No challenge found, or upheld by a final ruling (71/2012, 72/2012, 77/2015, 83/2016, 33/2017) | 1 |
| Court of Appeal rejected the challenge and no further appeal is recorded (48/2020) | 1 |
| Still open: hearings scheduled or an appeal filed without a ruling (134/2024, 148/2025, 77/2017, 99/2021, 43/2020, 271/2024, 44/2013) | 0.91 |
| Annulled at first instance, the Council's appeal pending (80/2023) | 0.5 (sensitivity 0 and 0.91) |

A procedure of weight w counts w in the labelled group and 1 − w in the comparisons (as an ordinary contract of its buyer). Buyer-weighted rates use the largest weight of a buyer's labelled rows. Decision rule as before (one procedure per decision, buyer-half holdout, at least 10 labelled buyers, counted by weight).

## Decision rule amendment, 2026-10-20 (owner: the safeguards were too strict; fewer, more lenient, and less certainty means fewer points)

Made after results under the old rule had been seen (Romania, Colombia, Ukraine and the Korean preparation run). It applies to every country alike and is implemented once, in `tools/propose-indicator-points.py` (`decide`).

- **Kept:** at least 10 labelled buyers; buyer-weighted rates (each buyer counts once); LR shrunk toward 1 by a prior worth 10 buyers; 95 % intervals from resampling buyers.
- **Points from the evidence we are 75 % sure of:** points = 10 × log2 of the shrunk LR at the 25th percentile of the buyer resamples (never above the shrunk LR itself), floored at 0. Uncertainty lowers the points instead of excluding the check; any check reliably above LR 1 gets some points, possibly a fraction of one.
- **Dropped:** the requirement that the learn half's 95 % interval lie above 1 and the check half's LR exceed 1 (the halves are still reported), and one tender/procedure per case as the points basis: all linked tenders are the basis, one per case is reported as robustness.
- Hit rate stays the first column reported, as before.
