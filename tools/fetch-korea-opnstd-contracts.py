#!/usr/bin/env python3
"""Download PPS open-standard contracts (data.go.kr 15058815) nationwide, newest week first.

One gzipped JSONL file per 7-day window of signature dates in the private cache;
complete windows are skipped, so reruns resume. Stops on any non-JSON or non-00
reply (quota error 22 included). The service key is read from
~/.config/contract-signals/data-go-kr.key and never written anywhere.
"""
import argparse
import gzip
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

URL = 'https://apis.data.go.kr/1230000/ao/PubDataOpnStdService/getDataSetOpnStdCntrctInfo'
KEY_FILE = Path.home() / '.config/contract-signals/data-go-kr.key'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea/opnstd-contracts'
ROWS = 999


def windows(start, end):
    """7-day windows [lo, hi] from end back to start, inclusive."""
    hi = end
    while hi >= start:
        lo = max(start, hi - timedelta(days=6))
        yield lo, hi
        hi = lo - timedelta(days=1)


def call(opener, key, lo, hi, page):
    query = urllib.parse.urlencode(dict(serviceKey=key, pageNo=page, numOfRows=ROWS, type='json',
                                        cntrctCnclsBgnDate=lo.strftime('%Y%m%d'), cntrctCnclsEndDate=hi.strftime('%Y%m%d')))
    for attempt in range(8):
        try:
            body = opener.open(f'{URL}?{query}', timeout=180).read().decode('utf-8', 'replace')
            break
        except Exception as error:
            if attempt == 7:
                raise SystemExit(f'{lo}..{hi} page {page}: {type(error).__name__}: {str(error).replace(key, "<KEY>")[:200]}')
            time.sleep(min(300, 15 * 2 ** attempt))
    try:
        response = json.loads(body)['response']
    except (ValueError, KeyError):
        raise SystemExit(f'{lo}..{hi} page {page}: unexpected reply (quota?): {body.replace(key, "<KEY>")[:300]}')
    if response['header']['resultCode'] != '00':
        raise SystemExit(f'{lo}..{hi} page {page}: {response["header"]}')
    items = response['body'].get('items') or []
    if isinstance(items, dict):
        items = items.get('item', [])
    return int(response['body']['totalCount']), items if isinstance(items, list) else [items]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', default='2024-09-01')
    parser.add_argument('--end', default='2026-09-01')
    parser.add_argument('--max-calls', type=int, default=9500, help='stop before the daily quota (10,000)')
    args = parser.parse_args()
    key = KEY_FILE.read_text().strip()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    CACHE.mkdir(parents=True, exist_ok=True)
    calls = 0
    for lo, hi in windows(date.fromisoformat(args.start), date.fromisoformat(args.end)):
        target = CACHE / f'{lo}_{hi}.jsonl.gz'
        if target.exists():
            continue
        # Paging is not stable on a live table: rows repeat, shift between pages, or are added
        # mid-run. Passes accumulate distinct contracts until they reach a fresh totalCount; after
        # two passes a shortfall of at most 0.05 % is accepted and recorded in the sidecar file.
        partial = target.with_suffix('.part')
        seen, repeats = set(), 0
        with gzip.open(partial, 'wt', encoding='utf-8') as out:
            for attempt in range(2):
                total, rows = call(opener, key, lo, hi, 1)
                calls += 1
                pages = -(-total // ROWS)
                if calls + pages > args.max_calls:
                    raise SystemExit(f'stopping before {lo}..{hi}: {calls} calls used, window needs {pages}')
                for page in range(1, pages + 1):
                    if page > 1:
                        rows = call(opener, key, lo, hi, page)[1]
                        calls += 1
                        time.sleep(0.2)
                    for row in rows:
                        if row['untyCntrctNo'] in seen:
                            repeats += 1
                            continue
                        seen.add(row['untyCntrctNo'])
                        out.write(json.dumps(row, ensure_ascii=False) + '\n')
                total_after = call(opener, key, lo, hi, 1)[0]
                calls += 1
                if len(seen) >= total_after:
                    break
                print(f'{lo}..{hi}: pass {attempt + 1} has {len(seen)} distinct, totalCount {total} then {total_after}; another pass', flush=True)
            else:
                if total_after - len(seen) > max(2, total_after // 2000):
                    raise SystemExit(f'{lo}..{hi}: {len(seen)} distinct after 2 passes, totalCount {total_after}')
        summary = dict(window=[str(lo), str(hi)], distinct=len(seen), total_count=total_after,
                       shortfall=max(0, total_after - len(seen)), repeats_dropped=repeats, passes=attempt + 1)
        target.with_name(target.name.replace('.jsonl.gz', '.summary.json')).write_text(json.dumps(summary) + '\n')
        partial.rename(target)
        print(f'{lo}..{hi}: {len(seen)} rows, shortfall {summary["shortfall"]}, passes {attempt + 1}, total calls {calls}', flush=True)


if __name__ == '__main__':
    main()
