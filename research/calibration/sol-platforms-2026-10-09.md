<!-- Research draft by GPT-6.1-Sol via Codex, 2026-10-09. Web research, not independently re-verified except where noted in label-calibration-plan.md. -->

**The clearest published precedents are equal-weight averages, context-specific category scores, and audit priorities. Regression-based selection of flags does not necessarily mean regression-estimated final weights.** “Unverified” below means I could not establish the detail from accessible primary sources.

| Platform/version | Weighting and aggregation | Validation evidence |
|---|---|---|
| Fazekas–Tóth–King 2016 | Weighted sum; category contributions ranked using regression effects, then rescaled | External corruption proxies; details below |
| Fazekas–Kocsis 2020 | Six equally weighted flags; CRI 0–1 | Single-bidding models, prices, tax havens, country indices |
| ProACT | Unweighted mean of available indicators; displayed integrity 0–100 | Statistical association with single bidding/concentration |
| Opentender | Available-indicator mean, 0–100; higher means greater integrity | Proxy validation |
| Prozorro/DASU | Historical numerical weights; 2024 rules use risk priorities | Legal/expert basis; case-calibrated weights unverified |
| DOZORRO AI | Learned model; public weights/labels unverified | Expert judgments and subsequent civic review |
| Legacy ARACHNE | Unequal indicator maxima; category scores 0–50; category mean | Confirmed-case calibration unverified |
| ALICE; redflags.eu; Cardinal | Alerts/individual flags; no verified standard weighted composite | Operational review/testing |

**Fazekas–Tóth–King, EJCPR 2016.** The accepted manuscript reports:

\[
CRI_i=\sum_j w_jCI_i^j,\qquad \sum_jw_j=1,\qquad CRI_i,CI_i^j\in[0,1].
\]

