#!/usr/bin/env python3
"""Download KONEPS bid-opening results (data.go.kr 조달청_나라장터 낙찰정보서비스, ScsbidInfoService).

  notices  every opening result (물품 Thng, 용역 Servc, 공사 Cnstwk, 외자 Frgcpt) entered in [--start, --end),
           by 7-day window of input date (inqryDiv=1): status, participants, winner. About 1,000 calls.
  bids     every bidder of every opening (open-standard dataset, PubDataOpnStdService
           getDataSetOpnStdScsbidInfo), by opening day and business type: rank, business number and name, bid
           amount, rate and time, reserve and base prices, disqualification reason, final winner. About 180
           calls per working day nationwide (2 years: ~90,000, about 10 quota days). Kept fields: KEEP below (CEO names, the
           winner's address, telephone and official are dropped: not needed, and personal).
           --days FILE fetches only the listed days (one YYYY-MM-DD per line), e.g. those of labelled tenders.
  openings opening dates of the notices in --notices FILE (one bidNtceNo per line; the KFTC-rigged tenders
           whose decision gives none), by notice number (inqryDiv=4), works first, then goods and services;
           appends "notice<TAB>date" to bids/openings.tsv, so a rerun skips notices already found.

Private cache ~/.cache/contract-signals/korea/bids (gzipped JSONL per window or day); every stage resumes (bids page
by page).
Stops on any non-00 reply and before --max-calls per operation and run (development keys: ScsbidInfoService
1,000 calls a day, PubDataOpnStdService 10,000; production keys 1,000,000). The service key is read from
~/.config/contract-signals/data-go-kr.key and never written anywhere. Losing bidders' identities and CEO names
stay in this private cache; the explorer only receives derived indicators.
"""
import argparse
import gzip
import json
import os
import sys
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

BASE = 'https://apis.data.go.kr/1230000/as/ScsbidInfoService/'
OPEN_STANDARD = 'https://apis.data.go.kr/1230000/ao/PubDataOpnStdService/getDataSetOpnStdScsbidInfo'
BUSINESS = {1: 'goods', 2: 'foreign', 3: 'works', 5: 'services'}   # bsnsDivCd
KEEP = ('bidNtceNo', 'bidNtceOrd', 'bidNtceNm', 'bsnsDivNm', 'cntrctCnclsSttusNm', 'cntrctCnclsMthdNm', 'bidwinrDcsnMthdNm',
        'ntceInsttNm', 'ntceInsttCd', 'dmndInsttNm', 'dmndInsttCd', 'sucsfLwstlmtRt', 'presmptPrce', 'rsrvtnPrce', 'bssAmt',
        'opengDate', 'opengTm', 'opengRsltDivNm', 'opengRank', 'bidprcCorpBizrno', 'bidprcCorpNm', 'bidprcAmt', 'bidprcRt',
        'bidprcDate', 'bidprcTm', 'sucsfYn', 'dqlfctnRsn', 'fnlSucsfAmt', 'fnlSucsfRt', 'fnlSucsfDate', 'fnlSucsfCorpNm',
        'fnlSucsfCorpBizrno', 'dataBssDate')
KINDS = ('Thng', 'Servc', 'Cnstwk', 'Frgcpt')
KEY_FILE = Path.home() / '.config/contract-signals/data-go-kr.key'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea/bids'
ROWS = 999


class Budget(Exception):
    pass


