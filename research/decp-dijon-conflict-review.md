# Dijon DECP conflict: procedure identifier versus lot contracts

## Scope and result

The frozen review row is `decp-21210231300013-2023VDAO1642`: exact municipal buyer SIRET `21210231300013`, source identifier `2023VDAO1642`. The six saved Ministry rows have distinct holders and amounts, and contain no modification identifiers. They are grouped by the current importer into one conflict-safe, unscored row. This investigation made **no published data or score changes**.

A new bounded official-source check and document review found an important explanation: BOAMP award notice **24-79759** explicitly declares **2023VDAO1642 as its procedure's internal identifier**, and gives separate lot-level contract references. Thus the DECP buyer + supplied ID cannot safely be interpreted as one unique contract here. The six conflicting amounts can each be paired with a separate awarded lot in this notice under the exact buyer/procedure scope.

This is stronger evidence of **procedure-level identity collapse** than an unexplained version conflict. It is not permission to choose one amount, sum the amounts, or globally change DECP granularity. Individual cross-source pairings remain **candidates**: BOAMP's winning-holder registration fields are placeholders, so we cannot independently establish exact holder identity from that notice. No signed buyer contract, notification letter or original buyer-profile DECP export was acquired.

## Update 2026-10-08 (later): project-wide reconciliation and integration

The owner approved splitting the group, with the resulting records kept linked to each other. Investigation was widened to the whole operation, because **2023VDAO1642 is only one procedure of a larger project**. Twenty-six distinct DECP source rows (plus two unrelated rows that reuse one identifier) name the Maison des Associations project. They were compared with **five BOAMP award notices**: 24-79759 (the original procedure), 24-73828, 24-77579 and 24-78296 (the 2024 relaunches and additional lots), and 25-33856 (the 2025 lot-12 relaunch).

**Timeline** (from BOAMP; private responses frozen in `project-notices-20261008/`):

- 2023-12-21: call 23-176628 publishes 23 lots (1–18, 20–24).
- 2024-04-10: relaunch calls 24-41263 (lots 2–6, 8–11, 15, 24) and 24-41260 (lots 16, 18, 21), both titled *"Relance après déclaration sans suite"*. A new call, 24-41255, covers lots 19 and 25–27.
- 2024-06-26 to 2024-07-09: four award notices. The original notice 24-79759 shows 7 lots awarded and 16 closed with no winner (`clos-nw`, reason "other"). Those 16 lots match the relaunch calls, except lots 17 and 22, which have no relaunch notice in this search.
- 2025-03-25: 25-33856 re-awards lot 12 (194,000 EUR HT, 6 offers) to a different holder than the 2024 lot-12 contract. No DECP modification records why the original lot-12 contract ended.

**Findings** (tool `tools/reconcile-dijon-project.py`; private output `project-reconciliation.json`):

- **Three identifier patterns are mixed together**, each needing different handling:
  1. *Procedure ID for several lot contracts*: `2023VDAO1642` (6 lots) and `2024VDPA0121` (4 lots, MAPA). Every row is linked to one notice lot by exact amount, date and contract reference, with the holder verified in the register.
  2. *One ID for unrelated contracts*: `2024VDPA66` covers the 2025 lot-12 relaunch, an OPC mission for a school, and a Parc des Expositions diagnostic. Objects, CPV codes, durations and holders all differ.
  3. *Joint contract published one row per holder*: `2024VDAO017006` (`typegroupementoperateurs=Conjoint`). The notice names **one** winner for lot 6. The second DECP holder is the company the notice names as the **lot 8** winner, and lot 8 (559,742.62 EUR, reference 2024vdao017008, 6 offers) **has no DECP row at all**. It is absent from the live Ministry API by exact ID and by exact amount (1 request, 0 results). A data-entry mix-up is plausible but not established. This group **stays excluded**.
