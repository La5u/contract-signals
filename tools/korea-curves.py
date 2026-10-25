#!/usr/bin/env python3
"""Research only: per-country curves for continuous Korean indicators (indicator-standard.md, kind 3).

Plan: research/calibration/korea-labels-plan.md, "PRICE-RATIO curve, fixed 2026-10-24". Records, labels, label
weights and comparisons come from tools/korea-label-checks.py (prepare). For a measure:

- bins: K equal-count bins at the comparisons' quantiles (every comparison record with a value counts once; labels
  never place edges), coinciding edges merged, K in KS;
- K by 5-fold cross-validation over whole cases (labels by case hash, comparisons by buyer hash): each class's bin
  distribution estimated buyer-weighted on the training folds (each buyer counts once with its largest label weight,
  as propose-indicator-points.weighted) with 0.5 added per bin; score the held-out balanced log-loss; chosen K is the
  smallest within one standard error of the best;
- points per bin of the chosen K by the decision rule (propose-indicator-points.analyse/decide), a bin vs any other
  known value;
- one range [a, b) (owner 2026-10-25), a and b at the comparison percentiles 1-99 or open-ended, only where labels are
  more common than comparisons: lowest cross-validated loss, each fold's training choice, a 200-resample bootstrap
  (labelled cases, comparison buyers); rated raw (decision rule) and with the value-band control of
  tools/korea-bid-controls.py. Size-like measures (BUYER-SHARE, SUPPLIER-DEPENDENCE) choose the range with comparisons
  reweighted to the labels' value bands (labels / 1.3), and the controlled points are their decision.
"""
import argparse
import hashlib
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lc', ROOT / 'tools/korea-label-checks.py')
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)
pp = lc.pp
bspec = importlib.util.spec_from_file_location('bc', ROOT / 'tools/korea-bid-controls.py')
bc = importlib.util.module_from_spec(bspec)
bspec.loader.exec_module(bc)

KS = [2, 3, 4, 5, 6, 8, 10, 12, 15, 20]
FOLDS = 5
BOOT_CUT = 200
SMOOTH = 0.5
# Former fixed cut-offs (K6, UA-C9, G3, N4, G6), listed for reference only.
REFERENCE_CUTS = {'PRICE-RATIO': [0.95, 0.98], 'BUYER-SHARE': [0.05], 'SUPPLIER-DEPENDENCE': [0.25], 'AMEND-PRICE': [0.2], 'FLOOR-GAP': []}


def price_ratio(c, ctx):
    return c['amount'] / float(c['reserve']) if c['reserve'] and c['amount'] and float(c['reserve']) > 0 else None


def buyer_share(c, ctx):
    t = ctx['total'][(c['buyer'], c['year'])]
    return c['amount'] / t if t and c['amount'] else None


def supplier_dependence(c, ctx):
    t = ctx['total'][(c['buyer'], c['year'])]
    return ctx['by_supplier'][(c['buyer'], c['year'], c['supplier'])] / t if t and c['supplier'] else None


def amend_price(c, ctx):
    if not c['amount'] or not c['window_complete'] or c['long_term']:
        return None
    return c['last_amount'] / c['amount'] - 1


def floor_gap(c, ctx):
    """Winning rate minus the opening's stated minimum winning rate (percentage points)."""
    o = ctx['opening'](c)
    if o is None or not o['lower_rate'] or not o['winner_rate']:
        return None
    return o['winner_rate'] - o['lower_rate']


# name: (function, size-like). Size-like measures contain the contract amount: value-band control (plan 2026-10-25).
MEASURES = {'PRICE-RATIO': (price_ratio, False), 'BUYER-SHARE': (buyer_share, True),
            'SUPPLIER-DEPENDENCE': (supplier_dependence, True), 'AMEND-PRICE': (amend_price, False),
            'FLOOR-GAP': (floor_gap, False)}
NEEDS_BIDS = {'FLOOR-GAP'}


