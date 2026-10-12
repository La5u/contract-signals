# Ukraine public discovery completeness review — buyer 20089290

## Scope and reproduction

Only existing buyer `20089290`; no national feed, bulk retrieval, new buyers, tender-detail requests, dataset replacement, scores, or inclusion-rule changes. Read `docs/ukraine-audit.md`, `tools/import-prozorro.py`, the public raw manifest, and the published prior audit. Evidence: `data/ukraine-discovery-evidence.json`. Published fields are limited to tender/buyer identifiers, dates, page counts, source hashes, URLs and request metadata; no titles, names or contacts.

Offline replay (zero requests; no private cache dependency):

```sh
python tools/audit-ukraine-discovery.py
python tools/audit-ukraine-discovery.py --public-replay data/ukraine-discovery-evidence.json
python -m unittest discover -s tests -p test_audit_ukraine_discovery.py -v
```

Opt-in future public fetch, **not needed for reproduction**:

```sh
python tools/audit-ukraine-discovery.py --fetch \
  --private-dir /tmp/ukraine-discovery-NEW-EXCLUSIVE-DIRECTORY \
  --write /tmp/ukraine-discovery-minimized.json
```

The raw directory must be an absolute, new exclusive directory outside (and not an ancestor of) the repository. Parent traversal and symlinks in any path component are rejected; directory-descriptor traversal with `O_NOFOLLOW` and descriptor-relative exclusive body creation prevent symlink redirection. It is created with mode 0700; bodies are exclusively created with mode 0600. Future invocations allow at most five requests, a configured 15-second socket timeout **plus a POSIX main-thread 15-second wall alarm** covering DNS/connect/headers/body read and processing, a 2 MiB response bound, and at least one second between request starts. Environment proxies are explicitly disabled; no auth or cookie handlers, credentials, redirects, retries, challenge handling/bypass, or contact are used. Any HTTP failure (including 403/429), timeout, oversize or invalid payload stops the run. This tool does not inherit the importer's retry/90-second policy.

**Historical versus future timeout:** the five recorded calls used a configured 15-second socket timeout, not the newly added wall alarm. Their unchanged `bounds.timeoutSeconds` records that historical configuration; it does not prove a historical 15-second wall cap. New fetch output separately records `wallCapSeconds: 15`. The stricter fetch path has been tested only with mocked responses; it was not executed against the portal in this follow-up.

### Fail-closed offline integrity

Replay accepts only the reviewed historical baseline. It checks strict JSON (duplicate keys and non-finite values rejected), an exact top-level/request-field allowlist, POST and exact canonical URLs, positive pages and scopes, UTC chronology with at least one-second start spacing, at most five numbered requests, HTTP failure stop behavior, body bounds, SHA-256 syntax, tenderID syntax/calendar dates, row/window/duplicate counts, and allowlisted finite scalar pagination. Analysis is recomputed and compared before publication; no stored completeness assertion is trusted.

The snapshot must exactly match locally recomputed public manifest/audit evidence. Both source files are pinned by byte SHA-256, and the audit's buyer discovery counts must agree with the manifest. `auditFileSha256` fingerprints the existing cached published audit (`77e7098acad425b516a45cfe441b17f599e6d601401386569110b0c4993a37dc`); no audit regeneration or remote refetch was performed. Its discovery entry agrees with the same manifest's 500 listed / 134 window IDs. Extra fields, including private-cache pointers or personal-information fields, and stale sources/snapshots are rejected before output. Replay requires only the public minimized evidence, public manifest, and published audit—not original tender bodies or private responses.

`integrity.evidenceSha256` is SHA-256 of canonical UTF-8 JSON (sorted keys, compact separators, no non-finite numbers), excluding only the `integrity` object. The tool separately pins the reviewed checksum `1658d71afd2d5010ea29ab545eb155e2cbb6a63d23042235450e31f86c90bcd0`; merely resealing an altered file cannot make it replayable. Its label is **local minimized evidence integrity; not remote authentication**. These checks detect local changes against the reviewed baseline, not server authenticity or correspondence between omitted raw bodies and published projections. Fresh fetch output has its own checksum but is not automatically accepted as a historical replay baseline; a new baseline requires explicit review. Changing local source bytes likewise requires explicit baseline review.

## Recorded snapshot and stopping rule

Manifest retrieval: `2026-09-25T21:26:04.793512+00:00` through `2026-09-25T21:38:58.878003+00:00`. Vinnytsia recorded **500 all-time listed results**, of which **134 tenderIDs** were retained by the fixed creation-date window `[2024-09-01, 2026-09-01)`. The importer did **not** submit a date-filtered search: it listed all-time IDs and applied the date embedded in tenderID before fetching official records; official `dateCreated` and buyer attribution were then checked offline.

Importer pagination starts at page 1 with an empty-body POST to `https://prozorro.gov.ua/api/search/tenders?buyer%5B%5D=20089290`. It stops once accumulated rows reach the first reported total, or a page is empty. It rejects total drift, final count inequality and duplicate IDs. Thus 500 is an **observed total**, not an explicit hardcoded importer ceiling. Equality with the published total is internal consistency, not proof that the endpoint's total is uncapped. Original page bodies, original page size, out-of-window all-time IDs and a beyond-total control were not retained in the manifest. No historical pagination reconstruction is possible from those counts alone.