- **Pairing:** 26 of 27 project rows pair uniquely with a notice lot on exact amount and date, and every contract reference matches. The exception is `2024VDPN0137`, a negotiated contract (75,596.06 EUR) with no notice in scope. Holders link in the register for **22 of 27** rows. Of the five that don't: lot 3 has a different current register name (same postcode), lot 15 has a renamed-looking name (STCE ELECTRICITE / STCE ENERGIES), the lot-16 establishment is closed with a different postcode, the lot-6 second holder is discussed above, and `2024VDPN0137` has no notice. Linkage requires an exact SIRET, a SIREN consistent with it, distinctive name tokens contained in either direction (legal forms ignored), and an equal postcode.
- **Offer counts disagree on 7 lots**: printed lots 7 (DECP 2 / notice 4), 12 (2/5), 20 (2/3), 14 (1/2), 9 (5/6), 24 (6/4) and 16 (3/2). The disagreements go in both directions. Every offer was electronic. DECP (`source: AWS`) and the notices (eSender Avenue-Web Systèmes) are two declarations by the same buyer through the same platform, so neither is independent. **No rule picks one.** Settling them needs the buyer's offer-analysis reports (*rapports d'analyse des offres*). These are normally communicable on request after award, with business secrets redacted, but they have not been requested.
- **The notices' printed-lot field is unreliable.** The eForms `InternalID` contradicts the buyer's own lot title in 24-73828 ("Lot n°16" carries 19, "Lot n°18" carries 25) and in 24-78296 ("Lot n°27" carries 4). Lot numbers are taken from the title and checked against the contract-reference suffix.
- **DECP identifier typos:** `2024CDAO017002` (reference 2024vdao017002) and `2024VDPA0174118` (reference 2024vdpa017118). They are kept as published.
- **Tax basis:** for the one notice that states it (25-33856), the DECP amount equals the notice's **HT** (excluding VAT) amount.
- **Procedure-choice context, not a finding:** lots 16, 18 and 21 of a works operation tendered under an open procedure were relaunched as an adapted procedure (MAPA). French law allows this for small lots within limits (Code de la commande publique R2123-1 2°). Checking those limits would need the operation's total estimated value, which we do not have. No indicator was added.

**Integration (published data changed; not committed or deployed):**

- `data/decp-cities-curated.json`, generated by the tool from linked evidence only:
  - 3 procedure splits (13 rows);
  - 4 offer conflicts on single rows;
  - 1 unresolved group (`2024VDAO017006`);
  - 1 documented project: 18 identifiers, a 9-notice timeline, and no project total or project score.
- `tools/import-decp-cities.py` applies it. A split happens only when every distinct source row matches exactly one curated lot (holder SIRET, amount, date) and every lot is used. Any change to the source rows, or a published modification, **stops the import** rather than guessing.
  - Lot rows keep DECP's own amount, date, holder and identifier, and add `lotId`, `noticeId` and `procedureGroup` (members, kind, contract reference, lot title and basis).
  - Disputed offer counts become `null`, with `offersConflict` holding both values.
- `script.js`: rows that share an identifier stay ambiguous unless they are **exactly** the members of a validated procedure group. The record panel lists sibling lots as buttons, shows disputed offer counts, and links to the whole project through the existing project view.
- **Score effect (cities cohort only):** rows 1,270 → 1,280; excluded 172 → 169; flagged 111 → 110; single-bid 52 → 51. The single-bid change is lot 14 (DECP 1 offer, notice 2), which is now unknown. All 13 new lot rows score 0. Other datasets are unchanged. The missing-amount inventory drops from 1,537 to 1,534 gaps, because three null-amount groups now have lot amounts.
- **Requests this phase:** 3 exact BOAMP notices, 19 register lookups and 1 Ministry query, all HTTP 200 and bounded as before.

## Update 2026-10-08: holder linkage established for all six rows

The identity gap left by BOAMP's placeholder winner registrations is now closed through an independent official register. Each Ministry row's single holder SIRET was looked up once, by exact SIRET, in the DINUM company register (`recherche-entreprises.api.gouv.fr`). The establishment record was then compared with the winner that the award notice names for that row's candidate lot, following the structured chain `LotResult → LotTender → TenderingParty → Organization`.

A row counts as **holder-linked** only if all of the following hold: the register returns exactly one establishment for that SIRET; the establishment's SIREN equals the SIRET prefix; the winner's name tokens, after removing legal-form words, are contained in a register name; the establishment postcode equals the winner's postcode; and no winner accounts for two rows. **All six candidate pairings meet every condition** (printed lots 1, 7, 12, 13, 20, 23). The six winners are six distinct establishments, so the six DECP rows are six separate lot contracts by different holders, not versions of one contract.

| Printed lot | Name agrees | Postcode agrees | Register state today |
| ---: | :---: | :---: | --- |
| 1 | yes | yes | active |
| 7 | yes | yes | active |
| 12 | yes | yes | active |
| 13 | yes | yes | active |
| 20 | yes | yes | **closed establishment** (current state, not at notification) |
| 23 | yes | yes | active |

Six requests were made, all HTTP 200, each 4–5 KB. Policy: 512 KiB cap, 15-second timeout, two-second spacing, no redirects or retries, and an exclusive plan freeze. Raw responses are in private `holder-registry-20261008/`, and the minimized result (no names or identifiers) is in private `holder-linkage.json`. Tool: `tools/link-dijon-holders.py` (offline by default; `--fetch` refuses to run again once the freeze exists). Tests: `tests/test_link_dijon_holders.py` (10).

