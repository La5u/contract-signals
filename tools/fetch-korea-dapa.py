#!/usr/bin/env python3
"""Download DAPA (방위사업청, 국방전자조달 D2B) contracts from data.go.kr 방위사업청_군수품조달정보 계약정보_GW
(15158419, apis.data.go.kr/1690000/CntrctInfoService; licence 이용허락범위 제한 없음).

Research only, for linking KFTC-rigged DAPA tenders (most unlinked KFTC tenders after PPS) and for contract-level
checks on defence contracts. Three operations, one month per request window (cntrctDateBegin/End, YYYYMMDD), 1,000
rows a page: domestic (getDmstcCntrctInfoList: amount, planned price, winning rate, method, winner name), facility
(getFcltyCntrctInfoList: also bid date, winning bid, construction dates) and foreign (getOutnatnCntrctInfoList:
number, winner, date only). The API gives no business registration number; winners are firm names.

Writes ~/.cache/contract-signals/korea/dapa/contracts/<kind>/<YYYY-MM>.jsonl.gz (rows as published) and
done.tsv (kind, month, totalCount, rows); a rerun skips finished months. Months run in --order: the label years
first by default (2008-2016), then the rest back to --start. Stops cleanly at the daily quota
(LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR) or after --max-calls per operation; rerun the next day.
"""
import argparse
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

BASE = 'https://apis.data.go.kr/1690000/CntrctInfoService/'
KINDS = {'domestic': 'getDmstcCntrctInfoList', 'facility': 'getFcltyCntrctInfoList', 'foreign': 'getOutnatnCntrctInfoList'}
KEY_FILE = Path.home() / '.config/contract-signals/data-go-kr.key'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea/dapa/contracts'
ROWS = 1000
QUOTA = 'LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR'


class Budget(Exception):
    pass


class Api:
    def __init__(self, key, max_calls, delay):
        self.key, self.max_calls, self.delay, self.calls = key, max_calls, delay, {}
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def get(self, operation, **params):
        """(totalCount, items) of one page; raises Budget at the quota or the per-operation limit."""
        if self.calls.get(operation, 0) >= self.max_calls:
            raise Budget(f'{operation}: --max-calls reached')
        self.calls[operation] = self.calls.get(operation, 0) + 1
        query = urllib.parse.urlencode(dict(serviceKey=self.key, _type='json', numOfRows=ROWS, **params))
        for attempt in range(7):
            try:
                body = self.opener.open(f'{BASE}{operation}?{query}', timeout=180).read().decode('utf-8', 'replace')
                break
            except Exception as error:
                text = error.read().decode('utf-8', 'replace') if isinstance(error, urllib.error.HTTPError) else ''
                if QUOTA in text:
                    raise Budget(f'{operation}: daily quota')
                if attempt == 6:
                    raise SystemExit(f'{operation} {params}: {type(error).__name__}: {str(error).replace(self.key, "<KEY>")[:200]}')
                print(f'retry {attempt + 1}/6 {operation} {params}: {type(error).__name__}', file=sys.stderr, flush=True)
                time.sleep(min(300, 15 * 2 ** attempt))
        time.sleep(self.delay)
        if QUOTA in body:
            raise Budget(f'{operation}: daily quota')
        try:
            response = json.loads(body)['response']
        except (ValueError, KeyError):
            raise SystemExit(f'{operation} {params}: unexpected reply: {body.replace(self.key, "<KEY>")[:300]}')
        if response['header']['resultCode'] != '00':
            raise SystemExit(f'{operation} {params}: {response["header"]}')
        items = (response.get('body') or {}).get('items') or []
        if isinstance(items, dict):
            items = items.get('item', [])
        return int((response.get('body') or {}).get('totalCount') or 0), items if isinstance(items, list) else [items]


def months(start, end, first):
    """Months [start, end] as (year, month): those in the `first` years, then the rest, newest first."""
    out = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    out.sort(reverse=True)
    return [x for x in out if x[0] in first] + [x for x in out if x[0] not in first]


def month_end(y, m):
    return (date(y + (m == 12), m % 12 + 1, 1).toordinal() - 1)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--start', default='2003-01-01', help='first month (YYYY-MM-DD)')
    p.add_argument('--end', default=date.today().isoformat(), help='last month (YYYY-MM-DD)')
    p.add_argument('--first-years', default='2008-2016', help='years fetched first (label years of the rigged tenders)')
    p.add_argument('--kinds', default='domestic,facility,foreign')
    p.add_argument('--max-calls', type=int, default=95, help='calls per operation this run (development quota 100/day)')
    p.add_argument('--delay', type=float, default=1.0, help='seconds between calls')
    args = p.parse_args(argv)
    lo, hi = (int(x) for x in args.first_years.split('-'))
    order = months(date.fromisoformat(args.start), date.fromisoformat(args.end), set(range(lo, hi + 1)))
    api = Api(KEY_FILE.read_text().strip(), args.max_calls, args.delay)
    done_file = CACHE / 'done.tsv'
    CACHE.mkdir(parents=True, exist_ok=True)
    done = {tuple(line.split('\t')[:2]) for line in done_file.read_text().splitlines()} if done_file.exists() else set()
    for kind in args.kinds.split(','):
        operation = KINDS[kind]
        (CACHE / kind).mkdir(exist_ok=True)
        fetched = 0
        try:
            for y, m in order:
                key = (kind, f'{y}-{m:02d}')
                if key in done:
                    continue
                begin, end = f'{y}{m:02d}01', date.fromordinal(month_end(y, m)).strftime('%Y%m%d')
                total, rows = api.get(operation, pageNo=1, cntrctDateBegin=begin, cntrctDateEnd=end)
                for page in range(2, -(-total // ROWS) + 1):
                    rows += api.get(operation, pageNo=page, cntrctDateBegin=begin, cntrctDateEnd=end)[1]
                if len(rows) != total:
                    print(f'{kind} {key[1]}: {len(rows)} rows for totalCount {total}', file=sys.stderr, flush=True)
                tmp = CACHE / kind / f'{key[1]}.jsonl.gz.tmp'
                with gzip.open(tmp, 'wt', encoding='utf-8') as f:
                    for r in rows:
                        f.write(json.dumps(r, ensure_ascii=False) + '\n')
                tmp.rename(CACHE / kind / f'{key[1]}.jsonl.gz')
                with open(done_file, 'a') as f:
                    f.write(f'{kind}\t{key[1]}\t{total}\t{len(rows)}\n')
                done.add(key)
                fetched += 1
                print(f'{kind} {key[1]}: {total} contracts', flush=True)
        except Budget as stop:
            print(f'stopped: {stop}', flush=True)
        left = sum(1 for y, m in order if (kind, f'{y}-{m:02d}') not in done)
        print(f'{kind}: {fetched} months this run, {left} left, {api.calls.get(operation, 0)} calls', flush=True)


if __name__ == '__main__':
    main()
