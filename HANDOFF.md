# Project handoff

Updated: 2026-09-22 (Colombia indicators implemented; importer liquidation bug fixed; Paraguay anonymous access validated)

## 1. Location, name and repository — RESOLVED

The working project is at:

```text
/home/lasu/coding/contract-signals
```

- The user confirmed the final repository/product name: **`contract-signals`** (the directory rename was intentional). The handoff’s earlier candidates are obsolete.
- Git is on branch `main`; history starts at root commit `55da263` (English migration + repo init), then `0cbc9eb` (handoff refresh), `723289f`, `68db765`, `e4a24b4` (Colombia pilot). An earlier handoff cited SHAs `aab438f`/`718e4fd` that no longer exist (history was rewritten) — ignore them.
- **Published**: remote `origin = git@github.com:La5u/contract-signals.git`, `main` pushed and tracking (SHA-verified). No `gh` CLI on this machine; pushes go through the SSH remote.
- `HANDOFF.md` itself is committed; update it as work continues.

## 2. Product direction — English-first migration COMPLETE

Decisions confirmed by the user on 2026-09-21:

- **English-only static UI.** No French toggle and **no `I18N` dictionary** — strings were translated in place. If a second UI language is ever wanted, a dictionary extraction will be needed; until then do not re-add French chrome.
- The “and also…” item from the previous session was resolved as **nothing pending**.
- Original-language evidence is preserved everywhere: contract descriptions, notices, buyer explanations, citations, source PDFs and **dataset-embedded provenance text** (e.g. `notes`, `consultation.exclusions`, `identifierNote` inside the JSONs) remain French by design. Do not “fix” those.
- `'Définitif ferme'` in `script.js` is a **data schema value comparison** (DECP `priceType`), not UI text — it must stay French or scoring breaks.
- Locales switched to English: `Intl.Collator('en')`, money `en-IE` EUR, dates `en-GB` UTC, `toLocaleLowerCase('en')` for severity labels.
- Non-accusatory terminology kept: “vigilance index”, “Not assessed ≠ zero”, “outside the index”, no probability language.

## 3. Project constraints (unchanged, still binding)

- Vanilla HTML/CSS/JS only; local JSON only; no backend, framework, build step or runtime API calls.
- Must work over static HTTP **and** the `file://` JSON picker.
- Never represent unknowns as zero; the index is editorial, not a probability or gravity measure.
- No points for amounts, R2122 citations, project membership, names, country reputation or CPI; no summing of correlated signals within a family; official findings stay outside the index.
- Jurisdiction-specific thresholds; no international rankings or currency mixing.
- Preserve PDFs, raw XML, provenance, historical coverage snapshots and `tools/legacy/scoring-v2.1.js`.

## 4. Active implementation: vigilance index v3.0

Unchanged by the migration. `SCORE_VERSION = '3.0'` in `script.js`; method in `docs/score-v3.md` (now English). Eight checks, `min(100, max(competition) + max(execution/duration))`, `null` = “Not assessed”, exclusions for conflicting versions, duplicate identities, `unverified` records and aggregate audit findings. `tools/legacy/scoring-v2.1.js` stays frozen and unloaded.

`data/score-v3-review.json` was **regenerated** after the translation to re-bind the `script.js` SHA-256. Counts are identical to the pre-migration run, proving no scoring perturbation:

| Dataset | Rows | Positive v3 | Zero | Not assessed |
| --- | ---: | ---: | ---: | ---: |
| `contracts.json` | 3,010 | 277 | 2,665 | 68 |
| `decp-history.json` | 2,594 | 404 | 1,835 | 355 |
| `decp-cities.json` | 1,270 | 124 | 974 | 172 |
| `consultations.json` | 10 | 0 | 0 | 10 |
| `tours-notices.json` | 66 | 0 | 0 | 66 |

Sensitivity numbers in the report/docs are unchanged (Spearman 0.773–1.000 by dataset/scenario; documented ties, e.g. 66 rows at the six-cities top-20 cutoff).

## 5. Tests — last verified state (all green, 2026-09-22)

