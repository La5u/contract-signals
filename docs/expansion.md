# Evidence-first expansion

Prepared 2026-09-30 with a battery-friendly metadata pass. **No new procurement records have been imported, and no new country is available in the explorer from this work.** Existing explorer datasets, published source snapshots and scores remain unchanged.

**Download update:** after explicit authorization on 2026-09-30, the three frozen IMPIC ZIP archives for 2024, 2025 and 2026 were streamed to a private cache outside the repository (142,077,565 bytes total). Byte counts match catalogue metadata; SHA-256 values and source URLs are in [`data/portugal-base-downloads.json`](../data/portugal-base-downloads.json). No whole extraction, full-file scan, conversion or import was performed. A subsequent bounded inspection read ZIP directories and only the first 64 KiB/three records of each JSON member; results and the reuse/personal-field review are in [portugal-base.md](portugal-base.md). Exact terms and field-specific review still gate publication.

The preregistered work order, buyer identifiers, windows and gates are in [`data/expansion-plan.json`](../data/expansion-plan.json). Small official metadata checks are retained in [`data/expansion-source-checks.json`](../data/expansion-source-checks.json). Source availability is not evidence of completeness or unrestricted reuse.

## Priority and frozen scope

1. **France: deepen existing buyers.** Backfill notifications during 2023-01-01 inclusive to 2024-01-01 exclusive for the same six municipal SIRETs, listed explicitly in the plan. Keep this as a separate browse-only historical cohort until coverage and scoring contexts are reviewed. The DECP source keeps latest versions; a longer query window does not reconstruct every original version or amendment. Do not overwrite the existing 2024–2025 raw snapshot.
2. **Complementary evidence:** seek correction/amendment notices for existing Portugal/Romania procedures, using exact published procedure, notice and lot IDs. Freeze the identifier list before fetching records; ambiguous links stay unknown. New history initially remains context, not score points. Never link solely by supplier name, subject similarity or amount.
3. **Portugal: national coverage.** Keep the current three buyer NIFs (503933813, 508779472, 500051070), with national-source publication dates 2024-09-01 inclusive to 2026-09-01 exclusive if that field exists. Signing dates must not silently substitute for publication dates. Use a separate national-source cohort, not a merged spending total with TED. Verify rights, field meanings, contract/lot granularity, totals and exact join identifiers first.
4. **Indonesia: metadata feasibility before a buyer pilot.** Identify awarded/signed procurement records, rather than aggregate performance indicators or SIRUP plans. Then establish licence, field semantics and one buyer's official identifier before collecting a fixed 2025 calendar-year publication cohort. No Indonesian records or scoring are approved yet.
5. **Russia: separate feasibility gate.** Official access, reuse terms and current publication omissions must be established before any cohort. No alternate mirrors, credentials, CAPTCHA bypass or proxy rotation. No jurisdiction's thresholds are transplanted to these records.

## What the small checks established

### Portugal

- The guessed BASE documentation path `/Base4/pt/dados-abertos/` returned **404**. This says that path was not found, not that BASE open data is unavailable.
- The official dados.gov.pt catalogue answered a metadata search and identified IMPIC's [Contratos Públicos - Portal Base - IMPIC - Contratos de 2012 a 2026](https://dados.gov.pt/datasets/contratos-publicos-portal-base-impic-contratos-de-2012-a-2026).
- Dataset metadata labels its licence **`other-pd`**. The official licence catalogue now confirms this means **“Outra (Domínio Público)”—Other (Public Domain)**, with no terms URL. Do not turn that declaration into CC0, CC BY or privacy clearance. Source statements, field observations and remaining questions are in [portugal-base.md](portugal-base.md).
- Metadata lists official downloadable resources. The 2026 ZIP is **42,232,603 bytes**; the 2026 XLSX is **49,075,037 bytes**. Neither was downloaded during the initial metadata pass. ZIPs for 2024–2026 have since been downloaded privately as described above; the XLSX was not downloaded. Resource URLs and metadata hashes are in the check report. Historical XLSX resources are also advertised; filenames/date ranges do not independently verify their contents or completeness.
- Next, when plugged in: read applicable terms and distribution schema; choose a bounded extraction method, preserve publication-date meaning and filter the three buyer IDs. The explorer does not directly import XLSX/ZIP; conversion must happen offline with source values and provenance preserved. A snapshot larger than the host's per-file limit must not be copied into the static site.

### Indonesia

- [LKPP's data portal](https://data.lkpp.go.id/) and its CKAN metadata search answered **200** without credentials.
- The first three `pengadaan` search results concern procurement performance/governance indicators and standards. They do **not** establish contract-level data availability. Their licence fields are empty.
- Advertised CSV/JSON/XLSX resources were not downloaded. One catalogue resource pointed to a private-network address; it was not fetched, and the address was excluded from the retained report.
- The single [SIRUP](https://sirup.lkpp.go.id/sirup/home) request failed at the network layer. No retries or alternate routes were attempted. Even accessible SIRUP planning packages must not be represented as awards.
- Next: locate official contract/award-level metadata and clarify reuse terms. If only aggregates or plans are available, retain the feasibility status instead of manufacturing a contract pilot.

### Russia

- The single [official EIS landing-page](https://zakupki.gov.ru/epz/main/public/home.html) request failed at the network layer. This does not establish a permanent access ban, geoblocking, or missing data; the cause was not diagnosed.
- No records, APIs, reuse licence or representative cohort were established. Further access review is deferred; no bypass attempted.

## Lightweight tooling

```sh
python tools/expansion-plan.py           # small plan only; no network or rebuilds
python tools/expansion-plan.py --probe   # explicit metadata checks only; cached attempts are skipped
```

The probe has seven preregistered URLs total, at most 128 KiB read per reply, 12-second request timeouts, serial requests spaced two seconds apart, no retries/redirects and no browser automation. It stops the run on 401/403/429/503 and caches failures as well as successes. With the current report all seven attempts are cached, so repeating the command makes no requests. Do not erase refusal records to evade a restriction; any new collection budget needs deliberate review.

Catalogue links are retained only for public-looking HTTP(S) destinations; private-network addresses and URL credentials are excluded. **No resource URL is automatically fetched.** Metadata summaries contain titles, publisher/licence labels and distribution details—not procurement rows or contacts. Checks demonstrate only the stated observations.

While on battery, do not run download importers, raw-file scans, XML/XLSX conversions, dataset rebuilds, browser tests or the full suite. This delivery uses only the metadata requests and small focused checks. Record extraction, normalization and publication are later, explicitly bounded steps after the gates above pass.

## Authorized archive download (no extraction)

```sh
python tools/download-base-archives.py             # frozen plan; no network
python tools/download-base-archives.py --download  # stream the three exact ZIPs to the private cache
```

The fixed URLs, resource IDs, expected sizes and buyer/date scope are in [`data/portugal-base-download-plan.json`](../data/portugal-base-download-plan.json). The cache defaults to `$XDG_CACHE_HOME/contract-signals/base-archives` or `~/.cache/contract-signals/base-archives`; it must be outside the repository/web root. Files are mode 0600 inside a mode 0700 directory. Completed attempts are skipped; failed/interrupted attempts require manual review, not automatic retries. The downloader permits three URLs, 60 MiB per archive and 160 MiB total, serial requests, no redirects/retries, and streaming hashes. It never extracts archives. These private files are not included in Git or deployed to the static host. The lightweight inspection tool reads only bounded JSON prefixes; all nine sampled records share 39 fields, but this is not a whole-file schema or coverage audit.