Components are selected through prediction of single bidding, exclusion of all but one bid, and/or the winner’s share of the buyer’s contracts. Continuous variables are banded by fitting linear predictors, inspecting residual jumps, and refitting categorical specifications. Weighting combines theory and regression evidence: each substantive component initially receives 1; significant categories are ranked by impact—e.g. **1, .75, .5, .25**, rather than directly copying coefficients. The reported construction divides by **13 components**, then by the observed raw maximum **.805**. Validation uses profitability, final/estimated price ratios, political connections and tax-haven registration. **No prosecuted-case validation was verified**; court-established cases are suggested as future calibration. [Accepted manuscript, §§4, 6 and Table 5](https://www.repository.cam.ac.uk/bitstreams/9220033b-23bb-4ea1-9d0e-6f5847ddd93f/download).

**Fazekas–Kocsis, BJPS 2020, including appendix.** Binary logistic regressions identify significant, substantive predictors of single bidding, controlling for procurement characteristics. The six components are single bidding, absent tender publication, procedure type, evaluation criteria, advertisement period and decision period. Exact scoring is:

\[
CRI_i=\tfrac16\sum_{j=1}^{6}RF_{ij}.
\]

The text explicitly says **“each ‘red flag’ is weighted equally.”** Appendix A identifies two residual jumps for continuous predictors, permitting risky extremes; definitions vary by country—short advertisement periods include ≤44 days in Greece versus ≤27 in Britain. Annex E lists country definitions. Validation covers tax-haven suppliers, relative prices, manually collected CT-scanner/road unit prices, and country corruption indices. **Confirmed-case validation was not verified.** [Accepted paper and annexes](https://api.repository.cam.ac.uk/server/api/core/bitstreams/b113c770-ec7d-4414-a728-bed571781a38/content).

**GTI/ProACT.** The platform states **“simple unweighted mean”**, considering nonmissing indicators only. Its selection process tests relationships with single bidding and spending concentration. Displayed indicators use **0 = high risk, 50 = mild risk, 100 = low risk** where applicable; supplier dependency remains continuous. [Official methodology page](https://www.procurementintegrity.org/about). The [GitHub pipeline](https://github.com/INTVP/proACT) separately describes underlying CRI as an elementary-indicator average on 0–1 and documents country scripts; missing-value code **99** is a category code, not 99 risk points. **Limitation:** the [2022 technical paper](https://www.procurementintegrity.org/assets/about/ProACT_methods_paper_20220809_final.pdf) was search-indexed but its full text could not be retrieved; its Annex 2 thresholds were not independently checked.

**Opentender.eu.** The 2026 methodology specifies an arithmetic mean of available integrity indicators, **0–100**, with country-specific **0/50/100** bands for periods and procedures. It reports validation against World Bank Control of Corruption. [Methodology and indicator annex](https://imonitor.govtransparency.eu/wp-content/uploads/2026/03/D2.2-Updated-Risk-Assessment-Methodology_final.pdf). A deployed Opentender dashboard also permits user-adjusted weights; applicability to every deployment is unverified. [Dashboard explanation](https://ug.opentender.eu/dashboards/integrity).

**Ukraine.** Historical DASU weights were **0.1–0.5**; the [published indicator list](https://dasu.gov.ua/attachments/15d1d96c-5327-41fe-a267-6ba7e37f3273_%D0%9F%D0%B5%D1%80%D0%B5%D0%BB%D1%96%D0%BA.pdf) exposes individual values. Order 476/2024 instead publishes **high/medium/low priorities**, reflecting potential effects of violations. [Ministry methodology](https://mof.gov.ua/storage/files/Додаток_%20Методика%20%28наказ%20476%29.pdf), [priority list](https://mof.gov.ua/storage/files/Додаток_%20Перелік%20%28наказ%20476%29.pdf). Rule code is [public](https://github.com/ProzorroUKR/prozorro-risks).

DOZORRO’s initial labels were **risk/no-risk judgments by 20 experts reviewing approximately 3,500 tenders**, blinded to amounts and buyer names—not convictions. Subsequent human assessments supported learning. **Model weights, training-label dataset and held-out performance remain unverified.** [Operator’s account](https://ti-ukraine.org/en/news/dozorro-artificial-intelligence-to-find-violations-in-prozorro-how-it-works/).

**ARACHNE.** Legacy indicator maxima vary **5–40**; seven categories—procurement, contract management, eligibility, performance, concentration, reputational/fraud alerts, reasonability—each score to **50**. Overall risk is their arithmetic mean; reputational/fraud risk averages its **top ten** individual scores. Other within-category formulas remain unverified. [Commission FAQ, questions 36–37](https://mmr.gov.cz/Dotace/media/SF/Arachne-FAQ.pdf). These are legacy rules: the Commission reports replacement by Arachne+ during 2026; its exact aggregation is unverified. [Current Commission page](https://antifraud-knowledge-centre.ec.europa.eu/useful-tools/what-arachne_en).

**Other implementations.** CGU ALICE uses 30+ audit trails and auditor review; TCU ALICE 360 reports operational findings. Neither source establishes public flag weights or confirmed-case calibration. [CGU manual](https://www.gov.br/cgu/pt-br/assuntos/auditoria-e-fiscalizacao/alice/arquivos/sfc-manual-pratico-alice.pdf), [TCU account](https://ia.tcu.gov.br/noticia.html?slug=alice-360-reforca-controle-compras-publicas). K-Monitor/redflags.eu explicitly says **“we did not develop such an index”**, although weighting support exists in code; experts and months of testing reduced 60+ candidates to 40 operational indicators. [Developer booklet, pp.11–13](https://transparency.lt/wp-content/uploads/2018/04/OLAF_Red_Flags_Booklet.pdf). [Cardinal](https://cardinal.readthedocs.io/en/latest/) calculates individual indicators; the [OCP guide, pp.14–15](https://www.open-contracting.org/wp-content/uploads/2024/12/OCP2024-RedFlagProcurement.pdf) offers counts or optional weighted indices, without prescribing weights, and recommends contextual validation.

**Confirmed-case estimation.** Ferwerda, Deleanu & Unger (2017; online 2016) estimate **ordered-probit coefficients** from **192 procurements: 24 confirmed corrupt, 72 suspected (“grey”), 96 clean**, across eight countries/five sectors. Confirmed means judicial ruling or validated confession. Their AIC-selected model retains eight indicators, pseudo-\(R^2=.38\); Tables 7–8 publish coefficients. These are estimated associations, not portable point weights or population probabilities; the sample deliberately balances cases and controls. [Study](https://link.springer.com/article/10.1007/s10610-016-9312-3).