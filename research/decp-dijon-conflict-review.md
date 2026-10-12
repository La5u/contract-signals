# Dijon DECP conflict: procedure identifier versus lot contracts

## Conclusion and integration (2026-10-08)

Buyer **21210231300013**, ID **2023VDAO1642** covers six distinct lot contracts, not six versions. Notice **24-79759** identifies it as a procedure ID and supplies separate contract references. All six holders were linked through the official register. The owner approved splitting, retaining source IDs and sibling links; this supersedes the earlier excluded-row/approval-pending decisions.

The wider Maison des Associations review compared **26 distinct project DECP source rows**, plus two unrelated rows reusing an ID, with awards **24-79759, 24-73828, 24-77579, 24-78296, 25-33856**.

## Project timeline and findings

- **2023-12-21:** call **23-176628**, 23 lots (1–18, 20–24).
- **2024-04-10:** relaunch **24-41263** (2–6, 8–11, 15, 24), **24-41260** (16, 18, 21), both “Relance après déclaration sans suite”; new **24-41255** (19, 25–27).
- **2024-06-26–07-09:** four awards. Original **24-79759** awards 7 lots, closes 16 without winner (`clos-nw`, “other”). These match relaunches except 17/22, with none found.
- **2025-03-25:** **25-33856** re-awards lot 12, **194,000 EUR HT, 6 offers**, to another holder. No DECP modification explains the original contract's end.

`tools/reconcile-dijon-project.py`, private `project-reconciliation.json`, distinguishes:

- Procedure IDs: **2023VDAO1642 (6 lots)**, **2024VDPA0121 (4 MAPA lots)**; exact amount/date/reference and register-holder linkage.
- Unrelated contracts: **2024VDPA66** covers lot-12 relaunch, school OPC and Parc des Expositions diagnostic; objects, CPV, durations and holders differ.
- Joint-holder rows: **2024VDAO017006**, `Conjoint`, has two Ministry holders but one notice lot-6 winner. The other is notice lot-8 winner; lot 8 (**559,742.62 EUR**, **2024vdao017008**, **6 offers**) has no DECP row in the exact-ID/amount check. Mix-up plausible, unproved; this group stayed excluded at this integration stage.

**26 of 27 project rows** pair uniquely on amount/date, with matching references; **2024VDPN0137**, negotiated **75,596.06 EUR**, has no notice in scope. **22 of 27** holders link. Exceptions: lot 3 current-name mismatch (same postcode), lot 15 STCE ELECTRICITE/STCE ENERGIES, lot 16 closed/different postcode, extra lot-6 holder, and the unpaired contract.

**Seven offer disagreements:** lots **7 (2/4), 12 (2/5), 20 (2/3), 14 (1/2), 9 (5/6), 24 (6/4), 16 (3/2)**, DECP/notice. All offers electronic. AWS DECP and Avenue-Web Systèmes notices are buyer declarations through the same platform, not independent witnesses. No value wins; buyer offer-analysis reports are needed and were not requested. Such reports are normally communicable after award with business secrets redacted.

- Printed lot IDs can be wrong: **24-73828** titles 16/18 carry InternalID 19/25; **24-78296** title 27 carries 4. Use titles checked against reference suffixes, not technical IDs.
- Keep DECP typos **2024CDAO017002** (notice `2024vdao017002`) and **2024VDPA0174118** (`2024vdpa017118`) as published.
- Only **25-33856** states tax basis; DECP equals its HT amount. Other tax/scope comparability remains unresolved.
- Relaunching works lots 16/18/21 as MAPA may fall under Code de la commande publique **R2123-1 2°**; the operation's estimated total is missing, so limits cannot be checked. No indicator added.

## Six original lot pairings

| Technical notice lot | Printed lot number | Printable contract reference | Notice value (EUR) | DECP notification / notice conclusion | DECP offers | Notice total offers | Contract reference PDF page |
| --- | ---: | --- | ---: | --- | ---: | ---: | ---: |
| LOT-0001 | 1 | 2023vdao164201 | 456,516.27 | 2024-06-11 | 10 | 10 | 28 |
| LOT-0007 | 7 | 2023vdao164207 | 668,893.00 | 2024-06-27 | 2 | **4** | 29 |
| LOT-0012 | 12 | 2023vdao164212 | 168,127.96 | 2024-06-27 | 2 | **5** | 30 |
| LOT-0013 | 13 | 2023vdao164213 | 580,470.95 | 2024-06-27 | 4 | 4 | 31 |
| LOT-0019 | 20 | 2023vdao164220 | 155,995.41 | 2024-06-27 | 2 | **3** | 33 |
| LOT-0022 | 23 | 2023vdao164223 | 105,055.00 | 2024-06-27 | 2 | 2 | 34 |

