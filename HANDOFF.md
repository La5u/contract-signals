# Project handoff

Updated: 2026-09-21

## 1. Current location and intended rename

The working project is currently located at:

```text
/home/lasu/coding/corruption
```

The previously mentioned `/home/lasu/coding/french_corruption` directory does not exist. The directory may be moved before the next session, so the next agent should first run `pwd` and locate this `HANDOFF.md` rather than assuming the old absolute path.

This directory is **not currently a Git repository** (`.git` was not found when checked). Initialize or attach Git only after the user has chosen the final repository name.

The user intends to rename the project before publishing it to GitHub because “corruption” is too accusatory for an evidence and triage tool. Recommended repository name:

```text
procurement-transparency-indicators
```

Other names discussed:

- `public-contracts-observatory`
- `procurement-data-lens`
- `open-contract-indicators`
- `procurement-vigilance`
- `contract-transparency-explorer`

No rename has been performed yet. Confirm the final name with the user before changing internal titles, URLs, or directory names.

## 2. Pending product direction

The next major task is an **English-first presentation**, with the possibility of additional UI languages later.

Requirements already agreed in principle:

- English should become the default interface and documentation language.
- Contract descriptions, procurement notices, official quotations, legal citations, source documents, and PDFs must remain in their original language.
- The source language should be made explicit where useful.
- French legal terminology should not be replaced with an imprecise translation; retain the original term/citation and provide an English explanation.
- UI strings should be centralized for future translation rather than duplicating datasets.
- Avoid “corruption score” terminology. Prefer “procurement vigilance index”, “heuristic indicators”, “review indicators”, “procurement transparency indicators”, or similarly non-accusatory wording.
- Do not start this migration until the user completes any additional request that followed “and also…” in the prior conversation; that thought was unfinished.

A sensible implementation sequence for the next session:

1. Confirm the repository/product name and the unfinished “and also…” requirement.
2. Inventory every user-facing French string in `index.html` and `script.js`.
3. Introduce a small static string dictionary, e.g. `const I18N = { en: {...}, fr: {...} }`, with English default and no framework/build step.
4. Translate interface chrome, methodology summaries, filters, status labels, generated explanations, accessibility labels, and errors.
5. Do **not** translate source fields stored in JSON. Label them as original-language source text.
6. Translate/restructure the README and methodology docs while preserving French-source terminology and links.
7. Add English browser assertions and optional French-language switching tests if a selector is introduced.
8. Retest both HTTP and `file://` operation.

## 3. Project constraints that must remain true

- Vanilla HTML, CSS, and JavaScript only.
- Local JSON only at runtime.
- No backend, database, framework, build step, or runtime API calls.
- Must work over ordinary static HTTP hosting and through the existing `file://` JSON picker.
- Preserve all datasets, sources, PDFs, provenance, unknown values, and non-accusatory framing.
- Never represent missing/not-assessable information as a reassuring zero.
- Do not treat a score as a probability of corruption, illegality, or guilt.
- Do not add points merely for monetary size, an R2122 citation, project membership, a named entity, country reputation, or CPI.
- Avoid double-counting correlated indicators.
- Official findings must remain separate from the heuristic index.
- Keep currencies, legal rules, schemas, and thresholds jurisdiction-specific.
- Do not create unsupported international rankings or combine incomparable currencies/spending totals.
- All imported source wording and documents remain in their original language.

## 4. Current implementation: vigilance index v3.0

The active version is:

```js
const SCORE_VERSION = '3.0';
```

in `script.js`.

Full active methodology: [`docs/score-v3.md`](docs/score-v3.md).

The old v2.1 implementation is frozen solely for reproducibility at:

```text
tools/legacy/scoring-v2.1.js
```

It is not loaded by the site.

### Core v3 semantics

`getAssessment(contract)` returns eight explicit checks. Each check reports:

- applicability: `yes`, `no`, or `unknown`;
- status: `signal`, `clear`, `unknown`, or `not-applicable`;
- family, reason, and any triggered weight.

