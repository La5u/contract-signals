# Project handoff

Updated: 2026-10-12. Current state only; delivery history is in [docs/project-journal.md](docs/project-journal.md).

## Project and standing instructions

- Contract signals is a static public-procurement explorer that flags contracts for closer review. Plain HTML/CSS/JavaScript; no build step or runtime API calls.
- Accuracy comes before expansion or scoring changes. Prioritize authoritative evidence for zero amounts and missing fields. A signal is not proof; source agreement does not establish upstream truth.
- Use public evidence and transparent open-source methods. Buyer-request drafts are historical, not the next step. Keep unresolved fields visible; never infer amounts, allocate ceilings, sum versions/holders, convert currencies or turn null into zero.
- Keep jurisdiction-specific checks and the family-max review index. Do not introduce corruption probabilities or learned weights without adequate independently reviewed labels. Read the relevant country method before changing scoring.
- Keep appropriate published supplier names, but omit unnecessary personal IDs, contacts and unsuccessful bidder identities. Source reuse terms and privacy limits still apply.
- Keep raw live responses, scans, migration archives and private evidence outside the repository/server root, under `~/.cache/contract-signals/`. Never upload the migration ZIP.
- Battery restriction remains active: check power and authorization before heavy scans, conversions, extraction, rebuilds, large downloads, Chromium or the full suite. Earlier bounded downloads/full-suite runs do not authorize national rebuilds.
- Use single-purpose commits with descriptive bodies and no AI attribution or attribution trailers. Preserve existing work. Give bounded progress updates and accurate completion claims.
- Pushing `main` deploys Cloudflare Pages at https://contracts.lasu.dev; release requires owner approval. Keep Rocket Loader, Email Obfuscation and Web Analytics off; keep `lasu.dev` on auto-renew.

## Current state

- All work through the Ukraine random-sample check of 2026-10-12 is committed locally, not pushed or deployed. Older checkout, branch and deployment checkpoints are superseded.
- Latest score version: **3.5** (owner-approved 2026-10-13, revised 2026-10-14; branch `research/ukraine-calibration-v3.5`, uncommitted). Ukrainian points come from court verdicts and AMCU bid-rigging decisions, points = 10 × log2(shrunk LR) ([research/calibration/ukraine-results-2026-10-14.md](research/calibration/ukraine-results-2026-10-14.md)). `ua-single-offer` 12 → 1 (data say 0; owner kept a point), `ua-better-bid-disqualified` 12 → 4, `ua-contract-amendments` 8 → 6 at 3–4 and 10 at 5+, plus 6 with a term extension; new `ua-term-extension` 4. Ukraine has **50 contracts with a positive score** (48 in 3.4). Points are per jurisdiction; other countries unchanged. The frozen Ukrainian public-audit plan replays from its 3.4 selection scores in `data/ukraine-public-audit-scores.json`.
- France DECP is one explorer entry: **5,286 rows / eight buyers**, backed by Paris/Ardèche (**2,997**) and six-city (**2,289**) files. Old `cities` links redirect to `decp`.
- Other cohorts: Tours notices **66**, BOAMP consultation notices **10**, BOAMP awards/audit dossiers **3,010**, Chile **522**, Colombia **7,560**, Paraguay **84 + 293**, Portugal TED **493**, Romania **356**, Czechia **674**, Ukraine **488**, UK **1,081**. Counts describe records, not independently validated unique contracts; see [README.md](README.md).
- French disagreements are displayed/exported as ranges; amount checks use the whole range. Duplicate clusters count once in buyer baselines. Dijon shared-procedure lots are split and linked; disputed offers stay null.
- CPV recovery applied **165 check digits (86 cities + 79 history)** using the pinned **9,454-code** official vocabulary. Raw evidence is preserved; assessed coverage improved.
- BOAMP↔DECP review: **7 active candidates / 2 dismissed leads / 0 confirmed links / 0 ambiguous active pairs**. Paris LOT-0001 and Nantes technical LOT-0003 leads were dismissed for conflicting lot evidence; no replacement identity was established.
- Three BOAMP↔TED versions are verified: **25-21317→126421-2025**, **25-21329→129139-2025**, **25-47556→277338-2025**, all version `01`. These verify notices, not DECP contracts. Two other XML versions remain unverified after HTTP 429.
- Ukraine audit: frozen **12-contract sample (5 flagged / 7 zero)** plus **11 amount differences**. Seven differences have explicit net/VAT basis evidence; **4 amount cases + 14 VAT-only cases** remain unresolved. No amount replacements.
- Ukraine amendment counts agree for **12/12** sampled contracts. Six omitted lists mean zero by the publisher's API rule; the sole 3+ flag has three active changes. Interpretation is an additive overlay; frozen evidence stays intact.
- Ukraine field check: **488 rows × 20 fields** match cached official records. A frozen **40-row random sample** matches live tender and contracting-module records; only **3 sampled rows are competitive**. This establishes reproduction of Prozorro, not agreement with signed contracts.
- Remaining limits include a mixed-currency minimum-amount filter with one numeric cutoff, incomplete historical holder coverage, and missing offers/dates/durations. The UK audit found nine rows without amount/currency and three notice-date fallbacks; see [research/uk-contract-multiplicity-review.md](research/uk-contract-multiplicity-review.md).
- Local import is browser-only, **25 MiB / 20,000 records** maximum, with preview/confirmation. Browse-only is default; French scoring requires opt-in and excludes `unverified` rows. Notes exports are plaintext; keep sensitive casework out.

