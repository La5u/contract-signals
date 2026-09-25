# Paraguay method — DNCP OCDS checks (v3.0 framework)

**Jurisdiction-specific checks for the Paraguayan DNCP cohorts.** Same vigilance-index framework as [score-v3.md](score-v3.md) and [score-colombia.md](score-colombia.md): two families, family maxima, cap at 100, `null` = “Not assessed”, unknowns never counted as zero. **Different checks, eligibility and thresholds.** French and Colombian rules are never applied to these rows.

This is an editorial sorting tool, not a probability, not a measure of legal gravity and not a certificate of regularity. A signal describes a published declaration in one bounded cohort; it is not a finding of irregularity. No CPI, no country coefficient, no cross-country ranking, no currency conversion (PYG only).

## How the checks were chosen, and what that means

The checks were written on 25 September 2026, **after** reading the field distributions of the first pilot (Fernando de la Mora, 84 rows), and **before** downloading any record of the three-buyer cohort. The pilot's counts are therefore not a blind test of the rules; the three-buyer cohort is the first cohort where the rules were fixed in advance. Thresholds follow the French v3 weights where the concept is the same (single offer 12, award without competition 18, increase >20 %), so that no weight was tuned to a Paraguayan result. None of this is calibrated against labelled cases.

## What never scores

- **Ordinary modalities.** “Menor cuantía”, “Licitación por concurso de ofertas”, “Licitación pública nacional” and ordinary direct contracting add no points by themselves.
- **Declared amounts** (contract, award, amendments, in PYG): visible and sortable, never weighted, converted or summed across rows.
- **The published tender period** (`tenderPeriod.durationInDays`): shown as context. No validated Paraguayan minimum per modality is encoded, so the short-period check stays out of scope.
- **Supplier sanctions, complaints, names and sizes** (the DNCP publishes some of these): outside the index, as everywhere else.
- **Contract period start**: it is not a signature date; `dateSigned` is not published on these rows.

## The eight checks

| Check | ID | Family | Eligibility / trigger | Weight |
| --- | --- | --- | --- | --- |
| Single tenderer in a competitive procedure | `dncp-single-tenderer` | Competition | OCDS `procurementMethod` open / selective / limited; `numberOfTenderers` published and equal to the tenderer list; = 1 | **12**, flat |
| Award by exception to competitive procedure (CVE) | `dncp-exception-award` | Competition | `procurementMethod = direct` and declared modality is a *Contratación por Vía de la Excepción* | **18**, flat |
| Repeated single-tenderer awards to the same supplier | `dncp-repeated-single-tenderer` | Competition | This award is a single-tenderer award; same buyer and supplier RUC won ≥3 distinct processes as the only tenderer | **12 at 3 → 40 at 10**, linear |
| Repeated exception awards to the same supplier | `dncp-repeated-exception` | Competition | This award is a CVE; same buyer and supplier RUC has ≥3 distinct CVE processes | **18 at 3 → 60 at 10**, linear |
| Concentrated awards within a procurement category | `dncp-concentration` | Competition | Same buyer and `mainProcurementCategory` (goods / works / services); ≥10 identified contracts, coverage ≥80 %, supplier share ≥60 % | **12 at 60 % → 40 at 100 %**, linear |
| Declared amount increase | `dncp-amount-increase` | Execution | Sum of published amendment amounts (`amendsAmount`, PYG) over the original contract value; strictly >20 % | **8 near 20 % → 40 at +100 %**, linear |
| Short bidding period | `short-bidding-period` | Competition | **Out of scope**: no validated Paraguayan minimum per modality | — |
| Long declared duration | `long-contract` | Execution | **Out of scope**: no contract end date or duration published | — |

Score = competition maximum + execution maximum, capped at 100, rounded to the tenth.

## Design notes