All **16 buyer-association mismatches remain excluded** under the official `procuringEntity.identifier.id` rule. Their minimized identifier pairs are preserved in the evidence: seven belong to listing buyer `00012925`, nine to `26510514`, and zero to `20089290`. They are not reclassified or used to increase this buyer's count. The existing 526 buyer-matched tender records and 488 retained contract rows are unchanged.

## Actual public requests: five total

Requests were made on **2026-10-11**, using the importer's native published search endpoint and empty-body **POST** method. All returned HTTP 200. No documentation requests were made (zero). The five historical search calls are unchanged; this follow-up made **zero network requests** and leaves the remaining budget reserved for the two documentation requests untouched. Each request's exact URL, timestamp, body byte count and SHA-256 are in the public evidence. Calls 1–4 were one bounded invocation; call 5 was a single continuation for the empty-page control, with no repeat of earlier requests. A future invocation schedules that control before the window probe within the same five-request ceiling.

| Call | Scope | Page | Reported total | `per_page` | Rows | IDs in fixed creation window |
|---|---|---:|---:|---:|---:|---:|
| 1 | All time | 1 | 506 | 20 | 20 | 7 |
| 2 | All time boundary | 25 | 506 | 20 | 20 | 0 |
| 3 | All time beyond 500 / computed last | 26 | 506 | 20 | 6 | 0 |
| 4 | Portal date-filter probe | 1 | 6 | 20 | 6 | 6 |
| 5 | All time beyond computed last | 27 | 506 | 20 | 0 | 0 |

Observed semantics: one-based pages, 20 rows per full page, scalar `page`, `per_page`, `total`, and no reported last-page field. With observed size 20, page `floor(500/20)+1 = 26` is precisely beyond result 500 and also `ceil(506/20)`, the computed last page. Page 25 gives the immediately preceding boundary control; page 27 is empty but still reports total 506. All four all-time totals agree. No duplicates occur within any sampled page, and no IDs overlap across sampled all-time pages, including the 25/26 boundary. Pages 2–24 were deliberately **not** fetched; duplicate/gap freedom there is unknown. Ordering was not treated as a contractual guarantee.

**No current 500-result cap is observed:** six IDs are accessible past position 500 under the observed page semantics. The total is six higher than the old snapshot's 500, but this is a net count difference, not proof of exactly six additions or no deletions/reindexing. These sparse current probes do not establish a general absence of other caps or a full tender census.

## All-time versus fixed-window blocker

The fourth request uses the portal's existing date-filter spelling from `tools/build-ukraine-verdict-cohort.py`: `date[tender][start]=2024-09-01` and `date[tender][end]=2026-08-31`. The preceding calendar day is an intended translation of the exclusive 2026-09-01 boundary; **inclusive-end behavior is not certified**. Response total is **6**, all on that page and within the tenderID date window, versus **134** window IDs in the original manifest. Even the current unfiltered first page contains **seven** in-window IDs. The portal date-filter result therefore cannot be substituted for filtering all-time discovery by tender creation date. The filter's underlying date field, interval behavior, indexing or additional semantics remain unresolved; no source documentation was fetched within the exhausted request budget. It may filter a different date field; this audit does not assert which one.

This is an actual blocker to an endpoint-filtered fixed-creation-window completeness claim. The native importer's all-time-list-then-dateCreated-check approach must remain distinct from this portal filter. No corrected window census or additional tender cohort was downloaded.

## Conclusion and actual limits

- Current published pagination passes the sampled 500 boundary and ends consistently at 506 in the sampled controls; no total drift or sampled duplicate boundary was found.
- **Cannot retrocertify the 2026-09-25 snapshot with current counts.** Historical page evidence is missing, current results are mutable, and current total 506 does not tell us what page 26 or the date filter returned then.
- No full all-time or fixed-window completeness certification: intermediate pages were not traversed, portal date-filter semantics are unresolved, and discovery association is not official buyer attribution.
- Public minimized evidence replays without raw/private responses. SHA-256 fingerprints bind the observed bodies but do not reconstruct their contents or independently authenticate the server; the public file intentionally omits the non-minimized bodies.
- Follow-up checks: **18 discovery tests passed**, including stale manifest/audit sources and baseline drift (even when resealed), extra/private-information fields and cache pointers, within-page IDs/counts, source hashes, scalar pagination, body/request caps, chronology/spacing, stop-on-HTTP-failure behavior, unsafe directory paths, disabled environment proxy/auth handlers, wall-alarm interruption during body read, and fresh-directory offline replay with socket creation forbidden and no private cache. **9 existing Prozorro audit tests passed**. Historical order remains `1,25,26,fixed-window 1,27`; the tested current probe schedules `1,25,26,27,fixed-window 1`, and is not represented as the code that executed the historical sequence. No shared files changed, no commits or pushes, and no follow-up network requests.
