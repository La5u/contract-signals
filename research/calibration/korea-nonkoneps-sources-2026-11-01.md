## 1. KOGAS — 61 unmatched contracts

| Source | Availability, fields and access |
|---|---|
| [Contract API, data.go.kr **15072207**](https://www.data.go.kr/data/15072207/openapi.do) | Contract-level XML; contract number, name or supplier search, contract date, amount and method. Bidder list and earliest contract year **unverified**. The published operation is [`getContractinfoList4`](https://apis.data.go.kr/B551210/contractInfoList4/getContractinfoList4); live response and completeness **unverified**. Free, unrestricted reuse; the catalogue lists operational approval by review. API use requires an owner’s data.go.kr application and key. [Catalogue description](https://govapiatlas.com/ko/org/b551210/). |
| [Bid API, data.go.kr **15157366**](https://www.data.go.kr/data/15157366/openapi.do) | Bid number, title, method, closing and opening dates, and contract-related information; winner and full bidder fields **unverified**. [Published operation](https://apis.data.go.kr/B551210/bidInfoList2/getBidInfoList2); historical start and live response **unverified**. Catalogue says free, unrestricted reuse and automatic operational approval; key required. |
| [KOGAS bid list](https://www.kogas.or.kr/site/koGas/referenceBidList.do?Key=1050105000000) | **Guest access verified:** current titles, numbers, methods and dates appeared without login. Historical depth, awards, bulk export and website reuse terms **unverified**. The [procurement system](http://bid.kogas.or.kr) timed out during checking. |

## 2. Military units / DAPA — approximately 80 unmatched

| Source | Availability, fields and access |
|---|---|
| DAPA CSVs: [facility works **15050928**](https://www.data.go.kr/data/15050928/fileData.do) and [domestic procurement **15050918**](https://www.data.go.kr/data/15050918/fileData.do) | Bulk bid-level results for **public quotation procedures**, not all defence contracts. The 2025-dated files have 11,517 and 4,875 rows respectively; earliest underlying year is **unspecified**. Fields include title, procuring unit, deadline, budget, method, result status and estimated price; the listed schemas do **not** identify winning or competing firms. Free, unrestricted reuse. Portal states files can be downloaded without login; generated JSON/XML API requires registration and application. File download and API response **not tested**. |
| [D2B](https://www.d2b.go.kr/) | DAPA describes real-time bid notices, results and contract information in its [service guide](https://www.d2b.go.kr/contents/info/mobile.do?key=607). Exact query URLs, fields, historical depth, guest access, bulk export and reuse terms **unverified**; the homepage timed out. Do not assume the CSVs cover all D2B procedures. |

## 3. LH and Korea Expressway — 26 unmatched combined

| Source | Availability, fields and access |
|---|---|
| [LH contract API, **15159010**](https://www.data.go.kr/data/15159010/openapi.do) | Contract-level XML searchable by contract date and notice number: contract number, title, date, amount, method, counterparty and period. Bidders and earliest record year **unverified**; API registration in 2016 is not evidence of historical coverage. Free, unrestricted reuse; automatic approval, 1,000 development calls/day. Owner must apply for a key. Exact operation URL and live response **unverified**. [LH e-procurement](https://ebid.lh.or.kr/) timed out; guest access and site terms **unverified**. |
| [LH opening-results API, **15159014**](https://www.data.go.kr/data/15159014/openapi.do) | Notice number, title, design amount and estimated price, queried by opening date. Winner and bidder fields, earliest year and live response **unverified**. [Published service endpoint](https://apis.data.go.kr/B552555/OpenTenderopenList); free, unrestricted reuse; key required. [Official catalogue](https://www.data.go.kr/catalog/15159014/openapi.json). |
| [Expressway contract API, **15128076**](https://www.data.go.kr/data/15128076/openapi.do) | A government catalogue mirror describes contract title, date, amount, method, supplier and notice number; bidder list and earliest year **unverified**. It reports free use and CC0; confirm terms and key requirements on the provider before reuse. [Mirror](https://data.edmgr.kr/dataView.do?id=www-data-go-kr-data-openapi-15128076); [provider catalogue entry, API 0622](http://data.ex.co.kr/openapi/basicinfo/openApiInfoM?apiId=0622). Live operation URL and response **unverified**. [e-bid](https://ebid.ex.co.kr/) timed out; guest access and site terms **unverified**. |

## 4. KEPCO — 24 unmatched

| Source | Availability, fields and access |
|---|---|
| [Distribution construction contracts, **15090394**](https://www.data.go.kr/data/15090394/fileData.do) | **878-row CSV**, limited to distribution unit-price works and dated 2022-12-29; earliest underlying contract year **unspecified**. Includes contract number, title, date, counterparty, amounts and bidder **count**, but not a bidder-name list. Free, unrestricted reuse. Portal says guest file downloads are allowed; download **not tested**. Generated API requires registration and application. The schema also lists personal fields: exclude those from the project. |
| [KEPCO SRM](https://srm.kepco.net/) | Site opened without readable page content. Guest search, contract and bid fields, export/API, historical depth and reuse terms **unverified**. |

## 5. KORAIL / KR — 24 unmatched combined

| Source | Availability, fields and access |
|---|---|
| [KORAIL e-procurement](https://ebid.korail.com/) | Opened without readable page content. Guest search, fields, historical depth, bulk/API and terms **unverified**. One [official KORAIL tender](https://www.g2b.go.kr/pn/pnp/pnpe/UntyAtchFile/downloadFile.do?bidPbancNo=R26BK01488249&bidPbancOrd=000&fileSeq=2&fileType=&prcmBsneSeCd=07) uses KONEPS for its bid and opening result, then KORAIL for the contract; recheck KONEPS for those cases. This example does not establish historical coverage. |
| [KR e-procurement](https://ebid.kr.or.kr/main.do) | **Guest homepage verified:** current notice titles and dates are visible. Site says bidding requires certificate or fingerprint login; guest access to historical details, results and contracts remains **unverified**. Bulk/API, earliest year, amount, winner, bidders and reuse terms **unverified**. KORAIL and KR are separate buyers and systems. |

## Cross-buyer and recommended order

[ALIO](https://www.alio.go.kr/) is a cross-buyer lead for public-institution bid and direct-contract disclosures, including these corporations; it is not a demonstrated complete contract archive. The [disclosure rules](https://phlb.tistory.com/entry/%EA%B3%B5%EA%B3%B5%EA%B8%B0%EA%B4%80-%EC%A7%80%EC%B9%A8-%EA%B3%B5%EA%B3%B5%EA%B8%B0%EA%B4%80%EC%9D%98-%ED%86%B5%ED%95%A9%EA%B3%B5%EC%8B%9C%EC%97%90-%EA%B4%80%ED%95%9C-%EA%B8%B0%EC%A4%8025228%EA%B0%9C%EC%A0%95) describe public-bid information and quarterly direct-contract disclosures, with five years of disclosure generally required. ALIO returned **403** during checking: guest use, record fields, bulk/API, terms and pre-2010 coverage remain **unverified**.

1. **Apply for KOGAS and LH keys**, while downloading the two DAPA files and KEPCO CSV; match titles, dates and amounts first. The ranking is a hypothesis based on unmatched counts and documented fields, not measured yields.
2. **Test Expressway’s API and D2B public search**, then investigate KORAIL/KR and ALIO. Ask the owner to apply for any required API keys; no login-walled data is needed for the research above.
3. For all **452 pre-2010 cases**, test earliest available dates explicitly before building an ingestion pipeline. No source above establishes pre-2010 contract coverage. Keep candidate matches separate from confirmed links until checked against the ruling.

## Checked 2026-11-01 (after the table above)

- **DAPA CSVs 15050928, 15050918:** downloaded as guest. They run from 2024-11-01 to 2025-12-31 only, cover quotation procedures, and name no winner. No use for court labels.
- **KEPCO CSV 15090394:** contracts of late 2022 only (878 rows). No use for court labels, whose contracts are mostly older.
- **KOGAS APIs 15072207, 15157366:** the project's key answers `SERVICE_KEY_IS_NOT_REGISTERED_ERROR`, so each needs 활용신청 on data.go.kr. Start year still unknown.
- **LH 15159014:** the endpoint in the table answers `NO_OPENAPI_SERVICE_ERROR`, so that path is wrong; take it from the dataset page.

KOGAS is the only source left that could add many labels, and only if it reaches back far enough.