- **Tenderer counts** come from the process (`tender.numberOfTenderers`), not from an offers table. The count must match the published tenderer list. For a process with several lots, a total above one does not show that each lot had competition, so it stays *unknown*. A total of one means one per lot.
- **Repetition** counts distinct processes (OCIDs), so one process split into several contracts is counted once. Contexts are computed over the whole loaded cohort, before filters.
- **Supplier identity** is the published RUC party ID (`PY-RUC-…`). Names are never used for matching.
- **Amendments.** The DNCP publishes an amount amendment twice: once inside the parent contract (`contracts[].amendments[].amendsAmount`, the increase), and once as a separate contract entry with no award link (`AC-…`). The importer keeps the first and excludes the second, so an increase is never counted as a new award. Amendments without an amount (term, scope) are not monetary and are skipped. An amendment that is not in the record cannot be seen: a clear result is not proof that nothing changed.
- The Paraguayan legal framework (Ley 7021/22 and its regulations) is **not** encoded. No check claims that a threshold is a legal limit.

## Results

### Fernando de la Mora pilot (84 rows; reproduced by `tests/paraguay.cjs`)

| Check | Signals | Clear | Unknown | Out of scope |
| --- | ---: | ---: | ---: | ---: |
| `dncp-single-tenderer` | 34 | 46 | 3 | 1 |
| `dncp-exception-award` | 1 | 0 | 0 | 83 |
| `dncp-repeated-single-tenderer` | 21 | 13 | 3 | 47 |
| `dncp-repeated-exception` | 0 | 1 | 0 | 83 |
| `dncp-concentration` | 0 | 77 | 7 | 0 |
| `dncp-amount-increase` | 0 | 84 | 0 | 0 |

35 rows with a signal, 49 zero after evaluation, 0 not assessed. Almost every process is “Menor cuantía nacional” (open); 34 of 83 competitive awards had one published tenderer, and 21 of those went to a supplier that won at least three processes as the only tenderer. The two published amount amendments are +20.0 % and +19.99 %, evaluated and below the strict >20 % threshold.

### Three-buyer cohort

**Ministerio de Obras Públicas y Comunicaciones** (national, `DNCP-SICP-CODE-20`), **Gobierno Departamental de Central** (departmental, `-81`), **Municipalidad de Asunción** (municipal, `-108`). Announced on 25 September 2026 before download, chosen by level and a reviewable process count; the Ministerio de Educación y Ciencias (3,517 processes) was set aside for volume. Calls published 2024-09-01 → 2026-09-01. 339 processes (149 / 95 / 97; two found under two buyers are counted once), 326 contract entries, **293 retained** (168 / 88 / 37). Excluded: 12 amendment entries (the amendment stays on its parent contract), 21 budget-only entries with no contract ID, and one multi-buyer second-stage process with no single compiled buyer (`ocds-03ad3f-471760`).

| Check | Signals | Clear | Unknown | Out of scope |
| --- | ---: | ---: | ---: | ---: |
| `dncp-single-tenderer` | 51 | 132 | 108 | 2 |
| `dncp-exception-award` | 2 | 0 | 0 | 291 |
| `dncp-repeated-single-tenderer` | 3 | 48 | 108 | 134 |
| `dncp-repeated-exception` | 0 | 2 | 0 | 291 |
| `dncp-concentration` | 0 | 282 | 11 | 0 |
| `dncp-amount-increase` | 0 | 293 | 0 | 0 |

53 rows with a signal (MOPC 10/168, Central 28/88, Asunción 15/37), 240 zero after evaluation, 0 not assessed; 118 rows have at least one unknown check.

