# Outcome labels from official sources (research, not website data)

Contract-linked outcome labels for datasets the explorer already bundles, collected for a later positive-unlabelled calibration of indicator weights per country. These files are research artifacts: they do not feed the website or the index, and they make no claim of corruption.

## What was collected (retrieved 2026-10-03/04)

| Dataset | Source | Join key | Positives | Reviewed negatives | Unknown |
|---|---|---|---|---|---|
| Colombia SECOP II (7,560 contracts, 3 buyers) | datos.gov.co `it5q-hg94` "SECOPII - Multas y Sanciones", CC BY-SA 4.0 (ANCP-CCE) | `id_contrato` == `contractId`, exact | 0 | 0 | 7,560 |
| Ukraine Prozorro (488 contracts / 488 tenders) | DASU monitorings, `https://audit-api.prozorro.gov.ua/api/2.5/monitorings` | `tender_id` == `procedureId`, exact | 0 | 0 | 488 |

Both collections returned **no usable label**. That is a finding about these cohorts, not a defect to be patched by turning nulls into negatives.

### Colombia
- The sanctions register has 557 rows in total (all years, all entities); 465 point to SECOP II contracts outside the cohort and 92 have no SECOP II contract identifier. Only 2 rows belong to the cohort buyers' entity codes, both for older contracts (2018 and 2022 signature, one with no contract id), none in the 2024-09..2026-08 window.
- The dataset has no buyer NIT column. The cohort buyers' entity codes were taken from the SECOP II contracts dataset (`jbjy-vk9h`) with the exact NIT **and** buyer name, because NIT 899999061 is shared by many Bogota local mayoralties.
- Records are versioned drafts/comments with odd `estado`/`tipo` values; publisher completeness is not documented, so unmatched contracts are `null`, never `false`.
- Not joinable, documented and skipped: Contraloria fiscal responsibility `jr8e-e8tu` (person/NIT and resolution, no contract id), Procuraduria SIRI `iaeu-rcn6` (sanctioned natural persons, no contract id; not collected), SECOP I fines `4n4q-k399` (legacy platform, cohort is SECOP II only; 69 rows exist for the buyers but cannot match). SECOP II status `terminado` is normal completion, not breach; suspensions (`u99c-7mfm`) are not sanctions. No machine-readable `caducidad` / early-termination register keyed to SECOP II ids was found in the catalogue.

### Ukraine
- The audit API feed was read in full from the first cohort tender-creation date (2024-09-09): 29,583 monitoring entries over 30 pages. No entry references a cohort tender. A cross-check with `/tenders/{procedureId}/monitorings` agreed for a seeded sample of 40 cohort tenders (all empty) and for a positive control taken from the feed (total 1).
- DASU targets by its own risk indicators (see `docs/indicators.md`, sas-3-x), and these three buyers' 488 tenders were simply not selected (or not yet public). Unmonitored means `null`.
- Monitorings flagged restricted might not appear publicly; absence is not proof of no monitoring.
- The collector is ready for other label states: a concluded monitoring with `violationOccurred=false` gives `audit_violation=false` (reviewed negative, conditional on selection); `true` gives a positive; monitored but unconcluded (active, declined, stopped) stays `null`. `violationType` values starting `corruption*` are DASU checklist categories, kept as a separate target `audit_violation_corruption_category`, not a finding of corruption. Free-text findings, party names and documents are not stored.

## Files
- `colombia.json`, `ukraine.json`: provenance (URLs, dataset ids, licences, retrieval times, SHA-256 of every response), join diagnostics, per-contract rows `{dataset, id, labels, evidence, dates}`, summary counts.
- `association-colombia.json`, `association-ukraine.json`: descriptive indicator table from `tools/label-indicator-table.cjs`. With zero positives each reports "no comparison possible"; the helper was exercised on a synthetic labelling to confirm the output shape.

## Rerun
```sh
python3 tools/collect-labels-colombia.py                # offline plan, no requests
python3 tools/collect-labels-colombia.py --fetch        # serial, >=1.2 s spacing, budget 600, resumable
python3 tools/collect-labels-ukraine.py --fetch --spot-check 40
python3 tools/collect-labels-colombia.py --from-cache   # rebuild from cache only
node tools/label-indicator-table.cjs research/labels/ukraine.json data/prozorro.json research/labels/association-ukraine.json
python3 -m unittest tests/test_collect_labels.py
```
Raw responses are cached outside git in `~/.cache/contract-signals/labels/{colombia,ukraine}`. Delete the cache to refresh; cached feed pages are a snapshot (the last partial page will not grow). Requests made: Colombia 9, Ukraine 71 (budget 600 each).