## Run, test and reproduce

Use HTTP for combined datasets. Private scientific/document dependencies live in the venv; `/tmp` browser dependencies are ephemeral.

```sh
cd /home/lasu/coding/contract-signals
python3 -m http.server 8000 --bind 127.0.0.1
# Tests, when power/heavy-processing authorization permits:
source ~/.cache/contract-signals/venv/bin/activate
sh tests/run-all.sh
# NO_BROWSER=1 skips Chromium; CI uses .github/workflows/tests.yml.
# Restore browser dependencies if needed:
npm install --prefix /tmp/procurement-browser playwright@1.58.2
/tmp/procurement-browser/node_modules/.bin/playwright install chromium
```

- Set `PLAYWRIGHT_PATH` or `CHROMIUM_PATH` for alternate installations. Previous browser checks passed; a later run could not start after `/tmp/procurement-browser` disappeared.
- Ukraine audit tools no longer verify SHA-256 pins (removed 2026-10-12); hash fields in the frozen JSON are kept as metadata only. Replays still check content, mappings and counts.
- The optional scientific suite also has a calibration-catalogue mismatch: `test_calibrate_indicators.CalibrationTests.test_catalogue` expects **18 kinds**, while Score 3.4 has **19**, including `contract-amendments`.
- After any `script.js` edit: `node tools/review-score-v3.cjs`, then `node tests/score-review.cjs`. After city scoring edits, also run `node tools/update-cities-coverage.cjs`. Keep browser wording and `tools/i18n_table.py` in sync; regenerate translations with `python tools/i18n-strings.py`.
- Dataset offline rebuild commands are in [README.md](README.md). French rebuild order: both DECP imports → `python tools/build-decp-france-coverage.py` → `python tools/build-boamp-decp-links.py` → `python tools/review-link-resolutions.py` → score review.
- Public-link replay: `python tools/build-public-link-evidence.py`; `python tools/investigate-paris-ted.py --replay-public data/paris-ted-version-evidence.json`. Review overlays validate frozen inputs and fail closed when stale.
- Ukraine offline replays: `python tools/audit-ukraine-discovery.py`, `python tools/audit-ukraine-amendments.py`, `python tools/audit-ukraine-amount-bases.py`, `python tools/review-ukraine-amendment-documents.py [--version 1]`, `python tools/interpret-ukraine-amendments.py`.
- Random-sample replay: `python tools/check-ukraine-random-sample.py` uses private cache. Its `--plan` and `--fetch` stages are complete. Do not repeat frozen network runs or reuse unused request slots; new acquisition needs a separately reviewed plan.

## Open items

This merges the 2026-10-09 list with later follow-ups; older queues are superseded.

