# Colombia pilot method — SECOP II indicators (v3.0 framework)

**Jurisdiction-specific check set for the SECOP II · Colombia cohort** (three announced buyers, signatures 2024-09-01 → 2026-09-01, 7,560 contracts). Same vigilance-index framework as [score-v3.md](score-v3.md) — two families, family maxima, cap at 100, `null` = “Not assessed”, unknowns never counted as zero — but **different checks, eligibility and thresholds**: French thresholds are not Colombian legal thresholds, and none of them is applied to these rows.

An editorial sorting tool, not a probability, not a measure of legal gravity, not a certificate of regularity. A signal describes a published declaration in this cohort; it is not a finding of irregularity. No CPI, no country coefficient, no cross-country ranking, no currency conversion (COP only).

## What never scores for Colombia

- **The bare declared modality.** The direct-family modalities (Contratación directa, Contratación Directa (con ofertas), régimen especial, Mínima cuantía) represent ≈82 % of this cohort. Ordinary direct contracting — especially professional-services contracts — is legal context, never a signal by itself. (This deliberately differs from the French `direct-award` check: in France an explicit direct award is the signal; in this Colombian cohort the base rate makes the bare modality uninformative.)
- **Ordinary modality justifications**: professional services and management support, interadministrative agreements, minimum-amount rules (presupuesto inferior al 10 % de la menor cuantía), regime statutes (Decreto 092, Regla aplicable, Ley 1150), rental, loan of use, scientific activities. They add zero points.
- **Declared amounts** (contract, paid, invoiced, in COP): visible, searchable, sortable — no weight, no tier, no conversion. Paid/invoiced values are platform declarations, not audited payments, and are never summed.
- **Official statuses** (estado_contrato, liquidación, suspensión), supplier names, SME/group flags, post-conflict and reversion flags: context only.
- **Official findings, sanctions, CPI, project membership, personal identifiers**: outside the index, as everywhere else.
- The four French checks that need fields this extract does not contain (see below).

## The eight checks

Eight checks are always displayed. Four are jurisdiction-specific; four are the French checks kept **out of scope** with an explicit reason — never silently dropped, never scored.

| Check | ID | Family | Eligibility / trigger | Weight |
| --- | --- | --- | --- | --- |
| Award declared without supplier plurality or under manifest urgency | `secop2-plurality-award` | Competition | Declared modality in the direct family; published justification is exactly “No existe pluralidad de oferentes en el mercado” or “Urgencia manifiesta” | **18**, flat, all amounts |
| Repeated awards declared without supplier plurality | `secop2-repeated-plurality` | Competition | This contract is in the avoidance-justified set; same buyer (NIT) and same supplier document (Cédula/NIT) has ≥3 such awards in the cohort | **18 at 3 → 60 at 10**, linear |
| Concentrated awards within a contract type | `secop2-concentration` | Competition | Single identified holder; same buyer and contract type; group ≥10 identified contracts, coverage ≥80 %, this holder’s share ≥60 % | **12 at 60 % → 40 at 100 %**, linear |
| Long declared duration | `secop2-long-duration` | Execution/duration | Published `duraci_n_del_contrato` parses to months ≥36 | **8 at 36 months → 40 at 120 months**, linear |
| Single offer in a competitive procedure | `single-bid` | Competition | **Not applicable**: no offers/proposals table in this extract | — |
| Short bidding period | `short-bidding-period` | Competition | **Not applicable**: no publication–deadline chronology | — |
| Relative increase in declared amount | `amount-increase` | Execution | **Not applicable**: no published amendment history with comparable amounts | — |
| Repeated low competition | `repeated-single-bid` | Competition | **Not applicable**: depends on offer counts, absent here | — |

Score = competition maximum + execution/duration maximum, capped at 100, rounded to the tenth. `null` only when no check can be evaluated; `0` requires at least one evaluated check with no threshold crossed.

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
| four French out-of-scope checks | 0 | 0 | 0 | 7,560 each |

- Rows with at least one signal: **215** (score > 0); zero after evaluation: **7,345**; not assessed: **0**; partial coverage (≥1 unknown): **71**.
- The ≈82 % ordinary direct/professional-services rows score **0 or a duration-only score** — the bare modality never fires.
- Max observed concentration share in an eligible buyer/contract-type group: 31.3 % — below the 60 % entry threshold; the check is evaluated, not absent.
- These counts are cohort descriptions, not target proportions. No tuning was done to reach them; changing the cohort would change them.

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
node tests/browser.cjs                             # server on 8765, test-only Playwright
```

French method: [score-v3.md](score-v3.md). Country order and access checks: [international-pilots.md](international-pilots.md).
