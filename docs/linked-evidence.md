# Linked checks and responsible collection

Added 2026-09-28 within the v3 family-maximum framework. These exploratory rules were designed after inspecting the saved field structures, not preregistered before the original downloads. They add at most **5 competition points**, never five points on top of a stronger competition signal. There is no target number of flags.

## Tours BOAMP/TED: late correction without extension

One additional check per notice/lot. It compares **one explicitly referenced predecessor**, with the same procedure UUID and lot ID, unique reference resolution, increasing publication dates, timezone-bearing deadlines and no BOAMP/TED conflict.

- Signal: the lot title or published award criteria changes, the entire possible publication-day interval falls within seven days before the old deadline, and the new deadline is no later than the old one.
- Clear: the explicitly linked pair extends the deadline. This is not a judgment about other corrections or the procurement as a whole.
- Unknown: missing/ambiguous links, timestamps, conflicting sources, or no established title/criteria change. No assumption that attachments stayed unchanged.
- Out of scope: not a correction notice.

Date-only publication is conservatively bounded using UTC −14h to the following day +14h; no publication hour is invented. Title/criteria differences are an observable weak signal, not a determination of legal materiality. An earlier deadline is shown but does not automatically establish a short original bidding period. The original full-chain bidding-period check remains unchanged.

**Current result:** six correction/lot pairs extend the deadline (five by three days, one by seven days). Six rows now have an evaluated zero; 60 remain not assessed. No new positive signal. Nationwide BOAMP award samples and Portuguese/Romanian TED award cohorts have no imported correction chain: this check is not transplanted to them.

## Ukraine: bid attrition

One additional check on completed competitive tenders with at least two uniquely identified submitted bids on the awarded lot. Each must link to exactly one award decision on that lot. The selected winner must be active, explicitly qualified and eligible; every other bid must have an unsuccessful award explicitly marked `qualified=false`.

Only that complete pattern earns **5 points**. An unsuccessful award alone is not proof of disqualification; pending/cancelled, duplicate or missing decisions remain unknown. A single offer belongs to the existing single-offer check. Reporting is out of scope. Reasons, when exposed, remain in the original language; lawful disqualification is possible.

**Current result:** 26 competitive multi-bid rows remain unknown; 462 rows are out of scope. No additional signal. We do not manufacture attrition by treating an unexamined bid as rejected. More complete decisions or qualifications are needed before any broader admissibility claim.

## Contract history: three exact links, no amendment score yet

`data/prozorro-contract-links.json` records a separately dated sample: the first three unique embedded contract IDs by SHA-256 of the existing row ID. Selection was fixed before these API requests. All three official `/api/2.5/contracts/{id}` responses matched internal contract ID, public contract ID and tender ID. One publishes one change; two do not publish a change list, so their counts are **unknown**, not zero.

The site shows those verified links, retrieval dates, published change counts and minimized change IDs/statuses/dates/reason codes. The single published change is coded `priceReductionWithoutQuantity`; the code is retained verbatim, not treated as misconduct. A later contract status may differ from the tender snapshot. No duration/amount comparison is scored: a current value or a change count does not establish a comparable sequence of original and amended terms. Identical buyer/supplier names are never join keys.

## Collection controls

`tools/fetch-linked-records.py` defaults to showing its plan. `--download` explicitly permits this **three-request sample only**:

- Public API GETs only; exact host/path allowlist, no search crawl or attachments.
- One request at a time, at least three seconds apart; process lock prevents parallel batches using the same cache.
- Fifteen-second request timeout and five-MiB response limit.
- No automatic retries or redirects. HTTP 401/403 blocks further collection; HTTP 429/503 stops the batch and persists a cooldown of at least an hour, extended by `Retry-After` (seconds or HTTP date).
- Successes and failures are cached. Re-running does not repeatedly fetch the same URLs; cache refresh requires deliberate review rather than a silent fresh download.
- Descriptive User-Agent; no credentials, access-control bypass, proxy rotation or browser scraping.
- Raw replies stay in gitignored `data/.linked-cache/`. Published summaries contain exact IDs, source URL/hash/date, status, change counts and change dates/reason codes only—no contacts, bank details or extra personal profiles. Downloaded documents would need a separate rights/privacy review. Keep the raw cache access-restricted and remove it after review (normally within 30 days); retain the minimized report and hashes. Deleting cache files is not permission to reset a refusal/cooldown or initiate another batch.

The [publisher's open-data terms](https://prozorro.gov.ua/openprocurement) permit reuse with source attribution. That permission is not blanket permission to redistribute every linked attachment or personal detail. BOAMP-published dataset reuse has since been supported as Licence Ouverte 2.0 by DILA and official dataset records ([source register](data-sources.md)); third-party attachments and privacy remain separate questions. This original delivery processes already-saved notices and makes no new BOAMP requests. The ReadTheDocs documentation returned 403 during research; it was not bypassed. API identity checks, not a presumed schema join, establish the three retained contract links.

```sh
python tools/import-tours-notices.py --offline
python tools/import-prozorro.py --offline
python tools/fetch-linked-records.py                 # inspect plan; no network
python tools/fetch-linked-records.py --download     # at most three requests
python tools/fetch-linked-records.py --offline --write data/prozorro-contract-links.json
python tools/import-prozorro.py --offline           # apply published minimized links
```

The minimized link report ships with the repository, so ordinary importer rebuilds need no private cache or network. Re-fetching the historical exact responses is not guaranteed; the cache's SHA-256 records what was checked.

## Next bounded expansion

Before expanding beyond this sample, publish an immutable list of exact contract IDs and the selected buyer/date scope, confirm current API rules, and set a small daily request budget. Prefer official bulk releases if they cover the necessary records. Separate immutable historical snapshots from updates; stop on changed totals or ambiguous joins. Link amendments by contract ID and changes by their published IDs; require comparable currency, scope and dated terms before adding amount/duration indicators. Resolve Ukraine search pagination completeness before adding buyers. The old broad download commands are not the new bounded collection path.