1. **Accuracy denominator:** the earlier sample lacked linkable notices for **76/90** contracts. Current notice preparation has **0 eligible/selected, 1,726 unknown, 3,560 outside scope**. Obtain primary-law/applicability and individual eligibility evidence before measuring accuracy. Preserve `~/.cache/contract-signals/notice-accuracy-review/v2-cpv/plan.json`. Public-document benchmark: **9 blocked / 0 eligible / denominator 0**; future selection needs a new freeze incorporating link dispositions.
2. **French amounts:** all **885 disagreements (782 Paris + 6 Ardèche + 97 cities)** remain unresolved; **519** differ by more than 2×. Annual/full-term equivalence is unproven. Investigate **25 notice-search candidates** with exact buyer/full-reference linkage. Decide whether to leave sorting values empty above 2×; no sorting rule changed.
3. **French links:** seek an authoritative public crosswalk from full Paris reference to short DECP ID and unique buyer/contract/lot. Never globally strip repeated years or terminal zeros. Larger Atexo exports need a bounded licensing plan. `checkQuerySyntax:true` validates syntax without executing a TED search; do not interpret it as zero hits.
4. **Offers and duplicates:** **7 Dijon notice-vs-DECP + 5 feed-vs-Ministry** offer disagreements; **25 flagged records / 10 duplicate clusters** lack resolution evidence. Dijon lot 8, `2024vdao017008` (**559,742.62 EUR**), appears in the award notice but not retained DECP inputs. Buyer offer-analysis reports remain the evidence gap; current work stays public-only.
5. **Ukraine:** obtain exact documents for the **4 + 14** financial cases under a separately reviewed redirect-aware attachment plan; the first attachment returned an unfollowed HTTP 302. Verify portal date filters and fixed-window listing before expansion. Vinnytsia now lists **506** records without an observed 500 cap, but historical completeness remains unproven. Court verdicts set Ukrainian points (v3.5) but are never attached to rows; DASU findings stay outside scoring. Direct award is still unmeasured: the verdict comparison sample has no direct-award reports.
6. **Verification and housekeeping:** resolve the calibration catalogue mismatch before release; restore browser tools as needed. Old `cities|` browser review marks no longer show. Historical housekeeping notes record `stash@{0}` (an old generated score review) and missing global Git identity; confirm before acting.
7. **Release:** owner decides deployment. Portugal BASE remains a private **3,966-row candidate / 3 set aside**, browse-only if released; publication is unapproved. Any release still needs its rights/privacy and coverage gates.

## Detail pointers

- Accuracy queue and evidence: [research/accuracy-priority.md](research/accuracy-priority.md), [research/notice-accuracy-review.md](research/notice-accuracy-review.md), [research/france-amount-disagreements.md](research/france-amount-disagreements.md), [research/france-unresolved-evidence-requests.md](research/france-unresolved-evidence-requests.md).
- French reconciliation: [research/france-cross-dataset-check.md](research/france-cross-dataset-check.md), [research/decp-dijon-conflict-review.md](research/decp-dijon-conflict-review.md), [research/decp-identifier-collisions.md](research/decp-identifier-collisions.md), [research/decp-cpv-review.md](research/decp-cpv-review.md).
- Public links: [docs/public-evidence.md](docs/public-evidence.md), [research/link-corrections-log.md](research/link-corrections-log.md), [research/paris-identifier-convention.md](research/paris-identifier-convention.md), [research/paris-ted-link-review.md](research/paris-ted-link-review.md), [research/public-document-benchmark.md](research/public-document-benchmark.md).
- Ukraine: [research/ukraine-public-audit.md](research/ukraine-public-audit.md), [research/ukraine-corrections-log.md](research/ukraine-corrections-log.md#1-omitted-amendment-list-was-silently-counted-as-zero), [research/ukraine-random-sample.md](research/ukraine-random-sample.md), [docs/score-ukraine.md](docs/score-ukraine.md).
- Methods, rights and privacy: [docs/score-v3.md](docs/score-v3.md), [docs/indicators.md](docs/indicators.md), [docs/data-sources.md](docs/data-sources.md), [docs/personal-data.md](docs/personal-data.md), [docs/data-format.md](docs/data-format.md), [docs/portugal-base-review.md](docs/portugal-base-review.md). [Prozorro reuse terms](https://prozorro.gov.ua/openprocurement) permit reuse with attribution; no standard API-record licence is named.
