# South Korea: checks against KONEPS tenders found rigged by the Fair Trade Commission — first results (2026-10-20, preparation run)

Plan and amendments: [korea-labels-plan.md](korea-labels-plan.md). Research only: no score, weight or dataset change without the owner.
Scripts: `tools/extract-korea-kftc-tenders.py` (tender tables read from decision images), `tools/match-korea-kftc-tenders.py`
(links to KONEPS notices), `tools/check-korea-kftc-finality.py` (court outcomes), `tools/korea-label-checks.py` (this table).

**Status: preparation, not a decision.** Decision rule as amended 2026-10-20 (owner: fewer, more lenient safeguards): all linked tenders, points from the LR we are 75 % sure of; see the plan. Collusion family only (court convictions not linked yet).
Finality: law.go.kr publishes 100 court rulings on KFTC bid-rigging
orders, and only 2 of them cite one of the 124 cases with linked tenders (both upheld). The other cases count as "no challenge
found", weight 1.

**Rerun 2026-10-22:** contracts whose original version (ord 0) is not in the data are no longer labels, comparisons or part of any total (their signing year and original amount are an amendment's); 3 linked notices drop out (721 with a contract; two have no original anywhere in the data), and comparisons fall from 432,515 to 409,522 (mostly contracts signed before the scan window, whose in-window changes had been taken for originals). Decision-rule points moved by at most 0.6 (G3 7.6 → 8.2, K5 3.5 → 3.7).
**Bid-level checks, 2026-10-22:** B1-B7 as fixed in the plan ("Bid-level checks"), from the KONEPS bid-opening results (`tools/fetch-korea-bid-results.py bids`, label days plus 24 sampled days per label year, 2010-2026; `tools/korea-bid-features.py`: 5,424 day files, 1,461,145 openings). A contract's B checks are unknown when its notice's opening is not in those days, so they are rated on 294 labelled tenders and 38,809 comparisons (buyer = contracting office). All other rows are unchanged. Under the decision rule B2 two or three bids earns 14.8 points, B5 large first gap 12.1 and B4 low bid dispersion 4.5; B1, B3, B6 and B7 earn none (B1 and B3 are rarer among rigged tenders than among comparisons; a cartel needs at least two bidders, so B1 cannot work on these labels, and G1 single offer stays uncomputed). The demanding-body sensitivity agrees (13.5, 12.0, 4.0). Size does not explain them: size-standardised, rigged values / 1.3, B2 16.2, B5 13.2, B4 4.7 ([korea-buyer-share-size-results.md](korea-buyer-share-size-results.md)); points use the lower, decision-rule values.
**Bid-level rerun and further checks, 2026-10-24:** bid openings now cover every day 2008-07..2019 plus the earlier sampled days (KONEPS API day files and Data Hub exports; `tools/korea-bid-features.py`: 13,192 day files, 3,212,914 openings), so B1-B9 are rated on 612 labelled tenders and 125,417 comparisons (buyer = contracting office). B10 and B11 come from `tools/korea-bid-history.py` (rolling 731-day bid history per opening; complete for openings to 2019, so 380 and 158 labelled tenders have a value). Decision-rule points of B1-B7 shift from the 2026-10-22 run: B2 14.8 → 12.1, B5 12.1 → 11.0, B4 4.5 → 1.0, B7 0 → 2.2 (demanding body: B2 11.4, B5 9.3, B4 0, B7 10.9, a large gap between the modes for B7); the live site still has the 2026-10-22 points (owner decision). The six further checks fixed 2026-10-22 earn no points in either mode: B8 exact floor hit 7 % vs 19 %, B9 shared CEO 1 % vs 6 %, B10 rotation 15 % vs 55 %, B11 repeated quote pair 6 % vs 12 %, N6 short notice period 44 % vs 52 %, N7 just below a threshold 1 % vs 2 %. Rigged tenders have few bidders (59 % have two or three, B2) and B3, B8-B11 fire more often the more bidders an opening has, so the raw rates are confounded by bidder count. Descriptive check, not the decision rule (unweighted, every opening with that number of bidders as comparison; exact count up to 20, then bins of 25): observed / expected hits among rigged tenders are B3 0.51 (65 / 128.6), B8 0.99 (59 / 59.5), B9 1.14 (6 / 5.3), B10 0.85 (128 / 150.3), B11 0.21 (7 / 33.3). So B8 and B9 carry no information once size is controlled (B9's 6 hits cannot separate 1.14 from 1), and B3, B10 and B11 are rarer on rigged tenders even at equal size: a cartel's designated winner bids well above the floor (which K6 already scores) and cover bids are not the repeated close quotes B11 looks for.

**Controls for bidder count, value, type, period and winner size, 2026-10-24 (research only, not the decision rule):** `tools/korea-bid-controls.py` (same labels, weights and comparisons as the decision set; output `~/.cache/contract-signals/korea/bid-controls-{contract,demand}-2026-10-24.{txt,json}`). Each rigged tender is compared with the buyer-weighted comparison rate of its own stratum (bidder count of the opening; value band, rigged amounts divided by 1.3; business type; period 2008-12/2013-16/2017-19/2020+; winner's contract value with every buyer in the three previous years), falling back to a coarser stratum under 30 comparisons or 5 comparison buyers; same shrinkage and 25th-percentile points rule. The uncontrolled column reproduces the decision rule (contracting office: B2 12.1, B5 10.7, B4 1, B7 2.2). Rigged tenders differ in exactly these factors: 2 bids 35 % vs 18 % of comparisons, ≥ 101 bids 0 % vs 9 %, value ≥ 300 M KRW 50 % vs 29 %, winner ≥ 10 bn KRW prior value 43 % vs 28 % (contracting office). Points (contracting office / demanding body):

| Check | Raw | Bidders | Bidders x value x type | + period | + winner size | Value x type x period x winner (no bidders) | Within buyer x bidders x value |
|---|---|---|---|---|---|---|---|
| B2 two or three bids | 12.1 / 11.5 | (by construction 0) | – | – | – | 8.3 / 7.3 | 8.7 / 8.5 |
| B5 large first gap | 10.7 / 9.3 | 1.0 / 0 | 1.9 / 0.9 | 2.0 / 1.1 | 0.9 / 0.4 | 6.1 / 6.0 | 0.7 / 0.4 |
| B4 low bid dispersion | 1.0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| B7 same-minute bids | 2.2 / 10.9 | 0 / 8.8 | 0 / 1.4 | 0 / 1.0 | 0 / 1.0 | 0 / 2.1 | 0 / 0 |
| K6 award >= 95 % of reserve | 11.7 / 10.3 | 9.5 / 9.1 | 6.2 / 5.4 | 5.6 / 4.9 | 5.4 / 5.4 | 5.8 / 4.1 | 9.5 / 8.3 |
| K5 restricted competition | 3.7 / 4.2 | 0 / 0.5 | 0 / 0.1 | 0 / 0.4 | 0 / 0 | 0.9 / 3.5 | 0.6 / 0.8 |
| G3 buyer share >= 5 % | 8.2 / 6.8 | 18.6 / 15.1 | 20.1 / 15.6 | 16.8 / 15.3 | 20.1 / 16.4 | 12.0 / 13.1 | 6.2 / 1.9 |

B1, B3, B6, B8-B11 earn no points under any control in either mode (B8 4.9 / 4.1 in the demanding-body mode under bidders and bidders x value only; gone once business type enters). Reading: B5's points are mostly B2 counted again (few bidders make a large first gap likely); what is left after bidder count is ≤ 2 points. B7's gap between the modes is business type: it vanishes once type is controlled. B2 keeps about 8 points after value, type, period and winner size, and within buyer. K6 loses about half its points to business type and value (works tenders sit near the reserve price more often). G3 rises under cross-buyer strata because which buyers fill a cell changes its rate; within buyer it is 6.2 / 1.9, consistent with the size control of 2026-10-20 (G3 is size-like and was already cut). Bidder count is partly an effect of rigging (cartels deter entry), so controlling the other checks for it is meant to avoid counting B2 twice, not to deny B2. Firm size from the Data Hub field 계약시점기업구분 (winners only): about 95 % of winners are small and medium firms, too little variation to control for; prior contract value is used instead and includes the cartel's own awards.



Labels: 1,218 KFTC bid-rigging decisions → 12,534 tenders read → 6,480 public tenders → 1,087 linked to one KONEPS notice
(416 by winner + amount, 269 by notice number, 249 by amount + buyer, 153 by winner + buyer + name; 109 ambiguous,
5,284 unmatched, mostly buyers outside KONEPS: DAPA, KEPCO, the Korea Expressway Corporation, KORAIL) → 740 notices in 106 cases.

Agency links (2026-10-24, `tools/match-korea-kftc-agencies.py`, research only, not yet in the label checks): the 5,284
unmatched tenders run through the same rules against DAPA contracts (domestic 2003–2026; facility to 2021-12 at the time;
foreign not yet downloaded), LH contracts 2007–2026 and KOGAS bid results 2009–2026. Agency-only limits on winner +
buyer + name: the tender needs its own date, and a known award ≥ 1M KRW must be within 5 % of the record (smaller
awards are unit prices). Result: 225 tenders linked (130 winner + amount, 74 winner + buyer + name, 21 amount + buyer;
DAPA 89, LH 75, KOGAS 61) → 122 agency notices; 33 decisions had no linked tender before; 238 ambiguous, 4,821 still
unmatched. Defence misses: about 40 % have no winner, amount or date read; many winners (military food at unit prices,
unit-run repair purchases) are not in the DAPA contract feed at all. Spot check of 16 links: all the same purchase.
These tenders have no KONEPS bid or contract data, so they can only feed checks computed inside each agency's own
records (K6 from DAPA planned price / KOGAS award rate, G3/N4 within the agency), which needs a plan amendment first.

MAS call-off links (2026-10-24, `tools/match-korea-kftc-mas.py`, research only, not yet in the label checks): the
three decisions on 다수공급자계약 second-stage competitions (14663 GRP pipe and manholes, 15581 PE-coated steel pipe,
14711 hume pipe; 646 tenders) award a shopping-mall delivery request (납품요구), not a contract, so no tender was in
the open-standard contracts. Source: PPS Data Hub report UI-ADOXFA-190R (특정품목 조달 내역, guest CSV export,
`tools/fetch-korea-datahub-items.py`), five goods classes × 2010–2016, 81,005 delivery requests, 1,557 flagged
이단계경쟁제안서제출여부 = Y. A request is its original version (변경차수 00) summed over all its item lines and
classes. Linked only on the award amount (± 0.05 %) plus tender-name similarity ≥ 0.3; 14663 prints awards without VAT
(request = award × 1.1), 15581 with VAT. Result: 572 of 646 linked (14663 230/268, 15581 206/230, 14711 136/148),
66 ambiguous, 8 unmatched; 572 distinct requests (none claimed twice), 204 demanding bodies, 2011–2016. Every decision
winner maps to exactly one business number, including renamed firms (한국화이바 = 스페이스프로, 서울강관 = 에스엘,
신이피엔씨 = 제우피엔씨) and the masked A사/B사. Name similarity alone was rejected: sister projects differ by one
character (군산/온산 처리구역). These are framework call-offs among a closed set of MAS suppliers: the bid-level
checks (B1–B11) and K5/K6 do not apply as defined for open tenders, so they need their own comparison set (other
second-stage requests of the same classes) before any rate is computed.

Debarment links (2026-10-24, `tools/match-korea-debarments.py`, research only): the current-sanctions snapshot
(580 rows from 2022-09) has 124 fraud-type sanction decisions on 121 firms, classed by legal ground: bad performance
36, forgery 40, collusion 29, fraud 13, bribery 6 (non-performance, refusal to sign, subcontracting and paperwork
grounds left out). A debarment does not name its contract, so candidates are the firm's contracts (business number)
with the sanctioning institution or its own sub-units (code, or a name starting with the institution's; a
province or metropolitan city does not cover its cities, counties and districts; 조달청 = any PPS office), signed in
the five years before the notice. 14 decisions leave exactly one contract (e.g. 코오롱생명과학 응집제 2022, collusion),
68 a firm-buyer pair with 2–113 contracts (1,071 contracts, 154 buyers in all), 17 only contracts with other buyers,
25 none in the data. Pairs by family: bad performance 28, collusion 21, forgery 21, fraud 7, bribery 5. The label
unit is the firm-buyer pair (or the single contract); firm-level labels would mostly mark the firm, not how a
contract was won, so collusion and bribery pairs are the ones closest to the checks.

## Buyer = contracting office (plan)

    740 linked notices in 106 cases; 721 with a contract in the data; 228 buyer-years (buyer_code); 432671 contracts
    finality: {'none': 699, 'upheld': 22} 

### weighted, one per case, all contracts (decision basis until 2026-10-20): 102 labelled (50 buyers), 409522 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 14% (8/102, 50 buyers) | 65% (180399/409522, 133 buyers) | 0.35 [0.23, 0.48] | 0.395 / 0.497 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 32% (18/102, 50 buyers) | 19% (514/409522, 133 buyers) | 1.551 [1.00, 2.37] | 1.43 / 1.488 | 6.3 [0.0, 12.4] | 4.2 points |
| G4 concentration | 15% (8/92, 41 buyers) | 16% (12570/409134, 105 buyers) | 0.949 [0.51, 1.47] | 0.966 / 0.909 | 0.0 [0.0, 5.5] | no points |
| G5 3+ changes | 7% (4/84, 41 buyers) | 3% (16401/385595, 133 buyers) | 1.861 [0.35, 3.91] | 1.589 / 1.598 | 9.0 [0.0, 19.7] | 2.6 points |
| G6 amount increase > 20 % | 7% (4/84, 41 buyers) | 3% (26557/385587, 133 buyers) | 1.621 [0.33, 3.28] | 0.507 / 2.304 | 7.0 [0.0, 17.2] | 0.6 points |
| N1 December signature | 12% (17/102, 50 buyers) | 10% (48275/409522, 133 buyers) | 1.204 [0.52, 1.97] | 1.402 / 0.836 | 2.7 [0.0, 9.7] | no points |
| N2 weekend signature | 1% (1/102, 50 buyers) | 1% (2460/409522, 133 buyers) | 0.948 [0.15, 3.22] | 0.27 / 1.467 | 0.0 [0.0, 16.9] | no points |
| N4 supplier dependence >= 25 % | 21% (12/102, 50 buyers) | 22% (4873/409522, 133 buyers) | 0.969 [0.59, 1.47] | 1.052 / 0.867 | 0.0 [0.0, 5.5] | no points |
| N5 first-time supplier | 38% (16/58, 31 buyers) | 49% (82443/296398, 97 buyers) | 0.818 [0.58, 1.08] | 0.927 / 0.752 | 0.0 [0.0, 1.2] | no points |
| U2 repeated private contract | 6% (3/102, 50 buyers) | 29% (96289/409522, 133 buyers) | 0.339 [0.17, 0.55] | 0.359 / 0.522 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/102, 50 buyers) | 0% (2167/409522, 133 buyers) | 0.167 [0.14, 0.20] | 0.27 / 0.303 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/102, 50 buyers) | 2% (18626/409522, 133 buyers) | 0.167 [0.14, 0.20] | 0.27 / 0.303 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/102, 50 buyers) | 0% (348/409522, 133 buyers) | 0.167 [0.14, 0.20] | 0.27 / 0.303 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 2% (1/102, 50 buyers) | 1% (2242/409522, 133 buyers) | 1.205 [0.15, 3.60] | 0.27 / 1.978 | 2.7 [0.0, 18.5] | no points |
| K5 restricted competition | 45% (45/102, 50 buyers) | 26% (137859/409522, 133 buyers) | 1.615 [1.17, 2.10] | 1.411 / 1.633 | 6.9 [2.3, 10.7] | 5.5 points |
| K6 award >= 95 % of reserve | 64% (49/73, 33 buyers) | 26% (175613/309409, 129 buyers) | 2.072 [1.57, 2.62] | 1.867 / 1.85 | 10.5 [6.5, 13.9] | 9.2 points |
| B1 single bid | 5% (2/73, 38 buyers) | 5% (39761/125417, 119 buyers) | 1.012 [0.19, 2.35] | 0.849 / 1.127 | 0.2 [0.0, 12.3] | no points |
| B2 two or three bids | 60% (52/73, 38 buyers) | 22% (34159/125417, 119 buyers) | 2.326 [1.76, 3.00] | 2.032 / 2.146 | 12.2 [8.1, 15.9] | 10.9 points |
| B3 just above the lower limit | 17% (15/71, 37 buyers) | 42% (30668/125027, 119 buyers) | 0.54 [0.33, 0.77] | 0.629 / 0.613 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 12% (3/20, 16 buyers) | 10% (5337/50613, 112 buyers) | 1.067 [0.43, 2.01] | 1.47 / 0.704 | 0.9 [0.0, 10.1] | no points |
| B5 large first gap | 38% (6/20, 16 buyers) | 10% (6151/50613, 112 buyers) | 2.654 [1.17, 4.50] | 2.219 / 2.061 | 14.1 [2.3, 21.7] | 10.7 points |
| B6 better bids disqualified | 0% (0/71, 37 buyers) | 2% (2216/124868, 119 buyers) | 0.213 [0.17, 0.27] | 0.333 / 0.37 | 0.0 [0.0, 0.0] | no points |
| B7 same-minute bids | 9% (10/73, 38 buyers) | 4% (6135/125417, 119 buyers) | 1.861 [0.46, 3.75] | 1.019 / 2.24 | 9.0 [0.0, 19.1] | 3.5 points |
| B8 exact floor hit | 17% (15/71, 37 buyers) | 19% (23131/125027, 119 buyers) | 0.912 [0.47, 1.40] | 0.999 / 0.854 | 0.0 [0.0, 4.8] | no points |
| B9 shared CEO | 0% (1/72, 38 buyers) | 6% (2942/68379, 118 buyers) | 0.223 [0.18, 0.28] | 0.323 / 0.391 | 0.0 [0.0, 0.0] | no points |
| B10 rotation | 17% (6/43, 26 buyers) | 55% (12645/63441, 99 buyers) | 0.495 [0.33, 0.71] | 0.594 / 0.616 | 0.0 [0.0, 0.0] | no points |
| B11 repeated quote pair | 8% (1/24, 13 buyers) | 12% (2463/49810, 97 buyers) | 0.792 [0.37, 1.67] | 0.972 / 0.667 | 0.0 [0.0, 7.4] | no points |
| N6 short notice period | 40% (16/68, 34 buyers) | 52% (73229/281552, 127 buyers) | 0.811 [0.58, 1.04] | 0.794 / 0.912 | 0.0 [0.0, 0.5] | no points |
| N7 just below a threshold | 3% (2/75, 39 buyers) | 2% (6669/283202, 127 buyers) | 1.313 [0.19, 3.89] | 0.323 / 1.843 | 3.9 [0.0, 19.6] | no points |

