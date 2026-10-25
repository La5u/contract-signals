#!/usr/bin/env python3
"""Download contracts of Korean public companies that procure outside KONEPS, for linking KFTC-rigged tenders.

  lh     한국토지주택공사 계약현황정보_GW (data.go.kr 15159010, B552555/OpenContractInfoList/getOpenContractInfo):
         contract number, name, date, method, amount, start/end dates, winner name and business number, ordering
         department. By contract date (contractDtStart/End). The winner's CEO name and address are dropped.
  kogas  한국가스공사_입찰정보 (15157366, B551210/bidInfoList2/getBidInfoList2): bid number, name, type, method,
         notice/closing/opening dates, winner name and business number, winning amount, rate and date. By notice
         date (DOCDATE_START/END).

Research only. One calendar year per window, 1,000 rows a page. Writes
~/.cache/contract-signals/korea/agencies/<source>/<year>.jsonl.gz and done.tsv (source, year, totalCount, rows);
a rerun skips finished years. Licence of both: 이용허락범위 제한 없음.
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
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

KEY_FILE = Path.home() / '.config/contract-signals/data-go-kr.key'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea/agencies'
ROWS = 1000
SOURCES = {
    'lh': {'url': 'https://apis.data.go.kr/B552555/OpenContractInfoList/getOpenContractInfo', 'encoding': 'euc-kr',
           'window': lambda y: {'contractDtStart': f'{y}0101', 'contractDtEnd': f'{y}1231', 'bidNum': ''},
           'drop': ('ctrctVndrCeoNm', 'ctrctVndrAddr')},
    'kogas': {'url': 'https://apis.data.go.kr/B551210/bidInfoList2/getBidInfoList2', 'encoding': 'utf-8',
              'window': lambda y: {'DOCDATE_START': f'{y}0101', 'DOCDATE_END': f'{y}1231'}, 'drop': ()},
}


def page(opener, key, source, year, number):
    s = SOURCES[source]
    query = urllib.parse.urlencode(dict(serviceKey=key, pageNo=number, numOfRows=ROWS, **s['window'](year)))
    for attempt in range(6):
        try:
            raw = opener.open(f'{s["url"]}?{query}', timeout=180).read()
            break
        except Exception as error:
            if attempt == 5:
                raise SystemExit(f'{source} {year} p{number}: {type(error).__name__}: {str(error).replace(key, "<KEY>")[:200]}')
            time.sleep(15 * 2 ** attempt)
    text = raw.decode(s['encoding'], 'replace')
    if 'LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR' in text:
        raise SystemExit(f'{source}: daily quota reached; rerun tomorrow')
    root = ET.fromstring(text.split('?>', 1)[-1].strip())
    code = root.findtext('header/resultCode')
    if code not in ('00', '0'):
        if code == '03':  # NODATA
            return 0, []
        raise SystemExit(f'{source} {year}: {code} {root.findtext("header/resultMsg")}')
    total = int(root.findtext('body/totalCount') or 0)
    rows = [{c.tag: (c.text or '').strip() for c in item if c.tag not in s['drop']} for item in root.iter('item')]
    return total, rows


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--sources', default='lh,kogas')
    p.add_argument('--start', type=int, default=2000)
    p.add_argument('--end', type=int, default=date.today().year)
    p.add_argument('--delay', type=float, default=1.0)
    args = p.parse_args(argv)
    key = KEY_FILE.read_text().strip()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    CACHE.mkdir(parents=True, exist_ok=True)
    done_file = CACHE / 'done.tsv'
    done = {tuple(l.split('\t')[:2]) for l in done_file.read_text().splitlines()} if done_file.exists() else set()
    for source in args.sources.split(','):
        (CACHE / source).mkdir(exist_ok=True)
        for year in range(args.end, args.start - 1, -1):
            if (source, str(year)) in done:
                continue
            total, rows = page(opener, key, source, year, 1)
            time.sleep(args.delay)
            for n in range(2, -(-total // ROWS) + 1):
                rows += page(opener, key, source, year, n)[1]
                time.sleep(args.delay)
            if len(rows) != total:
                print(f'{source} {year}: {len(rows)} rows for totalCount {total}', file=sys.stderr, flush=True)
            with gzip.open(CACHE / source / f'{year}.jsonl.gz', 'wt', encoding='utf-8') as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + '\n')
            with open(done_file, 'a') as f:
                f.write(f'{source}\t{year}\t{total}\t{len(rows)}\n')
            print(f'{source} {year}: {total}', flush=True)


if __name__ == '__main__':
    main()
