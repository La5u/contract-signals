#!/usr/bin/env python3
"""Download Fair Trade Commission decisions or court rulings (law.go.kr DRF API) for corruption labels.

Research only. --target ftc lists every KFTC decision whose title matches 입찰 (tender) or 공동행위 (cartel)
into ~/.cache/contract-signals/korea/ftc/; --target ftc-suits lists court rulings on suits against KFTC orders
(case names with 시정명령 / 과징금) into korea/ftc-suits/; --target prec lists court rulings whose full text matches procurement
procurement-offence queries into ~/.cache/contract-signals/korea/prec/. Each full text is fetched once, slowly
(law.go.kr limits bursts), as decisions/<serial>.xml.gz, plus list.json. Reruns resume.
The OC credential is read from ~/.config/contract-signals/law-go-kr.oc and never written anywhere.
Source: 법제처 국가법령정보센터 (attribution required by its terms).
"""
import argparse
import gzip
import json
import os
import re
import sys
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = 'https://www.law.go.kr/DRF'
OC_FILE = Path.home() / '.config/contract-signals/law-go-kr.oc'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea'
TARGETS = {
    # target: (list element, serial field, search scope, queries); search 1 = title, 2 = full text
    'ftc': ('ftc', '결정문일련번호', 1, ('입찰', '공동행위')),
    'prec': ('prec', '판례일련번호', 2, (
        '뇌물 계약', '뇌물 입찰', '입찰방해', '수의계약 뇌물', '배임 수의계약', '업무방해 입찰', '공무상비밀누설 입찰',
        '공무상비밀누설 예정가격',
        # added 2026-10-22: other procurement offences (cartels, construction bribery, brokering, abuse of office,
        # false inspection, fraud, splitting, price leaks, debarment suits, damages suits)
        '건설산업기본법위반 입찰', '건설산업기본법위반 뇌물', '공정거래법위반 입찰', '독점규제및공정거래에관한법률위반 입찰',
        '입찰담합', '들러리 입찰', '배임수재 입찰', '배임수재 납품', '배임수재 공사', '업무상배임 입찰', '알선수재 입찰',
        '알선수재 공사', '알선수재 납품', '제3자뇌물 공사', '뇌물 납품', '뇌물 공사', '뇌물 용역', '뇌물 관급',
        '관급공사 뇌물', '검수 뇌물', '부정한 청탁 공사 계약', '납품 비리', '방위사업 뇌물', '청탁금지법 계약',
        '직권남용 계약', '직권남용 입찰', '허위공문서작성 준공', '허위공문서작성 검수', '국고손실 계약', '횡령 관급',
        '사기 관급', '사기 납품 조달', '입찰 위조 실적', '적격심사 위조', '수의계약 분할', '지방계약법 수의계약',
        '예정가격 누설', '기초금액 누설', '전자입찰 조작', '부정당업자', '입찰참가자격제한처분', '손해배상 담합 입찰')),
    # court rulings on suits against KFTC orders (case-name search), for the finality of collusion labels
    'ftc-suits': ('prec', '판례일련번호', 1, ('시정명령', '과징금납부명령', '과징금부과처분')),
}
API_TARGET = {'ftc-suits': 'prec'}


MAX_FAILURES_IN_A_ROW = 20  # a systematic failure ends the run instead of walking the whole list

def get(opener, path, tries=6, timeout=120, **params):
    url = f'{BASE}/{path}?{urllib.parse.urlencode(params)}'
    for attempt in range(tries):
        try:
            body = opener.open(url, timeout=timeout).read()
            ET.fromstring(body)  # an error page is HTML, not XML
            return body
        except Exception as error:  # network error or non-XML reply: back off, then give up
            if attempt == tries - 1:
                raise SystemExit(f'{path} {params.get("ID") or params.get("page")}: {str(error)[:200]}')
            print(f'retry {attempt + 1} {params.get("ID") or params.get("page")}: {str(error)[:120]}', flush=True)
            time.sleep(30 * (attempt + 1) if tries > 3 else 5)


