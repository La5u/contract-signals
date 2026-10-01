# Colombia pilot method — SECOP II indicators (v3.0 framework)

**Jurisdiction-specific check set for the SECOP II · Colombia cohort** (three announced buyers, signatures 2024-09-01 → 2026-09-01, 7,560 contracts). Same vigilance-index framework as [score-v3.md](score-v3.md) — two families, family maxima, cap at 100, `null` = “Not assessed”, unknowns never counted as zero — but **different checks, eligibility and thresholds**: French thresholds are not Colombian legal thresholds, and none of them is applied to these rows.

An editorial sorting tool, not a probability, not a measure of legal gravity, not a certificate of regularity. A signal describes a published declaration in this cohort; it is not a finding of irregularity. No CPI, no country coefficient, no cross-country ranking, no currency conversion (COP only).

## What never scores for Colombia

- **The bare declared modality.** The direct-family modalities (Contratación directa, Contratación Directa (con ofertas), régimen especial, Mínima cuantía) represent ≈82 % of this cohort. Ordinary direct contracting — especially professional-services contracts — is legal context, never a signal by itself. (This deliberately differs from the French `direct-award` check: in France an explicit direct award is the signal; in this Colombian cohort the base rate makes the bare modality uninformative.)
- **Ordinary modality justifications**: professional services and management support, interadministrative agreements, minimum-amount rules (presupuesto inferior al 10 % de la menor cuantía), regime statutes (Decreto 092, Regla aplicable, Ley 1150), rental, loan of use, scientific activities. They add zero points.
- **Declared amounts** (contract, paid, invoiced, in COP): visible, searchable, sortable — no weight, no tier, no conversion. Paid/invoiced values are platform declarations, not audited payments, and are never summed.
- **Official statuses** (estado_contrato, liquidación, suspensión), supplier names, SME/group flags, post-conflict and reversion flags: context only.
- **Official findings, sanctions, CPI, project membership, personal identifiers**: outside the index, as everywhere else.
- The three French checks that need fields this extract does not contain (see below).

## The eight checks

Eight checks are always displayed. Five are jurisdiction-specific; three are the French checks kept **out of scope** with an explicit reason — never silently dropped, never scored.

| Check | ID | Family | Eligibility / trigger | Weight |
| --- | --- | --- | --- | --- |
| Award declared without supplier plurality or under manifest urgency | `secop2-plurality-award` | Competition | Declared modality in the direct family; published justification is exactly “No existe pluralidad de oferentes en el mercado” or “Urgencia manifiesta” | **18**, flat, all amounts |
| Repeated awards declared without supplier plurality | `secop2-repeated-plurality` | Competition | This contract is in the avoidance-justified set; same buyer (NIT) and same supplier document (Cédula/NIT) has ≥3 such awards in the cohort | **18 at 3 → 60 at 10**, linear |
| Concentrated awards within a contract type | `secop2-concentration` | Competition | Single identified holder; same buyer and contract type; group ≥10 identified contracts, coverage ≥80 %, this holder’s share ≥60 % | **12 at 60 % → 40 at 100 %**, linear |
| Long declared duration | `secop2-long-duration` | Execution/duration | Published `duraci_n_del_contrato` parses to months ≥36 | **8 at 36 months → 40 at 120 months**, linear |
| Single offer in a competitive procedure | `single-bid` | Competition | **Not applicable**: no offers/proposals table in this extract | — |
| Short bidding period | `short-bidding-period` | Competition | **Not applicable**: no publication–deadline chronology | — |
| Declared term more than doubled by extensions | `secop2-term-extension` | Execution/duration | Published `dias_adicionados` divided by the declared term (`duraci_n_del_contrato` in days) strictly above +100 % | **8 at +100 % → 40 at +300 %**, linear |
| Repeated low competition | `repeated-single-bid` | Competition | **Not applicable**: depends on offer counts, absent here | — |

Score = competition maximum + execution/duration maximum, capped at 100, rounded to the tenth. `null` only when no check can be evaluated; `0` requires at least one evaluated check with no threshold crossed.

## Term extension (added 2026-09-26)

SECOP II publishes `dias_adicionados`, the days added to the contract term, on every row (1,552 of 7,560 are above zero). The check divides it by the declared term in days (months × 30.4375) and signals **strictly above +100 %**, i.e. a term more than doubled, from 8 points to 40 at +300 %, in the execution/duration family (so it is not added to a long-duration signal on the same row). Amount additions (*adiciones*) are not published in this extract and remain out of scope.