**Offer counts remain unresolved.** For printed lots 7, 12 and 20, DECP says 2 offers and the notice says 4, 5 and 3. Both records come from the same buyer through the same platform: the DECP rows carry `source: AWS`, and the notice's eSender is Avenue-Web Systèmes. So these are two conflicting declarations by one publisher, and neither source is independent of the other. The notice records every offer for these lots as electronic (`tenders` = `t-esubm`), which rules out a paper-versus-electronic explanation. Only the buyer's offer-analysis report could settle the counts, and it is not public. Any integration must therefore leave these three offer counts **unknown** (null, never 2 or the notice value). Single-bid and low-competition checks must not evaluate those three lots. A later notice, **25-33856** (2025), re-tenders printed lot 12. This is recorded as context only: nothing about the original lot-12 contract's fate is inferred from it.

**Resolution status:** the conflict's cause is established (a procedure ID reused for six lot contracts), and amount, date and holder linkage are corroborated for all six rows. What remains is an owner decision on integration, set out under "Decision and next gate".

## Exact linkage and documentary evidence

Official sources:

- Ministry DECP API: exact `acheteur_id='21210231300013' AND id='2023VDAO1642'`, without a year restriction. The live response still contains **six rows**, with the same six amounts as the retained snapshot.
- BOAMP exact text search for `2023VDAO1642` in notice data: two results, initial notice **23-176628** and award notice **24-79759**. Discovery did not select a record merely by similar title or amount.
- Award notice [24-79759](https://www.boamp.fr/pages/avis/?q=idweb:24-79759), [official PDF](https://www.boamp.fr/telechargements/FILES/PDF/2024/07/24-79759.pdf): **39 pages**, notice UUID `abf0a548-7c69-44e0-a066-402d0b1aa048`, version **01**, procedure UUID `682e7482-e0b9-440b-9031-d9438725cea9`. Exact buyer SIRET and internal procedure ID match the DECP scope.

For each candidate, the notice's `LotResult` links the exact `LotTender` and `SettledContract`; the tender links the exact technical lot; the settled contract links the same tender and supplies a printable contract reference. These chains were followed, not inferred from adjacent text or identical monetary values alone. The PDF corroborates the exact lot's amount, printed reference, conclusion date and total-tenders statistic from the structured notice.

## Six candidate lot pairings

| Technical notice lot | Printed lot number | Printable contract reference | Notice value (EUR) | DECP notification / notice conclusion | DECP offers | Notice total offers | Contract reference PDF page |
| --- | ---: | --- | ---: | --- | ---: | ---: | ---: |
| LOT-0001 | 1 | 2023vdao164201 | 456,516.27 | 2024-06-11 | 10 | 10 | 28 |
| LOT-0007 | 7 | 2023vdao164207 | 668,893.00 | 2024-06-27 | 2 | **4** | 29 |
| LOT-0012 | 12 | 2023vdao164212 | 168,127.96 | 2024-06-27 | 2 | **5** | 30 |
| LOT-0013 | 13 | 2023vdao164213 | 580,470.95 | 2024-06-27 | 4 | 4 | 31 |
| LOT-0019 | 20 | 2023vdao164220 | 155,995.41 | 2024-06-27 | 2 | **3** | 33 |
| LOT-0022 | 23 | 2023vdao164223 | 105,055.00 | 2024-06-27 | 2 | 2 | 34 |

**Technical IDs are not printed lot numbers.** `LOT-0019` is printed lot **20**, and `LOT-0022` is printed lot **23**; deriving the lot number by parsing the technical ID would be wrong. Likewise, the contract reference suffix is not universally the technical lot ID.

The notice has seven awarded results overall. The additional photovoltaic result is **LOT-0014**, value **57,000 EUR**, contract reference **2024vdao164214**. It is not one of the six source rows and uses a different year prefix; it was not forced into the target DECP group or included in a replacement total.

Dates agree numerically, but DECP describes **notification** while the notice describes **conclusion**. Agreement does not collapse those meanings into one verified signature date. The notice value is winning-tender PayableAmount, while DECP retains a declared initial amount; tax/scope comparability remains unresolved. No payment, amendment or signed-contract total has been established.

## Newly identified accuracy concern

Three candidate pairings have inconsistent offer counts:

- Printed lot 7: DECP **2**, notice **4**.
- Printed lot 12: DECP **2**, notice **5**.
- Printed lot 20: DECP **2**, notice **3**.

These are genuine disagreements between the retained/live DECP source fields and the exact linked notice statistics under the candidate mapping—not an independently established choice of which source is right. The PDF repeats the notice values. `t-esubm` electronic counts were not substituted for `tenders`; each reported notice total comes from the latter. No existing count was overwritten and no candidate was scored.

Winning-holder organization registration values in the BOAMP notice are unusable placeholders, rather than exact matching SIRETs. A title/holder-name match or amount/date agreement does not repair this identity gap. The six Ministry holder sets are distinct, but their personal/company identifiers are not reproduced in this report or the minimized candidate output.

## Why the unique national row did not resolve the conflict

The cached national parquet contains one exact buyer/procedure row at **456,516.27 EUR**, corresponding to candidate printed lot 1. It does not contain a complete view of this procedure's six source rows. The new award notice shows why preferring that lone national row would misrepresent the other lot contracts. Source uniqueness is not authoritative precedence or procurement completeness.

## Acquisition, privacy and reproducibility

Four new official requests total:

1. Exact Ministry buyer/ID query, limit 100, HTTP 200.
2. BOAMP contract-reference search, limit 5, two results, HTTP 200.
3. BOAMP project/buyer discovery, limit 10, total 15, HTTP 200. This intentionally partial discovery response was not treated as a complete project history and was not used as sole identity evidence. An existing cached relaunch notice 25-33856 concerned a later lot-12 procedure, not the target original award, and was not substituted.
4. Exact award PDF request, HTTP 200, **2,734,764 bytes**.

API responses: 2 MiB cap, 15-second timeout, two-second spacing, no redirects/retries, stop on refusal/rate limit/server failure. PDF: a separately bounded single official request, 10 MiB cap and 15-second timeout, no redirects/retries. The PDF URL follows the publisher's documented eForms endpoint template using the exact record's publication year/month and ID; no unrelated attachment crawl was performed.

Private evidence: `~/.cache/contract-signals/decp-conflict-dijon/`. Requests, responses, UTC retrieval times, byte counts and SHA-256 are retained. Responses/PDF/text contain names and identifiers and must not be committed or served. Minimized lot candidates contain procurement identities and numeric fields but not holder names or identifiers.

PDF SHA-256:

```text
54ecaae5649ff9ede84f576442fd1c40935b01916728c4b939e184d740b0af36
```

Tools:

```sh
# Default is a no-network plan; --fetch performs the three frozen discovery requests.
python tools/fetch-decp-conflict-evidence.py

# Offline candidate and PDF reconciliation; requires private evidence and pypdf.
~/.cache/contract-signals/venv/bin/python tools/reconcile-dijon-conflict.py

python -m unittest discover -s tests -p 'test_*decp_conflict*.py'
python -m unittest discover -s tests -p 'test_reconcile_dijon_conflict.py'
```

The fetcher refuses an existing plan rather than silently rerunning requests. The reconciler uses finite Decimal amounts, validates exact buyer/procedure IDs and relationship uniqueness, and records conflicts rather than declaring candidates verified. Seven reconciliation tests cover insufficient amount-only matching, identity mismatches, duplicate relationships/source rows, offer-statistic conflicts, placeholder holders, PDF notice-version mismatch and zero/nonfinite numeric handling. Four fetcher tests cover fixed scope, private permissions, no repeat requests, refusal/oversize stops and repository-output rejection.

Full repository validation after this investigation: **302 Python tests**, all JavaScript suites and the browser test passed. Test success establishes implementation behaviour, not factual correctness of either publisher.

## Decision and next gate

**Updated 2026-10-08.** Holder linkage is now established, so the identity precondition below is met. Proposed integration, awaiting owner approval and not yet done: split the grouped row into six lot-level rows. Each would keep DECP's own amount, notification date and holder, and carry the notice's printable contract reference (e.g. `2023vdao164207`) and printed lot number as a provenance field. That field is evidence; the DECP `id` itself would not be rewritten. Offers would be null for printed lots 7, 12 and 20, and LOT-0014 would stay excluded. The importer change should handle only this exact buyer/ID pair, or an equally evidenced allow-list. It must not become a global rule of the form "distinct holders ⇒ distinct contracts".

Earlier decision, kept for history:

- **Keep the published grouped row excluded**, with no amount filled and no score computed.
- Record the root-cause explanation as **procedure-ID / lot-contract granularity collision**, with exact notice evidence.
- Retain six separate **private candidate** lot records rather than one invented total. Their field disagreements and unknown holder/tax comparability must remain explicit.
- To integrate them safely, obtain authoritative buyer-profile lot/contract identifiers and holder linkage, or make an explicitly separate BOAMP notice-lot cohort with its own source/basis—not silently rewrite DECP identifiers to invented lot IDs.
- Investigate the three offer-count disagreements against the buyer's original award/notification documents. Do not prefer the larger, smaller or newer number without evidence.

This remains assistant source/document review, not independent expert validation or a finding of wrongdoing.
