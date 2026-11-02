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
SITE_CHECKS order (korea-label-checks.CHECKS up to B7, then K7 and B12, then SITE_EXTRA) (s signal, c clear, u unknown), then the number of
bids opened in its tender (empty when the opening was not found), for every contract (the full history stays local
for tuning; tools/build-korea-site.py publishes only its period). Private; reads only.
"""
import argparse
import heapq
import os
import sqlite3
import sys
import time
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load  # noqa: E402

ko = load('korea_checks', 'tools/korea-label-checks.py')
# The published letters: korea-label-checks.CHECKS up to B7, then its price slot (K7, B12, 2026-10-25), the order
# tools/build-korea-site.py expects. Other research checks (B11, N6/N7, A*, the other UA-* and BID-*) stay out.
# 2026-11-02 appended (old letter strings stay readable by position): exactly two bids and one valid bid (B2 split), and
# the checks the court-conviction labels rate (corruption index). Each gets a short site code in the header. B9 shared
# CEO and B10 rotation also earn corruption points but cannot be assessed in the published period: the bidders' CEO
# names stop in 2018 (Data Hub exports) and the bid history in 2019.
SITE_EXTRA = [('BC2', 'BID-COUNT 2'), ('BV1', 'BID-VALID only one valid of 2+'), ('B8', 'B8 exact floor hit'),
              ('C11', 'UA-C11 price increase')]
SITE_CHECKS = ko.CHECKS[:ko.CHECKS.index('B7 same-minute bids') + 1] + ko.PRICE_CHECKS + [k for _, k in SITE_EXTRA]
HEADER = (ko.CHECKS[:ko.CHECKS.index('B7 same-minute bids') + 1] + ko.PRICE_CHECKS
          + [k if k.split(' ')[0] == code else f'{code} {k}' for code, k in SITE_EXTRA])
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


def resume_point(part):
    """(offices already written, byte length of the part file through the last of them). Each office is followed by a
    line in <part>.done naming it and the part's length after it, so a killed or failed run resumes after the last
    complete office; a half-written office is cut off."""
    done = part.with_name(part.name + '.done')
    offices, length = set(), 0
    if part.exists() and done.exists():
        for line in done.read_text().splitlines():
            office, _, size = line.partition('\t')
            if size.isdigit():
                offices.add(office)
                length = int(size)
    return offices, length


def work(job):
    """One worker: its offices, one at a time, into its own part file; resumes after the last complete office."""
    db, attrib, part, buyers, first_year, bids_path = job
    bids = ko.Bids(bids_path) if bids_path else None
    con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    con.execute('ATTACH ? AS a', (f'file:{attrib}?mode=ro',))
    written, started = 0, time.time()
    finished, length = resume_point(part)
    if finished:
        print(f'{part.name}: resuming after {len(finished)} offices', flush=True)
    with open(part, 'a' if finished else 'w') as out, open(part.with_name(part.name + '.done'), 'a' if finished else 'w') as log:
        out.truncate(length)
        out.seek(length)
        for i, buyer in enumerate(buyers, 1):
            if buyer in finished:
                continue
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
                    # Bids opened in the tender, from the same opening the B checks read (empty when not found).
                    opening = bids.opening(c['notice'], c.get('notice_ord', ''), c.get('supplier')) if bids and c['notice'] and c['original'] else None
                    n = '' if opening is None or opening['bids'] is None else str(opening['bids'])
                    out.write(no + '\t' + ''.join(LETTER[result[k]['status']] for k in SITE_CHECKS) + '\t' + n + '\n')
                written += len(contracts)
            out.flush()
            log.write(f'{buyer}\t{out.tell()}\n')
            log.flush()
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
    p.add_argument('--bids', type=Path, default=ko.BASE / 'bid-features-2026-10-28.sqlite',
                   help='tools/korea-bid-features.py output; without it the B checks are unknown')
    args = p.parse_args(argv)
    bids_path = args.bids if args.bids.exists() else None
    if not bids_path:
        print(f'{args.bids} missing: bid-level checks unknown', flush=True)
    con = sqlite3.connect(f'file:{args.db}?mode=ro', uri=True)
    first_year = int(con.execute('SELECT min(signed) FROM versions').fetchone()[0][:4])
    # The attribution is kept next to the output until the run completes, so a resumed run skips it.
    attrib = args.out.with_name(args.out.name + '.attrib.sqlite')
    started = time.time()
    if attrib.exists():
        con.execute('ATTACH ? AS a', (f'file:{attrib}?mode=ro',))
        print('offices attribution reused', flush=True)
    else:
        staging = attrib.with_name(attrib.name + '.part')
        staging.unlink(missing_ok=True)
        con.execute('ATTACH ? AS a', (str(staging),))
        con.execute('CREATE TABLE a.attrib (buyer TEXT, cntrct_no TEXT, PRIMARY KEY (buyer, cntrct_no)) WITHOUT ROWID')
        con.execute(ATTRIBUTE)
        con.commit()
        con.execute('DETACH a')
        staging.rename(attrib)
        con.execute('ATTACH ? AS a', (f'file:{attrib}?mode=ro',))
        print(f'offices attributed in {time.time() - started:.0f} s', flush=True)
    sizes = con.execute('SELECT buyer, count(*) FROM a.attrib GROUP BY buyer ORDER BY buyer').fetchall()
    con.close()
    # Biggest offices first, each to the least-loaded worker, so the workers finish at about the same time.
    heap = [(0, i, []) for i in range(args.workers)]
    for buyer, n in sorted(sizes, key=lambda s: (-s[1], s[0])):  # fixed order: a resumed run gives each worker the same offices
        load_, i, buyers = heapq.heappop(heap)
        buyers.append(buyer)
        heapq.heappush(heap, (load_ + n, i, buyers))
    parts = [args.out.with_suffix(f'.part{i}') for i in range(args.workers)]
    logs = sorted(args.out.parent.glob(args.out.stem + '.part*.done'))
    if logs and len(logs) != args.workers:
        raise SystemExit(f'{len(logs)} resumable part files from an earlier run with another --workers: rerun with '
                         f'--workers {len(logs)}, or delete {args.out.stem}.part* to start over')
    jobs = [(args.db, attrib, parts[i], buyers, first_year, bids_path) for _, i, buyers in sorted(heap, key=lambda h: h[1])]
    print(f'{len(sizes)} offices, {sum(n for _, n in sizes)} contracts, {args.workers} workers', flush=True)
    if args.workers == 1:
        written = work(jobs[0])
    else:
        with Pool(args.workers) as pool:
            written = sum(pool.map(work, jobs, chunksize=1))
    staged = args.out.with_suffix('.part')
    with staged.open('w') as out:
        out.write('# ' + '\t'.join(['contract'] + HEADER + ['bids']) + '\n')
        for part in parts:
            with part.open() as f:
                for line in f:
                    out.write(line)
    staged.rename(args.out)
    for part in parts:
        part.unlink()
        part.with_name(part.name + '.done').unlink(missing_ok=True)
    attrib.unlink()
    print(f'{written} contracts with checks -> {args.out}')


if __name__ == '__main__':
    main()
