#!/usr/bin/env python3
"""Bounded, resumable download of official full-tender records for one frozen slice of the national ID index.

Selection (from tools/collect-prozorro-national-index.py's feed-index-v2.sqlite, never from any result): one
procurementMethodType and feed status, dateCreated in [--since, --until) Kyiv dates, ranked by SHA-256 of
`<--salt>:<internal id>`, first --limit. The frozen list is written to slice.json before any request and reused
on resume. Each body is cached as <sha256(url)[:32]>.gz plus .meta.json (url, status, sha256, retrieved_at), the
cache format tools/import-prozorro.py --cache-dir reads. One request at a time per worker (--worker i/n splits the
list), starts at least --delay seconds apart; stops on HTTP 403 or repeated 429/503. No attachments, no contracting-module records.
"""
import argparse
import gzip
import hashlib
import http.client
import json
import os
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

HOST = 'public-api.prozorro.gov.ua'
API = f'https://{HOST}/api/2.5'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/prozorro-national'
UA = 'contract-signals/0.1 (public research; offline snapshot)'
KYIV = timezone(timedelta(hours=3))  # Summer time; the bounds used here (Jun-Sep) fall inside EEST.


def kyiv_midnight_utc(day):
    return datetime.fromisoformat(day).replace(tzinfo=KYIV).astimezone(timezone.utc).isoformat()


def select(index, method, status, since, until, salt, limit):
    db = sqlite3.connect(f'file:{index}?mode=ro', uri=True)
    ids = [r[0] for r in db.execute(
        'select id from tenders where method = ? and status = ? and date_created >= ? and date_created < ?',
        (method, status, kyiv_midnight_utc(since), kyiv_midnight_utc(until)))]
    ranked = sorted(ids, key=lambda i: hashlib.sha256(f'{salt}:{i}'.encode()).hexdigest())
    return len(ids), ranked[:limit]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--index', type=Path, default=CACHE / 'feed-index-v2.sqlite')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--method', default='aboveThreshold')
    parser.add_argument('--status', default='complete')
    parser.add_argument('--since', required=True, help='Kyiv date, inclusive')
    parser.add_argument('--until', required=True, help='Kyiv date, exclusive')
    parser.add_argument('--limit', type=int, required=True)
    parser.add_argument('--salt', default='prozorro-slice-v1')
    parser.add_argument('--delay', type=float, default=1.0)
    parser.add_argument('--worker', default='0/1', help='i/n: fetch only every n-th id from i (run n of these in parallel)')
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    frozen = args.out / 'slice.json'
    if frozen.exists():
        spec = json.loads(frozen.read_text())
    else:
        eligible, ids = select(args.index, args.method, args.status, args.since, args.until, args.salt, args.limit)
        spec = {'selection': {k: getattr(args, k) for k in ('method', 'status', 'since', 'until', 'salt', 'limit')}
                | {'index': str(args.index), 'eligible': eligible, 'basis': 'feed dateCreated, Kyiv dates; feed status at index time'},
                'frozenAt': datetime.now(timezone.utc).isoformat(), 'ids': ids}
        frozen.write_text(json.dumps(spec, indent=1) + '\n')
    ids = spec['ids']
    print(f"{len(ids)} of {spec['selection']['eligible']} eligible tenders", flush=True)

    worker, workers = map(int, args.worker.split('/'))
    connection, last, fetched, failed = None, 0.0, 0, []
    for n, internal in enumerate(ids, 1):
        if (n - 1) % workers != worker:
            continue
        url = f'{API}/tenders/{internal}'
        key = hashlib.sha256(url.encode()).hexdigest()[:32]
        if (args.out / f'{key}.meta.json').exists():
            continue
        for attempt in range(6):
            time.sleep(max(0.0, last + args.delay - time.monotonic()))
            last = time.monotonic()
            try:
                connection = connection or http.client.HTTPSConnection(HOST, timeout=60)
                connection.request('GET', f'/api/2.5/tenders/{internal}', headers={'User-Agent': UA, 'Accept-Encoding': 'gzip'})
                response = connection.getresponse()
                body = response.read()
                if response.getheader('Content-Encoding') == 'gzip':
                    body = gzip.decompress(body)
            except (OSError, http.client.HTTPException):
                connection = None
                time.sleep(2 ** attempt)
                continue
            if response.status == 403:
                raise SystemExit(f'HTTP 403 at {internal}: stopped')
            if response.status in (429, 503) and attempt < 5:
                time.sleep(5 * 2 ** attempt)
                continue
            if response.status != 200 or json.loads(body)['data'].get('id') != internal:
                failed.append(internal)
                break
            (args.out / f'{key}.gz').write_bytes(gzip.compress(body, mtime=0))
            meta = {'url': url, 'status': 200, 'sha256': hashlib.sha256(body).hexdigest(),
                    'retrieved_at': datetime.now(timezone.utc).isoformat()}
            (args.out / f'{key}.meta.json').write_text(json.dumps(meta) + '\n')
            fetched += 1
            break
        else:
            failed.append(internal)
        if fetched and fetched % 100 == 0:
            print(f'worker {worker}: {n}/{len(ids)} ({fetched} fetched this run, {len(failed)} failed)', flush=True)
    (args.out / f'failed-{worker}.json' if workers > 1 else args.out / 'failed.json').write_text(json.dumps(failed) + '\n')
    print(f'done: {fetched} fetched this run, {len(failed)} failed', flush=True)


if __name__ == '__main__':
    main()
