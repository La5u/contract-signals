#!/usr/bin/env python3
"""Every KONEPS contracting institution (수요기관) with its region and type, for the Korean buyer picker.

사용자정보서비스 getDminsttInfo02 (data.go.kr 15129466), inqryDiv=1 by registration or change date, one calendar year
per window -> ~/.cache/contract-signals/korea/institutions/institutions.jsonl (code, name, jurisdiction, three type
levels, region code and name, top-level institution, deleted flag, change date) and done.txt (finished years).
Telephone, fax and street address are dropped. A rerun skips finished years; the latest change of a code wins when read.
"""
import argparse
import importlib.util
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('group', HERE / 'fetch-korea-group-inputs.py')
group = importlib.util.module_from_spec(spec)
spec.loader.exec_module(group)

PATH = 'ao/UsrInfoService02/getDminsttInfo02'
OUT = group.CACHE.parent / 'institutions'
KEEP = {'dminsttCd': 'code', 'dminsttNm': 'name', 'jrsdctnDivNm': 'jurisdiction', 'insttTyCdLrgclsfcNm': 'type1',
        'insttTyCdMidclsfcNm': 'type2', 'insttTyCdSmlclsfcNm': 'type3', 'rgnCd': 'region_code', 'rgnNm': 'region',
        'toplvlInsttCd': 'top_code', 'toplvlInsttNm': 'top_name', 'dltYn': 'deleted', 'chgDt': 'changed',
        'rgstDt': 'registered'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--start', type=int, default=1995)
    p.add_argument('--end', type=int, default=date.today().year)
    p.add_argument('--max-calls', type=int, default=900)
    p.add_argument('--workers', type=int, default=4)
    a = p.parse_args()
    client = group.Client(group.KEY_FILE.read_text().strip(), a.max_calls)
    OUT.mkdir(parents=True, exist_ok=True)
    done = group.done_set(OUT / 'done.txt')
    lock = threading.Lock()
    with (OUT / 'institutions.jsonl').open('a', encoding='utf-8') as fo, (OUT / 'done.txt').open('a') as fd:
        def one(year):
            try:
                rows = client.all_pages(PATH, inqryDiv=1, inqryBgnDt=f'{year}01010000', inqryEndDt=f'{year}12312359')
            except group.Quota:
                print(f'{year} stopped: quota or --max-calls; rerun later', flush=True)
                return
            with lock:  # a year's rows and its done line are written together, so a stop loses nothing
                for r in rows:
                    fo.write(json.dumps({v: (r.get(k) or '').strip() or None for k, v in KEEP.items()}, ensure_ascii=False) + '\n')
                fo.flush()
                fd.write(f'{year}\n')
                fd.flush()
                print(year, len(rows), flush=True)
        with ThreadPoolExecutor(a.workers) as pool:
            list(pool.map(one, [y for y in range(a.start, a.end + 1) if str(y) not in done]))


if __name__ == '__main__':
    main()