def context(contracts, bids=None):
    """Buyer-year totals over original versions, as build_checks in korea-label-checks.py; the contract's opening
    (the B checks' choice, korea-label-checks.Bids.opening) when bids are given."""
    total, by_supplier = defaultdict(float), defaultdict(float)
    for c in contracts.values():
        if c.get('original', True):
            total[(c['buyer'], c['year'])] += c['amount']
            if c['supplier']:
                by_supplier[(c['buyer'], c['year'], c['supplier'])] += c['amount']
    opening = (lambda c: bids.opening(c['notice'], c.get('notice_ord', '')) if c['notice'] else None) if bids else (lambda c: None)
    return {'total': total, 'by_supplier': by_supplier, 'opening': opening}


def make_checks(names, bids_path=None):
    def make(contracts):
        bids = lc.Bids(bids_path, Path('/nonexistent')) if bids_path and NEEDS_BIDS & set(names) else None
        ctx = context(contracts, bids)
        return lambda c: {**{n: MEASURES[n][0](c, ctx) for n in names}, '_amount': c['amount']}
    return make


def fold_of(key):
    return int(hashlib.sha256(str(key).encode()).hexdigest()[:8], 16) % FOLDS


class Data:
    """Records with a known value as arrays: x, is_label, weight, buyer index, case index (labels), fold."""

    def __init__(self, rows, measure):
        recs = [(r['checks'][measure], 'combined' in r['groups'], r.get('weight', 1.0), r['buyer'], r['case'])
                for r in rows if r['checks'][measure] is not None]
        self.x = np.array([r[0] for r in recs], float)
        self.lab = np.array([r[1] for r in recs], bool)
        self.w = np.array([r[2] for r in recs], float)
        buyers = sorted({r[3] for r in recs})
        bi = {b: i for i, b in enumerate(buyers)}
        self.buyer = np.array([bi[r[3]] for r in recs])
        self.nb = len(buyers)
        cases = sorted({r[4] for r in recs if r[1]})
        ci = {c: i for i, c in enumerate(cases)}
        self.case = np.array([ci[r[4]] if r[1] else -1 for r in recs])
        self.nc = len(cases)
        self.fold = np.array([fold_of(r[4]) if r[1] else fold_of(r[3]) for r in recs])
        self.comp_x = self.x[~self.lab]
        # Value band (labelled amounts / 1.3, owner rule 2026-10-20), and a within-buyer reweighting of the comparisons
        # to the labels' buyer-weighted value-band mix, for size-like measures; 1 otherwise.
        amount = np.array([float(r['checks'].get('_amount') or 0) for r in rows if r['checks'][measure] is not None])
        self.amount = amount
        self.band = np.array([bc.band(a / bc.OVERPRICING if l else a, bc.VALUE_EDGES) for a, l in zip(amount, self.lab)])
        self.mult = np.ones(len(self.x))

    def size_reweight(self):
        nband = len(bc.VALUE_EDGES) + 1
        one = np.ones(len(self.x))
        hl, _ = bw_hist(self, self.band, nband, self.lab, one)
        hc, _ = bw_hist(self, self.band, nband, ~self.lab, one)
        pl, pc = hl / hl.sum(), hc / hc.sum()
        r = np.divide(pl, pc, out=np.zeros_like(pl), where=pc > 0)
        self.mult = np.where(self.lab, 1.0, r[self.band])
        return {'label_bands': pl.round(3).tolist(), 'comparison_bands': pc.round(3).tolist()}

    def cells(self, edges):
        return np.searchsorted(edges, self.x, side='right')

    def edges(self, qs):
        return np.unique(np.quantile(self.comp_x, qs))


def bw_hist(d, cell, ncell, mask, mult, bmult=None):
    """Buyer-weighted histogram of one class: each buyer adds its largest weight, spread over its records' cells in
    proportion to weight x mult (as propose-indicator-points.weighted). bmult (per record, not normalised) scales a
    record's share afterwards: resampling counts, so a buyer or case drawn twice counts twice (Sol review 2026-10-25:
    a draw count inside mult cancelled in the normalisation). Also per-record shares."""
    eff = np.where(mask, d.w * mult, 0.0)
    sumw = np.bincount(d.buyer, eff, d.nb)
    maxw = np.zeros(d.nb)
    np.maximum.at(maxw, d.buyer, np.where(eff > 0, d.w, 0.0))
    share = np.divide(eff * maxw[d.buyer], sumw[d.buyer], out=np.zeros_like(eff), where=sumw[d.buyer] > 0)
    if bmult is not None:
        share = share * bmult
    return np.bincount(cell, share, ncell), share


