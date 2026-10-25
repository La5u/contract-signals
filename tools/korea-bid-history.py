#!/usr/bin/env python3
"""Research only: compact rolling B10/B11 history; definitions fixed in the plan.

Process opening-date quarters, retaining only [block start - 365, block end + 365]
(inclusive; block end is the last day). Hub filenames are NOTICE weeks: select
weeks intersecting [window start - 120, window end]; API filenames are opening
days. Filter streamed rows by opening date. Each file is normally read twice near
an advancing window edge, sometimes three times for long notice/opening delays.
Only gzip files successfully read to EOF contribute coverage. Coverage is unchanged:
every one of the target's 731 days needs all four API types or every Hub Monday
covering notice dates from day - 60 through day. Empty/weekend days count too.

Integer keys, ordinal dates, demand lookup IDs and integer thousandth rates keep
bids compact. A packed integer fractional tail preserves round-the-DIFFERENCE
semantics when source quotes have more than three decimals. Nonnumeric notice and
bidder IDs use negative IDs in a small lookup (numeric IDs remain direct integers).
Bids/openings are scratch history; checks and blocks persist after pruning.
Blocks become done only after their WHOLE window is covered and computed. Pending
blocks retain per-opening unknowns and are revisited when relevant files arrive.
Unchanged blocks, including pending blocks, need no reread. New relevant files
invalidate even completed blocks. Changed/deleted sources still require --rebuild.

Commits are bounded by 5,000 bids, 100 opening summaries, or 1,000 results. A file's
loaded range is committed only after EOF and stat validation; retries upsert partial
imports. checks_ready gates readers across interrupted runs. Block completion commits
only after all results have been written. DELETE journals avoid a large WAL; freed pages are reused without
VACUUM (which would double peak space). The default hard main-database ceiling is
4 GB, leaving about 1 GB for bounded rollback journals under a 5 GB disk budget.
Exceeding the ceiling fails safely: reduce --block-months (requires --rebuild) or
supply more disk. The ceiling covers scratch, results, indexes and lookup tables.

Use a separate --out for --start/--end/--limit smoke runs: these options restrict the
source inventory, never confer coverage from unimported files. Progress reports
row counts, file reads, timings and peak SQLite + journal bytes, never label rates.
No network, public artifacts, bidder pair expansion, or label reports are involved.
"""
import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import os
import sqlite3
import multiprocessing
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal, InvalidOperation, ROUND_FLOOR, ROUND_HALF_UP
from itertools import combinations
from pathlib import Path

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea'
BUSINESS = ('goods', 'services', 'works', 'foreign')
SCHEMA = '2'
# Rows and openings per transaction. Each commit rewrites every touched index page (and its journal copy), so
# small batches multiply disk writes: 5,000/100 wrote 418 GB in 39 min while pruning a 3 GB file (2026-10-23).
BATCH = 1_000_000
OPENINGS_BATCH = 20_000
HUB_DELAY = 120
DEFAULT_MAX_BYTES = 4_000_000_000


def day(value):
    text = str(value or '').strip()
    try:
        return dt.date.fromisoformat(text[:10] if '-' in text else text[:8]).toordinal()
    except ValueError:
        return None


def rate(value):
    """Integer thousandths plus a lossless fractional tail (1-prefix decimal digits)."""
    try:
        n = Decimal(str(value).strip().replace(',', '')) * 1000
        if not n.is_finite():
            return None, None
        whole = int(n.to_integral_value(rounding=ROUND_FLOOR))
        fraction = n - whole
        tail = int('1' + format(fraction, 'f').split('.')[1].rstrip('0')) if fraction else None
        if abs(whole) >= 2**63 or (tail is not None and tail >= 2**63):
            raise ValueError('Quote exceeds lossless integer storage precision')
        return whole, tail
    except InvalidOperation:
        return None, None


