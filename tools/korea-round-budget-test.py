#!/usr/bin/env python3
"""Exploratory: round budgets on labelled notices vs the same buyer's other notices of the same year and type.
Observed vs expected per case; uncertainty by resampling whole cases."""
import json, sqlite3, random, math, collections, sys, os
K = os.path.expanduser('~/.cache/contract-signals/korea')
db = sqlite3.connect(f'file:{K}/notice-budgets.sqlite?mode=ro', uri=True)
LINKED = ('notice', 'amount', 'amount-buyer', 'buyer-name', 'buyer-only', 'bid-opening')

def sig(x):
    return len(str(int(x)).rstrip('0'))
NICE = {1, 2, 25, 3, 5}
DEFS = {
    '1 digit': lambda b: sig(b) == 1,
    '<=2 digits': lambda b: sig(b) <= 2,
    '<=3 digits': lambda b: sig(b) <= 3,
    'x10M': lambda b: b % 10_000_000 == 0,
    'x100M': lambda b: b % 100_000_000 == 0,
    'nice 1/2/2.5/3/5': lambda b: int(str(int(b)).rstrip('0')) in NICE,
}

def labels(path, family):
    out = collections.defaultdict(set)   # case -> notices
    for l in open(path):
        x = json.loads(l)
        if x.get('link') not in LINKED or not x.get('candidates'):
            continue
        n = x['candidates'][0].get('notice_no') or ''
        if not n or n.startswith('contract:'):
            continue
        case = x.get('case_no') or x.get('serial')
        out[f'{family}:{case}'].add(n.split('-')[0])
    return out

def row(n):
    return db.execute('SELECT budget, date, buyer, type, method FROM budgets WHERE notice = ?', (n,)).fetchone()

cache = {}
def peers(buyer, year, typ):
    k = (buyer, year, typ)
    if k not in cache:
        cache[k] = [b for (b,) in db.execute('SELECT budget FROM budgets WHERE buyer = ? AND substr(date,1,4) = ? AND type = ? '
                                              'AND budget >= 1000000', (buyer, year, typ))]
    return cache[k]

def analyse(cases, name, drop=()):
    per_case = {}   # case -> {def: (observed, expected, n)}
    for case, notices in cases.items():
        if case.split(':', 1)[1] in drop:
            continue
        acc = {d: [0.0, 0.0, 0] for d in DEFS}
        for n in notices:
            r = row(n)
            if not r or r[0] < 1_000_000 or not r[1]:
                continue
            b, date, buyer, typ, method = r
            ps = peers(buyer, date[:4], typ)
            if len(ps) < 20:
                continue
            for d, f in DEFS.items():
                e = sum(map(f, ps)) / len(ps)
                acc[d][0] += f(b); acc[d][1] += e; acc[d][2] += 1
        if acc['1 digit'][2]:
            # each case weighs 1: its own observed and expected rates
            per_case[case] = {d: (o / k, e / k) for d, (o, e, k) in acc.items()}
    print(f'\n== {name}: {len(per_case)} cases with budgets (drop {list(drop)})')
    cs = list(per_case)
    for d in DEFS:
        O = sum(per_case[c][d][0] for c in cs); E = sum(per_case[c][d][1] for c in cs)
        ratios = []
        rnd = random.Random(1)
        for _ in range(2000):
            s = [rnd.choice(cs) for _ in cs]
            o = sum(per_case[c][d][0] for c in s); e = sum(per_case[c][d][1] for c in s)
            ratios.append(o / e if e else float('nan'))
        ratios.sort()
        lo, hi = ratios[int(0.025 * len(ratios))], ratios[int(0.975 * len(ratios))]
        print(f'  {d:18s} labelled {O / len(cs):6.1%}  expected {E / len(cs):6.1%}  ratio {O / E if E else float("nan"):4.2f}  [{lo:.2f}, {hi:.2f}]')

col = labels(f'{K}/ftc/extract/links.jsonl', 'kftc')
court = labels(f'{K}/prec/extract/links.jsonl', 'court')
audit = labels(f'{K}/bai/links.jsonl', 'audit') if os.path.exists(f'{K}/bai/links.jsonl') else {}
analyse(col, 'cartel (KFTC)')
analyse(col, 'cartel without the two artifact cases', drop=('2017카총1272', '2022입담1177, 1152, 1153, 1154, 1155, 1156'))
analyse(court, 'court convictions')
if audit:
    analyse(audit, 'audit findings')