def probs(h):
    return (h + SMOOTH) / (h.sum() + SMOOTH * len(h))


def heldout_loss(d, cell, ncell, k):
    """Balanced held-out log-loss of fold k, trained on the other folds."""
    one = d.mult  # value-band reweighting of the comparisons for size-like measures, else 1
    train, test = d.fold != k, d.fold == k
    pl = probs(bw_hist(d, cell, ncell, train & d.lab, one)[0])
    pc = probs(bw_hist(d, cell, ncell, train & ~d.lab, one)[0])
    post_l = pl / (pl + pc)
    out = []
    for cls, post in ((d.lab, post_l), (~d.lab, 1 - post_l)):
        _, share = bw_hist(d, cell, ncell, test & cls, one)
        if share.sum() == 0:
            return None
        out.append((share * -np.log(post[cell])).sum() / share.sum())
    return sum(out) / 2


def cv(d, cell, ncell):
    losses = [heldout_loss(d, cell, ncell, k) for k in range(FOLDS)]
    losses = [x for x in losses if x is not None]
    if len(losses) < 2:  # too few scorable folds for a standard error (Sol review 2026-10-25)
        return float('nan'), float('nan'), losses
    return float(np.mean(losses)), float(np.std(losses, ddof=1) / np.sqrt(len(losses))), losses


def range_losses(hl, hc, tl, tc, counter=False):
    """Balanced log-loss of every one-range split [cell i, cell j) vs the rest, trained on histograms hl/hc and scored
    on tl/tc (the same for in-sample). Matrix [i, j]; inf where the training labels' share in range is not above the
    comparisons' (plan: only ranges where labels are more common), and for the whole range."""
    cum = lambda h: np.concatenate([[0.0], np.cumsum(h)])
    HL, HC, TL, TC = cum(hl), cum(hc), cum(tl), cum(tc)
    n = len(hl)
    i, j = np.triu_indices(n + 1, 1)
    a_in, c_in = HL[j] - HL[i], HC[j] - HC[i]
    pl_in = (a_in + SMOOTH) / (HL[-1] + 2 * SMOOTH)
    pc_in = (c_in + SMOOTH) / (HC[-1] + 2 * SMOOTH)
    pl_out, pc_out = 1 - pl_in, 1 - pc_in
    post_in, post_out = pl_in / (pl_in + pc_in), pl_out / (pl_out + pc_out)
    t_in, u_in = TL[j] - TL[i], TC[j] - TC[i]
    loss = ((t_in * -np.log(post_in) + (TL[-1] - t_in) * -np.log(post_out)) / TL[-1]
            + (u_in * -np.log(1 - post_in) + (TC[-1] - u_in) * -np.log(1 - post_out)) / TC[-1]) / 2
    wrong = (a_in / HL[-1] >= c_in / HC[-1]) if counter else (a_in / HL[-1] <= c_in / HC[-1])
    loss[wrong | ((i == 0) & (j == n))] = np.inf
    m = np.full((n + 1, n + 1), np.inf)
    m[i, j] = loss
    return m


def best_range(d, cell, ncell, lb=None, cb=None, mask=None, counter=False):
    """In-sample best range (i, j); lb / cb: resampling counts per labelled / comparison record (None: 1)."""
    mask = np.ones(len(d.x), bool) if mask is None else mask
    hl, _ = bw_hist(d, cell, ncell, mask & d.lab, np.ones(len(d.x)), lb)
    hc, _ = bw_hist(d, cell, ncell, mask & ~d.lab, d.mult, cb)
    m = range_losses(hl, hc, hl, hc, counter)
    return np.unravel_index(np.argmin(m), m.shape)


