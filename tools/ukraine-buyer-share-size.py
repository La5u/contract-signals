#!/usr/bin/env python3
"""Research only: is the Ukrainian buyer-share check (R1, ua-buyer-share) more than a size effect?

Prosecutors favour large amounts, and a tender that is >= 5 % of its buyer's year is usually a large tender,
so the R1 likelihood ratio may partly measure what gets prosecuted. Same rows as R1 in
tools/ukraine-relative-candidates.py (convicted tenders against the census of the same buyer-years);
each row also gets its UAH value band. Rules fixed in research/calibration/bias-controls-plan.md:
  A  size-standardised: the comparisons' R1 rate in each value band, weighted by the convicted tenders' band
     mix (direct standardisation); LR and decision points as in tools/propose-indicator-points.py;
  B  within each value band (bands with at least MIN_BUYERS convicted buyers);
  C  size alone: "value >= V", V the census value whose convicted hit rate is closest to R1's, unstandardised;
     what a pure size check would score.
Changes no score, weight or dataset.
"""
import argparse
import bisect
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


rel = load('relative', 'tools/ukraine-relative-candidates.py')
pp, cand, census_mod, vc, bc = rel.pp, rel.cand, rel.census_mod, rel.vc, rel.bc
R1 = 'R1 buyer-share'
# Owner, 2026-10-20: corruption may have inflated convicted contracts' prices; points assume x1.3, so convicted
# tenders are banded at value / 1.3 (the uninflated basis is reported too).
INFLATION = 1.3
# UAH; edges fixed in the plan before this ran (open-tender thresholds 200,000 and 1,500,000 fall inside bands)
EDGES = [50_000, 200_000, 1_000_000, 5_000_000, 20_000_000]
NAMES = ['< 50k', '50k-200k', '200k-1M', '1M-5M', '5M-20M', '>= 20M']


def band(value):
    return None if value is None else NAMES[bisect.bisect_right(EDGES, value)]


def values(rows, census):
    """Row id -> UAH value, read exactly as census_rows() reads it."""
    listed, out = census['tenders'], {}
    for r in rows:
        t = listed.get(r['tenderID'])
        out[r['id']] = rel.uah(t.get('value')) if t else (r.get('amount') if r.get('currency') == 'UAH' else None)
    for tid, t in listed.items():
        out.setdefault(tid, rel.uah(t.get('value')))
    return out


