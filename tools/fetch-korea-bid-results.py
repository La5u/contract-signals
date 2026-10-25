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
  ceos     same days and paging as bids; only notice, order, rank, business number and a keyed CEO hash.
           The hash only supports equality checks (shared-CEO check 3); names stay out of the cache.
  openings opening dates of the notices in --notices FILE (one bidNtceNo per line; the KFTC-rigged tenders
           whose decision gives none), by notice number (inqryDiv=4), works first, then goods and services;
           appends "notice<TAB>date" to bids/openings.tsv, so a rerun skips notices already found.
  announcements every bid notice (입찰공고, BidPublicInfoService getBidPblancListInfo*) registered in [--start, --end),
           by 7-day window and kind: notice, deadline and opening dates, method, estimated price, restrictions
           (notice period and threshold checks). About 9,000 calls for 2009-2023. The buyer official's name,
           telephone and e-mail and the document links are dropped.
  opnstd-notices every bid notice of [--start, --end) by notice day from the open-standard dataset
           (getDataSetOpnStdBidPblancInfo, production quota): notice, deadline and opening dates, estimated price,
           method, restrictions. ~2 calls a day. Officials' names, telephones and e-mails are dropped.
  reserves the multiple reserve prices (복수예비가격, getOpengResultListInfo*PreparPcDetail: the 15 drawn prices of
           each tender) entered on the --days listed, one file per day and kind. About 16 calls per day.
  by-notice announcements and reserve prices for --notices FILE, trying works, goods, services and foreign
           (or the kinds after a tab: "notice<TAB>Thng,Servc");
           appends plain JSONL and resumes via by-notice/done.tsv.

Private cache ~/.cache/contract-signals/korea/bids (gzipped JSONL per window or day); every stage resumes (bids page
by page).
Stops on any non-00 reply and before --max-calls per operation and run (development keys: ScsbidInfoService
1,000 calls a day, PubDataOpnStdService 10,000; production keys 1,000,000). The service key is read from
~/.config/contract-signals/data-go-kr.key and never written anywhere. Losing bidders' identities stay in this
private cache; CEO names are never written, and the explorer only receives derived indicators.
"""
import argparse
import gzip
import hashlib
import hmac
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

BASE = 'https://apis.data.go.kr/1230000/as/ScsbidInfoService/'
NOTICE_BASE = 'https://apis.data.go.kr/1230000/ad/BidPublicInfoService/'
NOTICE_DROP = ('Ofcl', 'exctvNm', 'crdtrNm', 'DocUrl', 'FileNm')   # substrings of dropped notice fields
OPEN_STANDARD = 'https://apis.data.go.kr/1230000/ao/PubDataOpnStdService/getDataSetOpnStdScsbidInfo'
OPEN_STANDARD_NOTICES = 'https://apis.data.go.kr/1230000/ao/PubDataOpnStdService/getDataSetOpnStdBidPblancInfo'
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

    def exhausted(self, operation):
        """The server's own quota is spent: later calls of this operation stop locally, without a request."""
        with self.lock:
            self.calls[operation] = self.max_calls
        raise Budget(operation)

    def get(self, operation, **params):
        """(totalCount, items) of one page; raises Budget before the per-operation call limit."""
        with self.lock:
            if self.calls.get(operation, 0) >= self.max_calls:
                raise Budget(operation)
            self.calls[operation] = self.calls.get(operation, 0) + 1
        query = urllib.parse.urlencode(dict(serviceKey=self.key, type='json', numOfRows=ROWS, **params))
        url = (OPEN_STANDARD if operation == 'openStandard' else OPEN_STANDARD_NOTICES if operation == 'openStandardNotices' else
               f'{NOTICE_BASE}{operation}' if operation.startswith('getBidPblanc') else f'{BASE}{operation}')
        for attempt in range(8):
            try:
                body = self.opener.open(f'{url}?{query}', timeout=180).read().decode('utf-8', 'replace')
                break
            except Exception as error:
                if isinstance(error, urllib.error.HTTPError):
                    if 'LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR' in error.read().decode('utf-8', 'replace'):   # a bare 429 is throttling: retry
                        self.exhausted(operation)
                if attempt == 7:
                    raise SystemExit(f'{operation} {params}: {type(error).__name__}: {str(error).replace(self.key, "<KEY>")[:200]}')
                print(f'retry {attempt + 1}/7 {operation} {params}: {type(error).__name__}', file=sys.stderr, flush=True)
                time.sleep(min(300, 15 * 2 ** attempt))
        if 'LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR' in body:
            self.exhausted(operation)
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


