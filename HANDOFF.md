# Project handoff

Updated: 2026-09-25. The current state only; the dated history of each delivery is in `docs/project-journal.md` and in git.

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
- **Paraguay** (DNCP OCDS, CC BY 4.0), Paraguayan checks (`docs/score-paraguay.md`): six checks plus two out of scope (single tenderer, CVE exception award, their per-supplier repetition in distinct OCIDs, buyer/category concentration, amount increase >20 %). Two separate cohorts, never merged: Fernando de la Mora pilot (84 rows; 35 flagged / 49 zero; checks written after reading this pilot) and MOPC / Central / Asunción (`paraguay3`, 293 rows, calls 2024-09 → 2026-09; checks fixed before download; 53 flagged / 240 zero / 0 not assessed, 118 partial). Importer: `tools/import-paraguay-dncp.py --cohort fernando|3buyers --offline|--download`; the 3-buyer raw records are gzipped (`mtime=0`, exact response bytes). Multi-lot processes stay unknown for single tenderer (no per-lot count). Amount amendments cluster at +20 %, likely a legal ceiling, not encoded.
- **Outcome labels**: zero contract-linked final judgments in any dataset; one dated press lead (`crc-station-nuage`), status unknown (`docs/adjudicated-outcomes.md`).
- **Supplier names**: `tools/enrich-suppliers.py` looks up every typed French SIREN in both DECP cohorts (Paris & Ardèche + six cities) in the Recherche d’entreprises API. It keeps a name only when `statut_diffusion = O` and the SIREN matches exactly, then writes `supplierProfiles` into both datasets. Snapshot 2026-09-24: 1,960 SIRENs queried, 1,949 named, 10 withheld (restricted diffusion), 1 no exact match; names on 2,586/2,594 Paris & Ardèche rows and 1,116/1,270 six-city rows. The tool checkpoints to `data/.supplier-identities.partial.json` (gitignored), so an interrupted run resumes; after it, run `tools/update-cities-coverage.cjs` and `tools/review-score-v3.cjs`. Names are current, not historical, and never scored. `--offline` re-applies the snapshot without network access.
- **Paraguay context outside the index** (`docs/score-paraguay.md`): 20 % amendment ceiling label (Ley 7021/22 Art. 67, 10 rows), DNCP complaints (19 rows; participant names never imported), debarment in force at award date from `data/dncp-sanctions.json` (minimised snapshot via `tools/fetch-dncp-sanctions.py`; 0 rows on 2026-09-25), and per-lot evidence links (bid comparison tables / evaluation reports) on every award.
- **Verification**: “Sources and how to verify” panel per dataset (`sources` in the dataset registry: publisher, links, licence, raw path, rebuild command); “Verify it yourself” section per row from `verificationLinks(c)` (only URLs published in the data, human-readable pages first) and `verificationIdentifiers(c)`; `Verify:` lines in copied summaries; `verifyUrls` export column. All panel links were checked HTTP 200 on 2026-09-25 (DNCP `publicationPolicy` `/datos/legal` is 404; `/datos/aviso-legal` is used).
- **Explorer features**: view state in the URL fragment (`#dataset=…&q=…&sort=…&page=…&size=…`, defaults omitted; `hashchange` reloads when the dataset differs); CSV/JSON export of every filtered record (formula-guarded CSV, empty = not assessed); “Open your own JSON file” always visible (`docs/data-format.md`); `<meta name="referrer" content="no-referrer">`.

## Tests

```sh
sh tests/run-all.sh      # every suite; NO_BROWSER=1 skips Chromium. CI runs the same (.github/workflows/tests.yml)
```

Playwright is test-only, installed in `/tmp/procurement-browser` (reinstall with `npm install --prefix /tmp/procurement-browser playwright` if `/tmp` was cleared; Chromium at `/usr/bin/chromium`, or `CHROMIUM_PATH`). Never add it to the site. CI has not run yet: it starts on the first push.

**After changing `script.js`:** `node tools/review-score-v3.cjs`, then `node tests/score-review.cjs` (the report binds the script's SHA-256). After city scoring changes, also run `node tools/update-cities-coverage.cjs`.

**Rebuilding data:** every dataset now has an `--offline` importer (table in README). All were re-run on 2026-09-25 with no drift. The Paris & Ardèche and BOAMP importers were rebuilt from the journal and checked field by field against the originals (`rebuild` in `decp-coverage.json` and `coverage.json`); tests assert the published files equal the importer output.

## Cautions

- Read `docs/score-v3.md` before touching French scoring and `docs/score-colombia.md` before Colombian scoring. Never apply French thresholds to `secop2` rows; never turn the bare “Contratación directa” modality into a signal.
- The top of the default (index-descending) ranking contains many routine cases: proprietary-software maintenance in France, and in Colombia *comodato*, *empréstito* and interadministrative agreements with public counterparties. Examine flagged **and** unflagged examples before changing thresholds.
- Browser test regexes depend on exact UI wording (e.g. `/lots other than/`, `/not historical/`); keep them in sync.
- Commit convention: single-purpose commits, descriptive body, no attribution trailers.

## Next steps

1. **Hosting on `contracts.lasu.dev` (decided).** Needs the account owner: create the Cloudflare Pages project (no build command, output `/`), add the custom domain, keep Rocket Loader / Email Obfuscation / Web Analytics off. `_headers` (CSP, no-referrer) is ready and was tested in Chromium with no violations. Keep `lasu.dev` on auto-renew: shared view links depend on it.
2. **Licences to confirm:** BOAMP (API metadata states none), TED, and the Recherche d’entreprises API; update `docs/data-sources.md`.
3. **Reduce routine noise at the top of the ranking**: label or exclude public-to-public Colombian contracts; add a context label (not a score change) for French single-vendor software maintenance.
4. **Six-city DECP maps “Dialogue compétitif” to unknown**, while the Paris & Ardèche cohort treats it as competitive (the correct reading). Aligning it changes six-city counts; decide deliberately and update `tests/cities.cjs`.
5. Colombia: offers/proposals and payment reconciliation before any attrition/payment indicator. Paraguay: per-lot tenderers exist only in PDFs (bid comparison tables, now linked on every row); read DNCP Resolución 230/25 art. 181 before relying on the separate 20 % for unilateral changes; more buyers only with a pre-announced cohort. Brazil stays blocked (PNCP access not established; a first HTTP 200 invalidates the pin in `tests/score-review.cjs`).
6. Possible: generic DECP/OCDS import for people’s own buyers; Git LFS or release assets if raw snapshots grow (raw snapshots total about 70 MB, gzipped where large; the largest single file is 17 MB).
