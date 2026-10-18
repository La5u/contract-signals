# National Prozorro collection: bounded feasibility check

## Current status

**No full national tender/contract download has been launched.** A bounded pilot
collected 1,500 tender identifiers plus modification timestamps into:

```text
~/.cache/contract-signals/prozorro-national/feed-index.sqlite
```

The three feed pages transferred 145,914 response bytes. This is a private,
restartable **partial identifier index**, not 1,500 contract records, a
creation-date census, a website dataset or evidence of complete coverage.
No documents/attachments were downloaded.

The proposed target is all published tenders created from 2024-09-01 inclusive
to 2026-09-01 exclusive, matching the pilot's creation-date window. This is a
provisional scope, not permission to claim all history or all real-world procurement.
The index's observation end is frozen separately because older tenders can be
modified after that creation window ends.

## Size and collection cost

Six convenience-sampled official full-tender responses averaged approximately:

- 81,646 JSON bytes per tender;
- 10,100 gzip bytes per tender;
- **9.41 GiB compressed per million tenders**, if that mean held.

This tiny sample is **not representative** and there is no verified national
count yet. It is a scaling illustration, not a total-size estimate. Full records
vary substantially; attachments, intermediate databases, indexes and backups add
space. At one detail request per second, each million tenders takes **11.57 days**
before retries and processing. No faster rate or provider capacity is assumed.

The machine had approximately 139 GiB available at the check, but was on battery.
Do not start an unbounded request-intensive national detail collector on that
basis. The initial feed pilot was strictly limited to three pages / 1 MiB.
Detailed feasibility measurements are local:
`~/.local/state/contract-signals/prozorro-national-feasibility.json`.

## Discovery findings and traps

- The official public tender feed answers anonymously at
  `https://public-api.prozorro.gov.ua/api/2.5/tenders`.
- The site search reported **10,000** with and without the broad date filter.
  Treat this as an apparent cap, **not a national count**. Site date-filter
  semantics have not been validated as `dateCreated`.
- The feed exposes IDs and `dateModified`, not `dateCreated` or contract status.
  Full official tender records are needed for creation-window filtering and
  extracting signed/terminated contract rows.
- Live feed pages contained out-of-order modification timestamps. Do not stop at
  the first out-of-window row or assume cursor order establishes a chronological
  completeness proof. The collector follows the opaque same-origin continuation
  URI, keeps partial state, and never claims national completeness.
- An empty page, successful HTTP response or reaching a byte budget is not proof
  that the desired national contract population has been collected.
- Feed/schema/discovery behavior and any bulk alternative still need validation
  before expanding the pilot into a national run. The documentation host returned
  403/404 in the bounded check; a stable official bulk export was not established.
  This does not prove no bulk export exists.

## Implemented collector

`tools/collect-prozorro-national-index.py` uses stdlib-only HTTPS + SQLite,
transactionally storing one row per tender ID plus page URL/body hashes and an
opaque continuation cursor. It follows only the expected HTTPS host/feed path,
requires positive explicit budgets, spaces requests by at least a second and
stops rather than checkpointing a truncated response. The index remains outside
the repository/web root with private file permissions. No auto-retry loops,
background service or automatic national continuation have been installed.

Default pilot/resume:

```sh
python tools/collect-prozorro-national-index.py --max-pages 3 --max-bytes 1048576
python -m unittest tests.test_collect_prozorro_national_index
```

Existing indices preserve their original modification window and observation
end. Passing a different window fails rather than silently mixing cohorts.
Pages can contain repeated IDs; deduplication retains the latest observed
modification timestamp. Six synthetic tests cover same-origin continuation,
resume/deduplication, strict response budgets, ID/timestamp validation, nonmonotonic
feed dates and refusal to infer contract completeness from date boundaries.

## Recommended next decision

1. Validate feed discovery/cursor coverage and investigate an official bulk route.
2. On AC power, run a budgeted identifier-only inventory to estimate scope, without
   launching millions of detail requests or calling it a contract dataset.
3. Choose total disk/request/time limits from that result. Prefer compact sanitized
   contract extracts and no attachments; retain raw data only with an explicit
   provenance/retention policy.
4. Then authorize a resumable full-detail collection or a demonstrably complete
   official bulk import. Publish coverage/exclusions honestly and keep it separate
   from the frozen three-buyer pilot during validation.