def listing(opener, oc, delay, target):
    element, serial_field, scope, queries = TARGETS[target]
    found = {}
    for query in queries:
        page = 1
        while True:
            root = ET.fromstring(get(opener, 'lawSearch.do', OC=oc, target=API_TARGET.get(target, target), type='XML', query=query,
                                     search=scope, display=100, page=page))
            items = root.findall(element)
            for item in items:
                serial = item.findtext(serial_field)
                found.setdefault(serial, {child.tag: (child.text or '').strip() for child in item})
                found[serial].setdefault('queries', [])
                if query not in found[serial]['queries']:
                    found[serial]['queries'].append(query)
            total = int(root.findtext('totalCnt') or 0)
            print(f'{query}: page {page}, {len(items)} items, total {total}', flush=True)
            if not items or page * 100 >= total:
                break
            page += 1
            time.sleep(delay)
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delay', type=float, default=2.0, help='seconds between requests')
    parser.add_argument('--workers', type=int, default=1, help='parallel full-text requests')
    parser.add_argument('--since', default='', help='only rulings/decisions dated from this year on, e.g. 2010')
    parser.add_argument('--skip-kinds', nargs='*', default=[], help='case kinds (사건종류명) not to fetch, e.g. 세무 가사 특허')
    parser.add_argument('--relist', action='store_true', help='refresh list.json')
    parser.add_argument('--target', choices=sorted(TARGETS), default='ftc')
    args = parser.parse_args()
    oc = OC_FILE.read_text().strip()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    opener.addheaders = [('User-Agent', 'contract-signals research (bid-rigging labels; slow sequential)')]
    out = CACHE / args.target / 'decisions'
    out.mkdir(parents=True, exist_ok=True)
    list_file = CACHE / args.target / 'list.json'
    if args.relist or not list_file.exists():
        found = listing(opener, oc, args.delay, args.target)
        list_file.write_text(json.dumps(found, ensure_ascii=False, indent=1) + '\n')
    found = json.loads(list_file.read_text())
    todo = [s for s in found if re.fullmatch(r'\d+', s) and not (out / f'{s}.xml.gz').exists()
            and (found[s].get('선고일자') or found[s].get('결정일자') or '')[:4] >= args.since and found[s].get('사건종류명') not in args.skip_kinds]
    print(f'{len(found)} decisions listed, {len(todo)} to fetch', flush=True)
    done, failed = [0], {'run': 0, 'all': 0}
    lock = threading.Lock()

    def fetch(serial):
        if failed['run'] >= MAX_FAILURES_IN_A_ROW:
            return
        try:
            body = get(opener, 'lawService.do', tries=3, timeout=45, OC=oc, target=API_TARGET.get(args.target, args.target), ID=serial, type='XML')
        except SystemExit as error:  # one document the server never answers must not stop the rest; a rerun retries it
            with lock:
                failed['run'] += 1
                failed['all'] += 1
            print(f'skipped {serial}: {error}', flush=True)
            return
        with lock:
            failed['run'] = 0
        tmp = out / f'{serial}.part'
        tmp.write_bytes(gzip.compress(body))
        tmp.rename(out / f'{serial}.xml.gz')
        done[0] += 1
        if done[0] % 50 == 0:
            print(f'{done[0]}/{len(todo)} fetched', flush=True)
        time.sleep(args.delay)

    with ThreadPoolExecutor(args.workers) as pool:  # each worker waits --delay between its own requests
        list(pool.map(fetch, todo))
    if failed['run'] >= MAX_FAILURES_IN_A_ROW:
        sys.exit(f'stopped: {MAX_FAILURES_IN_A_ROW} documents failed in a row (server down, blocked or credential '
                 f'rejected?); {done[0]} fetched')
    if failed['all']:
        sys.exit(f'done with {failed["all"]} documents skipped; rerun to retry them')
    print('done', flush=True)


if __name__ == '__main__':
    main()