def quote_gap(a, b, at=None, bt=None):
    if a is None or b is None:
        return None
    if at is None and bt is None:
        return abs(a - b)
    def exact(whole, tail):
        return Decimal(whole) + (Decimal('0.' + str(tail)[1:]) if tail else 0)
    return int(abs(exact(a, at) - exact(b, bt)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


class Codes:
    """Only exceptional alphanumeric identities and demand codes need dictionaries."""
    def __init__(self, db):
        self.db = db
        self.ids = {(k, v): i for k, v, i in db.execute('SELECT kind, value, id FROM identities')}
        self.demands = {v: i for i, v in db.execute('SELECT id, code FROM demands')}

    def identity(self, kind, value):
        if value.isascii() and value.isdigit() and int(value) < 2**63:
            return int(value)
        key = kind, value
        if key not in self.ids:
            ident = -len(self.ids) - 1
            self.db.execute('INSERT INTO identities VALUES (?, ?, ?)', (*key, ident))
            self.ids[key] = ident
        return self.ids[key]

    def demand(self, code):
        if not code:
            return None
        if code not in self.demands:
            ident = len(self.demands) + 1
            self.db.execute('INSERT INTO demands VALUES (?, ?)', (ident, code))
            self.demands[code] = ident
        return self.demands[code]


def numeric_id(value):
    """The integer itself when Codes.identity would return it; otherwise the text (mapped in the main process)."""
    return int(value) if value.isascii() and value.isdigit() and int(value) < 2**63 else value


def fields(r, hub):
    """One source row as plain values; runs in the parsing workers, so no database or Codes access."""
    keys = (('입찰공고번호', '입찰공고차수', '개찰일자', '수요기관코드', '업체사업자등록번호', '투찰율', '낙찰자선정여부') if hub else
            ('bidNtceNo', 'bidNtceOrd', 'opengDate', 'dmndInsttCd', 'bidprcCorpBizrno', 'bidprcRt', 'sucsfYn'))
    notice, ord_, opened, demand, bizno, quoted, won = (str(r.get(k) or '').strip() for k in keys)
    opened = day(opened)
    if not notice or not bizno or opened is None or not (ord_ or '0').isdigit():
        return None  # one 2010 API row has bidNtceOrd '0-2'; it cannot join an integer order, so B10/B11 stay unknown
    quoted, tail = rate(quoted)
    return (numeric_id(notice), int(ord_ or '0'), opened, demand, numeric_id(bizno), quoted, tail, int(won == 'Y'),
            int(not hub))


def encode(item, codes):
    notice, ord_, opened, demand, bizno, *rest = item
    return (notice if isinstance(notice, int) else codes.identity('notice', notice), ord_, opened, codes.demand(demand),
            bizno if isinstance(bizno, int) else codes.identity('bizno', bizno), *rest)


def record(r, hub, codes):
    item = fields(r, hub)
    return None if item is None else encode(item, codes)


def parse_rows(path, kind, lo, hi, old=None):
    """Rows of one source file opened in [lo, hi] and outside the range already loaded, as `fields` tuples."""
    out = []
    with gzip.open(path, 'rt', encoding='utf-8-sig', newline='') as f:
        rows = csv.DictReader(f, delimiter='\t') if kind == 'hub' else (json.loads(line) for line in f)
        date_key = '개찰일자' if kind == 'hub' else 'opengDate'
        for r in rows:
            opened = day(r.get(date_key))
            if opened is None or not lo <= opened <= hi or (old and old[0] <= opened <= old[1]):
                continue
            item = fields(r, kind == 'hub')
            if item is not None:
                out.append(item)
    return out


def parsed(jobs, pool, ahead):
    """Yield (job, rows) in job order; at most `ahead` files are parsed but not yet written (memory bound).
    Without a pool, rows is None and import_file parses in this process."""
    if pool is None:
        for job in jobs:
            yield job, None
        return
    pending = deque()
    for job in jobs:
        path, kind, _, a, b, old = job
        pending.append((job, pool.submit(parse_rows, path, kind, a, b, old)))
        if len(pending) > ahead:
            first, future = pending.popleft()
            yield first, future.result()
    while pending:
        first, future = pending.popleft()
        yield first, future.result()


def inventory(args):
    files = [(p, 'hub', p.name[:10]) for p in sorted(args.datahub.glob('????-??-??.csv.gz'))]
    files += [(p, kind, p.name[:10]) for kind in BUSINESS for p in sorted((args.bids / kind).glob('????-??-??.jsonl.gz'))]
    files = [(p.resolve(), kind, stamp) for p, kind, stamp in files
             if (not args.start or stamp >= args.start) and (not args.end or stamp < args.end)]
    return files[:args.limit] if args.limit is not None else files


def connect(path, max_bytes=DEFAULT_MAX_BYTES):
    Path(path).touch(mode=0o600, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute('PRAGMA journal_mode=DELETE')
    # No fsync per commit: with it, every batch forced its rewritten index pages to disk (~50x the data size,
    # 10 GB/min on 2026-10-23). A killed process still rolls back from the journal; an OS crash or power loss can
    # corrupt this file, which --rebuild recreates from the downloads.
    db.execute('PRAGMA synchronous=OFF')
    db.execute('PRAGMA temp_store=MEMORY')  # only bounded groups/single-opening queries sort
    db.execute('PRAGMA cache_size=-1572864')  # 1.5 GiB: dirty index pages coalesce within a batch
    pages = max_bytes // db.execute('PRAGMA page_size').fetchone()[0]
    if db.execute('PRAGMA page_count').fetchone()[0] > pages:
        db.close()
        raise SystemExit('Existing database exceeds --max-sqlite-bytes')
    db.execute(f'PRAGMA max_page_count={pages}')
    db.create_function('quote_gap', 4, lambda a, at, b, bt: quote_gap(a, b, at, bt), deterministic=True)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT) WITHOUT ROWID;
        CREATE TABLE IF NOT EXISTS sources (
            path TEXT PRIMARY KEY, kind TEXT, day INTEGER, size INTEGER, mtime INTEGER) WITHOUT ROWID;
        CREATE TABLE IF NOT EXISTS loads (path TEXT PRIMARY KEY, lo INTEGER, hi INTEGER) WITHOUT ROWID;
        CREATE TABLE IF NOT EXISTS identities (
            kind TEXT, value TEXT, id INTEGER, PRIMARY KEY (kind, value)) WITHOUT ROWID;
        CREATE TABLE IF NOT EXISTS demands (id INTEGER PRIMARY KEY, code TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS bids (
            notice INTEGER, ord INTEGER, opening_date INTEGER, demand_code INTEGER, bizno INTEGER,
            rate INTEGER, rate_tail INTEGER, won INTEGER, priority INTEGER,
            PRIMARY KEY (notice, ord, bizno)) WITHOUT ROWID;
        CREATE INDEX IF NOT EXISTS bids_bidder ON bids (bizno, opening_date);
        CREATE INDEX IF NOT EXISTS bids_winner ON bids (notice, ord, bizno) WHERE won = 1;
        CREATE TABLE IF NOT EXISTS dirty (notice INTEGER, ord INTEGER, PRIMARY KEY (notice, ord)) WITHOUT ROWID;
        CREATE TEMP TABLE work (notice INTEGER, ord INTEGER, PRIMARY KEY (notice, ord)) WITHOUT ROWID;
        CREATE TABLE IF NOT EXISTS openings (
            notice INTEGER, ord INTEGER, opening_date INTEGER, demand_code INTEGER,
            bids INTEGER, winners INTEGER, winner INTEGER, PRIMARY KEY (notice, ord)) WITHOUT ROWID;
        CREATE INDEX IF NOT EXISTS openings_day ON openings (opening_date);
        CREATE TABLE IF NOT EXISTS checks (
            notice INTEGER, ord INTEGER, b10 INTEGER, b11 INTEGER, PRIMARY KEY (notice, ord)) WITHOUT ROWID;
        CREATE TABLE IF NOT EXISTS blocks (
            start INTEGER PRIMARY KEY, end INTEGER, signature TEXT, status TEXT) WITHOUT ROWID;
    ''')
    return db


UPSERT = '''INSERT INTO bids VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT (notice, ord, bizno) DO UPDATE SET
    opening_date = CASE WHEN excluded.priority >= bids.priority THEN excluded.opening_date ELSE bids.opening_date END,
    demand_code = CASE WHEN excluded.priority >= bids.priority THEN COALESCE(excluded.demand_code, bids.demand_code)
                      ELSE COALESCE(bids.demand_code, excluded.demand_code) END,
    rate = CASE WHEN excluded.priority >= bids.priority THEN COALESCE(excluded.rate, bids.rate)
                ELSE COALESCE(bids.rate, excluded.rate) END,
    rate_tail = CASE WHEN excluded.rate IS NULL THEN bids.rate_tail
                    WHEN excluded.priority >= bids.priority OR bids.rate IS NULL THEN excluded.rate_tail ELSE bids.rate_tail END,
    won = MAX(bids.won, excluded.won), priority = MAX(bids.priority, excluded.priority)'''


COMMITTED_AT = {}  # connection id -> total_changes at its last commit_due commit


def commit_due(db):
    """Commit once BATCH changes are pending, across source files: one commit per small day file made every
    commit rewrite the scattered bidder-index pages (~17x the data size). Load markers commit with their rows."""
    if db.total_changes - COMMITTED_AT.get(id(db), 0) >= BATCH:
        db.commit()
        COMMITTED_AT[id(db)] = db.total_changes


class Usage:
    def __init__(self, db, out):
        self.db, self.out = db, out
        self.peak = self.sqlite_peak = self.rows_peak = 0

    def sample(self):
        size = self.db.execute('PRAGMA page_count').fetchone()[0] * self.db.execute('PRAGMA page_size').fetchone()[0]
        self.sqlite_peak = max(self.sqlite_peak, size)
        self.peak = max(self.peak, size + sum(p.stat().st_size for p in
                        (Path(str(self.out) + suffix) for suffix in ('-journal', '-wal', '-shm')) if p.exists()))


def import_file(db, codes, path, kind, stamp, stat, lo, hi, old=None, usage=None, rows=None):
    count, batch = 0, []
    def write():
        if not batch:
            return
        db.executemany(UPSERT, batch)
        db.executemany('INSERT OR IGNORE INTO dirty VALUES (?, ?)', {(r[0], r[1]) for r in batch})
        if usage:
            usage.sample()
        commit_due(db)
        batch.clear()
    # The load marker is deliberately separate from batch commits: a truncated gzip
    # leaves no coverage/marker and is fully reread after restart.
    for item in parse_rows(path, kind, lo, hi, old) if rows is None else rows:
        batch.append(encode(item, codes))
        count += 1
        if len(batch) == BATCH:
            write()
    write()
    now = path.stat()
    if (now.st_size, now.st_mtime_ns) != (stat.st_size, stat.st_mtime_ns):
        raise RuntimeError(f'File changed during import: {path}; use --rebuild after download completes')
    db.execute('INSERT OR REPLACE INTO loads VALUES (?, ?, ?)', (str(path), lo, hi))
    db.execute('INSERT OR REPLACE INTO sources VALUES (?, ?, ?, ?, ?)',
               (str(path), kind, day(stamp), stat.st_size, stat.st_mtime_ns))
    commit_due(db)
    return count


def refresh_openings(db, usage=None):
    while db.execute('SELECT 1 FROM dirty LIMIT 1').fetchone():
        with db:
            db.execute('DELETE FROM work')
            db.execute('INSERT INTO work SELECT * FROM dirty LIMIT ?', (OPENINGS_BATCH,))
            # Lexical demand precedence must use codes, not arbitrary dictionary IDs.
            db.execute('''INSERT OR REPLACE INTO openings
                SELECT notice, ord, opened, d.id, bids, winners, winner FROM (
                SELECT w.notice, w.ord,
                       COALESCE(MAX(CASE WHEN b.priority = 1 THEN b.opening_date END), MAX(b.opening_date)) AS opened,
                       COALESCE(MAX(CASE WHEN b.priority = 1 THEN d.code END), MAX(d.code)) AS code,
                       COUNT(*) AS bids, SUM(b.won) AS winners, MAX(CASE WHEN b.won THEN b.bizno END) AS winner
                FROM work w CROSS JOIN bids b USING (notice, ord)
                LEFT JOIN demands d ON d.id = b.demand_code GROUP BY w.notice, w.ord
                ) summary LEFT JOIN demands d USING (code)''')
            if usage:
                usage.sample()
        # Large openings must not turn metadata normalization into an unbounded
        # rollback journal. The dirty marker survives every intermediate commit.
        while True:
            with db:
                changed = db.execute('''UPDATE bids AS b SET (opening_date, demand_code) =
                    (SELECT o.opening_date, o.demand_code FROM openings o WHERE o.notice = b.notice AND o.ord = b.ord)
                    WHERE (b.notice, b.ord, b.bizno) IN (
                        SELECT x.notice, x.ord, x.bizno FROM work w CROSS JOIN bids x USING (notice, ord)
                        JOIN openings o USING (notice, ord)
                        WHERE (x.opening_date, x.demand_code) IS NOT (o.opening_date, o.demand_code) LIMIT ?)''',
                                     (BATCH,)).rowcount
                if usage:
                    usage.sample()
            if changed < BATCH:
                break
        with db:
            db.execute('DELETE FROM dirty WHERE (notice, ord) IN (SELECT notice, ord FROM work)')
            if usage:
                usage.sample()


def complete_days(files):
    """Centers whose full inclusive +/-365-day window is covered by imported files."""
    weeks, api = set(), {}
    for _, kind, stamp in files:
        d = dt.date.fromisoformat(stamp)
        if kind == 'hub':
            if d.weekday() != 0:
                raise ValueError(f'Data Hub filename must be a Monday: {stamp}')
            weeks.add(d)
        else:
            api.setdefault(d, set()).add(kind)
    if not weeks and not api:
        return set()
    lo = min(weeks | api.keys())
    hi = max(weeks | api.keys()) + dt.timedelta(days=6)
    complete, streak = set(), 0
    d = lo
    while d <= hi:
        first = d - dt.timedelta(days=60)
        monday = first - dt.timedelta(days=first.weekday())
        last = d - dt.timedelta(days=d.weekday())
        hub = True
        while monday <= last:
            if monday not in weeks:
                hub = False
                break
            monday += dt.timedelta(days=7)
        if len(api.get(d, ())) == 4 or hub:
            streak += 1
        else:
            streak = 0
        if streak >= 731:
            complete.add((d - dt.timedelta(days=365)).toordinal())
        d += dt.timedelta(days=1)
    return complete
def rotation(db, o, lo, hi):
    notice, ord_, _, demand, _, winners, winner = o
    if not demand or winners != 1:
        return None
    # Only a peer who won another common opening can qualify. This avoids expanding
    # all pairs at large openings. Other common openings may have ANY winner.
    peers = db.execute('''SELECT DISTINCT f.bizno FROM bids w INDEXED BY bids_bidder
        JOIN bids f INDEXED BY bids_winner ON f.notice = w.notice AND f.ord = w.ord AND f.won = 1
        JOIN bids here ON here.notice = ? AND here.ord = ? AND here.bizno = f.bizno
        WHERE w.bizno = ? AND w.demand_code = ? AND w.opening_date BETWEEN ? AND ?
          AND (w.notice != ? OR w.ord != ?) AND f.bizno != ?''',
                       (notice, ord_, winner, demand, lo, hi, notice, ord_, winner))
    for (peer,) in peers:
        count = db.execute('''SELECT COUNT(*) FROM (
            SELECT 1 FROM bids w INDEXED BY bids_bidder
            JOIN bids f ON f.notice = w.notice AND f.ord = w.ord AND f.bizno = ?
            WHERE w.bizno = ? AND w.demand_code = ? AND w.opening_date BETWEEN ? AND ?
              AND (w.notice != ? OR w.ord != ?) LIMIT 3)''', (peer, winner, demand, lo, hi, notice, ord_)).fetchone()[0]
        if count == 3:
            return 1
    return 0


def repeated_quotes(db, o, lo, hi):
    notice, ord_, _, _, size, _, _ = o
    if not 2 <= size <= 20:
        return 0
    bidders = db.execute('SELECT bizno, rate, rate_tail FROM bids WHERE notice = ? AND ord = ? ORDER BY bizno', (notice, ord_)).fetchall()
    unknown = False
    for (a, ar, at), (b, br, bt) in combinations(bidders, 2):
        gap = quote_gap(ar, br, at, bt)
        if gap == 0:
            continue
        if gap is None:
            # Missing input at the target stays unknown unless another pair proves
            # the signal, as with other checks' missing-input handling.
            unknown = True
            continue
        # Missing historical rates matter only if they could supply enough repeats.
        # At most two exact matches or two missing comparisons need to be read.
        params = (b, a, lo, hi, notice, ord_)
        common = '''FROM bids a INDEXED BY bids_bidder
            JOIN bids b ON b.notice = a.notice AND b.ord = a.ord AND b.bizno = ?
            WHERE a.bizno = ? AND a.opening_date BETWEEN ? AND ?
              AND (a.notice != ? OR a.ord != ?)'''
        exact = db.execute('SELECT COUNT(*) FROM (SELECT 1 ' + common + ''' AND
            CASE WHEN a.rate_tail IS NULL AND b.rate_tail IS NULL THEN ABS(a.rate - b.rate)
                 ELSE quote_gap(a.rate, a.rate_tail, b.rate, b.rate_tail) END = ? LIMIT 2)''',
                           params + (gap,)).fetchone()[0]
        if exact == 2:
            return 1
        missing = db.execute('SELECT COUNT(*) FROM (SELECT 1 ' + common +
                             ' AND (a.rate IS NULL OR b.rate IS NULL) LIMIT 2)', params).fetchone()[0]
        if exact + missing >= 2:
            unknown = True
    return None if unknown else 0



def prune(db, lo, hi, usage=None):
    """Delete in small transactions; free pages remain reusable in this same file."""
    while True:
        with db:
            db.execute('DELETE FROM work')
            db.execute('INSERT INTO work SELECT notice, ord FROM openings WHERE opening_date < ? LIMIT ?', (lo, OPENINGS_BATCH))
            if not db.execute('SELECT 1 FROM work LIMIT 1').fetchone():
                db.execute('INSERT INTO work SELECT notice, ord FROM openings WHERE opening_date > ? LIMIT ?', (hi, OPENINGS_BATCH))
        if not db.execute('SELECT 1 FROM work LIMIT 1').fetchone():
            break
        while True:
            with db:
                n = db.execute('''DELETE FROM bids WHERE (notice, ord, bizno) IN (
                    SELECT b.notice, b.ord, b.bizno FROM work w CROSS JOIN bids b USING (notice, ord) LIMIT ?)''',
                               (BATCH,)).rowcount
                if usage:
                    usage.sample()
            if n < BATCH:
                break
        with db:
            db.execute('DELETE FROM openings WHERE (notice, ord) IN (SELECT notice, ord FROM work)')
    with db:
        db.execute('UPDATE loads SET lo = MAX(lo, ?), hi = MIN(hi, ?)', (lo, hi))
        db.execute('DELETE FROM loads WHERE lo > hi')


def blocks(files, months):
    if not files:
        return
    first = dt.date.fromordinal(min(day(s) for _, _, s in files))
    last = max(day(s) + (HUB_DELAY + 6 if k == 'hub' else 0) for _, k, s in files)
    start = dt.date(first.year, ((first.month - 1) // months) * months + 1, 1)
    while start.toordinal() <= last:
        month = start.year * 12 + start.month - 1 + months
        end = dt.date(month // 12, month % 12 + 1, 1)
        yield start.toordinal(), end.toordinal()  # exclusive block end
        start = end


def candidates(files, lo, hi):
    return [(p, k, s) for p, k, s in files
            if day(s) <= hi and day(s) + (HUB_DELAY + 6 if k == 'hub' else 0) >= lo]


READER = None  # read-only connection of a worker process (open_reader)
CHECK_CHUNK = 2000


def open_reader(path):
    global READER
    READER = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    READER.execute('PRAGMA cache_size=-262144')
    READER.create_function('quote_gap', 4, lambda a, at, b, bt: quote_gap(a, b, at, bt), deterministic=True)


def check_targets(targets, complete, db=None):
    db = db or READER
    out = []
    for o in targets:
        b10 = b11 = None
        if o[2] in complete:
            b10 = rotation(db, o, o[2] - 365, o[2] + 365)
            b11 = repeated_quotes(db, o, o[2] - 365, o[2] + 365)
        out.append((o[0], o[1], b10, b11))
    return out


def refresh_checks(db, start, end, complete, usage=None, pool=None):
    """Write only the target block; per-target 731-day coverage is unchanged. With a pool, workers read the
    committed database and the results are written only after all of them are computed (no writer meanwhile)."""
    targets = db.execute('SELECT * FROM openings WHERE opening_date >= ? AND opening_date < ? ORDER BY opening_date',
                         (start, end)).fetchall()
    chunks = [targets[i:i + CHECK_CHUNK] for i in range(0, len(targets), CHECK_CHUNK)]
    days = frozenset(d for d in complete if start - 1 <= d <= end)
    results = (pool.map(check_targets, chunks, [days] * len(chunks)) if pool
               else (check_targets(c, days, db) for c in chunks))
    count = 0
    for rows in results:
        if not pool:
            with db:
                db.executemany('INSERT OR REPLACE INTO checks VALUES (?, ?, ?, ?)', rows)
        else:
            db.executemany('INSERT OR REPLACE INTO checks VALUES (?, ?, ?, ?)', rows)
        before, count = count, count + len(rows)
        if usage:
            usage.sample()
        if count // 10000 > before // 10000:
            print(f'  {count // 10000 * 10000} target openings computed', flush=True)
    db.commit()
    return count


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--datahub', type=Path, default=BASE / 'datahub')
    p.add_argument('--bids', type=Path, default=BASE / 'bids/bids')
    p.add_argument('--out', type=Path, default=BASE / 'bid-history.sqlite')
    p.add_argument('--start', type=dt.date.fromisoformat, help='source filename date, inclusive')
    p.add_argument('--end', type=dt.date.fromisoformat, help='source filename date, exclusive')
    p.add_argument('--limit', type=int, help='first N source files (Hub first); use a separate --out for smoke runs')
    p.add_argument('--block-months', type=int, choices=(1, 3), default=3)
    p.add_argument('--max-sqlite-bytes', type=int, default=DEFAULT_MAX_BYTES,
                   help='hard main-database limit; default 4 GB leaves journal headroom below 5 GB')
    p.add_argument('--rebuild', action='store_true', help='discard the existing output and import from scratch')
    p.add_argument('--workers', type=int, default=4,
                   help='processes parsing source files while the main process writes (0: parse in-process)')
    args = p.parse_args(argv)
    if args.limit is not None and args.limit < 0:
        p.error('--limit must be nonnegative')
    if args.start and args.end and args.start >= args.end:
        p.error('--start must precede --end')
    if args.max_sqlite_bytes < 1_000_000:
        p.error('--max-sqlite-bytes must be at least 1000000')
    args.start = args.start.isoformat() if args.start else None
    args.end = args.end.isoformat() if args.end else None
    files = inventory(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.rebuild:
        for suffix in ('', '-wal', '-shm', '-journal'):
            Path(str(args.out) + suffix).unlink(missing_ok=True)
    db = connect(args.out, args.max_sqlite_bytes)
    usage = Usage(db, args.out)
    # fork: workers inherit the loaded module, so this also works when the tool is imported from a file path
    pool = (ProcessPoolExecutor(args.workers, mp_context=multiprocessing.get_context('fork'),
                                initializer=open_reader, initargs=(str(args.out),))
            if args.workers > 0 else None)
    try:
        scope = json.dumps([SCHEMA, str(args.datahub.resolve()), str(args.bids.resolve()),
                            args.start, args.end, args.limit, args.block_months])
        previous = db.execute("SELECT value FROM meta WHERE key = 'scope'").fetchone()
        if previous and previous[0] != scope:
            raise SystemExit('Input scope changed; use a separate --out or --rebuild')
        stats = {str(path): path.stat() for path, _, _ in files}
        known = {r[0]: (r[1], r[2]) for r in db.execute('SELECT path, size, mtime FROM sources')}
        if any(path not in stats or (stats[path].st_size, stats[path].st_mtime_ns) != signature
               for path, signature in known.items()):
            raise SystemExit('An imported source changed or disappeared; rerun with --rebuild')
        with db:
            db.execute("INSERT OR IGNORE INTO meta VALUES ('scope', ?)", (scope,))
            db.execute("INSERT OR REPLACE INTO meta VALUES ('checks_ready', '0')")
        codes = Codes(db)
        started, reads, total, refreshed, skipped = time.monotonic(), 0, 0, 0, 0
        refresh_openings(db, usage)  # finish interrupted scratch normalization before pruning
        for start, end in blocks(files, args.block_months):
            lo, hi = start - 365, end - 1 + 365
            selected = candidates(files, lo, hi)
            signature = hashlib.sha256(json.dumps([(str(f), k, s, stats[str(f)].st_size,
                        stats[str(f)].st_mtime_ns) for f, k, s in selected]).encode()).hexdigest()
            previous = db.execute('SELECT signature FROM blocks WHERE start = ?', (start,)).fetchone()
            if previous and previous[0] == signature:
                skipped += 1
                continue
            prune(db, lo, hi, usage)
            print(f'block {dt.date.fromordinal(start)}..{dt.date.fromordinal(end - 1)}, '
                  f'window {dt.date.fromordinal(lo)}..{dt.date.fromordinal(hi)}', flush=True)
            jobs = []
            for path, kind, stamp in selected:
                a = max(lo, day(stamp))
                b = min(hi, day(stamp) + (HUB_DELAY + 6 if kind == 'hub' else 0))
                old = db.execute('SELECT lo, hi FROM loads WHERE path = ?', (str(path),)).fetchone()
                if not (old and old[0] <= a and old[1] >= b):
                    jobs.append((path, kind, stamp, a, b, old))
            tick = time.monotonic()
            for (path, kind, stamp, a, b, old), rows in parsed(jobs, pool, args.workers):
                # Register signatures before batch commits, even if EOF later fails.
                stat = stats[str(path)]
                db.execute('INSERT OR REPLACE INTO sources VALUES (?, ?, ?, ?, ?)',
                           (str(path), kind, day(stamp), stat.st_size, stat.st_mtime_ns))
                n = import_file(db, codes, path, kind, stamp, stat, a, b, old, usage, rows)
                reads += 1
                total += n
                elapsed, tick = time.monotonic() - tick, time.monotonic()
                print(f'  {kind}/{path.name}: {n} rows in {elapsed:.1f} s '
                      f'({n / max(elapsed, .001):.0f} rows/s)', flush=True)
            refresh_openings(db, usage)
            # Metadata corrections can move an opening across a window boundary.
            prune(db, lo, hi, usage)
            complete = complete_days(selected)
            count = refresh_checks(db, start, end, complete, usage, pool)
            status = 'done' if all(d in complete for d in range(start, end)) else 'pending'
            with db:
                db.execute('INSERT OR REPLACE INTO blocks VALUES (?, ?, ?, ?)', (start, end, signature, status))
                usage.sample()
            refreshed += count
            rows = db.execute('SELECT COUNT(*) FROM bids').fetchone()[0]
            usage.rows_peak = max(usage.rows_peak, rows)
            print(f'  {status}: {count} targets, {rows} retained bids; '
                  f'peak sqlite {usage.sqlite_peak:,} bytes, with journal {usage.peak:,}', flush=True)
        with db:
            db.execute("INSERT OR REPLACE INTO meta VALUES ('checks_ready', '1')")
            usage.sample()
        print(f'{reads} file reads, {total} rows imported; {refreshed} openings computed, {skipped} unchanged blocks; '
              f'{time.monotonic() - started:.1f} s; peak sqlite {usage.sqlite_peak:,} bytes, '
              f'with journal {usage.peak:,} bytes -> {args.out}', flush=True)
    except sqlite3.OperationalError as exc:
        if 'full' in str(exc):
            raise SystemExit('SQLite size ceiling reached; results remain resumable. Use --block-months 1 '
                             'with --rebuild, or increase --max-sqlite-bytes if disk permits.') from exc
        raise
    finally:
        if pool:
            pool.shutdown(cancel_futures=True)
        db.close()


if __name__ == '__main__':
    main()