class Api:
    def __init__(self, key, max_calls):
        self.key, self.max_calls, self.calls, self.lock = key, max_calls, {}, threading.Lock()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def get(self, operation, **params):
        """(totalCount, items) of one page; raises Budget before the per-operation call limit."""
        with self.lock:
            if self.calls.get(operation, 0) >= self.max_calls:
                raise Budget(operation)
            self.calls[operation] = self.calls.get(operation, 0) + 1
        query = urllib.parse.urlencode(dict(serviceKey=self.key, type='json', numOfRows=ROWS, **params))
        url = OPEN_STANDARD if operation == 'openStandard' else f'{BASE}{operation}'
        for attempt in range(8):
            try:
                body = self.opener.open(f'{url}?{query}', timeout=180).read().decode('utf-8', 'replace')
                break
            except Exception as error:
                if attempt == 7:
                    raise SystemExit(f'{operation} {params}: {type(error).__name__}: {str(error).replace(self.key, "<KEY>")[:200]}')
                print(f'retry {attempt + 1}/7 {operation} {params}: {type(error).__name__}', file=sys.stderr, flush=True)
                time.sleep(min(300, 15 * 2 ** attempt))
        try:
            response = json.loads(body)['response']
        except (ValueError, KeyError):
            raise SystemExit(f'{operation} {params}: unexpected reply (quota?): {body.replace(self.key, "<KEY>")[:300]}')
        if response['header']['resultCode'] != '00':
            raise SystemExit(f'{operation} {params}: {response["header"]}')
        items = response['body'].get('items') or []
        if isinstance(items, dict):
            items = items.get('item', [])
        return int(response['body'].get('totalCount') or 0), items if isinstance(items, list) else [items]

    def all_pages(self, operation, **params):
        total, rows = self.get(operation, pageNo=1, **params)
        for page in range(2, -(-total // ROWS) + 1):
            rows += self.get(operation, pageNo=page, **params)[1]
        return total, rows


def windows(start, end):
    """7-day windows [lo, hi) from end back to start."""
    hi = end
    while hi > start:
        lo = max(start, hi - timedelta(days=7))
        yield lo, hi
        hi = lo


def fetch_notices(api, start, end):
    for kind in KINDS:
        folder = CACHE / 'notices' / kind
        folder.mkdir(parents=True, exist_ok=True)
        for lo, hi in windows(start, end):
            target = folder / f'{lo}_{hi}.jsonl.gz'
            if target.exists():
                continue
            last = hi - timedelta(days=1)
            total, rows = api.all_pages(f'getOpengResultListInfo{kind}', inqryDiv=1,
                                        inqryBgnDt=lo.strftime('%Y%m%d') + '0000', inqryEndDt=last.strftime('%Y%m%d') + '2359')
            if len(rows) < total:
                raise SystemExit(f'{kind} {lo}..{hi}: {len(rows)} of {total} rows; not saved')
            part = target.with_suffix('.part')
            with gzip.open(part, 'wt', encoding='utf-8') as out:
                for row in rows:
                    out.write(json.dumps({**row, 'kind': kind}, ensure_ascii=False) + '\n')
            part.rename(target)
            print(f'{kind} {lo}..{hi}: {total} notices', flush=True)


def fetch_bids(api, start, end, only=None, workers=1):
    """One file per opening day and business type, newest day first, `workers` at a time. A day is saved only when
    its rows reach the totalCount of its first page (past openings no longer change). only: a set of days instead
    of the range."""
    days = sorted(only, reverse=True) if only else [end - timedelta(days=i + 1) for i in range((end - start).days)]
    tasks = []
    for day in days:
        for code, name in BUSINESS.items():
            folder = CACHE / 'bids' / name
            folder.mkdir(parents=True, exist_ok=True)
            if not (folder / f'{day}.jsonl.gz').exists():
                tasks.append((day, code, name, folder / f'{day}.jsonl.gz'))
    pool = ThreadPoolExecutor(workers)
    try:
        for future in [pool.submit(fetch_bid_day, api, *task) for task in tasks]:
            future.result()
    finally:
        pool.shutdown(cancel_futures=True)   # on an error, finish the running days only


def fetch_bid_day(api, day, code, name, target):
    """Each page is saved as it arrives (in <day>.pages/, with the day's totalCount), so a restart repeats only the
    pages in flight; the pages are joined into <day>.jsonl.gz once all are there."""
    stamp = day.strftime('%Y%m%d')
    params = dict(bsnsDivCd=code, opengBgnDt=stamp + '0000', opengEndDt=stamp + '2359')
    pages = target.with_name(f'{day}.pages')
    pages.mkdir(exist_ok=True)
    total_file = pages / 'total'
    total = int(total_file.read_text()) if total_file.exists() else None
    page_file = lambda n: pages / f'{n:05}.jsonl.gz'

    def save(n, rows):
        part = page_file(n).with_suffix('.part')
        with gzip.open(part, 'wt', encoding='utf-8') as out:
            for row in rows:
                out.write(json.dumps({k: row.get(k) for k in KEEP}, ensure_ascii=False) + '\n')
        part.rename(page_file(n))

    if total is None or not page_file(1).exists():
        first_total, rows = api.get('openStandard', pageNo=1, **params)
        if total is not None and first_total != total:   # the day changed since the saved pages: start over
            for old in pages.iterdir():
                old.unlink()
        total = first_total
        save(1, rows)
        total_file.write_text(str(total))
    count = max(1, -(-total // ROWS))
    for n in range(2, count + 1):
        if not page_file(n).exists():
            page_total, rows = api.get('openStandard', pageNo=n, **params)
            if page_total != total:
                raise SystemExit(f'{name} {day}: totalCount changed from {total} to {page_total} at page {n}')
            save(n, rows)
    saved = 0
    part = target.with_suffix('.part')
    with gzip.open(part, 'wt', encoding='utf-8') as out:
        for n in range(1, count + 1):
            with gzip.open(page_file(n), 'rt', encoding='utf-8') as f:
                for line in f:
                    out.write(line)
                    saved += 1
    if saved < total:
        part.unlink()
        raise SystemExit(f'{name} {day}: {saved} of {total} rows; not saved')
    part.rename(target)
    for old in pages.iterdir():
        old.unlink()
    pages.rmdir()
    if total:
        print(f'{name} {day}: {total} bid rows', flush=True)


def find_openings(api, notices):
    out = CACHE / 'bids' / 'openings.tsv'
    out.parent.mkdir(parents=True, exist_ok=True)
    found = {line.split('\t')[0] for line in out.read_text().splitlines()} if out.exists() else set()
    with out.open('a') as f:
        for notice in notices:
            if notice in found:
                continue
            date_found = None
            for kind in ('Cnstwk', 'Thng', 'Servc', 'Frgcpt'):
                _, rows = api.get(f'getOpengResultListInfo{kind}', pageNo=1, inqryDiv=4, bidNtceNo=notice)
                dates = sorted({r['opengDt'][:10] for r in rows if r.get('opengDt')})
                if dates:
                    date_found = dates[0]
                    break
            f.write(f'{notice}\t{date_found or ""}\n')
            f.flush()
            found.add(notice)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('stage', choices=('notices', 'bids', 'openings'))
    parser.add_argument('--days', type=Path, help='bids: only these days (YYYY-MM-DD per line)')
    parser.add_argument('--notices', type=Path, help='openings: notice numbers, one per line')
    parser.add_argument('--start', default='2024-09-01')
    parser.add_argument('--end', default='2026-09-01', help='exclusive')
    parser.add_argument('--max-calls', type=int, default=9500, help='per operation and run (daily quota 10,000)')
    parser.add_argument('--workers', type=int, default=1, help='bids: days fetched at once (calls take ~13 s)')
    args = parser.parse_args()
    api = Api(KEY_FILE.read_text().strip(), args.max_calls)
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        if args.stage == 'openings':
            find_openings(api, args.notices.read_text().split())
        elif args.stage == 'bids' and args.days:
            fetch_bids(api, None, None, {date.fromisoformat(d) for d in args.days.read_text().split()}, args.workers)
        else:
            start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
            if args.stage == 'notices':
                fetch_notices(api, start, end)
            else:
                fetch_bids(api, start, end, workers=args.workers)
    except Budget:
        print(f'{args.stage}: call limit reached; rerun tomorrow to continue', flush=True)
    print('calls:', api.calls, flush=True)


if __name__ == '__main__':
    main()
