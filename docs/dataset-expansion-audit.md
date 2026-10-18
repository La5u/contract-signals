# Dataset expansion: coverage, overlap and Korea query options

Read-only audit, 2026-10-17. **This is an options paper, not approval or implementation of a new Korean architecture.** Only this document is added. No UI changes, rebuilds, downloads, database-wide queries or raw procurement scans were run. Evidence: source code, existing research/coverage documents, the local published-build metadata, file-size metadata, and small normalized French/Paraguayan cohort identity comparisons. Hosting plans, current provider limits/prices and live deployment contents were not independently verified.

## Executive findings

- Korea already has a **national, all-contracting-institution snapshot**, not merely a few downloaded buyers. Its public files contain 2,725,329 contract rows. The UI nevertheless accepts only one selected buyer's rows at a time. Global pagination/search/filter/export is a separate query problem, not a missing-download problem for that published snapshot.
- “All” must specify a snapshot and source scope. All published normalized rows, all downloaded versions (including newer historical backfill), and all historical Korean public procurement are **three different claims**. None implies the next.
- Free static Pages can serve prebuilt pages and indexes. It does not execute arbitrary SQL or magically paginate/filter all shards. Global arbitrary queries require either potentially substantial browser work or a query service.
- The French DECP cohorts and the two Paraguayan cohorts have disjoint buyer sets and no shared normalized IDs. France also has proven cross-source overlap with BOAMP and national/buyer feeds; those must not be concatenated as new spending. There is no demonstrated duplicate-contract overlap between the Paraguayan cohorts.

## 1. Korea: actual collection, publication and UI boundaries

### Published snapshot versus historical collection

The local `~/.cache/contract-signals/korea/site/meta.json`, built `2026-10-17T14:42:31+00:00`, reports:

| Property | Observed value |
| --- | ---: |
| Contract rows | 2,725,329 |
| Contracting institutions | 25,495 |
| Buyer-grouped JSON shards | 327 |
| Display-date extrema | 2024-09-01 to 2026-09-01 |
| Files in build, including index/headers/robots | 332 |
| Total uncompressed file bytes | 559,721,714 (559.7 MB decimal) |
| Smallest / largest shard | 1,258,165 / 9,426,452 bytes |
| Buyer index | approximately 2.1 MiB |

Sizes were obtained from directory entries/stat calls, not shard-content scans. These are local build sizes, **not measured wire transfer, gzip/Brotli sizes, or browser heap usage**. The handoff's “~1.5 MB shards” describes the target, not a maximum.

[The original profile](../research/korea-opnstd-profile.md) records 3,743,496 versions and 2,725,329 contract numbers in 105 weekly windows, with reported API-count shortfall zero for that collection. Of these, 2,526,389 contracts were originally signed within the period; **198,940 are older contracts observed through an in-period change**. Version counts are not contract counts. The fetcher uses inclusive window endpoints, including 2026-09-01; do not silently relabel the actual collection as an exclusive September boundary.

Local raw-cache filenames now extend to older years and include an unfinished `.part` file. Their presence is evidence of historical collection work, **not proof that all older windows are complete, normalized into the current SQLite database, or published**. The existing site's metadata still describes the two-year snapshot. No historical completion census was attempted here.

Use these separate scope labels:

1. **All rows in published snapshot X:** the normalized contract projection in that manifest; feasible to expose globally without additional collection.
2. **All successfully downloaded records:** potentially many versions and historical windows beyond X. Requires a reviewed completion manifest, normalization, identity/conflict checks and a new publication before the UI can claim to include them.
3. **All historical Korean procurement:** not established. National institution coverage within one PPS service is not proof of coverage of every procurement channel, unpublished/exempt records, all years, or every amendment. Matching the API's reported count tests retrieval against that API response, not real-world completeness.

### What `tools/build-korea-site.py` actually builds

- Opens SQLite read-only; joins `contracts` to its latest observed `versions` row. Publishes one row per contract number, **not every version**. The latest version means latest in the normalized input, not necessarily latest today.
- Uses signed date or first observed change date. `dateIsFirstChange` distinguishes older originals; original amount is null when the original is outside the period. Amounts are declarations, not payments; unit-price/ceiling and joint-contract limitations remain relevant.
- Sorts by buyer code, date and contract number; packs whole consecutive buyers into shards. Each buyer maps to one shard. The flush occurs **after** adding a buyer, so large buyers exceed `SHARD_BYTES = 1_500_000`; dictionary/envelope overhead is also outside the approximate row-byte counter.
- Publishes 19 array columns, shared method/type dictionaries and per-shard demand/legal dictionaries. Buyer identity comes from the shard/index context. This is a compact display projection, not a portable full-history relational archive.
- Materializes all buyers' rows and dates in Python memory. Historical expansion therefore affects build RAM and sorting, independently of hosting feasibility. The output directory is deleted before rebuilding; publication needs separate staging/versioning rather than serving a half-built directory.
- Emits CORS, `noindex`, robots and security headers. Those are not access controls. No secret API key or private raw database belongs in this public output.

