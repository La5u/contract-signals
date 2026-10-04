# Real-case calibration feasibility review

## Result

Reviewed **16 official World Bank Sanctions Board decision documents**, including merits decisions, reconsiderations and an appeal. These are **not 16 independent awarded contracts**. They do not yet constitute a usable calibration dataset: exact procurement joins and independently reviewed comparison contracts are missing, and none supplies a complete 18-indicator feature vector.

No real-case model-performance comparison or new website weights were produced. Nothing was pushed. This is a source/evidence review, not an assertion that either LR or logistic detects actual corruption better.

## Official archive

- [Sanctions Board decisions](https://www.worldbank.org/en/about/unit/sanctions-system/sanctions-board/decisions)
- [World Bank Documents & Reports search API, bounded query used](https://search.worldbank.org/api/v2/wds?format=json&qterm=Sanctions%20Board%20Decision&rows=10)

The API returned **328 search results**, not a verified count of unique decisions or contracts. Reconsiderations, related cases, duplicate publications and other document types require deduplication. Country/project catalogue fields can disagree with the decision narrative; do not use them as verified contract joins.

Documents were downloaded to temporary directories and their full PDF/TXT text reviewed. `documents.worldbank.org` text downloads sometimes returned 403; official `documents1.worldbank.org` counterparts were used where successful. HTML/error responses were not treated as decision text. This review did not independently link decisions to procurement data or verify every subsequent remedy/change.

## Reviewed decisions

Administrative findings below are not criminal convictions. Separate **corrupt**, **fraudulent**, **collusive** and **obstructive** practices; do not merge them into a corruption target.

| Decision | Verified geography / caveat | Substantive result | Unit/linkage caveat |
| --- | --- | --- | --- |
| 148 | Bangladesh | Fraud: omitted agent disclosures. | ICU-bed direct contract, signed during 21–28 May 2020, about US$572,500; no unique contract ID. |
| 147 | Somalia, not respondent firm's Kenya | Fraud concerning one consulting contract; obstruction concerning two. | SCORE contract signed 20 November 2018, US$330,000; SCALED-UP single-source contract signed 16 September 2020. Do not propagate the fraud finding across both. |
| 146 | Iraq | Related corrupt and fraudulent practices: public-official payments/offers and concealed commissions. | Mobile-substation JV contract signed 2 November 2016, US$9,785,978; no unique procurement ID. Seven-to-ten-unit revision was **before signature**, not an amendment signal. |
| 65 | Russia | Fraud through undisclosed conflict of interest; controlling-affiliate responsibility/reprimand separate from winning firm. | Automated-system consulting contract signed 21 August 2008, about US$162,000; winning subsidiary and unique contract ID not disclosed. |
| 67 | Indonesia | Fraud: recklessly submitted falsified bid security; reprimand. | Respondent's bid was rejected. **Not a positive awarded-contract observation**. |
| 134 | Vietnam | Fraud and obstruction, with different findings for two firms and three contracts. | Bus-transit Package 2.1 Parts 1/2 and Contract 3.3, signed April–November 2014. Package 2.1 fraud must not automatically label Contract 3.3 fraudulent. |
| 80 | Uzbekistan in catalogue only; procurement country not established by this text | Reconsideration denied; preserves Decision 41's corrupt/fraudulent findings. | Original Cases 77/110 need review. Not a new independent misconduct episode; procurement unit unknown. |
| 57 | Peru in catalogue only | Reconsideration denied; preserves Decision 49 fraud finding. | Underlying procurement unit/stage unknown from this text. |
| 107 | India explicitly established | Challenge rejected; preserves Decision 100 fraud finding for forged expense claims. | Contract execution/reimbursement; unique contract ID and actual contract value absent. |
| 89 | Underlying Philippines case; catalogue says Moldova | Reconsideration denied; preserves Decision 4 collusion finding. | Same Case 73 as Decision 84. Designated-winner status does not establish a signed contract. |
| 84 | Philippines in narrative; catalogue says Moldova | Reconsideration/reprieve denied; preserves Decision 4 collusion finding. | Construction bidding; no exact awarded-contract ID. Deduplicate with 89 and original 4. |
| 101 | Brazil in catalogue, not a fresh procurement finding | Successorship appeal allowed: extending a prior sanction lacked an observable basis. | **Not a corruption positive against appellant; not a clean-contract negative either.** |
| 58 | Bangladesh in catalogue only | Reconsideration denied; preserves Decision 54 fraud finding. | Underlying procurement unit/stage absent. |
| 62 | India | Reconsideration denied; reiterates procurement misrepresentations leading to drug-supply awards. | Fraud, not a corrupt-practice finding; multiple contract awards but no exact IDs/values. Text issuance date 13 January 2014 differs from catalogue's 10 January. |
| 132 | DRC | Reconsideration denied; preserves Decision 125 corrupt-practice finding involving solicitation during consultant agreements. | Not a new independent episode. Exact consultant-agreement IDs absent. |
| 133 | DRC | Substantive corrupt-practice finding involving things of value influencing consultant/public-official conduct. | Two consultant agreements signed 13 December 2004; three affected contractor works described, not uniquely identified. Payment vehicles EUR15,000/EUR40,000 are **not procurement contract values**. |

Four reviewed documents expressly establish or preserve corrupt-practice findings (146, 80, 132, 133). This is a **document count**, not four independently linked positive contracts: reconsiderations and overlapping projects/actors require further original-decision and procurement-level review.

## Source passages and links

### Recently issued merits decisions

- [148 PDF](https://www.worldbank.org/content/dam/documents/sanctions/sanctions-board/2026/sep/Sanctions%20Board%20Decision%20No.%20148.pdf): procurement paras 6–8, liability 33–36.
- [147 PDF](https://www.worldbank.org/content/dam/documents/sanctions/sanctions-board/2026/jun/Sanctions_Board_Decision_No._147.pdf): contracts paras 6–12, fraud 34–41, obstruction 48.
- [146 PDF](https://www.worldbank.org/content/dam/documents/sanctions/sanctions-board/2026/mar/Sanctions-Board-Decision-No-146.pdf): procurement paras 6–8, corrupt practices 31–40, related practices 63.

### Earlier merits decisions

- [65 PDF](https://www.worldbank.org/content/dam/documents/sanctions/sanctions-board/2018/nov/SanctionsBoardDecisionNo-65.pdf): procurement para 8, fraud 58, affiliate responsibility 63, disposition 86. Current official reprimand letter dated 2014 resides in a 2025 URL directory; **URL directory year is not a new sanction date**.
- [67 PDF](https://www.worldbank.org/content/dam/documents/sanctions/sanctions-board/2018/nov/Sanctions-Board-Decision-No-67.pdf): rejected bid 7, recklessness 27, liability 31, reprimand 45.
- [134 PDF](https://www.worldbank.org/content/dam/documents/sanctions/sanctions-board/2021/nov/Sanctions%20Board%20Decision%20No.%20134.pdf): packages 8, conduct 9, liability 58–60, disposition 88. The current official debarment-page footnote distinguishes this sanction from a later overlapping decision.

### Additional archive documents

- [80 TXT](https://documents1.worldbank.org/curated/en/099452501262434511/text/IDU104857ce71ad9b1437b187f313416b09493d1.txt): paras 1, 15, 19.
- [57 TXT](https://documents1.worldbank.org/curated/en/099037101252456023/text/IDU19ff7b77f1626f14b3b1a64e1f65fdcf1ffcc.txt): paras 1, 11–16.
- [107 TXT](https://documents1.worldbank.org/curated/en/099336401292439007/text/IDU1d8e3178e1ca6a147ec19c511f5b7557da3fd.txt): paras 3, 12–15.
- [89 TXT](https://documents1.worldbank.org/curated/en/099555501262421631/text/IDU12001f1911b2ee148e61861714753840cf8ad.txt): paras 1, 3, 11, 14.
- [84 TXT](https://documents1.worldbank.org/curated/en/099526401262438910/text/IDU1c5fff2a31003d14d1f1851f1247787eddd8d.txt): paras 1, 5, 31, 39.
- [101 TXT](https://documents1.worldbank.org/curated/en/099058401262444827/text/IDU1e157f1da1686114a4c1a2de18d738ffe8f29.txt): paras 10–23.
- [58 TXT](https://documents1.worldbank.org/curated/en/099043301252430811/text/IDU1ce75693815c6e1447219d061b9e5afdae937.txt): paras 1, 11–15.
- [62 TXT](https://documents1.worldbank.org/curated/en/099051101252442673/text/IDU1b192361512b71143b91ac29114c549b6617c.txt): paras 1, 10–13.
- [132 TXT](https://documents1.worldbank.org/curated/en/099819112052331593/text/IDU1244b2830126ba149011ab221a71ce5ac079e.txt): paras 3, 10–13.
- [133 TXT](https://documents1.worldbank.org/curated/en/099918412052328359/text/IDU03578d05f08c1e04e6c0bcd10cfe2006ecf6f.txt): agreements/contracts 4–6, conduct 20–29, disposition 44.

## What this tells us about the indicators

These sources document mechanisms that a procurement-metadata index can miss: bribes/commissions, undisclosed conflicts, invented expert qualifications, forged bid guarantees, reimbursement fraud and obstruction. They often require documents, communications or transaction evidence absent from open procurement tables.

Selected decisions disclose direct/single-source procurement; most do not supply complete offer counts, rankings, deadlines, duration, amendments, payment/progress snapshots, comparable unit prices, publication chronology or buyer/supplier cohort denominators. Financing amounts and undisclosed bribe/remuneration payments must not become contract amounts. RFP dates are not submission deadlines. Missing fields are unknown, not clear checks.

This is a feasibility result, **not a measured false-negative rate**: the reviewed documents are selected and are not a representative labelled procurement sample.

## Why a clearer model winner is not yet supported

1. **Exact unit joins missing.** A project, supplier, sanction or case is not interchangeable with a contract/lot/procedure. Bid fraud involving a rejected bid cannot label the eventual winner's contract corrupt.
2. **Deduplication needed.** Reconsiderations repeat outcomes; connected contracts/cases must remain in the same train/test group.
3. **Feature vectors incomplete.** Do not impute narrative omissions as evidence that an indicator did not occur. Do not infer a fraud/corruption mechanism from a lawful direct award alone.
4. **No valid control set.** Unsanctioned suppliers, uninvestigated contracts, dismissed successor appeals and missing labels are not automatically clean contracts.
5. **Selection/finality differs.** Institutional administrative misconduct is a separate target from criminal corruption convictions; audit irregularity and investigations stay separate. Later corrections/remedies need tracking.

## Next credible experiment

Choose one outcome and one jurisdiction/project class. Retrieve original merits decisions and link their specific procurement IDs to complete official award/contract records. Build a separately reviewed comparison sample from the same procurement population, accounting for which contracts were inspected and how cases were discovered. Record labels, finality, feature availability and evidence dates independently of scores. Freeze the benchmark before fitting; group related cases, projects, buyers and periods across splits.

Then compare both LR and logistic on the **same** eligible features, controls, missing-data policy and held-out groups, reporting top-review-budget precision/recall, AP, uncertainty and per-scheme results. Until those prerequisites exist, a real-world winner is **not established**. Keep both offline methods available and do not publish synthetic weights as empirically validated weights.
