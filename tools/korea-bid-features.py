#!/usr/bin/env python3
"""Research only: one row of bid features per KONEPS bid opening, for the bid-level checks B1-B7.

Plan: research/calibration/korea-labels-plan.md, "Bid-level checks" (fixed before any labelled bid was read). Reads
every day file in ~/.cache/contract-signals/korea/bids/bids/<type>/<day>.jsonl.gz (tools/fetch-korea-bid-results.py
bids) and writes ~/.cache/contract-signals/korea/bid-features.sqlite:

- `openings`: notice, ord (bidNtceOrd), day, business type, year; bids (rows), valid (정상) bids, winner's bid rate
  and lower-limit rate (null without a winner), coefficient of variation of the valid amounts and relative distance
  (two lowest valid amounts' gap / spread of the other valid amounts; both null under three valid bids), bids lower
  than the winner's excluded for another reason than 정상 / 낙찰하한선 미달, whether two bids share a minute.
- `refs`: per business type and year, the 10th percentile of cv and the 90th of rd (B4, B5 thresholds).

Only derived numbers; no bidder identity leaves the private cache. tools/korea-label-checks.py reads this file.
"""
import argparse
import contextlib
import gzip
import json
import os
import sqlite3
import statistics
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea'
VALID = '정상'
LOSING = ('정상', '낙찰하한선 미달')
COLS = ['notice', 'ord', 'day', 'type', 'year', 'bids', 'valid', 'winner', 'winner_rate', 'lower_rate', 'cv', 'rd', 'dq_lower',
        'same_minute']


def number(v):
    try:
        return float(str(v).replace(',', ''))
    except (TypeError, ValueError):
        return None


def features(rows):
    """Features of one opening's rows (plan definitions)."""
    valid = sorted(a for a in (number(r.get('bidprcAmt')) for r in rows if r.get('dqlfctnRsn') == VALID) if a and a > 0)
    winners = [r for r in rows if r.get('sucsfYn') == 'Y']
    w = winners[0] if winners else None
    cv = rd = None
    if len(valid) >= 3:
        mean = statistics.fmean(valid)
        cv = statistics.pstdev(valid) / mean if mean else None
        spread = statistics.stdev(valid[1:])
        gap = valid[1] - valid[0]
        rd = gap / spread if spread else (0.0 if gap == 0 else float('inf'))
    w_amount = number(w.get('bidprcAmt')) if w else None
    dq_lower = None
    if w_amount:
        dq_lower = sum(1 for r in rows if (r.get('dqlfctnRsn') or '') not in LOSING and r.get('dqlfctnRsn')
                       and (number(r.get('bidprcAmt')) or float('inf')) < w_amount)
    stamps = [(r.get('bidprcDate'), r.get('bidprcTm')) for r in rows if r.get('bidprcDate') and r.get('bidprcTm')]
    return {'bids': len(rows), 'valid': len(valid), 'winner': w is not None, 'winner_rate': number(w.get('bidprcRt')) if w else None,
            'lower_rate': number(rows[0].get('sucsfLwstlmtRt')), 'cv': cv, 'rd': rd, 'dq_lower': dq_lower,
            'same_minute': len(stamps) != len(set(stamps))}


def read_day(path):
    groups = defaultdict(list)
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            groups[(r['bidNtceNo'], r.get('bidNtceOrd') or '000')].append(r)
    day = path.name[:10]
    out = []
    for (notice, ord_), rows in groups.items():
        f = features(rows)
        out.append((notice, ord_, day, rows[0].get('bsnsDivNm') or path.parent.name, int(day[:4]),
                    *(f[c] for c in COLS[5:])))
    return out


def percentile(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(q * len(values)))] if values else None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--bids', type=Path, default=BASE / 'bids/bids')
    p.add_argument('--out', type=Path, default=BASE / 'bid-features.sqlite')
    p.add_argument('--workers', type=int, default=os.cpu_count())
    args = p.parse_args(argv)
    files = sorted(args.bids.glob('*/*.jsonl.gz'))
    staged = args.out.with_suffix('.part')
    staged.unlink(missing_ok=True)
    db = sqlite3.connect(staged)
    db.execute(f'CREATE TABLE openings ({", ".join(COLS)}, PRIMARY KEY (notice, ord, day)) WITHOUT ROWID')
    db.execute('CREATE TABLE refs (type, year, cv_p10, rd_p90, openings, PRIMARY KEY (type, year))')
    cvs, rds = defaultdict(list), defaultdict(list)
    pool = Pool(args.workers) if args.workers > 1 else None
    with pool or contextlib.nullcontext():
        for i, rows in enumerate(pool.imap_unordered(read_day, files, chunksize=4) if pool else map(read_day, files), 1):
            db.executemany(f'INSERT OR REPLACE INTO openings VALUES ({",".join("?" * len(COLS))})', rows)
            for r in rows:
                cv, rd = r[COLS.index('cv')], r[COLS.index('rd')]
                if cv is not None:
                    cvs[(r[3], r[4])].append(cv)
                    rds[(r[3], r[4])].append(rd)
            if i % 200 == 0:
                print(f'{i}/{len(files)} day files', flush=True)
    db.executemany('INSERT INTO refs VALUES (?, ?, ?, ?, ?)',
                   [(t, y, percentile(cvs[(t, y)], 0.1), percentile(rds[(t, y)], 0.9), len(cvs[(t, y)])) for t, y in sorted(cvs)])
    db.commit()
    n = db.execute('SELECT count(*) FROM openings').fetchone()[0]
    db.close()
    staged.rename(args.out)
    print(f'{len(files)} day files, {n} openings, {len(cvs)} type-years -> {args.out}')


if __name__ == '__main__':
    main()
