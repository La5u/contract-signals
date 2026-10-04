# Local real-case benchmark construction

This is research material, **not a website dataset or calibrated scoring model**. No deployment or push is authorized. Inputs use public official decisions and procurement notices; raw HTML, contact details, addresses and supplier names are not included in the assembled benchmark.

## Current result

- Six bounded source pages yielded **184 award notices**, not a certified count of distinct contracts and not the entire project population.
- **Somalia Decision 147 / OP00104863:** corroborated multi-field match to SCALED-UP Business Automation Registration Phase II, borrower reference `SO-MOF-176000-CS-CDS`, signed `2020-09-16`. One assistant-reviewed **administrative fraud-positive**; not a criminal conviction or corruption-positive. The separate SCORE contract does not inherit this fraud finding.
- **Bangladesh Decision 148 / OP00102403:** tentative hospital-bed match, reference `PACKAGE GD-13`, signed `2020-05-28`; outcomes remain unknown until scope and USD/BDT valuation discrepancies are resolved.
- **Eight unreviewed comparison candidates**, four per case, selected from the same project and procurement group with the same currency, signature within 366 days and price ratio between 0.25 and 4. Procurement method is **not matched**, avoiding conditioning away the direct-award indicator. This selection is exploratory and nonrepresentative.
- **Iraq Decision146 / G3:** now a corroborated documentary-contract match. The Ministry of Electricity audit lists G3, its JV and USD9,785,978; a procurement plan supplies full reference `EODP-MOE/T.E/G3` and actual signature `2016-11-02`, matching the decision. It carries administrative corrupt- and fraudulent-practice findings, not a criminal conviction or company-wide guilt label. The plan's conflicting USD10,785,978 is retained. Tender `OP00036262` remains a tender; the G7 five-unit award remains rejected as a case match.
- **Three pending case links:** Vietnam2.1/3.3 and DRC. Follow-up verified three Vietnam historical award records and two paired DRC consulting records, but full party/JV and outcome-unit attribution remains unresolved; see `remaining-link-reviews.json`. Vietnam3.3 must not inherit2.1 fraud. Related contracts/decisions are not independent samples.

`case-links.json` preserves source passages, corroboration, rejected matches and hashed documentary records. `benchmark.json` contains three case rows and eight comparison rows, decision standards and limitations, source-response fingerprints/retrieval dates, input manifest fingerprint and readiness diagnostics. `comparison-reviews.json` records the completed public-record fact checks for all eight candidates; their outcome reviews remain incomplete. Labels are tri-state: true/false/null; **null is unknown**.

Current usable labels: **one corroborated administrative corruption-positive and two administrative fraud-positives** (the Iraq record belongs to both), **zero reviewed negatives**. These are assistant documentary reviews, not independent expert validation. `ready_for_fit` deliberately remains false. Merely having one positive and one negative would not make a valid calibration sample.

## Reproduce the bounded collection and assembly

```sh
python tools/worldbank-benchmark.py --fetch \
  --project P168115 --project P173757 \
  --offset 200 --offset 300 --offset 400 \
  --output /tmp/worldbank-comparison-pool.json

python tools/assemble-calibration-benchmark.py \
  --cases research/calibration/case-links.json \
  --pool /tmp/worldbank-comparison-pool.json \
  --output /tmp/worldbank-benchmark.json

python -m unittest discover -s tests -p 'test_worldbank_benchmark.py'
python -m unittest discover -s tests -p 'test_assemble_calibration_benchmark.py'
```

The source API changes over time, so fixed offsets may no longer contain the same cases or peers. Every returned project ID is checked; fingerprints document the actual responses. Publisher dates, signature dates, award prices and source currencies retain their meanings. No automatic exchange-rate conversion. The parser's supported-currency set is deliberately bounded; unsupported prices remain unknown. Ambiguous signature headings, prices, duplicate versions/events and uncertain scope/contact sections are handled conservatively.

World Bank procurement notices are not interchangeable with its major-award tables. The old Socrata endpoint now redirects to HTML. Verified Finances One tables are historical `DS01004/RS00934` (FY2001–FY2016, retired prior-review snapshot) and current `DS00005/RS00005` (advertised FY2020 onward). FY2017–FY2019 coverage is unresolved. Current JV supplier rows can split contract value; source availability is not completeness.

## Review needed before calibration

1. Independently verify decision-to-contract linkage, substantive final finding, later remedies and precise unit/lot/phase; retain administrative fraud/corruption, judicial corruption, audit irregularity and investigations as distinct outcomes.
2. Reconcile the Bangladesh scope, signature and valuation without inventing exchange rates: a2024plan adds actual signature2020-06-10 and USD584,736.99, conflicting with the notice and decision window. Retain Iraq's amount discrepancy and clarify respondent/JV roles without assigning guilt to every member. Resolve Vietnam party/JV and full-value details, plus DRC consultant-employer and outcome-unit attribution. Historical references/date pairs are now documented, but those remaining uncertainties still block additional training labels.
3. Review comparison candidates with a recorded protocol, sources and follow-up window. **No discovered sanction/investigation is not evidence of a clean contract.** If trustworthy negatives cannot be established, design a positive-unlabelled comparison with explicit contamination/selection assumptions rather than turning null into false.
4. Establish indicator applicability and observed evidence from procurement records, independently of outcome labels. Missing inputs must remain unknown. Do not infer post-award amendments from pre-award revisions or use project finance/bribe payments as contract prices.
5. Predeclare the target, sampling, minimum usable evidence, grouping/holdouts and metrics before fitting. Related cases/projects/contracts must not cross train/test boundaries. Labels and case-discovery coverage are essential to interpreting any model difference.

There is no real-world LR-versus-logistic winner yet. The tools assemble evidence and prevent premature fitting; they do not fill missing ground truth or imply independent validation.
