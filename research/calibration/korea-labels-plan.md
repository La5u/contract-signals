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

## Decision rule amendment, 2026-10-20 (owner: the safeguards were too strict; fewer, more lenient, and less certainty means fewer points)

Made after results under the old rule had been seen (Romania, Colombia, Ukraine and the Korean preparation run). It applies to every country alike and is implemented once, in `tools/propose-indicator-points.py` (`decide`).

- **Kept:** at least 10 labelled buyers; buyer-weighted rates (each buyer counts once); LR shrunk toward 1 by a prior worth 10 buyers; 95 % intervals from resampling buyers.
- **Points from the evidence we are 75 % sure of:** points = 10 × log2 of the shrunk LR at the 25th percentile of the buyer resamples (never above the shrunk LR itself), floored at 0. Uncertainty lowers the points instead of excluding the check; any check reliably above LR 1 gets some points, possibly a fraction of one.
- **Dropped:** the requirement that the learn half's 95 % interval lie above 1 and the check half's LR exceed 1 (the halves are still reported), and one tender/procedure per case as the points basis: all linked tenders are the basis, one per case is reported as robustness.
- Hit rate stays the first column reported, as before.

## Bid-level checks, fixed 2026-10-22 (before any bid of a labelled tender or of its comparisons was downloaded)

Seen beforehand: the field list and value vocabulary of one 2024-25 day file (no label, no rate). Bid-opening rows from
the open-standard dataset (`getDataSetOpnStdScsbidInfo`, `tools/fetch-korea-bid-results.py bids`), joined to contracts
by `bidNtceNo` = `notice_no`.