- **Multi-lot tenders are the main blind spot.** 92 of the 108 unknown single-tenderer checks are multi-lot processes (mostly MOPC *Licitación Pública Nacional*) with several tenderers in total; the records publish no per-lot count (`bids` appears on 3 of 293 records, `awards.relatedLots` on none). They stay unknown, never clear. The other 16 have no published count.
- **Amount amendments cluster at +20 %.** Of 12 amendments, 6 are exactly +20.0 % and 2 are +19.99 % (others 8.4–18.6 %). This matches the legal ceiling in **Ley 7021/22, Art. 67**: modifications “en ningún caso podrán exceder conjunta o separadamente, el 20 % (veinte por ciento), del monto y plazo originalmente pactados” (official text, [BACN](https://www.bacn.gov.py/leyes-paraguayas/11220/ley-n-7021-de-suministro-y-contrataciones-publicas), read 2026-09-25). DNCP Resolución 230/25 art. 181 reportedly allows a further 20 % for unilateral public-interest changes (Art. 65 b), counted separately, so a total above 20 % is not by itself unlawful; that resolution was not read here. The >20 % threshold was not changed after seeing this.
- **Examples read at the source.** The 2 CVE signals are Asunción insurance cover and rubbish bags, both *CVE con difusión previa* (advertised exceptions; one drew 2 tenderers): routine-looking uses of a lawful route. The 3 repeated single-tenderer signals are one supplier winning 3 Central processes (paving, wooden boats, a greenhouse) as the only tenderer. Zero-scored rows include a 27-tenderer, 10-lot MOPC roadworks call and a 13-tenderer framework agreement. The source category is imperfect (the boats are filed under services), which limits the concentration check.
- Concentration never reached 60 % in any eligible buyer/category group.

## Context outside the index (no points)

- **At the 20 % ceiling** (`dncpAtCeiling`, filter *Legal context → Paraguay · amendments at the 20 % ceiling*): published amendments total 20 % ± 0.05 points of the original amount. 10 contracts (pilot 2, three buyers 8). Reaching the ceiling is lawful; it means no further agreed increase is possible under Art. 67. The law applicable to each process is not verified.
- **Complaints before the DNCP** (`complaints`, filter *Paraguay · complaint or investigation*): 19 contracts (pilot 2, three buyers 17) belong to a process with a recorded protest (*protesta*) or a DNCP investigation opened on a report (*denuncia*). The row shows the case number, kind, step count and dates, whether a closing resolution is recorded, and links to the DNCP resolutions. A complaint is a filing, not a finding; the outcome is only in the resolutions. The names of judges, clerks and complainants published in the source are **not** imported.
- **Debarment in force at the award date** (`sanctionsInForceAtAward`): from a minimised snapshot of the DNCP supplier register (`data/dncp-sanctions.json`, `tools/fetch-dncp-sanctions.py`: RUC, entity type, sanction type/status/description/period; no contacts or raw responses). Only an *INHABILITACION* whose period covers the award date is attached to a contract; warnings (*AMONESTACION*) and sanctions outside the award date are not. On 2026-09-25, 53 of 229 suppliers had some sanction on record (45 debarments, 58 warnings) and **no debarment covered an award date** in either cohort; the closest cases miss by a few weeks.
- **Per-lot competition.** The OCDS data never says how many tenderers each lot had (checked: full record, `/tender/{id}`, `/awards/{id}`; `bids` on 3 of 293 records, without lot links). Every multi-lot award links, under “Verify it yourself”, to its *Cuadro Comparativo de Ofertas* (offers per lot) or *Informe de Evaluación*, so a reviewer can settle the unknown by hand.

## Limits

- Bounded cohorts of a few buyers, selected in advance: not a country sample, no exhaustiveness claim for any buyer's procurement.
- One tenderer can have lawful explanations (a small local market, a specialised good, a correctly advertised call nobody else answered). Read the award page, evaluation report and tenderer list linked on every row.
- Thresholds are editorial and not calibrated against labelled cases. No precision, recall or probability is claimed.

## Reproduction

```sh
python tools/import-paraguay-dncp.py --cohort fernando --offline
python tools/import-paraguay-dncp.py --cohort 3buyers --offline
node tests/paraguay.cjs
python -m unittest discover -s tests -p 'test_*.py'
```

Data provenance: `data/paraguay-dncp-coverage.json`, `data/paraguay-dncp-3buyers-coverage.json`. Earlier documentary pilot notes: [paraguay-pilot.md](paraguay-pilot.md).
