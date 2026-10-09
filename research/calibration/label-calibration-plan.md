# Setting indicator points from labelled cases: plan (2026-10-09)

Research only. No score, weight or dataset changed. Supporting reports: [platforms](sol-platforms-2026-10-09.md), [Ukraine court register](sol-ukraine-2026-10-09.md), [Colombia sources](sol-colombia-2026-10-09.md), [single-bid stand-in test](single-bid-proxy.md).

## What comparable platforms do

- **Government Transparency Institute / ProACT / Opentender:** flags are *selected* (and continuous variables banded) by whether they predict single bidding; the composite is then an **equal-weight mean** (Fazekas & Kocsis 2020: "each 'red flag' is weighted equally"). The 2016 version graded categories 1 / .75 / .5 / .25 by regression impact, not by copying coefficients. Validation is against proxies (prices, tax havens, country indices), not convictions.
- **ARACHNE (legacy):** unequal indicator maxima (5–40), seven categories scored to 50, overall score their mean.
- **Prozorro / DASU:** historical weights 0.1–0.5; since Order 476/2024, high/medium/low priorities. **DOZORRO** learned from ~3,500 tenders labelled risk/no-risk by 20 experts, not convictions.
- **K-Monitor redflags.eu, OCP Cardinal, Brazil ALICE:** individual flags, no published weighted index.
- **Only study found that estimates effects from confirmed cases:** Ferwerda, Deleanu & Unger (2017), 192 procurements (96 with detected corruption, 96 without) across eight EU countries; 8 of 28 indicators retained. Sample size confirmed against the abstract; model details from the Sol report only.

So weighting from confirmed cases would go beyond current practice. The realistic design is: equal or graded weights as the default, single-bid stand-in calibration where data allow, and labelled cases to validate and adjust.

## Label sources

| Country | Best source | Links to a contract? | Status |
| --- | --- | --- | --- |
| Ukraine | Court decisions register: verdicts (вирок), arts. 191/364/366/368/369 and also 354, 369-2 | Some verdicts quote the Prozorro tender ID (three examples found); Clarity Project already shows judgments per tender | Annual CSV metadata exports (CC BY), texts as separate HTML; **no finality field**, so the entry-into-force date and any appeal must be checked by hand. Unverified planning range: 50–500 usable verdicts 2018–2026 |
| Colombia | Criminal judgments (interés indebido, contrato sin requisitos legales, peculado, cohecho) | Judgments name contract numbers; each must be resolved to one SECOP II ID | No API; Monitor Ciudadano (1,243 cases 2016–2022, CC BY-SA) gives leads. SECOP fines, SIRI and fiscal liability are other outcomes, not corruption |

## Proposed pilot (needs owner approval: network access, new cohort)

1. **Ukraine, discovery only:** search the register and Clarity Project for verdicts citing a tender ID; record case number, articles, verdict date, finality evidence and the exact tender string. Target 50 candidates. No tender downloads yet.
2. If 30 or more pass the finality and linkage review, fetch those tenders plus same-buyer, same-year ordinary tenders through the existing Prozorro importer, and compute each indicator's rate in both groups with a likelihood ratio and interval (`tools/calibrate-indicators.py`).
3. Use the result first to **check** the current points; change points only where the lower confidence bound clearly departs from the current level. Comparison contracts are unlabelled, not proven clean.
4. Colombia follows the same pattern later, starting from 20–50 judgments.

## Owner decisions (2026-10-09)

- **Finality:** a verdict counts as *presumed final* when no appeal was found and it is at least 3 months old (Ukrainian verdicts enter into force when the appeal period passes without an appeal). A verdict with a known appeal counts only once the appeal is decided and the conviction stands. Each label records whether finality is confirmed or presumed, so the strict version can be rerun.
- **Two positive labels:** *corruption* (a public official took part) and *procurement fraud* (contractor only, no official established). Both are used for hit rates; results are reported for each separately and combined.
- **Priority:** an indicator's hit rate on positive contracts decides whether it matters; its rate on ordinary contracts only sets its points (via the likelihood ratio). Points need not be whole numbers.

## Finality from the register page (2026-10-09)

The register page header shows "Дата набрання законної сили" (date of entry into legal force) when the court has recorded it; for example verdict 137630272 shows 17.08.2026. This can confirm finality without the presumed rule. **The register rate-limits hard:** about 28 parallel page fetches got HTTP 429, a captcha, then refused connections. Fetch one page at a time, with pauses, and stop at the first 429.

## First results (2026-10-09, preliminary)

Cohort: 20 positive tenders (12 corruption, 8 procurement fraud; 4 with confirmed finality, the rest presumed) and 58 same-buyer, same-year comparison tenders from the Prozorro buyer search (`tools/build-ukraine-verdict-cohort.py --download --budget 350 --scan-pages 3 --k 3`; 350 requests, cap reached with 2 positives at 1 comparison). Full output: [ukraine-verdict-pilot-results.txt](ukraine-verdict-pilot-results.txt).

| Check | Hit rate, positives | Rate, comparisons | LR+ combined [95 % CI] |
| --- | --- | --- | --- |
| Better bid disqualified | 5/15 (33 %) | 7/58 (12 %) | 2.7 [1.04, 7.0] |
| Award without competition | 2/17 (12 %) | 0/58 | 16 [0.8, 326] (smoothed; too few events) |
| Single offer | 3/15 (20 %) | 25/58 (43 %) | 0.51 [0.19, 1.34] |
| Repeated single offer / repeated direct | 0/3, 0/2 | 0/25, none | not estimable |
| Concentration | all unknown (needs buyer history this cohort lacks) | | |
| Amount increase, long duration, late publication | not applicable in the Ukrainian engine | | |

Reading:
- **Hit rates are low for every current check.** The most frequent, better bid disqualified, fires on a third of positives. Most convictions are payment-stage fraud or price-raising amendments, which no Ukrainian check measures.
- **Single offer fires *less* often on convicted tenders than on their buyers' other tenders.** Corrupt schemes here often ran through competitive tenders.
- Better bid disqualified is the only check whose interval lies above 1.
- Next indicator to build: **contract amendments that raise the price** (Prozorro publishes them; StateWatch's ARI 1-1 flags 3+ amendments). Several verdicts are about exactly this.
- Caveats: 20 positives; positives were found by web search of verdicts quoting a tender ID (selection bias); intervals ignore buyer matching; comparisons are unlabelled, not clean.
