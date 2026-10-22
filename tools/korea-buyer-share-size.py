#!/usr/bin/env python3
"""Research only: are the Korean size-related checks (G3 buyer share, N4 supplier dependence) more than size?

Same rows as the decision rule in tools/korea-label-checks.py (all linked KFTC-rigged tenders, weighted by court
outcome, buyer = contracting office). Size control as for Ukraine and Colombia (research/calibration/
bias-controls-plan.md): the comparisons' rate in each value band, weighted by the rigged contracts' band mix
(direct standardisation, tools/ukraine-buyer-share-size.py). Bands fixed before this ran: the Colombian scheme,
comparison-value percentiles 50/80/90/95/98/99 (KRW, original contract amount). Points basis: rigged contracts
banded at value / 1.3 (owner, 2026-10-20: prices assumed inflated x1.3); the uninflated basis is reported.
K6 (award >= 95 % of reserve) is reported as a sensitivity. Changes no score, weight or dataset.
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
CHECKS = ['G3 buyer share >= 5 %', 'N4 supplier dependence >= 25 %', 'K6 award >= 95 % of reserve']
QUANTILES = (0.5, 0.8, 0.9, 0.95, 0.98, 0.99)
NAMES = ['<p50', 'p50-80', 'p80-90', 'p90-95', 'p95-98', 'p98-99', '>=p99']


def decision_rows(db):
    """The rows of 'weighted, all linked tenders, all contracts' in korea-label-checks.py, with each contract's value."""
    labels = ko.load_labels()
    fin_path = ko.BASE / 'ftc-suits/finality.json'
    finality = json.loads(fin_path.read_text()) if fin_path.exists() else {}
    versions, key_col = ko.scan(db, labels, 'contract')
    contracts = ko.contracts_from(versions, key_col)
    checks = ko.build_checks(contracts)
    members, reps = set(), {}
    for lab in labels.values():
        cs = [contracts[n] for n in lab['contracts'] if n in contracts]
        members |= {c['no'] for c in cs}
        cs = [c for c in cs if c['original']]  # as korea-label-checks.py: amendment-only records are no label
        if cs:
            reps.setdefault(max(cs, key=lambda c: (c['amount'], c['no']))['no'], lab)
    status = lambda case: (finality.get(case) or {}).get('status', 'none')
    buyer_years = {(contracts[n]['buyer'], contracts[n]['year']) for n in reps}
    out = []
    for c in contracts.values():
        if (c['buyer'], c['year']) not in buyer_years or not c['original']:
            continue
        lab = reps.get(c['no'])
        if c['no'] in members and not lab:
            continue
        w = ko.WEIGHTS[status(lab['case'])] if lab else 1.0
        ch = checks(c)
        base = {'id': c['no'], 'buyer': c['buyer'], 'value': c['amount'] or None, 'checks': ch}
        if lab and w > 0:
            out.append(dict(base, groups=['collusion', 'combined'], **({'weight': w} if w < 1 else {})))
        if not lab or w < 1:
            out.append(dict(base, groups=['comparison'], **({'weight': 1 - w} if lab else {})))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--db', type=Path, default=ko.BASE / 'opnstd.sqlite')
    p.add_argument('--json')
    args = p.parse_args(argv)
    rows = decision_rows(args.db)
    values = sorted(r['value'] for r in rows if 'comparison' in r['groups'] and r['value'])
    edges = [values[int(q * len(values))] for q in QUANTILES]
    band = lambda v: None if not v else NAMES[bisect.bisect_right(edges, v)]
    plain = [dict(r, band=band(r['value'])) for r in rows]
    inflated = [dict(r, band=band(r['value'] and r['value'] / size.INFLATION)) if 'combined' in r['groups'] else r for r in plain]
    out = {'edges_krw': edges, 'quantiles': QUANTILES, 'checks': {}}
    print(f"{sum('combined' in r['groups'] for r in rows)} rigged rows, {sum('comparison' in r['groups'] for r in rows)} comparisons")
    print(f"Comparison value edges (KRW) at {QUANTILES}: {[f'{e:,.0f}' for e in edges]}")
    print(f"Rigged band mix: {Counter(r['band'] for r in plain if 'combined' in r['groups'])}\n")
    print('| Basis | Hit rate, rigged | Comparisons | LR shrunk [95 %] | LR at 25th pct | Decision points |')
    print('|---|---|---|---|---|---|')
    for check in CHECKS:
        res = {'unadjusted': pp.analyse(plain, check), 'size_standardised': size.standardise(plain, check, NAMES),
               'size_standardised_inflation': dict(size.standardise(inflated, check, NAMES), inflation=size.INFLATION)}
        res['within_band'] = {b: pp.analyse([r for r in plain if r['band'] == b], check) for b in NAMES}
        out['checks'][check] = res
        print(size.line(f'{check} unadjusted', res['unadjusted']))
        print(size.line(f'{check} size-standardised', res['size_standardised']))
        print(size.line(f'{check} size-standardised, rigged values / {size.INFLATION} (points basis)', res['size_standardised_inflation']))
        for b, r in res['within_band'].items():
            c, k = r['combined'], r['comparison']
            if c['buyers']:
                print(f"| {check} within {b} | {c['tender_hits']}/{c['tenders']} ({c['buyers']} buyers) | {k['rate'] * 100:.1f}% | {r.get('lr_shrunk')} | | |")
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1, default=list) + '\n')


if __name__ == '__main__':
    main()