### weighted, all linked tenders, all contracts (decision rule, amendment 2026-10-20): 721 labelled (139 buyers), 409522 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 29% (102/721, 139 buyers) | 65% (180399/409522, 133 buyers) | 0.483 [0.39, 0.58] | 0.463 / 0.581 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 38% (84/721, 139 buyers) | 19% (514/409522, 133 buyers) | 1.901 [1.55, 2.43] | 2.036 / 1.6 | 9.3 [6.3, 12.8] | 8.2 points |
| G4 concentration | 32% (66/659, 99 buyers) | 16% (12570/409134, 105 buyers) | 1.854 [1.47, 2.41] | 1.721 / 1.796 | 8.9 [5.6, 12.7] | 7.7 points |
| G5 3+ changes | 3% (21/679, 130 buyers) | 3% (16401/385595, 133 buyers) | 0.865 [0.20, 1.72] | 0.631 / 0.954 | 0.0 [0.0, 7.8] | no points |
| G6 amount increase > 20 % | 2% (21/679, 130 buyers) | 3% (26557/385587, 133 buyers) | 0.674 [0.21, 1.38] | 0.581 / 0.721 | 0.0 [0.0, 4.6] | no points |
| N1 December signature | 9% (80/721, 139 buyers) | 10% (48275/409522, 133 buyers) | 0.899 [0.53, 1.32] | 1.055 / 0.655 | 0.0 [0.0, 4.0] | no points |
| N2 weekend signature | 0% (7/721, 139 buyers) | 1% (2460/409522, 133 buyers) | 0.205 [0.07, 0.59] | 0.116 / 0.369 | 0.0 [0.0, 0.0] | no points |
| N4 supplier dependence >= 25 % | 35% (85/721, 139 buyers) | 22% (4873/409522, 133 buyers) | 1.563 [1.34, 1.87] | 1.642 / 1.356 | 6.4 [4.2, 9.0] | 5.6 points |
| N5 first-time supplier | 48% (141/550, 101 buyers) | 49% (82443/296398, 97 buyers) | 0.965 [0.84, 1.09] | 1.024 / 0.881 | 0.0 [0.0, 1.3] | no points |
| U2 repeated private contract | 15% (60/721, 139 buyers) | 29% (96289/409522, 133 buyers) | 0.558 [0.40, 0.70] | 0.544 / 0.633 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/721, 139 buyers) | 0% (2167/409522, 133 buyers) | 0.067 [0.07, 0.07] | 0.116 / 0.137 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (7/721, 139 buyers) | 2% (18626/409522, 133 buyers) | 0.286 [0.07, 0.71] | 0.415 / 0.143 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/721, 139 buyers) | 0% (348/409522, 133 buyers) | 0.067 [0.07, 0.07] | 0.116 / 0.137 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 1% (1/721, 139 buyers) | 1% (2242/409522, 133 buyers) | 0.485 [0.07, 1.50] | 0.116 / 0.894 | 0.0 [0.0, 5.8] | no points |
| K5 restricted competition | 37% (279/721, 139 buyers) | 26% (137859/409522, 133 buyers) | 1.391 [1.14, 1.70] | 1.394 / 1.32 | 4.8 [1.8, 7.6] | 3.7 points |
| K6 award >= 95 % of reserve | 67% (391/641, 119 buyers) | 26% (175613/309409, 129 buyers) | 2.389 [1.98, 2.90] | 2.195 / 2.371 | 12.6 [9.9, 15.3] | 11.6 points |
| B1 single bid | 1% (11/612, 122 buyers) | 5% (39761/125417, 119 buyers) | 0.333 [0.09, 0.73] | 0.427 / 0.264 | 0.0 [0.0, 0.0] | no points |
| B2 two or three bids | 59% (270/612, 122 buyers) | 22% (34159/125417, 119 buyers) | 2.476 [2.03, 3.07] | 2.197 / 2.565 | 13.1 [10.2, 16.2] | 12.1 points |
| B3 just above the lower limit | 7% (50/607, 122 buyers) | 42% (30668/125027, 119 buyers) | 0.236 [0.15, 0.34] | 0.31 / 0.271 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 14% (37/242, 55 buyers) | 10% (5337/50613, 112 buyers) | 1.32 [0.67, 2.16] | 1.764 / 0.816 | 4.0 [0.0, 11.1] | 1 points |
| B5 large first gap | 28% (55/242, 55 buyers) | 10% (6151/50613, 112 buyers) | 2.467 [1.48, 3.64] | 1.795 / 2.634 | 13.0 [5.7, 18.6] | 11 points |
| B6 better bids disqualified | 0% (1/607, 122 buyers) | 2% (2216/124868, 119 buyers) | 0.113 [0.07, 0.16] | 0.13 / 0.21 | 0.0 [0.0, 0.0] | no points |
| B7 same-minute bids | 6% (52/612, 122 buyers) | 4% (6135/125417, 119 buyers) | 1.454 [0.74, 2.43] | 1.302 / 1.342 | 5.4 [0.0, 12.8] | 2.2 points |
| B8 exact floor hit | 7% (44/607, 122 buyers) | 19% (23131/125027, 119 buyers) | 0.4 [0.23, 0.61] | 0.498 / 0.387 | 0.0 [0.0, 0.0] | no points |
| B9 shared CEO | 0% (6/604, 122 buyers) | 6% (2942/68379, 118 buyers) | 0.105 [0.07, 0.17] | 0.185 / 0.157 | 0.0 [0.0, 0.0] | no points |
| B10 rotation | 15% (128/380, 86 buyers) | 55% (12645/63441, 99 buyers) | 0.342 [0.23, 0.47] | 0.377 / 0.43 | 0.0 [0.0, 0.0] | no points |
| B11 repeated quote pair | 6% (7/158, 28 buyers) | 12% (2463/49810, 97 buyers) | 0.635 [0.31, 1.14] | 0.598 / 0.816 | 0.0 [0.0, 1.9] | no points |
| N6 short notice period | 44% (121/613, 123 buyers) | 52% (73229/281552, 127 buyers) | 0.85 [0.71, 0.99] | 0.723 / 1.012 | 0.0 [0.0, 0.0] | no points |
| N7 just below a threshold | 1% (13/624, 125 buyers) | 2% (6669/283202, 127 buyers) | 0.631 [0.12, 1.62] | 0.128 / 1.009 | 0.0 [0.0, 7.0] | no points |

