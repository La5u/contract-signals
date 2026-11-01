#!/usr/bin/env python3
"""Research only: group and placement indicators G1-G10 (korea-labels-plan.md, "Group and placement indicators,
fixed 2026-10-26"), per target opening; rated by tools/korea-curves.py --group.

Stages (private cache ~/.cache/contract-signals/korea/group):
  targets   the openings korea-label-checks.py uses (Bids.opening of every labelled and comparison contract) for the
            collusion, court and audit families -> targets.tsv (notice, ord, day, role: label/comparison).
  history   G1-G5 from the rolling bid history: tools/korea-bid-history.py's import, pruning and coverage, with its
            B10/B11 step replaced by G1-G5 for the target openings only -> --out sqlite, table group_checks.
  openings  every bid row of the target openings (API day files first, else Data Hub weeks; firm names dropped)
            -> openings.jsonl.gz (notice, ord, bidders [bizno, reason, won]); G6 comes from these.
  lists     the fixed sample (all labelled openings, comparisons whose SHA-256 of "korea-group-sample:<notice>-<ord>"
            is in the lowest 5 %) -> picks-notices.txt (G7 fetch) and firm-biznos.txt (G9 fetch: bidders of the
            sample's openings with 2-20 bids).
  assemble  measures.tsv: notice, ord, G1..G7, G9, G10 (empty = unknown); rivals.tsv.gz: per (target, rival) G1, G3, G5
            and the rival's futile bid, pick match, shared contact and consortium tie with the winner (same-rival pairs).

Losing bidders' identities stay in the private cache; nothing here is published.
"""
import argparse
import bisect
import datetime as dt
import gzip
import hashlib
import importlib.util
import json
import multiprocessing
import os
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bh = load('korea_bid_history', 'korea-bid-history.py')
BASE = bh.BASE
GROUP = BASE / 'group'
FUTILE = ('예가초과', '낙찰하한선 미달')
SAMPLE = 0.05
NO_PAIR = 1000.0
COLUMNS = ('G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G9', 'G10')


def ord3(value):
    return str(value).strip().zfill(3)


# ---------------------------------------------------------------- targets

def targets(args):
    lc = load('korea_label_checks', 'korea-label-checks.py')
    out = {}
    runs = [('collusion', 'collusion', None), ('court', 'corruption', BASE / 'prec/extract/links.jsonl'),
            ('audit', 'corruption', BASE / 'bai/links.jsonl')]
    for name, family, links in runs:
        if args.families and name not in args.families.split(','):
            continue
        ns = SimpleNamespace(db=BASE / 'opnstd.sqlite', buyer='contract', family=family, court_links=links)

        def make(contracts):
            bids = lc.Bids(args.bids, Path('/nonexistent'))
            def check(c):
                o = bids.opening(c['notice'], c.get('notice_ord', '')) if c['notice'] else None
                return {'open': (str(o['notice']), ord3(o['ord']), dt.date.fromisoformat(o['day']).toordinal())
                        if o is not None else None}
            return check
        rows, _, _ = lc.prepare(ns, make)
        n = 0
        for r in rows(lambda c: True, True):
            o = r['checks']['open']
            if o is None:
                continue
            role = 'label' if 'combined' in r['groups'] else 'comparison'
            key = o[:2]
            if out.get(key, (None, 'comparison'))[1] != 'label':
                out[key] = (o[2], role)
            n += 1
        print(f'{name}: {n} rows with an opening; {len(out)} distinct openings so far', flush=True)
    GROUP.mkdir(parents=True, exist_ok=True)
    with (GROUP / 'targets.tsv').open('w', encoding='utf-8') as f:
        for (notice, order), (day, role) in sorted(out.items()):
            f.write(f'{notice}\t{order}\t{day}\t{role}\n')
    print(f'{len(out)} openings -> {GROUP / "targets.tsv"}')


def read_targets():
    with (GROUP / 'targets.tsv').open(encoding='utf-8') as f:
        return [tuple(line.rstrip('\n').split('\t')) for line in f if line.strip()]


# ---------------------------------------------------------------- history (G1-G5)

TARGETS = set()  # (notice id, ord) as bid-history stores them; filled in main before bh.main runs


