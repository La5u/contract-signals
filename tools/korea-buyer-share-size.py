#!/usr/bin/env python3
"""Research only: are the Korean size-related checks (G3 buyer share, N4 supplier dependence) more than size?

Same rows as the decision rule in tools/korea-label-checks.py (all linked labelled tenders, weighted by court
outcome, buyer = contracting office; `--family corruption` for the court-conviction labels, 2026-11-02). Size control as for Ukraine and Colombia (research/calibration/
bias-controls-plan.md): the comparisons' rate in each value band, weighted by the rigged contracts' band mix
(direct standardisation, tools/ukraine-buyer-share-size.py). Bands fixed before this ran: the Colombian scheme,
comparison-value percentiles 50/80/90/95/98/99 (KRW, original contract amount). Points basis: rigged contracts
banded at value / 1.3 (owner, 2026-10-20: prices assumed inflated x1.3); the uninflated basis is reported.
K6 (award >= 95 % of reserve) is reported as a sensitivity, and so are the bid-level checks that earned points (B2, B4,
B5; bid features from tools/korea-bid-features.py, `--bids`). Changes no score, weight or dataset.
"""
import argparse
import bisect
import json
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load  # noqa: E402

ko = load('korea_checks', 'tools/korea-label-checks.py')
size = load('ua_size', 'tools/ukraine-buyer-share-size.py')
pp = size.pp
CHECKS = ['G3 buyer share >= 5 %', 'N4 supplier dependence >= 25 %', 'G4 concentration', 'K5 restricted competition',
          'K6 award >= 95 % of reserve', 'B2 two or three bids', 'B4 low bid dispersion', 'B5 large first gap',
          'BID-COUNT 2', 'BID-VALID only one valid of 2+', 'B8 exact floor hit', 'B9 shared CEO', 'G5 3+ changes',
          'UA-C11 price increase', *ko.PRICE_CHECKS]
QUANTILES = (0.5, 0.8, 0.9, 0.95, 0.98, 0.99)
NAMES = ['<p50', 'p50-80', 'p80-90', 'p90-95', 'p95-98', 'p98-99', '>=p99']


def decision_rows(db, bids_path=None, family='collusion', court_links=None):
    """The rows of 'weighted, all linked tenders, all contracts' in korea-label-checks.py (its prepare(), so the
    labels, weights and comparisons are the same), with each contract's value."""
    args = argparse.Namespace(db=db, buyer='contract', family=family,
                              court_links=court_links or ko.BASE / 'prec/extract/links.jsonl')

    def make_checks(contracts):
        base = ko.build_checks(contracts, bids=ko.Bids(bids_path) if bids_path and bids_path.exists() else None)
        # The yearly totals behind G3 and N4, as build_checks() sums them (original contracts only), so that deflate()
        # can recompute both shares with a rigged contract's amount taken as inflated.
        total, by_supplier = Counter(), Counter()
        for c in contracts.values():
            if c.get('original', True):
                total[(c['buyer'], c['year'])] += c['amount']
                if c['supplier']:
                    by_supplier[(c['buyer'], c['year'], c['supplier'])] += c['amount']
        return lambda c: {**base(c), '_value': c['amount'] or None,
                          '_shares': (c['amount'], total[(c['buyer'], c['year'])],
                                      by_supplier[(c['buyer'], c['year'], c['supplier'])] if c['supplier'] else None)}

    rows, _, _ = ko.prepare(args, make_checks)
    return [dict(r, value=r['checks']['_value']) for r in rows(lambda c: True, True)]


def deflate(r, factor):
    """A rigged row as if its price were not inflated: value / factor, and G3 and N4 recomputed with that amount in
    the office's yearly total (Sol's review, 2026-11-02: only the band moved before, the share signals kept the
    inflated amount). The office's other rigged contracts are not known, so they stay as published."""
    a, total, supplier = r['checks']['_shares']
    if not a or not total:
        return dict(r, value=r['value'] and r['value'] / factor)
    a2 = a / factor
    t2 = total - a + a2
    ch = dict(r['checks'])
    g3, n4 = 'G3 buyer share >= 5 %', 'N4 supplier dependence >= 25 %'
    if ch[g3]['status'] in ('signal', 'clear'):
        ch[g3] = ko.status(a2 / t2 >= 0.05)
    if supplier is not None and ch[n4]['status'] in ('signal', 'clear'):
        ch[n4] = ko.status((supplier - a + a2) / t2 >= 0.25)
    return dict(r, value=r['value'] / factor, checks=ch)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--db', type=Path, default=ko.BASE / 'opnstd.sqlite')
    p.add_argument('--bids', type=Path, default=ko.BASE / 'bid-features-2026-11-02.sqlite')
    p.add_argument('--family', choices=('collusion', 'corruption', 'both'), default='collusion')
    p.add_argument('--court-links', type=Path, default=ko.BASE / 'prec/extract/links.jsonl')
    p.add_argument('--json')
    args = p.parse_args(argv)
    rows = decision_rows(args.db, args.bids, args.family, args.court_links)
    values = sorted(r['value'] for r in rows if 'comparison' in r['groups'] and r['value'])
    edges = [values[int(q * len(values))] for q in QUANTILES]
    band = lambda v: None if not v else NAMES[bisect.bisect_right(edges, v)]
    plain = [dict(r, band=band(r['value'])) for r in rows]
    deflated = [deflate(r, size.INFLATION) if 'combined' in r['groups'] else r for r in plain]
    inflated = [dict(r, band=band(r['value'])) for r in deflated]
    out = {'edges_krw': edges, 'quantiles': QUANTILES, 'checks': {}}
    print(f"{sum('combined' in r['groups'] for r in rows)} rigged rows, {sum('comparison' in r['groups'] for r in rows)} comparisons")
    print(f"Comparison value edges (KRW) at {QUANTILES}: {[f'{e:,.0f}' for e in edges]}")
    print(f"Rigged band mix: {Counter(r['band'] for r in plain if 'combined' in r['groups'])}\n")
    print('| Basis | Hit rate, rigged | Comparisons | LR shrunk [95 %] | LR at 25th pct | Decision points |')
    print('|---|---|---|---|---|---|')
    for check in CHECKS:
        res = {'unadjusted': pp.analyse(plain, check), 'size_standardised': size.standardise(plain, check, NAMES),
               'size_standardised_inflation': dict(size.standardise(inflated, check, NAMES) or {}, inflation=size.INFLATION),
               'size_smooth': size.standardise_smooth(plain, check),
               'size_smooth_inflation': dict(size.standardise_smooth(deflated, check) or {}, inflation=size.INFLATION)}
        res['within_band'] = {b: pp.analyse([r for r in plain if r['band'] == b], check) for b in NAMES}
        out['checks'][check] = res
        print(size.line(f'{check} unadjusted', res['unadjusted']))
        print(size.line(f'{check} size-standardised', res['size_standardised']))
        print(size.line(f'{check} size-standardised, rigged values / {size.INFLATION} (points basis)', res['size_standardised_inflation']))
        print(size.line(f'{check} smooth size control (no bands)', res['size_smooth']))
        print(size.line(f'{check} smooth, rigged values / {size.INFLATION} (points basis)', res['size_smooth_inflation']))
        for b, r in res['within_band'].items():
            c, k = r['combined'], r['comparison']
            if c['buyers']:
                print(f"| {check} within {b} | {c['tender_hits']}/{c['tenders']} ({c['buyers']} buyers) | {k['rate'] * 100:.1f}% | {r.get('lr_shrunk')} | | |")
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1, default=list) + '\n')


if __name__ == '__main__':
    main()