### weighted, one per case, competitive tenders with a notice: 79 labelled (39 buyers), 175433 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 0% (0/79, 39 buyers) | 0% (0/175433, 116 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 26% (12/79, 39 buyers) | 17% (307/175433, 116 buyers) | 1.4 [0.76, 2.23] | 1.236 / 1.443 | 4.9 [0.0, 11.6] | 2 points |
| G4 concentration | 16% (7/72, 33 buyers) | 16% (4049/175297, 102 buyers) | 0.981 [0.46, 1.58] | 1.103 / 0.769 | 0.0 [0.0, 6.6] | no points |
| G5 3+ changes | 6% (3/68, 35 buyers) | 8% (11679/160898, 116 buyers) | 0.816 [0.24, 1.66] | 0.909 / 0.777 | 0.0 [0.0, 7.3] | no points |
| G6 amount increase > 20 % | 5% (3/68, 35 buyers) | 6% (17005/160893, 116 buyers) | 0.835 [0.24, 1.82] | 0.475 / 1.181 | 0.0 [0.0, 8.7] | no points |
| N1 December signature | 14% (14/79, 39 buyers) | 11% (20551/175433, 116 buyers) | 1.171 [0.54, 1.90] | 1.265 / 0.944 | 2.3 [0.0, 9.3] | no points |
| N2 weekend signature | 1% (2/79, 39 buyers) | 0% (1242/175433, 116 buyers) | 1.836 [0.20, 5.50] | 0.312 / 2.112 | 8.8 [0.0, 24.6] | no points |
| N4 supplier dependence >= 25 % | 17% (8/79, 39 buyers) | 18% (1603/175433, 116 buyers) | 0.913 [0.48, 1.49] | 0.967 / 0.833 | 0.0 [0.0, 5.7] | no points |
| N5 first-time supplier | 28% (12/58, 27 buyers) | 50% (51986/168881, 80 buyers) | 0.686 [0.47, 0.92] | 0.82 / 0.648 | 0.0 [0.0, 0.0] | no points |
| U2 repeated private contract | 0% (0/79, 39 buyers) | 0% (0/175433, 116 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/79, 39 buyers) | 0% (0/175433, 116 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/79, 39 buyers) | 0% (0/175433, 116 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/79, 39 buyers) | 0% (0/175433, 116 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 0% (0/79, 39 buyers) | 0% (0/175433, 116 buyers) | 0.204 [0.17, 0.26] | 0.312 / 0.37 | 0.0 [0.0, 0.0] | no points |
| K5 restricted competition | 54% (37/79, 39 buyers) | 82% (111778/175433, 116 buyers) | 0.723 [0.58, 0.85] | 0.731 / 0.821 | 0.0 [0.0, 0.0] | no points |
| K6 award >= 95 % of reserve | 65% (41/60, 30 buyers) | 19% (30996/105033, 116 buyers) | 2.755 [2.01, 3.67] | 2.313 / 2.455 | 14.6 [10.1, 18.8] | 13.1 points |
| B1 single bid | 5% (2/77, 38 buyers) | 1% (2545/70392, 110 buyers) | 3.584 [0.20, 6.87] | 2.194 / 2.65 | 18.4 [0.0, 27.8] | 10.9 points |
| B2 two or three bids | 62% (54/77, 38 buyers) | 22% (28737/70392, 110 buyers) | 2.353 [1.80, 3.00] | 2.221 / 1.922 | 12.3 [8.5, 15.8] | 11 points |
| B3 just above the lower limit | 20% (16/75, 37 buyers) | 46% (23894/70075, 110 buyers) | 0.556 [0.37, 0.79] | 0.58 / 0.696 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 10% (3/23, 17 buyers) | 8% (4053/38901, 105 buyers) | 1.155 [0.40, 2.26] | 1.515 / 0.679 | 2.1 [0.0, 11.8] | no points |
| B5 large first gap | 37% (7/23, 17 buyers) | 9% (4928/38901, 105 buyers) | 2.959 [1.27, 5.01] | 2.543 / 2.171 | 15.6 [3.5, 23.3] | 12 points |
| B6 better bids disqualified | 0% (0/75, 37 buyers) | 2% (2209/69982, 110 buyers) | 0.213 [0.17, 0.27] | 0.323 / 0.385 | 0.0 [0.0, 0.0] | no points |
| B7 same-minute bids | 10% (11/77, 38 buyers) | 4% (5093/70392, 110 buyers) | 1.923 [0.68, 3.67] | 0.892 / 2.662 | 9.4 [0.0, 18.7] | 4.7 points |
| B8 exact floor hit | 20% (16/75, 37 buyers) | 26% (20173/70075, 110 buyers) | 0.827 [0.48, 1.25] | 0.808 / 0.908 | 0.0 [0.0, 3.2] | no points |
| B9 shared CEO | 0% (1/76, 38 buyers) | 11% (2467/38627, 107 buyers) | 0.215 [0.18, 0.27] | 0.312 / 0.395 | 0.0 [0.0, 0.0] | no points |
| B10 rotation | 16% (6/46, 27 buyers) | 53% (8711/36565, 96 buyers) | 0.491 [0.32, 0.70] | 0.574 / 0.625 | 0.0 [0.0, 0.0] | no points |
| B11 repeated quote pair | 7% (1/25, 14 buyers) | 11% (1804/25451, 93 buyers) | 0.787 [0.36, 1.73] | 0.957 / 0.625 | 0.0 [0.0, 7.9] | no points |
| N6 short notice period | 38% (16/72, 35 buyers) | 35% (7860/173929, 116 buyers) | 1.071 [0.75, 1.41] | 1.111 / 1.008 | 1.0 [0.0, 5.0] | no points |
| N7 just below a threshold | 3% (2/79, 39 buyers) | 2% (4412/175036, 116 buyers) | 0.926 [0.19, 2.59] | 0.312 / 1.338 | 0.0 [0.0, 13.7] | no points |

### unweighted (court outcome ignored), one per case, all contracts: 102 labelled (50 buyers), 409522 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 14% (8/102, 50 buyers) | 65% (180399/409522, 133 buyers) | 0.35 [0.23, 0.48] | 0.395 / 0.497 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 32% (18/102, 50 buyers) | 19% (514/409522, 133 buyers) | 1.551 [1.00, 2.37] | 1.43 / 1.488 | 6.3 [0.0, 12.4] | 4.2 points |
| G4 concentration | 15% (8/92, 41 buyers) | 16% (12570/409134, 105 buyers) | 0.949 [0.51, 1.47] | 0.966 / 0.909 | 0.0 [0.0, 5.5] | no points |
| G5 3+ changes | 7% (4/84, 41 buyers) | 3% (16401/385595, 133 buyers) | 1.861 [0.35, 3.91] | 1.589 / 1.598 | 9.0 [0.0, 19.7] | 2.6 points |
| G6 amount increase > 20 % | 7% (4/84, 41 buyers) | 3% (26557/385587, 133 buyers) | 1.621 [0.33, 3.28] | 0.507 / 2.304 | 7.0 [0.0, 17.2] | 0.6 points |
| N1 December signature | 12% (17/102, 50 buyers) | 10% (48275/409522, 133 buyers) | 1.204 [0.52, 1.97] | 1.402 / 0.836 | 2.7 [0.0, 9.7] | no points |
| N2 weekend signature | 1% (1/102, 50 buyers) | 1% (2460/409522, 133 buyers) | 0.948 [0.15, 3.22] | 0.27 / 1.467 | 0.0 [0.0, 16.9] | no points |
| N4 supplier dependence >= 25 % | 21% (12/102, 50 buyers) | 22% (4873/409522, 133 buyers) | 0.969 [0.59, 1.47] | 1.052 / 0.867 | 0.0 [0.0, 5.5] | no points |
| N5 first-time supplier | 38% (16/58, 31 buyers) | 49% (82443/296398, 97 buyers) | 0.818 [0.58, 1.08] | 0.927 / 0.752 | 0.0 [0.0, 1.2] | no points |
| U2 repeated private contract | 6% (3/102, 50 buyers) | 29% (96289/409522, 133 buyers) | 0.339 [0.17, 0.55] | 0.359 / 0.522 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/102, 50 buyers) | 0% (2167/409522, 133 buyers) | 0.167 [0.14, 0.20] | 0.27 / 0.303 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/102, 50 buyers) | 2% (18626/409522, 133 buyers) | 0.167 [0.14, 0.20] | 0.27 / 0.303 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/102, 50 buyers) | 0% (348/409522, 133 buyers) | 0.167 [0.14, 0.20] | 0.27 / 0.303 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 2% (1/102, 50 buyers) | 1% (2242/409522, 133 buyers) | 1.205 [0.15, 3.60] | 0.27 / 1.978 | 2.7 [0.0, 18.5] | no points |
| K5 restricted competition | 45% (45/102, 50 buyers) | 26% (137859/409522, 133 buyers) | 1.615 [1.17, 2.10] | 1.411 / 1.633 | 6.9 [2.3, 10.7] | 5.5 points |
| K6 award >= 95 % of reserve | 64% (49/73, 33 buyers) | 26% (175613/309409, 129 buyers) | 2.072 [1.57, 2.62] | 1.867 / 1.85 | 10.5 [6.5, 13.9] | 9.2 points |
| B1 single bid | 5% (2/73, 38 buyers) | 5% (39761/125417, 119 buyers) | 1.012 [0.19, 2.35] | 0.849 / 1.127 | 0.2 [0.0, 12.3] | no points |
| B2 two or three bids | 60% (52/73, 38 buyers) | 22% (34159/125417, 119 buyers) | 2.326 [1.76, 3.00] | 2.032 / 2.146 | 12.2 [8.1, 15.9] | 10.9 points |
| B3 just above the lower limit | 17% (15/71, 37 buyers) | 42% (30668/125027, 119 buyers) | 0.54 [0.33, 0.77] | 0.629 / 0.613 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 12% (3/20, 16 buyers) | 10% (5337/50613, 112 buyers) | 1.067 [0.43, 2.01] | 1.47 / 0.704 | 0.9 [0.0, 10.1] | no points |
| B5 large first gap | 38% (6/20, 16 buyers) | 10% (6151/50613, 112 buyers) | 2.654 [1.17, 4.50] | 2.219 / 2.061 | 14.1 [2.3, 21.7] | 10.7 points |
| B6 better bids disqualified | 0% (0/71, 37 buyers) | 2% (2216/124868, 119 buyers) | 0.213 [0.17, 0.27] | 0.333 / 0.37 | 0.0 [0.0, 0.0] | no points |
| B7 same-minute bids | 9% (10/73, 38 buyers) | 4% (6135/125417, 119 buyers) | 1.861 [0.46, 3.75] | 1.019 / 2.24 | 9.0 [0.0, 19.1] | 3.5 points |
| B8 exact floor hit | 17% (15/71, 37 buyers) | 19% (23131/125027, 119 buyers) | 0.912 [0.47, 1.40] | 0.999 / 0.854 | 0.0 [0.0, 4.8] | no points |
| B9 shared CEO | 0% (1/72, 38 buyers) | 6% (2942/68379, 118 buyers) | 0.223 [0.18, 0.28] | 0.323 / 0.391 | 0.0 [0.0, 0.0] | no points |
| B10 rotation | 17% (6/43, 26 buyers) | 55% (12645/63441, 99 buyers) | 0.495 [0.33, 0.71] | 0.594 / 0.616 | 0.0 [0.0, 0.0] | no points |
| B11 repeated quote pair | 8% (1/24, 13 buyers) | 12% (2463/49810, 97 buyers) | 0.792 [0.37, 1.67] | 0.972 / 0.667 | 0.0 [0.0, 7.4] | no points |
| N6 short notice period | 40% (16/68, 34 buyers) | 52% (73229/281552, 127 buyers) | 0.811 [0.58, 1.04] | 0.794 / 0.912 | 0.0 [0.0, 0.5] | no points |
| N7 just below a threshold | 3% (2/75, 39 buyers) | 2% (6669/283202, 127 buyers) | 1.313 [0.19, 3.89] | 0.323 / 1.843 | 3.9 [0.0, 19.6] | no points |