## Use for weight calibration
May: use as a positive-unlabelled design once positives exist (positives vs everything else, with the selection mechanism stated), grouped by buyer/country, with the target kept separate (contractual sanction, audit violation, corruption-category are different outcomes).
May not: treat `null` as clean; pool Colombian sanctions with Ukrainian audit findings; claim the index detects corruption; fit anything on the present data (zero positives); treat DASU reviewed negatives as unconditional (they were selected by overlapping risk indicators). Extending to more buyers or to all monitored Prozorro tenders is needed before any fitting.

## Ukraine audit-outcome cohort (retrieved 2026-10-04)

A label-first research cohort, separate from the three-buyer website cohort above: Prozorro tenders whose State Audit Service (DASU) monitoring outcome is known, plus unmonitored comparison tenders. It is **not** website data (not in `index.html`/`script.js`) and makes no claim of corruption.

- Build: `python3 tools/build-ukraine-label-cohort.py` (plan, offline) / `--fetch` (serial, >=1.0 s spacing, 429/503 backoff, a 403 stops the run, hard cap 9,000 requests across resumed runs, counter in the cache) / `--from-cache`. Raw responses are cached gzipped outside git in `~/.cache/contract-signals/labels/ukraine-cohort/`. Test: `python3 -m unittest tests/test_build_ukraine_label_cohort.py`.
- Outputs: `ukraine-cohort.json.gz` (provenance with SHA-256 and retrieval time of every response, selection diagnostics, tenders with labels and monitoring refs, minimized contract rows), `ukraine-cohort-summary.json`, `ukraine-cohort-analysis.json` (from `tools/analyze-ukraine-label-cohort.py`, which imports `tools/calibrate-thresholds.py` unchanged and runs the site engine through `tools/ukraine-cohort-indicators.cjs`).
- Labels follow the DASU status standard: `addressed`/`completed` = violations found, `declined`/`closed` = no violations found, other statuses = null. The feed's `opt_fields` cannot return the conclusion, so the label is taken from the status; the monitoring detail was fetched for every sampled violation=true tender (violation types) and for 30 violation=false tenders as a spot check: 1,280 of 1,280 conclusions agree with the status mapping. DASU `corruption*` types are kept as a separate category target (30 tenders), never as a finding.
- Sample (seed `ukraine-audit-cohort-20261004`, SHA-256 ranking): monitorings created 2024-09-01..2026-09-01 (21,668 tenders in the pool: 13,526 true, 8,115 false, 27 unconcluded); 1,250 true + 1,250 false + 27 unconcluded sampled (sampling weights recorded). Of these, 1,135 / 1,197 / 20 have at least one signed-contract row (the rest were never contracted or have no unique supplier).
- Comparison tenders: one unmonitored tender of the same buyer, created within +-90 days, same procedure type when possible (1,050 same type, 232 other type), label null. Selection is recorded per tender for a positive-unlabelled analysis. **Coverage is partial**: the public tender feed has about 12 pages of 1,000 tenders per day, so a full scan (about 9,000 pages) did not fit the request cap; 3,100 pages cover tenders modified 2024-09-01 to 2025-06-12. 1,218 sampled monitored tenders have no comparison (created later, or no candidate). Comparisons are therefore time-skewed to the early window; each is matched to its own monitored tender. Only tenders with a signed contract row are kept as comparisons.
- Minimization: no supplier or buyer names, titles, contact data or free text; natural persons' tax numbers are masked (`tools/personal_ids.py`); buyer ids and company ids stay as published. The local raw cache keeps the exact responses (including public contact fields of buyers) and stays outside git.
- Requests: 8,499 in total (11 exploratory probes + the run). No throttling responses.
- Caveats: DASU selects tenders with its own risk rules that overlap the explorer indicators; violation=false is conditional on that selection; a monitored-not-in-feed or restricted tender looks unmonitored; the monitoring feed is read by modification date from 2024-09-01, so older monitorings of tenders created before that date are not seen (comparisons are limited to tenders created from 2024-09-01 for that reason).
- May: compare indicator rates between true and false audit outcomes, use the comparison tenders as unlabelled data. May not: treat comparison tenders as clean, treat violation types `other` (98 % of violations) as specific misconduct, claim detection of corruption.
