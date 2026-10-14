#!/usr/bin/env python3
"""Research only: do the v3.5 Ukrainian likelihood ratios survive changes to the label set?

Reruns tools/propose-indicator-points.py's analysis for the re-pointed checks on variants of the
verdict cohort: strict finality, one tender per court case, without the largest split scheme, and
before / from 2022. Changes no score, weight or dataset.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('propose_indicator_points', ROOT / 'tools/propose-indicator-points.py')
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)
REVIEWED = ROOT / 'research/labels/ukraine-verdict-sweep-reviewed.json'
LINKED = ROOT / 'research/labels/ukraine-verdict-linked.json'   # verdicts without a tender ID, linked by rule
CHANGES = ROOT / 'research/labels/ukraine-verdict-sweep-contract-changes.json'
SPLIT_SCHEME = {'991/8983/26', '991/8984/26', '991/8985/26', '296/8819/24'}   # one scheme split over many tenders
AMEND = pp.AMENDMENT_CHECK
CHECKS = [('ua-single-offer', None), ('ua-better-bid-disqualified', None), (AMEND, None),
          (AMEND + ' 3–4', lambda c: 3 <= c.get('changes', 0) <= 4), (AMEND + ' 5+', lambda c: c.get('changes', 0) >= 5)]


def year(row_id):
    return row_id.split('UA-', 1)[1][:4] if 'UA-' in row_id else ''


def one_per_case(raw, cases):
    """Ids of the first positive tender (by id) of each court case or set of cases."""
    seen, first = set(), set()
    for r in sorted((r for r in raw if r['label'] in pp.POSITIVE), key=lambda r: r['id']):
        key = tuple(sorted(cases.get(v, v) for v in r.get('verdict_ids') or [])) or (r['id'],)
        if key not in seen:
            seen.add(key)
            first.add(r['id'])
    return first


def write_one_per_case(rows_path, raw, cases):
    """Write the one-tender-per-case rows and candidate features next to the full ones."""
    keep = one_per_case(raw, cases)
    for src in (Path(rows_path), Path(str(rows_path).replace('-rows.json', '-candidate-features.json'))):
        data = json.loads(src.read_text())
        out = src.with_name(src.name.replace('-rows.json', '-one-per-case-rows.json').replace('-candidate-features.json', '-one-per-case-candidate-features.json'))
        out.write_text(json.dumps([r for r in data if r['label'] not in pp.POSITIVE or r['id'] in keep]) + '\n')
        print(f'wrote {out}', file=sys.stderr)


def variants(rows, raw, cases):
    positive = lambda r: 'combined' in r['groups']
    final = {r['id'] for r in raw if r.get('finality') == 'confirmed'}
    first_per_case = one_per_case(raw, cases)
    split = {r['id'] for r in raw if any(cases.get(v) in SPLIT_SCHEME for v in r.get('verdict_ids') or [])}
    yield 'all (v3.5 basis)', rows
    yield 'confirmed finality only', [r for r in rows if not positive(r) or r['id'] in final]
    yield 'one tender per court case', [r for r in rows if not positive(r) or r['id'] in first_per_case]
    yield 'without the split scheme (4 cases)', [r for r in rows if not positive(r) or r['id'] not in split]
    yield 'tenders created before 2022', [r for r in rows if year(r['id']) < '2022']
    yield 'tenders created 2022 or later', [r for r in rows if year(r['id']) >= '2022']


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('rows', help='per-row checks JSON from analyze-ukraine-verdict-cohort.cjs')
    p.add_argument('--json', help='write full results here')
    p.add_argument('--changes', default=str(CHANGES), help='amendment features JSON from fetch-verdict-contract-changes.py')
    p.add_argument('--write-one-per-case', action='store_true',
                   help='also write <name>-one-per-case-rows.json and -candidate-features.json (the v3.5 points basis)')
    args = p.parse_args(argv)
    raw = json.loads(Path(args.rows).read_text())
    cases = {v['reyestr_id']: v['case_number'] for path in (REVIEWED, LINKED) if path.exists() for v in json.loads(path.read_text())['verdicts']}
    if args.write_one_per_case:
        write_one_per_case(args.rows, raw, cases)
    rows, _ = pp.load_rows(args.rows, args.changes)
    out = []
    print('| Variant | Positives (buyers) | ' + ' | '.join(name for name, _ in CHECKS) + ' |')
    print('|---|---|' + '---|' * len(CHECKS))
    for name, subset in variants(rows, raw, cases):
        pos = [r for r in subset if 'combined' in r['groups']]
        cells, res_all = [], {}
        for check, band in CHECKS:
            test = (lambda c, band=band: c['status'] == 'signal' and band(c)) if band else (lambda c: c['status'] == 'signal')
            res = pp.analyse(subset, AMEND if band else check, test)
            res_all[check] = res
            ci = f" [{res['lr_ci'][0]:.2f}, {res['lr_ci'][1]:.2f}]" if res.get('lr_ci') else ''
            cells.append(f"{res['combined']['rate'] * 100:.0f}% vs {res['comparison']['rate'] * 100:.0f}%: LR {res['lr_shrunk']:.2f}{ci} → {res['proposed_points']}"
                         if res.get('lr_shrunk') and res['combined']['rate'] is not None else 'NA')
        print(f"| {name} | {len(pos)} ({len({r['buyer'] for r in pos})}) | " + ' | '.join(cells) + ' |')
        out.append({'variant': name, 'positives': len(pos), 'results': res_all})
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
