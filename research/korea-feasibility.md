# South Korea (KONEPS / 나라장터): feasibility and plan

Status 2026-10-15: owner approved adding Korea. Nothing downloaded; the APIs need a data.go.kr service key that only the owner can register.

## Sources (Public Procurement Service, 조달청, via data.go.kr)

Checked on the official listing pages on 2026-10-15 (copies in `~/.cache/contract-signals/korea-feasibility/`):

| Service | data.go.kr id | Licence field (이용허락범위) | Approval | Daily quota (development key) |
| --- | --- | --- | --- | --- |
| 나라장터 입찰공고정보서비스 (bid notices) | [15129394](https://www.data.go.kr/data/15129394/openapi.do) | 제한 없음 (no restriction) | automatic | 1,000 calls |
| 나라장터 낙찰정보서비스 (award and bid-opening results) | [15129397](https://www.data.go.kr/data/15129397/openapi.do) | 제한 없음 | automatic | 1,000 calls |
| 나라장터 계약정보서비스 (contracts, change and deletion history) | [15129427](https://www.data.go.kr/data/15129427/openapi.do) | 제한 없음 | automatic | 1,000 calls |
| 나라장터 공공데이터개방표준서비스 (open-standard notices, awards, contracts) | [15058815](https://www.data.go.kr/data/15058815/openapi.do) | 제한 없음 | automatic | 1,000 calls |

All four are free, JSON or XML, and carry no restriction on use, so the cohort can be bundled like the other datasets (attribution to 조달청 and data.go.kr). Owner rule for any Korean source whose licence forbids republication or modification (for example a 공공누리 type 3 or 4 dataset, or bid documents): do not bundle it; link to the official record only. Note for data/LICENSE.md: the project being open source does not change a data licence, because anyone can reuse the repository commercially; each source's own terms travel with its files.

Operations seen on the pages (field lists to be confirmed from the reference documents `조달청_OpenAPI참고자료_나라장터_낙찰정보서비스_1.2.docx` and `..._계약정보서비스_1.0.docx`):

- Awards: `getScsbidListSttus{Thng,Servc,Cnstwk,Frgcpt}` (successful bids: goods, services, works, foreign purchases) and `getOpengResultListInfo{Thng,Servc,Cnstwk,Frgcpt}` (bid-opening results with every bidder's rank and price), plus failed and re-bid lists. Offer counts should come from the opening results.
- Contracts: `getCntrctInfoList{Thng,Servc,Cnstwk,Frgcpt}` with `...ChgHstry` (change history) and `...DltHstry` (deletions), so amendments can be counted as in Ukraine.

## Plan (to be fixed before any download, as for the other countries)

1. **Owner:** register at data.go.kr and request the three services above (development keys are approved automatically). Sign-up may require Korean identity verification; not confirmed.
2. **Cohort:** three buyers announced before download, one national, one regional (광역), one municipal (기초), chosen by count queries only; contracts signed 2024-09-01 → 2026-09-01. With 1,000 calls per day per service, buyers are chosen so that the download fits in a few days.
3. **Checks (editorial points, capped at 30 until measured):** single offer in a competitive procedure; award without competition (수의계약, private contract), with the legal grounds of the Act on Contracts to which the State is a Party (국가계약법) and its enforcement decree recorded as context; repeated single offers and repeated private contracts to one supplier; concentration; three or more contract changes; late publication if dates allow. Thresholds follow Korean law and are written down before computing.
4. **Privacy:** keep company names and business registration numbers of winners; drop representative names (대표자명) and other personal fields; keep unsuccessful bidders as counts only, never names.
5. **Labels for measured points later:** Korea Fair Trade Commission (공정거래위원회) bid-rigging decisions are a likely source, as the Competition Council decisions were in Romania; publication format not checked yet.
6. **Language:** source text stays in Korean; interface strings for the new checks get Spanish and French entries as usual.