The returned assessment includes:

- `applicable`
- `evaluated`
- `unknown`
- `unknownApplicability`
- `notApplicable`
- `signals`
- `excludedReason`

`getVigilanceScore(contract)` returns:

- `null` when no control is evaluable; the UI displays **Non évalué**;
- `0` only when at least one check is evaluated and none is triggered;
- otherwise a bounded heuristic score.

Current formula:

```text
min(100, max(competition signals) + max(execution/duration signals))
```

There is no normalization by missingness and no addition of correlated signals within one family.

### Eight active checks

1. Competitive procedure with exactly one declared offer: fixed 12 points.
2. Explicit direct award: fixed 18 points, all amounts.
3. Repeated single-bid competition: graduated 12–40 after sample/coverage safeguards.
4. Supplier concentration: graduated 12–40 after sample/coverage safeguards.
5. Repeated direct awards: graduated 18–60 from 3 to 10 known direct awards.
6. Short bidding period: graduated 8–40 only with a reliable open, non-accelerated chronology.
7. Long declared duration: graduated 8–40 from 120 to 360 months.
8. Comparable relative amount increase: graduated 8–40 above 20% up to 100%, only for explicitly fixed-price DECP history without conflicts.

Thresholds and limitations are documented precisely in `docs/score-v3.md`.

### Explicit removals and separations

- No `amountTier()` effect remains in active scoring.
- Direct award and repeated direct-award checks include all monetary amounts, including unknown amounts.
- The amount-increase check no longer has a €50,000 absolute threshold.
- A single offer is scored only when the procedure is explicitly competitive (`directAward === false`).
- A single offer in a direct award does not add another signal.
- `officialFinding` adds zero heuristic points.
- Official findings remain visible, sourced, filterable, and sortable with a “hors indice” badge.
- R2122 citations remain contextual and add no points.
- Amounts remain visible as financial context but do not amplify the index.
- Aggregate audit findings are not scored as individual contracts.

### Exclusions

The following receive no individual score:

- conflicting initial versions;
- conflicting modification versions;
- duplicate DECP buyer/contract identities;
- `dataStatus: unverified` dossiers;
- aggregate official-audit findings as individual scoring units.

Excluded rows display `null` / “Non évalué”, never zero.

### UI additions

The interface now includes:

- assessment filter: unevaluated/excluded, partial coverage, evaluated zero;
- official-finding filter and dedicated sorting;
- unknown scores always sorted last in ascending and descending score order;
- coverage summary and all eight check states in expanded details;
- separate official-finding badge/panel;
- explicit explanation that monetary stakes and official findings are outside the heuristic score;
- links to the v3 methodology and international pilot documentation.

## 5. Current dataset results

These counts are generated from unchanged source cohorts and recorded in `data/score-v3-review.json`:

| Dataset | Rows | Positive v3 | Evaluated zero | Unevaluated |
| --- | ---: | ---: | ---: | ---: |
| `contracts.json` | 3,010 | 277 | 2,665 | 68 |
| `decp-history.json` | 2,594 | 404 | 1,835 | 355 |
| `decp-cities.json` | 1,270 | 124 | 974 | 172 |
| `consultations.json` | 10 | 0 | 0 | 10 |
| `tours-notices.json` | 66 | 0 | 0 | 66 |

The eight official findings in the main dataset remain available but are not included in positive heuristic counts.

Indicator counts currently recorded:

- Main contracts: 241 single-bid, 28 direct-award, 8 long-contract.
- Paris/Ardèche: 119 single-bid, 262 direct-award, 8 concentration, 28 repeated direct-award, 9 repeated single-bid, 1 long-contract, 24 amount-increase.
- Six cities: 52 single-bid, 66 direct-award, 3 repeated direct-award, 11 repeated single-bid, 4 long-contract, 2 amount-increase.

Do not optimize weights to increase these numbers.

## 6. Sensitivity and review work

Generator:

```text
tools/review-score-v3.cjs
```

Output:

```text
data/score-v3-review.json
```

The report contains:

- SHA-256 hashes of active and frozen scoring code;
- input dataset hashes;
- v2.1-to-v3 transitions;
- v3 category and indicator counts;
- two diagnostic reweighting scenarios;
- Spearman rank correlations with average tie ranks;
- top-20 overlap and cutoff tie counts;
- reproducible review queues selected by SHA-256 of identifiers.

Sensitivity variants multiply competition/execution by 0.8/1.2 and then 1.2/0.8. They are diagnostics only and are not used by the UI. The report explicitly states that this is not statistical validation or comparison to labelled corruption ground truth.

Notable results:

- Main contracts: rank correlations 0.773 and 1.000.
- Paris/Ardèche: 0.9791 and 0.9822; top-20 overlap 18/20 and 17/20.
- Six cities: 0.9578 and 0.9863; top-20 overlap 18/20 and 20/20.
- Ties are substantial; for six cities, 66 rows share the baseline top-20 cutoff score.

Six already-downloaded city excerpts were read as a limited plausibility/counterexample review and documented in `docs/score-v3.md`. This was assistant review, not independent human/legal validation and not labelled ground truth. The JSON queue intentionally says `queued-not-ground-truth`.

Coverage metadata files retain historical snapshots and now have `currentIndex.version: "3.0"` pointers. `data/decp-cities-coverage.json` also has active `indexV3Metrics`. Do not erase historical fields merely because their old counts differ from v3.

## 7. Existing data and source work to preserve

Important files:

```text
data/contracts.json
data/decp-history.json
data/decp-cities.json
data/decp-cities-raw.json
data/consultations.json
data/consultations-raw.json
data/tours-notices.json
data/supplier-identities.json
25-119743-boamp.pdf
Chronologie_marche_2501435.pdf
```

Also preserve all corresponding `*-coverage.json` files and nested raw BOAMP/TED files under `data/`.

### Six-city DECP cohort

- 1,865 raw rows.
- 1,270 normalized buyer/identifier groups.
- 172 ambiguous groups excluded from calculations.
- 365 modification events.
- 100 current public supplier identities selected deterministically from 703 SIRENs.
- Identity data is current public identity, not historical ownership and not evidence of related-party control.

### Tours full-notice cohort

- 27 BOAMP notices.
- 28 TED XML files.
- 25 buyer-verified notices.
- 66 notice/lot rows.
- 25 rows with award criteria.
- 68 criterion entries.
- Two corrections and nine explicit notice/lot links.
- Documentary rows remain “Non évalué” where bidding chronology is not reliably assessable.

### Consultation cohort

- Bounded BOAMP consultation set with correction chronology.
- Conservative short-period eligibility.
- Current ten rows remain unevaluated because chronology completeness/acceleration cannot be established reliably.

## 8. International expansion research

Detailed recommendation:

```text
docs/international-pilots.md
```

Machine-readable HTTP checks:

```text
data/international-access-checks.json
```

Optional checker:

```text
tools/check-international-access.py
```

The checks were small anonymous access tests, not foreign procurement imports. No foreign personal-data rows were retained.

Current recommendation:

1. **Colombia / SECOP II first**: official dataset metadata and a one-row JSON request returned HTTP 200 without a token. Start with three preselected buyers and a common 24-month window. Verify process–contract–supplier joins before claiming proposal/payment indicators.
2. **Paraguay second, conditionally**: DNCP portal and Swagger were accessible, and OCDS routes are documented, but global Bearer security is declared. No real OCDS record was retrieved. Confirm authorized access, license, quotas, and a real OCID first.
3. **Brazil later**: PNCP requests tested returned an error or timed out. Do not claim operational access yet. PNCP, Compras, transparency/payment data, and company data must not be described as already linked.
4. Ukraine’s public Prozorro index and Moldova’s official open-data page were reachable, but local legal/publication context needs further work.
5. A bounded TED cohort in another EU country is the least expensive technical extension, but TED is not complete national procurement or payment coverage.