## Buyer = demanding body (sensitivity)

    740 linked notices in 106 cases; 738 with a contract in the data; 416 buyer-years (demand_code); 207486 contracts
    finality: {'none': 716, 'upheld': 22} 

### weighted, one per case, all contracts (decision basis until 2026-10-20): 104 labelled (76 buyers), 204999 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 9% (8/104, 76 buyers) | 63% (113995/204999, 269 buyers) | 0.248 [0.16, 0.34] | 0.268 / 0.406 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 32% (28/104, 76 buyers) | 15% (1122/204999, 269 buyers) | 1.921 [1.32, 2.61] | 2.152 / 1.369 | 9.4 [4.0, 13.9] | 7.5 points |
| G4 concentration | 10% (8/90, 63 buyers) | 14% (21456/204161, 230 buyers) | 0.763 [0.35, 1.21] | 0.831 / 0.734 | 0.0 [0.0, 2.8] | no points |
| G5 3+ changes | 4% (4/85, 68 buyers) | 3% (15527/196856, 269 buyers) | 1.302 [0.22, 2.81] | 0.976 / 1.46 | 3.8 [0.0, 14.9] | no points |
| G6 amount increase > 20 % | 2% (4/85, 68 buyers) | 3% (22183/196848, 269 buyers) | 0.812 [0.13, 1.87] | 0.2 / 1.39 | 0.0 [0.0, 9.0] | no points |
| N1 December signature | 18% (18/104, 76 buyers) | 12% (23703/204999, 269 buyers) | 1.469 [0.88, 2.13] | 1.941 / 0.72 | 5.6 [0.0, 10.9] | 3.2 points |
| N2 weekend signature | 1% (1/104, 76 buyers) | 1% (1467/204999, 269 buyers) | 1.671 [0.10, 5.29] | 2.025 / 0.244 | 7.4 [0.0, 24.0] | no points |
| N4 supplier dependence >= 25 % | 16% (14/104, 76 buyers) | 15% (5596/204999, 269 buyers) | 0.996 [0.57, 1.53] | 1.237 / 0.714 | 0.0 [0.0, 6.1] | no points |
| N5 first-time supplier | 47% (25/54, 45 buyers) | 49% (46580/151144, 189 buyers) | 0.97 [0.74, 1.21] | 0.992 / 0.943 | 0.0 [0.0, 2.8] | no points |
| U2 repeated private contract | 4% (3/104, 76 buyers) | 26% (57451/204999, 269 buyers) | 0.252 [0.12, 0.42] | 0.251 / 0.436 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/104, 76 buyers) | 0% (36/204999, 269 buyers) | 0.116 [0.10, 0.14] | 0.182 / 0.244 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/104, 76 buyers) | 2% (3024/204999, 269 buyers) | 0.116 [0.10, 0.14] | 0.182 / 0.244 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/104, 76 buyers) | 0% (477/204999, 269 buyers) | 0.116 [0.10, 0.14] | 0.182 / 0.244 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 1% (1/104, 76 buyers) | 1% (3638/204999, 269 buyers) | 0.981 [0.10, 3.02] | 0.182 / 2.066 | 0.0 [0.0, 15.9] | no points |
| K5 restricted competition | 46% (45/104, 76 buyers) | 26% (54321/204999, 269 buyers) | 1.654 [1.27, 2.06] | 1.777 / 1.346 | 7.3 [3.4, 10.4] | 6.1 points |
| K6 award >= 95 % of reserve | 67% (48/72, 57 buyers) | 30% (35356/107181, 264 buyers) | 2.046 [1.69, 2.45] | 2.147 / 1.641 | 10.3 [7.6, 12.9] | 9.4 points |
| B1 single bid | 4% (2/75, 56 buyers) | 8% (5400/41291, 249 buyers) | 0.528 [0.14, 1.11] | 0.507 / 0.686 | 0.0 [0.0, 1.5] | no points |
| B2 two or three bids | 70% (53/75, 56 buyers) | 24% (7070/41291, 249 buyers) | 2.596 [2.15, 3.05] | 2.33 / 2.443 | 13.8 [11.0, 16.1] | 12.8 points |
| B3 just above the lower limit | 21% (18/73, 54 buyers) | 42% (16562/40719, 248 buyers) | 0.575 [0.38, 0.79] | 0.566 / 0.72 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 15% (3/19, 16 buyers) | 10% (2645/27398, 233 buyers) | 1.261 [0.43, 2.40] | 1.472 / 0.86 | 3.3 [0.0, 12.7] | no points |
| B5 large first gap | 38% (6/19, 16 buyers) | 10% (2554/27398, 233 buyers) | 2.634 [1.19, 4.16] | 2.021 / 2.362 | 14.0 [2.5, 20.6] | 10.5 points |
| B6 better bids disqualified | 0% (0/73, 54 buyers) | 2% (939/40708, 248 buyers) | 0.156 [0.13, 0.20] | 0.238 / 0.312 | 0.0 [0.0, 0.0] | no points |
| B7 same-minute bids | 15% (13/75, 56 buyers) | 6% (1703/41291, 249 buyers) | 2.325 [1.20, 3.69] | 1.81 / 2.45 | 12.2 [2.6, 18.8] | 9.1 points |
| B8 exact floor hit | 21% (18/73, 54 buyers) | 23% (7984/40719, 248 buyers) | 0.937 [0.56, 1.35] | 0.863 / 1.046 | 0.0 [0.0, 4.3] | no points |
| B9 shared CEO | 2% (1/74, 55 buyers) | 7% (2219/25327, 245 buyers) | 0.357 [0.14, 0.86] | 0.538 / 0.303 | 0.0 [0.0, 0.0] | no points |
| B10 rotation | 12% (6/47, 35 buyers) | 50% (14804/25003, 211 buyers) | 0.415 [0.26, 0.60] | 0.518 / 0.525 | 0.0 [0.0, 0.0] | no points |
| B11 repeated quote pair | 5% (1/28, 19 buyers) | 10% (1798/19488, 205 buyers) | 0.672 [0.29, 1.43] | 0.959 / 0.556 | 0.0 [0.0, 5.2] | no points |
| N6 short notice period | 25% (16/70, 54 buyers) | 46% (46298/125722, 259 buyers) | 0.607 [0.41, 0.80] | 0.6 / 0.738 | 0.0 [0.0, 0.0] | no points |
| N7 just below a threshold | 4% (2/77, 56 buyers) | 2% (2728/128099, 259 buyers) | 1.667 [0.14, 3.99] | 0.233 / 2.945 | 7.4 [0.0, 20.0] | no points |

