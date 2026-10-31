#!/usr/bin/env python3
"""SEAP buyer-year totals for the Romanian TED cohort's buyers: data/romania-seap-totals.json.

TED lists above-threshold awards only, so the buyer share (RO2) and supplier dependence (N4) checks take their
denominators from SEAP's published contract exports, as the calibration did (tools/romania-bid-rigging-checks.py,
totals of the plan amendment 2026-10-28): quarterly copies of a contract once; each value key (buyer, award notice,
lot, value) once per buyer-year; a value's supplier share split equally among its winners. Framework ceilings stay in,
counted once (the export has no call-off values). Only years with all four quarterly exports are written.
Supplier values only for CUIs the TED cohort already publishes (data/ted-romania.json): SEAP rows are not
privacy-cleared for republication, so no other supplier identifier is written.
Input: ~/.cache/contract-signals/romania-seap/normalized/<year>/ (tools/normalize-romania-seap.py).
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ro = load('ro_checks', 'tools/romania-bid-rigging-checks.py')
ted = load('ted', 'tools/import-ted-cohorts.py')
OUT = ROOT / 'data/romania-seap-totals.json'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--years', type=int, nargs='+', default=[2024, 2025])
    args = p.parse_args(argv)
    buyers = {b['id'] for b in ted.COHORTS['romania']['buyers']}
    published = {ro.cui(x['id']) for r in json.loads((ROOT / 'data/ted-romania.json').read_text(encoding='utf-8'))
                 for x in r.get('supplierIds') or [] if x.get('identifierType') == 'CUI'}
    files = {y: sorted(f.name for f in (ro.SEAP / str(y)).glob('*.jsonl.gz')) for y in args.years}
    for y, names in files.items():
        if len(names) != 4:
            sys.exit(f'{y}: {len(names)} quarterly exports, need 4: {names}')
    total, seen = defaultdict(float), set()
    rows = defaultdict(list)
    for r in ro.stream_seap(args.years):
        b, y = ro.cui(r.get('buyer_cui')), ro.year_of(r)
        if b in buyers and y in files:
            rows[(b, y)].append(r)
    supplier = defaultdict(float)
    for (b, y), rs in rows.items():
        winners = defaultdict(set)
        for r in rs:
            if ro.cui(r.get('winner_cui')):
                winners[ro.value_key(r)].add(ro.cui(r.get('winner_cui')))
        credited = set()
        for r in rs:
            k, w, v = ro.value_key(r), ro.cui(r.get('winner_cui')), r.get('value_ron_num') or 0
            if (y, k) not in seen:
                seen.add((y, k))
                total[(b, y)] += v
            if w and (k, w) not in credited:
                credited.add((k, w))
                supplier[(b, y, w)] += v / len(winners[k])
    out = {'source': 'SEAP contract exports (data.gov.ro, Agenția Națională pentru Achiziții Publice), normalised by tools/normalize-romania-seap.py',
           'method': __doc__.split('\n\n')[1].replace('\n', ' '),
           'files': {str(y): names for y, names in files.items()},
           'reproduce': 'python tools/build-romania-seap-totals.py',
           'buyers': {b: {str(y): {'totalRon': round(total[(b, y)], 2), 'contracts': len(rows[(b, y)]),
                                   'suppliersRon': {w: round(v, 2) for (bb, yy, w), v in sorted(supplier.items()) if (bb, yy) == (b, y) and w in published}}
                          for y in args.years if (b, y) in rows} for b in sorted(buyers)}}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for b, ys in out['buyers'].items():
        for y, v in ys.items():
            print(b, y, f"{v['totalRon']:,.0f} RON", v['contracts'], 'rows', len(v['suppliersRon']), 'suppliers')


if __name__ == '__main__':
    main()
