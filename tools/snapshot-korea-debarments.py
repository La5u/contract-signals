#!/usr/bin/env python3
"""Save today's KONEPS debarment list (부정당제재, data.go.kr 15129466 UsrInfoService02/getUnptRsttCorpInfo02).

The API lists only sanctions still in force (inqryDiv=2, by date range): firm, business number, sanctioning body,
legal ground and period. A sanction drops off when it ends, so a snapshot per month keeps the history. Writes
~/.cache/contract-signals/korea/debarments/<YYYY-MM-DD>.jsonl.gz. Run monthly (user timer korea-debarments).
"""
import gzip
import json
import os
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

URL = 'https://apis.data.go.kr/1230000/ao/UsrInfoService02/getUnptRsttCorpInfo02'
KEY_FILE = Path.home() / '.config/contract-signals/data-go-kr.key'
OUT = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea/debarments'


def main():
    key, rows, page = KEY_FILE.read_text().strip(), [], 1
    while True:
        query = urllib.parse.urlencode(dict(serviceKey=key, type='json', numOfRows=999, pageNo=page, inqryDiv=2,
                                            inqryBgnDt='200001010000', inqryEndDt=date.today().strftime('%Y%m%d2359')))
        body = json.loads(urllib.request.urlopen(f'{URL}?{query}', timeout=120).read())['response']['body']
        rows += body.get('items') or []
        if page * 999 >= int(body['totalCount']):
            break
        page += 1
    OUT.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT / f'{date.today()}.jsonl.gz', 'wt', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'{len(rows)} sanctions saved')


if __name__ == '__main__':
    main()
