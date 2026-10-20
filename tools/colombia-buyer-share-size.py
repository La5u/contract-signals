#!/usr/bin/env python3
"""Research only: is the Colombian buyer-share check (CO4, 14 points) more than a size effect?

Same rows as CO4 in tools/colombia-conviction-checks.py (all labelled contracts, the points basis). Size control
as for Ukraine (research/calibration/bias-controls-plan.md): the comparisons' CO4 rate in each value band,
weighted by the convicted contracts' band mix (direct standardisation, tools/ukraine-buyer-share-size.py).
Bands: quintiles of the comparison contracts' values (COP), since the UAH bands do not transfer. With 10
convicted buyers the within-band rates are reported but too thin to decide. Changes no score, weight or dataset.
"""
import argparse
import bisect
import importlib.util
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


co = load('colombia', 'tools/colombia-conviction-checks.py')
size = load('ua_size', 'tools/ukraine-buyer-share-size.py')
pp = size.pp
CO4 = 'CO4 buyer share >= 5 %'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--json')
    args = p.parse_args(argv)
    records = [json.loads(l) for l in co.LEADS.read_text().splitlines() if l.strip().startswith('{"lead')]
    records = [r for r in records if r.get('outcome') in ('conviction', 'plea') and r.get('label') in ('final', 'first-instance')]
    years = co.load_years()
    labelled, _ = co.resolve(records, years)
    value_of = {x['uid']: co.num(x.get('cuantia_contrato')) for rows in years.values() for x in rows}
    rows = co.analysis_rows(years, labelled, False)
    cmp_values = sorted(value_of[r['id']] for r in rows if 'comparison' in r['groups'] and value_of[r['id']])
    edges = [cmp_values[int(q * len(cmp_values))] for q in (0.2, 0.4, 0.6, 0.8)]
    names = [f'Q{i + 1}' for i in range(5)]
    band = lambda v: None if not v else names[bisect.bisect_right(edges, v)]
    analysis = [dict(r, band=band(value_of[r['id']]), checks={CO4: r['checks'][CO4]}) for r in rows]
    out = {'edges_cop': edges, 'unadjusted': pp.analyse(analysis, CO4), 'size_standardised': size.standardise(analysis, CO4, names)}
    out['within_band'] = {b: pp.analyse([r for r in analysis if r['band'] == b], CO4) for b in names}
    print(f"Comparison value quintile edges (COP): {[f'{e:,.0f}' for e in edges]}")
    print(f"Convicted band mix: {out['size_standardised']['band_mix_convicted']}\n")
    print('| Basis | Hit rate, convicted | Comparisons | LR shrunk [95 %] | LR at 25th pct | Decision points |')
    print('|---|---|---|---|---|---|')
    print(size.line('CO4 unadjusted', out['unadjusted']))
    print(size.line('CO4 size-standardised', out['size_standardised']))
    for b, res in out['within_band'].items():
        c, k = res['combined'], res['comparison']
        print(f"| CO4 within {b} | {c['tender_hits']}/{c['tenders']} ({c['buyers']} buyers) | {k['rate'] and k['rate'] * 100:.1f}% | {res.get('lr_shrunk')} | | |"
              if c['buyers'] else f"| CO4 within {b} | none | | | | |")
    # Sensitivity (chosen after seeing that the quintiles put 28 of 30 convicted contracts in Q5): finer top bands.
    fine_q = (0.5, 0.8, 0.9, 0.95, 0.98, 0.99)
    fine_edges = [cmp_values[int(q * len(cmp_values))] for q in fine_q]
    fine_names = ['<p50', 'p50-80', 'p80-90', 'p90-95', 'p95-98', 'p98-99', '>=p99']
    fine = [dict(r, band=None if not value_of[r['id']] else fine_names[bisect.bisect_right(fine_edges, value_of[r['id']])]) for r in analysis]
    out['fine_edges_cop'], out['size_standardised_fine'] = fine_edges, size.standardise(fine, CO4, fine_names)
    k = size.INFLATION   # owner, 2026-10-20: convicted prices assumed inflated x1.3
    fine_k = [dict(r, band=None if not value_of[r['id']] else fine_names[bisect.bisect_right(fine_edges, value_of[r['id']] / k)]) if 'combined' in r['groups'] else r for r in fine]
    out['size_standardised_fine_inflation'] = dict(size.standardise(fine_k, CO4, fine_names), inflation=k)
    out['within_fine_band'] = {b: pp.analyse([r for r in fine if r['band'] == b], CO4) for b in fine_names}
    print(f"\nSensitivity, finer top bands (COP edges at comparison percentiles {fine_q}): {[f'{e:,.0f}' for e in fine_edges]}")
    print(f"Convicted band mix: {out['size_standardised_fine']['band_mix_convicted']}")
    print(size.line('CO4 size-standardised, fine bands', out['size_standardised_fine']))
    print(size.line(f'CO4 fine bands, convicted values / {k} (points basis)', out['size_standardised_fine_inflation']))
    for b, res in out['within_fine_band'].items():
        c, k = res['combined'], res['comparison']
        if c['buyers']:
            print(f"| CO4 within {b} | {c['tender_hits']}/{c['tenders']} ({c['buyers']} buyers) | {k['rate'] * 100:.1f}% | {res.get('lr_shrunk')} | | |")
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
