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

Single offer cannot be tested: SEAP exports carry no offer counts (TED has them for above-threshold notices only; reported separately if at least 10 labelled procedures match a TED notice).

## Method and decision rule

Same as Ukraine: buyer-weighted hit rates (reported first), LR shrunk toward 1 by a prior worth 10 buyers, 95 % intervals from resampling buyers, points = 10 × log2(LR) floored at 0, no proposal below 10 labelled buyers. Holdout: buyers split in halves by hash; a check passes when the learn-half interval is above 1 and the check-half LR is above 1. Points basis: **one procedure per decision** (the largest scheme could otherwise dominate); all procedures reported as a robustness set. Points are Romanian only.

Expected biases, stated in advance: the Council builds cases on bid evidence and on complaints, so its cases over-represent detectable cartels in competitive procedures; RO1 (direct award) is therefore expected to be rare among labels, which says little about direct awards as such.
