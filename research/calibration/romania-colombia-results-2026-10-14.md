# Romania and Colombia: indicator checks against labelled cases — results (2026-10-14)

Plans fixed before computing: [Romania](romania-bid-rigging-plan.md), [Colombia](colombia-convictions-plan.md). Sources: [romania-colombia-label-sources-2026-10-14.md](romania-colombia-label-sources-2026-10-14.md). Research only; **no score or weight changed.** Rates count each buyer once; LR shrunk toward 1 by a prior worth 10 buyers; 95 % intervals from resampling buyers; points = 10 × log2(LR); no proposal below 10 labelled buyers.

## Romania: procedures found rigged by the Competition Council

- **Labels:** 30 decisions read (13 blacklist decisions OCR'd plus older text decisions; 9 blacklist decisions not found on the Council site or not yet published), 347 procedures, **136 rigged** in 23 decisions (two schemes dominate: 33 procedures in 77/2017, 32 in 7/2015). Extraction by GPT-6.1-Sol from local texts (recovered from its session log after a write failure; counts match its summary exactly), not hand-checked.
- **Linking to SEAP contracts** (exports 2007–2024, `tools/normalize-romania-seap.py`, `tools/romania-bid-rigging-checks.py`): **38 of 136 resolved** (15 by notice number, 16 by buyer name + winner + subject, 5 by buyer CUI + winner, 2 more on an exact date); 54 ambiguous (the cartel firms won several procedures from the same buyer), 44 not found. Old procedures (2005–2007) predate SEAP; 2022 Q2–Q4 and 2023 XLS exports stop at 64,999 rows at the source, so some recent contracts and comparisons are missing.
- **Challenges** (court portal, `tools/check-romania-cc-court.py`): 7 of the 23 decisions are challenged at the Bucharest Court of Appeal (134/2024, 148/2025, 271/2024, 48/2020, 77/2017, 80/2023, 99/2021); High Court outcomes are not visible in the portal.

| Set | Labelled (buyers) | RO2 buyer share ≥ 5 %: rigged vs comparisons | LR+ [95 %] | Learn / check | Decision |
| --- | --- | --- | --- | --- | --- |
| Unchallenged, one per decision (**decision rule**) | 10 (8) | 29 % vs 20 % | 1.14 [0.65, 1.88] | 1.05 / 1.16 | too few buyers |
| All Council findings, all procedures | 25 (20) | 49 % vs 20 % | **1.80 [1.16, 3.59]** | 1.61 / 1.51 | passes the holdout rule |
| All findings, 2+ offers | 15 (13) | 49 % vs 11 % | 2.53 [1.22, 6.53] | 1.98 / 1.72 | fails (learn interval) |

Other checks (all findings, all procedures): single offer 32 % vs 38 % (LR 0.89); direct award 1 % vs 12 % (0.39, expected: cartels need a competitive call); concentration 2 % vs 2 %; framework/subsequent 35 % vs 24 % (1.25 [0.75, 2.02]).

**Reading:** the decision-rule set is too small (8 buyers) for a proposal. On all Council findings, contracts that are a large share of the buyer's year are about twice as frequent among rigged procedures — the same direction as Ukraine (R1, LR 8.0) and Colombia (below). Single offer does not separate rigged procedures, as in Ukraine's AMCU cases (bid rigging needs several bidders).

## Colombia: contracts named in criminal convictions

- **Labels:** 71 conviction records (15 final, 56 first instance; GPT-6.1-Sol from Corte Suprema rulings and press, partly source-checked), 135 contracts 2010+ with a number and entity NIT. SECOP I (`x6v4-i8gf`) for the 45 entity-years (`tools/fetch-colombia-secop1.py`).
- **Linking** (`tools/colombia-conviction-checks.py`): 30 contracts resolved, 7 ambiguous, 98 not found (many entities' 2016+ contracts are not in this table; one strong final case, UAERMV 638/2013, has NIT "No Definido" in SECOP I). **30 contracts from 7 cases at 7 buyers** (29 first instance, 1 final): below the 10-buyer minimum, so direction only.

| Check (one contract per case) | Convicted | Comparisons | LR+ [95 %] |
| --- | ---: | ---: | --- |
| CO4 buyer share ≥ 5 % | 43 % (3/7) | 11 % | 1.93 [0.77, 5.58] |
| CO1 direct award | 14 % (1/7) | 58 % | 0.69 [0.52, 0.95] |
| CO2 amount increase > 20 % | 14 % | 4 % | 1.48 [0.53, 3.92] |
| CO3 term extension | 14 % | 11 % | 1.04 [0.53, 2.36] |
| CO5 concentration | 0 % | 0 % | — (never fires at entity-year level) |

## Summary

Buyer share (a contract of ≥ 5 % of its buyer's yearly procurement) points the same way in all three countries: Ukraine LR 8.0 (adopted in 3.6), Romania 1.8 on all Council findings (passes the holdout, but the strict unchallenged set is too small), Colombia 1.9 on 7 cases (direction only). Direct award is *less* frequent among labelled contracts everywhere. **Nothing adopted for Romania or Colombia**; owner decision. Next data that would help: the 9 missing Romanian blacklist decisions, disambiguating the 54 ambiguous Romanian procedures (lot and value from the decision texts), High Court outcomes for the 7 challenged decisions, and SECOP II for Colombian 2016+ contracts.
