# Ukraine: bounded cached expansion v1

This is a **separate, unpublished-to-the-UI convenience cohort**, not a replacement for the three-buyer pilot. Subsequent replay/overlap/engine verification recommends **not registering this convenience sample as a general second dataset**; see [the verification and publication decision](expansion-candidate-decision.md). The pilot's 488 rows, raw manifest, amendment snapshot and audit evidence are unchanged. No national coverage or buyer-level completeness is claimed.

## Frozen scope and results

`data/prozorro-expansion/config.json` fixes the creation window (2024-09-01 inclusive → 2026-09-01 exclusive), tender IDs, official internal IDs, published buyer IDs, response SHA-256 hashes and original retrieval times. `contracts.json` contains normalized contract rows; `coverage.json` preserves per-tender provenance, including tenders producing no rows. Source bodies stay in the existing external cache; no full raw responses, contacts or attachments were newly published.

Selection: inspect the full-tender endpoint metadata pairs in the existing `labels/ukraine-cohort` cache, accept only HTTP 200 official `/api/2.5/tenders/{32-hex-id}` responses, require official `dateCreated` in the window, an eight-digit published buyer identifier, and exclude the pilot buyer IDs `00012925`, `20089290`, `26510514`. Rank by hexadecimal SHA-256 of `prozorro-cache-expansion-v1:` plus internal ID; freeze the first 100. No label, score, contract-status or amount filter was applied during selection. The local inventory contained **4,106 full cached responses; 3,856 eligible**. The committed allowlist, not a later scan of a changing cache, controls replay.

**Important bias:** that cache was collected for DASU audit/label research and comparisons (`tools/build-ukraine-label-cohort.py`). Hash ranking does not remove its selection bias. These are neither 97 complete buyer histories nor an administrative-level sample. Do not use them to estimate national prevalence or treat their supplier concentration/threshold splitting metrics as complete buyer histories. The original research labels are not imported or inferred to be clean.

Exact results:

- **100 tenders / 97 published buyer IDs** selected; **106 retained contracts / 96 buyer IDs** in the contract extract.
- **1 tender without retained contracts**, preserved in coverage rather than silently lost.
- **8 excluded contracts:** 7 cancelled, 1 pending.
- Procedures among retained contracts: 80 `aboveThreshold`, 22 `reporting`, 4 `belowThreshold`.
- All 106 amounts in UAH; published offers known on 84 rows; unknowns remain null.
- Original source retrievals: **2026-10-04T08:54:35+00:00 → 2026-10-04T11:57:48+00:00**. Expansion performed **zero network requests**. These are not fresh API observations.
- No amendment enrichment performed; missing counts are not zero. No payment, legal-validity, attachment, current-status or supplier-identity verification is claimed.

## Reproduce

From the repository root, with the existing response cache:

```sh
python tools/import-prozorro.py \
  --expansion-config data/prozorro-expansion/config.json \
  --cache-dir "$HOME/.cache/contract-signals/labels/ukraine-cohort" \
  --output-dir data/prozorro-expansion
python -m unittest tests.test_import_prozorro_expansion tests.test_import_national.ProzorroTests
```

The expansion path is strictly offline, accepts 1–5000 explicit tender entries, verifies source URL/status/body hash/retrieval timestamp plus official tender/buyer/date identities, rejects duplicates, and validates all entries before writing outputs. Missing or changed cached bodies fail closed. Expansion flags cannot mix with pilot `--download`, `--offline` or `--contract-changes`. Default pilot CLI behavior remains unchanged. Raw source hashes refer to original decompressed HTTP bytes, not reserialized JSON. Output contains the frozen config hash; rerunning against the same cache produces byte-identical files.

**Replay portability blocker:** full HTTP bodies are outside git. A checkout without the cache cannot fully regenerate the normalized extract; it can check the committed config/output provenance and counts. This mode deliberately does not silently redownload or substitute current responses for frozen hashes. A future fresh cohort needs a new configuration and budgeted collector, not reuse of these historical hashes.

## Parent integration instructions

1. Keep `data/prozorro.json` and its audit/score assumptions unchanged. Stage the importer, this doc, expansion-specific tests and `data/prozorro-expansion/{config,contracts,coverage}.json` together.
2. The independent expansion is available for research via `data/prozorro-expansion/contracts.json` (same `dataFamily: prozorro`, separate `cohortId`). Verify current downstream semantics before concatenating; never relabel it as the original three-buyer or a national cohort.
3. No UI, deployment, generic metadata or HANDOFF changes were made. UI/metadata inclusion, if wanted, belongs to the parent and requires explicit convenience-sample disclosure and incomplete-history treatment for concentration checks.
4. Country/buyer census expansion remains blocked by the discovery audit prerequisites in [ukraine-audit.md](ukraine-audit.md): resolve the original 16 buyer-association exclusions and establish pagination/date semantics. Cached full tenders bypass those discovery uncertainties only for the explicit tender identities, not for completeness.

Targeted validation: **10 tests passed** (expansion tests and existing `ProzorroTests` only). No full suite or deployment run.
