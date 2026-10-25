# Board of Audit reports as Korean labels: pilot (2026-10-24)

Research only; nothing enters the scoring. Tool: `tools/extract-korea-bai-reports.py` (stages `list`, `fetch`,
`extract`, `check`); linking with `tools/match-korea-court-contracts.py --rulings bai/checked.jsonl`. Private cache
`~/.cache/contract-signals/korea/bai/`.

## Source and terms

- bai.go.kr serves listings, search and files only through `/api/`, which its robots.txt disallows (`DisAllow:/api/`),
  so the site is not scripted. The same reports are attached to BAI press releases on 정책브리핑 (korea.kr,
  department code C00022; robots.txt allows all): the press release (HWP) and the full public report (공개문 PDF).
- Reports are 공공누리 4유형 (attribution, non-commercial, no derivatives): kept privately, facts only.
- korea.kr's list shows the last year only (178 releases, 127 not personnel/events/consulting). Older years need the
  list's date parameters (not tried).

## Sample and reading

- 20 audit-result releases from 2025-10..2026-08, seeded random order, report with ≥ 30 procurement terms
  (계약, 입찰, 낙찰, 공사, 용역); 14 others were skipped (no report PDF or too few terms). 2.9 M characters.
- One model call per 90,000-character chunk, court-ruling schema adapted to audit findings. Free DeepSeek
  (`opencode/deepseek-v4.1-flash-free`) read 11 reports and part of a 12th, then stalled for 17 min (another session
  was using the free tier); Haiku read the rest.
- Result: 13 of 20 reports name specific contracts; 64 findings, 212 contracts (210 with a name, 200 with an
  amount, 177 with a date, suppliers mostly masked as (대표이사 A)). 14 reports have a problem flag: quotes not found
  verbatim in the PDF text (layout breaks or retyping; 36 quotes) or low confidence.

## Linkability

147 distinct contracts from 12 reports went to the court matcher: **43 linked (29 %), all by amount + buyer**,
1 ambiguous, 103 unmatched. Six spot-checked links are all the same contract (e.g. 김해시 생활폐기물 수집·운반 대행용역
3 구역, 2,577,300,000 KRW, 2023-07-14). Linkability depends on the report: 김해시 regular audit 27 of 28, 광화문
project 6 of 7, 경상남도 6 of 11, but the 대법원 audit 0 of 37, SH Corporation (서울주택도시개발공사) 0, the
contract-misconduct inspection 1 of 22. Unmatched contracts are mostly 2022–2024, so not a date-coverage problem;
likely causes are amounts that differ from the contract record (multi-year or changed contracts), buyers outside
KONEPS, and masked suppliers that leave only the amount + buyer route.

## Reading

Roughly 2 linked contracts per audit release, about 250 a year from one year of releases. The findings are audit
irregularities (unjustified direct contracts, steering, inflated changes, bribery), not court-proven offences: a
separate label family with its own weight, decided by the owner before any use. Next if pursued: older years of
releases, a second reading of flagged reports, and a buyer-only route for masked suppliers with name similarity.

## Larger sample and first check rates (2026-10-24 evening)

- korea.kr list read year by year (`list --first-year 2016`; the list takes `startDate`/`endDate`): 1,657 BAI
  releases, 1,357 audit results 2016–2026. Sample grown to 80 (same seeded order; 37 more skipped for no report PDF,
  46 for few procurement terms): 2017 3, 2018 14, 2019 6, 2020 4, 2021 5, 2022 7, 2023 2, 2024 8, 2025 10, 2026 21.
- Read: 56 of 80 reports name contracts; 234 findings, 877 contracts (711 named, 635 with amount, 771 dated). The free
  DeepSeek tier stalled again; Haiku read the 60 new reports (137 chunks) in about 15 min. 62 reports carry a flag
  (quote not verbatim or low confidence).
- Linked: 97 of 668 distinct contracts (15 %), 22 reports, 30 buyers. Lower than the first 20 (29 %): older reports
  more often describe contracts without amounts or with masked buyers. A name + exact-date route (similarity ≥ 0.8,
  ±3 days, one candidate) would add 10 of the first 20 reports' 83 dated misses (29 % → 36 %): matching is not the main
  limit; audit amounts are often multi-year totals, partial payments or unit prices (대법원 IT maintenance: audit
  15,869,640,000 = 2 × the yearly 7,934,820,000 on record, buyer recorded as 대법원, not 법원행정처).
- Check rates, `korea-label-checks.py --family corruption --court-links bai/links.jsonl` (audit labels weighted as
  court labels: 0.91 if under two years old, else 1), compared with the court-conviction labels
  (`prec/extract/links.jsonl`, 17 cases, 18 buyers) run the same way:

| Check | Audit, one per case (22 cases, 18 buyers) | Audit, all linked (91, 29 buyers) | Court, one per case (13, 12 buyers) | Court, all linked (49, 18 buyers) |
|---|---|---|---|---|
| G2 private contract | 52 % vs 72 %, 0 | 0 | 17 % vs 60 %, 0 | 0 |
| G3 buyer share ≥ 5 % | 17 % vs 2 %, 11.7 | 13 % vs 2 %, 11.8 | 17 % vs 1 %, 9.5 | 12 % vs 1 %, 7.5 |
| N5 first-time supplier | 78 % vs 39 %, 5.9 | 52 % vs 39 %, 1.8 | too few buyers | too few buyers |
| K5 restricted competition | 20 % vs 22 %, 0 | 33 % vs 22 %, 2.4 | 67 % vs 27 %, 6.3 | 67 % vs 27 %, 7.6 |
| U2 repeated private contract | 6 % vs 35 %, 0 | 0 | 8 % vs 28 %, 0 | 0 |

  (hit rate among labelled vs comparisons, points by the decision rule). Audit and court labels agree in direction on
  G2, U2 and G3 (G3 is size-like: auditors and prosecutors both pick large contracts, so its points need the size
  control before use); they differ on K5. N5 is the one check the audit labels add. Bid-level checks: too few audit
  labels with bid data (≤ 5 buyers).
