#!/usr/bin/env python3
"""Write the slim, minified copies of the record files that the browser loads.

The canonical files in data/ keep archival fields that review tools and tests read
(source row variants, unused SECOP II columns). The explorer never reads them, so the
copies in data/web/ omit them; everything else is kept as is. One value is derived from the
dropped DECP source rows: operatorGrouping, the declared grouping of several holders.

    python tools/build-web-data.py          # rewrite data/web/
    python tools/build-web-data.py --check  # exit 1 if a copy is missing or stale
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Fields the explorer (script.js, import.js) never reads, per canonical file.
DROP = {
    'decp-history.json': ['rawVariantCount', 'feedUid'],
    'decp-cities.json': ['sourceRowVariants', 'feedUid'],
    'colombia-secop2.json': [
        'buyerLevel', 'buyerOrden', 'departamento', 'ciudad', 'supplierGroup', 'supplierSme',
        'spendingDestination', 'amountAmortized', 'amountPendingPayment', 'amountPendingExecution',
        'startDate', 'endDate', 'lastUpdated', 'postConflict', 'reversion', 'liquidation',
    ],
}


def operator_grouping(row):
    """The grouping the DECP source rows declare (typegroupementoperateurs), sorted, or None."""
    values = {v.get('typegroupementoperateurs') for v in row.get('sourceRowVariants') or [] if isinstance(v, dict)}
    values.discard(None); values.discard('')
    return sorted(values) or None


def slim_row(name, row):
    out = {k: v for k, v in row.items() if k not in DROP[name]}
    # Kept from the dropped source rows: the explorer words the several-holders note from it.
    if name == 'decp-cities.json' and len(row.get('supplierIds') or []) > 1 and operator_grouping(row):
        out['operatorGrouping'] = operator_grouping(row)
    return out


def slim(name):
    rows = json.loads((ROOT / 'data' / name).read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise SystemExit(f'{name}: expected a list of records')
    out = [slim_row(name, row) for row in rows]
    return json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true', help='only verify that data/web/ is current')
    args = parser.parse_args()
    stale = []
    for name in DROP:
        target = ROOT / 'data' / 'web' / name
        text = slim(name)
        if args.check:
            if not target.exists() or target.read_text(encoding='utf-8') != text:
                stale.append(name)
            continue
        target.parent.mkdir(exist_ok=True)
        target.write_text(text, encoding='utf-8')
        print(f'{target.relative_to(ROOT)}: {(ROOT / "data" / name).stat().st_size:,} → {target.stat().st_size:,} bytes')
    if stale:
        print('Stale data/web copies (run python tools/build-web-data.py): ' + ', '.join(stale), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