```sh
node --check script.js
node --check tools/review-score-v3.cjs
node --check tools/update-cities-coverage.cjs
node tests/scoring-v3.cjs    # 31,032 assertions
node tests/score-review.cjs  # hashes/counts/sensitivity/version pointers
node tests/rules.cjs         # 124 frozen v2.1 assertions
node tests/cities.cjs        # 4,835 assertions
node tests/tours.cjs         # 831 assertions
node tests/colombia.cjs      # 181,492 assertions: cohort, join, Colombian indicators
python -m unittest discover -s tests -p 'test_*.py'  # 26 tests (incl. 9 Colombia importer regressions)
node tools/review-score-v3.cjs  # regenerate after any script.js change
```

Browser suite (updated to English string assertions) passed for HTTP and `file://`, including city profiles, legal/correction panels, assessment filters, eight-check details, official findings, sorting/grouping, stationary pagination:

```sh
python -m http.server 8765 &
node tests/browser.cjs
```

Playwright is test-only in `/tmp/procurement-browser` (still installed; Chromium at `/usr/bin/chromium`). Reinstall per the README if `/tmp` was cleared. Never add it to the static site.

**After changing `script.js`:** run `node tools/review-score-v3.cjs` then `node tests/score-review.cjs`. After city scoring/metrics changes also `node tools/update-cities-coverage.cjs`.

## 6. Files changed by the migration and the Colombia work

- `index.html` — full English rewrite (same ids/structure); 2026-09-22: international eyebrow/subtitle, four SECOP II indicator filter options, Colombia method paragraph in the method panel.
- `script.js` — all user-facing strings, dataset notes, errors, validation messages, CPV sector names translated; locales switched; `'Définitif ferme'` and proper nouns kept. 2026-09-22: `getAssessmentSecop2` + constants/parser, secop2 contexts in `prepareContracts`, updated Colombia dataset note/detail panel/completeness duration count.
- `README.md`, `docs/score-v3.md`, `docs/international-pilots.md` — English translations preserving counts, links, archive framing; 2026-09-22: Colombia scoring sections, run lists, raw-size fix (28 MB not 43 MB).
- `docs/score-colombia.md` — **new**: Colombian method, thresholds, exact counts, limits.
- `tests/browser.cjs` — assertions now match English UI strings (`/Not assessed/`, `/unknown applicabilities/`, `/No points added/`, `/Current public identity — not historical/`, `/not assessable/`, `/lots other than/`, `/outside the index/`, `/Official finding · outside the index/`, `/172 ambiguous/`); 2026-09-22: Colombia block asserts 215 flagged / 0 not assessed / 7,345 zero / indicator filter 176 / eight checks in the detail panel.
- `tests/colombia.cjs` — rewritten for the indicator set (181,492 assertions).
- `tests/score-review.cjs` — added `colombia-secop2-coverage` to the version-pointer list.
- `tests/test_import_colombia_secop2.py` — **new**: 9 importer regressions (liquidaci_n, ids, amounts, dates, counts).
- `tools/import-colombia-secop2.py` — `liquidaci_n` fix, `liquidation_counts`, `indicators` block in coverage, updated limitations/currentIndex/duration notes.
- `tools/check-international-access.py` — Paraguay OCDS record/search probes; optional label-substring CLI filter.
- `data/colombia-secop2.json`, `data/colombia-secop2-coverage.json` — regenerated (liquidation populated; indicators metadata).
- `data/score-v3-review.json` — regenerated (new script hash; French counts unchanged).
- `data/international-access-checks.json` — appended Paraguay probes.
- `.gitignore` — new (`__pycache__/`, `*.pyc`, OS cruft).

## 7. International expansion — COLOMBIA SCORED; NEXT IS PARAGUAY VALIDATION

**Colombia/SECOP II (import 2026-09-22, indicators same day):** first international cohort. Three buyers announced before download (MEN national / Gobernación de Caldas departmental / Alcaldía Local de Usaquén municipal-local), 7,560 rows, 24-month signature window, raw pages under `data/colombia-secop2/raw/` (28 MB), extract 15 MB, coverage with `joinVerification` (100 % intra-row join) and `counts.liquidation` (Si 1,542 / No 6,018). Spanish verbatim, COP only, no conversion. Licence CC BY-SA 4.0 verified.