def save_rows(target, rows, kind, keep=lambda row: row):
    part = target.with_suffix('.part')
    with gzip.open(part, 'wt', encoding='utf-8') as out:
        for row in rows:
            out.write(json.dumps({**keep(row), 'kind': kind}, ensure_ascii=False) + '\n')
    part.rename(target)


def run_tasks(tasks, workers):
    """Tasks whose operation reached its call limit are skipped (left for the next run); the others go on."""
    pool, limited = ThreadPoolExecutor(workers), set()
    try:
        for future in [pool.submit(*task) for task in tasks]:
            try:
                future.result()
            except Budget as limit:
                limited.add(str(limit))
    finally:
        pool.shutdown(cancel_futures=True)
    if limited:
        raise Budget(', '.join(sorted(limited)))


def fetch_announcements(api, start, end, workers=1):
    def window(kind, lo, hi, target):
        last = hi - timedelta(days=1)
        total, rows = api.all_pages(f'getBidPblancListInfo{kind}', inqryDiv=1,
                                    inqryBgnDt=lo.strftime('%Y%m%d') + '0000', inqryEndDt=last.strftime('%Y%m%d') + '2359')
        if len(rows) < total:
            raise SystemExit(f'announcements {kind} {lo}..{hi}: {len(rows)} of {total} rows; not saved')
        save_rows(target, rows, kind, lambda row: {k: v for k, v in row.items() if not any(d in k for d in NOTICE_DROP)})
        print(f'announcements {kind} {lo}..{hi}: {total} notices', flush=True)

    tasks = []
    for kind in KINDS:
        folder = CACHE / 'announcements' / kind
        folder.mkdir(parents=True, exist_ok=True)
        tasks += [(window, kind, lo, hi, folder / f'{lo}_{hi}.jsonl.gz') for lo, hi in windows(start, end)
                  if not (folder / f'{lo}_{hi}.jsonl.gz').exists()]
    run_tasks(tasks, workers)


def fetch_opnstd_notices(api, start, end, workers=1):
    def day(d, target):
        stamp = d.strftime('%Y%m%d')
        total, rows = api.all_pages('openStandardNotices', bidNtceBgnDt=stamp + '0000', bidNtceEndDt=stamp + '2359')
        if len(rows) < total:
            raise SystemExit(f'opnstd-notices {d}: {len(rows)} of {total} rows; not saved')
        save_rows(target, rows, '', lambda row: {k: v for k, v in row.items() if not any(x in k for x in NOTICE_DROP)})
        print(f'opnstd-notices {d}: {total} notices', flush=True)

    folder = CACHE / 'opnstd-notices'
    folder.mkdir(parents=True, exist_ok=True)
    days = [end - timedelta(days=i + 1) for i in range((end - start).days)]
    run_tasks([(day, d, folder / f'{d}.jsonl.gz') for d in days if not (folder / f'{d}.jsonl.gz').exists()], workers)


