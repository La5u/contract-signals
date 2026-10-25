#!/usr/bin/env python3
"""Download every DOJ press release (justice.gov/api/v1/press_releases.json) for US label search.

Research only: False Claims Act settlements, bid-rigging pleas and procurement-fraud cases are found later by
filtering these locally. One page of 50 releases per request, one request in flight, --delay seconds apart (robots.txt
allows /api/). Writes ~/.cache/contract-signals/us-doj/press/<page>.json.gz (results as published); a rerun skips
pages already saved. The archive is ordered by the API, so a rerun after new releases may shift pages: refetch the
newest pages with --refresh N.
"""
import argparse
import gzip
import json
import os
import time
import urllib.request
from pathlib import Path

API = 'https://www.justice.gov/api/v1/press_releases.json'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/us-doj/press'
UA = 'contract-signals research (procurement integrity; contact via https://contracts.lasu.dev)'


def get(page):
    req = urllib.request.Request(f'{API}?pagesize=50&page={page}', headers={'User-Agent': UA})
    for attempt in range(6):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=120).read())
        except Exception as error:
            if attempt == 5:
                raise SystemExit(f'page {page}: {type(error).__name__}: {error}')
            time.sleep(20 * 2 ** attempt)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--delay', type=float, default=1.0)
    p.add_argument('--refresh', type=int, default=0, help='refetch the first N pages')
    args = p.parse_args(argv)
    CACHE.mkdir(parents=True, exist_ok=True)
    first = get(0)
    pages = -(-int(first['metadata']['resultset']['count']) // 50)
    print(f'{first["metadata"]["resultset"]["count"]} releases, {pages} pages', flush=True)
    for page in range(pages):
        out = CACHE / f'{page:05d}.json.gz'
        if out.exists() and page >= args.refresh:
            continue
        data = first if page == 0 else get(page)
        tmp = out.with_suffix('.tmp')
        with gzip.open(tmp, 'wt', encoding='utf-8') as f:
            json.dump(data.get('results', []), f, ensure_ascii=False)
        tmp.rename(out)
        if page % 100 == 0:
            print(f'page {page}/{pages}', flush=True)
        time.sleep(args.delay)
    print('done', flush=True)


if __name__ == '__main__':
    main()