- **The published end date is not used.** Among extended contracts, 567 end dates equal start + declared term + days added, but 819 equal start + declared term only: the end date is often not updated after an extension. `dias_adicionados` is taken as published.
- **Why +100 %.** 1,002 extensions are at or below +50 %, including a cluster of professional-services contracts extended by exactly 50 %; 200 fall between +50 % and +100 %; 57 are above +100 %. The threshold is editorial, chosen after reading this distribution and flagged and unflagged examples; it is not a Colombian legal limit (Ley 80 caps value additions at 50 %, not term extensions).
- **Examples read.** Flagged: an architect's professional-services contract of 12 days extended by 90 (+739 %), institutional rain jackets supplied over 2 months extended by 397 days (+652 %), two La Merced interadministrative agreements (+510 %, +382 %), road *interventorías* and works in Caldas (+246 % to +375 %). 41 of 57 are Gobernación de Caldas contracts, 19 carry the public-to-public context label. Unflagged near-misses: many 6- and 7-month professional-services contracts at exactly +50 %, and Caldas agreements with municipalities at +93 % to +99 %.
- An extension can be lawful and necessary (weather, design changes, the budget calendar); the signal says the published timetable changed substantially, not why.

## Notes on the design
## Notes on the design

- **Justifications that declare competition avoidance** (non-plurality of suppliers, manifest urgency) are structured modality-declaration fields — the buyer’s published answer to “why this modality?”. The signal is the declared absence of ordinary competition conditions, not the citation of a legal article. This is distinct from the French treatment of R2122 citations, which remain context without points in the French cohorts (unchanged). Legal validity of a Colombian justification is not assessed.
- **Duration** is parsed read-only from the published free text (`6 Mes(es)`, `345 Dia(s)`, `12 Semana(s)`, `5 Año(s)`); the extract text is never rewritten. Durations in hours or anything else stay unknown, not zero. No renewal is invented. 36 months is an editorial cutoff for a cohort where durations of 6–12 months are ordinary; it is not a Colombian legal threshold.
- **Concentration and repetition contexts** are computed over the whole loaded cohort before any filter, like the French contexts. Supplier identity uses a usable typed document identifier (never names); seven published `No Definido` placeholders are treated as unknown, not as a shared supplier. Different document types cannot collide. No SIREN/SIRET matching is involved.
- **No French field is synthesized**: no `offers`, no `directAward` boolean, no CPV, no SIRET, no `priceType`. Where they are missing, the corresponding check is out of scope with a reason.

## Results on the pilot cohort (reproduced by `tests/colombia.cjs`)

| Check | Signals | Clear | Unknown | Out of scope |
| --- | ---: | ---: | ---: | ---: |
| `secop2-plurality-award` | 176 | 7,161 | 0 | 223 |
| `secop2-repeated-plurality` | 15 | 161 | 0 | 7,384 |
| `secop2-concentration` | 0 | 7,490 | 70 | 0 |
| `secop2-long-duration` | 39 | 7,520 | 1 | 0 |
| `secop2-term-extension` | 57 | 7,500 | 3 | 0 |
| three French out-of-scope checks | 0 | 0 | 0 | 7,560 each |

- Rows with at least one signal: **272** (score > 0); zero after evaluation: **7,288**; not assessed: **0**; partial coverage (≥1 unknown): **73**. The term-extension check (added 2026-09-26) accounts for 57 of these rows; before it, 215 rows were flagged.
- The ≈82 % ordinary direct/professional-services rows score **0 or a duration-only score** — the bare modality never fires.
- Max observed concentration share in an eligible buyer/contract-type group: 31.3 % — below the 60 % entry threshold; the check is evaluated, not absent.
- These counts are cohort descriptions, not target proportions. No tuning was done to reach them; changing the cohort would change them.

## Context outside the index (no points)

**Public-to-public agreement** (`secop2PublicCounterparty`, filter *Legal context → Colombia · public-to-public agreement*, row note “Context · public-to-public agreement · no points”). The label changes no index value and excludes no row; it tells a reader that a row near the top of the ranking is an agreement between public bodies, where a long duration or a direct modality is ordinary.

SECOP II publishes no field for the counterparty's legal nature (checked on all 85 raw fields: no public/private flag; `tipodocproveedor` is NIT for companies and public bodies alike). The positive evidence is therefore always a **published declaration**; a name never grants the label.