def fetch_reserves(api, days, workers=1):
    def day_kind(kind, day, target):
        stamp = day.strftime('%Y%m%d')
        total, rows = api.all_pages(f'getOpengResultListInfo{kind}PreparPcDetail', inqryDiv=1,
                                    inqryBgnDt=stamp + '0000', inqryEndDt=stamp + '2359')
        if len(rows) < total:
            raise SystemExit(f'reserves {kind} {day}: {len(rows)} of {total} rows; not saved')
        save_rows(target, rows, kind)
        print(f'reserves {kind} {day}: {total} rows', flush=True)

    tasks = []
    for kind in KINDS:
        folder = CACHE / 'reserves' / kind
        folder.mkdir(parents=True, exist_ok=True)
        tasks += [(day_kind, kind, day, folder / f'{day}.jsonl.gz') for day in sorted(days, reverse=True)
                  if not (folder / f'{day}.jsonl.gz').exists()]
    run_tasks(tasks, workers)


def ceo_row(row, key):
    name = re.sub(r'\([^)]*\)', '', row.get('bidprcCorpCeoNm') or '')
    name = re.sub(r'외\s*\d+\s*인.*$', '', name).strip().replace(' ', '')
    return {**{k: row.get(k) for k in ('bidNtceNo', 'bidNtceOrd', 'opengRank', 'bidprcCorpBizrno')},
            'ceo': hmac.new(key, name.encode('utf-8'), hashlib.sha256).hexdigest()[:16] if name else None}


def fetch_bids(api, start, end, only=None, workers=1, page_workers=1, folder=None,
               transform=lambda row: {k: row.get(k) for k in KEEP}):
    """One file per opening day and business type, newest day first, `workers` at a time. A day is saved only when
    its rows reach the totalCount of its first page (past openings no longer change). only: a set of days instead
    of the range."""
    folder = CACHE / 'bids' if folder is None else folder
    days = sorted(only, reverse=True) if only else [end - timedelta(days=i + 1) for i in range((end - start).days)]
    tasks = []
    for day in days:
        for code, name in BUSINESS.items():
            business = folder / name
            business.mkdir(parents=True, exist_ok=True)
            if not (business / f'{day}.jsonl.gz').exists():
                tasks.append((day, code, name, business / f'{day}.jsonl.gz'))
    pool = ThreadPoolExecutor(workers)
    try:
        for future in [pool.submit(fetch_bid_day, api, *task, page_workers, transform) for task in tasks]:
            future.result()
    finally:
        pool.shutdown(cancel_futures=True)   # on an error, finish the running days only


def fetch_bid_day(api, day, code, name, target, page_workers=1,
                  transform=lambda row: {k: row.get(k) for k in KEEP}):
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
                out.write(json.dumps(transform(row), ensure_ascii=False) + '\n')
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

    def page(n):
        page_total, rows = api.get('openStandard', pageNo=n, **params)
        if page_total != total:
            raise SystemExit(f'{name} {day}: totalCount changed from {total} to {page_total} at page {n}')
        save(n, rows)

    missing = [n for n in range(2, count + 1) if not page_file(n).exists()]
    with ThreadPoolExecutor(min(page_workers, len(missing)) or 1) as pool:
        for future in [pool.submit(page, n) for n in missing]:
            future.result()
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


def fetch_by_notice(api, notices, workers=1):
    folder = CACHE / 'by-notice'
    folder.mkdir(parents=True, exist_ok=True)
    done = folder / 'done.tsv'
    found = {line.split('\t')[0] for line in done.read_text().splitlines()} if done.exists() else set()
    lock = threading.Lock()
    with (folder / 'notices.jsonl').open('a', encoding='utf-8') as announcements, \
         (folder / 'reserves.jsonl').open('a', encoding='utf-8') as reserves, \
         done.open('a', encoding='utf-8') as finished:
        def notice_rows(notice, kinds):
            kind_found, rows, prices = '', [], []
            try:
                for kind in kinds:
                    total, rows = api.all_pages(f'getBidPblancListInfo{kind}', inqryDiv=2, bidNtceNo=notice)
                    if len(rows) < total:
                        raise SystemExit(f'by-notice {notice}: {len(rows)} of {total} notices; not saved')
                    if rows:
                        total, prices = api.all_pages(f'getOpengResultListInfo{kind}PreparPcDetail',
                                                     inqryDiv=2, bidNtceNo=notice)
                        if len(prices) < total:
                            raise SystemExit(f'by-notice {notice}: {len(prices)} of {total} reserves; not saved')
                        kind_found = kind
                        break
            except Budget as limit:   # this operation's daily quota: leave the notice for a later run, go on with others
                print(f'by-notice {notice}: call limit of {limit}; retried next run', flush=True)
                return
            with lock:
                for row in rows:
                    announcements.write(json.dumps({**{k: v for k, v in row.items() if not any(d in k for d in NOTICE_DROP)},
                                                     'kind': kind_found}, ensure_ascii=False) + '\n')
                for row in prices:
                    reserves.write(json.dumps({**row, 'kind': kind_found}, ensure_ascii=False) + '\n')
                announcements.flush()
                reserves.flush()
                finished.write(f'{notice}\t{kind_found}\n')
                finished.flush()
            print(f'by-notice {notice}: {kind_found} {len(rows)} notices, {len(prices)} reserves', flush=True)

        run_tasks([(notice_rows, notice, kinds) for notice, kinds in notices.items() if notice not in found], workers)