In `script.js`, `koreaIndex()` fetches metadata and the buyer list; buyer search returns at most 30 institution matches. `loadKorea()` requires a buyer, fetches that buyer's shard and passes only `koreaRecords(meta, shard, buyer)` to the ordinary explorer. Thus existing record search, sorting, filters, pagination and export operate on **that selected buyer**, not the national snapshot. Neighboring buyers in the downloaded shard are not automatically queried. The shard promise cache has no eviction, so browsing many buyers can accumulate client memory.

Korean assessments remain browse-only/not assessed. An architecture change must not introduce foreign thresholds or turn unknowns into zero.

## 2. What a genuine “ALL contracts” view must guarantee

Before choosing storage, agree on the query contract:

- Default global sort and a deterministic tie-breaker, e.g. date descending then contract number; define null/change-date ordering explicitly.
- Exact filter semantics (contracting versus demand institution, date basis, amount basis/currency, method/type, supplier). Define Korean text matching: whitespace, Unicode normalization, substring versus token/prefix search, and identifier matching. SQLite FTS or another generic tokenizer is not automatically equivalent to Korean substring search.
- Pagination over the **whole matching snapshot**, not filtering one loaded page. Distinguish exact totals/facets from partial or estimated results.
- Stable snapshot ID in page cursors, links and exports. Never mix `meta.json`, buyer maps, dictionaries or shards from different builds.
- Export means all matching rows, or clearly says “current page/selected buyer.” Large exports need progress, cancellation, bounded memory and possibly multipart/prebuilt files. Counts and exports must use the same filters as the list.
- Preserve source links, date flags, unknowns, amount semantics and privacy behavior. Published individual-business names remain visible and flagged; omit their registration numbers and apply the [individual-supplier export rule](personal-data.md) consistently in every output engine.

### Architecture options

| Option | What it realistically supports | Costs and limitations |
| --- | --- | --- |
| **Static Pages + precomputed JSON pages/indexes** | Fast first national page and next/previous browsing in a chosen prebuilt order. Buyer/date/method partitions and precomputed counts can support a finite menu of global filters. Prebuilt full/partition exports are possible. | No runtime database. Arbitrary filter combinations, global text search and arbitrary sort require additional indexes or scanning data. Precomputing every combination is combinatorial. New partition/index design and a custom client query layer are real work. Existing buyer shards alone are not a global search index. |
| **Pages UI + DuckDB-Wasm + public Parquet** | Rich client SQL, global sort/filter/aggregation/export without a hosted SQL service. Projected columns, partition pruning and row-group statistics can reduce transfer for selective queries. | Requires new sanitized Parquet publication and browser integration, not simply pointing DuckDB at current shards. Global free-text search, unselective counts or sorts can read much of the dataset. Cold-start, WASM, browser RAM/storage and mobile performance need measurement. Full downloads and full exports remain substantial. |
| **Worker + D1, optionally R2** | Indexed, server-side filters and cursor pagination without sending the corpus to every browser. D1 can hold a searchable relational projection; R2 can hold immutable sanitized files, downloads and possibly export artifacts. | Adds ingestion, schema/index migrations, API/query limits, abuse controls and operational monitoring. D1 capacity includes indexes and may constrain a multi-million-row history. R2 is object storage, not an SQL search engine. A Worker cannot efficiently query the private 4.8 GiB SQLite file by treating an object URL as a local database. Free-tier suitability and export execution budgets need validation. |
| **Pages UI + small server with SQLite** | Conventional indexed SQL, stable cursor API, controlled text search and streamed exports. Reuses SQLite tooling and permits a purpose-built sanitized serving database. | Requires hosting, backups, patching, monitoring, TLS/CORS and capacity planning. Free ongoing operation is not established. Private normalization tables/fields must not be exposed. Index building, large sorts and concurrent exports need resource controls; immutable read-only snapshots simplify serving. |

**Free-static interpretation:** static assets may be served on a free Pages plan if the build fits the provider's current deployment constraints. No current quota or price was checked here. Verify file count, largest asset, deployment size/upload method, build limits and applicable terms against official documentation before a larger publication. A free frontend does not establish that a Worker/D1/R2 backend or external server will remain free.

**DuckDB-specific gates:** check remote Parquet byte-range support, appropriate CORS/exposed headers, cache behavior and MIME types on the chosen host; do not assume CDN compression preserves useful range behavior. Use a Web Worker, cancellation and memory limits. Multi-threaded configurations may require cross-origin-isolation changes incompatible with some third-party resources. Parquet is columnar storage, **not a full-text index**; arbitrary substring search may still scan the text column. Benchmark representative low-memory devices before making it the default.

**API-specific gates:** use parameterized queries, an allowlisted filter/sort grammar, page-size caps and snapshot-bound keyset cursors. Deep `OFFSET` pages can become expensive; keyset pagination is preferable for sequential browsing but does not provide arbitrary page-number jumps for free. Exact counts/facets and full filtered exports are separate workloads, not automatic side effects of fetching one page. Stream or stage large exports; do not buffer millions of rows in a single short-lived request.

### Decision path, not a premature implementation

