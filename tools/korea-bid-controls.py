#!/usr/bin/env python3
"""Research only: Korean checks against KFTC-rigged tenders, controlled for bidder count, value, business type,
period and winner size.

Same labels, buyer modes, label weights and comparisons as tools/korea-label-checks.py (decision set "weighted, all
linked tenders, all contracts"). Instead of the raw comparison rate, each labelled tender is compared with the
comparison contracts of its own stratum (indirect standardisation): expected hit = the stratum's buyer-weighted
comparison rate (each comparison buyer's own rate in the stratum, averaged over the buyers that have one, as the
decision rule weights buyers), smoothed (sum + 0.5) / (buyers + 1). A stratum with fewer than MIN_BUYERS_CELL
comparison buyers or MIN_CELL comparisons falls back to the next coarser model (last factor dropped). Buyer-weighted as the decision rule: per labelled buyer the mean observed and
mean expected hit; LR = observed / expected, shrunk by 10 buyers towards 1; points 10 x log2 of the LR at the
25th percentile of 2,000 buyer resamples (all buyers redrawn, stratum rates recomputed per draw).

Factors: bidder count of the contract's opening (none without one), value band (labelled amounts divided by 1.3,
owner rule 2026-10-20: rigged contracts are assumed overpriced), business type, period (2008-12, 2013-16, 2017-19,
2020+), buyer (within-buyer model: the label's own buyer's comparisons only), winner size (supplier's original contract value with every buyer in the three previous years, opnstd
`contracts`; it includes the cartel's own awards, so it can over-control).
"""
import argparse
import importlib.util
import json
import random
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lc', ROOT / 'tools/korea-label-checks.py')
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)
pp = lc.pp

OVERPRICING = 1.3
MIN_CELL = 30
MIN_BUYERS_CELL = 5
BIDDER_BINS = [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 7), (8, 10), (11, 15), (16, 20), (21, 30), (31, 50),
               (51, 100), (101, 200), (201, 500), (501, 10**9)]
VALUE_EDGES = [20e6, 50e6, 100e6, 300e6, 1e9, 3e9, 10e9]
SIZE_EDGES = [1, 100e6, 1e9, 10e9]
MODELS = {
    'raw (no control)': [],
    'bidders': ['bidders'],
    'bidders x value': ['bidders', 'value'],
    'bidders x value x type': ['bidders', 'value', 'type'],
    'bidders x value x type x period': ['bidders', 'value', 'type', 'period'],
    'bidders x value x type x winner size': ['bidders', 'value', 'type', 'winner'],
    'value x type x period x winner size (no bidders)': ['value', 'type', 'period', 'winner'],
    'within buyer: buyer x bidders x value': ['buyer', 'bidders', 'value'],
}


def band(x, edges):
    return sum(x >= e for e in edges)


def bidder_bin(n):
    if not n:
        return 'none'
    return next(f'{lo}-{hi}' if lo != hi else str(lo) for lo, hi in BIDDER_BINS if lo <= n <= hi)


def period(y):
    return '2008-12' if y <= 2012 else '2013-16' if y <= 2016 else '2017-19' if y <= 2019 else '2020+'


def supplier_values(db, suppliers):
    """(supplier, year) -> original contract value signed that year, every buyer."""
    con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    out = Counter()
    for s, y, v in con.execute('SELECT last_supplier_bizrno, substr(signed, 1, 4), original_amount FROM contracts '
                               'WHERE last_supplier_bizrno IS NOT NULL AND signed IS NOT NULL'):
        if s in suppliers and v:
            out[(s, int(y))] += v
    return out


