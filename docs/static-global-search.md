# Static cross-country filtering: contract and limits

## Scope and audit conclusion

Cross-country filtering can run entirely in the visitor's browser over published,
versioned static JSON chunks. It needs no paid backend, database, search service,
or server-side execution. The explorer now implements bounded scan-page browsing
in `script.js` (`scanKoreaPage` and `scanPublishedPage`). `static-scan.js` is a
separate reusable full-count scan primitive, tested by `tests/static-scan.cjs`;
it is not loaded by the current UI. No national rebuild was needed for these UI changes.

### Implemented UI

- Choose **All published collections** in the country selector for a scan across
  existing published registry collections, or **South Korea** for all institutions.
  Korea's single-buyer mode remains available. Private candidate datasets are excluded.
- Existing filters apply before page retention, including indicators, assessment,
  sector, minimum native-currency amount and context. New filters select record
  country, inclusive displayed-date range, buyer name/ID, supplier name and procedure.
  Unknown dates do not match an active date range. Date meanings vary by source.
- Scan pages retain at most 200 matching records. Loading stops after finding the
  page plus a look-ahead match; counts are explicitly partial unless the entire
  scope has been exhausted. Next/previous scan pages rescan from the beginning.
- Filters and review marks are snapshotted; changes invalidate the page and require
  a rescan. Cancel and stale-response guards prevent obsolete results replacing it.
- Sorting and grouping operate only on the retained scan page. In global scope,
  sorting stays within each collection; no cross-country risk ranking is produced.
  Copy/CSV/JSON export only that page and label the scope accordingly.
- Global records retain collection labels and original IDs. Overlapping
  representations remain separate; they are not distinct-procurement totals.
- Ordinary collections load one collection at a time; Korea fetches one shard at a
  time and converts small batches. Memory is bounded by the page and current
  collection/shard, rather than the whole national corpus.

Browser tests use synthetic fixtures, not a 2.7-million-row national download.
Deployment has not been performed. Current source URLs are not immutable
snapshot manifests: a concurrent publication can still mix builds, even though
Korea buyer row-count checks detect some incomplete-shard cases. Versioned,
atomic publication remains a hardening task; a scan is not evidence of upstream
or historical completeness.

A search covers **all rows in the selected published chunk manifest**, not all
procurement in a country, all time, or every upstream record. Show the selected
countries/datasets, published snapshot, actual coverage dates and limitations.
Do not substitute collection date for procurement coverage. Unknown coverage
must remain unknown. A manifest should pin immutable/versioned chunk URLs and
contain chunk and row counts; mixing updates mid-scan cannot produce a reliable
snapshot. A successful scan of an incomplete manifest does not establish upstream
completeness. Avoid overlapping datasets unless an upstream publication step
provides explicit identity/deduplication rules: the scanner counts rows, not unique
contracts, and does not silently deduplicate.

Arbitrary predicates can use **only collected fields** and explicitly derived
values. Missing fields, unavailable documents and unimplemented indicators are
not negative findings or evidence of a clean contract. Do not display unknown
indicators as assessed, scored zero, or “no risk.” Distinguish not assessed,
not applicable and assessed with no signal using the dataset's actual evidence.
No backend or client predicate can query information that was never published.
Cross-country scores and field semantics are not automatically comparable.

## Exact integration API (browser and CommonJS)

Load `static-scan.js` before a browser consumer to expose `globalThis.StaticScan`.
Node consumers use `require('../static-scan.js')`. Exports:

```js
StaticScan.loadChunks(descriptors, loadChunk, { signal } = {}) // async generator
StaticScan.scan(chunks, {
  predicate,        // default () => true; boolean or Promise<boolean>
  offset: 0,        // matching rows to skip, NOT a source-row/chunk offset
  pageSize: 50,     // retained matches; zero supports count-only scans
  onProgress,      // optional sync/async callback(snapshot)
  signal,          // optional AbortSignal
  expectedChunks,  // optional manifest count, checked exactly
  expectedRows,    // optional manifest row count, checked exactly
  yieldEvery: 1000,
  yieldControl     // optional async scheduler, injected by consumer
}) // Promise<result>, not an iterator of pages
```

`chunks` is a synchronous or asynchronous iterable yielding **arrays of rows**.
`loadChunks` adapts a sync/async descriptor iterable into that protocol, calling
`await loadChunk(descriptor, {signal, index})` sequentially. The loader must return
an array (including a genuinely empty chunk) or reject. The module has no built-in
fetch, URL convention, country schema, DOM access, filesystem access or cache.
Extract wrapped payloads in the loader; never turn HTTP/JSON/schema errors into
empty arrays or skip failed descriptors. Validate row schemas there as needed.

The predicate receives `(row, {rowIndex, chunkIndex, indexInChunk, signal})`.
Indices are zero-based source positions, independent of page offsets. Predicates
must return actual booleans; they may be async and may inspect any collected field.
Use deterministic, non-mutating predicates for reproducible pagination.

A resolved result has:

```js
{
  rows, offset, pageSize,
  scannedRows,    // rows whose predicate completed successfully
  matchedRows,    // ALL matches, including those outside the retained page
  scannedChunks, // fully processed chunks, including empty chunks
  complete: true,
  exact: true
}
```

`rows` contains at most `pageSize` row references. It preserves supplied chunk and
row order: **there is no score/date/global sorting guarantee**. It does not sort,
clone or mutate input. Sorting a retained page is not global sorting. If global
ordering is needed, explicitly publish chunks in that order or design a separate
bounded top-k algorithm. The scan continues after filling a page, after skipping
all available matches, and with `pageSize: 0`. Every requested page requires a
fresh iterable and full scan for exact counts. Generators are single-use.

