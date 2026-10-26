#!/usr/bin/env python3
"""Does the explorer's Korean index rank KFTC-rigged tenders above the same offices' other contracts?

Research only (owner 2026-10-25: "run the check" before investigating leads). Each check was calibrated alone; the
index adds family maxima, which assumes the families are separate evidence. This scores the calibration's own label
and comparison rows (tools/korea-label-checks.py prepare(), collusion family, contracting office) with the site's rules
(checks-national.js KR_CHECKS, scoring.js getScoreBreakdown) and reports, per index band, the share of rigged tenders
against the share of comparisons, buyer-weighted as the calibration weights rates, with buyer-bootstrap intervals.

In-sample: the points were chosen on these labels, so the separation is optimistic. Rigged tenders more often have a
bid opening on file (their label years were downloaded in full); the B checks then add points that comparisons
without an opening cannot get, so the bands are also reported within rows whose opening was found.

  python3 tools/korea-index-check.py [--json out.json]
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load  # noqa: E402

ko = load('korea_checks', 'tools/korea-label-checks.py')

# checks-national.js KR_CHECKS (2026-10-26): check name -> (family, points when signal).
NEW = {'B2 two or three bids': ('competition', 12.1), 'B5 large first gap': ('competition', 11.4),
       'B7 same-minute bids': ('competition', 2.5), 'B4 low bid dispersion': ('competition', 0.9),
       'K5 restricted competition': ('competition', 3.7),
       'N4 supplier dependence >= 25 %': ('concentration', 9.2), 'G3 buyer share >= 5 %': ('concentration', 8.4),
       'G4 concentration': ('concentration', 7.7)}
K6 = 'K6 award >= 95 % of reserve'
K7, B12 = ko.PRICE_CHECKS
BANDS = [(0, 0), (0.1, 19.9), (20, 29.9), (30, 39.9), (40, 100)]
THRESHOLDS = [10, 20, 30, 40]


def index(checks, version):
    st = lambda k: checks[k]['status']
    fam = defaultdict(float)
    for k, (f, w) in NEW.items():
        if st(k) == 'signal':
            fam[f] = max(fam[f], w)
    if version == 'old':  # 92d9595: K6 >= 95 % 12.7 in the price family, no negative points
        if st(K6) == 'signal':
            fam['price'] = 12.7
    elif st(B12) in ('signal', 'clear'):
        fam['price'] = 18.0 if st(B12) == 'signal' else -11.0
    elif st(K7) == 'signal':
        fam['price'] = 15.5
    return round(max(0.0, min(100.0, sum(fam.values()))), 1)


def per_buyer(rows, group, test):
    """Per office: (weight, weighted share of its group rows passing test), as propose-indicator-points.weighted."""
    per = defaultdict(list)
    for r in rows:
        if group in r['groups']:
            per[r['buyer']].append((test(r), r.get('weight', 1)))
    return {b: (max(w for _, w in v), sum(w * h for h, w in v) / sum(w for _, w in v)) for b, v in per.items()}


def share_of(pb, buyers=None):
    """Buyer-weighted share over the given offices (a bootstrap draw may repeat one), all offices if None."""
    got = [pb[b] for b in (buyers if buyers is not None else pb) if b in pb]
    n = sum(bw for bw, _ in got)
    return sum(bw * rate for bw, rate in got) / n if n else None


def share(rows, group, test, buyers=None):
    """Buyer-weighted share of a group's rows passing test (propose-indicator-points.weighted's rule)."""
    return share_of(per_buyer(rows, group, test), buyers)


def auc(rows):
    """Plain probability that a rigged tender outscores a comparison (ties count half), label weights applied."""
    pos = [(r['score'], r.get('weight', 1)) for r in rows if 'combined' in r['groups']]
    neg = defaultdict(float)
    for r in rows:
        if 'comparison' in r['groups']:
            neg[r['score']] += r.get('weight', 1)
    total = sum(neg.values())
    num = sum(w * (sum(v for k, v in neg.items() if k < s) + neg.get(s, 0) / 2) for s, w in pos)
    return num / (sum(w for _, w in pos) * total)


def report(rows, title, reps=500):
    lab = [r for r in rows if 'combined' in r['groups']]
    out = {'title': title, 'labelled': len(lab), 'labelled_buyers': len({r['buyer'] for r in lab}),
           'cases': len({r['case'] for r in lab}), 'comparisons': sum('comparison' in r['groups'] for r in rows)}
    print(f'\n### {title}: {out["labelled"]} rigged tenders ({out["labelled_buyers"]} offices, {out["cases"]} cases), '
          f'{out["comparisons"]} comparisons\n')
    buyers_l = sorted({r['buyer'] for r in lab})
    buyers_c = sorted({r['buyer'] for r in rows if 'comparison' in r['groups']})
    rnd = random.Random(1)
    draws = [([rnd.choice(buyers_l) for _ in buyers_l], [rnd.choice(buyers_c) for _ in buyers_c]) for _ in range(reps)]
    for version in ('new', 'old'):
        key = version  # rows keep both: r['new'], r['old']
        for r in rows:
            r['score'] = r[key]
        print(f'Index {version}: AUC {auc(rows):.3f} (chance 0.5)\n')
        print('| Index | Rigged | Comparisons | Ratio [95 %] |')
        print('|---|---|---|---|')
        res = []
        tests = [(f'{lo:g}-{hi:g}' if lo != hi else '0', lambda r, lo=lo, hi=hi: lo <= r['score'] <= hi) for lo, hi in BANDS]
        tests += [(f'>= {t}', lambda r, t=t: r['score'] >= t) for t in THRESHOLDS]
        for name, test in tests:
            pl, pc = per_buyer(rows, 'combined', test), per_buyer(rows, 'comparison', test)
            a, b = share_of(pl), share_of(pc)
            ratios = sorted(x / y for x, y in ((share_of(pl, bl), share_of(pc, bc))
                                              for bl, bc in draws) if x is not None and y)
            ci = (ratios[int(0.025 * len(ratios))], ratios[int(0.975 * len(ratios)) - 1]) if ratios else None
            ratio = a / b if b else None
            print(f'| {name} | {a:.1%} | {b:.2%} | {f"{ratio:.1f}" if ratio else "NA"}'
                  f'{f" [{ci[0]:.1f}, {ci[1]:.1f}]" if ci else ""} |')
            res.append({'band': name, 'rigged': a, 'comparisons': b, 'ratio': ratio, 'ci': ci})
        print()
        out[version] = {'auc': auc(rows), 'bands': res}
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--db', type=Path, default=ko.BASE / 'opnstd.sqlite')
    p.add_argument('--bids', type=Path, default=ko.BASE / 'bid-features.sqlite')
    p.add_argument('--json', type=Path)
    args = p.parse_args()
    args.buyer, args.family, args.court_links = 'contract', 'collusion', None

    def make_checks(contracts):
        return ko.build_checks(contracts, bids=ko.Bids(args.bids) if args.bids.exists() else None)

    rows_of, _, _ = ko.prepare(args, make_checks)
    rows = rows_of(lambda c: True, True)
    for r in rows:  # keep only what the index needs, then drop the full check dicts
        r['new'], r['old'] = index(r['checks'], 'new'), index(r['checks'], 'old')
        r['score'] = r['new']
        r['opening'] = r['checks']['B2 two or three bids']['status'] in ('signal', 'clear')
        del r['checks']
    sets = {'all linked tenders (decision rule)': rows,
            'one per case': ko.one_per_case(rows),
            'bid opening found': [r for r in rows if r['opening']]}
    opened = {g: share(rows, g, lambda r: r['opening']) for g in ('combined', 'comparison')}
    print(f'\nBid opening found (buyer-weighted): rigged {opened["combined"]:.1%}, comparisons {opened["comparison"]:.1%}')
    out = {'opening_found': opened, 'sets': [report(rs, name) for name, rs in sets.items()]}
    if args.json:
        args.json.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