def standardise(analysis, check=R1, names=NAMES, seed=pp.SEED):
    """A: direct standardisation. Comparison rate = sum over bands of P(band | convicted) x the comparisons'
    buyer-weighted R1 rate in that band; LR shrunk as in propose-indicator-points; 95 % interval and the
    decision quantile by resampling buyers. (A first version reweighted rows inside each buyer; the weights
    cancel for buyers whose tenders sit in one band, so it under-adjusted. Replaced before any decision.)"""
    known = [r for r in analysis if r['band'] and r['checks'][check]['status'] in ('signal', 'clear')]
    per = {g: defaultdict(lambda: defaultdict(list)) for g in ('combined', 'comparison')}
    for r in known:
        for g in per:
            if g in r['groups']:
                per[g][r['buyer']][r['band']].append((r['checks'][check]['status'] == 'signal', r.get('weight', 1)))

    def estimate(drawn):
        # positives as pp.weighted: a buyer counts with the largest label weight of its rows, spread over its rows by
        # their weights (2026-11-02: label weights were ignored here before; every weight 1 gives the old result);
        # band mix from the same weights
        h1 = n1 = 0.0
        mix = defaultdict(float)
        for b in drawn:
            bands = per['combined'].get(b)
            if not bands:
                continue
            k = sum(w for v in bands.values() for _, w in v)
            if not k:
                continue
            bw = max(w for v in bands.values() for _, w in v)
            h1 += bw * sum(w * h for v in bands.values() for h, w in v) / k
            n1 += bw
            for band_, v in bands.items():
                mix[band_] += bw * sum(w for _, w in v) / k
        hits, n = defaultdict(float), defaultdict(float)
        n0 = 0
        for b in drawn:
            bands = per['comparison'].get(b)
            if not bands:
                continue
            n0 += 1
            for band_, v in bands.items():
                hits[band_] += sum(h for h, _ in v) / len(v)
                n[band_] += 1
        if not n1 or not n0:
            return None
        rate0 = sum(mix[b] / n1 * (hits[b] / n[b]) for b in mix if n[b])
        return pp.shrunk_lr(h1, n1, rate0 * n0, n0), h1, n1, rate0, n0, {b: round(mix[b] / n1, 3) for b in names}

    buyers = sorted({r['buyer'] for r in known})
    first = estimate(buyers)
    if first is None:
        return None
    lr, h1, n1, rate0, n0, mix = first
    import random
    rng = random.Random(f'{seed}-{check}-standardised')
    boot = sorted(x[0] for x in (estimate(rng.choices(buyers, k=len(buyers))) for _ in range(pp.BOOT)) if x and x[0])
    q = lambda f: boot[min(len(boot) - 1, int(f * len(boot)))]
    conf = min(q(pp.CONFIDENT_Q), lr)
    return {'combined': {'rate': round(h1 / n1, 3), 'buyers': n1, 'tender_hits': sum(r['checks'][check]['status'] == 'signal' for r in known if 'combined' in r['groups']),
                         'tenders': sum('combined' in r['groups'] for r in known)},
            'comparison': {'rate': round(rate0, 3), 'buyers': n0}, 'band_mix_convicted': mix,
            'lr_shrunk': round(lr, 3), 'lr_ci': [round(q(0.025), 3), round(q(0.975), 3)], 'lr_confident': round(conf, 3),
            'decision_points': pp.points(conf) if n1 >= pp.MIN_BUYERS else 0.0}


GRID = 400                                        # log-value grid points for the smooth size control
MASSES = (2, 5, 10, 20, 50, 100, 200, 500)  # adaptive kernel: comparison buyers' weight it must cover, searched