1. **Declared interadministrative agreement** — the published `justificacion_modalidad_de` is exactly “Contratos o convenios Interadministrativos (con valor)” or “Contratos o convenios Interadministrativos (valor cero)”: the buyer declares a contract with another public entity. 569 rows declare it; **436 are labelled**.
2. **Comodato or empréstito with a public counterparty** — contract type or justification “Comodato”, “Prestamo de uso” or “Operaciones de Crédito Público”, **and** the counterparty's typed document (exact match, as in the other Colombian contexts) is the counterparty of a labelled interadministrative agreement elsewhere in the cohort, so a buyer has declared it public. **6 rows**: five municipalities receiving a comodato from the Gobernación de Caldas and one empréstito from INFICALDAS.

The label is **withheld** on a declared interadministrative agreement when published fields contradict the declaration: the counterparty holds a personal identity document (Cédula de Ciudadanía/Extranjería, 3 rows) or its published name designates a community body, a *junta de acción comunal* or similar (pattern `acción comunal`, `desarrollo comunal`, or a name starting with `JAC` or `Junta`; 130 rows). Juntas de acción comunal are community organisations (Ley 2166 de 2021), not public entities; the Gobernación de Caldas files many of its road-maintenance agreements with them under this justification. The row detail says why the label is withheld.

**Result: 442 rows labelled** (436 + 6), of which **28 have a positive index** (out of 272; 19 of them through the term-extension check). The label reaches the top of the ranking only in part: of the ten rows at 40, three are labelled (the INFICALDAS empréstito and two La Merced agreements).

**Precision review** (assistant's reading of the published counterparty names, not an independent or legal review). All 442 labelled rows, by counterparty: about **382 public bodies** (municipalities, universities, ministries and agencies, ICETEX, state companies); **27 uncertain** (indigenous authorities such as *cabildos* and *resguardos*, which have a special public status, and mixed-economy funds or corporations such as PROPAIS or Fondo Mixto Cartago); **33 private or foreign** (for example People Contact S.A.S. and Promueve Más S.A.S., private universities, the Cámara de Comercio and the Federación Nacional de Cafeteros, associations and foundations, the French embassy and a UN office). That is roughly 86 % public, 93 % counting the uncertain group. These false positives come from the buyer's declaration and are kept, because no published field refutes them; the label says the public status is the buyer's declaration.

**Near-misses, not labelled** (reviewed): the INFIMANIZALES empréstito (40 points), the two comodatos to the Asamblea Departamental de Caldas, and a comodato to “Dirección Regional Viejo Caldas N° 6” are public-looking counterparties that never appear in a declared interadministrative agreement (false negatives of the rule). A comodato to the Cuerpo de Bomberos Voluntarios de Anserma (40 points) and the 16 Usaquén comodatos to juntas de acción comunal are correctly unlabelled. One Universidad Pedagógica Nacional contract describes itself as “CONTRATO INTERADMINISTRATIVO” but is declared under “No existe pluralidad de oferentes en el mercado” (18 points); the declared justification wins.

**Not covered**: 74 road-maintenance agreements (*Conservación Rutinaria Manual*), 70 of them with juntas de acción comunal, declared under “No existe pluralidad de oferentes en el mercado” score 18 each and fill much of the Colombian ranking below the top rows. They are community agreements, not public-to-public, and are left for a separate decision.

## Limits

- Three buyers, 24 months: not a country. No exhaustiveness claim for either buyer’s procurement.
- No offers table, no payment reconciliation, no proposals: competition is read only through declared modalities and justifications, never through offer counts.
- A lawful ground may underlie any signal; a zero or an unflagged row proves nothing. Flagged **and** unflagged examples must be read in the source (`processUrl` on every row).
- Thresholds are editorial and were chosen from the field semantics and this cohort’s structure, not calibrated against labelled ground truth. No precision, recall or probability is claimed.

## Reproduction

```sh
python tools/import-colombia-secop2.py --offline   # re-normalize from the raw snapshot
node tests/colombia.cjs                            # exact counts above
node tools/review-score-v3.cjs                     # after any script.js change (French datasets)
node tests/score-review.cjs
python -m unittest discover -s tests -p 'test_*.py'
node tests/browser.cjs                             # own server on a free port, test-only Playwright
```

French method: [score-v3.md](score-v3.md). Country order and access checks: [international-pilots.md](international-pilots.md).
