# Colombia: indicator checks against criminal convictions — plan (fixed 2026-10-14, before any rate was computed)

Owner request (2026-10-14): repeat the Ukrainian method for Colombia, and accept first-instance convictions as a second, weaker label. Sources: [romania-colombia-label-sources-2026-10-14.md](romania-colombia-label-sources-2026-10-14.md). Research only.

## Labels

- **Final conviction:** casación decided or not admitted, or an ejecutoriada judgment, for interés indebido en la celebración de contratos (CP art. 409), contrato sin cumplimiento de requisitos legales (art. 410), peculado (art. 397), cohecho or concierto para delinquir tied to the contract.
- **First-instance conviction (weaker):** a conviction or plea agreement not yet shown to be final. Reported separately and combined; never mixed silently.
- A contract is labelled when the judgment or an official bulletin names it (number, year, entity) and it resolves to **one** SECOP I record of that entity (NIT) by number and signing year, with the object consistent with the judgment. Ambiguous matches are listed, not used.

## Comparison

All other SECOP I contracts (datos.gov.co `x6v4-i8gf`) of the same entity (NIT) signed in the same year, excluding labelled contracts. Unlabelled, not proven clean. Buyer-weighted rates.

## Checks tested (SECOP I fields)

| ID | Rule |
| --- | --- |
| CO1 direct award | `tipo_de_proceso` is Contratación Directa. |
| CO2 amount increase | `valor_total_de_adiciones` / `cuantia_contrato` > 20 % (the existing editorial threshold elsewhere). |
| CO3 term extension | `tiempo_adiciones_en_dias` + 30 × `tiempo_adiciones_en_meses` > 0. |
| CO4 buyer share | `cuantia_contrato` ≥ 5 % of the entity's SECOP I contract total for that signing year (the Ukrainian R1 rule). |
| CO5 concentration | Same entity and year: the contractor holds ≥ 60 % of ≥ 10 contracts with an identified contractor (the existing rule, by year). |

Method and decision rule as in Ukraine (buyer-weighted hit rates first, LR shrunk toward 1 by a prior worth 10 buyers, buyer-resampled 95 % intervals, points = 10 × log2(LR), no proposal below 10 labelled buyers, buyer-half holdout). Points basis: one contract per case, final and first-instance combined, each label also reported alone. Expected weakness: few cases (tens); results are a check of direction unless intervals are clearly away from 1. Colombian points stay separate from other countries.