**Colombian indicators (implemented 2026-09-22):** method `docs/score-colombia.md`, code branch in `getAssessmentSecop2` (`script.js`). Four checks, v3.0 framework, **jurisdiction-specific thresholds**: `secop2-plurality-award` (18 flat; justification ∈ {No existe pluralidad de oferentes, Urgencia manifiesta} on a direct-family modality — **the bare “Contratación directa” ≈82 % base never fires**), `secop2-repeated-plurality` (same buyer NIT + supplier document, ≥3 such awards → 18..60), `secop2-concentration` (buyer + contract type, ≥10 known, ≥80 % coverage, share ≥60 % → 12..40; **0 signals**, max observed share 31.3 %), `secop2-long-duration` (published free text parsed read-only, ≥36 months → 8..40). The four French offer/timetable/history checks are **out of scope with reasons** (no offers table, no chronology, no amendment history) so every row still shows exactly 8 checks. Cohort totals: **215 flagged / 7,345 zero / 0 not assessed / 56 partial**; fires 176 / 15 / 0 / 39. French datasets untouched (review counts identical: 277/404/124/0/0). Importer bug fixed en route: `liquidación` → `liquidaci_n` (was null on all rows; now tested by `tests/test_import_colombia_secop2.py`). Extract + coverage regenerated via `--offline`.

**Paraguay access validated (2026-09-22):** despite the Swagger’s global Bearer declaration, three data routes answered **HTTP 200 without a token** — `/ocds/record/ocds-03ad3f-365292-1` (full OCDS 1.1 record package), date-filtered `/search/processes` (one row), and `/parameters/parameters` (100 entries). Payload licence **CC BY 4.0**, publisher DNCP, policy `/datos/legal`. **Correct base path is `/datos/api/v3/doc` (Swagger `basePath`), not `/datos/api/v3`.** Search requires at least one filter (`page`/`items_per_page` are not enough). Probes: `python tools/check-international-access.py Paraguay` (label-substring filter). **Still open before import:** quotas/exhaustiveness of national history, rate limits, then one bounded buyer cohort with Paraguayan indicators (never a French/Colombian transplant). **Brazil** stays blocked (PNCP access not established). Ukraine/Moldova/TED-EU remain lighter options. Checks log: `data/international-access-checks.json`. No CPI-driven selection, ever.

## 8. Cautions carried forward

- Read `docs/score-v3.md` before touching French scoring; do not reintroduce amount tiers, the 50-point finding family, or “unknown procedure ⇒ competitive”.
- Read `docs/score-colombia.md` before touching Colombian scoring; do not apply French thresholds to `secop2` rows, never turn the bare direct-family modality into a signal, never score amounts.
- Do not translate/normalize legal or source text; do not erase PDFs, raw XML, provenance or historical coverage snapshots.
- Dataset-embedded French strings surface in the UI (e.g. Tours `notes`, `exclusions`) — that is intended provenance display, not a missed translation.
- The browser test regex `/lots other than/` depends on the exact English wording of the notice-evidence panel; keep them in sync.
- Commit convention: single-purpose commits; the root commit message documents the migration.
- **No AI-attribution trailers, ever.** Commits must not contain AI-tool attribution trailers (“Generated with …”, “Co-Authored-By: <AI tool>”) or any equivalent. A permanent global `commit-msg` hook at `~/.config/git/hooks/commit-msg` (via `core.hooksPath`) blocks such trailers in every repo of this machine — do not remove or bypass it, and never add agent attributions to commit messages, authorship, READMEs or docs.

## 9. Next steps for the next session

1. ~~Publish to GitHub~~ — **done** (`git@github.com:La5u/contract-signals.git`, pushed 2026-09-21).
2. ~~Colombia SECOP II pilot~~ — **imported** (see section 7). ~~Design jurisdiction-specific Colombian indicators~~ — **implemented** (`docs/score-colombia.md`; 215 flagged / 7,345 zero / 0 not assessed). Remaining Colombia work: examine flagged **and unflagged** examples in the sources before any threshold change; offers/proposals and payment-reconciliation verification before any attrition/payment indicator.
3. ~~Paraguay access validation~~ — **done (2026-09-22)**: record/search/parameters all HTTP 200 anonymously; base path `/datos/api/v3/doc`; licence CC BY 4.0. Next for Paraguay: quotas/exhaustiveness, then design one bounded buyer cohort and Paraguayan indicators (nothing imported yet). Brazil re-consultation when convenient (record in the checks log; a first 200 would invalidate the current “access not established” pin in `tests/score-review.cjs` — update docs together with it).
4. If a French UI is ever requested again, plan a proper string-extraction pass first (no dictionary exists yet).