def standardise_smooth(analysis, check=R1, seed=pp.SEED):
    """A without value bands (plan amendment 2026-10-30): the comparisons' buyer-weighted signal rate as a smooth
    function of log value (local-linear regression with a Gaussian kernel whose width at each value covers a set comparison weight, in buyers, so the
    rate is defined everywhere; that weight chosen by leave-one-out likelihood on the comparisons), read at
    each positive row's own value and averaged with the positives' buyer weights. Rows carry 'value' (positives
    already divided by any inflation factor). Shrinkage, interval and decision quantile as in standardise()."""
    import zlib
    import numpy as np
    known = [r for r in analysis if r.get('value') and r['value'] > 0 and
             r['checks'][check]['status'] in ('signal', 'clear')]
    if not any('combined' in r['groups'] for r in known) or not any('comparison' in r['groups'] for r in known):
        return None
    buyers = sorted({r['buyer'] for r in known})
    bidx = {b: i for i, b in enumerate(buyers)}
    logs = np.log([r['value'] for r in known])
    lo, hi = logs.min(), logs.max()
    cell = np.clip(((logs - lo) / (hi - lo or 1) * (GRID - 1)).round().astype(int), 0, GRID - 1)
    centre = lo + np.arange(GRID) * (hi - lo) / (GRID - 1)
    sides = {}
    # Each buyer counts with the largest label weight of its rows, spread over them by weight (pp.weighted; label
    # weights were ignored here before 2026-11-02, every weight 1 gives the old result).
    buyer_weight = np.zeros(len(buyers))
    for g in ('combined', 'comparison'):
        sel = [i for i, r in enumerate(known) if g in r['groups']]
        wt = lambda i: known[i].get('weight', 1) if g == 'combined' else 1
        per_buyer, top = Counter(), Counter()
        for i in sel:
            per_buyer[known[i]['buyer']] += wt(i)
            top[known[i]['buyer']] = max(top[known[i]['buyer']], wt(i))
        if g == 'combined':
            for b, v in top.items():
                buyer_weight[bidx[b]] = v
        sides[g] = (np.array([bidx[known[i]['buyer']] for i in sel], int), cell[sel],
                    np.array([top[known[i]['buyer']] * wt(i) / per_buyer[known[i]['buyer']] if per_buyer[known[i]['buyer']] else 0
                              for i in sel]),
                    np.array([known[i]['checks'][check]['status'] == 'signal' for i in sel], float))
    dist = np.abs(centre[:, None] - centre[None, :])
    near = np.argsort(dist, axis=1, kind='stable')
    step = (hi - lo) / (GRID - 1) or 1.0
    fixed_mass = np.bincount(sides['comparison'][1], sides['comparison'][2], GRID)
    cum = np.cumsum(fixed_mass[near], axis=1)
    def adaptive(m):
        k = np.minimum((cum < m).sum(1), GRID - 1)
        width = np.maximum(dist[np.arange(GRID), near[np.arange(GRID), k]], step)
        return np.exp(-0.5 * (dist / width[:, None]) ** 2)
    masses = [m for m in MASSES if m < fixed_mass.sum()] or [fixed_mass.sum() / 2]

    def local_linear(Kh, mass, hits, own=None):
        """Rate at every grid point by local-linear kernel regression (removes the bias a plain kernel average
        has where comparisons are denser on one side); own = (cells, weights, hits) to leave out, giving the rate
        at those rows without them."""
        x = centre
        s0, s1x, s2x = Kh @ mass, Kh @ (mass * x), Kh @ (mass * x * x)
        t0, t1x = Kh @ hits, Kh @ (hits * x)
        if own is None:
            s1, s2, t1 = s1x - x * s0, s2x - 2 * x * s1x + x * x * s0, t1x - x * t0
            out = (s2 * t0 - s1 * t1) / np.maximum(s0 * s2 - s1 * s1, 1e-300)
            flat = t0 / np.maximum(s0, 1e-300)
            return np.clip(np.where(s0 * s2 - s1 * s1 > 1e-12 * s0 * s0, out, flat), 0, 1)
        c, w, y = own
        xc = x[c]
        a0, a1x, a2x, b0, b1x = s0[c] - w, s1x[c] - w * xc, s2x[c] - w * xc * xc, t0[c] - w * y, t1x[c] - w * y * xc
        s1, s2, t1 = a1x - xc * a0, a2x - 2 * xc * a1x + xc * xc * a0, b1x - xc * b0
        det = a0 * s2 - s1 * s1
        out = (s2 * b0 - s1 * t1) / np.maximum(det, 1e-300)
        flat = b0 / np.maximum(a0, 1e-300)
        return np.clip(np.where(det > 1e-12 * a0 * a0, out, flat), 0, 1)
    kernels = {m: adaptive(m) for m in masses}

    # comparisons: as each buyer counts once inside each value band, here each row is weighted by 1 / its buyer's
    # kernel-weighted number of rows near its value, so every buyer counts about once at every value it has
    b0, c0, _, y0 = sides['comparison']
    order = np.argsort(b0, kind='stable')
    starts = np.flatnonzero(np.r_[True, np.diff(b0[order]) != 0])
    def local_weights(Kh):
        w = np.empty(len(b0))
        for lo_, hi_ in zip(starts, np.r_[starts[1:], len(order)]):
            idx = order[lo_:hi_]
            u_, inv, cnt = np.unique(c0[idx], return_inverse=True, return_counts=True)
            w[idx] = 1 / (Kh[np.ix_(u_, u_)] @ cnt)[inv]
        return w
    # width: leave-one-out Bernoulli likelihood of the comparison rows, each scored with its fixed buyer weight
    # (1 / the buyer's rows) so that the widths are compared on the same footing
    fixed = sides['comparison'][2]
    def loo(h):
        w0 = local_weights(kernels[h])
        hits, mass = np.bincount(c0, w0 * y0, GRID), np.bincount(c0, w0, GRID)
        rate = np.clip(local_linear(kernels[h], mass, hits, (c0, w0, y0)), 1e-6, 1 - 1e-6)
        return float((fixed * (y0 * np.log(rate) + (1 - y0) * np.log(1 - rate))).sum())
    width = max(masses, key=loo)
    K = kernels[width]
    w0 = local_weights(K)

    def estimate(times):
        b1, c1, w1, y1 = sides['combined']
        t1 = times[b1]
        n1 = float((times * buyer_weight).sum())
        if not n1:
            return None
        h1 = float((t1 * w1 * y1).sum())
        tc = times[b0]
        rate_at = local_linear(K, np.bincount(c0, tc * w0, GRID), np.bincount(c0, tc * w0 * y0, GRID))
        n0 = float((times * np.isin(np.arange(len(buyers)), b0)).sum())
        if not n0:
            return None
        rate0 = float((t1 * w1 * rate_at[c1]).sum() / (t1 * w1).sum())
        return pp.shrunk_lr(h1, n1, rate0 * n0, n0), h1, n1, rate0, n0

    lr, h1, n1, rate0, n0 = estimate(np.ones(len(buyers)))
    rng = np.random.default_rng(zlib.crc32(f'{seed}-{check}-smooth'.encode()))
    boot = sorted(x[0] for x in (estimate(np.bincount(rng.integers(0, len(buyers), len(buyers)), minlength=len(buyers))
                                          .astype(float)) for _ in range(pp.BOOT)) if x and x[0])
    q = lambda f: boot[min(len(boot) - 1, int(f * len(boot)))]
    conf = min(q(pp.CONFIDENT_Q), lr)
    return {'combined': {'rate': round(h1 / n1, 3), 'buyers': int(n1),
                         'tender_hits': sum(r['checks'][check]['status'] == 'signal' for r in known if 'combined' in r['groups']),
                         'tenders': sum('combined' in r['groups'] for r in known)},
            'comparison': {'rate': round(rate0, 3), 'buyers': int(n0)}, 'kernel_mass_buyers': width,
            'lr_shrunk': round(lr, 3), 'lr_ci': [round(q(0.025), 3), round(q(0.975), 3)], 'lr_confident': round(conf, 3),
            'decision_points': pp.points(conf) if n1 >= pp.MIN_BUYERS else 0.0}


