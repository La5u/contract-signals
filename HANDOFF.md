# Project handoff

Updated: 2026-10-08. **Restart from the checkpoint immediately below. It supersedes older working-tree, deployment, test-count and priority statements.** Older material is preserved as historical context, including Portugal evidence and constraints. Delivery history is in `docs/project-journal.md` and git.

## Restart here — latest checkpoint (2026-10-08, accuracy-first laptop session)

### Owner instructions and next action

- Owner transferred the migration ZIP to this laptop and asked to restore/setup it, then continue data work. Owner explicitly prioritizes **accuracy over expansion/scoring changes**, followed by finding authoritative evidence for zero amounts and missing fields. Never claim there is no inaccurate data: tests and source reconciliation do not establish upstream truth.
- Current requested investigation: **continue the Dijon DECP conflict**, exact municipal buyer `21210231300013`, source ID `2023VDAO1642`. Latest findings are below and in **`research/decp-dijon-conflict-review.md`**. Do not restart from the earlier assumption that this is simply six competing versions of one contract.
- **(Done 2026-10-08: holder linkage, see the Dijon holder-linkage section; the integration decision awaits the owner.)** Earlier next step: locate the buyer's original lot-level award/notification/DECP publication for this procedure, establish exact holder and contract linkage, and investigate the three offer-count disagreements. The official buyer-profile URL in the notice is only `http://www.marches-publics.info/`; no exact original buyer contract/notification has yet been acquired. Do not assume that a general portal link or supplier-name similarity validates the contract. Keep requests bounded and evidence private.
- No push, commit, publication, deployment or dataset replacement was performed in this session. **No standing permission to push:** `main` deploys Cloudflare Pages. Older deployment claims below were not reverified this session.
- All findings here are assistant-assisted source/document review, **not independent expert validation**. Signature authenticity, legal correctness, payments and completeness remain unverified unless specifically stated. Preserve every unresolved/conflicting field; never fill by inference, allocate a ceiling to a lot, sum versions/holders, convert currencies, or turn null into zero.
- Scoring recommendation given to owner: explainable jurisdiction-specific indicator profiles first, conservative family-max editorial review-priority index second. No corruption probability or learned weights without adequate independently reviewed labels. No weights/thresholds changed in this session. Accuracy/primary-law verification takes precedence.

### Checkout truth — preserve existing work

- Working directory: `/home/lasu/coding/contract-signals`.
- Git HEAD: **`581fe2c98e64e66ed5fd3964f599115f8e42767f`**, `Retry tests workflow`. Working tree is **dirty**, not clean. No changes committed by this session.
- **Pre-existing local work was preserved:** modifications to `script.js`, `index.html`, `style.css`, `i18n-es.js`, `i18n-fr.js`, `tests/browser.cjs`, `tools/i18n_table.py`, `docs/data-sources.md`, `data/score-v3-review.json`; untracked `tools/i18n_concise.py`, `tests/test_concise_ui.py`. These include concise UI/translation work and must not be discarded or attributed entirely to the accuracy session.
- Session additionally changed `script.js` (currency accuracy), `tests/browser.cjs` (unknown-currency regression), `tests/run-all.sh` (currency suite), `tools/import-boamp-sample.py`, `tests/test_import_boamp_sample.py`, and regenerated `data/score-v3-review.json`. Most new research/helpers/tests listed below are **untracked**; do not lose them during reset/cleanup. Run `git status --short` before editing.
- Original procurement dataset values were not rebuilt or replaced. Regenerating the required score-review artifact changed its timestamp/script hash, not measured scores in its five review datasets. No source weights/cohorts were altered.

### Migration, environment and local server

- ZIP: `contract-signals-migration-20261007-165010.zip` (private, mode 0600). Includes repository/git history and unpublished/raw data with personal/contact fields. **Never upload it.** Locally excluded through `.git/info/exclude` (`/contract-signals-migration-*.zip`); this is local exclusion, not a shared `.gitignore` change.
- Restored **17,073 private-cache files** to `~/.cache/contract-signals/` (mode 0700). Preserved the full archived checkout separately at `~/.cache/contract-signals/migration-20261007-165010/`; nine differing current files were NOT overwritten. Restored the missing `research/france-2023-backfill.md` into the active checkout. Restore details: private `migration-20261007-165010/restore-report.json`.
- Laptop architecture **aarch64**, Python **3.14.7**, Node **v22.23.1**. Private venv `~/.cache/contract-signals/venv` has PyArrow, NumPy, SciPy, scikit-learn, plus **pypdf and Pillow** added for document reading. The saved migration `python-environment.txt` predates these last two additions; use `pip freeze` for current truth. No project/site runtime dependency added.
- Playwright **1.58.2** installed at `/tmp/procurement-browser/node_modules/playwright`; downloaded ARM64 Chromium/headless shell in `~/.cache/ms-playwright/`. Fedora is not officially supported by Playwright, but the Ubuntu ARM64 fallback passed the browser suite. `/tmp` may disappear after reboot; reinstall if required.
- Server started at owner's request: **http://localhost:8000**, loopback only, background PID **169742** at last check. Command `python3 -m http.server 8000 --bind 127.0.0.1`; log `~/.cache/contract-signals/local-server.log`. HTTP 200 verified before writing this checkpoint. PID may become stale; check before starting another server. Private cache is outside the served repository.

```sh
cd ~/coding/contract-signals
source ~/.cache/contract-signals/venv/bin/activate
sh tests/run-all.sh
# If /tmp Playwright was lost:
npm install --prefix /tmp/procurement-browser playwright@1.58.2
/tmp/procurement-browser/node_modules/.bin/playwright install chromium
# If the local server is no longer running:
python3 -m http.server 8000 --bind 127.0.0.1
```

### Accuracy inventory and amount reconciliation

- **`research/accuracy-priority.md`** is the ranked work queue. Inventory: **14 published datasets / 18,501 normalized rows**, not 18,501 independently validated unique contracts.
- `tools/audit-data-quality.py` + `tests/test_audit_data_quality.py`; findings **`research/accuracy-inventory.md`**. Counts: **1,383 null amounts, 154 explicit zeros, 16,964 positive amounts**; no negative/non-numeric top-level amounts, malformed top-level dates, duplicate within-dataset row IDs or missing primary source URLs detected. These are narrow structural checks, not factual assurances. 527 rows have initial-conflict markers. Broad private review queue has 15,932 rows, including expected omissions; it is not an error count.
- 6,979 currencies are absent as explicit fields, mostly legacy French EUR-default rows. Do not describe all of these as demonstrably unknown denominations. Whole international cohorts lack top-level `publicationDate`; this is not proof their publishers supply none. Notice-only records may legitimately lack contract fields.
- `tools/review-missing-amounts.py` + `tests/test_review_missing_amounts.py`; **`research/missing-amounts-review.md`** reconciles **all 1,537 zero/null rows** against retained evidence:
  - **154 explicit source zeros**;
  - **780 amounts absent** from relevant source fields;
  - **526 unresolved DECP initial amount conflicts**;
  - **76 notice-only rows**, outside contract-amount scope;
  - **1 negative BOAMP PayableAmount**, deliberately not imported as positive.
- **Zero safe replacement amounts found.** Private amount evidence queue has 2,025 entries: the 1,537 gaps plus 488 Ukraine contract provenance checks. Ukraine's contract values are retained; 11 contract/award differences are different bases, not automatic corrections.
- `tools/recheck-amount-gaps.py` + `tests/test_recheck_amount_gaps.py`; **`research/current-amount-recheck.md`**: three preregistered exact-ID live official API requests (BOAMP missing, BOAMP zero, Colombia zero), all HTTP 200. One missing amount and two zeros persisted; no positive candidates. Not a representative upstream accuracy estimate.

### French mapping review and accuracy fixes

- **`research/accuracy-france-source-review.md`**, read-only helper **`research/accuracy-france-source-review.py`**: six-city DECP 1,865 raw rows → 1,270 groups; Paris/Ardèche 2,949 → 2,594; BOAMP 16,002 eligible occurrences and exact 3,000 sampled lots. Zero regeneration/independently reviewed-field mismatches, with curated overlays explicitly separated. These do not validate signed contracts or publisher declarations.
- Currency fixes in `script.js`: sorting and profile currency groups use `recordCurrency`, imports with unknown currency are not treated as EUR for French thresholds, zero/nonpositive differs from missing in explanations, history/initial variants use `moneyFor(c)`. Legacy French EUR convention remains. `tests/currency-accuracy.cjs` wired into `tests/run-all.sh`; browser test now expects French-opt-in unknown currency to remain unassessed, then verifies an explicit EUR fixture.
- BOAMP importer hardening: finite/nonnegative amounts and MONTH durations, validated calendar dates, numeric `#text` statistics, conflicting `tenders` totals become null, holder-reference pairs retained correctly; unresolved holder references conservatively excluded. **14 BOAMP tests**, ten added regressions. Exact saved-snapshot complete build/sample unchanged; no dataset write-path rebuild performed. Independent helper updated to tolerate the fixed synthetic probes.
- Required after any `script.js` edit: `node tools/review-score-v3.cjs`. This was run after currency changes. Existing review-cohort scores did not change.

### Frozen six-row documentary pass

- Plan: private `~/.cache/contract-signals/document-review/plan.json`, immutable/exclusive freeze; hash **`6533cc7c41384b2e7d33fd6c06e8f0fd5d6409634b236e56901ef481a1609b03`**. Do not overwrite or reselect after seeing outcomes.
- Tool/tests: `tools/prepare-document-review.py`, `tests/test_prepare_document_review.py`; protocol **`research/document-review-protocol.md`**. Actual cohort-prepared app scores used through Node VM, then lexicographically selected fixed strata.
- Outcomes: **`research/document-review-results.md`**, helper `tools/review-boamp-documents.py`, `tests/test_review_boamp_documents.py`:
  - Flagged `boamp-25-11411-lot-0001`: PDF agrees on 138,555 EUR, conclusion 2024-09-09, one offer; tax and underlying contract truth unknown.
  - Zero-score positive `boamp-25-11426-lot-0001`: no correct PDF acquired within eight-request BOAMP cap; explicitly unverified, not replaced with another row.
  - Zero `boamp-25-11531-lot-0005`: PDF explicitly says 0 EUR; not evidence of a free service. Conclusion 2024-12-23, two offers.
  - Missing `boamp-25-11359-lot-0001`: PDF states a **1,000,000 EUR lot framework ceiling**, not a winning-offer amount. Procedure ceiling is 1,240,000 EUR. **Never fill the blank with either.** Conclusion agrees; electronic submissions not total offers.
  - Dijon DECP conflict: initial pass remained unresolved; newer follow-up below supersedes that limited understanding.
  - Paraguay `dncp-ocds-03ad3f-452188-1-MN-30173-24-244215`: five-page linked scan states procurement 452188 and total **252,144,563 PYG, IVA incluido**, matching numerically. Handwritten subscription date read as **2024-10-21**: **private candidate only**, awaiting independent review. Existing published date remains period start, not silently signature. Full OCDS contract ID is not printed; linkage is the exact source document/award metadata, handwritten local contract number unresolved. Signatures visible, authenticity not verified. 120 days run from a start order, not necessarily signature.
- Document acquisition had failures recorded: initial four BOAMP requests used the wrong documented template branch and returned 404; eForms `source_schema=3.2.5` uses `/telechargements/FILES/PDF/{year}/{month}/{idweb}.pdf`. Three PDFs were then acquired within eight requests including prior HTML. No hidden retries/redirects. Paraguay exact frozen PDF acquired in one request; text empty, all embedded scans inspected with pypdf/Pillow. Raw scans contain personal IDs/signatures: **keep private**.

### Current open items (2026-10-09) — supersedes every "open", "left" or "decisions" list below

Work is committed on branch `france-decp-reconciliation` (`9367b7c` plus the doc fix after it). Nothing is pushed or deployed.

1. **No measured accuracy rate.** The preregistered sample (`tools/accuracy-sample.py`) found no linkable notice for 76 of 90 contracts. A real rate needs a document-review sample restricted to contracts that must have award notices (open procedures above EU thresholds), or buyer documents.
2. **885 French amount disagreements** (788 Paris, 97 cities). They are shown as ranges and amount checks use the whole range. They are mostly basis differences (annual vs full term, maximum vs estimate). Settling them needs notices or buyer documents. Option to consider: leave the sorting value empty when sources differ by more than 2×.
3. **Offer-count disagreements:** 7 Dijon notice-vs-DECP and 5 feed-vs-Ministry. Only the buyers' offer-analysis reports (rapports d'analyse des offres, communicable on request) can settle them.
4. **25 possible-duplicate records** with no evidence either way. Dijon lot 8 (`2024vdao017008`, 559,742.62 EUR) is absent from every source.
5. **Not built:** cross-links between BOAMP sample lots and DECP contracts (agreed in principle). Missing CPV check digits for about 128 feed/portal-added contracts, which keep them out of CPV-based baselines.
6. **Housekeeping:** the stray `stash@{0}` (old generated score review) can be dropped. Git has no global identity on this laptop. Review marks saved in browsers under the old `cities|` key no longer show.
7. **Deployment** is the owner's call: merging into `main` and pushing deploys Cloudflare Pages.

### France DECP merged into one dataset; issues settled (2026-10-08, newest; not committed or deployed)

- The explorer's `decp` entry now loads both DECP import files (5,286 contracts, eight buyers). `cities` links redirect to it.
  - New: `data/decp-france-coverage.json` (`tools/build-decp-france-coverage.py`).
  - Dataset metadata rewritten (`cities` entry removed).
  - `tools/compare-score-revisions.cjs` and `tools/audit-data-quality.py` accept list paths.