def read_notice_kinds(path):
    """notice -> kinds to try: "notice" alone tries all; "notice<TAB>Thng,Servc" only those, in that order."""
    out = {}
    for line in path.read_text().splitlines():
        notice, _, kinds = line.strip().partition('\t')
        if notice:
            out[notice] = tuple(k for k in kinds.split(',') if k) or ('Cnstwk', 'Thng', 'Servc', 'Frgcpt')
    return out


def read_days(files):
    return {date.fromisoformat(d) for f in files for d in f.read_text().split()}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('stage', choices=('notices', 'bids', 'ceos', 'openings', 'announcements', 'opnstd-notices', 'reserves', 'by-notice'))
    parser.add_argument('--days', type=Path, nargs='+', help='bids, ceos: only these days; reserves: these days (files of YYYY-MM-DD lines)')
    parser.add_argument('--notices', type=Path, help='openings, by-notice: notice numbers, one per line')
    parser.add_argument('--start', default='2024-09-01')
    parser.add_argument('--end', default='2026-09-01', help='exclusive')
    parser.add_argument('--max-calls', type=int, default=9500, help='per operation and run (daily quota 10,000)')
    parser.add_argument('--workers', type=int, default=1, help='bids, ceos, announcements, reserves, by-notice: days, windows or notices fetched at once (calls take ~13 s)')
    parser.add_argument('--page-workers', type=int, default=1, help='bids, ceos: pages of one day fetched at once')
    args = parser.parse_args()
    api = Api(KEY_FILE.read_text().strip(), args.max_calls)
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        if args.stage == 'openings':
            find_openings(api, args.notices.read_text().split())
        elif args.stage == 'by-notice':
            fetch_by_notice(api, read_notice_kinds(args.notices), args.workers)
        elif args.stage == 'ceos':
            fetch_bids(api, date.fromisoformat(args.start), date.fromisoformat(args.end),
                       read_days(args.days) if args.days else None, args.workers, args.page_workers,
                       CACHE / 'ceos', lambda row: ceo_row(row, api.key.encode('utf-8')))
        elif args.stage == 'bids' and args.days:
            fetch_bids(api, None, None, read_days(args.days), args.workers, args.page_workers)
        elif args.stage == 'reserves':
            fetch_reserves(api, read_days(args.days), args.workers)
        else:
            start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
            if args.stage == 'notices':
                fetch_notices(api, start, end)
            elif args.stage == 'opnstd-notices':
                fetch_opnstd_notices(api, start, end, args.workers)
            elif args.stage == 'announcements':
                fetch_announcements(api, start, end, args.workers)
            else:
                fetch_bids(api, start, end, workers=args.workers, page_workers=args.page_workers)
    except Budget:
        print(f'{args.stage}: call limit reached; rerun tomorrow to continue', flush=True)
    print('calls:', api.calls, flush=True)


if __name__ == '__main__':
    main()
