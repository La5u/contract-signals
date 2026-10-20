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
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
                per[g][r['buyer']][r['band']].append(r['checks'][check]['status'] == 'signal')

    def estimate(drawn):
        # positives: each buyer weight 1 over its rows (as pp.weighted); band mix from the same weights
        h1 = n1 = 0.0
        mix = defaultdict(float)
        for b in drawn:
            bands = per['combined'].get(b)
            if not bands:
                continue
            k = sum(len(v) for v in bands.values())
            h1 += sum(sum(v) for v in bands.values()) / k
            n1 += 1
            for band_, v in bands.items():
                mix[band_] += len(v) / k
        hits, n = defaultdict(float), defaultdict(float)
        n0 = 0
        for b in drawn:
            bands = per['comparison'].get(b)
            if not bands:
                continue
            n0 += 1
            for band_, v in bands.items():
                hits[band_] += sum(v) / len(v)
                n[band_] += 1
        if not n1 or not n0:
            return None
        rate0 = sum(mix[b] / n1 * (hits[b] / n[b]) for b in mix if n[b])
        return pp.shrunk_lr(h1, n1, rate0 * n0, n0), h1, n1, rate0, n0, {b: round(mix[b] / n1, 3) for b in names}

    buyers = sorted({r['buyer'] for r in known})
    lr, h1, n1, rate0, n0, mix = estimate(buyers)
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
    analysis = [dict(r, band=band(value_of[r['id']]), checks={R1: r['checks'][R1]}) for r in rel.census_rows(rows, census, {})]

    out = {'unadjusted': pp.analyse(analysis, R1)}
    out['size_standardised'] = standardise(analysis)
    inflated = [dict(r, band=band(None if value_of[r['id']] is None else value_of[r['id']] / INFLATION)) if 'combined' in r['groups'] else r for r in analysis]
    out['size_standardised_inflation'] = dict(standardise(inflated), inflation=INFLATION)
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
    for h, res in out['size_standardised_halves'].items():
        print(line(f'  A, {h} half', res))
    for b, res in out['within_band'].items():
        print(line(f'R1 within {b} (B)', res) if 'check' in res else f"| R1 within {b} (B) | too few buyers ({res['too_few_buyers']}) | | | | |")
    print(line(f"Size alone, value >= UAH {out['size_only']['cut_uah']:,.0f} (C)", out['size_only']))
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
