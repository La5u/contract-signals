#!/usr/bin/env python3
"""Research only: allocated budget (배정예산, asignBdgtAmt) per KONEPS notice, from the open-standard notice files
(tools/fetch-korea-bid-results.py opnstd-notices -> bids/opnstd-notices/<day>.jsonl.gz), for the round-budget checks
A5/A6 (korea-labels-plan.md, "Round-number checks"), with the notice's date, buyer (공고기관), demanding body, business
type, method and estimated price, so round budgets can be compared within buyer, year and type. Latest notice order
wins. Output: korea/notice-budgets.sqlite.
"""
import gzip
import json
import os
import sqlite3
from pathlib import Path

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea'


def main():
    out = BASE / 'notice-budgets.sqlite'
    tmp = out.with_suffix('.part')
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    con.execute('CREATE TABLE budgets (notice TEXT PRIMARY KEY, ord TEXT, budget INTEGER, date TEXT, buyer TEXT, '
                'demand TEXT, type TEXT, method TEXT, presmpt INTEGER) WITHOUT ROWID')
    files = sorted((BASE / 'bids/opnstd-notices').glob('*.jsonl.gz'))
    for i, f in enumerate(files):
        rows = []
        for line in gzip.open(f, 'rt'):
            r = json.loads(line)
            try:
                b = int(float(r.get('asignBdgtAmt') or 0))
            except ValueError:
                b = 0
            try:
                e = int(float(r.get('presmptPrce') or 0)) or None
            except ValueError:
                e = None
            if b > 0 and r.get('bidNtceNo'):
                rows.append((r['bidNtceNo'], r.get('bidNtceOrd') or '', b, r.get('bidNtceDate'), r.get('ntceInsttCd'),
                             r.get('dmndInsttCd'), r.get('bsnsDivNm'), r.get('cntrctCnclsMthdNm'), e))
        con.executemany('INSERT INTO budgets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(notice) DO UPDATE SET '
                        'ord = excluded.ord, budget = excluded.budget, date = excluded.date, buyer = excluded.buyer, '
                        'demand = excluded.demand, type = excluded.type, method = excluded.method, '
                        'presmpt = excluded.presmpt WHERE excluded.ord >= budgets.ord', rows)
        if i % 500 == 0:
            con.commit()
            print(f'{i}/{len(files)} {f.name}', flush=True)
    con.execute('CREATE INDEX budgets_buyer ON budgets(buyer, date)')
    con.commit()
    print('notices with a budget:', con.execute('SELECT count(*) FROM budgets').fetchone()[0])
    con.close()
    tmp.rename(out)


if __name__ == '__main__':
    main()
