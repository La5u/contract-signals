#!/usr/bin/env python3
"""Download Fair Trade Commission decisions or court rulings (law.go.kr DRF API) for corruption labels.

Research only. --target ftc lists every KFTC decision whose title matches 입찰 (tender) or 공동행위 (cartel)
into ~/.cache/contract-signals/korea/ftc/; --target ftc-suits lists court rulings on suits against KFTC orders
(case names with 시정명령 / 과징금) into korea/ftc-suits/; --target prec lists court rulings whose full text matches procurement
bribery/obstruction queries into ~/.cache/contract-signals/korea/prec/. Each full text is fetched once, slowly
(law.go.kr limits bursts), as decisions/<serial>.xml.gz, plus list.json. Reruns resume.
The OC credential is read from ~/.config/contract-signals/law-go-kr.oc and never written anywhere.
Source: 법제처 국가법령정보센터 (attribution required by its terms).
"""
import argparse
import gzip
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = 'https://www.law.go.kr/DRF'
OC_FILE = Path.home() / '.config/contract-signals/law-go-kr.oc'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea'
TARGETS = {
    # target: (list element, serial field, search scope, queries); search 1 = title, 2 = full text
    'ftc': ('ftc', '결정문일련번호', 1, ('입찰', '공동행위')),
    'prec': ('prec', '판례일련번호', 2, ('뇌물 계약', '뇌물 입찰', '입찰방해', '수의계약 뇌물', '배임 수의계약',
                                     '업무방해 입찰', '공무상비밀누설 입찰', '공무상비밀누설 예정가격')),
    # court rulings on suits against KFTC orders (case-name search), for the finality of collusion labels
    'ftc-suits': ('prec', '판례일련번호', 1, ('시정명령', '과징금납부명령', '과징금부과처분')),
}
API_TARGET = {'ftc-suits': 'prec'}


def get(opener, path, **params):
    url = f'{BASE}/{path}?{urllib.parse.urlencode(params)}'
    for attempt in range(6):
        try:
            body = opener.open(url, timeout=120).read()
            ET.fromstring(body)  # an error page is HTML, not XML
            return body
        except Exception as error:  # network error or non-XML reply: back off, then give up
            if attempt == 5:
                raise SystemExit(f'{path} {params.get("ID") or params.get("page")}: {str(error)[:200]}')
            time.sleep(30 * (attempt + 1))


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
    todo = [s for s in found if re.fullmatch(r'\d+', s) and not (out / f'{s}.xml.gz').exists()]
    print(f'{len(found)} decisions listed, {len(todo)} to fetch', flush=True)
    for n, serial in enumerate(todo, 1):
        body = get(opener, 'lawService.do', OC=oc, target=API_TARGET.get(args.target, args.target), ID=serial, type='XML')
        tmp = out / f'{serial}.part'
        tmp.write_bytes(gzip.compress(body))
        tmp.rename(out / f'{serial}.xml.gz')
        if n % 50 == 0:
            print(f'{n}/{len(todo)} fetched', flush=True)
        time.sleep(args.delay)
    print('done', flush=True)


if __name__ == '__main__':
    main()