def analyse(units, check, factors, rng_seed):
    """units: (buyer, is_label, weight, status, strata dict). Returns the controlled result for one check and model."""
    ev = [u for u in units if u[3] in ('signal', 'clear')]
    levels = [tuple(factors[:k]) for k in range(len(factors), -1, -1)]  # finest first
    buyers = sorted({u[0] for u in units})
    bidx = {b: i for i, b in enumerate(buyers)}
    # Comparison counts per buyer and stratum, for every level.
    cells = []
    for lev in levels:
        keys = {}
        for u in ev:
            keys.setdefault(tuple(u[4][f] for f in lev), len(keys))
        H = np.zeros((len(buyers), len(keys)))
        N = np.zeros((len(buyers), len(keys)))
        for u in ev:
            w = u[2] if not u[1] else 0.0
            if w:
                k = keys[tuple(u[4][f] for f in lev)]
                N[bidx[u[0]], k] += w
                H[bidx[u[0]], k] += w * (u[3] == 'signal')
        P = (N > 0).astype(float)
        R = np.divide(H, N, out=np.zeros_like(H), where=N > 0)
        cells.append((lev, keys, R, P, N))
    labels = [u for u in ev if u[1]]
    if not labels:
        return None
    # Level per label: finest with at least MIN_CELL comparisons in the full sample.
    lab_level, lab_key = [], []
    for u in labels:
        for li, (lev, keys, R, P, N) in enumerate(cells):
            k = keys[tuple(u[4][f] for f in lev)]
            # A buyer's own cell has one comparison buyer by construction: only its size counts.
            enough_buyers = 'buyer' in lev or P[:, k].sum() >= MIN_BUYERS_CELL
            if (N[:, k].sum() >= MIN_CELL and enough_buyers) or li == len(cells) - 1:
                lab_level.append(li)
                lab_key.append(k)
                break
    lab_buyer = np.array([bidx[u[0]] for u in labels])
    lab_w = np.array([u[2] for u in labels])
    lab_hit = np.array([u[3] == 'signal' for u in labels], float)
    lab_level, lab_key = np.array(lab_level), np.array(lab_key)
    fell_back = int((lab_level > 0).sum())

    def stat(mult):
        e = np.empty(len(labels))
        for li, (lev, keys, R, P, N) in enumerate(cells):
            sel = lab_level == li
            if sel.any():
                rate = (mult @ R + 0.5) / (mult @ P + 1)
                e[sel] = rate[lab_key[sel]]
        O = E = W = 0.0
        for b in np.unique(lab_buyer):
            s = lab_buyer == b
            if not mult[b]:
                continue
            ws = lab_w[s]
            bw = ws.max() * mult[b]
            O += bw * (ws * lab_hit[s]).sum() / ws.sum()
            E += bw * (ws * e[s]).sum() / ws.sum()
            W += bw
        if not W or not E:
            return None
        p0 = E / W
        return (O, E, W, ((O + pp.PRIOR_BUYERS * p0) / (W + pp.PRIOR_BUYERS)) / p0)

    full = stat(np.ones(len(buyers)))
    if not full:
        return None
    O, E, W, lr = full
    rng = random.Random(f'{rng_seed}-{check}')
    draws = []
    for _ in range(pp.BOOT):
        mult = np.bincount([rng.randrange(len(buyers)) for _ in buyers], minlength=len(buyers)).astype(float)
        r = stat(mult)
        if r:
            draws.append(r[3])
    draws.sort()
    q = lambda p: draws[min(len(draws) - 1, int(p * len(draws)))]
    n_lab_buyers = len({u[0] for u in labels})
    conf = min(q(pp.CONFIDENT_Q), lr)
    return {'observed': round(O, 2), 'expected': round(E, 2), 'buyers': n_lab_buyers, 'tenders': len(labels),
            'fell_back': fell_back, 'lr': round(lr, 3), 'lr_ci': [round(q(0.025), 3), round(q(0.975), 3)],
            'lr_confident': round(conf, 3),
            'points': pp.points(conf) if n_lab_buyers >= pp.MIN_BUYERS else 0.0}


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--db', type=Path, default=lc.BASE / 'opnstd.sqlite')
    p.add_argument('--buyer', choices=('contract', 'demand'), default='contract')
    p.add_argument('--bids', type=Path, default=lc.BASE / 'bid-features-2026-10-24.sqlite')
    p.add_argument('--history', type=Path, default=lc.BASE / 'bid-history.sqlite')
    p.add_argument('--checks', default='B,K6,K5,G3', help='comma-separated check prefixes to run')
    p.add_argument('--json', type=Path)
    args = p.parse_args()

    labels = lc.load_labels()
    fin_path = lc.BASE / 'ftc-suits/finality.json'
    finality = json.loads(fin_path.read_text()) if fin_path.exists() else {}
    versions, key_col = lc.scan(args.db, labels, args.buyer)
    contracts = lc.contracts_from(versions, key_col)
    del versions
    bids = lc.Bids(args.bids, args.history)
    checks = lc.build_checks(contracts, bids=bids)
    members, reps = set(), {}
    for lab in labels.values():
        cs = [contracts[n] for n in lab['contracts'] if n in contracts]
        members |= {c['no'] for c in cs}
        cs = [c for c in cs if c['original']]
        if cs:
            rep = max(cs, key=lambda c: (c['amount'], c['no']))
            reps.setdefault(rep['no'], lab)
    weight = lambda case: lc.WEIGHTS[(finality.get(case) or {}).get('status', 'none')]
    buyer_years = {(contracts[n]['buyer'], contracts[n]['year']) for n in reps}
    pool = [c for c in contracts.values() if (c['buyer'], c['year']) in buyer_years and c['original']
            and not (c['no'] in members and c['no'] not in reps)]
    print(f'{len(reps)} labelled contracts, {len(pool) - len(reps)} comparisons ({key_col})', flush=True)

    sizes = supplier_values(args.db, {c['supplier'] for c in pool if c['supplier']})
    wanted = [k for k in lc.CHECKS if any(k.startswith(x + ' ') or k.split(' ')[0].startswith(x) for x in args.checks.split(','))]
    per_check = defaultdict(list)
    profile = defaultdict(Counter)
    for c in pool:
        lab = reps.get(c['no'])
        o = bids.opening(c['notice'], c.get('notice_ord', '')) if c['notice'] else None
        amount = c['amount'] / OVERPRICING if lab else c['amount']
        prior = sum(sizes.get((c['supplier'], c['year'] - k), 0) for k in (1, 2, 3)) if c['supplier'] else 0
        strata = {'bidders': bidder_bin(o['bids'] if o else None), 'value': band(amount, VALUE_EDGES),
                  'type': c['business'] or '', 'period': period(c['year']), 'winner': band(prior, SIZE_EDGES),
                  'buyer': c['buyer']}
        ch = checks(c)
        w = weight(lab['case']) if lab else 1.0
        for k in wanted:
            st = ch[k]['status']
            if lab and w > 0:
                per_check[k].append((c['buyer'], True, w, st, strata))
            if not lab or w < 1:
                per_check[k].append((c['buyer'], False, 1 - w if lab else 1.0, st, strata))
        if o:
            for f in ('bidders', 'value', 'winner'):
                profile[(f, 'rigged' if lab else 'comparison')][strata[f]] += 1
    print('\nProfile of contracts with an opening (share of rigged / comparison):')
    for f in ('bidders', 'value', 'winner'):
        r, k = profile[(f, 'rigged')], profile[(f, 'comparison')]
        tr, tk = sum(r.values()), sum(k.values())
        keys = sorted(set(r) | set(k), key=lambda x: (isinstance(x, str) and x != 'none' and int(x.split('-')[0]), str(x)))
        print(f'  {f}: ' + ', '.join(f'{x}: {r[x] / tr * 100:.0f}/{k[x] / tk * 100:.0f}' for x in keys))

    out = {'buyer': key_col, 'models': {}}
    print('\n| Check | ' + ' | '.join(MODELS) + ' |')
    print('|---|' + '---|' * len(MODELS))
    for k in wanted:
        cellsout = []
        for name, factors in MODELS.items():
            res = analyse(per_check[k], k, factors, pp.SEED)
            out['models'].setdefault(name, {})[k] = res
            cellsout.append('NA' if not res else f"{res['observed']:.1f}/{res['expected']:.1f} = {res['lr']:.2f} "
                            f"[{res['lr_ci'][0]:.2f}, {res['lr_ci'][1]:.2f}] → {res['points']:g}"
                            + (f" ({res['fell_back']} coarser)" if res['fell_back'] else ''))
        print(f'| {k} | ' + ' | '.join(cellsout) + ' |', flush=True)
    if args.json:
        args.json.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