Technical **LOT-0019/LOT-0022** mean printed lots **20/23**. The seventh award, **LOT-0014**, **57,000 EUR**, reference **2024vdao164214**, is outside the six-row group; it was not added to a replacement total.

Notification/conclusion dates agree numerically but retain different meanings. Notice winning-tender payable and DECP initial declarations are not verified signed-contract/payment totals. The national parquet's lone **456,516.27 EUR** row covers lot 1, not the six lots; uniqueness does not justify preferring it.

Holder linkage uses `LotResult → LotTender → TenderingParty → Organization` and DINUM `recherche-entreprises.api.gouv.fr`: unique establishment/SIRET, matching SIREN prefix, legal-form-stripped name tokens, equal postcode, no winner reused. All six (1,7,12,13,20,23) pass; lot 20's establishment is closed today, not necessarily at notification.

## Applied safeguards and historical score effect

`data/decp-cities-curated.json` contains **3 splits/13 rows, 4 single-row offer conflicts, 1 unresolved group**, and one project with **18 identifiers/9-notice timeline**, no total or score.

- `tools/import-decp-cities.py` splits only if every distinct source row matches exactly one curated lot by holder/amount/date and every lot is used. Source drift or modifications stop import.
- Keep DECP amount/date/holder/ID; add `lotId`, `noticeId`, `procedureGroup` with members, kind, reference, title and basis. Disputed offers are null, alternatives in `offersConflict`.
- `script.js` permits shared IDs only for exact validated members; panel links siblings/project and shows disputes.
- Cities: records **1,270 → 1,280**, excluded **172 → 169**, flagged **111 → 110**, single-bid **52 → 51** (lot 14 now unknown). All 13 new lots score **0**. Other datasets unchanged; overall amount gaps **1,537 → 1,534**.

This describes the integration stage; published data changed then, without commitment/deployment at that point.

## Sources, private evidence and reproduction

[Notice 24-79759](https://www.boamp.fr/pages/avis/?q=idweb:24-79759), [official PDF](https://www.boamp.fr/telechargements/FILES/PDF/2024/07/24-79759.pdf): **39 pages**, version **01**, notice UUID **abf0a548-7c69-44e0-a066-402d0b1aa048**, procedure UUID **682e7482-e0b9-440b-9031-d9438725cea9**. Exact buyer/procedure match; PDF corroborates structured relationships and lot values/references/dates/offers. BOAMP exact-ID search also finds call **23-176628**; live Ministry exact buyer/ID still had six amounts, without year restriction.

Private root: `~/.cache/contract-signals/decp-conflict-dijon/`; `project-notices-20261008/`, `holder-registry-20261008/`, minimized `holder-linkage.json`. Responses, retrieval metadata and hashes stay private; raw names/identifiers/PDFs must not be served. Original project discovery was partial (**15** results), not exhaustive.

API policy: **2 MiB**, **15 seconds**, **2-second** spacing, no redirects/retries, stop on failures; PDF **10 MiB**, **15 seconds**, received **2,734,764 bytes**; register **512 KiB**, **15 seconds**. Plans are exclusive; fetchers refuse repeats.

```sh
# Default is a no-network plan; --fetch performs the three frozen discovery requests.
python tools/fetch-decp-conflict-evidence.py

# Offline candidate and PDF reconciliation; requires private evidence and pypdf.
~/.cache/contract-signals/venv/bin/python tools/reconcile-dijon-conflict.py

python -m unittest discover -s tests -p 'test_*decp_conflict*.py'
python -m unittest discover -s tests -p 'test_reconcile_dijon_conflict.py'
```

Holder tool: `tools/link-dijon-holders.py` (offline default, `--fetch`), `tests/test_link_dijon_holders.py` (**10 tests**). Reconciler uses finite Decimal, exact buyer/procedure and unique relationships. **7 reconciliation + 4 fetcher tests** cover identity/basis/reference ambiguity and acquisition limits; full validation: **302 Python tests**, all JavaScript suites and browser passed. Tests establish behaviour, not publisher accuracy.
