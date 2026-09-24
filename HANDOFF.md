# Project handoff

Updated: 2026-09-24. The current state only; the dated history of each delivery is in `docs/project-journal.md` and in git.

## Where things are

- Repository: `/home/lasu/coding/contract-signals`, branch `main`, remote `origin = git@github.com:La5u/contract-signals.git` (SSH; no `gh` CLI on this machine).
- Licence: code and docs MIT (`LICENSE`); data keeps source licences (`docs/data-sources.md`).
- Not yet hosted. The choice between `lasu.dev` (Cloudflare) and `la5u.github.io` is open; see “Next steps”.

## Binding constraints

- Vanilla HTML/CSS/JS, local JSON only: no backend, framework, build step, runtime API call, analytics or cookies. Must work over static HTTP **and** `file://` (file picker).
- User-facing UI in English, no i18n dictionary. Source evidence (descriptions, notices, citations, `notes`, `exclusions`, `identifierNote`) stays in its original language — do not translate it. `'Définitif ferme'` in `script.js` is a DECP schema value, not UI text.
- Never show unknowns as zero (“Not assessed”). The index is editorial, not a probability or a measure of gravity. No points for amounts, R2122 citations, projects, names, country or CPI. Correlated signals in one family are not summed. Official findings, audit dossiers, reported investigations and adjudicated outcomes stay outside the index.
- Thresholds are specific to each jurisdiction. No international ranking, no currency conversion or cross-source sums.
- Preserve PDFs (`docs/sources/`), raw snapshots (`data/*/raw/`), provenance, coverage files and `tools/legacy/scoring-v2.1.js` (frozen, not loaded).
- **No AI-attribution trailers, ever** — in commits, authorship, READMEs or docs. A global `commit-msg` hook (`~/.config/git/hooks`, via `core.hooksPath`) enforces this; do not bypass it.

## Current state

- **Index v3.0** (`SCORE_VERSION`), method `docs/score-v3.md`: eight checks, `min(100, max(competition) + max(execution/duration))`. French review counts (from `data/score-v3-review.json`): BOAMP/CRC 277 positive / 2,665 zero / 68 not assessed; Paris & Ardèche 404 / 1,835 / 355; six cities 124 / 974 / 172; consultations and Tours all not assessed.
- **Colombia** (SECOP II, 7,560 rows, 3 buyers): Colombian checks (`docs/score-colombia.md`): 215 flagged / 7,345 zero / 0 not assessed. CC BY-SA 4.0.
- **Paraguay** (DNCP OCDS, 84 rows, one municipality): documentary pilot, all not assessed; no Paraguayan method approved (`docs/paraguay-pilot.md`). CC BY 4.0.
- **Outcome labels**: zero contract-linked final judgments in any dataset; one dated press lead (`crc-station-nuage`), status unknown (`docs/adjudicated-outcomes.md`).
- **Supplier names**: `tools/enrich-suppliers.py` looks up every typed French SIREN in both DECP cohorts (Paris & Ardèche + six cities) in the Recherche d’entreprises API. It keeps a name only when `statut_diffusion = O` and the SIREN matches exactly, then writes `supplierProfiles` into both datasets. Snapshot 2026-09-24: 1,960 SIRENs queried, 1,949 named, 10 withheld (restricted diffusion), 1 no exact match; names on 2,586/2,594 Paris & Ardèche rows and 1,116/1,270 six-city rows. The tool checkpoints to `data/.supplier-identities.partial.json` (gitignored), so an interrupted run resumes; after it, run `tools/update-cities-coverage.cjs` and `tools/review-score-v3.cjs`. Names are current, not historical, and never scored. `--offline` re-applies the snapshot without network access.
- **Explorer features**: view state in the URL fragment (`#dataset=…&q=…&sort=…&page=…&size=…`, defaults omitted; `hashchange` reloads when the dataset differs); CSV/JSON export of every filtered record (formula-guarded CSV, empty = not assessed); “Open your own JSON file” always visible (`docs/data-format.md`); `<meta name="referrer" content="no-referrer">`.

## Tests

```sh
node tests/scoring-v3.cjs && node tests/score-review.cjs && node tests/rules.cjs
node tests/cities.cjs && node tests/tours.cjs && node tests/colombia.cjs && node tests/paraguay.cjs
node tests/outcomes.cjs && node tests/page-copy.cjs && node tests/view-export.cjs
python -m unittest discover -s tests -p 'test_*.py'
node tests/browser.cjs   # starts its own static server on a free port (PORT to override)
```

Playwright is test-only, installed in `/tmp/procurement-browser` (reinstall with `npm install --prefix /tmp/procurement-browser playwright` if `/tmp` was cleared; Chromium at `/usr/bin/chromium`). Never add it to the site.

**After changing `script.js`:** `node tools/review-score-v3.cjs`, then `node tests/score-review.cjs` (the report binds the script's SHA-256). After city scoring changes, also run `node tools/update-cities-coverage.cjs`.

## Cautions

- Read `docs/score-v3.md` before touching French scoring and `docs/score-colombia.md` before Colombian scoring. Never apply French thresholds to `secop2` rows; never turn the bare “Contratación directa” modality into a signal.
- The top of the default (index-descending) ranking contains many routine cases: proprietary-software maintenance in France, and in Colombia *comodato*, *empréstito* and interadministrative agreements with public counterparties. Examine flagged **and** unflagged examples before changing thresholds.
- Browser test regexes depend on exact UI wording (e.g. `/lots other than/`, `/not historical/`); keep them in sync.
- Commit convention: single-purpose commits, descriptive body, no attribution trailers.

## Next steps

1. **Hosting.** Pick `lasu.dev` or `la5u.github.io`, then add the deploy (GitHub Pages workflow or Cloudflare Pages project). The site uses only relative paths, so it works under any sub-path. The largest file, `data/colombia-secop2.json` (15.6 MB), is under Cloudflare Pages’ 25 MiB per-file limit.
2. **Licences to confirm:** BOAMP (API metadata states none), TED, and the Recherche d’entreprises API; update `docs/data-sources.md`.
3. **Reduce routine noise at the top of the ranking**: label or exclude public-to-public Colombian contracts; add a context label (not a score change) for French single-vendor software maintenance.
4. Colombia: offers/proposals and payment reconciliation before any attrition/payment indicator. Paraguay: quotas and exhaustiveness, then local indicators. Brazil stays blocked (PNCP access not established; a first HTTP 200 invalidates the pin in `tests/score-review.cjs`).
5. Possible: generic DECP/OCDS import for people’s own buyers; CI workflow running the suites; Git LFS or release assets for raw snapshots.