### weighted, all linked tenders, all contracts (decision rule, amendment 2026-10-20): 738 labelled (275 buyers), 204999 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 26% (105/738, 275 buyers) | 63% (113995/204999, 269 buyers) | 0.431 [0.35, 0.51] | 0.436 / 0.469 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 27% (146/738, 275 buyers) | 15% (1122/204999, 269 buyers) | 1.722 [1.42, 2.08] | 1.956 / 1.37 | 7.8 [5.0, 10.6] | 6.9 points |
| G4 concentration | 12% (63/645, 214 buyers) | 14% (21456/204161, 230 buyers) | 0.904 [0.65, 1.16] | 1.0 / 0.789 | 0.0 [0.0, 2.1] | no points |
| G5 3+ changes | 2% (21/695, 267 buyers) | 3% (15527/196856, 269 buyers) | 0.623 [0.20, 1.18] | 0.585 / 0.619 | 0.0 [0.0, 2.3] | no points |
| G6 amount increase > 20 % | 2% (21/695, 267 buyers) | 3% (22183/196848, 269 buyers) | 0.513 [0.20, 0.96] | 0.292 / 0.689 | 0.0 [0.0, 0.0] | no points |
| N1 December signature | 10% (81/738, 275 buyers) | 12% (23703/204999, 269 buyers) | 0.883 [0.63, 1.14] | 1.108 / 0.613 | 0.0 [0.0, 1.8] | no points |
| N2 weekend signature | 1% (7/738, 275 buyers) | 1% (1467/204999, 269 buyers) | 1.254 [0.20, 2.85] | 1.273 / 0.672 | 3.3 [0.0, 15.1] | no points |
| N4 supplier dependence >= 25 % | 19% (90/738, 275 buyers) | 15% (5596/204999, 269 buyers) | 1.201 [0.98, 1.48] | 1.404 / 0.961 | 2.6 [0.0, 5.6] | 1.6 points |
| N5 first-time supplier | 55% (219/551, 194 buyers) | 49% (46580/151144, 189 buyers) | 1.109 [1.00, 1.22] | 1.092 / 1.118 | 1.5 [0.0, 2.8] | 0.9 points |
| U2 repeated private contract | 7% (36/738, 275 buyers) | 26% (57451/204999, 269 buyers) | 0.308 [0.21, 0.41] | 0.312 / 0.353 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/738, 275 buyers) | 0% (36/204999, 269 buyers) | 0.035 [0.04, 0.04] | 0.062 / 0.074 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 2% (7/738, 275 buyers) | 2% (3024/204999, 269 buyers) | 0.911 [0.28, 1.72] | 0.921 / 0.754 | 0.0 [0.0, 7.8] | no points |
| K3 just under small-value limit | 0% (0/738, 275 buyers) | 0% (477/204999, 269 buyers) | 0.035 [0.04, 0.04] | 0.062 / 0.074 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 0% (1/738, 275 buyers) | 1% (3638/204999, 269 buyers) | 0.296 [0.04, 0.92] | 0.062 / 0.627 | 0.0 [0.0, 0.0] | no points |
| K5 restricted competition | 38% (280/738, 275 buyers) | 26% (54321/204999, 269 buyers) | 1.413 [1.20, 1.64] | 1.569 / 1.205 | 5.0 [2.6, 7.1] | 4.3 points |
| K6 award >= 95 % of reserve | 66% (392/643, 233 buyers) | 30% (35356/107181, 264 buyers) | 2.14 [1.89, 2.42] | 2.166 / 2.009 | 11.0 [9.2, 12.7] | 10.3 points |
| B1 single bid | 4% (11/627, 223 buyers) | 8% (5400/41291, 249 buyers) | 0.505 [0.23, 0.85] | 0.501 / 0.536 | 0.0 [0.0, 0.0] | no points |
| B2 two or three bids | 58% (283/627, 223 buyers) | 24% (7070/41291, 249 buyers) | 2.336 [2.03, 2.67] | 2.123 / 2.433 | 12.2 [10.2, 14.2] | 11.4 points |
| B3 just above the lower limit | 16% (65/622, 223 buyers) | 42% (16562/40719, 248 buyers) | 0.405 [0.31, 0.52] | 0.37 / 0.5 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 11% (37/246, 99 buyers) | 10% (2645/27398, 233 buyers) | 1.082 [0.64, 1.65] | 1.189 / 0.926 | 1.1 [0.0, 7.2] | no points |
| B5 large first gap | 23% (55/246, 99 buyers) | 10% (2554/27398, 233 buyers) | 2.157 [1.44, 3.05] | 1.649 / 2.539 | 11.1 [5.3, 16.1] | 9.3 points |
| B6 better bids disqualified | 0% (1/622, 223 buyers) | 2% (939/40708, 248 buyers) | 0.067 [0.04, 0.11] | 0.077 / 0.135 | 0.0 [0.0, 0.0] | no points |
| B7 same-minute bids | 14% (67/627, 223 buyers) | 6% (1703/41291, 249 buyers) | 2.36 [1.72, 3.23] | 2.133 / 2.351 | 12.4 [7.8, 16.9] | 10.9 points |
| B8 exact floor hit | 16% (59/622, 223 buyers) | 23% (7984/40719, 248 buyers) | 0.708 [0.52, 0.90] | 0.618 / 0.83 | 0.0 [0.0, 0.0] | no points |
| B9 shared CEO | 1% (6/619, 222 buyers) | 7% (2219/25327, 245 buyers) | 0.171 [0.04, 0.36] | 0.2 / 0.206 | 0.0 [0.0, 0.0] | no points |
| B10 rotation | 11% (128/395, 150 buyers) | 50% (14804/25003, 211 buyers) | 0.269 [0.19, 0.36] | 0.309 / 0.315 | 0.0 [0.0, 0.0] | no points |
| B11 repeated quote pair | 7% (7/173, 62 buyers) | 10% (1798/19488, 205 buyers) | 0.703 [0.28, 1.23] | 0.919 / 0.549 | 0.0 [0.0, 3.0] | no points |
| N6 short notice period | 27% (121/628, 223 buyers) | 46% (46298/125722, 259 buyers) | 0.599 [0.49, 0.70] | 0.53 / 0.712 | 0.0 [0.0, 0.0] | no points |
| N7 just below a threshold | 1% (13/639, 225 buyers) | 2% (2728/128099, 259 buyers) | 0.553 [0.16, 1.10] | 0.175 / 0.902 | 0.0 [0.0, 1.4] | no points |

