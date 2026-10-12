# Bounded current official-source amount recheck

## Result and scope

On 2026-10-07 UTC, an authorized check compared three current official responses with the offline review queue. A private plan selected the first full published ID in each stratum: BOAMP missing, BOAMP zero and Colombia zero.

| Preregistered stratum | Planned | HTTP 200 / compared | Current missing | Current zero | Positive candidates | Identity conflicts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BOAMP: retained source missing | 1 | 1 | 1 | 0 | 0 | 0 |
| BOAMP: retained source zero | 1 | 1 | 0 | 1 | 0 | 0 |
| Colombia: retained source zero | 1 | 1 | 0 | 1 | 0 | 0 |
| **Total** | **3** | **3** | **1** | **2** | **0** | **0** |

All three requests succeeded. No planned row was left unchecked, no identity conflict occurred, and no positive recovery candidate was found. Published data was unchanged.

## Method and reproduction

`tools/recheck-amount-gaps.py` freezes `plan.json` without network activity by default; only `--fetch` enables requests. Full IDs, evidence and request URLs stay in `~/.cache/contract-signals/current-amount-recheck/`.

- BOAMP Explore records API: exact `idweb`, limit **2**. Match notice, lot, contract, result and original winning tender; read only that tender's `PayableAmount`.
- Colombia datos.gov.co dataset `jbjy-vk9h`: exact full `contractId`, limit **2**. Select `id_contrato`, `proceso_de_compra`, `valor_del_contrato`, `estado_contrato`; require unique contract/process matches. Basis: SECOP contract value in COP.
- Limits: **3 requests**, serial, **2 seconds** between completed attempts, **15-second** timeout and **2 MiB** cap. Reject responses reaching the cap. No redirects or retries; stop on non-200, transport/parsing failure or identity ambiguity, without replacing rows.
- Private directories/files: **0700/0600**, checked on the fetched run. Retain response bytes, UTC retrieval, URL, byte count, hash and comparison. A future positive result is a research candidate, not an automatic correction.

## Limits and validation

This three-row check is not representative. Current responses need not reconstruct historical publication. Missing and zero are separate; neither establishes economic value. BOAMP payable is not verified signed-contract value, and SECOP contract value is not payment or execution value. Linked notices, amendments and attachments were outside scope.

`docs/data-sources.md` records BOAMP Licence Ouverte 2.0 and Colombia CC BY-SA 4.0; these do not clear all personal-data or incorporated-content issues.

**7 recheck tests and 11 offline-review tests passed**, covering selection, exact identity/currency/basis, candidate handling, error stops and request/privacy limits. Both the no-network plan and live run completed.
