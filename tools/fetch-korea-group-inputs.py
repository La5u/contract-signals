#!/usr/bin/env python3
"""Research only: inputs of the group indicators G7, G9 and G10 (korea-labels-plan.md, 2026-10-26).

  picks   --notices FILE ("notice<TAB>ord" lines): every bidder's two 복수예비가격 picks of each opening
          (낙찰정보서비스 getOpengResultListInfoOpengCompt, one call per opening) -> group/picks.jsonl
          (notice, ord, clsfc, rbid, bizno, rank, picks); firm and CEO names are dropped.
  firms   --biznos FILE (one business number per line): KONEPS firm registry (사용자정보서비스
          getPrcrmntCorpBasicInfo02) -> group/firms.jsonl (bizno, telephone, fax, address, registration dates);
          the CEO name is dropped; firms not found are recorded as such.
  joint   --start --end (contract dates, end exclusive): contracts with two or more members (계약정보서비스
          getCntrctInfoList{Thng,Servc,Cnstwk,Frgcpt}, by day) -> group/joint/joint.jsonl (kind, contract, date, notice,
          members as [bizno, share]); group/joint/done.tsv records every finished kind-day, joint contracts or not.

Private cache ~/.cache/contract-signals/korea/group (raw replies are not kept). Each stage resumes from its done file
and stops on the server's quota reply (LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR) or after --max-calls; rerun
the next day. The key is read from ~/.config/contract-signals/data-go-kr.key and never written anywhere.
"""
import argparse
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

KEY_FILE = Path.home() / '.config/contract-signals/data-go-kr.key'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea/group'
API = 'https://apis.data.go.kr/1230000/'
PICKS = 'as/ScsbidInfoService/getOpengResultListInfoOpengCompt'
FIRMS = 'ao/UsrInfoService02/getPrcrmntCorpBasicInfo02'
JOINT = 'ao/CntrctInfoService/getCntrctInfoList'
KINDS = ('Thng', 'Servc', 'Cnstwk', 'Frgcpt')
ROWS = 999
QUOTA = 'LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR'


class Quota(Exception):
    pass