### weighted, one per case, competitive tenders with a notice: 80 labelled (59 buyers), 82313 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 0% (0/80, 59 buyers) | 0% (0/82313, 248 buyers) | 0.145 [0.12, 0.17] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 23% (17/80, 59 buyers) | 14% (621/82313, 248 buyers) | 1.581 [0.94, 2.37] | 1.891 / 0.643 | 6.6 [0.0, 12.4] | 4.3 points |
| G4 concentration | 11% (7/69, 49 buyers) | 11% (5828/81887, 224 buyers) | 0.942 [0.40, 1.58] | 1.094 / 0.732 | 0.0 [0.0, 6.6] | no points |
| G5 3+ changes | 4% (3/69, 55 buyers) | 8% (12179/77902, 248 buyers) | 0.587 [0.16, 1.16] | 0.538 / 0.762 | 0.0 [0.0, 2.2] | no points |
| G6 amount increase > 20 % | 2% (3/69, 55 buyers) | 5% (16544/77900, 248 buyers) | 0.58 [0.14, 1.37] | 0.227 / 1.09 | 0.0 [0.0, 4.6] | no points |
| N1 December signature | 18% (15/80, 59 buyers) | 12% (8619/82313, 248 buyers) | 1.421 [0.78, 2.11] | 1.738 / 0.878 | 5.1 [0.0, 10.8] | 2.5 points |
| N2 weekend signature | 3% (2/80, 59 buyers) | 0% (820/82313, 248 buyers) | 5.491 [0.14, 14.91] | 5.661 / 0.312 | 24.6 [0.0, 39.0] | 14.9 points |
| N4 supplier dependence >= 25 % | 15% (11/80, 59 buyers) | 12% (1842/82313, 248 buyers) | 1.206 [0.62, 1.87] | 1.534 / 0.634 | 2.7 [0.0, 9.0] | no points |
| N5 first-time supplier | 41% (22/53, 44 buyers) | 55% (23429/70738, 171 buyers) | 0.795 [0.60, 1.00] | 0.824 / 0.828 | 0.0 [0.0, 0.0] | no points |
| U2 repeated private contract | 0% (0/80, 59 buyers) | 0% (0/82313, 248 buyers) | 0.145 [0.12, 0.18] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/80, 59 buyers) | 0% (0/82313, 248 buyers) | 0.145 [0.12, 0.18] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/80, 59 buyers) | 0% (0/82313, 248 buyers) | 0.145 [0.12, 0.18] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/80, 59 buyers) | 0% (0/82313, 248 buyers) | 0.145 [0.12, 0.18] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 0% (0/80, 59 buyers) | 0% (0/82313, 248 buyers) | 0.145 [0.12, 0.18] | 0.213 / 0.312 | 0.0 [0.0, 0.0] | no points |
| K5 restricted competition | 48% (37/80, 59 buyers) | 78% (51276/82313, 248 buyers) | 0.675 [0.54, 0.80] | 0.763 / 0.652 | 0.0 [0.0, 0.0] | no points |
| K6 award >= 95 % of reserve | 72% (41/58, 46 buyers) | 20% (12080/43552, 240 buyers) | 3.067 [2.46, 3.74] | 3.298 / 1.997 | 16.2 [13.0, 19.0] | 15.1 points |
| B1 single bid | 3% (2/78, 59 buyers) | 2% (241/20206, 238 buyers) | 1.606 [0.14, 4.20] | 1.059 / 2.045 | 6.8 [0.0, 20.7] | no points |
| B2 two or three bids | 70% (55/78, 59 buyers) | 27% (4641/20206, 238 buyers) | 2.328 [1.92, 2.79] | 2.161 / 2.162 | 12.2 [9.4, 14.8] | 11.3 points |
| B3 just above the lower limit | 22% (19/76, 57 buyers) | 45% (8243/19852, 238 buyers) | 0.561 [0.38, 0.78] | 0.496 / 0.803 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 13% (3/21, 18 buyers) | 8% (1249/14947, 222 buyers) | 1.362 [0.40, 2.71] | 1.509 / 0.874 | 4.5 [0.0, 14.4] | no points |
| B5 large first gap | 33% (6/21, 18 buyers) | 8% (1150/14947, 222 buyers) | 2.883 [1.20, 4.80] | 2.173 / 2.595 | 15.3 [2.6, 22.6] | 11.6 points |
| B6 better bids disqualified | 0% (0/76, 57 buyers) | 3% (934/19849, 238 buyers) | 0.149 [0.12, 0.18] | 0.217 / 0.323 | 0.0 [0.0, 0.0] | no points |
| B7 same-minute bids | 16% (14/78, 59 buyers) | 7% (1147/20206, 238 buyers) | 2.203 [1.14, 3.44] | 1.44 / 2.831 | 11.4 [1.9, 17.8] | 8.5 points |
| B8 exact floor hit | 22% (19/76, 57 buyers) | 29% (5089/19852, 238 buyers) | 0.787 [0.49, 1.10] | 0.653 / 1.056 | 0.0 [0.0, 1.3] | no points |
| B9 shared CEO | 2% (1/77, 58 buyers) | 13% (1662/12780, 233 buyers) | 0.262 [0.13, 0.56] | 0.383 / 0.312 | 0.0 [0.0, 0.0] | no points |
| B10 rotation | 12% (6/49, 37 buyers) | 49% (6968/12009, 204 buyers) | 0.401 [0.26, 0.57] | 0.472 / 0.543 | 0.0 [0.0, 0.0] | no points |
| B11 repeated quote pair | 5% (1/29, 20 buyers) | 9% (700/9405, 197 buyers) | 0.706 [0.28, 1.56] | 1.061 / 0.526 | 0.0 [0.0, 6.4] | no points |
| N6 short notice period | 24% (16/73, 57 buyers) | 28% (11223/80101, 248 buyers) | 0.856 [0.56, 1.18] | 0.858 / 0.905 | 0.0 [0.0, 2.3] | no points |
| N7 just below a threshold | 3% (2/80, 59 buyers) | 3% (2184/81980, 248 buyers) | 1.186 [0.14, 2.73] | 0.213 / 2.296 | 2.5 [0.0, 14.5] | no points |

