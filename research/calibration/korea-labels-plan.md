# South Korea: indicator points from corruption and bid-rigging findings — plan (drafted 2026-10-16, before any rate was computed)

Owner request (2026-10-16): repeat the Romanian/Ukrainian label method for Korea, tune Korean checks and test the global ones. Sources: [korea-label-sources-2026-10-16.md](korea-label-sources-2026-10-16.md). Research only; no score, weight or dataset change without the owner.

Owner, 2026-10-16: "any corruption should be detected". The checks are judged on **every officially established form of procurement corruption**, not on bid rigging alone: the decision set is the union of the label families below; each family is also reported alone, as in Ukraine (corruption and fraud reported separately and combined).

## Labels

| Family | Source | Finding |
| --- | --- | --- |
| **Collusion** | Fair Trade Commission decisions (law.go.kr `target=ftc`) | tender rigged by bidders (below) |
| **Corruption** | Court rulings (law.go.kr `target=prec`, full-text queries on bribery, tender obstruction, breach of trust, leaking reserve prices) | conviction of an official or a supplier for bribery (뇌물), obstruction of a tender (입찰방해, 공무집행방해), breach of trust (배임) or leaking secrets (공무상비밀누설) tied to a named public contract or tender |
| **Irregularity** | Local-government, education-office, MOIS and BAI audit annexes | contract found unlawfully split, steered or awarded; reported alone and in a second union, never in the decision set (an audit is not a court or tribunal finding, and splitting findings are circular for K3/K4) |