`onProgress` receives a new count-only snapshot with the same fields except
`rows`, initially, at each fully processed chunk, every `yieldEvery` rows, and at
successful completion. Intermediate snapshots have `complete:false, exact:false`;
`matchedRows` is then only a lower bound, not a total or extrapolated estimate.
`scannedRows` can include part of the next chunk while `scannedChunks` counts only
finished chunks. The final callback has both flags true after exhaustion and
expected-count validation. Await the scan promise before committing final UI
results: callbacks, cancellation, and scheduler failures can still reject it.
Callbacks are awaited; their failures are not ignored.

Errors reject rather than return partial success. Runtime errors have
`name: 'StaticScanError'`, the original `.cause`, and `.progress` with
`complete:false, exact:false`. Cancellation rejects with `name: 'AbortError'`
and the same partial-count structure. Invalid option values reject with TypeError
before scanning. No partial page is returned on failure. Never replace failure
with “0 results,” or show partial counts as exact. Missing/malformed chunks,
iterator errors, predicate errors and count mismatches are failures. Expected
counts detect an accidentally short/long source; without a manifest there is no
way to distinguish natural iterator completion from an omitted chunk. Count
checks alone cannot detect equal-sized substitutions: versioned manifests and,
where needed, per-chunk content hashes belong in the publication/loader layer.

## Example browser adapter (not an existing UI integration)

```js
const controller = new AbortController();
const { signal } = controller;
const chunks = StaticScan.loadChunks(manifest.chunks, async (entry, { signal }) => {
  const response = await fetch(entry.url, { signal });
  if (!response.ok) throw new Error(`Chunk failed: ${response.status}`);
  const rows = await response.json();
  if (!Array.isArray(rows) || rows.length !== entry.rowCount) {
    throw new Error('Invalid chunk or manifest mismatch');
  }
  return rows;
}, { signal });

const result = await StaticScan.scan(chunks, {
  signal,
  expectedChunks: manifest.chunks.length,
  expectedRows: manifest.rowCount,
  predicate: row => selectedCountries.has(row.country)
    && typeof row.amount === 'number' && row.amount >= minimum,
  offset: pageIndex * pageSize,
  pageSize,
  onProgress: p => showScanProgress(p), // partial counts labelled as such
  yieldEvery: 1000,
  yieldControl: () => new Promise(resolve => setTimeout(resolve, 0))
});
showCompletedPage(result);
// On filter changes: controller.abort(); start a new scan with a fresh source.
```

This illustrative amount predicate does not normalize currencies, tax, award vs
contract value or reporting periods. An actual cross-country filter must apply
explicitly supported currency/amount semantics or limit its scope accordingly.

Use a new AbortController and a request-generation token for every search. Abort
the previous scan, and ignore stale callbacks/results in the UI; abort alone
cannot undo already-rendered progress. Pass the *same signal* to the scanner and
loader. Pending iterator, loader and predicate promises are raced against abort,
so even an uncooperative pending operation cannot hold the scan promise hostage.
Actual I/O stops only if the loader cooperates. Iterator `return()` is requested
on failure without waiting indefinitely for cleanup; pending foreign operations
may still finish. A synchronous CPU-bound predicate cannot be interrupted by an
AbortSignal. Inject a task-queue scheduler as above to allow painting and user
abort events during large cached chunks (microtask-only awaits are insufficient).
For expensive computation consider a worker and explicit resource limits.

## Memory, network and publication costs

The scanner keeps counters and one bounded page; it sequentially requests chunks
and retains no all-row array, match list, index, or chunk cache. Peak application
memory is O(largest decoded chunk + pageSize), excluding the producer/loader,
predicate/callback state, browser HTTP cache and JSON parsing overhead. At a chunk
boundary, a previous array and incoming array can transiently coexist. Keep chunks
small enough to decode on low-memory devices. A source that already concatenates
all chunks, a loader cache, or a callback that stores rows defeats this bound.
Do not prefetch all chunks concurrently. The browser may retain response buffers
or HTTP caches independently; this is not a strict process-RSS guarantee.

An arbitrary-field exact scan generally downloads **every selected chunk** to each
visitor, even for a tiny result page. If selected compressed data is B bytes and
there are V cold scans, transfer is approximately B × V, plus manifest/HTTP
overhead. Repeated pages/filters may reuse browser caches, but cache hits must not
be assumed; parsing and rescanning still cost CPU, memory, time, battery and
potential mobile-data charges. Static hosting is not zero-cost at unlimited scale.

Existing free static hosting (for example GitHub Pages or Cloudflare Pages) can
serve the manifest and chunks without a paid backend **while within the provider's
current free-plan terms**. Check documented repository/deployment size, per-file
size, file count, bandwidth/fair-use, build and request limits before publishing;
limits and free-plan eligibility change. References:

- https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- https://developers.cloudflare.com/pages/platform/limits/

Use compressed transfer and immutable chunk URLs with a small versioned manifest;
verify deployment actually serves every manifest URL and correct cache headers.
A static host does not provide arbitrary server-side filtering. A static index can
reduce transfer for specific indexed predicates, not arbitrary unindexed fields.
Publish a deliberately scoped snapshot if a full national history exceeds free
hosting or reasonable client download budgets. Expanding to all-time national data
requires a separate size/licensing/privacy/coverage audit and explicit disclosure,
not merely changing the UI label to “global.” This implementation performs no
national builds, upstream collection or downloads.

## Verification

Run `node tests/static-scan.cjs`. Synthetic tests exercise browser exports, async
loading, input-order pagination across every row, empty pages/chunks, count-only
scans, exact vs partial progress, scheduler hooks, manifest mismatches, malformed
chunks, loader/iterator/predicate/callback errors, cancellation before/during work
and while uncooperative operations are pending, iterator cleanup and bounded
retained pages across many chunks.