def connect(path, max_bytes=bh.DEFAULT_MAX_BYTES, _connect=bh.connect):
    db = _connect(path, max_bytes)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS group_checks (
            notice INTEGER, ord INTEGER, g1 REAL, g2 REAL, g3 REAL, g4 REAL, g5 REAL,
            PRIMARY KEY (notice, ord)) WITHOUT ROWID;
        CREATE TABLE IF NOT EXISTS group_rivals (
            notice INTEGER, ord INTEGER, rival INTEGER, g1 REAL, g3 REAL, g5 REAL,
            PRIMARY KEY (notice, ord, rival)) WITHOUT ROWID;
        CREATE INDEX IF NOT EXISTS openings_demand ON openings (demand_code, opening_date);
    ''')
    return db


def measures(db, demand, wanted, lo, hi):
    """G1-G5 for the target openings `wanted` [(notice, ord, day, winners, winner)] of one demand institution, and
    G1, G3 and G5 per rival [(notice, ord, rival, g1, g3, g5)] for the same-rival pairs (plan amendment 2026-10-27)."""
    ops = db.execute('SELECT notice, ord, opening_date, winners, winner FROM openings WHERE demand_code = ? '
                     'AND opening_date BETWEEN ? AND ? ORDER BY opening_date, notice, ord', (demand, lo, hi)).fetchall()
    index = {(n, o): i for i, (n, o, *_) in enumerate(ops)}
    days = [r[2] for r in ops]
    notice_of = [r[0] for r in ops]
    winner_of = [r[4] if r[3] == 1 else None for r in ops]
    bidders = [dict() for _ in ops]  # bizno -> rate (percentage points) or None
    firm_ops = defaultdict(list)
    for n, o, bizno, rate, tail in db.execute(
            'SELECT b.notice, b.ord, b.bizno, b.rate, b.rate_tail FROM openings o JOIN bids b USING (notice, ord) '
            'WHERE o.demand_code = ? AND o.opening_date BETWEEN ? AND ?', (demand, lo, hi)):
        i = index.get((n, o))
        if i is None:
            continue
        value = None if rate is None else rate / 1000 + (float('0.' + str(tail)[1:]) / 1000 if tail else 0)
        bidders[i][bizno] = value
    for i, bs in enumerate(bidders):
        for b in bs:
            firm_ops[b].append(i)  # increasing i, since ops are in index order
    out, per_rival = [], []
    for notice, order, day, winners, winner in wanted:
        t = index.get((notice, order))
        if t is None or winners != 1:
            out.append((notice, order, None, None, None, None, None))
            continue
        w = winner
        a, b = bisect.bisect_left(days, day - 365), bisect.bisect_right(days, day + 365)
        inside = lambda i: a <= i < b and notice_of[i] != notice
        N = sum(1 for i in range(a, b) if notice_of[i] != notice)
        O = {f: {i for i in firm_ops[f][bisect.bisect_left(firm_ops[f], a):bisect.bisect_left(firm_ops[f], b)] if inside(i)}
             for f in bidders[t]}
        Ow = O.get(w, set())
        rivals = [f for f in bidders[t] if f != w]
        # G1 CO-BID
        g1_r = {r: len(Ow & O[r]) / (len(Ow) * len(O[r]) / N + 1) if N else 0.0 for r in rivals}
        g1 = max(g1_r.values()) if rivals and N else 0.0
        # G2 ROTATION
        group = {w} | {r for r in rivals if len(Ow & O[r]) >= 3}
        g2 = 0.0
        if len(group) > 1:
            wins = Counter()
            for i in set().union(*(O[f] for f in group)) | {t}:
                if winner_of[i] in group and sum(1 for f in group if f in bidders[i]) >= 2:
                    wins[winner_of[i]] += 1
            m = sum(wins.values())
            if m >= 3:
                g2 = 1 - max(wins.values()) / m
        # G3 COVER
        g3_r = {r: sum(1 for i in O[r] if winner_of[i] == w) / len(O[r])
                if len(O[r]) >= 3 and not any(winner_of[i] == r for i in O[r]) else 0.0 for r in rivals}
        g3 = max(g3_r.values(), default=0.0)
        # G4 TURF (national bids of the winner; the retained window covers [lo, hi])
        bids_all, wins_all, bids_d, wins_d = db.execute(
            'SELECT COUNT(*), COALESCE(SUM(won), 0), COALESCE(SUM(demand_code = ?), 0), '
            'COALESCE(SUM(won AND demand_code = ?), 0) FROM bids INDEXED BY bids_bidder '
            'WHERE bizno = ? AND opening_date BETWEEN ? AND ? AND notice != ?',
            (demand, demand, w, day - 365, day + 365, notice)).fetchone()
        g4 = (wins_d / wins_all - (bids_d / bids_all if bids_all else 0)) if wins_all else 0.0
        # G5 STABLE-GAP
        g5_r = dict.fromkeys(rivals, NO_PAIR)
        for r in rivals:
            shared = (Ow & O[r]) | {t}
            if len(shared) < 3:
                continue
            diffs = [bidders[i][r] - bidders[i][w] for i in shared
                     if bidders[i].get(r) is not None and bidders[i].get(w) is not None]
            if len(diffs) >= 3:
                mean = sum(diffs) / len(diffs)
                g5_r[r] = (sum((x - mean) ** 2 for x in diffs) / len(diffs)) ** 0.5
        g5 = min(g5_r.values(), default=NO_PAIR)
        out.append((notice, order, g1, g2, g3, g4, g5))
        per_rival += [(notice, order, r, g1_r[r], g3_r[r], g5_r[r]) for r in rivals]
    return out, per_rival


def group_chunk(jobs, complete):
    db = bh.READER
    out, per_rival = [], []
    for demand, wanted, lo, hi in jobs:
        known = [x for x in wanted if x[2] in complete]
        out += [(n, o, None, None, None, None, None) for n, o, d, *_ in wanted if d not in complete]
        if known:
            rows, rivals = measures(db, demand, known, lo, hi)
            out += rows
            per_rival += rivals
    return out, per_rival


def refresh_group(db, start, end, complete, usage=None, pool=None):
    """Replaces bh.refresh_checks: G1-G5 for the block's target openings, grouped by demand institution."""
    rows = [r for r in db.execute('SELECT notice, ord, opening_date, demand_code, winners, winner FROM openings '
                                  'WHERE opening_date >= ? AND opening_date < ?', (start, end))
            if (r[0], r[1]) in TARGETS]
    by_demand = defaultdict(list)
    for n, o, d, demand, winners, winner in rows:
        if demand is None:
            continue
        by_demand[demand].append((n, o, d, winners, winner))
    jobs = [(demand, wanted, start - 730, end - 1 + 730) for demand, wanted in by_demand.items()]
    # Window per job: every target's +/-365 days lies within [start - 365, end - 1 + 365], the retained range; the
    # wider bounds only cost nothing, since pruning has already removed rows outside it.
    days = frozenset(d for d in complete if start - 1 <= d <= end)
    chunks = [jobs[i::8] for i in range(8)] if pool else [jobs]
    results = pool.map(group_chunk, chunks, [days] * len(chunks)) if pool else (group_chunk_local(db, c, days) for c in chunks)
    count = 0
    for res, rivals in results:
        db.executemany('INSERT OR REPLACE INTO group_checks VALUES (?, ?, ?, ?, ?, ?, ?)', res)
        db.executemany('INSERT OR REPLACE INTO group_rivals VALUES (?, ?, ?, ?, ?, ?)', rivals)
        count += len(res)
    db.commit()
    print(f'  {count} target openings measured in {len(jobs)} demand institutions', flush=True)
    return count


def group_chunk_local(db, jobs, complete):
    bh.READER = db
    return group_chunk(jobs, complete)


def history(args, rest):
    by_text = {(n, int(o)) for n, o, _, _ in read_targets()}
    out = Path(rest[rest.index('--out') + 1]) if '--out' in rest else GROUP / 'group-history.sqlite'
    if '--out' not in rest:
        rest = rest + ['--out', str(out)]
    # Notice texts as bid-history stores them: digits directly, others through its identities table (created by
    # the import itself, so they are resolved lazily per block).
    numeric = {(int(n), o) for n, o in by_text if n.isascii() and n.isdigit()}
    others = {(n, o) for n, o in by_text if not (n.isascii() and n.isdigit())}
    TARGETS.update(numeric)
    if others:
        print(f'{len(others)} non-numeric notices: resolved per block', flush=True)
    original = refresh_group

    def refresh(db, start, end, complete, usage=None, pool=None):
        for n, o in list(others):
            row = db.execute("SELECT id FROM identities WHERE kind = 'notice' AND value = ?", (n,)).fetchone()
            if row:
                TARGETS.add((row[0], o))
                others.discard((n, o))
        return original(db, start, end, complete, usage, pool)
    bh.SCHEMA = 'group-2'
    bh.connect = connect
    bh.refresh_checks = refresh
    bh.main(rest)


# ---------------------------------------------------------------- openings (raw rows, G6, lists)

WANTED = set()  # target (notice, ord) texts; set before the pool forks, so workers inherit it


def scan_file(job):
    path, kind = job
    wanted = WANTED
    found = defaultdict(dict)
    with gzip.open(path, 'rt', encoding='utf-8-sig', newline='') as f:
        if kind == 'hub':
            import csv
            for r in csv.DictReader(f, delimiter='\t'):
                key = (r['입찰공고번호'].strip(), ord3(r['입찰공고차수'] or '0'))
                if key in wanted:
                    bizno = re.sub(r'\D', '', r['업체사업자등록번호'])
                    reason = r['입찰부적격사유'].strip() or ('정상' if r['부적격여부'].strip() != 'Y' else '')
                    found[key][bizno] = (reason, r['낙찰자선정여부'].strip() == 'Y')
        else:
            for line in f:
                r = json.loads(line)
                key = (str(r.get('bidNtceNo') or '').strip(), ord3(r.get('bidNtceOrd') or '0'))
                if key in wanted:
                    bizno = re.sub(r'\D', '', str(r.get('bidprcCorpBizrno') or ''))
                    found[key][bizno] = ((r.get('dqlfctnRsn') or '').strip(), r.get('sucsfYn') == 'Y')
    return kind, {k: v for k, v in found.items()}


def openings(args):
    rows = read_targets()
    wanted = {(n, o) for n, o, _, _ in rows}
    days = {dt.date.fromordinal(int(d)) for _, _, d, _ in rows}
    jobs = []
    for kind in bh.BUSINESS:
        folder = BASE / 'bids/bids' / kind
        for d in sorted(days):
            p = folder / f'{d.isoformat()}.jsonl.gz'
            if p.exists():
                jobs.append((p, 'api'))
    for p in sorted((BASE / 'datahub').glob('*.csv.gz')):
        monday = dt.date.fromisoformat(p.name[:10])
        if any(monday <= d <= monday + dt.timedelta(days=bh.HUB_DELAY + 6) for d in days):
            jobs.append((p, 'hub'))
    print(f'{len(jobs)} files to scan for {len(wanted)} openings', flush=True)
    api, hub = defaultdict(dict), defaultdict(dict)
    WANTED.update(wanted)
    with ProcessPoolExecutor(args.workers, mp_context=multiprocessing.get_context('fork')) as pool:
        for i, (kind, found) in enumerate(pool.map(scan_file, jobs, chunksize=1)):
            target = api if kind == 'api' else hub
            for k, v in found.items():
                target[k].update(v)
            if (i + 1) % 200 == 0:
                print(f'  {i + 1} of {len(jobs)} files', flush=True)
    out = GROUP / 'openings.jsonl.gz'
    with gzip.open(out, 'wt', encoding='utf-8') as f:
        for key in sorted(wanted):
            bs = api.get(key) or hub.get(key)
            if bs:
                f.write(json.dumps({'notice': key[0], 'ord': key[1], 'source': 'api' if key in api else 'hub',
                                    'bidders': [[b, r, w] for b, (r, w) in sorted(bs.items())]}, ensure_ascii=False) + '\n')
    print(f'{sum(1 for k in wanted if api.get(k) or hub.get(k))} of {len(wanted)} openings with rows -> {out}')


def read_openings():
    with gzip.open(GROUP / 'openings.jsonl.gz', 'rt', encoding='utf-8') as f:
        return {(r['notice'], r['ord']): r['bidders'] for r in map(json.loads, f)}


def sampled(notice, order):
    h = hashlib.sha256(f'korea-group-sample:{notice}-{order}'.encode()).digest()
    return int.from_bytes(h[:8], 'big') / 2 ** 64 < SAMPLE


def lists(args):
    rows = read_targets()
    ops = read_openings()
    chosen = [(n, o) for n, o, _, role in rows if role == 'label' or sampled(n, o)]
    with (GROUP / 'picks-notices.txt').open('w', encoding='utf-8') as f:
        for n, o in chosen:
            if (n, o) in ops:
                f.write(f'{n}\t{o}\n')
    firms = sorted({b for k in chosen if 2 <= len(ops.get(k, ())) <= 20 for b, _, _ in ops[k] if len(b) == 10})
    (GROUP / 'firm-biznos.txt').write_text(''.join(b + '\n' for b in firms), encoding='utf-8')
    labels = sum(1 for _, _, _, role in rows if role == 'label')
    print(f'sample: {len(chosen)} openings ({labels} labelled), {sum(1 for k in chosen if k in ops)} with rows; '
          f'{len(firms)} firms of 2-20-bid openings')


# ---------------------------------------------------------------- assemble

def winner_rivals(bidders):
    winners = [b for b, _, won in bidders if won]
    if len(winners) != 1:
        return None, []
    return winners[0], [x for x in bidders if x[0] != winners[0]]


def contact_keys(path_firms, fallback):
    keys = defaultdict(set)  # bizno -> {('tel', digits), ('adr', text)}
    found = set()
    if path_firms.exists():
        for r in map(json.loads, path_firms.open(encoding='utf-8')):
            if not r.get('found'):
                continue
            found.add(r['bizno'])
            tel = re.sub(r'\D', '', r.get('tel') or '')
            if len(tel) >= 8:
                keys[r['bizno']].add(('tel', tel))
            adr = re.sub(r'\s', '', (r.get('adrs') or '') + (r.get('dtl') or ''))
            if adr:
                keys[r['bizno']].add(('adr', adr))
    for bizno, (adr, tel) in fallback.items():
        if bizno in found:
            continue
        tel = re.sub(r'\D', '', tel or '')
        if len(tel) >= 8:
            keys[bizno].add(('tel', tel))
        adr = re.sub(r'\s', '', adr or '')
        if adr:
            keys[bizno].add(('adr', adr))
    holders = Counter(k for ks in keys.values() for k in ks)
    return {b: {k for k in ks if holders[k] <= 3} for b, ks in keys.items()}, keys.keys()


def winner_contacts(wanted):
    """Winner address and telephone from the raw open-standard contracts, for business numbers in `wanted`."""
    out = {}
    for p in sorted((BASE / 'opnstd-contracts').glob('*.jsonl.gz')):
        with gzip.open(p, 'rt', encoding='utf-8') as f:
            for line in f:
                if '"rprsntCorpBizrno"' not in line:
                    continue
                r = json.loads(line)
                b = re.sub(r'\D', '', r.get('rprsntCorpBizrno') or '')
                if b in wanted and (r.get('rprsntCorpAdrs') or r.get('rprsntCorpContactTel')):
                    out[b] = (r.get('rprsntCorpAdrs'), r.get('rprsntCorpContactTel'))
    return out


RIVAL_COLUMNS = ('g1', 'g3', 'g5', 'futile', 'pick', 'contact', 'joint')


def rival_rows(key, w, rivals, hist, picks, picks_fetched, contacts, with_contact, contacts_known, partners, joint_known):
    """Per rival of one target opening: (bizno, [g1, g3, g5, futile, pick, contact, joint]), None = unknown. Rivals are
    those of the opening rows (w known) joined with those of the bid history; flags need the opening rows."""
    reasons = {b: reason for b, reason, _ in rivals} if w else {}
    out = []
    for r in sorted(set(reasons) | set(hist)):
        g = list(hist.get(r, [None] * 3))
        futile = pick = contact = joint = None
        if r in reasons:
            futile = float(reasons[r] in FUTILE)
            if picks_fetched and w in picks and r in picks:
                pick = float(picks[r] == picks[w])
            if contacts_known and w in with_contact and r in with_contact:
                contact = float(bool(contacts.get(w, set()) & contacts.get(r, set())))
            if joint_known:
                joint = float(r in partners)
        out.append((r, g + [futile, pick, contact, joint]))
    return out


def assemble(args):
    rows = read_targets()
    ops = read_openings()
    hist, hist_rivals = {}, defaultdict(dict)
    hpath = GROUP / 'group-history.sqlite'
    if hpath.exists():
        import sqlite3
        con = sqlite3.connect(f'file:{hpath}?mode=ro', uri=True)
        ids = {i: v for v, i in con.execute("SELECT value, id FROM identities WHERE kind = 'notice'")}
        firms = {i: v for v, i in con.execute("SELECT value, id FROM identities WHERE kind = 'bizno'")}
        for n, o, *g in con.execute('SELECT * FROM group_checks'):
            hist[(ids.get(n, str(n)), ord3(o))] = g
        if con.execute("SELECT 1 FROM sqlite_master WHERE name = 'group_rivals'").fetchone():
            for n, o, r, *g in con.execute('SELECT * FROM group_rivals'):
                hist_rivals[(ids.get(n, str(n)), ord3(o))][firms.get(r, str(r).zfill(10))] = g
    picks = defaultdict(dict)
    ppath = GROUP / 'picks/picks.jsonl'
    if ppath.exists():
        for r in map(json.loads, ppath.open(encoding='utf-8')):
            if len(r['picks']) == 2:
                picks[(r['notice'], r['ord'])][r['bizno']] = tuple(sorted(r['picks']))
    fetched_picks = {line.rstrip('\n').replace(' ', '\t') for line in (GROUP / 'picks/done.txt').open()} if (GROUP / 'picks/done.txt').exists() else set()
    biznos = {b for k in ops for b, _, _ in ops[k]}
    fallback = winner_contacts(biznos) if not args.no_fallback else {}
    contacts, with_contact = contact_keys(GROUP / 'firms/firms.jsonl', fallback)
    with_contact = set(with_contact)
    joint = defaultdict(list)  # bizno -> [(day, members)]
    jdone = set()
    jpath = GROUP / 'joint/joint.jsonl'
    if jpath.exists():
        for r in map(json.loads, jpath.open(encoding='utf-8')):
            try:
                d = dt.date.fromisoformat(r['date'][:10]).toordinal()
            except ValueError:
                continue
            ms = frozenset(m[0] for m in r['members'])
            for m in ms:
                joint[m].append((d, ms))
        jdone = Counter(line.split('\t')[1].strip() for line in (GROUP / 'joint/done.tsv').open())
    joint_day_ok = {dt.date.fromisoformat(d).toordinal() for d, c in jdone.items() if c == 4} if jdone else set()
    out = GROUP / 'measures.tsv'
    counts = Counter()
    with out.open('w', encoding='utf-8') as f, gzip.open(GROUP / 'rivals.tsv.gz', 'wt', encoding='utf-8') as fr:
        f.write('notice\tord\t' + '\t'.join(COLUMNS) + '\n')
        fr.write('notice\tord\trival\t' + '\t'.join(RIVAL_COLUMNS) + '\n')
        for n, o, day, role in rows:
            day = int(day)
            key = (n, o)
            g = list(hist.get(key, [None] * 5))
            bidders = ops.get(key)
            w, rivals = winner_rivals(bidders) if bidders else (None, [])
            g6 = sum(1 for _, reason, _ in rivals if reason in FUTILE) / len(rivals) if w and rivals else None
            g7 = None
            if f'{n}\t{o}' in fetched_picks and w:
                p = picks.get(key, {})
                rp = [p[b] for b, _, _ in rivals if b in p]
                if w in p and rp:
                    g7 = sum(1 for x in rp if x == p[w]) / len(rp)
            g9 = None
            if bidders and 2 <= len(bidders) <= 20:
                have = [b for b, _, _ in bidders if b in with_contact]
                if len(have) >= 2:
                    seen = Counter(k for b in set(have) for k in contacts.get(b, ()))
                    g9 = 1.0 if any(c >= 2 for c in seen.values()) else 0.0
            g10 = None
            partners = set()
            if w and rivals and all(d in joint_day_ok for d in range(day - 365, day + 366)):
                rs = {b for b, _, _ in rivals}
                partners = {b for d, ms in joint.get(w, ()) if abs(d - day) <= 365 for b in ms & rs}
                g10 = 1.0 if partners else 0.0
            for r, row in rival_rows(key, w, rivals, hist_rivals.get(key, {}), picks.get(key, {}),
                                     f'{n}\t{o}' in fetched_picks, contacts, with_contact, g9 is not None, partners,
                                     g10 is not None):
                fr.write(f'{n}\t{o}\t{r}\t' + '\t'.join('' if v is None else f'{v:.6g}' for v in row) + '\n')
            vals = g + [g6, g7, g9, g10]
            for c, v in zip(COLUMNS, vals):
                counts[(c, role, v is not None)] += 1
            f.write(f'{n}\t{o}\t' + '\t'.join('' if v is None else f'{v:.6g}' for v in vals) + '\n')
    print(f'-> {out}\nknown values (label / comparison):')
    for c in COLUMNS:
        print(f'  {c}: {counts[(c, "label", True)]} / {counts[(c, "comparison", True)]}')


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('stage', choices=('targets', 'history', 'openings', 'lists', 'assemble'))
    p.add_argument('--bids', type=Path, default=BASE / 'bid-features-2026-10-28.sqlite')
    p.add_argument('--families', default='', help='targets: comma-separated subset of collusion,court,audit')
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--no-fallback', action='store_true', help='assemble: skip the open-standard winner contacts')
    args, rest = p.parse_known_args()
    if args.stage == 'history':
        history(args, rest + ['--workers', str(args.workers)])
    elif rest:
        p.error(f'unknown arguments: {rest}')
    else:
        {'targets': targets, 'openings': openings, 'lists': lists, 'assemble': assemble}[args.stage](args)


if __name__ == '__main__':
    main()