Corruption labels: final when the Supreme Court ruled or no appeal is found and the ruling is at least 6 months old; a conviction later quashed is excluded; a lower-court conviction with an appeal pending gets weight 0.91 (the Korean figure below is the KFTC's; no court-wide conviction-survival rate is used). Court rulings mask private parties' names but keep public bodies'; linking uses buyer + contract or tender name + date + amount, accepted only when it leaves one contract.

### Collusion

- **Collusion (Korea):** a public tender that a Fair Trade Commission decision (의결서) finds rigged: an unfair concerted act in a tender (부당한 공동행위, 입찰담합; 공정거래법 제40조제1항제9호, formerly 제19조제1항제8호). Tenders only *mentioned* in a decision are not labels. Private-sector buyers are excluded; so are tenders not run on KONEPS (나라장터).
- **Linking:** exact KONEPS notice number (`bidNtceNo`, `20YYMMNNNNN`, any order suffix) to the open-standard contracts' `notice_no`; otherwise buyer + tender name + year + winner (company name, then registration number), accepted only when it leaves one notice. Lot-level when the decision names the lot. Unresolved tenders are listed, not guessed.
- **Finality:** *confirmed* when a court challenge was rejected by a final ruling or none was filed; *presumed* when no challenge is found and the decision is at least 6 months old; *pending* when a challenge is undecided; *annulled* when a court annulled the finding (excluded). Sources: the decision's 후속심결 field and law.go.kr precedents naming the decision (시정명령등취소). Pending decisions are weighted as below (owner request 2026-10-16, fixed before any rate was computed).

### Weighting challenged decisions

Source: KFTC Statistical Yearbook 2024, Table 6-4 "행정처분 확정연도 기준 소송결과" (p. 39; respondents' administrative suits against KFTC dispositions, by year the suit became final, as of 2025-03-31), read directly from the PDF ([mirror](https://repokr.github.io/doc/Yearbook2024%282025%29.pdf#page=50); official collection on fairdata.go.kr):

| Year | Won | Partly won | Lost | Finding survives (won + partly won) |
| --- | ---: | ---: | ---: | ---: |
| 2020 | 43 | 13 | 6 | 90.3 % |
| 2021 | 72 | 8 | 8 | 90.9 % |
| 2022 | 56 | 16 | 7 | 91.1 % |
| 2023 | 54 | 15 | 8 | 89.6 % |
| 2024 | 69 | 8 | 6 | 92.8 % |
| 2020–2024 | 294 | 60 | 35 | **91.0 %** |

A partial win mostly means the violation stands and the fine or order is reduced (KFTC's explanation), so it counts as the finding surviving; a partial win that overturns the rigging finding itself is checked case by case where the ruling is found. **p = 0.91** (pooled 2020–2024, all case types). Sensitivity: cartel cases only, 2024 as reported in the press (42 cases, 40 won, 1 partly won: 0.976; not read in an official table), and 0 / 1.

| Decision status | Weight |
| --- | --- |
| No challenge found and at least 6 months old, or upheld by a final ruling | 1 |
| Challenge pending (no final ruling) | 0.91 |
| Annulled at first instance, appeal pending | 0.5 (sensitivity 0 and 0.91) |
| Annulled by a final ruling | excluded |

A tender of weight w counts w in the labelled group and 1 − w in the comparisons, and buyer-weighted rates use the largest weight of a buyer's labelled rows, as in Romania.

## Comparison

Contracts of the same buyer (`buyer_code`) signed in the same year, from the PPS open-standard contracts (data.go.kr 15058815), excluding labelled ones. Unlabelled, not proven clean. Buyer-weighted rates. Corruption can sit in any contract, so the decision set compares against **all contracts**. Bid rigging needs a competitive tender, so the collusion family is also reported among competitive contracts with a notice (일반·제한·지명경쟁 with `notice_no`), as the Ukrainian 2+ bid restriction.

## Checks tested

Global checks, as defined for the other countries ([untested-checks-plan.md](untested-checks-plan.md)):

| ID | Rule |
| --- | --- |
| G1 single offer | One bid at opening (bid-opening results, `getOpengResultListInfo*`), fetched for labelled notices and up to 20 random competitive comparisons per labelled buyer-year; unknown elsewhere. |
| G2 private contract | `method` 수의계약. |
| G3 buyer share ≥ 5 % | Contract amount ≥ 5 % of the buyer's total for the signing year. |
| G4 concentration | Same buyer, business type and year: the winner holds ≥ 60 % of ≥ 10 contracts. |
| G5 3+ changes | Three or more later versions (`cntrctOrd` ≥ 03) within 24 months of signature. |
| G6 amount increase | Last version's amount > 120 % of the original. |
| N1 December, N2 weekend | Signature in December; on a Saturday or Sunday. |
| N4 supplier dependence ≥ 25 % | The winner receives ≥ 25 % of the buyer's contract value for that year. |
| N5 first-time supplier | No contract between this buyer and supplier in the three preceding years (unknown when those years are not downloaded). |
| U2 repeated private contract | Private contract, and the same buyer and supplier have ≥ 3 private contracts that year. |

Korean checks (rules from the decrees' wording as cited in `prvtcntrctRsn`):

| ID | Rule |
| --- | --- |
| K1 single-bidder private contract | Private contract on the ground "경쟁입찰을 실시했으나 입찰자가 1인뿐인 경우" (국가계약법 시행령 제27조제3항, 지방계약법 시행령 제26조제2항). |
| K2 re-tender private contract | Private contract after a failed tender (제27조제1항, 지방 제26조제1항). |
| K3 just under the small-value limit | Small-value private contract for goods or services (추정가격 2천만원 이하: 국가 제26조제1항5호가2목, 지방 제25조제1항5호나목) with an amount of KRW 19.8–22 million (90–100 % of the limit with 10 % VAT). |
| K4 split contracts | Two or more small-value private contracts between the same buyer and supplier within 30 days whose sum exceeds KRW 22 million. |
| K5 restricted competition | Method 제한경쟁 or 지명경쟁 rather than 일반경쟁. |
| K6 high award ratio | Contract amount ≥ 95 % of the notice's reserve price (`reserve_price`), where known. |

Expected, stated in advance: collusion labels sit in competitive tenders, so G2, K1–K4 should be rare among them (that says little about private contracts as such); K3/K4 are meant for the audit (irregularity) labels, where they are circular and are reported but not decided. K6 and K5 are the classic bid-rigging candidates; G4 and N4 may fire on rotation cartels.

## Method and decision rule

Decision set: collusion ∪ corruption, one tender or contract per case. A contract with labels from both families counts once. Each family alone, and the union with irregularity, are reported beside it.

As for Romania: buyer-weighted hit rates reported first; LR shrunk toward 1 by a prior worth 10 buyers; 95 % intervals by resampling buyers; points = 10 × log2(LR), floored at 0; no proposal below 10 labelled buyers. Holdout: buyers split in halves by hash; a check passes when the learn-half interval is above 1 and the check-half LR is above 1. Points basis: **one tender per decision**; all linked tenders as a robustness set. Points are Korean only.

## Amendments, 2026-10-20 (preparation; a first, unweighted run of the collusion family had already been seen)

- **Linking accepted only when a second field agrees.** A printed notice number links only if the KONEPS tender name shares ≥ 30 % of its character bigrams with the decision's tender name, or the award amount equals the contract amount when the decision gives no name. Amount + buyer needs the same name agreement. Province names alone do not count as a buyer match. Before this rule, 107 notice-number links pointed at unrelated tenders: misread numbers, or other numbering schemes.
- **Case = decision type + number** (의결 / 결정 / 재결 / 의결(약) are numbered separately). A case split into per-respondent decisions counts once for "one tender per case".
- **Finality** comes from law.go.kr court rulings on suits against KFTC orders (case names with 시정명령 / 과징금; `tools/fetch-korea-lawgokr.py --target ftc-suits`). A ruling must cite both the decision number and the decision date. If the KFTC won at first instance and no appeal ruling is found two or more years later, the case counts as upheld; if the ruling is younger, it counts as pending. law.go.kr publishes only some rulings, so "none" means no challenge found, as defined above.
- **Buyer:** 계약기관 `buyer_code` as planned. 수요기관 `demand_code` is reported as a sensitivity, because most rigged tenders were run by the PPS (조달청) for another body, and the plan's buyer then puts hundreds of labels into one buyer.
- **Not yet computed:** G1 single offer (needs the bid-opening results per notice), and the corruption family (court convictions not linked yet). Until both are done, the "decision set" holds collusion only.
- G5 and G6 count as unknown for long-term continuing contracts (장기계속, whose amounts change by instalment) and when the 24-month window runs past the data's end (2026-09).
