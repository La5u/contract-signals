# Project handoff

Updated: 2026-09-21 (evening — after the English-first migration)

## 1. Location, name and repository — RESOLVED

The working project is at:

```text
/home/lasu/coding/contract-signals
```

- The user confirmed the final repository/product name: **`contract-signals`** (the directory rename was intentional). The handoff’s earlier candidates are obsolete.
- Git is now **initialized on branch `main`** with a root commit `aab438f` (migration) and `718e4fd` (handoff refresh). Working tree is clean.
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

## 5. Tests — last verified state (all green, 2026-09-21)

```sh
node --check script.js
node --check tools/review-score-v3.cjs
node --check tools/update-cities-coverage.cjs
node tests/scoring-v3.cjs    # 31,032 assertions
node tests/score-review.cjs  # hashes/counts/sensitivity/version pointers
node tests/rules.cjs         # 124 frozen v2.1 assertions
node tests/cities.cjs        # 4,835 assertions
node tests/tours.cjs         # 831 assertions
python -m unittest discover -s tests -p 'test_*.py'  # 17 tests
node tools/review-score-v3.cjs  # regenerate after any script.js change
```

Browser suite (updated to English string assertions) passed for HTTP and `file://`, including city profiles, legal/correction panels, assessment filters, eight-check details, official findings, sorting/grouping, stationary pagination:

```sh
python -m http.server 8765 &
node tests/browser.cjs
```

Playwright is test-only in `/tmp/procurement-browser` (still installed; Chromium at `/usr/bin/chromium`). Reinstall per the README if `/tmp` was cleared. Never add it to the static site.

**After changing `script.js`:** run `node tools/review-score-v3.cjs` then `node tests/score-review.cjs`. After city scoring/metrics changes also `node tools/update-cities-coverage.cjs`.

## 6. Files changed by the migration

- `index.html` — full English rewrite (same ids/structure).
- `script.js` — all user-facing strings, dataset notes, errors, validation messages, CPV sector names translated; locales switched; `'Définitif ferme'` and proper nouns kept.
- `README.md`, `docs/score-v3.md`, `docs/international-pilots.md` — English translations preserving counts, links, archive framing.
- `tests/browser.cjs` — assertions now match English UI strings (`/Not assessed/`, `/unknown applicabilities/`, `/No points added/`, `/Current public identity — not historical/`, `/not assessable/`, `/lots other than/`, `/outside the index/`, `/Official finding · outside the index/`, `/172 ambiguous/`).
- `data/score-v3-review.json` — regenerated (new script hash).
- `.gitignore` — new (`__pycache__/`, `*.pyc`, OS cruft).

## 7. International expansion (unchanged, next workstream)

Recommendation order stands: **Colombia/SECOP II first** (verified anonymous HTTP 200, `CC_40_BY_SA`), Paraguay conditionally (Bearer security declared; no real OCID yet), Brazil later (PNCP access not established), Ukraine/Moldova/TED-EU as lighter options. Details: `docs/international-pilots.md` (English), checks: `data/international-access-checks.json`, checker: `tools/check-international-access.py`. No foreign country imported yet; no CPI-driven selection.

## 8. Cautions carried forward

- Read `docs/score-v3.md` before touching scoring; do not reintroduce amount tiers, the 50-point finding family, or “unknown procedure ⇒ competitive”.
- Do not translate/normalize legal or source text; do not erase PDFs, raw XML, provenance or historical coverage snapshots.
- Dataset-embedded French strings surface in the UI (e.g. Tours `notes`, `exclusions`) — that is intended provenance display, not a missed translation.
- The browser test regex `/lots other than/` depends on the exact English wording of the notice-evidence panel; keep them in sync.
- Commit convention: single-purpose commits; the root commit message documents the migration.
- **No AI-attribution trailers, ever.** Commits must not contain AI-tool attribution trailers (“Generated with …”, “Co-Authored-By: <AI tool>”) or any equivalent. A permanent global `commit-msg` hook at `~/.config/git/hooks/commit-msg` (via `core.hooksPath`) blocks such trailers in every repo of this machine — do not remove or bypass it, and never add agent attributions to commit messages, authorship, READMEs or docs.

## 9. Next steps for the next session

1. ~~Publish to GitHub~~ — **done** (`git@github.com:La5u/contract-signals.git`, pushed 2026-09-21).
2. Optionally start the **Colombia SECOP II pilot scoping** (3 pre-selected buyers, 24-month window, verify process–contract–supplier joins before any indicator claims).
3. If a French UI is ever requested again, plan a proper string-extraction pass first (no dictionary exists yet).
