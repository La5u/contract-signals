# Ukraine public discovery completeness review — buyer 20089290

Current probes show **506 results**, with six accessible beyond position 500. No current 500 cap was observed. Historical completeness remains unknown: intermediate pages were not fetched, and portal date-filter semantics are unresolved. Evidence: `data/ukraine-discovery-evidence.json`; context: `docs/ukraine-audit.md`, `tools/import-prozorro.py` and the published prior audit.
The manifest, retrieved **2026-09-25T21:26:04.793512+00:00–2026-09-25T21:38:58.878003+00:00**, records **500 all-time results**, including **134 tenderIDs** in `[2024-09-01, 2026-09-01)`. The importer lists all-time IDs, filters by the tenderID date, then checks official `dateCreated` and buyer attribution offline. It sends empty-body POSTs to `https://prozorro.gov.ua/api/search/tenders?buyer%5B%5D=20089290`, starting at page 1 and stopping at the first reported total or an empty page; total drift, final count mismatch and duplicate IDs are rejected. **500 is an observed total, not a hardcoded ceiling.** Original page bodies, page size, out-of-window IDs and a beyond-total control were not retained.
All **16 buyer-association mismatches stay excluded** under official `procuringEntity.identifier.id`: seven from listing buyer `00012925`, nine from `26510514`, none from `20089290`. Their identifier pairs remain in evidence. The existing **526 buyer-matched tenders and 488 contract rows** are unchanged.

Five empty-body POSTs returned HTTP 200. Historical order was `1,25,26,fixed-window 1,27`; the tested future helper orders `1,25,26,27,fixed-window 1`.

| Scope | Page | Total | `per_page` | Rows | In creation window |
| --- | ---: | ---: | ---: | ---: | ---: |
| All time | 1 | 506 | 20 | 20 | 7 |
| All time boundary | 25 | 506 | 20 | 20 | 0 |
| Beyond 500 / computed last | 26 | 506 | 20 | 6 | 0 |
| Portal date-filter probe | 1 | 6 | 20 | 6 | 6 |
| Beyond computed last | 27 | 506 | 20 | 0 | 0 |
Pages are one-based, with scalar `page`, `per_page`, `total` and no last-page field. Page 26 is both `floor(500/20)+1` and `ceil(506/20)`; page 27 is empty but still reports 506. All all-time totals agree, with no duplicates within or between sampled all-time pages. Pages **2–24** remain unchecked; ordering is not guaranteed. The six-result increase does not prove exactly six additions or exclude deletions/reindexing, other caps or historical truncation.
The filter from `tools/build-ukraine-verdict-cohort.py` uses `date[tender][start]=2024-09-01` and `date[tender][end]=2026-08-31`. Inclusive-end behavior is unverified. Its **6** results cannot replace the historical **134** creation-window IDs; even the current unfiltered first page has **7** in-window IDs. The underlying date field, indexing and interval semantics remain unknown. No corrected census follows from these probes.

## Reproduction and safeguards

```sh
python tools/audit-ukraine-discovery.py
python tools/audit-ukraine-discovery.py --public-replay data/ukraine-discovery-evidence.json
python -m unittest discover -s tests -p test_audit_ukraine_discovery.py -v
```

Offline replay needs public evidence, manifest and published audit, not private responses. It pins the reviewed baseline, checks strict JSON, allowed fields, sources/counts, canonical POST URLs, pagination, IDs/dates, UTC chronology, spacing, bounds and failure stops, then recomputes analysis. Hashes detect local changes, including resealed altered evidence; they cannot reconstruct omitted bodies or authenticate the server. New evidence or source bytes require explicit baseline review. Published fields omit names, titles, contacts and private-cache pointers.
Future opt-in fetch, unnecessary for reproduction:

```sh
python tools/audit-ukraine-discovery.py --fetch \
  --private-dir /tmp/ukraine-discovery-NEW-EXCLUSIVE-DIRECTORY \
  --write /tmp/ukraine-discovery-minimized.json
```
Require a new absolute 0700 directory outside, and not an ancestor of, the repository; reject parent traversal and symlinks, using `O_NOFOLLOW` and exclusive 0600 body files. Limits: five requests, 2 MiB bodies, one-second start spacing, no proxies/authentication/cookies/redirects/retries, stop on HTTP failure (including 403/429), timeout, oversize or invalid payload. Historical calls had a **15-second socket timeout**, not a wall cap. Future calls add a **15-second POSIX main-thread wall alarm** through DNS/connect/headers/body processing, recorded as `wallCapSeconds: 15`; this path was tested with mocks only.
**18 discovery tests and 9 existing Prozorro audit tests passed**, covering stale/resealed evidence, privacy, IDs/counts, request bounds, safe storage, wall interruption and offline replay with sockets forbidden. Current probes cannot certify the 2026-09-25 snapshot or complete all-time/fixed-window discovery. Listing association still requires primary-record buyer attribution.