- **Days fetched:** every opening day of a labelled notice (`bids-label-days.txt`, 280 days 2009–2023), plus a fixed
  sample of 24 days per label year (the days whose SHA-256 of `korea-comparison-day:YYYY-MM-DD` is smallest among
  that year's days; weekends included, they are few and cheap). All four business types.
- **Universe:** contracts (as in `contracts_from`, originals only) of the labelled buyer-years whose notice has bid
  rows on a fetched day; everything else is unknown. Same buyer modes, weights, comparisons and decision rule as above.
  Comparisons are contracts of the same buyer-years whose notice opened on a fetched day (label days and sampled days
  alike).
- **Opening used:** of a notice's openings (`bidNtceOrd`, re-tenders), the one whose order equals the contract's
  `notice_ord`; else the latest with a winner (`sucsfYn` Y); else the latest. Bids counted: rows of that opening.
  "Valid" bids (B4, B5) are those with `dqlfctnRsn` 정상: bids below the lower limit (낙찰하한선 미달) lose by rule and
  are left out of the dispersion screens; they are not disqualifications either (B6).
- Amended 2026-10-22, still before any labelled bid was read: opening by `notice_ord` first; B4/B5 on 정상 bids only
  (were: 정상 and 낙찰하한선 미달); B5's gap is between the two lowest valid bids, its spread that of the valid bids
  other than the lowest (at least two, so B4/B5 need three valid bids). Reference percentiles (B4, B5) are computed
  over every opening in the downloaded day files of the same business type and opening year.

| ID | Rule |
| --- | --- |
| B1 single bid (G1) | One bid row at the opening. |
| B2 few bids | Two or three bid rows. |
| B3 just above the lower limit | Winner's bid rate (`bidprcRt`) less than 0.1 points above the lower-limit rate (`sucsfLwstlmtRt`); unknown without a lower-limit rate. |
| B4 low bid dispersion | Three or more valid bids, and the coefficient of variation of their amounts below the 10th percentile of all fetched openings of the same business type and year with three or more valid bids (screen from the cartel literature: cover bids cluster). |
| B5 large first gap | Three or more valid bids, and (2nd lowest − lowest valid amount) / standard deviation of the losing valid amounts above the 90th percentile, same reference (relative-distance screen). |
| B6 better bids disqualified | Two or more bids lower than the winner's excluded for a reason other than 정상 / 낙찰하한선 미달 (cf. Ukrainian C3). |
| B7 same-minute bids | Two to twenty bid rows, and two or more of them submitted in the same minute (`bidprcDate` + `bidprcTm`). |

Not tested: rotating winners and losers who never win (need every tender of a buyer-year, not sampled days). B1 and B2
are expected among collusion labels (cover bidders keep the field small); B3 is common in lawful 적격심사 tenders.
Everything else (weights, buyer modes, points rule) as in the amendments above; size control applies only if a check
turns out size-like.

## Further checks, fixed 2026-10-22 (before any rate of them was computed)

Sources: bid rows as above; for B11 and B12 also the PPS Data Hub report UI-ADOFAA-011R (every bidder of every tender
by notice week, 2010–2023, `tools/fetch-korea-datahub-bids.py`); keyed CEO-name hashes of the fetched days
(`fetch-korea-bid-results.py ceos`: names never stored); bid notices from the open-standard notice dataset
(`fetch-korea-bid-results.py opnstd-notices`, joined by `bidNtceNo`, the notice's latest order). Same universe,
weights, comparisons and decision rule as the bid-level checks; unknown where the input is missing.

| ID | Rule |
| --- | --- |
| B8 exact floor hit | Winner's bid rate less than 0.01 points above the lower-limit rate (B3 at a tenth of its margin: knowing the drawn reserve price, which is set only at opening, is the classic leak). |
| B9 shared CEO | Two or more bidders with different business numbers share a CEO hash, counting only hashes held by at most 3 business numbers in all CEO files (common names left out). Unknown without CEO rows for the opening. |
| B10 rotation | Some other bidder of the opening bid against the winner in at least 3 other openings of the same demand institution within 365 days either side, and won at least one of them while the winner bid. Needs the full bid history (B11 below). |
| B11 repeated quote pair | Openings of 2–20 bids: two bidders whose bid rates differ by the same non-zero amount (3 decimals) in this opening and in at least 2 other openings within 365 days either side. Needs the full bid history. |
| N6 short notice period | Days from notice date to bid deadline (`bidClseDate`) below the general minimum of the State Contract Act decree art. 35: works estimated price < 1 bn KRW 7 days, 1–5 bn 15 days, ≥ 5 bn 40 days; goods and services 7 days. Re-notices (`bidNtceSttusNm` containing 재) left out (5 days allowed); urgent notices cannot be told apart in this dataset, so some lawful 5-day urgent notices count as hits. |
| N7 just below a threshold | Estimated price (`presmptPrce`) in [0.97 T, T) for T in 100 m, 200 m, 300 m, 1 bn, 5 bn, 10 bn, 20 bn, 30 bn KRW (main breakpoints for procedure, regional restriction, PQ and evaluation method; a fixed screening list, not the exact year-by-year legal values). |

Not testable with public data: debarred winner (the public API lists only sanctions active today; a historical register
needs a PPS disclosure request) and evaluation scores (published only as per-tender attachments, mostly from 2020).
The 15 drawn reserve prices (복수예비가격) are fetched under the development quota; a B8 variant on them is left for later
and will be fixed here before it is computed.

## Audit family, fixed 2026-10-24 (owner: audit findings as a separate family; a 80-report pilot had been seen)

Seen before this amendment: the pilot in [korea-bai-pilot-2026-10-24.md](korea-bai-pilot-2026-10-24.md) (80 reports,
97 linked contracts, check rates next to the court family). Everything below applies to the full run, not the pilot.

- **Labels.** Findings of Board of Audit and Inspection reports (감사원 감사결과 공개문, taken from the BAI press
  releases on korea.kr because bai.go.kr's `/api/` is robots-disallowed) that tie an irregularity to a specific
  public contract, linked to KONEPS by the court matcher's routes (`tools/match-korea-court-contracts.py`). Sample:
  every audit-result release 2016–2026 with a report PDF and at least 30 procurement terms. One label weight of 1
  (an audit finding is not appealed like a court ruling); one case = one report.
- **Separate family.** Audit labels are never pooled with collusion (KFTC) or corruption (court) labels. Each check
  is rated in each family with the existing decision rule (shrinkage, LR at the 25th bootstrap percentile, ≥ 10
  labelled buyers).
- **When audit points count.** A check's points from the audit family count only if the corruption family does not
  contradict them: contradiction = the court family has ≥ 10 labelled buyers and its LR's 95 % upper bound is below 1.
  A check's points are the largest among the families that count; the family-max index is unchanged.
- **Size.** Size-like checks (G3 buyer share, N4 supplier dependence, and any check whose rate rises with contract
  value) earn audit points only under the value-band control with labelled prices ÷ 1.3, as for the other families;
  auditors, like prosecutors, select large contracts.
- **Outcome classes.** Each finding is classed by the action the report requests: (a) recovery, fine or payment
  correction (환수, 회수, 변상, 시정 with an amount), (b) criminal referral (고발, 수사요청), (c) discipline or warning only
  (징계, 주의, 통보). Rates are reported for all findings and for (a) + (b) alone; the (a) + (b) result is the
  sensitivity closest to reward-eligible cases and is shown next to the main one, not used for points.
- **Quality.** Quotes are checked verbatim against the report text; reports with flags (quote not found, low
  confidence) get a second reading by another model before linking; a hand check of 20 random links is reported.

## Round-number checks, fixed 2026-10-24 (owner idea; heaping measured on all contracts, no label rate seen)

Measured first on all 1.70 M price increases between consecutive contract versions (opnstd 2010–2026, labels not
looked at): increases heap at ratios of small whole numbers (+100 % ×996 its neighbours, 50 % ×86, 66.67 % ×56,
33.33 % ×32, 25 % ×21, 20 % ×12, 11.11 % ×11, 10 % ×9, 16.67 % ×9, 42.86 % ×9, 71.43 % ×12), i.e. quantity or period
changes (2 → 3 units, 9 → 10 months); exact whole-percent increases outside those ratios are rarer (5 % 550, 15 % 384,
4 %, 8 %, 12 %); 139,379 contracts have 2+ increases, a few hundred of them by the same step. 3.5 % of contract amounts
have one significant digit, 10.8 % two. Checks (contract-level letters in `tools/korea-label-checks.py`; same window
and long-term exclusion as G5/G6):

- **A1 round-percentage increase**: an increase that is an exact whole percentage of the previous amount and whose
  ratio new/old is not a fraction with denominator ≤ 9 (those are the quantity/period heaps). Sensitivities reported
  next to it: all exact whole-percent increases; and A1 without exactly +10 % (also the VAT rate).
- **A2 same step repeated**: two or more increases of the same percentage (to 0.01) of at least 1 % in one contract.
- **A3 / A4 round contract amount**: the original amount has one (A3) or exactly two (A4) significant digits.
- **A5 / A6 round budget**: the notice's allocated budget (asignBdgtAmt, open-standard notices) has one (A5) or exactly
  two (A6) significant digits; unknown without a notice or budget.
- Expected confounders, reported with the rates: round amounts are typical of private contracts at legal limits
  (K3) and of budgets set before pricing; A3–A6 are rated within buyer and by contract method as a control.

## Standard bid indicators, fixed 2026-10-24 (owner: universal, standardised indicators; seen before: B1, B2, UA-C1, UA-C2 results)

Per [indicator-standard.md](indicator-standard.md): BID-COUNT replaces B1/B2/UA-C1 as one graded indicator with bins
1, 2, 3, 4–5, 6–10, 11+ submitted offers (opening `bids`); BID-VALID has the categories "only one valid of 2+" (`valid`
= 1, `bids` ≥ 2) and "2+ better-ranked rejected" (B6). Each bin is rated against comparisons with the decision rule,
for the collusion, corruption (court) and audit families separately, one per case and all linked tenders. A record's
points are its bin's points. Already seen and not to be used for choosing bins: B1, B2, UA-C1, UA-C2 rates (2026-10-24).
PRICE-RATIO (award ÷ reserve price) is next: bins at the comparison deciles, number of bins by case-held-out
cross-validation, not computed in this step.

## PRICE-RATIO curve, fixed 2026-10-24 (before any bin rate was computed; seen before: K6 ≥ 95 % and UA-C9 ≥ 98 % rates)

Per [indicator-standard.md](indicator-standard.md), kind 3. Tool: `tools/korea-curves.py` (research only).

- **Measure:** the first version's contract amount ÷ its reserve price (예정가격, `reserve_price`), the fields K6 uses.
  Unknown without both. Records, labels, weights and comparisons are those of `tools/korea-label-checks.py` (labelled
  buyer-years, original versions, finality and court weights).
- **Bins:** K equal-count bins with edges at the quantiles of the comparisons' ratios (every comparison record with a
  ratio counts once; labels never place edges); edges that coincide (heaping at the legal lower limits) are merged.
  K ∈ {2, 3, 4, 5, 6, 8, 10, 12, 15, 20}.
- **Number of bins by cross-validation over whole cases:** labelled cases in 5 folds by a hash of the case key,
  comparisons in 5 folds by a hash of the buyer. On the training folds each class's bin distribution is estimated
  buyer-weighted (each buyer counts once, with its largest label weight, as in the decision rule) with 0.5 added per
  bin; the score is the held-out balanced log-loss (the two classes weighted equally, buyer-weighted within each).
  Chosen K: the smallest K whose mean loss is within one standard error (over folds) of the best K.
- **Points per bin:** each bin is rated as a yes/no check (in this bin vs any other known ratio) with the decision rule
  (`propose-indicator-points.decide`: ≥ 10 labelled buyers, shrinkage of 10 buyers, 25th bootstrap percentile).
  Bins with LR below 1 are counter-signals (0 points). No further smoothing; a non-monotone curve is reported as is.
- **Best single cut-off:** "ratio ≥ c" with c at the comparison percentiles 1–99; the c with the lowest
  cross-validated loss of the two-bin split, the c chosen on each fold's training part, and a 200-resample bootstrap
  (cases resampled for labels, buyers for comparisons) for its interval; its points by the decision rule. The former
  95 % and 98 % cut-offs are listed beside it for reference only.
- **Families and basis:** collusion (KFTC) is the decision basis, all linked tenders; one tender per case is reported
  as robustness. Corruption (court) and audit (Board of Audit) families are run and reported separately with the same
  bins (edges from their own comparisons). Nothing is adopted on the site without the owner's decision; BUYER-SHARE,
  SUPPLIER-DEPENDENCE, AMEND-PRICE and BID-GAP/SPREAD (within BID-COUNT bins) follow with the same method.
- **Amendment 2026-10-25 (after the collusion, court and audit curves had been seen):** the cross-validated cut-off
  is found by a loss that has no direction, so it is rated on the side where labels are more common than
  comparisons ("≥ c" or "< c"), not always "≥ c". Prompted by the court family, whose signal lies below its best cut
  (87.8 %) and showed LR 0.77 when rated as "≥ c". Bins are unchanged.
- **Fine scan, owner request 2026-10-25 (the binned curves above had been seen):** award ÷ reserve in 0.1 % bins from
  70 % to 100 % (plus < 70 % and ≥ 100 %), each bin rated with the decision rule (bin vs any other known ratio,
  buyer resamples), Benjamini–Hochberg at 10 % over the bins on the bootstrap share of LR ≤ 1, and a replication test:
  labelled cases split in two halves by hash; the correlation between the halves of the fine-scale label excess
  (log label ÷ comparison share minus its ±1 % moving average) against 500 draws in which both halves come from the
  smoothed label distribution. A fine peak counts as replicated only if the correlation is above the draws' 95th
  percentile and the peak appears in both halves. Descriptive: points stay with the binned curve until the owner decides.
  Tool: `tools/korea-price-ratio-fine.py`; graphs in `~/.cache/contract-signals/korea/plots/`.
- **Fine-scan test corrected 2026-10-25 (after the first collusion graph had been seen):** the first replication
  statistic included the comparison share, which both halves share, so pure noise already correlated (null mean 0.51).
  It now uses the label counts only: each half's counts minus the smooth label curve (±1 % moving average) times the
  comparisons' own fine structure (comparison share ÷ its moving average, so heaping at legal floors is expected), in
  standard units; nulls are
  halves drawn from the smoothed label distribution and random case halves. Also checked at 0.2, 0.5 and 1 % widths.

## One range per continuous indicator, fixed 2026-10-25 (owner; PRICE-RATIO curves and 0.1 % scans had been seen, no other measure's rates)

- **Owner decision:** each continuous indicator gets one signal range [a, b) for now; a second range only where it
  obviously helps (reported, not adopted, until the owner agrees). Multi-bin curves and fine scans stay descriptive.
- **Range:** a and b at the comparison percentiles (1–99, plus the minimum and maximum, so one-sided cut-offs are
  included); only ranges where the training labels' share exceeds the comparisons'. Chosen by the lowest mean
  held-out balanced log-loss of the two-bin split (in range / not), the same 5 case folds; the folds' own choices and
  a 200-resample bootstrap (cases, buyers) reported. Points: the decision rule on "in range".
- **Measures in this step** (`tools/korea-curves.py`, contract fields only):
  - PRICE-RATIO: as above.
  - BUYER-SHARE: the contract's original amount ÷ its buyer's total original amount that year (G3's measure).
  - SUPPLIER-DEPENDENCE: the supplier's total original amount with the buyer that year ÷ the buyer's total (N4's).
  - AMEND-PRICE: last ÷ first amount within 24 months − 1 (G6's); unknown for long-term contracts and incomplete windows.
- **Size control:** BUYER-SHARE and SUPPLIER-DEPENDENCE contain the contract amount, so they are size-like (owner
  rule 2026-10-20). The range is chosen with comparisons reweighted, within each buyer, to the labels' value-band mix
  (labelled amounts ÷ 1.3; bands of `korea-bid-controls.py`), and rated both raw and with the value-band control
  (`korea-bid-controls.analyse`, factor value); the controlled points are the decision. PRICE-RATIO and AMEND-PRICE
  are ratios of the contract's own amounts and are not size-controlled; their value-controlled rating is reported.
- Families: collusion (decision basis), court and audit, all linked tenders; one per case as robustness.
- **Fine-scan test revised 2026-10-25 after Sol's review (all fine results had been seen):** cases are counted at
  most once per 0.1 % bin (a case with many tenders at one price counts once), the null draws each half's case-bin
  counts from the smooth curve × the comparisons' heaping, and the smoother is local-linear (no edge artefacts).
  Checked on synthetic data: planted multi-case peak found (0.47 vs 95th 0.15), one clustered case per bin and a
  linear trend not flagged, 7 of 100 clustered null datasets at p < 0.05. Also: bootstrap draws without labels or
  comparisons rejected, points gated at 10 labelled buyers, and in `korea-curves.py` resampling counts now scale a
  buyer's whole contribution (they had cancelled in the normalisation).
- **FLOOR-GAP, added 2026-10-25 before any rate of it was computed (owner agreed to a floor-relative measure; the
  PRICE-RATIO curves and fine scans had been seen):** winning bid rate minus the opening's stated minimum winning
  rate (낙찰하한율, `sucsfLwstlmtRt` in the KONEPS bid results, `lower_rate` in `korea-bid-features.py`), in
  percentage points; unknown without an opening, a winner or a stated floor (0 = no floor). The floor is the legal X
  (kind 2: KONEPS states the value the applicable rule sets; it matches the 적격심사 and small-quotation tables), the
  distance above it is continuous (kind 3) and gets one range as above. Not size-like. Same opening as the B checks.
  Its values heap below 1.5 points (comparisons' mean gap 1.07); rigged tenders were seen to avoid the floor heaps.
- **Range gate, 2026-10-25 (after the first collusion ranges had been seen):** a range is accepted only if its
  nested held-out loss beats "no split" (log 2) by more than one standard error over the case folds (each fold's
  range chosen on its training part and scored on its held-out part; a first, non-nested version accepted pure noise
  in a synthetic test); otherwise the measure
  gets 0 points and its range is reported only. Prompted by BUYER-SHARE, SUPPLIER-DEPENDENCE and AMEND-PRICE, whose
  best ranges came within 0.003 of log 2 and were near-empty or near-full (noise), while PRICE-RATIO gained 0.11.

## Two ranges for audit PRICE-RATIO, fixed 2026-10-25 (owner chose this after the audit one-range result had been seen)

- **Why only here:** the audit family's one-range search split between the folds (three chose just under the
  reserve, 99.4–100 %, two the low end, 72–88 %), the two-ended pattern of the binned curve and the 0.1 % scan.
  Owner rule: a second range only where it obviously helps.
- **Two ranges:** disjoint [a, b) and [c, d), edges at the comparison quantiles in 2 % steps (plus open ends), each
  range alone with a training label share above the comparisons'. Chosen by the lowest in-sample balanced log-loss of
  "in either range" vs not, nested in the same 5 case folds.
- **Gate:** accepted only if (1) the nested held-out gain over no split exceeds one standard error over the folds and
  (2) the nested held-out gain over the one-range choice (paired by fold) also exceeds its standard error.
- **Points:** the decision rule on "in either range" (one check, one set of points); each range's own rate and LR
  reported. Value-band control reported. Collusion and court stay at one range.

## Counter-ranges and negative points, fixed 2026-10-25 (owner: "maybe negative points for close to floor"; FLOOR-GAP results had been seen)

- **Counter-range:** for a measure, one range [a, b) where labels are *less* common than comparisons, chosen and
  gated exactly like the signal range (nested case folds; held-out gain over no split above one standard error).
- **Negative points (research; changes the decision rule's floor at 0, so nothing goes on the site without the
  owner's decision):** 10 × log2 of the shrunk LR at the **75th** percentile of the buyer resamples (the mirror of the
  25th percentile used for positive points; never below the shrunk LR itself), capped at 0, at least 10 labelled
  buyers. Uncertainty pulls negative points towards 0, as it pulls positive points towards 0.
- **Family scope:** negative points count only within the family whose labels produced them (a near-floor bid argues
  against collusion, not against corruption: the court family's labels sat at the floor). How a family combines its
  positive maximum with a negative check is a scoring-design question for the owner; proposal: family score =
  largest positive points + most negative counter points, floored at 0.
- **First tested:** FLOOR-GAP and PRICE-RATIO, collusion family; court and audit reported.
- **Court and audit stay separate families** (owner 2026-10-25), each with its own ranges and points.
