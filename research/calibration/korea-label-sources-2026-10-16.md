# South Korea: label sources for indicator calibration (2026-10-16)

Owner request (2026-10-16): calibrate indicators on Korean contracts found corrupt or rigged, as for Romania and Ukraine, and test the global checks there. Research only; no points change without the owner. Source research by Sol (two web-research runs, reports in `~/.cache/contract-signals/korea/labels-research/`), checked here where marked.

## 1. Fair Trade Commission bid-rigging decisions (공정거래위원회 입찰담합) — first source

The Korean equivalent of the Romanian Competition Council decisions: label **collusion**.

- **law.go.kr decision API** (법제처, `target=ftc`): list `lawSearch.do`, detail `lawService.do`, XML/JSON, full text (주문, 이유) with case number, decision number and date; tables inside decisions are images and come through empty. Checked: a title search for 입찰 returns **1,305 decisions** (2012 onward at least). Needs an own `OC` credential (free registration at open.law.go.kr); the demo credential `OC=test` was used for two probe calls only, not for bulk.
- **KFTC public decision corpus** (fairdata.go.kr AI contest, `공개본 의결서.zip`, 243 MB, downloaded to `~/.cache/contract-signals/korea/ftc/corpus/`): 500 decisions published 2020–2026, PDF + text chunks + metadata (violation type, measure, respondents). 87 have violation type 공동-입찰담합, 91 concern tenders; many are private buyers (banks, builders). Licence not stated: used as research input only, not bundled.
- **Identifiers:** 9 of the 91 tender decisions quote KONEPS notice numbers (`20YYMMNNNNN-00`; up to 95 per decision), 33 mention 나라장터, 37 조달청. Others give buyer, tender name and dates, so linking falls back to buyer + tender name + year + winner, as in Romania.
- **Coverage limits:** KFTC also decides private-sector tenders (excluded) and SOE tenders on their own systems (KEPCO, Korea Expressway, LH before April 2024), which are not in KONEPS unless the notice is there. Volume: about 40–75 bid-rigging cases a year (KFTC yearbook 2024, p. 57; includes warnings).
- **Lag:** tender to decision 1–6 years; tenders in the sample date from 2011 to 2022.

## 2. Local-government, education-office and MOIS audits — second source (irregularity, not corruption)

Audit 처분요구서 annexes list individual contracts behind findings of unlawful splitting (분할계약), repeated private contracts and improper changes, with buyer, contract name, date and amount; supplier names are usually masked. Examples found by Sol: Busan agricultural centre 2021 (three contracts split under the one-quotation limit), MOIS joint audit of Ulsan 2021 (13 Ulju-gun medal purchases, KRW 170.6 m). Decentralised boards (PDF/HWP), no bulk API found; licences vary by publisher (some KOGL type 2 or 4), so only the label facts would be kept.

Label **irregularity**, reported separately from collusion. Circular for the split-contract check: an audit that finds splitting cannot validate a splitting indicator, so that check would be reported but not decided on these labels.

## 3. Other sources (later or supporting)

- **Court judgments** (law.go.kr precedent API; court portal KRW 1,000 per judgment, no bulk): private company names are masked; useful to confirm a case found elsewhere, not to find many.
- **Board of Audit and Inspection (감사원)** reports: authoritative but masked, KOGL type 4 (non-commercial, no derivatives); facts only.
- **Debarment** (조달청 부정당제재, data.go.kr 15137996; API 15129466): supplier-level, no notice or contract number; a lead, not a contract label.
- **News**: leads to be confirmed by an official finding; article text never stored.

## Contract data

PPS open-standard contracts (data.go.kr 15058815) answer for every year probed from 2010 (about 4,000–20,000 contracts a week). Older years are needed because labelled tenders predate the 2024–2026 download: 2019-01-01..2024-08-31 is downloading (systemd user unit `korea-opnstd-older`, log `~/.cache/contract-signals/korea/opnstd-older.log`); 2011–2018 when the linked labels need them. A notice number can also be traced to its contracts one by one (service 15129459).

## Next

1. Owner: register at open.law.go.kr for an `OC` credential with access to 공정거래위원회 결정문 (free).
2. Fetch all tender decisions, keep public-buyer ones, extract procedures (notice numbers, buyer, tender name, dates, winners, finality from 후속심결 and court outcomes).
3. Write the plan (labels, comparisons, checks, decision rule) before computing any rate, as in [Romania](romania-bid-rigging-plan.md).