### unweighted (court outcome ignored), one per case, all contracts: 104 labelled (76 buyers), 204999 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| G2 private contract | 9% (8/104, 76 buyers) | 63% (113995/204999, 269 buyers) | 0.248 [0.16, 0.34] | 0.268 / 0.406 | 0.0 [0.0, 0.0] | no points |
| G3 buyer share >= 5 % | 32% (28/104, 76 buyers) | 15% (1122/204999, 269 buyers) | 1.921 [1.32, 2.61] | 2.152 / 1.369 | 9.4 [4.0, 13.9] | 7.5 points |
| G4 concentration | 10% (8/90, 63 buyers) | 14% (21456/204161, 230 buyers) | 0.763 [0.35, 1.21] | 0.831 / 0.734 | 0.0 [0.0, 2.8] | no points |
| G5 3+ changes | 4% (4/85, 68 buyers) | 3% (15527/196856, 269 buyers) | 1.302 [0.22, 2.81] | 0.976 / 1.46 | 3.8 [0.0, 14.9] | no points |
| G6 amount increase > 20 % | 2% (4/85, 68 buyers) | 3% (22183/196848, 269 buyers) | 0.812 [0.13, 1.87] | 0.2 / 1.39 | 0.0 [0.0, 9.0] | no points |
| N1 December signature | 18% (18/104, 76 buyers) | 12% (23703/204999, 269 buyers) | 1.469 [0.88, 2.13] | 1.941 / 0.72 | 5.6 [0.0, 10.9] | 3.2 points |
| N2 weekend signature | 1% (1/104, 76 buyers) | 1% (1467/204999, 269 buyers) | 1.671 [0.10, 5.29] | 2.025 / 0.244 | 7.4 [0.0, 24.0] | no points |
| N4 supplier dependence >= 25 % | 16% (14/104, 76 buyers) | 15% (5596/204999, 269 buyers) | 0.996 [0.57, 1.53] | 1.237 / 0.714 | 0.0 [0.0, 6.1] | no points |
| N5 first-time supplier | 47% (25/54, 45 buyers) | 49% (46580/151144, 189 buyers) | 0.97 [0.74, 1.21] | 0.992 / 0.943 | 0.0 [0.0, 2.8] | no points |
| U2 repeated private contract | 4% (3/104, 76 buyers) | 26% (57451/204999, 269 buyers) | 0.252 [0.12, 0.42] | 0.251 / 0.436 | 0.0 [0.0, 0.0] | no points |
| K1 single-bidder private contract | 0% (0/104, 76 buyers) | 0% (36/204999, 269 buyers) | 0.116 [0.10, 0.14] | 0.182 / 0.244 | 0.0 [0.0, 0.0] | no points |
| K2 re-tender private contract | 0% (0/104, 76 buyers) | 2% (3024/204999, 269 buyers) | 0.116 [0.10, 0.14] | 0.182 / 0.244 | 0.0 [0.0, 0.0] | no points |
| K3 just under small-value limit | 0% (0/104, 76 buyers) | 0% (477/204999, 269 buyers) | 0.116 [0.10, 0.14] | 0.182 / 0.244 | 0.0 [0.0, 0.0] | no points |
| K4 split contracts | 1% (1/104, 76 buyers) | 1% (3638/204999, 269 buyers) | 0.981 [0.10, 3.02] | 0.182 / 2.066 | 0.0 [0.0, 15.9] | no points |
| K5 restricted competition | 46% (45/104, 76 buyers) | 26% (54321/204999, 269 buyers) | 1.654 [1.27, 2.06] | 1.777 / 1.346 | 7.3 [3.4, 10.4] | 6.1 points |
| K6 award >= 95 % of reserve | 67% (48/72, 57 buyers) | 30% (35356/107181, 264 buyers) | 2.046 [1.69, 2.45] | 2.147 / 1.641 | 10.3 [7.6, 12.9] | 9.4 points |
| B1 single bid | 4% (2/75, 56 buyers) | 8% (5400/41291, 249 buyers) | 0.528 [0.14, 1.11] | 0.507 / 0.686 | 0.0 [0.0, 1.5] | no points |
| B2 two or three bids | 70% (53/75, 56 buyers) | 24% (7070/41291, 249 buyers) | 2.596 [2.15, 3.05] | 2.33 / 2.443 | 13.8 [11.0, 16.1] | 12.8 points |
| B3 just above the lower limit | 21% (18/73, 54 buyers) | 42% (16562/40719, 248 buyers) | 0.575 [0.38, 0.79] | 0.566 / 0.72 | 0.0 [0.0, 0.0] | no points |
| B4 low bid dispersion | 15% (3/19, 16 buyers) | 10% (2645/27398, 233 buyers) | 1.261 [0.43, 2.40] | 1.472 / 0.86 | 3.3 [0.0, 12.7] | no points |
| B5 large first gap | 38% (6/19, 16 buyers) | 10% (2554/27398, 233 buyers) | 2.634 [1.19, 4.16] | 2.021 / 2.362 | 14.0 [2.5, 20.6] | 10.5 points |
| B6 better bids disqualified | 0% (0/73, 54 buyers) | 2% (939/40708, 248 buyers) | 0.156 [0.13, 0.20] | 0.238 / 0.312 | 0.0 [0.0, 0.0] | no points |
| B7 same-minute bids | 15% (13/75, 56 buyers) | 6% (1703/41291, 249 buyers) | 2.325 [1.20, 3.69] | 1.81 / 2.45 | 12.2 [2.6, 18.8] | 9.1 points |
| B8 exact floor hit | 21% (18/73, 54 buyers) | 23% (7984/40719, 248 buyers) | 0.937 [0.56, 1.35] | 0.863 / 1.046 | 0.0 [0.0, 4.3] | no points |
| B9 shared CEO | 2% (1/74, 55 buyers) | 7% (2219/25327, 245 buyers) | 0.357 [0.14, 0.86] | 0.538 / 0.303 | 0.0 [0.0, 0.0] | no points |
| B10 rotation | 12% (6/47, 35 buyers) | 50% (14804/25003, 211 buyers) | 0.415 [0.26, 0.60] | 0.518 / 0.525 | 0.0 [0.0, 0.0] | no points |
| B11 repeated quote pair | 5% (1/28, 19 buyers) | 10% (1798/19488, 205 buyers) | 0.672 [0.29, 1.43] | 0.959 / 0.556 | 0.0 [0.0, 5.2] | no points |
| N6 short notice period | 25% (16/70, 54 buyers) | 46% (46298/125722, 259 buyers) | 0.607 [0.41, 0.80] | 0.6 / 0.738 | 0.0 [0.0, 0.0] | no points |
| N7 just below a threshold | 4% (2/77, 56 buyers) | 2% (2728/128099, 259 buyers) | 1.667 [0.14, 3.99] | 0.233 / 2.945 | 7.4 [0.0, 20.0] | no points |

## Round-number checks A1–A6 (2026-10-24, plan "Round-number checks"; research, no points adopted)

`korea-label-checks.py` (letters appended after N7; budgets from `tools/korea-notice-budgets.py`, 3.53 M notices).
Collusion family, contracting office:

| Check | One per case | All linked tenders |
|---|---|---|
| A1 round-percentage increase | 2 % (1/84) vs 0.1 %, no points | 1 % (6/679) vs 0.1 %, no points |
| A2 same step repeated | 2/84 vs 0.04 %, 7.8 points (learn 1.5 / check 6.9) | 3/679, no points |
| A3 round amount, 1 digit | 0 % vs 2 % | 1 % vs 2 % |
| A4 round amount, 2 digits | 7 % vs 6 % | 5 % vs 6 % |
| A5 round budget, 1 digit | 7 % (3/56) vs 6 % | 29 % (50/569) vs 6 %, 18.6 points |
| A6 round budget, 2 digits | 0 % vs 9 % | 4 % vs 9 % |

Reading: rigged tenders do not have round amounts (A3/A4: competitive bids rarely land on round numbers). A5's
all-linked result is two cases: 28 of its 50 hits are 2017카총1272 (28 schools, school-helper robots, budget exactly
40,000,000 each) and 14 are 2022입담1177 (hospital drug tenders with a placeholder budget of 10 KRW). One per case shows
nothing, so A5 is not a signal on these labels; budgets below 1M KRW should be unknown (placeholder). A2 rests on 2
tenders. Court labels: no hits on any A check (≤ 13 cases). Round price increases (A1/A2) are too rare among KONEPS
labels to rate; the audit family (inflated changes are a common audit finding) is where they can be tested.

## Ukraine's checks on Korean labels (2026-10-24, owner: every check in every country; research, no points adopted)

Same rules as `ukraine-candidate-indicators-plan.md` where Korean data allow (`UA-` letters in
`korea-label-checks.py`). Already covered by Korean letters: C3 = B6, C7 = N1, C10 ≈ N7, C4 ≈ N6, R1 = G3, R3 = K3,
K4 ≈ B7. No data: C5, C6, C8, C14, K1–K3, K7, K8, young winner; C12 term extension (the `period` field is empty in about
97 % of contract versions). Collusion family, contracting office (one per case / all linked tenders):

| Check | Rigged | Comparisons | Points |
|---|---|---|---|
| UA-C1 exactly two bids | 51 % (42/73) / 48 % (212/612) | 13 % | **14.9 / 16.0** [11.4–21.3] |
| UA-C2 only one valid bid (2+ bids) | 20 % / 22 % | 7 % | **9.6 / 13.2** |
| UA-C9 award ≥ 98 % of reserve | 35 % / 35 % | 18 % | **5.6 / 7.3** |
| UA-C11 price increase | 12 % / 6 % | 11 % | 0 |
| UA-C13 amount cut | 14 % / 8 % | 10 % | 0 |
| UA-C15 individual supplier | 5 % / 3 % | 13 % | 0 |
| UA-D2 private contract above the small-value limit | 12 % / 26 % | 23 % | 0 / 0.6 |
| UA-K5 tight bids (CV < 3 %) | 42 % / 84 % | 82 % | 0 (Korean floor-price auctions make most bids tight) |

C1 failed on Ukrainian convictions but is the strongest single check on Korean cartel labels; C2 matches cover bids
made invalid on purpose. Both overlap B2 (two or three bids) and each other, and bidder count is partly a result of
rigging: they need the bidder-count controls of `korea-bid-controls.py` before any adoption. Court labels (10–15 cases
with bids): no UA check earns points (C11 1.4, K5 0.3).

## PRICE-RATIO curves and 0.1 % scan, 2026-10-25 (research; nothing adopted)

Plan: `korea-labels-plan.md` "PRICE-RATIO curve" and "Fine scan" amendments. Tools `tools/korea-curves.py`,
`tools/korea-price-ratio-fine.py`; outputs `~/.cache/contract-signals/korea/curve-price-ratio-*.txt` and `plots/`.