Do not use CPI to assign contract points or choose a “most corrupt” pilot. International expansion should be based on verified official access, licensing, schema tractability, coverage, and a small reproducible scope.

No foreign country is currently imported into the explorer.

## 9. Tests and last verified state

Last successful commands:

```sh
node --check script.js
node --check tools/review-score-v3.cjs
node --check tools/update-cities-coverage.cjs
node tests/scoring-v3.cjs
node tests/score-review.cjs
node tests/rules.cjs
node tests/cities.cjs
node tests/tours.cjs
python -m unittest discover -s tests -p 'test_*.py'
node tools/review-score-v3.cjs
```

Results:

- 31,032 active v3 assertions passed.
- Review hashes/counts/sensitivity bounds/version pointers passed.
- 124 frozen v2.1 assertions passed.
- 4,835 city-cohort assertions passed.
- 831 Tours assertions passed.
- 17 Python tests passed.

Browser test setup is deliberately outside the project and is not a runtime dependency:

```sh
npm install --prefix /tmp/procurement-browser playwright --no-audit --no-fund
python -m http.server 8765
# in another shell:
node tests/browser.cjs
```

Chromium was available at `/usr/bin/chromium`. The last browser run passed HTTP and `file://` picker operation, city identities, legal/correction panels, assessment filters, eight-check details, official findings outside the score, sorting/grouping, and stationary pagination.

If the directory is moved and `/tmp` has been cleared, reinstall the temporary Playwright package as shown above. Do not add Playwright or Node modules to the static site unless the user explicitly requests repository-managed development dependencies.

After any change to `script.js`, regenerate and verify the hash-bound report:

```sh
node tools/review-score-v3.cjs
node tests/score-review.cjs
```

After changing city scoring/preparation metrics, also run:

```sh
node tools/update-cities-coverage.cjs
node tools/review-score-v3.cjs
```

## 10. Files added or substantially changed during this work

Core/UI/documentation:

- `script.js`
- `index.html`
- `style.css`
- `README.md`
- `docs/score-v3.md`
- `docs/international-pilots.md`

Reports/metadata:

- `data/score-v3-review.json`
- `data/international-access-checks.json`
- coverage JSON files via `currentIndex` pointers

Testing/diagnostics:

- `tests/scoring-v3.cjs`
- `tests/score-review.cjs`
- `tests/rules.cjs`
- `tests/cities.cjs`
- `tests/tours.cjs`
- `tests/browser.cjs`
- `tools/review-score-v3.cjs`
- `tools/update-cities-coverage.cjs`
- `tools/legacy/scoring-v2.1.js`

Preparation/research scripts also changed during prior cohort work:

- `tools/check-international-access.py`
- `tools/download-tours-ted.py`
- `tools/enrich-city-suppliers.py`
- `tools/import-consultations.py`
- `tools/import-decp-cities.py`
- `tools/import-tours-notices.py`
- related Python import/identity tests

## 11. Important cautions for the next agent

- Read `docs/score-v3.md` before changing scoring.
- Do not reintroduce amount tiers or the 50-point official-finding family from v2.1.
- Do not turn unknown procedure type into a competitive procedure.
- Do not turn “no published modification in this extract” into “no amendment”.
- Do not pick one conflicting DECP version arbitrarily.
- Do not describe current supplier identity as historical ownership.
- Do not infer collusion/control from shared names, addresses, or administrators.
- Do not silently translate or normalize legal/source text.
- Do not erase PDFs, raw XML, source variants, provenance URLs, or historical coverage snapshots.
- Keep generated explanations non-accusatory and avoid probability language.
- Preserve `file://` support while implementing English/i18n; loading an external translation file may fail under browser file restrictions, so an embedded/local JavaScript dictionary is safer unless the picker architecture is extended carefully.
- The current repository root has no Git metadata, so there is no `git diff` or commit history available in this checkout.

## 12. Immediate next-session question

Ask the user:

> Which final repository/product name should I use, and what was the remaining requirement after “and also…”?

Then perform the rename/English-first migration without altering original-language procurement evidence.
