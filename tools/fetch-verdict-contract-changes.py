#!/usr/bin/env python3
"""Research only: contract amendments for the verdict cohort, and candidate amendment checks.

Reads research/labels/ukraine-verdict-cohort.json.gz, maps each row's contractID to the
internal contract id through the cached tender record, and fetches the contracting-module
record (public API 2.5 /contracts/{id}) with the verdict cohort's serial, capped, cached
Fetcher. Default is offline (cache only). Writes per-row amendment features and prints,
for each candidate check, its hit rate among positives first, then its rate among
comparisons. Changes no score, weight or dataset.
"""
import argparse
import gzip
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('verdict_cohort', ROOT / 'tools/build-ukraine-verdict-cohort.py')
vc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vc)
bc = vc.bc
COHORT = ROOT / 'research/labels/ukraine-verdict-cohort.json.gz'
OUT = ROOT / 'research/labels/ukraine-verdict-contract-changes.json'
PRICE_RATIONALES = {'itemPriceVariation', 'priceReduction', 'fiscalYearExtension', 'taxRate'}


def contract_url(internal_id):
    return f'{bc.PUBLIC_API}/contracts/{internal_id}'


def internal_contract_id(f, row):
    r = f.fetch(bc.tender_url(row['procedureId']))
    if not r or r['status'] != 200:
        return None
    tender = json.loads(r['body'])['data']
    ids = [c['id'] for c in tender.get('contracts', []) if c.get('contractID') == row['contractId']]
    return ids[0] if len(ids) == 1 else None


def features(contract, signed_amount):
    changes = [c for c in contract.get('changes', []) if c.get('status') == 'active']
    rationales = sorted({t for c in changes for t in c.get('rationaleTypes', [])})
    final = (contract.get('value') or {}).get('amount')
    increase = (final - signed_amount) / signed_amount if final is not None and signed_amount else None
    return {'changes': len(changes), 'rationaleTypes': rationales, 'signedAmount': signed_amount, 'finalAmount': final,
            'increase': round(increase, 4) if increase is not None else None}


CHECKS = {
    'three-or-more-amendments': lambda x: x['changes'] >= 3,
    'price-variation-amendment': lambda x: bool(PRICE_RATIONALES & set(x['rationaleTypes'])),
    'value-increased-after-signing': lambda x: x['increase'] is not None and x['increase'] > 0.001,
}


def wilson(k, n, z=1.959963984540054):
    if not n:
        return None
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return c - h, c + h


def report(rows):
    groups = {'corruption': lambda r: r['label'] == 'corruption', 'fraud': lambda r: r['label'] == 'fraud',
              'combined': lambda r: r['label'] in ('corruption', 'fraud'), 'comparison': lambda r: r['label'] == 'comparison'}
    print('Hit rates first (Wilson 95 %); rows without a contract record are unknown, never zero.')
    for name, check in CHECKS.items():
        print('\n' + name)
        for g, member in groups.items():
            known = [r for r in rows if member(r) and r.get('features')]
            k, n = sum(check(r['features']) for r in known), len(known)
            unknown = sum(1 for r in rows if member(r) and not r.get('features'))
            ci = wilson(k, n)
            print(f'  {g}: {k}/{n}' + (f' {100 * k / n:.1f}% [{100 * ci[0]:.1f}%, {100 * ci[1]:.1f}%]' if n else ' NA') + f'; unknown={unknown}')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--download', action='store_true', help='fetch uncached contract records (default: cache only)')
    p.add_argument('--budget', type=int, default=450, help='hard request cap shared with the cohort builder cache')
    p.add_argument('--cache', default=str(vc.CACHE))
    args = p.parse_args(argv)
    cohort = json.loads(gzip.decompress(COHORT.read_bytes()))
    f = bc.Fetcher(Path(args.cache).expanduser(), budget=args.budget, network=args.download, prior=0, opener=vc.opener)
    out, note = [], None
    try:
        for row in cohort['rows']:
            rec = {'id': row['id'], 'tenderID': row['tenderID'], 'label': row['label'], 'positive': row.get('positive'),
                   'finality': row.get('finality'), 'features': None}
            out.append(rec)
            internal = internal_contract_id(f, row)
            if not internal:
                rec['unavailable'] = 'contract id not found in cached tender'
                continue
            r = f.fetch(contract_url(internal))
            if not r or r['status'] != 200:
                rec['unavailable'] = 'contract record not cached' if not r else f"HTTP {r['status']}"
                continue
            rec['features'] = features(json.loads(r['body'])['data'], row.get('amount'))
    except (bc.BudgetExceeded, bc.Blocked, bc.Throttled) as e:
        note = str(e)
    OUT.write_text(json.dumps({'source': str(COHORT.relative_to(ROOT)), 'requests_total': f.requests, 'note': note,
                               'priceRationales': sorted(PRICE_RATIONALES), 'rows': out}, ensure_ascii=False, indent=1) + '\n')
    print(f'{sum(1 for r in out if r["features"])}/{len(out)} rows with a contract record; {f.requests} requests total' + (f'; {note}' if note else ''))
    report([r for r in out if r['label'] == 'comparison' or r['finality'] in ('confirmed', 'presumed')])


if __name__ == '__main__':
    main()