- **Binned curve (decision rule):** collusion K = 3: < 89.2 % counter-signal (LR 0.29), **89.2–99.5 % LR 2.33 → 11.5
  points**, ≥ 99.5 % none (0.89); best single cut ≥ 92.2 % (12.4 points; former 95 % 11.7, 98 % 7.3). One per case:
  K = 8, peak 99.3–99.8 % (LR 4.7, 13 cases). Court (11 cases): signal below 87.75 % (5.4 points), none ≥ 99 %.
  Audit (130 cases) K = 8, two-ended: < 87.7 % 7.6 points, 98.7–99.8 % 4.9, 99.8–99.99 % 11.1.
- **0.1 % scan, 70–100 %:** no single bin survives Benjamini–Hochberg 10 % in any family (collusion 3/300 bands above
  1, ~8 by chance). Replication between case halves (label counts against the smooth label curve × the comparisons'
  own heaping): collusion 0.13 (noise 95th 0.14, p 0.06; without sparse bins 0.16, p 0.15; random case halves mean
  0.22), court 0.003, audit 0.035. What repeats in collusion: deficits where comparisons heap (87.7 % floor: 1 rigged
  vs 27 expected; 87.8, 90.0, 98.0, 98.8 %) and a peak at 99.3 % (14 tenders, 7 cases, both halves). Audit: the rise
  at 99.7–99.9 % is in both halves (14 and 21 cases); its < 87.7 % signal scatters over sparse bins.
- The replication test was corrected twice after the first graphs (shared comparison term; floor heaping), see plan.
- **Replication after Sol's review (cases once per bin, calibrated null, 2026-10-25):** collusion 0.115 (null 95th
  0.126, p 0.058; random case halves mean 0.24, i.e. most other splits would clear the null), court −0.007 (p 0.43),
  audit 0.041 (p 0.30). Conclusion unchanged: collusion's fine structure is borderline-replicable, the others' is not.

## One range per indicator, counter-ranges and two ranges, 2026-10-25 (research; nothing adopted)

Plan: `korea-labels-plan.md` sections "One range per continuous indicator", "Two ranges for audit PRICE-RATIO" and
"Counter-ranges and negative points" (with the nested gate and FLOOR-GAP amendments). Outputs
`~/.cache/contract-signals/korea/{ranges,floorgap,two-ranges,counter}-*.txt`. Decision basis: all linked tenders.

| Measure | Collusion | Court | Audit |
|---|---|---|---|
| PRICE-RATIO (award ÷ reserve) | [92.2 %, 100 %): 77.5 % vs 23.4 %, LR 3.11 → **15.5** (value-controlled LR 3.58); counter [86.7 %, 90.4 %): LR 0.22 → **−20.2** | none; counter [87.8 %, 92.5 %) → −12.2 (11 cases) | two ranges, < 87.3 % or [98.2 %, 100 %): 32.6 % vs 15.9 %, LR 1.97 → **8.6** |
| FLOOR-GAP (win − stated floor, points) | ≥ 0.97: 96.5 % vs 24.4 %, LR 3.66 → **17.8**; counter < 0.97 → **−27.7** (217 labels, 31 cases) | none (at-floor LR 3.9, 7 cases, gate failed) | none |
| BUYER-SHARE (size-controlled) | none (G3 5 % raw 8.3 → controlled LR 0.61) | none | none |
| SUPPLIER-DEPENDENCE (size-controlled) | none | none | none |
| AMEND-PRICE | none | none | none |

- Gate: nested held-out gain over no split > 1 SE over case folds. Accepted gains: FLOOR-GAP 0.25, PRICE-RATIO 0.08
  (collusion); audit two ranges 0.014 and +0.012 over one range. One per case agrees for FLOOR-GAP (≥ 1.10, 14
  points; counter −10.9) and PRICE-RATIO collusion (≥ 92.2 %, 9.2); the audit two-range and the collusion PRICE-RATIO
  counter do not pass there.
- FLOOR-GAP and PRICE-RATIO overlap (both measure a high price); the FLOOR-GAP counter-range is the other side of its
  own cut. How negative points combine within a family is open (owner).
- **Owner's decision 2026-10-25 (option 1, adopted for the site):** one price check per tender. Where the bid opening
  states a lower award limit, FLOOR-GAP scores the price (≥ 0.97: +17.8; below: **−10.9**, the one-per-case counter
  value rather than −27.7, which leans on a few large cases; negatives shrink towards 0 until the joint model);
  otherwise PRICE-RATIO [92.2 %, 100 %) +15.5 replaces K6 (≥ 95 %, 12.7). PRICE-RATIO's −20.2 counter is not used (it
  failed the one-per-case check). The negative offsets the other site families (the index sums family maxima); the
  index is floored at 0. Site letters K7 and B12 (`korea-label-checks.PRICE_CHECKS`); audit's two ranges stay off the
  site, which scores collusion labels only. The joint model replaces this.

## Index check: does the site's Korean index rank rigged tenders higher? 2026-10-25 (research; nothing adopted)

`tools/korea-index-check.py` scores the decision set (contracting office, collusion) with the site's rules
(checks-national.js KR_CHECKS, family maxima summed, floored at 0) and compares buyer-weighted shares per index band;
95 % intervals from 500 buyer bootstraps. "Old" is the index before the price slot (`92d9595`: K6 12.7, no negative
points). In-sample: the points were chosen on these labels. Output
`~/.cache/contract-signals/korea/index-check-2026-10-25.{txt,json}`.

| Set | AUC new / old | Index ≥ 20: rigged vs comparisons, ratio | Index ≥ 30 | Index ≥ 40 |
|---|---|---|---|---|
| All linked tenders: 721 rigged (139 offices), 409,522 comparisons | 0.773 / 0.738 | 71.8 % vs 9.9 %, 7.2 [5.4, 10.5] | 42.7 % vs 3.3 %, 13.2 [8.9, 20.9] | 24.5 % vs 1.8 %, 13.7 [7.7, 32.0] |
| One per case: 102 rigged (50 offices) | 0.776 / 0.777 | 42.7 % vs 9.9 %, 4.3 [2.7, 6.5] | 28.2 % vs 3.3 %, 8.7 [4.9, 15.0] | 11.0 % vs 1.8 %, 6.1 [1.6, 16.5] |
| Bid opening found: 612 rigged (122 offices), 76,201 comparisons | 0.696 / 0.658 | 80.9 % vs 22.5 %, 3.6 [2.9, 4.5] | 49.9 % vs 16.4 %, 3.0 [2.3, 4.1] | 28.3 % vs 7.4 %, 3.8 [2.3, 7.2] |

- Index 0: 3.3 % of rigged tenders vs 47.9 % of comparisons (all linked tenders).
- A bid opening is on file for 85.2 % of rigged tenders but 16.0 % of comparisons (buyer-weighted). Not a download
  gap: rigged tenders were signed 2010-2019 (about 90 %), where day files are complete. Most comparisons have no
  opening at all (only 175,433 of 409,522 are competitive tenders with a notice). Comparisons without an opening
  cannot get the B points, so part of the overall separation is the contract type. Within rows with an opening the
  index separates much less (AUC 0.696), and band 20–29.9 (ratio 5.2) beats 30–39.9 (2.4): families may overlap once
  bid data is present. The "bid opening found" row is the fairer measure for competitive tenders.
- Separately, for the site: bid openings 2021-01..2024-08 were mostly missing, so those contracts could not get B
  points. Backfill `bids/backfill2021.sh` started 2026-10-25; it barely changes this check (few labels after 2019).

### Rerun 2026-10-26: measured points, B7, backfilled bid openings

Same check after `7c4fcc5`: points measured on the backfilled bid openings (B12 floor gap ≥ 1.01: +18, closer: −11;
B2 12.1, B5 11.4, B4 0.9, B7 2.5) and the backfill, which raised the comparisons' opening share from 16.0 % to 28.5 %
(rigged 85.2 %, unchanged). "Old" is still `92d9595`, now scored on the same backfilled openings. Output
`~/.cache/contract-signals/korea/rerun-1026/index-check-final.{txt,json}`.

| Set | AUC new / old | Index ≥ 20: rigged vs comparisons, ratio | Index ≥ 30 | Index ≥ 40 |
|---|---|---|---|---|
| All linked tenders: 721 rigged (139 offices), 409,522 comparisons | 0.761 / 0.691 | 70.7 % vs 11.3 %, 6.3 [4.8, 8.7] | 38.4 % vs 4.9 %, 7.8 [5.0, 13.0] | none |
| One per case: 102 rigged (50 offices) | 0.763 / 0.700 | 42.2 % vs 11.3 %, 3.7 [2.3, 5.5] | 22.3 % vs 4.9 %, 4.5 [2.2, 8.4] | none |
| Bid opening found: 612 rigged (122 offices), 143,875 comparisons | 0.712 / 0.644 | 79.7 % vs 21.9 %, 3.6 [2.9, 4.6] | 44.2 % vs 13.8 %, 3.2 [2.3, 4.6] | none |

- The maximum is now 39.3, so no contract reaches 40. Index 0: 3.3 % of rigged tenders vs 49.5 % of comparisons.
- Against the 2026-10-25 run the overall AUC falls (0.773 → 0.761) and the top band weakens (≥ 30: 13.2 → 7.8),
  but that run had far fewer comparison openings; on the same data the new points beat the old ones in every set
  (AUC +0.06 to +0.07). Within rows with an opening, AUC rises from 0.696 to 0.712.
- Still not monotone where bids are on file: band 20–29.9 (ratio 4.4) beats 30–39.9 (3.2). The family maxima still
  appear to overlap once bid data is present; the joint model is the fix.