class Client:
    def __init__(self, key, max_calls):
        self.key, self.max_calls, self.calls, self.lock, self.spent = key, max_calls, 0, threading.Lock(), False
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def get(self, path, **params):
        """(totalCount, items) of one page."""
        with self.lock:
            if self.spent or self.calls >= self.max_calls:
                raise Quota(path)
            self.calls += 1
        query = urllib.parse.urlencode(dict(ServiceKey=self.key, type='json', **params))
        for attempt in range(6):
            try:
                body = self.opener.open(f'{API}{path}?{query}', timeout=120).read().decode('utf-8', 'replace')
                break
            except Exception as error:
                if isinstance(error, urllib.error.HTTPError) and QUOTA in error.read().decode('utf-8', 'replace'):
                    body = QUOTA
                    break
                if attempt == 5:
                    raise SystemExit(f'{path} {params}: {type(error).__name__}: {str(error).replace(self.key, "<KEY>")[:200]}')
                time.sleep(min(300, 10 * 2 ** attempt))
        if QUOTA in body:
            self.spent = True
            raise Quota(path)
        try:
            response = json.loads(body)['response']
        except (ValueError, KeyError):
            raise SystemExit(f'{path} {params}: unexpected reply: {body.replace(self.key, "<KEY>")[:300]}')
        if response['header']['resultCode'] != '00':
            raise SystemExit(f'{path} {params}: {response["header"]}')
        items = response['body'].get('items') or []
        if isinstance(items, dict):
            items = items.get('item', [])
        return int(response['body'].get('totalCount') or 0), items if isinstance(items, list) else [items]

    def all_pages(self, path, **params):
        total, rows = self.get(path, pageNo=1, numOfRows=ROWS, **params)
        for page in range(2, -(-total // ROWS) + 1):
            rows += self.get(path, pageNo=page, numOfRows=ROWS, **params)[1]
        return rows


def done_set(path):
    return {line.rstrip('\n') for line in path.open(encoding='utf-8')} if path.exists() else set()


def run(items, work, out, done, workers):
    """work(item) -> list of output dicts; output and done lines are appended together, so a stop loses nothing."""
    lock, count = threading.Lock(), [0]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('a', encoding='utf-8') as fo, done.open('a', encoding='utf-8') as fd:
        def one(item):
            rows = work(item)
            with lock:
                for r in rows:
                    fo.write(json.dumps(r, ensure_ascii=False) + '\n')
                fd.write(item + '\n')
                fo.flush()
                fd.flush()
                count[0] += 1
                if count[0] % 500 == 0:
                    print(f'  {count[0]} of {len(items)}', flush=True)
        with ThreadPoolExecutor(workers) as pool:
            futures = [pool.submit(one, i) for i in items]
            stopped = False
            for f in futures:
                try:
                    f.result()
                except Quota:
                    stopped = True
            if stopped:
                print(f'quota or --max-calls reached after {count[0]} items; rerun later to resume', flush=True)
    return count[0]


def num(value):
    value = str(value or '').strip()
    return int(value) if value.isdigit() else None


def picks(client, args):
    wanted = [line.rstrip('\n').replace('\t', ' ') for line in args.notices.open(encoding='utf-8') if line.strip()]
    folder = CACHE / 'picks'
    done = folder / 'done.txt'
    seen = done_set(done)
    items = [i for i in dict.fromkeys(wanted) if i not in seen]
    print(f'{len(items)} openings to fetch', flush=True)

    def work(item):
        notice, order = item.split(' ')
        rows = client.all_pages(PICKS, bidNtceNo=notice, bidNtceOrd=order.zfill(3))
        return [{'notice': notice, 'ord': order.zfill(3), 'clsfc': r.get('bidClsfcNo'), 'rbid': r.get('rbidNo'),
                 'bizno': re.sub(r'\D', '', r.get('prcbdrBizno') or ''), 'rank': r.get('opengRank'),
                 'picks': [n for n in (num(r.get('drwtNo1')), num(r.get('drwtNo2'))) if n is not None]} for r in rows]
    return run(items, work, folder / 'picks.jsonl', done, args.workers)


def firms(client, args):
    wanted = [re.sub(r'\D', '', line) for line in args.biznos.open(encoding='utf-8')]
    folder = CACHE / 'firms'
    done = folder / 'done.txt'
    seen = done_set(done)
    items = [i for i in dict.fromkeys(w for w in wanted if len(w) == 10) if i not in seen]
    print(f'{len(items)} firms to fetch', flush=True)

    def work(bizno):
        _, rows = client.get(FIRMS, inqryDiv=3, bizno=bizno, pageNo=1, numOfRows=10)
        if not rows:
            return [{'bizno': bizno, 'found': False}]
        return [{'bizno': bizno, 'found': True, 'tel': r.get('telNo'), 'fax': r.get('faxNo'), 'zip': r.get('zip'),
                 'adrs': r.get('adrs'), 'dtl': r.get('dtlAdrs'), 'region': r.get('rgnCd'), 'opened': r.get('opbizDt'),
                 'registered': r.get('rgstDt'), 'changed': r.get('chgDt'), 'office': r.get('hdoffceDivNm'),
                 'employees': r.get('emplyeNum')} for r in rows]
    return run(items, work, folder / 'firms.jsonl', done, args.workers)


def members(text):
    """corpList '[1^name^…^share^…^^bizno],[2^…]' -> [[bizno, share]]."""
    out = []
    for part in re.findall(r'\[([^\]]*)\]', text or ''):
        f = part.split('^')
        bizno = re.sub(r'\D', '', f[-1]) if f else ''
        share = next((float(x) for x in f[1:-1] if re.fullmatch(r'\d+(\.\d+)?', x or '')), None)
        if bizno:
            out.append([bizno, share])
    return out


def joint(client, args):
    folder = CACHE / 'joint'
    done = folder / 'done.tsv'
    seen = done_set(done)
    days = []
    d = args.end - timedelta(days=1)
    while d >= args.start:
        days.append(d)
        d -= timedelta(days=1)
    items = [f'{k}\t{d.isoformat()}' for d in days for k in KINDS if f'{k}\t{d.isoformat()}' not in seen]
    print(f'{len(items)} kind-days to fetch', flush=True)

    def work(item):
        kind, day = item.split('\t')
        stamp = day.replace('-', '')
        rows = client.all_pages(JOINT + kind, inqryDiv=1, inqryBgnDt=stamp + '0000', inqryEndDt=stamp + '2359')
        out = []
        for r in rows:
            m = members(r.get('corpList'))
            if len(m) >= 2:
                out.append({'kind': kind, 'contract': r.get('untyCntrctNo'), 'date': r.get('cntrctCnclsDate') or day,
                            'notice': r.get('ntceNo'), 'joint_flag': r.get('cmmnCntrctYn'), 'members': m})
        return out
    return run(items, work, folder / 'joint.jsonl', done, args.workers)


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('stage', choices=('picks', 'firms', 'joint'))
    p.add_argument('--notices', type=Path)
    p.add_argument('--biznos', type=Path)
    p.add_argument('--start', type=date.fromisoformat)
    p.add_argument('--end', type=date.fromisoformat)
    p.add_argument('--max-calls', type=int, default=1_000_000)
    p.add_argument('--workers', type=int, default=4)
    args = p.parse_args()
    need = {'picks': ('notices',), 'firms': ('biznos',), 'joint': ('start', 'end')}[args.stage]
    if any(getattr(args, n) is None for n in need):
        p.error(f'{args.stage} needs --{" --".join(need)}')
    client = Client(KEY_FILE.read_text().strip(), args.max_calls)
    n = {'picks': picks, 'firms': firms, 'joint': joint}[args.stage](client, args)
    print(f'{n} items done, {client.calls} calls', flush=True)


if __name__ == '__main__':
    main()