def size_only(analysis, value_of):
    """C: the size cut whose convicted hit rate is closest to R1's; its unstandardised LR."""
    target = pp.analyse(analysis, R1)['combined']['rate']
    cuts = sorted({v for v in value_of.values() if v})
    best = None
    for q in [i / 100 for i in range(1, 100)]:
        v = cuts[int(q * (len(cuts) - 1))]
        rows = [dict(r, checks={'size': {'status': 'unknown' if value_of[r['id']] is None else
                                         'signal' if value_of[r['id']] >= v else 'clear'}}) for r in analysis]
        res = pp.analyse(rows, 'size')
        gap = abs(res['combined']['rate'] - target)
        if best is None or gap < best[0]:
            best = (gap, v, res)
    return dict(best[2], cut_uah=best[1])


def line(name, res):
    if not res or 'combined' not in res:
        return f'| {name} | no evaluable rows | | | | |'
    c, k = res['combined'], res['comparison']
    ci = f"[{res['lr_ci'][0]:.2f}, {res['lr_ci'][1]:.2f}]" if res.get('lr_ci') else ''
    return (f"| {name} | {c['rate'] * 100:.0f}% ({c['tender_hits']}/{c['tenders']}, {c['buyers']} buyers) | "
            f"{k['rate'] * 100:.1f}% | {res['lr_shrunk']} {ci} | {res.get('lr_confident')} | {res['decision_points']} |")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--cohort', default=str(rel.COHORT))
    p.add_argument('--census', default=str(rel.CENSUS))
    p.add_argument('--cache', default=str(vc.CACHE))
    p.add_argument('--json', help='write results here')
    args = p.parse_args(argv)
    rows = json.loads(gzip.open(args.cohort).read())['rows']
    saved = json.loads(gzip.open(args.census).read())
    f = bc.Fetcher(Path(args.cache).expanduser(), network=False, prior=0, opener=vc.opener)
    tenders, incomplete = census_mod.census(f, {tuple(x) for x in saved['buyer_years']})
    if len(tenders) != len(saved['tenders']) or incomplete:
        raise SystemExit(f'cached listings do not replay the census: {len(tenders)} vs {len(saved["tenders"])} tenders')
    census = {'buyer_years': saved['buyer_years'], 'tenders': tenders}
    value_of = values(rows, census)
    analysis = [dict(r, band=band(value_of[r['id']]), value=value_of[r['id']], checks={R1: r['checks'][R1]})
                for r in rel.census_rows(rows, census, {})]

    out = {'unadjusted': pp.analyse(analysis, R1)}
    out['size_standardised'] = standardise(analysis)
    inflated = [dict(r, band=band(None if value_of[r['id']] is None else value_of[r['id']] / INFLATION)) if 'combined' in r['groups'] else r for r in analysis]
    out['size_standardised_inflation'] = dict(standardise(inflated), inflation=INFLATION)
    deflated = [dict(r, value=r['value'] and r['value'] / INFLATION) if 'combined' in r['groups'] else r for r in analysis]
    out['size_smooth'] = standardise_smooth(analysis)
    out['size_smooth_inflation'] = dict(standardise_smooth(deflated), inflation=INFLATION)
    out['size_standardised_halves'] = {h: standardise([r for r in analysis if cand.half(r['buyer']) == h]) for h in ('learn', 'check')}
    known = [r for r in analysis if r['band'] and r['checks'][R1]['status'] in ('signal', 'clear')]
    pos = dict(Counter(r['band'] for r in known if 'combined' in r['groups']))
    cmp_ = dict(Counter(r['band'] for r in known if 'comparison' in r['groups']))
    out['band_counts'] = {'convicted': pos, 'comparison': cmp_}
    out['within_band'] = {}
    for b in NAMES:
        sub = [r for r in analysis if r['band'] == b]
        res = pp.analyse(sub, R1)
        out['within_band'][b] = res if res['combined']['buyers'] >= pp.MIN_BUYERS else {'too_few_buyers': res['combined']['buyers']}
    out['size_only'] = size_only(analysis, value_of)

    print(f"Value bands (tenders with an R1 status): convicted {pos}; comparisons {cmp_}")
    print(f"Convicted band mix (buyer-weighted): {out['size_standardised']['band_mix_convicted']}\n")
    print('| Basis | Hit rate, convicted | Comparisons | LR shrunk [95 %] | LR at 25th pct | Decision points |')
    print('|---|---|---|---|---|---|')
    print(line('R1 unadjusted', out['unadjusted']))
    print(line('R1 size-standardised (A)', out['size_standardised']))
    print(line(f'R1 size-standardised, convicted values / {INFLATION} (points basis)', out['size_standardised_inflation']))
    print(line('R1 smooth size control (no bands)', out['size_smooth']))
    print(line(f'R1 smooth size control, convicted values / {INFLATION} (points basis)', out['size_smooth_inflation']))
    for h, res in out['size_standardised_halves'].items():
        print(line(f'  A, {h} half', res))
    for b, res in out['within_band'].items():
        print(line(f'R1 within {b} (B)', res) if 'check' in res else f"| R1 within {b} (B) | too few buyers ({res['too_few_buyers']}) | | | | |")
    print(line(f"Size alone, value >= UAH {out['size_only']['cut_uah']:,.0f} (C)", out['size_only']))
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