def cv_range(d, cell, ncell, counter=False):
    """Mean held-out loss matrix over the case folds, and the folds' own matrices."""
    total, n, per_fold = np.zeros((ncell + 1, ncell + 1)), 0, []
    one = np.ones(len(d.x))
    for k in range(FOLDS):
        train, test = d.fold != k, d.fold == k
        hl = bw_hist(d, cell, ncell, train & d.lab, one)[0]
        hc = bw_hist(d, cell, ncell, train & ~d.lab, d.mult)[0]
        tl = bw_hist(d, cell, ncell, test & d.lab, one)[0]
        tc = bw_hist(d, cell, ncell, test & ~d.lab, d.mult)[0]
        if tl.sum() and tc.sum():
            m = range_losses(hl, hc, tl, tc, counter)
            per_fold.append(m)
            total += m
            n += 1
        else:
            per_fold.append(None)
    return total / n, per_fold


def two_range_losses(hl, hc, tl, tc, combos):
    """Balanced log-loss of "in either of two disjoint ranges" vs not, per combo (i1, j1, i2, j2), trained on hl/hc
    and scored on tl/tc; inf where either range alone has no higher training label share than comparison share."""
    cum = lambda h: np.concatenate([[0.0], np.cumsum(h)])
    HL, HC, TL, TC = cum(hl), cum(hc), cum(tl), cum(tc)
    i1, j1, i2, j2 = combos.T
    seg = lambda C, a, b: C[b] - C[a]
    a1, a2, c1, c2 = seg(HL, i1, j1), seg(HL, i2, j2), seg(HC, i1, j1), seg(HC, i2, j2)
    pl_in = (a1 + a2 + SMOOTH) / (HL[-1] + 2 * SMOOTH)
    pc_in = (c1 + c2 + SMOOTH) / (HC[-1] + 2 * SMOOTH)
    post_in, post_out = pl_in / (pl_in + pc_in), (1 - pl_in) / (2 - pl_in - pc_in)
    t_in, u_in = seg(TL, i1, j1) + seg(TL, i2, j2), seg(TC, i1, j1) + seg(TC, i2, j2)
    loss = ((t_in * -np.log(post_in) + (TL[-1] - t_in) * -np.log(post_out)) / TL[-1]
            + (u_in * -np.log(1 - post_in) + (TC[-1] - u_in) * -np.log(1 - post_out)) / TC[-1]) / 2
    loss[(a1 / HL[-1] <= c1 / HC[-1]) | (a2 / HL[-1] <= c2 / HC[-1])] = np.inf
    return loss