1. If the immediate priority is **free hosting and seeing all contracts**, consider static global date-ordered pages plus explicit limited filters and downloadable snapshot parts. This is honest global browsing, but not unrestricted global search.
2. If arbitrary global filters/search and fast low-bandwidth use are essential, compare a D1 searchable projection against a small SQLite service. Do not promise either fits a free tier without measuring the sanitized schema plus indexes and representative query/export load.
3. If avoiding a backend is paramount and heavier client transfer is acceptable, evaluate DuckDB/Parquet as an optional analytical mode. Do not infer acceptable mobile behavior from successful desktop buyer browsing.
4. Only after the owner chooses the intended semantics and cost/complexity envelope, authorize a bounded benchmark: small sanitized sample, then a separately approved full-snapshot build. Measure time-to-first-page, cold/warm query bytes and latency, peak memory, total/index size, text-search correctness and export behavior. No such build or benchmark was performed in this audit.

## 3. Proven overlaps and safe merge boundaries

### France

A lightweight comparison of current normalized files finds `decp-history.json` **2,997 rows / two buyer SIRETs**, `decp-cities.json` **2,289 rows / six buyer SIRETs**, **zero shared buyer SIRETs and zero shared normalized `id`s**. Their existing eight-buyer union is 5,286 rows; that UI union is already implemented, not a new expansion proposal.

[The documented cross-source review](../research/france-cross-dataset-check.md) establishes a different kind of overlap:

- **Nine direct BOAMP lot overlaps** with these DECP cohorts (seven Paris, two Nantes). BOAMP lots and DECP contracts are not interchangeable units. Do not sum their rows or monetary values as distinct procurement.
- Ministry and national/buyer-feed comparisons cover many of the same contracts, with major amount disagreements. The final review retains **885 amount disagreements** (788 history, 97 cities) and **25 possible-duplicate records**. Feed-only and portal-only additions were reconciled, not blindly appended.
- AWS and scraped copies can be the same publication route. Agreement is corroboration, not independence or proof; route copies must not receive separate majority votes.
- Truncated identifiers and co-holders were materially important. Equal buyer/supplier/date/amount is a candidate link, not sufficient proof of a duplicate. Co-holders do not create additional contract value.

Those numbers describe the cited review, not a fresh raw-source re-audit. Its 649 national BOAMP candidate matches are not 649 proven unique contract equivalences. Preserve source-specific amounts/ranges and warnings; no universal automatic BOAMP-to-DECP amount cross-fill is supported.

### Paraguay

Current small normalized-file checks establish:

| Cohort | Rows | Distinct OCIDs | Buyers |
| --- | ---: | ---: | --- |
| Fernando de la Mora | 84 | 84 | `DNCP-SICP-CODE-66` |
| Three buyers | 293 | 211 | `…-20` (MOPC), `…-81` (Central), `…-108` (Asunción) |

Across the two files there are **zero shared buyer IDs, OCIDs, normalized IDs, contract IDs, or `(ocid, contractId)` pairs**. A browse union would therefore have 377 rows across four buyers; this audit does not implement it. Multiple contracts under one OCID in the three-buyer cohort are normal process/contract granularity, not proof of duplication. Older documents' cohort counts must not replace these current-file observations.

The proven *within-process* overlap is the DNCP `AC-…` amount-amendment entries described in [the pilot update](paraguay-pilot.md): attach them to the parent contract, do not count them as independent base awards or add a revised total as incremental spending. Distinct cohort windows select **call publication**, not signatures/payments. No national Paraguayan completeness or additional cross-source duplicate set was established here.

### Safeguards for any future expansion or combined view

1. Retain original snapshots, cohort IDs, source routes, retrieval dates, window semantics and licences. Build a separate versioned union manifest; do not overwrite frozen evidence.
2. Scope identities by jurisdiction/source family. For DECP start with buyer identifier + contract identifier, checking lot, truncation, date and version conflicts. For DNCP use OCID + contract ID; OCID alone identifies a process. Missing identities remain unresolved, never collapse all nulls into one key.
3. Distinguish exact copied records, alternative declarations, modifications, co-holders, lots and genuinely new contracts. Keep provenance and conflicts; never select the largest amount, latest retrieval or majority route without the established reconciliation policy.
4. Publish money only with currency and basis. Do not sum across versions, duplicated routes, co-holders, framework ceilings, unit prices, BOAMP/DECP representations or currencies. Do not treat contract value as payment.
5. Preserve unknown assessments and source-specific rules. Disjoint unions need not alter scores, but expanded buyer/time contexts can change repetition, concentration and denominators: review and version those contexts before rescoring.
6. Validate identity uniqueness, union/intersection counts, cohort membership, retained conflicts, export privacy and sample links before publication. Publish atomically with a snapshot manifest; stale caches must not mix index and data revisions.

**Bottom line:** Korea's current limitation is global access/query architecture over an already national published snapshot. Historical expansion is an additional collection/normalization project. Choose the required global-query semantics first; do not conflate an “ALL” dropdown, historical completeness, and a free scalable search backend.