- **Settled:**
  - Paris price-type "conflicts" were reordered sets: 0 excluded contracts remain.
  - 50 possible-duplicate records cleared by distinct route references; 10 folded as amount pairs; 25 remain flagged.
  - A self-contradicting route no longer votes.
  - Dijon lot 6: the Ministry-only second holder moves to `unconfirmedHolders` (notice and feed agree on the single winner).
  - Lot 8 is absent everywhere.
- **Rebuild:** run both DECP imports, then `tools/build-decp-france-coverage.py`, then `node tools/review-score-v3.cjs`.
- **Tests:** full suite passes.

### Open-data portals, majority tie-break, ranges, co-holders (2026-10-08; not committed or deployed)

- See `research/france-cross-dataset-check.md`, section "More sources, co-holders and ranges".
- **New sources:** `tools/extract-city-portals.py` → `data/city-portals-raw.json.gz` (Nantes 2024/2025 City lists and the Bordeaux datahub's City rows). A Nantes 2024 buyer-SIRET typo is corrected and documented. No current lists exist for Paris, Grenoble, Dijon, Tours or Ardèche; Rennes ends in 2022 with no amounts.
- **`tools/decp_feeds.py`:**
  - matching is two-phase (feeds, then portals);
  - `majority` tie-break counts routes, with AWS and its scraped copy as one;
  - co-holders dropped by the Ministry's 3-slot table are restored (67 rows; 4 distinct contracts added).
- **App:** disagreements are shown and exported as ranges (`amountLow`/`amountHigh`/`amountVerification`); there is a majority note and a portal-only label.
- **Cities:** 2,299 records (+78 from portals); 1,792 agree, 87 disagree, 64 settled by majority.
- **Supplier names:** 2,710 identities, refreshed incrementally.
- **Tests:** full suite passes. Playwright had to be reinstalled in `/tmp` (it had been cleared).

### Non-decision fixes after feed reconciliation (2026-10-08; not committed or deployed)

- **Offer counts:** where the Ministry and the buyer feed give different positive counts, the count is now unknown (`offersConflict.feed`). This affects 8 city contracts; zero counts are already unusable.
- **Supplier names:** `tools/enrich-suppliers.py --incremental` added 672 new SIRENs, with the 1,960 earlier lookups unchanged; 19 are unavailable. Names now cover 2,151/2,219 city and 2,867/2,997 Paris/Ardèche contracts.
- **Curated note:** `decp-cities-curated.json` now marks `2024VDAO017006` as `handledAs: joint-contract`.
- **Docs and attribution:**
  - `docs/data-sources.md` gains a licence row and a rebuild row for the buyer feeds;
  - the app's Sources panel links the national consolidation;
  - research inventories carry snapshot notes.
- **Flaky test:** the browser check for the filter-sidebar setting now waits for the save.
- **Full suite passes.**
- **Decisions still open for the owner:**
  1. Show large amount disagreements (more than about 2×) as unknown.
  2. Use BOAMP as a tie-breaker where a notice amount matches one source.
  3. Investigate or add the 71 feed rows sharing an ID with ours but with another holder.
  4. Fill CPV check digits from the official CPV list for 128 added contracts, which currently lack them and are left out of sector-based baselines.
  5. Run a document-review sample for a real accuracy rate.

### Buyer-feed reconciliation — done (2026-10-08; not committed or deployed)

- See `research/france-cross-dataset-check.md` ("Implementation" and "Random-sample accuracy check").
- **Tools:**
  - `tools/extract-decp-feeds.py` → `data/decp-feeds-raw.json.gz`;
  - `tools/decp_feeds.py`, used by both DECP importers;
  - `tools/accuracy-sample.py`, frozen sample, private results.
- **Tests:** `tests/test_decp_feeds.py` and `tests/test_accuracy_sample.py`. The full suite passes, including the browser test.
- **Data:** cities 2,219 records (+355 from feeds), Paris/Ardèche 2,997 (+403); all 355 Paris pairs resolved; 92 placeholders now unknown. Verification filter and amount-sources panel in the app.
- **Accuracy sample:**
  - no overall rate is possible: 76 of 90 contracts have no linkable notice, and "sources agree" is unmeasured;
  - for "sources disagree", the notice supports the shown amount in 2 of 7, and once the Ministry's value over the feed's (`2024S11872`);
  - treat disagreeing amounts as unreliable.
- **Next options:** document-review sample restricted to contracts that must have award notices; reconsider the feed-first rule for large disagreements (e.g. leave the shown amount unknown when sources differ by more than 2×).

### French cross-dataset check — read-only (2026-10-08)

- See `research/france-cross-dataset-check.md`. The owner asked for no changes yet.
- **Paris/Ardèche:** 433 of 2,230 comparable Paris contracts differ in amount from Paris's own feed (national `atexo_maximilien`). About 90 are 10 EUR placeholders. The rest are ×2/×4/×10 basis differences or single-digit differences. BOAMP maxima agree with Paris's feed in the cases checked.
- **The 355 Paris "conflict" pairs** look like two amount versions of one contract (Paris's feed keeps one). Do not split them like the cities.
- **Nantes:** 51 amount differences.
- **Coverage:** about 227 city and 387 Paris contracts are in the national feeds but absent from our Ministry "valid" snapshots.
- **BOAMP vs DECP:** 649 lots linkable; 202 amount differences in both directions; 15 offer differences.
- **Awaiting owner decision** on an amount-resolution rule.

### All six-city contracts included (2026-10-08; not committed or deployed)

- The owner chose to include every contract. Rows sharing a DECP `id` are split into distinct contracts by their declared fields and linked (`procedureGroup`). One joint contract was merged. 95 possible duplicates are flagged (`possibleDuplicateOf`); they are scored, and each cluster counts once in buyer baselines.
- **Cities cohort:** 1,864 rows, 0 excluded, 186 flagged, single-bid 82. All datasets: 19,095 rows. See `research/decp-identifier-collisions.md` ("Decision and implementation").
- **Tests:** full suite passes (322 Python tests, all JS suites, browser). The document-review tests are pinned to the frozen-time city file.
- **UI strings:** new English UI strings (duplicate and offer-conflict notes, sibling list) have no FR/ES translation entries yet.
- `data/decp-cities-curated.json` still lists `2024VDAO017006` under `unresolvedGroups` (no notice linkage); the importer now merges it as a joint contract per DECP.

### Remaining six-city conflicts: identifier problem, research only (2026-10-08)

- See `research/decp-identifier-collisions.md`. Of the 169 remaining conflict groups, **135 are unrelated contracts sharing one `id`**; only about 6 resemble the Dijon lot pattern.
- **Dijon, Bordeaux and Grenoble (AWS):** the export appears to truncate `id`s. The national `scrap_marches-publics.info` copy has longer `id`s with the short one as prefix, but it fully separates only 2 of 63 groups.
- **Nantes and Rennes:** `id` is not the contract number. Rennes award 24-24339 prints `Marché n° 2410046` for DECP `2024S00004`.
- No data changed. Next steps await the owner: publish distinct-object/CPV rows as linked "shared identifier" groups; contact the AWS/DECP maintainers; check Nantes notices.

### Dijon project reconciliation and split — implemented 2026-10-08 (newest; not committed or deployed)

- The owner approved splitting with linking. Details are in `research/decp-dijon-conflict-review.md` under "project-wide reconciliation and integration".
- New tools: `tools/reconcile-dijon-project.py` (`--fetch` is frozen and already used; `--write-curated` regenerates `data/decp-cities-curated.json`) and `tools/fetch-dijon-project-notices.py` (used). Tests: `tests/test_reconcile_dijon_project.py` (8) and `tests/test_link_dijon_holders.py`.
- **Published data changed:** `data/decp-cities.json` and its coverage file were regenerated with `python tools/import-decp-cities.py --offline`.
  - 3 groups split into 13 linked rows (`procedureGroup`); 7 disputed offer counts nulled (`offersConflict`); 26 rows attached to project `dijon-maison-des-associations`.
  - `script.js`: the identifier-ambiguity rule exempts only exact procedure-group members; the record panel shows sibling lots, disputed offers and a link to the project.
  - Cities cohort: 1,280 rows, 169 excluded, 110 flagged, single-bid 51. Totals across all datasets: 18,511 rows. Test expectations were updated to match.
  - `node tools/review-score-v3.cjs` was rerun. The full suite passes: 320 Python tests, all JS suites, and the browser suite.
- **Still open:**
  - Seven offer-count disagreements. These need the buyer's *rapports d'analyse des offres*; a records request to the Ville de Dijon would be the next step.
  - Lot 8 (2024vdao017008) has no DECP row at all.
  - `2024VDAO017006` has a joint-holder / notice mismatch and stays excluded.
  - Five unlinked holders, and lots 17/22, with no relaunch found.
- **Accidents in this session — check `git status` before committing:**
  - A stray `git stash` (`stash@{0}`) holds an older generated `data/score-v3-review.json`. Safe to drop once confirmed.
  - `i18n-fr.js` and `i18n-es.js` were reset by mistake and rebuilt with `python3 tools/i18n-strings.py` from `tools/i18n_table.py`. The generator-consistency test passes.
- Other research docs (`accuracy-inventory.md`, `missing-amounts-review.md`) still quote pre-split counts (18,501 rows / 1,537 gaps). Treat those as snapshots.

### Dijon holder linkage — resolved 2026-10-08

- `tools/link-dijon-holders.py` + `tests/test_link_dijon_holders.py` (10 tests). Six bounded exact-SIRET lookups in the official DINUM register (`recherche-entreprises.api.gouv.fr`), all HTTP 200, frozen in private `decp-conflict-dijon/holder-registry-20261008/`. **All six DECP rows are holder-linked** to their candidate lot's notice winner: exact SIRET, consistent SIREN, name tokens and postcode all agree, and the six winners are distinct. The conflict is fully explained as six lot contracts sharing one procedure ID.
- The establishment for printed lot 20 is **closed in the current register**. That is current state only.
- **Offer counts for printed lots 7, 12 and 20 remain unresolved.** DECP and the notice are two declarations by the same buyer through the same AWS platform. All offers were electronic, so that is not the explanation. Integrate those three counts as null.
- **Next / awaiting owner:** approve or decline the narrow integration proposed in `research/decp-dijon-conflict-review.md` ("Decision and next gate"): six lot rows, provenance contract references, three null offer counts, LOT-0014 excluded, an exact-pair rule only. Not yet implemented. No dataset, score, commit or push changes were made. Full Python suite: 312 tests OK.

### Latest Dijon conflict finding — earlier pass (superseded by the section above)

- Detailed report **`research/decp-dijon-conflict-review.md`**. New helpers/tests: `tools/fetch-decp-conflict-evidence.py`, `tools/reconcile-dijon-conflict.py`, `tests/test_fetch_decp_conflict_evidence.py`, `tests/test_reconcile_dijon_conflict.py`.
- Four bounded official requests: exact Ministry buyer/ID (no year filter), BOAMP exact reference search, limited title/buyer discovery, exact **24-79759** PDF. Raw responses and 39-page PDF remain private. PDF SHA-256 **`54ecaae5649ff9ede84f576442fd1c40935b01916728c4b939e184d740b0af36`**. Notice UUID **`abf0a548-7c69-44e0-a066-402d0b1aa048`**, version 01; procedure UUID **`682e7482-e0b9-440b-9031-d9438725cea9`**. Exact buyer SIRET and procedure's internal ID **2023VDAO1642** match.
- Live Ministry still has six rows, each different holder/amount, no modification IDs. Award notice has distinct lot contracts; amount/date/contract-reference relationships and PDF values support six **candidate** pairings:

| Technical lot | Printed lot | Contract reference | EUR value | DECP / notice offers |
| --- | ---: | --- | ---: | --- |
| LOT-0001 | 1 | 2023vdao164201 | 456,516.27 | 10 / 10 |
| LOT-0007 | 7 | 2023vdao164207 | 668,893.00 | **2 / 4** |
| LOT-0012 | 12 | 2023vdao164212 | 168,127.96 | **2 / 5** |
| LOT-0013 | 13 | 2023vdao164213 | 580,470.95 | 4 / 4 |
| LOT-0019 | 20 | 2023vdao164220 | 155,995.41 | **2 / 3** |
| LOT-0022 | 23 | 2023vdao164223 | 105,055.00 | 2 / 2 |

- **Root-cause explanation: procedure-ID / lot-contract granularity collision.** Do not treat buyer + supplied ID as one verified unique contract. Do not take the lone 456,516.27 national row as authoritative: it represents only one corresponding lot-value alternative, not complete procedure coverage.
- Technical lot IDs **are not printed lot numbers** (LOT-0019 → 20, LOT-0022 → 23). Never derive printed lot number/contract suffix from the technical ID.
- Notice's seventh awarded result: LOT-0014, 57,000 EUR, reference **2024vdao164214**, different year prefix; not forced into target group or used in a sum.
- **Three offer-count disagreements** (printed lots 7, 12, 20) persist between sources. PDF corroborates BOAMP `tenders` totals, not independent precedence over DECP. `t-esubm` was not substituted.
- BOAMP winning-holder registration fields are placeholders, **zero exact holder identities confirmed**. This prevents claiming fully verified DECP-row-to-lot matches. Matching amount/date within an exact buyer/procedure is candidate support, not enough for a published repair. Tax/scope also unresolved; notification and conclusion share dates but remain different meanings.
- **Decision:** published grouped row remains amount-null and excluded; six minimized private lot candidates retained, no score calculated, no published split. To integrate: first establish authoritative lot/holder linkage, or explicitly create a separate BOAMP notice-lot cohort with its own source/basis rather than inventing DECP lot IDs. Owner has not yet approved a dataset integration/deployment.

```sh
# No-network plan; do NOT rerun --fetch against the existing exclusive freeze.
python tools/fetch-decp-conflict-evidence.py
# Offline reconciliation with PDF, requires private cache/pypdf:
~/.cache/contract-signals/venv/bin/python tools/reconcile-dijon-conflict.py
```

### UK full-cohort audit and remaining accuracy risks

- `tools/audit-uk-contract-values.py`, `tests/test_audit_uk_contract_values.py`, **`research/uk-contract-multiplicity-review.md`**: 1,081 published rows, 516 saved releases, 1,233 awards, 1,086 raw contracts. Every published row has exactly one linked contract; no current multi-contract overwrite or observed award-value fallback. All amount/currency/date pairs match the importer rule. Nine lack amount+currency, **three dates use notice-date fallback**. Award value objects absent: zero differences means no comparable pairs, not demonstrated agreement.
- Open risks in `research/accuracy-priority.md`: independent documentary review; primary legal texts/eligibility; UK latent last-wins and fallback basis; Paris/Ardèche history omits 2,563 known initial holder IDs and lacks city-style modification conflicts (none observed in saved snapshot); mixed-currency minimum-amount filter still applies one numeric cutoff and was deliberately not redesigned; other importer numeric/temporal guards; missing offers/dates/durations and privacy-safe historical names.
- No blanket `dataStatus: verified` factual assurance. This is provenance metadata, not independent document validation or completeness. Null score is not zero; zero score can coexist with missing amount if other checks evaluate.

### France 2023 backfill — research only

- `research/france-2023-backfill.md`, `tools/audit-france-2023-backfill.py`, `tests/test_france_2023_backfill.py`.
- Six exact preregistered municipal buyers; cached national snapshot yields **612 rows / 491 candidate buyer-contract groups** in 2023, not 491 verified contracts. Offline all-year state audit: **76 conflicting initial groups**, **385 single initial-state groups dated 2023**, **61 groups have initial dates outside 2023**. No candidate cohort imported/published/scored.
- Tours exact municipality has zero 2023 matches, but **383 source rows dated 2025 and 471 dated 2026**: coverage gap, not zero purchasing. Three official metadata checks found no suitable historical procurement source; similarly named Tours “Les marchés” dataset is market locations/hours, not contracts, and concerns the metropolis. Do not substitute metropolitan buyer.
- Dijon conflict investigation shows why buyer/contract grouping itself must be reviewed before any historical cohort or year comparison.

### Private evidence and reproducible research index

**Never copy these directories into Git or the static server root:**

- `~/.cache/contract-signals/migration-20261007-165010/`: archived repository, restore report, migration instructions.
- `~/.cache/contract-signals/decp-national/`: parquet, manifest, national draft, 2023 audit, Tours metadata responses.
- `~/.cache/contract-signals/accuracy-review/`: broad review.jsonl, minimized UK full-cohort findings (`uk-contract-multiplicity-20261007/`), French reconciliation JSON and test logs. UK directory date is inherited; actual review context is in report.
- `~/.cache/contract-signals/missing-amounts-review/review.jsonl`: exact amount evidence/candidates, 2,025 entries.
- `~/.cache/contract-signals/current-amount-recheck/`: frozen three-request plan/live responses and provenance.
- `~/.cache/contract-signals/document-review/`: immutable plan, BOAMP PDF/HTML/text/manifests, `boamp-document-results.json`, Paraguay PDF/scans/private date candidate, `paraguay-document-result.json`, earlier `decp-conflict-evidence.json`.
- `~/.cache/contract-signals/decp-conflict-dijon/`: new `official-discovery-20261008/` frozen API plan/raw responses/manifest; `boamp-24-79759.pdf`, text and PDF manifest; `lot-candidate-reconciliation.json`. Cached 25-33856 is a later lot-12 relaunch, not the original target award.
- Existing BASE archives/candidates and labels remain private with their older rights/coverage constraints. Read source rights/privacy docs before attachments; reuse rights do not clear personal-data publication.

### Tests and refresh instructions

- **Latest full suite passes: 302 Python tests, all JavaScript suites, browser suite.** Run used venv on PATH so research-dependency tests did not silently skip for missing PyArrow/etc.
- Latest log: `~/.cache/contract-signals/accuracy-review/dijon-conflict-tests.log`; prior full logs retained nearby. Eleven tests added in latest Dijon phase (seven reconciliation, four bounded fetcher); complete count incorporates preceding migration/backfill/currency/amount/document/UK work.
- Latest reconciliation prints: six source rows, six unique candidate lot matches, three offer-count disagreements, zero holder identities confirmed, zero published changes. PDF corroborates all six candidate notice values/references/dates/offer counts, but this is not independent truth validation.
- After refresh: read this checkpoint, then **`research/decp-dijon-conflict-review.md`** and **`research/accuracy-priority.md`**, inspect `git status`, check cache/server availability, and continue exact buyer-profile lot/holder evidence. Do not repeat frozen network collection, discard dirty files, regenerate datasets for convenience, or push without approval.

## Historical checkpoint (2026-10-05; superseded where inconsistent above)

### Production and working-tree truth

- Production https://contracts.lasu.dev is at **`1fdac98`**, *Score 3.3: legal anchoring and national DECP evidence*. Deployment was verified in an isolated headless Chromium (desktop and mobile, no console errors). The working tree is clean. Pushes of score 3.2 and 3.3 were explicitly authorized by the owner on 2026-10-04/05. **That is not standing permission:** every push to `main` deploys Cloudflare Pages, so ask before the next one.
- Score history this session: **3.2** (buyer-relative late publication; French direct award only from the legal no-publicity threshold; tie-breaks; five evidence checks at 8 points and **hidden on records without evidence**, an owner-approved reversal of the earlier "always visible" decision). **3.3** (Paraguay 20 % ceiling bands, 8 points at the ceiling by owner decision; DECP late-publication excess 240 days; long-duration maximum 16, was 40; concentration entry kept at 60 % by owner decision).
- Owner dislikes long delays: give bounded progress and honest completion status. Never claim a working empirical model, completed outcome review, independent expert validation, or a deployment when only documentary/synthetic checks were done.
- Battery rule still applies to heavy work (national BASE rebuilds, large downloads): check AC power and get explicit authorization.
- Model usage: the owner wants long or mechanical tasks delegated to Sonnet subagents or Codex (`codex-sub`) to save usage. Codex has a separate usage limit that can run out mid-task.

### Audit corrections — owner-authorized release

- Corrected v3.3 leave-one-out median parity, French invalid-calendar-date eligibility and overlapping 180-day threshold transitions; regression tests added. No weights or source cohorts changed.
- Impact versus `5f94c8e`: 18,501 rows across 14 datasets; 21 changed scores (17 BOAMP, 4 Portugal TED), two added late-publication signals. Portugal positive/zero/unknown now 138/355/0; BOAMP positive total unchanged, one top-20 entry changes. Other 12 datasets unchanged. Details: `docs/score-audit.md`, `data/score-audit-impact.json`; reusable comparison: `tools/compare-score-revisions.cjs`.
- Regenerated score review; generator reads actual `SCORE_VERSION` (3.3), corrected stale report/coverage version pointers. Shared/country docs distinguish editorial weights, exploratory proxy evidence, legal rules and provisional Paraguay basis.
- All non-browser suites pass: 225 Python tests, 11 skipped; isolated headless Chromium browser suite passes. Playwright test dependency was restored under `/tmp/procurement-browser` after restart; `/tmp` is ephemeral. Owner explicitly authorized pushing these changes to `main` in the current session. Deployment confirmation must be checked after the push; prior authorization is not standing permission for future releases.

### Local research state outside git

- `~/.cache/contract-signals/venv` (pyarrow, numpy, scipy, sklearn) runs `tools/analyze-decp-national.py`. System Python lacks pyarrow, so its tests skip there.
- `~/.cache/contract-signals/decp-national/decp.parquet`: national DECP, data.gouv.fr dataset `608c055b35eb4e6ee20eb325`, Licence Ouverte 2.0, SHA-256 in `manifest.json`. A full analysis run takes about 7.5 minutes.
- `~/.cache/contract-signals/labels/` (about 810 MB): raw responses from the SECOP and DASU label collectors and the Ukrainian cohort, including buyers' public contact fields. Never copy them into the repo.

### Next work (ranked)

1. Practitioner feedback: if Rennes or Nantes reply, have them review the top-ranked rows. This is the most realistic validation available.
2. Ukraine: legal minimum submission periods per procedure need the primary texts of Law 922-VIII and Resolution 1178, and the importer must read `tenderPeriod`. A flat short-period check would flag the norm (about 62 % of tenders are under 10 days).
3. France: anchoring the short bidding period and modification caps needs data showing whether a contract is above the EU threshold. Colombia's 50 % additions cap needs the addition value, which SECOP II does not publish.
4. Concentration: on the national DECP, risk rises from 40 %, but the 60–70 % bin dips, so the predeclared rule only supports 90 %. Revisit with more data before moving the 60 % entry.

- **2026-10-04 score 3.3, DECP late publication:** for DECP only, the buyer-relative late-publication excess must exceed 240 days (was 120); buyers without a usual delay keep the legal 120 days; BOAMP/TED unchanged. Evidence in `research/thresholds/france-national.md` and `docs/threshold-calibration.md`. Paris & Ardèche 355/1,966/273 (was 1,881 zero/358 flagged), six cities 172/987/111 (was 949/149), BOAMP unchanged. Expectations updated in `tests/cities.cjs` and `tests/browser.cjs`; `sh tests/run-all.sh` passes. Owner decisions 2026-10-05: keep the concentration entry at 60 % (the predeclared rule gives 90 %), keep 8 points for Paraguayan amendments at the 20 % ceiling, and lower the long-duration maximum from 40 to 16 (France and Colombia), because national DECP single-bid odds fall with duration. Committed and pushed as score 3.3.

### Outreach and live-site review

- Prepared Rennes and Nantes municipal feedback requests and official contact-form instructions. Owner reports requests sent; actual delivery/recipient was not independently verified. Assistant did not send email or submit a form.
- Forms: https://data.rennesmetropole.fr/pages/contact/ and https://data.nantesmetropole.fr/pages/contact/ . Demo supplied: https://contracts.lasu.dev/?lang=fr#dataset=cities . Templates, task and adoption limits: `docs/adoption.md`.
- Live headless Chromium and Firefox checks used isolated temporary profiles, desktop and mobile. Passed French city search, official-source links, record panels, URL/reload state and failure recovery. Normal browser sessions were not disturbed.
- French record-counter translation fixed **locally only**, e.g. “Fiche 1 sur 303”; update `tools/i18n_table.py`, then regenerate dictionaries rather than directly editing generated language files.
- Any user-reported investigation is not an independently verified outcome, does not establish guilt or causation by the tool, and is not a training label. Keep public evidence, investigations, audits, administrative findings and criminal convictions distinct.

### Five additional indicators — implemented in the normal local explorer

- Shared browser/Node engine: **`indicator-evidence.js`**. CLI/API wrapper: **`tools/experimental-indicators.cjs`**. Normalized contract evidence is **`contract.indicatorEvidence`**. Documentation: `docs/experimental-indicators.md`; synthetic fixture: `tests/fixtures/experimental-indicators-positive.json`.
- Integration is in normal filters, assessments, row/panel signals and exports. The local universal catalogue has **18 indicator kinds**, not necessarily 18 applicable checks on each row. Key functions: `getAssessment(c)`, `computeAssessment(c)`, `getAdditionalIndicatorChecks(c, excludedReason)`, `getScoreBreakdown`, `INDICATOR_KINDS`.
- Trial weights/thresholds, all editorial and uncalibrated. **Since score 3.2 (2026-10-04, owner-approved) every check carries a uniform 8-point placeholder; the 20/10/5/3/1 below were the earlier arbitrary values:**
  1. **Cap proximity —20**, execution family: cumulative additions at95–100% of the particular contract's verified applicable cap, consistent valuation basis. Above-cap context is separate and gets no near-cap points.
  2. **Full payment / incomplete execution —10**, execution: verified net payments ≥99% of payable value, independently documented physical completion ≤80%, identical snapshot dates; advances/refunds excluded. Elapsed time is not physical progress.
  3. **Legal-ground mismatch —5**, competition: reviewed jurisdiction/classification/legal-ground mapping expressly says incompatible and is date-valid; no keyword-only inference.
  4. **Comparable annual unit-price rise —3**, execution: inflation-adjusted real rise ≥30%; buyer, supplier, item/specification, quantity/unit, currency, tax and delivery are explicitly comparable.
  5. **Exclusivity claim versus comparable competitive wins —1**, competition: verified supplier identity, documented claim, competitive win with at least two offers, matched market/territory/time/rights context. This is a review prompt, not proof that an exclusivity exception is invalid.
- Preserve family-max architecture: competition maximum60, execution40, transparency16, total capped100. These five alone can contribute at most **16** (8 execution+8 competition) since 3.2, not the CLI diagnostic sum40. Do not substitute additive logistic coefficients into family maxima and claim equivalent performance.
- Missing/conflicting/unsupported evidence is **not assessed**, points null; verified below-threshold observations get0. CLI total is null if nothing is assessed. Source references must be present, but the engine does **not** verify URLs or factual/legal assertions. `Verified`/`Confirmed`/`Reviewed` booleans are caller assertions, not independent verification.
- **Existing bundled datasets do not have normalized verified evidence mappings for these checks.** They are omitted from records without evidence (they appear only where `indicatorEvidence` is present) and add no points. Do not invent country-wide cap defaults (Colombia50%, Paraguay20%), progress from duration, prices from project financing, legal mappings from keywords or comparable rights from supplier names.
- No automatic payment audit, inflation acquisition, unit-price matching, legal library or cross-country supplier resolution. Source/schema evidence work remains necessary. Synthetic fixture success does not validate real contracts.
- `SCORE_VERSION` is **3.2** (A: buyer-relative late publication; B: French direct award only from the legal no-publicity threshold; C: tie-breaks by families then strongest signal; D: uniform 8-point weights; details and before/after counts in `docs/score-v3.md`). `data/score-v3-review.json` regenerated after script edits; existing observed score points are unchanged by the five missing-evidence checks, and since they are listed only on records carrying `indicatorEvidence` (9 checks per record, 10 for Tours), unknown-applicability counts do not increase. Old catalogue/help statements below describing nine checks are historical and not the expanded local catalogue. Audit methodology/help consistency before any proposed release.
- Tests: `tests/additional-indicators.cjs`, `tests/experimental-indicators.cjs`, plus adjusted country/import/catalogue suites. Example: `node tools/experimental-indicators.cjs tests/fixtures/experimental-indicators-positive.json` returns a **synthetic** diagnostic40, not a real index or legal finding.

### Indicator tuning follow-ups (2026-10-04)

- **Single-bid threshold calibration** (`tools/calibrate-thresholds.py`, `research/thresholds/results.json`, `docs/threshold-calibration.md`): the Fazekas & Kocsis method, per jurisdiction, with a predeclared rule. **No input met the rule anywhere, so no threshold was changed.** Some estimates point the same way as the current checks but fall short of the bar. Buyer×CPV3 concentration ≥40 % has OR 3.7 (CI 1.9–7.2) in France. Concentration ≥60 % has OR 10.8 in Czechia. Both are blocked because there are fewer than 20 buyer clusters, too few for reliable buyer-clustered errors. In France, delay and duration show no association with single bidding. That is expected for transparency and execution checks and is not a reason to demote them; a Codex AIC comparison of raw vs buyer-relative delay does not bear on why the check is buyer-relative. Root cause: the cohorts have too few buyers. Wider cohorts are needed before thresholds can be estimated.
- **Outcome labels** (`tools/collect-labels-colombia.py`, `tools/collect-labels-ukraine.py`, `research/labels/`): SECOP II Multas y Sanciones (`it5q-hg94`) and the DASU monitoring feed (`audit-api.prozorro.gov.ua`, 29,583 monitorings since 2024-09) give **0 matches** in the bundled cohorts. All labels are null. A label-first Ukrainian cohort built from monitored tenders is the realistic route, and it needs the owner's approval because it is a cohort expansion/download.

- **Ukrainian label-first cohort** (`tools/build-ukraine-label-cohort.py`, `tools/analyze-ukraine-label-cohort.py`, `research/labels/ukraine-cohort*`): 8,499 requests. It holds 1,250 tenders where the audit service found violations, 1,250 where it found none and 27 unconcluded, plus 1,282 unmonitored same-buyer comparison tenders (scanned only up to 2025-06-12). Labels come from monitoring status, which matched all 1,280 spot-checked conclusions, and 98 % of violations are typed `other`. Single bidding against submission period: under 10 days gives OR 3.19 (CI 1.76–5.78) against a reference of only 54 rows over 31 days. But 62 % of rows fall under 10 days, near what I believe is the wartime legal minimum, so a check would flag the norm; **not adopted**. Signal rates by outcome (smoothed LR, true vs false): single offer 1.30, better bid disqualified 0.60 (yet 36 % vs 11 % in comparison tenders, which fits the audit service picking tenders with disqualifications). Selection bias rules out weight changes from this cohort; **no Ukrainian weights changed**.

- **Legal-anchoring pass, score 3.3 (2026-10-04, owner-approved, uncommitted):** Paraguay amount increase anchored to Ley 7021/22 art. 67 (8 points from 19 % to the 20 % ceiling, 16 → 40 beyond; processes from 2024-02-19); the no-points `py-ceiling` context label and filter were removed. Pilot 35 → 36 flagged, three buyers 53 → 58. Every other country reviewed, unchanged with reasons in `docs/indicators.md` (legal-anchor table) and `docs/score-v3.md` (v3.3). Follow-ups needing primary legal text: Ukraine minimum tender period (Law 922-VIII / Resolution 1178), French R2161-x periods and R2194-x modification caps, Paraguay decree 2264/24 minimum periods; the BACN full text of Ley 7021 art. 65/67 was not readable.

### Dataset freshness — local normal UI

- New **`dataset-metadata.js`**, **`data/dataset-metadata.json`**, **`tests/dataset-metadata.cjs`**; rendered through `#dataset-dates` and `#dataset-date-notes`.
- All **14 coverage-backed datasets** represented. Distinguish local snapshot/observation date, coverage interval and publisher/source update date. A missing publisher update stays unknown; never fabricate it from a file timestamp, current date, URL directory year or snapshot date. Notes explain source-specific limitations.
- Dates appear in the normal local explorer; not a separate experimental display. These assets and UI changes are not deployed.

### Offline weight calibration — synthetic experiments, not real performance

- Owner wanted empirical weights across all indicators and a likelihood-ratio/logistic comparison. Implemented offline tools, not website scoring modes; both alternatives remain available. **No synthetic weights applied to website scores.** Detailed designs/results: `docs/calibration-experiments.md`.
- `tools/calibrate-indicators.py`, `tests/test_calibrate_indicators.py`: five pipelines (unweighted count, fixed family-max proxy, smoothed nonnegative LR, regularized nonnegative logistic, learned family-max); seven scenarios ×five seeds,4,000 synthetic rows/100 buyer groups per run; buyer split60/20/20 train/validation/test. Optional NumPy/SciPy/scikit-learn are research dependencies only; tests skip if missing.
- Scenarios: independent, correlated, family-max mechanism, pair interaction, outcome-dependent missingness, population drift and biased case discovery. AP/AUC use raw scores and respect ties; top5% precision/recall fractionally include boundary ties. Fixed proxy is not the complete actual real-contract score engine. Binary synthetic features do not capture all graduated real checks or legal eligibility.
- First comparison used different missing-data preprocessing, so its apparent logistic advantage under missingness (.421AP versus LR.242) was **not a fair method advantage**. Family-max has a disclosed built-in advantage in the scenario generated by that mechanism. No model dominates; simulation variability is not real-world confidence.
- Fair follow-up: `tools/compare-calibration-methods.py`, `tests/test_compare_calibration_methods.py`, seven scenarios ×ten seeds, identical training-mean imputation and grouped validation/test protocol for LR/logistic. Mean held-out AP (LR/logistic): independent.718/.716; correlated.521/.542; family-max.486/.485; interaction.541/.553; missingness.426/.419; drift.367/.363; biased discovery.691/.684.
- Modest directional logistic advantage for correlation/interactions; other differences small. Arbitrary practical tolerances were.02AP and.05 top5%precision; no scenario's entire paired interval clears these thresholds in either direction. Intervals crossing zero do **not** prove equivalence. No defensible real-world winner or justified real point values established.
- Mean imputation is only for latent offline ranking experiments, never evidence to display triggered checks or grant points. Discovery-bias simulation does not solve real positive-unlabelled selection bias. Nonnegative conditional coefficients are not causal importance or calibrated corruption probabilities.
- Outputs retained temporarily: `/tmp/contract-calibration-results.json`, `/tmp/contract-head-to-head.json`, `/tmp/contract-head-to-head-summary.json`. `/tmp` can disappear; scripts/docs are authoritative reproducible design, not these ephemeral files.

```sh
python tools/calibrate-indicators.py --output /tmp/contract-calibration-results.json
python tools/compare-calibration-methods.py --method both --output /tmp/contract-head-to-head.json
# Individual offline alternatives: --method lr / --method logistic
# This method switch filters reported results, not a website mode.
```

### Real-case source review and benchmark — latest completed follow-up

- Reviewed **16 World Bank Sanctions Board decision documents**, not16 independent corrupt contracts:148,147,146,65,67,134,80,57,107,89,84,101,58,62,132,133. Full decision/source passages, exclusions and standards: **`docs/calibration-real-case-review.md`**. Its initial “joins missing” result predates the newer Iraq documentary match; latest status is here and in `research/calibration/README.md`.
- Merits findings, reconsiderations and an appeal must not be double-counted. Four documents expressly establish/preserve corrupt-practice findings (146,80,132,133), not four independent exact-contract positives. API328 results are search hits, not unique decisions. Catalogue country metadata can disagree with decision narrative.
- Examples/exclusions:67 is rejected-bid fraud, not a positive awarded contract;101's successful successor appeal is neither a corruption positive nor a clean-contract negative;84/89 repeat underlying collusion case4;80 requires original41/cases77/110;132 preserves125 and is not a fresh episode.65 concerns fraud/conflict,107 expense fraud,62 drug-supply procurement fraud; do not relabel these corruption. URL directory year is not sanction date. No additional decision beyond the 16 listed was counted.
- Many mechanisms (bribes/commissions, conflicts, invented expert qualifications, forged guarantees, reimbursement fraud, obstruction) cannot be observed in public award metadata. None reviewed supplies a complete18-feature vector. This is a feasibility limitation, **not a measured false-negative rate**.
- Collection/assembly tools are standard-library Python: **`tools/worldbank-benchmark.py`**, **`tools/assemble-calibration-benchmark.py`**. Preserve retrieval times, hashes/provenance; validate project IDs, ambiguity/duplicate events; strip contacts; do not auto-label controls clean. Assembler now validates `documentary_records`, record-ID lookup/exclusion, corroborated-only documentary joins, source documents and conflicting values.
- Persisted research: **`research/calibration/README.md`**, **`case-links.json`**, **`benchmark.json`**, **`comparison-reviews.json`**, **`remaining-link-reviews.json`**. These are research artifacts, not normal website datasets or index labels. Final benchmark **11 rows: 3 case rows + 8 comparison candidates, 3 pending case links**.
- **Current usable administrative labels: 1 corruption-positive and 2 fraud-positives (Iraq overlaps both), 0 reviewed negatives.** Unknowns: 10 for corruption, 9 for fraud; irregularity remains unknown in all 11 rows. One tentative Bangladesh case has no assigned positive. `ready_for_fit:false` for every target; having two classes in a future file will not automatically satisfy adequacy/readiness.
- All eight candidates' basic public award facts were reviewed; **outcome review is still incomplete**. This is assistant documentary review, not independent expert validation/audit. No final contract-specific adverse or exonerating outcome established for these eight. They remain null, not false. Somalia archive requests were partly blocked; no retrieved decision is not evidence of no decision.
- Comparison selection: same project/group/currency, signing within366days, price ratio.25–4. **Do not match on procurement method**, which could condition away direct-award evidence. Pool is184award notices from six selected historical pages for Somalia/Bangladesh, not a representative complete procurement population. Fixed offsets drift over time.

#### Exact cases and remaining joins

- **Somalia Decision147**, `P168115`: `OP00104863`, `SO-MOF-176000-CS-CDS`, signed2020-09-16, USD500510.00, supplier platformID510969. Corroborated multi-field match; **administrative fraud-positive, corruption unknown**. Separate SCORE contract signed2018-11-20, USD330000 has different finding scope; do not propagate fraud across both. Obstruction and fraud are separate.
- **Iraq Decision146**, `P155732`: documentary record **`DOC-P155732-G3-2016`**, no award-noticeID. Full reference `EODP-MOE/T.E/G3`, actual signature2016-11-02. Audit lists a two-member JV (names kept out of the public repository; see the cited audit), USD9,785,978, matching decision. Procurement plan instead says USD10,785,978; both retained. Administrative corrupt/fraudulent-practice labels true; irregularity unknown. This establishes a contract link, not which JV member was respondent or company-wide guilt. Seven-to-ten mobile-substation revision occurred **before signature**, not an amendment flag.
  - Audit: https://documents.worldbank.org/curated/en/151361531916093371/pdf/EODP-Ministry-of-Elctricity-2017.pdf , printedp6/PDFp7, visually checked.
  - Plan: https://documents.worldbank.org/curated/en/667331509541481154/pdf/Plan-Archive-3.pdf , printedp2/PDFp4.
  - Decision: https://www.worldbank.org/content/dam/documents/sanctions/sanctions-board/2026/mar/Sanctions-Board-Decision-No-146.pdf . Source URLs/citations/SHA256s and discrepancy are persisted in manifest.
  - `OP00036262` is a **tender**, seven original units, deadline2016-04-06; not an award. G7 notice`OP00052335`, five units, USD4,860,000, signed2017-07-04 rejected as mismatching.
- **Bangladesh Decision148**, `P173757`: tentative`OP00102403`, `PACKAGE GD-13`, signed notice2020-05-28, BDT49,650,000, supplierID498003. Decision describes specialized ICU beds, approximatelyUSD572,500, signature during21–28May2020. Scope/currency reconciliation unresolved. Official2024plan adds USD584,736.99 and actual signature2020-06-10, conflicting with notice/window. **All labels remain unknown; no invented FX conversion or silent date reconciliation.** Supplementary plan: https://documents.worldbank.org/curated/en/099090924074531497/text/P1737571902c6a012195f31601825df9b67.txt .
- **Vietnam Decision134**: notice candidates`OP00028304` reference2.1 (`P123384`) and`OP00027043` reference3.3. Historical API confirms:
  - `P118610`, contract1519142, `2.1 PART 1`, signature2014-06-25, recorded supplier amount1,489,050.
  - `P123384`, contract1519141, `2.1 PART 2`, signature2014-11-14, amount2,945,937.
  - `P123384`, contract1517284, `CONTRACT 3.3/DSCDP-PIIP`, signature2014-04-02, amount3,904,419.
  - These are source supplier amounts, **not verified whole signed JV amounts/original currency**. Full parties/JV membership unresolved; a recorded supplier is not necessarily sanctioned respondent. QCBS/CQS source-method discrepancy for2.1 retained. Package2.1 fraud must not label3.3 fraud;3.3 is obstruction-related. Keep all linked packages/decisions together across splits; labels remain null.
- **DRC Decision133**, `P069258`, IDA3831-DRC: filtered historical source has51records/count51/top100, every projectID checked, source as-of11-Mar-2022. Two consulting records share exact2004-12-13 signature, Consultant Services/QCBS and the same recorded supplier (name kept out of the public repository: the decision anonymizes the consultant):
  -1246937, reference`296/SAPMP/SNEL-BCECO/DG/DPM/HMS/`, supplier amount3,517,321, Phase1feasibility/bidding documents/monitoring.
  -1246938, reference`297/SAPMP/SNEL-BCECO/DG/DPM/HMS/`, amount23,538,064, Phase2monitoring.
  - Strong paired-record/date/project/scope corroboration, but decision anonymizes Consultant, employer/party attribution remains inferential. Clarify target: corruption during consultancy execution versus corruptly awarded contractor works. Do not label consultant company guilty, use remuneration/payment vehicles EUR15,000/EUR40,000 as contract prices, assume original currency/full price, or count both agreements and reconsideration132 as independent episodes. **Research labels remain null.** Trailing slashes are preserved as recorded references, not claimed complete original references.

#### Eight comparison candidates — public-record facts, not clean outcomes

- Somalia`P168115`: `OP00092832` (`SO-MOF-169310-CS-INDV`,2020-05-19,USD156000,INDV); `OP00112083` (`SO-MOF-150489-CS-QCBS`,2020-09-24,USD274546.50,QCBS); `OP00125850` (`SO-MOF-155917-CS-CQS`,2021-03-25,USD179604.19,CQS); `OP00141709` (`SO-MOF-201599-CS-CDS`,2021-03-01,USD200000,CDS).
- Bangladesh`P173757`, allDIR: `OP00093630` (`PACKAGE GD-8`,2020-04-19,BDT92060000); `OP00102376` (`PACKAGE GD_3`,2020-05-20,BDT194600000); `OP00102738` (`PACKAGE GD-15`,2020-05-27,BDT197000000); `OP00102748` (`PACKAGE GD-5`,2020-04-17,BDT35000000).
- `comparison-reviews.json` records API URLs, dates, method/price, planned duration and source caveats. Multiple listed firms are not bidder counts; planned duration is not observed progress; publication date need not be the first publication in every venue. GD-5 title saysN95, scope saysKN95; retained as source discrepancy, not misconduct. No audited payments/acceptance/full losing bids/amendments/comparable unit prices obtained.

### Official endpoints, temporary evidence and reproduction

- Notices: `https://search.worldbank.org/api/v2/procnotices?format=json&project_id=P168115&rows=100&os=300` ; single notice same endpoint with`id=OP00104863`.
- Documents: `https://search.worldbank.org/api/v2/wds?format=json&qterm=Sanctions%20Board%20Decision&rows=10` . Administrative decision archive: https://www.worldbank.org/en/about/unit/sanctions-system/sanctions-board/decisions . Some official text downloads403; successful official`documents1.worldbank.org` counterparts used. Never treat HTML/error payload as decision text or bypass restricted access.
- Historical awards **DS01004/RS00934**, retired prior-review FY2001–FY2016 snapshot. Filtered request example: `https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice?datasetId=DS01004&resourceId=RS00934&top=100&type=json&filter=project_id%3D%27P069258%27` . Check returned projectIDs/counts and filter behavior, not just successfulHTTP. Vietnam filter was also checked with impossible-project negative query.
- Current **DS00005/RS00005** advertised FY2020onward; JV values split across supplier rows. FY2017–2019 coverage unresolved. Do not equate supplier portions with total contract prices or combine source snapshots indiscriminately.
- Temporary pool `/tmp/worldbank-comparison-pool.json`, assembly `/tmp/worldbank-benchmark.json`; persisted benchmark copied into research only after assembly. Case manifest fingerprint is checked by research tests.
- Temporary documentary evidence: `/tmp/wb146-deeper/` including visually checked`audit-p7.png`; `/tmp/research134-*`; `/tmp/drc-filter-final.json`; `/tmp/133.txt`; `/tmp/drccredit.json`; earlier `/tmp/wb-sanctions-research/`. These are ephemeral; persisted source passages/URLs/hashes are the restart record, not an assumption that cached bytes survive.
- `web_search` failed with provider error `Unsupported value: 'none' is not supported with the 'gpt-6.1-sol' model.` Use bounded official-source requests; do not pretend failed search verified anything.

```sh
# Selected historical pages, not representative/full-project collection:
python tools/worldbank-benchmark.py --fetch \
  --project P168115 --project P173757 \
  --offset 200 --offset 300 --offset 400 \
  --output /tmp/worldbank-comparison-pool.json
python tools/assemble-calibration-benchmark.py \
  --cases research/calibration/case-links.json \
  --pool /tmp/worldbank-comparison-pool.json \
  --output /tmp/worldbank-benchmark.json
# Inspect before replacing persisted research/calibration/benchmark.json.
```

### Verification limits and browser setup

- Full local site regression suite passed after indicator/metadata integration: JS suites and **136Python tests at that stage**, plus Chromium browser suite. Targeted local normal-UI/mobile integration passed in **Chromium and Firefox**. This is not a fresh full-suite claim after later calibration/benchmark additions.
- Latest focused benchmark/research verification: **20 tests passed** (7 World Bank collector, 9 assembler, 4 research snapshot tests), plus`git diff --check`. `tests/test_calibration_research.py` verifies case-manifest fingerprint, candidate fact consistency/unknown labels, documentary-vs-notice distinction, source-value conflict retention and no premature fit/corruption propagation. Calibration tools have their own previously passing focused tests; latest full combined suite still needs rerunning before a release proposal.
- Test-only Playwright1.58.2 in`/tmp/procurement-browser/node_modules/playwright`; Chromium`/usr/bin/chromium`. Firefox Playwright install stalled after download; archive manually unzipped to`/tmp/contracts-outreach-browsers/firefox-1509`; set`PLAYWRIGHT_BROWSERS_PATH=/tmp/contracts-outreach-browsers`. Use isolated temporary contexts/profiles and headless browsers; do not reuse, close or alter ordinary browser sessions. Reinstall only if temp directories disappeared.
- Temporary UI scripts/logs: `/tmp/contracts-outreach-check.cjs`, `/tmp/contracts-outreach-failure.cjs`, `/tmp/contracts-counter-check.cjs`, `/tmp/contracts-integrated-ui.cjs`, `/tmp/local-indicator-browser.log`, `/tmp/local-indicator-tests.log`, `/tmp/final-integrated-tests.log`. These are supporting session checks, not guaranteed retained fixtures.
- After **any** `script.js` edit: `node tools/review-score-v3.cjs`, then`node tests/score-review.cjs`; never manually fake report hashes. Language changes: edit`tools/i18n_table.py`, run`python tools/i18n-strings.py`. `tests/run-all.sh` includes additional-indicator, experimental-engine and metadata suites.

```sh
python -m unittest discover -s tests -p 'test_worldbank_benchmark.py'
python -m unittest discover -s tests -p 'test_assemble_calibration_benchmark.py'
python -m unittest discover -s tests -p 'test_calibration_research.py'
# Full regression when appropriate/authorized: sh tests/run-all.sh
```

### Actual stop point and next work — do not fit or publish yet

1. Read `research/calibration/README.md`, manifest, benchmark and both review JSONs first. Latest user-requested follow-up is complete as **documentary linkage/fact review**, not completed negative-outcome adjudication or real model calibration. Latest request is to preserve this information in handoff.
2. Resolve Bangladesh scope/date/valuation and Vietnam party/JV/full-value details. Clarify DRC observation-unit/employer attribution and Iraq respondent/JV scope plus conflicting price. Track subsequent remedies/corrections, exact lots/phases and finality independently.
3. Establish an explicit comparison-outcome protocol and independent substantive review; unaudited/uninvestigated contracts and missing sanctions are not negatives. If trustworthy reviewed negatives unavailable, consider a declared positive-unlabelled design, not silent null→false.
4. Build observed, applicable feature vectors independently of outcomes; retain unknowns. Fix feature cutoff/date windows and avoid deriving predictors from later investigation/judgment knowledge. Separate administrative corruption, fraud, audit irregularity, investigation and criminal conviction targets.
5. Predeclare sampling/population, case/project/buyer/time group holdouts, adequacy, metrics and review budget. Related contracts and repeated decisions must stay in one group. Current tiny/selective/mixed-country evidence does not justify generalized corruption probabilities, learned live weights, real precision/recall or a winner. Then compare LR/logistic on identical admissible features/processing and held-out groups; calibrate family-max directly if preserving it.
6. For usable new checks in the normal site, map a small manually reviewed public-evidence sample into`indicatorEvidence`; no auto-asserted verification. Keep empirical research separate from explorer scores. Recheck UI/help/method consistency and run regression/browser tests for any further edits. **No push, deployment, BASE rebuild or publication implied.**

## Previous checkpoint — Portugal BASE and earlier context (2026-10-02)

The following material is retained, including the pre-existing dirty Portugal work. Its BASE privacy/publication constraints remain relevant. Older outreach, branding, catalogue and test-status descriptions are superseded by the latest checkpoint above.

### Battery-only review (2026-10-02): current recommendation

- Owner cannot perform a technical review; the assistant conducted a bounded code/report review, not independent factual verification or legal clearance. **No publication authorized.** The follow-up bounded candidate check below passed with limitations. Findings, coverage reconciliation, source rechecks and exact verification limits: `docs/portugal-base-review.md`.
- Read only the private manifest/coverage, not candidate bytes or national archives. Candidate fingerprint below is reported, not freshly verified in this review. Private permissions checked; coverage counts reconcile, completeness remains unknown.
- Fixed importer subject redaction for exact single-word protected names, publication email rejection, and strict/canonical/size-bounded base64 validation. Existing candidate unchanged; no retroactive correction claim. Remaining gaps: name variants in subjects, decoded payload validity, public decoding/guessed-name matching, and schema validation cannot independently establish protection routing.
- Passed 43 tiny importer tests and 5 tiny inspection tests, plus `git diff --check`; no browser/full suite, rebuild, publication, commit or push. Two bounded official requests confirmed `other-pd` catalogue wording and privacy-page references, not field-specific legal permission. No inquiries sent.
- Follow-up owner authorization: checked the existing 10,255,719-byte candidate, not archives. Candidate/coverage/provenance fingerprints match; strict validation passes. No email/nine-digit-ID/tested phone/Portuguese IBAN pattern matches in subjects/display names. Reviewed 20 keyword-flagged descriptions: no individual contact/sensitive disclosures found. Five spaced protected-name samples decode/code-match correctly; a bounded subject-phrase/code audit found zero matches. See section 6 of `docs/portugal-base-review.md` for exact limits. No candidate changes, rebuild, full suite or publication; no evidence from these checks that a rebuild is needed.
- AC-power follow-up: owner authorized the full suite. All JS suites and 136 Python tests passed via `sh tests/run-all.sh` (~38 s); its browser step initially could not start because `/tmp` Playwright was missing. Restored test-only Playwright 1.58.2 outside the repository, then `node tests/browser.cjs` passed (~28 s), including HTTP/file://, CSP and mobile checks. All suite components passed; no publication, integration, commit or push.
- Next: full-suite authorization above was granted on AC power; do not infer permission for a national rebuild or publication. No publication approval has been given. Assistant does technical checks; owner only makes the release decision, not a fictional personal certification.

### User intent and limits

- Goal: make Contract signals useful and credible for public-sector review, without pretending that editorial signals detect corruption. The user has no budget/connections; prioritize an easy-to-share prototype, a small feedback request and useful deeper coverage over adding countries for breadth.
- **Battery restriction remains active:** do not run CPU-heavy work, whole-file scans/conversions, archive extraction, dataset rebuilds, Chromium or the full suite without checking that power/heavy processing is now authorized. The user explicitly authorized the three Portuguese downloads; that did **not** authorize the national streaming scan. Tiny synthetic tests and bounded metadata/prefix checks were allowed.
- **Names decision:** do not automatically anonymize all public suppliers. Retain published company and individual/sole-trader names where appropriate to identify contract participants, with source/context and no allegation or entity-type inference. Omit unnecessary personal tax IDs/contact data and unsuccessful bidder identities. Public access/open licensing is not blanket privacy clearance. The user wanted investigation of why fields are public, not just a generic “review personal data” disclaimer.

### Portugal BASE stop point (private pipeline, not the current calibration task)

- **BASE extraction (2026-10-01, AC power, about 6 minutes per run).** 655,235 national rows scanned; 3,986 in the window for the three buyers. The strict `NIF – name` rule kept 3,353; accepting holders published with a blank NIF keeps 3,966.
- **Names decision for BASE (owner, 2026-10-01): publish as the register does, but hard to collect in bulk.** A holder is a natural person when the NIF is blank or begins with 1, 2, 3 or 45 (in practice BASE blanks every such NIF: 615 holders, 475 distinct people, 613 contracts, mostly Município de Lisboa service contracts). Their names are stored scrambled (`supplierProtectedNames`: PBKDF2-SHA-256, 400,000 iterations, key from the record id; `scramble_name` in the importer, `revealProtectedName` in `script.js`, one shared test vector). Lists, search and exports show `Individual or foreign holder · <code>` (a blank NIF can also be a foreign entity, so the label does not claim a natural person); the code is stable per name, so repeat holders can be recognised. The record panel has a *Show name* button. A subject line repeating the holder's name is redacted to the same code (6 rows); a subject containing an e-mail address is set aside (1 row). **This is a deterrent, not secrecy**: the method is public and the names are public at BASE. Company names that contain a person's name (for example a law firm) stay as published.
- **Current private candidate:** 3,966 rows, 3 set aside, SHA-256 `309b17f2882f3ac2e171c82b5ee13e2835333965b67c477528d7256d45ea6a13`. Earlier candidates kept beside it (`base-candidate-strict-nif-2026-10-01/`, `base-candidate-plain-names-2026-10-01/`, the latter with names in clear: never copy it into the repository). **Not published**: `--publish-reviewed` needs the owner as named reviewer; then add the selector entry (browse-only), update the “All countries” row count in tests, and push.
- **Interface pass of 2026-10-01:** the record panel shows only what is specific to the record (about 1,200 characters instead of 5,600 on average). Dataset-wide notes (`dateNote`, `amountBasis`, `notes`, `identifierNote`, `offersNote` repeated on ≥20 % of rows) are listed once under “Scope and limits” (`sharedNotes`). Check reasons are cut to their first sentence (`briefReason`, translated first); all checks sit in a folded list. Table chips use short names (`KIND_SHORT`), one line each. Header: no logo, tagline “Explore published procurement records.”, the caveat moved into “Scope and limits”. Filtering and sorting no longer rebuild search text or recompute checks on every redraw (`assessmentCache`, `searchText`). New interface strings are in `tools/i18n_table.py` (`_NEW_EXACT`, `_NEW_PATTERNS`); the long method text in the help dialog and the source-link labels remain English.
- The three official ZIPs are already downloaded and present; **do not download them again**. Default cache is `~/.cache/contract-signals/base-archives/` (or `$XDG_CACHE_HOME/contract-signals/base-archives/`):
  - `contratos2024.zip`: 44,570,348 bytes.
  - `contratos2025.zip`: 55,274,614 bytes.
  - `contratos2026.zip`: 42,232,603 bytes.
  - Total 142,077,565 bytes; ZIP signatures, byte counts, streaming SHA-256 hashes and 0700/0600 cache permissions checked. Exact URLs/hashes: `data/portugal-base-downloads.json`. Binary files remain outside Git and the static web root.
- **Next:** review the existing private candidate before any publication; do not recreate it blindly. If an authorized rebuild is needed, preserve the existing evidence and use a distinct private output directory. Inspect coverage/exclusions/conflicts and review minimized names/subject text. Resolve needed source semantics/privacy questions. Only then explicitly publish the exact reviewed candidate and integrate a BASE dataset selector/source panel in `index.html`/`script.js`; keep it separate from TED and browse-only. No automatic BASE–TED joins or spending sums.

```sh
python tools/import-portugal-base.py                 # SAFE: plan only, no archives/network
# HEAVY: wait for power/explicit authorization; ~1.14 GB uncompressed input:
python tools/import-portugal-base.py --extract
# Only after reviewing the candidate; never invent a reviewer or hash:
python tools/import-portugal-base.py --publish-reviewed \
  --reviewer 'reviewer-or-role' --candidate-sha256 '<actual private manifest hash>'
```

- Private candidate defaults to `~/.cache/contract-signals/base-candidate/`: `candidate.json`, `coverage.json`, `manifest.json`. The eventual reviewed file is compatible with the existing local JSON import UI, even before a bundled menu entry is added. Both extraction and publication refuse differing existing outputs; investigate rather than deleting/resetting evidence to force a run.

### BASE implementation and source facts to preserve

- Frozen scope: buyer NIFs **503933813 / 508779472 / 500051070**; `dataPublicacao` from **2024-09-01 inclusive to 2026-09-01 exclusive**. Dates are strict DD/MM/YYYY input, not signing-date substitutions. Plan: `data/portugal-base-download-plan.json`.
- Each ZIP contains one deflated JSON array: `Contratos2024.json` (384,159,940 bytes), `Contratos2025.json` (437,904,158), `Contratos2026.json` (320,855,087). No whole archive was extracted. Prefix inspections parsed only three initial records/year, not representative or the selected-buyer cohort. Report pass reads max 64 KiB/member; nine samples share 39 fields (`data/portugal-base-inspection.json`).
- Importer is Python standard library, no network. It verifies archive fingerprints, frames JSON objects in bounded 64 KiB chunks (1 MiB/record, depth 64), filters scope, reconciles national/per-buyer counts, and caps cohort/output at 20,000 rows/<20 MiB. Equivalent **minimized** records are deduplicated; conflicting variants are all withheld. Syntax errors abort; normalization/date omissions are counted with reasons and make coverage uncertain.
- Names are extracted from strict `NIF – name` holder strings and retained, including multiple holders; NIFs, competitor identities and unrelated raw fields are not copied. Malformed strings go to review, not a fallback that leaks IDs as names. The source subject is retained, with review still required for incidental personal information.
- Mandatory `assessmentMode: browse`, `dataStatus: unverified`; `source` is the official dataset URL (not an invented contract-detail URL), `date` is publication date, signing/award/closure dates are separately labelled. Currency, duration months, direct-award status and offers remain unknown. No verified payments inferred from `PrecoTotalEfetivo`; sample zeros are not absence of spending.
- `--publish-reviewed` reads only the private candidate/provenance, requires reviewer + exact SHA-256, validates strict field whitelist/counts/hashes, refuses empty cohorts, and installs reviewer-bearing coverage before records. Review authorizes minimized redistribution/names, **not factual verification**. Publication is atomic per file, not a cross-file transaction; hard termination could leave coverage without records. UI remains unchanged by this command.
- Official catalogue maps `other-pd` to **“Outra (Domínio Público)”**, with no terms URL—not CC0. BASE explicitly recommends dados.gov.pt for raw downloads. Publication/reporting explanations describe the transparency pipeline, but dated 2022/2018–2019 references are not verified current field-specific mandates. Currency, `prazoExecucao` units, zero semantics and natural-person NIF publication/reuse scope remain to clarify. Evidence and public role contacts: `data/portugal-base-rights.json`; detailed guide/policy and unsent questions: `docs/portugal-base.md`.

### Work completed in this session

- **Audit/adoption:** reviewed methodology, provenance, UI/security/testing and live headers; credible prototype, not independently validated government service. Suggested first feedback targets: Rennes, then Nantes municipal procurement/open-data teams (municipal buyer, not an assumed metropolitan scope). Ask for one 10–20 minute public-record task, no internal data, endorsement or purchase. Templates/task/boundaries: `docs/adoption.md`. Nobody contacted; no email sent.
- **UI/import polish:** default closed advanced filters, visible search/signals-only/import shortcut. `import.js` adds CSV mapping, JSON/export-envelope/OCDS formats, preview then explicit confirmation, browse-only default, limits and unknown currency preservation. Explicit French opt-in does not verify records or enable generic cohort checks. Local notes use content/method/mapping SHA-256 identity; notes/plaintext imports bounded; CSV formula guard strengthened. See `docs/data-format.md`, `tests/import.cjs`, `tests/import-engine.cjs`.
- **Source rights/personal data:** BOAMP LO 2.0 supported by DILA + official API/dataset metadata despite null BOAMP catalogue licence fields. Limited Annuaire name/status/identifier enrichment LO 2.0 supported by its actual published dataset, not the API software MIT label. Evidence: `docs/source-rights-evidence.json`, `docs/data-sources.md`. `docs/personal-data.md` and `tools/audit-personal-data.py` distinguish public raw exposure, placeholders, meaningful fields and publication context. SECOP account-number fields are all placeholders here; supplier cédulas and other populated identity fields are a separate issue. No raw source snapshots sanitized/deleted by this session.
- **Repository presentation:** root `LICENSE` now standard MIT only; data notice in `data/LICENSE.md`; README has site link, screenshot (`docs/images/explorer.png`), explicit prototype status, privacy/storage distinction and licence/source links. Local machine path/hook details removed from handoff. User said they will add website to GitHub About; assistant did not change GitHub settings. Licence detection last observed as “Other” before these unpushed changes; recheck only after publication. No full Git-history secret scan performed.
- **Expansion:** `data/expansion-plan.json`, `docs/expansion.md`, `tools/expansion-plan.py` and cached `data/expansion-source-checks.json`. Priorities: same six French buyers' separate 2023 backfill; exact-ID complementary TED evidence; Portugal national coverage; then Indonesia/Russia feasibility. LKPP CKAN works, first hits aggregate indicators with empty licences—not awards/contracts. SIRUP/Russia single attempts failed at network layer, no retry/bypass or diagnosis of permanent blocking. Seven bounded metadata attempts cached; no Indonesia/Russia records added. `tools/download-base-archives.py` defaults to plan and streams only the three frozen official ZIPs with explicit `--download`; completed attempts skip.

### Verification and Git/deployment truth

- **2026-10-01:** fixed `bid_attrition` keeping partial decisions on unknown results (4 Ukraine rows; counts unchanged). Full suite passed on AC power: 119 Python tests, JS suites and Chromium HTTP/file:///mobile/CSP. All pending work committed as single-purpose commits on `main` after `3f858d1`; see `git log`. Check CI and the live site after each push.
- **2026-10-01 merge:** `origin/main` had 19 commits (26–27 Sep: v3.1 transparency family, UK/Chile/Czechia cohorts, All countries view, profiles, ES/FR interface, personal-ID masking, routine context labels, `ua-better-bid-disqualified`) that this local line had never seen. Merged rather than rebased. Owner decision: keep the remote 12-point Ukrainian disqualification check; the local `bid_attrition` result and linked contract records are context only. Remote additions to the inline detail row were ported into the side panel; the Indicator filter now lists shared kinds (`late-notice-change` added for Tours). Browser tests pin `locale: 'en-GB'` because the interface follows the browser language.

## Where things are

- Repository: https://github.com/La5u/contract-signals, default branch `main`.
- Licence: code and original documentation MIT (`LICENSE`); third-party data keeps source licences (`data/LICENSE.md`, `docs/data-sources.md`).
- Hosted at https://contracts.lasu.dev (Cloudflare Pages, from `main`).
- Historical beta workflow (owner's decision, 2026-09-26): direct-to-`main`, no pull requests; every push deploys. **Currently superseded by the no-push/no-deployment instruction above.** Passing tests alone is not release authorization.

## Binding constraints

- Vanilla HTML/CSS/JS, local JSON/CSV only: no backend, framework, build step, runtime API call, analytics or cookies. Must work over static HTTP **and** `file://` (local file picker). The CSP in `_headers` forbids inline scripts and inline `style` attributes (CSSOM `style.setProperty` is fine); the browser test serves pages with that CSP and fails on violations. Browser storage holds only the theme (`contract-signals-theme`), the advanced-filter state (`contract-signals-filters`) and the reviewer's own marks (`contract-signals-review-v1`), never imported data or tracking. Keep the UI plain and uncluttered: public-service look, no dashboard tiles or decorative colour.
- Interface in English, Spanish and French (2026-09-27): English is written in `script.js`/`index.html`; `i18n.js` swaps rendered interface text for the `i18n-es.js` / `i18n-fr.js` dictionaries, generated by `python tools/i18n-strings.py` from `tools/i18n_table.py` (edit the table, never the generated files; `tests/test_i18n.py` fails when they drift). A text node is replaced only on an exact match or a full-sentence `{slot}` pattern, and a captured slot stays as published unless it is itself interface text. When you change an English UI string, update its table row or it silently stays English. Source evidence (descriptions, notices, citations, `notes`, `exclusions`, `identifierNote`) stays in its original language — do not translate it. `'Définitif ferme'` in `script.js` is a DECP schema value, not UI text.
- The 2026-10-01 interface pass added new exact/pattern translations to `tools/i18n_table.py`. Some older redesign strings and long method/source text remain English; check the table rather than assuming every redesign string is absent.
- Never show unknowns as zero (“Not assessed”). The index is editorial, not a probability or a measure of gravity. No points for amounts, R2122 citations, projects, names, country or CPI. Correlated signals in one family are not summed. Official findings, audit dossiers, reported investigations and adjudicated outcomes stay outside the index.
- One indicator catalogue for every country (`docs/indicators.md`): each check maps to a universal kind; eligibility and thresholds stay specific to each jurisdiction's law and data. **All countries view** (owner's decision, 2026-09-27): every dataset listed side by side, ranked and filtered together, each still prepared on its own. Never convert currencies, never sum amounts across sources; the amount sort groups by currency.
- **Personal ID numbers are never republished in the explorer data.** Natural persons' national IDs (Colombian cédulas, Ukrainian RNOKPP, Chilean RUNs, cédula-based Paraguayan RUCs) become stable pseudonyms at import (`tools/personal_ids.py`, `masked-` + 16 hex); company identifiers stay. The raw snapshots keep the publishers' exact responses (lawfully public at source).
- Preserve PDFs (`docs/sources/`), raw snapshots (`data/*/raw/`), provenance, coverage files and `tools/legacy/scoring-v2.1.js` (frozen, not loaded).
- Do not add attribution trailers to commits, authorship, READMEs or documentation.

## Current state

- **Index v3.2** supersedes v3.1 below: counts BOAMP 432 / 2,566 / 12, Paris & Ardèche 358 / 1,881 / 355, six cities 149 / 949 / 172 (see `docs/score-v3.md`, section v3.2). Earlier description (v3.1, 2026-09-27): 14 checks per row since the five evidence-based ones (eight local + the universal `late-publication` + five), nine in v3.1, `min(100, max(competition) + max(execution/duration) + max(transparency))`. French review counts (from `data/score-v3-review.json`): BOAMP/CRC 535 positive / 2,466 zero / 9 not assessed; Paris & Ardèche 492 / 1,747 / 355; six cities 263 / 835 / 172; consultations and Tours all not assessed. (v3.0: 277/2,665/68, 404/1,835/355, 124/974/172.) Late publication = award published > 120 days after the contract date (above every EU/French legal deadline); out of scope for SECOP II, DNCP, Prozorro, Mercado Público and Find a Tender (its contract dates can be of old contracts being modified). In the DECP it mostly reflects buyer batch practice (Paris, Nantes). Tours adds a tenth, linked-notice check (6 evaluated zero, 60 not assessed).
- **Colombia** (SECOP II, 7,560 rows, 3 buyers): Colombian checks (`docs/score-colombia.md`): 272 flagged / 7,288 zero / 0 not assessed (215 before the term-extension check of 2026-09-26: `dias_adicionados` above +100 % of the declared term, 57 rows; the published end date is often not updated after an extension, so it is not used). CC BY-SA 4.0.
- **Paraguay** (DNCP OCDS, CC BY 4.0), Paraguayan checks (`docs/score-paraguay.md`): six checks plus two out of scope (single tenderer, CVE exception award, their per-supplier repetition in distinct OCIDs, buyer/category concentration, amount increase >20 %). Two separate cohorts, never merged: Fernando de la Mora pilot (84 rows; 35 flagged / 49 zero; checks written after reading this pilot) and MOPC / Central / Asunción (`paraguay3`, 293 rows, calls 2024-09 → 2026-09; checks fixed before download; 53 flagged / 240 zero / 0 not assessed, 118 partial). Importer: `tools/import-paraguay-dncp.py --cohort fernando|3buyers --offline|--download`; the 3-buyer raw records are gzipped (`mtime=0`, exact response bytes). Multi-lot processes stay unknown for single tenderer (no per-lot count). Amount amendments cluster at +20 %, likely a legal ceiling, not encoded.
- **Explorer outcome labels**: zero contract-linked final judgments in the bundled website datasets; one dated press lead (`crc-station-nuage`), status unknown (`docs/adjudicated-outcomes.md`). The separate local World Bank research benchmark now has administrative positives as described above; these are not website labels or criminal convictions.
- **Supplier names**: `tools/enrich-suppliers.py` looks up every typed French SIREN in both DECP cohorts (Paris & Ardèche + six cities) in the Recherche d’entreprises API. It keeps a name only when `statut_diffusion = O` and the SIREN matches exactly, then writes `supplierProfiles` into both datasets. The official data.gouv.fr dataset “Données des entreprises utilisées dans l'Annuaire des Entreprises” is labelled LO 2.0 and explicitly describes displayed full name, administrative/diffusion status, and identifiers; this supports the project's limited enrichment fields, not every API field/source. Evidence (fetched 2026-09-29 UTC, including response hash): `docs/source-rights-evidence.json`. Snapshot 2026-09-24: 1,960 SIRENs queried, 1,949 named, 10 withheld (restricted diffusion), 1 no exact match; names on 2,586/2,594 Paris & Ardèche rows and 1,116/1,270 six-city rows. The tool checkpoints to `data/.supplier-identities.partial.json` (gitignored), so an interrupted run resumes; after it, run `tools/update-cities-coverage.cjs` and `tools/review-score-v3.cjs`. Names are current, not historical, and never scored. `--offline` re-applies the snapshot without network access.
- **Paraguay context outside the index** (`docs/score-paraguay.md`): DNCP complaints (the 20 % ceiling label became a scored band in 3.3) (19 rows; participant names never imported), debarment in force at award date from `data/dncp-sanctions.json` (minimised snapshot via `tools/fetch-dncp-sanctions.py`; 0 rows on 2026-09-25), and per-lot evidence links (bid comparison tables / evaluation reports) on every award.
- **Prozorro reuse**: the [publisher’s developer page](https://prozorro.gov.ua/openprocurement) permits copying, publication, distribution and commercial reuse with attribution; no standard licence is named for API records. Do not infer CC BY from a separate data.gov.ua dataset entry. This clears the reuse gate, not the wartime completeness/validation gate.
- **DECP procedure alignment**: both cohorts now treat the exact label “Dialogue compétitif” as competitive. The six-city raw snapshot has no such label, so its published rows and index counts did not change; the importer and coverage mapping are ready for future snapshots.
- **Ukraine, Portugal, Romania** (added 2026-09-25/26): one shared engine in `script.js` (`NATIONAL_FAMILIES`, `getAssessmentNational`): single offer per lot, award without competition, both repeated per buyer+supplier in ≥3 distinct procedures, concentration by buyer+category counted in distinct procedures (a first run counted lots and inflated Romania: corrected). Ukraine (`tools/import-prozorro.py`, 488 contracts, 38 flagged; `reporting` skips offer/direct-award checks but retains concentration), Portugal and Romania (`tools/import-ted-cohorts.py`, 493 / 356 lots, 128 / 136 flagged). Methods: `docs/score-ukraine.md`, `docs/score-ted.md`; tests: `tests/national.cjs`, `tests/test_import_national.py`. Prozorro: the site search lists tender IDs (POST, pages start at 1, back off on 503), `/api/tenders/{tenderID}/details` gives the internal id, rows come from the official public API. TED: Search API v3 (429 when too fast), buyers matched by identifier spelling variants, never by name.
- **Brazil PNCP**: access works (page size must be 10–500; September timeouts were transient); no import yet, no licence declared.
- **Explorer layout (redesign 2026-09-29)**: deliberately plain, public-service styling (flat, square controls, standard blue links, yellow focus ring, no shadows or big figures). Top bar with help/method dialog and a Light/Dark/Auto theme (`theme.js` + CSS tokens). Dataset options sit under their country's optgroup without repeating it (`datasetLabel()` joins both for exports and summaries). Under the dataset/search row: the caveat and the Scope/Sources disclosures. One way to do each thing: filters live only in the sidebar (no shortcut figures or chips), badges describe but do not filter, the panel has no copy-link or search shortcuts (the address bar holds the link). Sort is the one kept overlap: headings sort, and the Sort list adds sorts no column offers. Advanced filters are closed by default; the open/closed choice is remembered in `contract-signals-filters`, and the panel folds below 1000 px. Groups: Signals / Contract / Your review / Context outside the index / local dataset import; Sort, Group and exports above the table. The indicator select is rebuilt per dataset (`computeOverview`) with only the checks it runs and their counts. Column headings sort (they drive the Sort control and the link).
- **Record panel**: rows open a side panel (`renderDetail`) instead of an inline detail row: header facts, review mark and note, then sections Signals (plain-language reasons first) → Record → Context outside the index → All checks → Verify it yourself. `open=<id>` in the link restores it; j/k and Previous/Next step through the filtered results; Print produces a case sheet (`body.print-detail`). Review marks live in localStorage keyed `<dataset>|<id>`, filterable (`#review`, not in the link), exportable/importable as `kind: review-notes` JSON (newer entry wins).
- **Verification**: “Sources and how to verify” panel per dataset (`sources` in the dataset registry: publisher, links, licence, raw path, rebuild command); “Verify it yourself” section per row from `verificationLinks(c)` (only URLs published in the data, human-readable pages first) and `verificationIdentifiers(c)`; `Verify:` lines in copied summaries; `verifyUrls` export column. All panel links were checked HTTP 200 on 2026-09-25 (DNCP `publicationPolicy` `/datos/legal` is 404; `/datos/aviso-legal` is used). BOAMP-published dataset content is documented as LO 2.0 based on DILA/data.gouv.fr terms; null API catalogue metadata does not leave that dataset licence unresolved. Third-party attachment/content scope and privacy questions remain. Retained evidence is in `docs/source-rights-evidence.json` (`docs/data-sources.md`).
- **Linked checks (2026-09-28)**: `docs/linked-evidence.md`, `tools/linked_evidence.py`. Tours: six exact correction/lot pairs extend deadlines, no signals. Ukraine: 26 multi-bid awards lack complete explicit disqualification evidence (unknown), 462 out of scope; no added flags. Since the 2026-10-01 merge only the Tours rule is scored; Ukrainian bid attrition is context only. Both rules carried 5 points within competition maximum, never added to stronger signals. Three contract API records fetched through `tools/fetch-linked-records.py` (plan by default, hard budget 3, serial/3s, cached, no retries/redirects, persistent 403 block and 429/503 cooldown). All three exact tender/contract joins verified; one publishes a change, two change lists absent. `data/prozorro-contract-links.json` is minimized; raw cache gitignored. Linked history is context, not amendment points.
- **Ukraine audit (2026-09-28)**: `tools/audit-prozorro.py`, `data/prozorro-audit.json`, `docs/ukraine-audit.md`. 542 raw records reconcile to 526 buyer-matched tenders / 488 retained contracts; 16 search-buyer mismatches excluded. All 64 competitive offer counts match. Seven sampled live tender/contract/award/supplier identities match; five assessed offer counts match, two reporting counts unavailable. Search completeness (including the recorded 500-result Vinnytsia listing) is not independently verified. No cohort expansion downloaded yet.
- **Badges and sorting**: buyer, supplier, CPV and offers headers sort too; all triggered indicator badges are visible (descriptive only); the record panel starts with a complete triggered-indicator list. Existing `sort=offers` links remain ascending.
- **Explorer features**: view state in the URL fragment (`#dataset=…&q=…&sort=…&page=…&size=…&open=…`, defaults omitted; `hashchange` reloads when the dataset differs); CSV/JSON export of every filtered record (formula-guarded CSV, empty = not assessed); “Import a dataset” in the closed-by-default advanced filters (`docs/data-format.md`); `<meta name="referrer" content="no-referrer">`.
- **Routine context labels outside the index** (added 2026-09-26; no index value changed, `data/score-v3-review.json` counts identical): filter *Legal context* and a row note. **France · single-vendor software maintenance** (`softwareMaintenanceContext`, `docs/score-v3.md`): software CPV (48/7221/7225/7226) or explicit progiciel/licence wording, plus maintenance/support/licence wording, plus one vendor (direct award, R2122-3 cited, or unclassified procedure with one offer; competitive single-offer lots are not labelled). 30 rows (BOAMP 4, Paris & Ardèche 25, six cities 1); five of the six top Paris & Ardèche rows; 28/30 read as vendor-product maintenance. **Colombia · public-to-public agreement** (`secop2PublicCounterparty`, `docs/score-colombia.md`): declared interadministrative justification (436 rows), or comodato/empréstito whose counterparty document is the counterparty of such an agreement (6 rows); withheld on 133 declared rows whose counterparty has a personal document or a *junta de acción comunal* name. 442 rows, 28 of them flagged; about 86 % public counterparties by name review (93 % with indigenous authorities and mixed funds), the rest private bodies the buyer declared as interadministrative.
- **United Kingdom** (added 2026-09-26): Find a Tender OCDS API, Open Government Licence v3.0 (`tools/import-find-a-tender.py`, `docs/score-uk.md`). The API cannot filter by buyer: `--discover` indexes every award release of the window in **one-day windows** (the cursor repeats releases and skips some over month-long windows: 366 vs 1,759 for September 2024), 33,457 releases; buyers announced from that index by volume only: FCDO `GB-FTS-131`, Lincolnshire County Council `GB-FTS-39`, Milton Keynes Council `GB-FTS-289` (ids above 500 notices left out). 516 notices, 1,081 single-supplier awards, 43 flagged / 1,036 zero / 2 not assessed. Same national engine (`NATIONAL_FAMILIES.fts`); supplier identity is the platform party id, which splits some companies across ids, so repetition can only be undercounted. Contact points never imported. The API rate-limits bursts (429): one request per second.
- **Chile** (added 2026-09-26): Mercado Público OCDS API, CC0 1.0 (`tools/import-chilecompra.py`, `docs/score-chile.md`). Licitaciones only: direct deals (trato directo) are purchase orders, not in this source, so the direct-award checks are out of scope. `--discover` lists every tender code per month (224,704; August 2026 answered 404) and maps each purchasing-unit prefix to its buyer (4,582); units announced from that map by volume: MOP `CL-MP-2015` (DGA tenders), Gobierno Regional del Maule `CL-MP-2592`, Municipalidad de Puente Alto `CL-MP-3414`. 844 tenders, 522 single-supplier awards, 71 flagged / 449 zero / 2 not assessed. Tenderers are per tender, not per line item; identity by RUT. The API returns some errors inside HTTP 200 bodies: 47 award records answered status 500 on every retry and are counted as unavailable.
- **Czechia** (added 2026-09-26): TED cohort (`--cohort czechia`), Ministry of Finance / Moravian-Silesian Region / Ostrava, 661 notices, 674 lots, 201 flagged / 473 zero / 0 not assessed with v3.1 (183 / 438 / 53 before); 279 lots use `oth-single`, left unclassified. TED answers empty HTTP 202s to fast clients: the importer waits 2 s and retries.
- **All countries** (`dataset=all`): loads every dataset (18,501 rows, about 3 s), country shown under each date; sort *Signals · newest first* (`recent-signal`). The *Indicator* filter lists universal kinds; old check ids in saved links still work (`indicatorKind`). Needs HTTP: under `file://` the combined fetch fails.
- **Buyer and supplier profiles** (2026-09-27): *Buyer profile* / *Supplier profile* buttons in each row's detail open a panel (`buildProfile`, `profileKey`): contracts, assessed and flagged counts, each indicator kind's rate against the whole dataset, top counterparts, amounts by currency (count and largest, never summed). The table filters to the profile's contracts until closed. Profiles never cross datasets (key = dataset + identifier); masked personal IDs still group one person's contracts.
- **Indicator chips**: the Indicators column lists every signal, heaviest first, with its family; a second signal in the same family is dashed and marked “not added” (only the family maximum counts). Routine context labels (French software maintenance, Colombian public-to-public, Paraguayan 20 % ceiling) appear as grey dotted chips from `contextLabels(c)`. On phones, where that column is hidden, a “Signals:” and a “Context:” line sit under the subject.
- **Explorer**: Date, Declared amount, Indicators and Index headings sort (they drive the Sort control and the link). Full-width rows span only visible columns (`visibleColumnCount`), fixing a phone layout where opening a row squeezed the subject column.
- **Languages** (2026-09-27): *Language* selector in the header; choice from `?lang=` > this browser's saved choice > browser languages > English. Dates and amounts use the chosen locale (`i18nLocale`). Translated: controls, headings, notes, status, chips, check labels and states, profiles, the frequent check reasons of every country. Still English: dataset descriptions (`sources`, `notes`, coverage text in the data files), the long method text, rarer reasons and tooltips assembled from several parts. Untranslated text stays English rather than being guessed.

## Tests

```sh
sh tests/run-all.sh      # every suite; NO_BROWSER=1 skips Chromium. CI runs the same (.github/workflows/tests.yml)
```

Playwright **1.58.2** is test-only, installed in `/tmp/procurement-browser` (reinstall with `npm install --prefix /tmp/procurement-browser playwright@1.58.2` if `/tmp` was cleared; Chromium at `/usr/bin/chromium`, or `CHROMIUM_PATH`). Never add it to the site. Historical verification:72Python tests on2026-09-29 and119on2026-10-01. Later full local site verification passed136Python tests and JS/browser components; subsequent research additions have focused verification only, as detailed in the newest checkpoint. Do not claim fresh full-suite/CI/deployment verification from those focused runs.

**After changing `script.js`:** `node tools/review-score-v3.cjs`, then `node tests/score-review.cjs` (the report binds the script's SHA-256). After city scoring changes, also run `node tools/update-cities-coverage.cjs`.

**Rebuilding data:** every dataset now has an `--offline` importer (table in README). All were re-run on 2026-09-25 with no drift. The Paris & Ardèche and BOAMP importers were rebuilt from the journal and checked field by field against the originals (`rebuild` in `decp-coverage.json` and `coverage.json`); tests assert the published files equal the importer output.

## Current local import behavior

- File selected explicitly; JSON/CSV is read in the browser only. CSV mapping/preview and separate confirmation are required before replacing the current dataset. Limits: 25 MiB and 20,000 normalized records. A changed file, method or mapping invalidates the preview.
- Browse-only/no scoring is the default. French v3 is explicit opt-in, but records defaulting to `unverified` remain excluded; opting in verifies neither jurisdiction nor provenance. Missing `source` and `currency` are not invented, and no EUR is assumed. JSON accepts record arrays and the explorer export envelope; OCDS accepts compiled/single releases and award rows only. Duplicate OCID versions and incomplete URL-only references are rejected; an OCDS award is not necessarily a signed contract.
- Imported-file reviewer notes are keyed to a stable SHA-256 of file text, method and mapping. Notes exports are plaintext: never put protected casework or sensitive information in them. The generic importer does not establish completeness or enable built-in-cohort repetition/concentration.
- `tools/audit-personal-data.py` produces aggregate field-presence indicators for reviewing raw/source data; its scan is heuristic and does not print values. See `docs/personal-data.md` before expanding imported/published fields.

## Cautions

- Read `docs/score-v3.md` before touching French scoring and `docs/score-colombia.md` before Colombian scoring. Never apply French thresholds to `secop2` rows; never turn the bare “Contratación directa” modality into a signal.
- The top of the default (index-descending) ranking contains many routine cases: proprietary-software maintenance in France, and in Colombia *comodato*, *empréstito* and interadministrative agreements with public counterparties. Examine flagged **and** unflagged examples before changing thresholds.
- Browser test regexes depend on exact UI wording (e.g. `/lots other than/`, `/not historical/`); keep them in sync, and keep the English key in `tools/i18n_table.py` in sync too (the Spanish/French browser checks look for `Ordenar`/`Trier`, `Señales:`/`Signaux :`).
- Commit convention: single-purpose commits, descriptive body, no attribution trailers.

## Historical battery-friendly expansion research (2026-09-30)

The following records the earlier inspection stage, not the current stop point. The 2026-10-01 private extraction and 2026-10-02 review above supersede statements that no candidate/extraction exists.

- Plan in `data/expansion-plan.json`, findings in `docs/expansion.md`, bounded official metadata observations in `data/expansion-source-checks.json`. No new procurement rows imported or scored.
- France: freeze the same six SIRETs for a separate 2023 notification backfill; confirm historical availability before record collection. Complementary TED evidence requires an immutable exact-ID list before fetching.
- Portugal: IMPIC national contract metadata found on dados.gov.pt; licence label `other-pd`, exact terms still to review. 2026 resource files are ~42–49 MB. After explicit authorization, ZIPs for 2024–2026 were downloaded to the private external cache (142,077,565 bytes total), not extracted/imported or added to Git; plan and hashes in `data/portugal-base-download-plan.json` and `data/portugal-base-downloads.json`. `tools/download-base-archives.py` defaults to a network-free plan; `--download` streams only the three fixed URLs. Buyer scope remains the existing three NIFs; new national records start browse-only.
- BASE steps 1–2 completed as bounded inspection: ZIPs contain single 321–438 MB JSON arrays, not spreadsheets. Only 64 KiB/three initial records per year inspected; nine samples share 39 fields, including separate publication/signing dates, numeric prices and NIF/name lists. No full-file scan or import. Reports: `data/portugal-base-inspection.json`, `data/portugal-base-rights.json`; method/minimization/questions: `docs/portugal-base.md`. Official `other-pd` means Other/Public Domain, not CC0 or privacy clearance; duration units/currency and field-specific publication scope remain unverified. Tool: `python tools/inspect-base-archives.py --write` (bounded prefixes only).
- Candidate importer implemented in `tools/import-portugal-base.py`, with only tiny synthetic tests run. Default is plan-only. `--extract` is the later heavy full scan: exact buyer/publication scope, bounded streaming, private output, minimized conflicts/reconciliation. Published supplier names are kept as participants, not classified/accused; supplier NIFs and competitor identities omitted. `--publish-reviewed --reviewer ROLE --candidate-sha256 HASH` checks exact private candidate/coverage hashes and whitelist before writing the separate browse/unverified JSON and coverage; it does not alter the UI. No real extraction, candidate, published BASE files or selector entry yet. Existing local JSON import can browse the eventual reviewed file.
- Indonesia: LKPP CKAN metadata search works; first hits are aggregate indicators with empty licences, not contract records. SIRUP and Russia EIS failed a single network attempt; no retries or bypass.
- `python tools/expansion-plan.py` is network-free by default. `--probe` permits only seven fixed metadata URLs (128 KiB/reply, 12s timeout, serial/2s, no retry/redirect, cache all attempts, stop on 401/403/429/503). All current attempts are cached; resource links are never fetched.
- While on battery: no CPU-heavy scans/rebuilds, whole-file conversion, browser tests or full suite. Explicitly authorized Portuguese downloads are complete and do not authorize the full scan. Focused tests/metadata checks only; full-suite verification of the new tools remains deferred.

## Task for a later Claude Code session: newly created supplier (France)

Parked on 2026-09-27 at the owner's request. Run it from a machine or environment where `recherche-entreprises.api.gouv.fr` answers reliably (it failed ~80 % of requests from the cloud).

1. In `tools/enrich-suppliers.py`, keep `date_creation` (legal-unit creation date, same API response already fetched) in each identity record, next to `name`, only when `statut_diffusion = O`. Re-run `python tools/enrich-suppliers.py` (resumable checkpoint; ~2,000 SIRENs), then `node tools/update-cities-coverage.cjs` and `node tools/review-score-v3.cjs`.
2. Add a universal check, kind `new-supplier` (competition family), for both DECP cohorts: the winning SIREN was created less than N months before the contract date (propose N = 6; read flagged **and** unflagged examples before fixing it, as the Cautions require). Unknown when the creation date is missing or restricted, never zero. Other countries: out of scope until a registry with creation dates is imported.
3. Add it to `INDICATOR_KINDS`, `docs/indicators.md` and `docs/score-v3.md`; update the review counts, `tests/scoring-v3.cjs` expectations, and this file.

## Next steps

1. **Hosting: live at https://contracts.lasu.dev** (Cloudflare Pages, deploys on push to `main`; CI runs `tests/run-all.sh`). `_headers` sends the CSP; `404.html` returns real 404s. Keep Rocket Loader / Email Obfuscation / Web Analytics off and `lasu.dev` on auto-renew.
2. **Remaining rights questions:** BOAMP-published dataset content is supported as LO 2.0 by DILA's legal notice and official data.gouv.fr dataset records; clarify only third-party attachment/content scope and any exceptions, not the dataset licence itself. The Annuaire dataset explicitly supports LO 2.0 for the limited supplier name/status/identifier enrichment used here, not every API field/source; clarify additional fields only if used. Evidence fetched 2026-09-29 UTC is retained in `docs/source-rights-evidence.json`. Also Brazil PNCP (none declared). Prozorro’s open-data reuse terms are confirmed (attribution required; no named licence for API records). TED is settled: free reuse under Commission Decision 2011/833/EU.
3. **Reduce routine noise at the top of the ranking**: label or exclude public-to-public Colombian contracts; add a context label (not a score change) for French single-vendor software maintenance.
4. **New cohorts:** validate wartime coverage and cohort completeness before expanding Prozorro; the Portuguese regional buyer (CIM do Cávado) yields 1 row because its notices link no winning tender (kept as announced); consider national portals (BASE, SEAP/SICAP) for below-threshold coverage; a Brazil PNCP pilot needs a reuse-licence check first.
5. Colombia: offers/proposals and payment reconciliation before any attrition/payment indicator. Paraguay: per-lot tenderers exist only in PDFs (bid comparison tables, now linked on every row); read DNCP Resolución 230/25 art. 181 before relying on the separate 20 % for unilateral changes; more buyers only with a pre-announced cohort.
6. Possible: native DECP field mapping and additional jurisdiction-specific import modes (generic CSV/JSON/OCDS browsing is implemented); Git LFS or release assets if raw snapshots grow (raw snapshots total about 70 MB, gzipped where large; the largest single file is 17 MB).
### Retired planning notes (not current instructions)

The notes below are retained only as historical context. BOAMP/Annuaire reuse evidence, Prozorro reuse terms, procedure alignment and generic import were resolved above; do not redo them based on these old notes.

2. **Earlier licence questions (superseded):** BOAMP and Annuaire dataset LO 2.0 evidence is documented; Prozorro permits reuse with attribution without a named standard licence. Brazil PNCP remains unresolved. TED reuse is settled.
3. **Routine noise, what is left** (labels above are done): Colombia's 18-point band is mostly 74 *Conservación Rutinaria Manual* road agreements with juntas de acción comunal declared under “No existe pluralidad de oferentes” (community agreements, not public-to-public): decide whether they deserve their own context label. Public counterparties never declared interadministrative stay unlabelled (INFIMANIZALES empréstito at 40, Asamblea Departamental comodatos): only a registry of public entities' NITs would catch them, not a name rule. France: the rule does not tell a vendor's product from bespoke software (2 doubtful rows) and trusts the CPV (a Tours gates works contract carries software CPV 48921000).
   **Network (2026-09-26):** the cloud environment reaches the UK, Chile, TED, SECOP and Prozorro hosts. French government hosts (recherche-entreprises.api.gouv.fr, data.gouv.fr) answer only about 2 requests in 10 from the cloud.
   Examined and not added: French threshold splitting (`docs/score-v3.md`) and TED frameworks over four years (`docs/score-ted.md`). No human blind review is planned (no people or budget): precision figures remain the documented reads of samples.
4. **Resolved procedure alignment:** both DECP importers now map “Dialogue compétitif” as competitive. The six-city snapshot contained none, so counts did not change.
5. **New cohorts:** confirm the Prozorro data licence; the Portuguese regional buyer (CIM do Cávado) yields 1 row because its notices link no winning tender (kept as announced); consider national portals (BASE, SEAP/SICAP) for below-threshold coverage; a Brazil PNCP pilot needs a reuse-licence check first.
6. Colombia: offers/proposals and payment reconciliation before any attrition/payment indicator. Paraguay: per-lot tenderers exist only in PDFs (bid comparison tables, now linked on every row); read DNCP Resolución 230/25 art. 181 before relying on the separate 20 % for unilateral changes; more buyers only with a pre-announced cohort. 
7. **Languages:** translate the dataset descriptions and method text (move them into the table as whole paragraphs), then Portuguese/Ukrainian/Czech/Romanian if people from those portals use the site. Consider sending a `lang` in copied summaries.
8. Possible: generic DECP/OCDS import for people’s own buyers; Git LFS or release assets if raw snapshots grow (raw snapshots total about 70 MB, gzipped where large; the largest single file is 17 MB).