def two_ranges(d, rows, measure, one_gain_by_fold):
    """Two disjoint ranges (plan: audit PRICE-RATIO, 2026-10-25): nested choice, gate against no split and against
    the one-range choice, rating of "in either range"."""
    from itertools import combinations
    pct = np.unique(np.quantile(d.comp_x, np.arange(1, 50) / 50))
    cell, ncell = d.cells(pct), len(pct) + 1
    combos = np.array([c for c in combinations(range(ncell + 1), 4) if c[1] < c[2]])
    edge = lambda i: -np.inf if i == 0 else (np.inf if i == ncell else float(pct[i - 1]))
    one = np.ones(len(d.x))
    hist = lambda mask, lab: bw_hist(d, cell, ncell, mask & (d.lab if lab else ~d.lab), one if lab else d.mult)[0]
    gains, picks = [], []
    for k in range(FOLDS):
        train, test = d.fold != k, d.fold == k
        hl, hc, tl, tc = hist(train, True), hist(train, False), hist(test, True), hist(test, False)
        if not (tl.sum() and tc.sum()) or k not in one_gain_by_fold:
            continue
        b = int(np.argmin(two_range_losses(hl, hc, hl, hc, combos)))
        picks.append(combos[b])
        gains.append((np.log(2) - two_range_losses(hl, hc, tl, tc, combos[b:b + 1])[0], one_gain_by_fold[k]))
    g = np.array(gains)
    se = lambda v: float(v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 1 else float('nan')
    gain, gain_se = float(g[:, 0].mean()), se(g[:, 0])
    over, over_se = float((g[:, 0] - g[:, 1]).mean()), se(g[:, 0] - g[:, 1])
    accepted = bool(gain > gain_se and over > over_se)
    hl, hc = hist(np.ones(len(d.x), bool), True), hist(np.ones(len(d.x), bool), False)
    i1, j1, i2, j2 = combos[int(np.argmin(two_range_losses(hl, hc, hl, hc, combos)))]
    r1, r2 = (edge(i1), edge(j1)), (edge(i2), edge(j2))
    show = lambda r: f'[{fmt_x(r[0]) if r[0] > -np.inf else "min"}, {fmt_x(r[1]) if r[1] < np.inf else "max"})'
    print(f'\nTwo ranges (plan 2026-10-25): {measure} in {show(r1)} or {show(r2)}; nested held-out gain over no split '
          f'{gain:.4f} (SE {gain_se:.4f}), over one range {over:.4f} (SE {over_se:.4f}): '
          f'{"accepted" if accepted else "NOT accepted, one range stays"}; per training fold '
          f'{", ".join(show((edge(a), edge(b))) + " + " + show((edge(c), edge(e))) for a, b, c, e in picks)}\n')
    name = f'{show(r1)} or {show(r2)} (two ranges)'
    check = f'{measure} {name}'
    rs = [dict(r, checks={check: lc.status(None if r['checks'][measure] is None else
                                           r1[0] <= r['checks'][measure] < r1[1] or r2[0] <= r['checks'][measure] < r2[1])})
          for r in rows]
    res = pp.analyse(rs, check)
    res = {**res, 'decision': pp.decide(res) if accepted else 'no points (two ranges not accepted)'}
    each = rated(rows, measure, [(f'{show(r1)} (first range alone)', *r1), (f'{show(r2)} (second range alone)', *r2)])
    table([res] + each)
    return {'ranges': [list(r1), list(r2)], 'gain': gain, 'gain_se': gain_se, 'gain_over_one': over,
            'gain_over_one_se': over_se, 'accepted': accepted, 'rated': res, 'each': each}


def counter_range(d, rows, measure):
    """Counter-range (plan 2026-10-25): labels less common than comparisons; same nested gate as the signal range;
    negative points from the shrunk LR at the 75th percentile of the buyer resamples, capped at 0."""
    pct = np.unique(np.quantile(d.comp_x, np.arange(1, 100) / 100))
    cell, ncell = d.cells(pct), len(pct) + 1
    bound = lambda i, lower: (-np.inf if i == 0 else float(pct[i - 1])) if lower else (np.inf if i == ncell else float(pct[i - 1]))
    m, per_fold = cv_range(d, cell, ncell, counter=True)
    ci, cj = np.unravel_index(np.argmin(m), m.shape)
    folds = [best_range(d, cell, ncell, mask=d.fold != k, counter=True) for k in range(FOLDS)]
    gain = np.array([np.log(2) - f[i, j] for f, (i, j) in zip(per_fold, folds) if f is not None])
    gain_mean = float(gain.mean()) if len(gain) else float('nan')
    gain_se = float(gain.std(ddof=1) / np.sqrt(len(gain))) if len(gain) > 1 else float('nan')
    accepted = bool(np.isfinite(gain_mean) and np.isfinite(gain_se) and gain_mean > gain_se)
    lo, hi = bound(ci, True), bound(cj, False)
    show = lambda a, b: f'[{fmt_x(a) if a > -np.inf else "min"}, {fmt_x(b) if b < np.inf else "max"})'
    check = f'{measure} {show(lo, hi)} (counter-range)'
    rs = [dict(r, checks={check: lc.status(None if r['checks'][measure] is None else lo <= r['checks'][measure] < hi)})
          for r in rows]
    res = pp.analyse(rs, check)
    q = pp.bootstrap(rs, check, 'combined', quantiles=(0.025, 0.75, 0.975)) if res.get('lr_shrunk') else None
    upper = max(q[1], res['lr_shrunk']) if q else None
    enough = res['combined']['buyers'] >= pp.MIN_BUYERS
    neg = round(min(0.0, 10 * np.log2(upper)), 1) if upper and enough and accepted else 0.0
    res = {**res, 'lr_confident_upper': upper, 'negative_points': neg,
           'decision': f'{neg:g} points' if neg else ('no points (counter-range not accepted)' if not accepted else 'no points')}
    print(f'\nCounter-range: {measure} in {show(lo, hi)}; nested held-out gain over no split {gain_mean:.4f} (SE {gain_se:.4f}): '
          f'{"accepted" if accepted else "NOT accepted"}; per training fold '
          f'{", ".join(show(bound(i, True), bound(j, False)) for i, j in folds)}; LR {res.get("lr_shrunk")}, '
          f'75th percentile {round(upper, 3) if upper else None} -> {neg:g} points\n')
    table([res])
    return {'range': [lo, hi], 'gain': gain_mean, 'gain_se': gain_se, 'accepted': accepted, 'rated': res}


def value_controlled(d, lo, hi, check):
    """The range rated with the value-band control of tools/korea-bid-controls.py (factor value, buyer resamples)."""
    inr = (d.x >= lo) & (d.x < hi)
    units = [(int(b), bool(l), float(w), 'signal' if s else 'clear', {'value': int(v)})
             for b, l, w, s, v in zip(d.buyer, d.lab, d.w, inr, d.band)]
    return bc.analyse(units, check, ['value'], pp.SEED)


def fmt_x(v):
    return f'{v:.4g}' if abs(v) < 10 else f'{v:,.0f}'


def rated(rows, measure, named):
    """pp.analyse per named interval [lo, hi): rows with that interval as a yes/no check."""
    out = []
    for name, lo, hi in named:
        check = f'{measure} {name}'
        rs = [dict(r, checks={check: lc.status(None if r['checks'][measure] is None
                                                 else lo <= r['checks'][measure] < hi)}) for r in rows]
        res = pp.analyse(rs, check)
        out.append({**res, 'interval': [lo, hi], 'decision': pp.decide(res)})
    return out


def table(results):
    print('| Interval | Hit rate, labelled | Comparisons | LR shrunk [95 %] | Points [95 %] | Decision |')
    print('|---|---|---|---|---|---|')
    for res in results:
        f = lambda g: (f"{res[g]['rate'] * 100:.1f}% ({res[g]['tender_hits']}/{res[g]['tenders']}, {res[g]['buyers']} buyers)"
                       if res[g]['rate'] is not None else 'NA')
        ci = f" [{res['lr_ci'][0]:.2f}, {res['lr_ci'][1]:.2f}]" if res.get('lr_ci') else ''
        print(f"| {res['check'].split(' ', 1)[1]} | {f('combined')} | {f('comparison')} | {res.get('lr_shrunk')}{ci} | "
              f"{res.get('proposed_points')} {res.get('proposed_points_ci') or ''} | {res['decision']} |")


def curve(rows, measure, size_like=False, two_range=(), counter=()):
    d = Data(rows, measure)
    print(f'{int(d.lab.sum())} labelled records with a value ({d.nc} cases), {int((~d.lab).sum())} comparisons, {d.nb} buyers')
    out = {'labelled': int(d.lab.sum()), 'cases': d.nc, 'comparisons': int((~d.lab).sum()), 'buyers': d.nb, 'cv': {}}

    print('\nCross-validated balanced log-loss by number of bins (lower is better):\n')
    print('| K asked | Bins after merging | Mean loss | SE |')
    print('|---|---|---|---|')
    for k in KS:
        edges = d.edges(np.arange(1, k) / k)
        m, se, _ = cv(d, d.cells(edges), len(edges) + 1)
        out['cv'][k] = {'bins': len(edges) + 1, 'loss': m, 'se': se, 'edges': edges.tolist()}
        print(f'| {k} | {len(edges) + 1} | {m:.4f} | {se:.4f} |')
    valid = {k: v for k, v in out['cv'].items() if np.isfinite(v['loss'])}
    if not valid:
        print('\nFewer than two scorable folds: no bins.')
        return out
    best = min(valid.values(), key=lambda v: v['loss'])
    chosen = min(k for k, v in valid.items() if v['loss'] <= best['loss'] + best['se'])
    out['chosen_k'] = chosen
    edges = out['cv'][chosen]['edges']
    print(f'\nChosen K = {chosen} (smallest within one SE of the best, {best["loss"]:.4f} + {best["se"]:.4f})\n')
    bounds = [-np.inf] + edges + [np.inf]
    named = [(f'[{fmt_x(lo) if lo > -np.inf else "min"}, {fmt_x(hi) if hi < np.inf else "max"})', lo, hi)
             for lo, hi in zip(bounds, bounds[1:])]
    out['bins'] = rated(rows, measure, named)
    table(out['bins'])

    sizes = d.size_reweight() if size_like else None
    if sizes:
        print(f"\nSize-like: comparisons reweighted within buyer to the labels' value bands (labels / {bc.OVERPRICING}); "
              f"bands labels {sizes['label_bands']}, comparisons {sizes['comparison_bands']}")
    pct = np.unique(np.quantile(d.comp_x, np.arange(1, 100) / 100))
    cell, ncell = d.cells(pct), len(pct) + 1
    bound = lambda i, lower: (-np.inf if i == 0 else float(pct[i - 1])) if lower else (np.inf if i == ncell else float(pct[i - 1]))
    m, per_fold = cv_range(d, cell, ncell)
    ci, cj = np.unravel_index(np.argmin(m), m.shape)
    # Gate (amendment 2026-10-25, after the first collusion ranges): nested, so the choice is not scored on the data
    # that chose it. Each fold picks its range on its training part; that range's held-out loss must beat "no split"
    # (log 2, an uninformative prediction) by more than one standard error over the folds.
    folds = [best_range(d, cell, ncell, mask=d.fold != k) for k in range(FOLDS)]
    one_gain_by_fold = {k: np.log(2) - f[i, j] for k, (f, (i, j)) in enumerate(zip(per_fold, folds)) if f is not None}
    gain = np.array(list(one_gain_by_fold.values()))
    gain_mean = float(gain.mean()) if len(gain) else float('nan')
    gain_se = float(gain.std(ddof=1) / np.sqrt(len(gain))) if len(gain) > 1 else float('nan')
    accepted = bool(np.isfinite(gain_mean) and np.isfinite(gain_se) and gain_mean > gain_se)
    rng = np.random.default_rng(20261025)
    boot = []
    for _ in range(BOOT_CUT):
        cm = np.bincount(rng.integers(0, d.nc, d.nc), minlength=d.nc).astype(float)
        bm = np.bincount(rng.integers(0, d.nb, d.nb), minlength=d.nb).astype(float)
        boot.append(best_range(d, cell, ncell, cm[np.maximum(d.case, 0)], bm[d.buyer]))
    lo, hi = bound(ci, True), bound(cj, False)
    show = lambda a, b: f'[{fmt_x(a) if a > -np.inf else "min"}, {fmt_x(b) if b < np.inf else "max"})'
    def pcts(v):  # open ends (min / max) counted apart: percentiles over the finite ones
        v = np.array(v)
        f = v[np.isfinite(v)]
        return (np.percentile(f, [2.5, 50, 97.5]) if len(f) else np.full(3, np.nan)), float(np.mean(~np.isfinite(v)))
    (qlo, open_lo), (qhi, open_hi) = pcts([bound(i, True) for i, _ in boot]), pcts([bound(j, False) for _, j in boot])
    out['range'] = {'cv_best': [lo, hi], 'cv_loss': float(m[ci, cj]), 'gain': gain_mean, 'gain_se': gain_se, 'accepted': accepted,
                    'folds': [[bound(i, True), bound(j, False)] for i, j in folds],
                    'bootstrap_lower_2.5_50_97.5': qlo.tolist(), 'bootstrap_upper_2.5_50_97.5': qhi.tolist(), 'bootstrap_open_lower': open_lo,
                    'bootstrap_open_upper': open_hi, 'size_bands': sizes}
    verdict = 'accepted' if accepted else 'NOT accepted: no better than no split, 0 points'
    print(f'\nOne range (cross-validated): {measure} in {show(lo, hi)}; nested held-out gain over no split {gain_mean:.4f} '
          f'(SE {gain_se:.4f}): {verdict}; per training fold '
          f'{", ".join(show(bound(i, True), bound(j, False)) for i, j in folds)}; bootstrap ({BOOT_CUT}): lower bound open (min) in '
          f'{open_lo:.0%}, else median {fmt_x(qlo[1])} [{fmt_x(qlo[0])}, {fmt_x(qlo[2])}]; upper bound open (max) in {open_hi:.0%}, '
          f'else median {fmt_x(qhi[1])} [{fmt_x(qhi[0])}, {fmt_x(qhi[2])}]\n')
    named = [(f'{show(lo, hi)} (cross-validated range)', lo, hi)]
    named += [(f'>= {fmt_x(c)} (former cut-off, reference)', c, np.inf) for c in REFERENCE_CUTS.get(measure, [])]
    out['range']['rated'] = rated(rows, measure, named)
    if not accepted:
        out['range']['rated'][0]['decision'] = 'no points (range not accepted)'
    table(out['range']['rated'])
    vc = value_controlled(d, lo, hi, f'{measure} range')
    out['range']['value_controlled'] = vc
    if vc:
        role = 'decision: size-like' if size_like else 'reported'
        fell = f" ({vc['fell_back']} labels fell back to no control)" if vc['fell_back'] else ''
        print(f"\nValue-band control ({role}): observed {vc['observed']:.1f} / expected {vc['expected']:.1f}, "
              f"LR {vc['lr']:.2f} [{vc['lr_ci'][0]:.2f}, {vc['lr_ci'][1]:.2f}] -> {vc['points'] if accepted else 0:g} points{fell}"
              f"{'' if accepted else ' (range not accepted)'}")
    if measure in two_range:
        out['two_ranges'] = two_ranges(d, rows, measure, one_gain_by_fold)
    if measure in counter:
        out['counter_range'] = counter_range(d, rows, measure)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--measures', default='PRICE-RATIO', help=f'comma-separated, of {", ".join(MEASURES)}')
    p.add_argument('--db', type=Path, default=lc.BASE / 'opnstd.sqlite')
    p.add_argument('--buyer', choices=('contract', 'demand'), default='contract')
    p.add_argument('--family', choices=('collusion', 'corruption', 'both'), default='collusion')
    p.add_argument('--court-links', type=Path, default=lc.BASE / 'prec/extract/links.jsonl',
                   help='corruption labels in the court-matcher format (bai/links.jsonl for audit findings)')
    p.add_argument('--bids', type=Path, default=lc.BASE / 'bid-features-2026-10-24.sqlite',
                   help='tools/korea-bid-features.py output, for FLOOR-GAP')
    p.add_argument('--two-ranges', default='', help='measures that also get the two-range test (plan 2026-10-25: audit PRICE-RATIO)')
    p.add_argument('--counter', default='', help='measures that also get a counter-range (plan 2026-10-25)')
    p.add_argument('--json', type=Path)
    args = p.parse_args()
    names = args.measures.split(',')
    two = args.two_ranges.split(',') if args.two_ranges else ()
    counters = args.counter.split(',') if args.counter else ()
    rows, key_col, _ = lc.prepare(args, make_checks(names, args.bids))
    every = lambda c: True
    sets = {'weighted, all linked tenders, all contracts (decision basis)': lambda: rows(every, True),
            'weighted, one per case, all contracts (robustness)': lambda: lc.one_per_case(rows(every, True))}
    out = {'family': args.family, 'buyer': key_col, 'measures': {}}
    for name, build in sets.items():
        rs = build()
        for measure in names:
            print(f'\n## {measure}, {args.family}: {name}\n', flush=True)
            out['measures'].setdefault(measure, {})[name] = curve(rs, measure, MEASURES[measure][1], two, counters)
        del rs
    if args.json:
        args.json.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float) + '\n')


if __name__ == '__main__':
    main()
