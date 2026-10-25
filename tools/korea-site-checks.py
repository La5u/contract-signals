#!/usr/bin/env python3
"""Korean checks for every contract, computed exactly as the calibration computes them.

Runs tools/korea-label-checks.py's contracts_from() and build_checks() one contracting office at a time over
~/.cache/contract-signals/korea/opnstd.sqlite, so the explorer's Korean checks and their points
(research/calibration/korea-collusion-results.md) cannot drift apart. A contract belongs to the office of its earliest
version, as in contracts_from() (not contracts.last_buyer_code: a contract that changed office would otherwise be
scored apart from the rest of its office's history). A first pass writes that attribution to a temporary indexed
table; the offices are shared out among --workers processes, each with its own read-only connection, and all of an
office's contracts are read together, so totals, concentration and the three-year first-supplier window are complete
(N5 is unknown in the data's first three years). Contracts whose original version is missing get unknown checks.

Writes ~/.cache/contract-signals/korea/site-checks.tsv: contract number, then one letter per check in
SITE_CHECKS order (korea-label-checks.CHECKS up to B7, then K7 and B12) (s signal, c clear, u unknown), for every contract (the full history stays local
for tuning; tools/build-korea-site.py publishes only its period). Private; reads only.
"""
import argparse
import heapq
import os
import sqlite3
import sys
import tempfile
import time
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load  # noqa: E402

ko = load('korea_checks', 'tools/korea-label-checks.py')
# The published letters: korea-label-checks.CHECKS up to B7, then its price slot (K7, B12, 2026-10-25), the order
# tools/build-korea-site.py expects. Research checks (B8-B11, N6/N7, A*, UA-*, BID-*) stay out until each is decided.
SITE_CHECKS = ko.CHECKS[:ko.CHECKS.index('B7 same-minute bids') + 1] + ko.PRICE_CHECKS
COLS = ['cntrct_no', 'ord', 'signed', 'method', 'amount', 'total_amount', 'business_type', 'buyer_code', 'demand_code',
        'supplier_bizrno', 'notice_no', 'notice_ord', 'legal_ref', 'reserve_price', 'term_type']
QUERY = (f'SELECT {", ".join("v." + c for c in COLS)} FROM a.attrib t JOIN versions v ON v.cntrct_no = t.cntrct_no '
         'WHERE t.buyer = ?')
# Each contract's office: the buyer code of its earliest version (ties: the smallest code), as in contracts_from().
ATTRIBUTE = '''
INSERT INTO a.attrib
SELECT min(v.buyer_code), v.cntrct_no FROM versions v
JOIN (SELECT cntrct_no, min(coalesce(ord, 0)) AS o FROM versions GROUP BY cntrct_no) m
  ON m.cntrct_no = v.cntrct_no AND coalesce(v.ord, 0) = m.o
GROUP BY v.cntrct_no HAVING min(v.buyer_code) IS NOT NULL
'''
LETTER = {'signal': 's', 'clear': 'c', 'unknown': 'u'}


def work(job):
    """One worker: its offices, one at a time, into its own part file."""
    db, attrib, part, buyers, first_year, bids_path = job
    bids = ko.Bids(bids_path) if bids_path else None
    con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    con.execute('ATTACH ? AS a', (f'file:{attrib}?mode=ro',))
    written, started = 0, time.time()
    with open(part, 'w') as out:
        for i, buyer in enumerate(buyers, 1):
            versions = defaultdict(list)
            for rec in con.execute(QUERY, (buyer,)):
                versions[rec[0]].append(dict(zip(COLS, rec)))
            contracts = ko.contracts_from(versions, 'buyer_code')
            stray = [no for no, c in contracts.items() if c['buyer'] != buyer]
            if stray:
                raise SystemExit(f'office {buyer}: {len(stray)} contracts attributed elsewhere, e.g. {stray[0]}')
            if contracts:
                checks = ko.build_checks(contracts, first_year, bids)
                for no, c in contracts.items():
                    result = checks(c)
                    out.write(no + '\t' + ''.join(LETTER[result[k]['status']] for k in SITE_CHECKS) + '\n')
                written += len(contracts)
            if i % 1000 == 0:
                print(f'{part.name}: {i}/{len(buyers)} offices, {written} contracts, {time.time() - started:.0f} s', flush=True)
    con.close()
    print(f'{part.name}: done, {written} contracts, {time.time() - started:.0f} s', flush=True)
    return written


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--db', type=Path, default=ko.BASE / 'opnstd.sqlite')
    p.add_argument('--out', type=Path, default=ko.BASE / 'site-checks.tsv')
    p.add_argument('--workers', type=int, default=os.cpu_count())
    p.add_argument('--bids', type=Path, default=ko.BASE / 'bid-features.sqlite',
                   help='tools/korea-bid-features.py output; without it the B checks are unknown')
    args = p.parse_args(argv)
    bids_path = args.bids if args.bids.exists() else None
    if not bids_path:
        print(f'{args.bids} missing: bid-level checks unknown', flush=True)
    con = sqlite3.connect(f'file:{args.db}?mode=ro', uri=True)
    first_year = int(con.execute('SELECT min(signed) FROM versions').fetchone()[0][:4])
    tmp = tempfile.TemporaryDirectory(dir=args.out.parent)
    attrib = Path(tmp.name) / 'attrib.sqlite'
    con.execute('ATTACH ? AS a', (str(attrib),))
    con.execute('CREATE TABLE a.attrib (buyer TEXT, cntrct_no TEXT, PRIMARY KEY (buyer, cntrct_no)) WITHOUT ROWID')
    started = time.time()
    con.execute(ATTRIBUTE)
    con.commit()
    sizes = con.execute('SELECT buyer, count(*) FROM a.attrib GROUP BY buyer').fetchall()
    con.close()
    print(f'offices attributed in {time.time() - started:.0f} s', flush=True)
    # Biggest offices first, each to the least-loaded worker, so the workers finish at about the same time.
    heap = [(0, i, []) for i in range(args.workers)]
    for buyer, n in sorted(sizes, key=lambda s: -s[1]):
        load_, i, buyers = heapq.heappop(heap)
        buyers.append(buyer)
        heapq.heappush(heap, (load_ + n, i, buyers))
    parts = [args.out.with_suffix(f'.part{i}') for i in range(args.workers)]
    jobs = [(args.db, attrib, parts[i], buyers, first_year, bids_path) for _, i, buyers in sorted(heap, key=lambda h: h[1])]
    print(f'{len(sizes)} offices, {sum(n for _, n in sizes)} contracts, {args.workers} workers', flush=True)
    if args.workers == 1:
        written = work(jobs[0])
    else:
        with Pool(args.workers) as pool:
            written = sum(pool.map(work, jobs, chunksize=1))
    staged = args.out.with_suffix('.part')
    with staged.open('w') as out:
        out.write('# ' + '\t'.join(['contract'] + SITE_CHECKS) + '\n')
        for part in parts:
            with part.open() as f:
                for line in f:
                    out.write(line)
            part.unlink()
    staged.rename(args.out)
    tmp.cleanup()
    print(f'{written} contracts with checks -> {args.out}')


if __name__ == '__main__':
    main()
