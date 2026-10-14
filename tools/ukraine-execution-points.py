#!/usr/bin/env python3
"""Research only: Ukrainian points for amendment bands, the term-extension sub-indicator and the v3.5 checks.

Same weight of evidence as tools/propose-indicator-points.py (buyer-weighted rates, LR shrunk by a prior
worth 10 buyers, buyer-resampled 95 % interval, points = 10 * log2(LR) floored at 0). Adds:
  - amendment bands 3–4 and 5+, each against the comparisons;
  - term extension (an active amendment with rationale durationExtension or fiscalYearExtension) overall,
    and as a bonus *within* each amendment band (positives with the band and an extension against
    comparisons with the band and an extension, divided by the band's own LR), which is what the engine
    adds on top of the band;
  - --multi-bid: keep only rows whose single-offer check is clear (2+ offers), for bid-rigging labels.

Inputs: per-row checks from analyze-ukraine-verdict-cohort.cjs, amendment features from
fetch-verdict-contract-changes.py, candidate features from ukraine-candidate-indicators.py.
Changes no score, weight or dataset.
"""
import argparse
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location('pip', Path(__file__).with_name('propose-indicator-points.py'))
pip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pip)

TERM = 'C12 term-extension-amendment'
CHECK = 'execution'


def load(rows_path, changes_path, features_path, positive, multi_bid):
    changes = {r['id']: r['features'] for r in json.loads(Path(changes_path).read_text())['rows'] if r.get('features')}
    term = {r['id']: r['checks'][TERM]['status'] for r in json.loads(Path(features_path).read_text())}
    out = []
    for r in json.loads(Path(rows_path).read_text()):
        if r.get('procedure') in pip.NON_COMPETITIVE:
            continue
        if multi_bid and r['checks'].get('ua-single-offer', {}).get('status') != 'clear':
            continue
        if r['label'] in positive:
            if r['finality'] not in pip.ELIGIBLE:
                continue
            groups = [r['label'], 'combined']
        elif r['label'] == 'comparison':
            groups = ['comparison']
        else:
            continue
        f, t = changes.get(r['id']), term.get(r['id'])
        checks = {k: r['checks'][k] for k in ('ua-single-offer', 'ua-better-bid-disqualified') if k in r['checks']}
        if f is not None and t in ('signal', 'clear'):
            checks[CHECK] = {'status': 'clear', 'n': f['changes'], 'ext': t == 'signal'}
        out.append({'id': r['id'], 'buyer': r.get('buyerId') or r['id'], 'groups': groups, 'checks': checks})
    return out


def band(c):
    return '5+' if c['n'] >= 5 else '3–4' if c['n'] >= 3 else '0–2'


def run(rows):
    res = []
    for check in ('ua-single-offer', 'ua-better-bid-disqualified'):
        res.append((check, pip.analyse(rows, check)))
    tests = {
        '3+ amendments': lambda c: c['n'] >= 3,
        '3–4 amendments': lambda c: 3 <= c['n'] <= 4,
        '5+ amendments': lambda c: c['n'] >= 5,
        'term extension, any count': lambda c: c['ext'],
        'term extension with 0–2 amendments': lambda c: c['ext'] and c['n'] < 3,
    }
    for name, t in tests.items():
        res.append((name, pip.analyse(rows, CHECK, t)))
    # Bonus within a band: restrict both groups to the band, then test the extension.
    for b in ('3–4', '5+', '3+'):
        inside = lambda c, b=b: c['n'] >= 3 if b == '3+' else band(c) == b
        sub = [dict(r, checks={CHECK: r['checks'][CHECK]}) for r in rows if CHECK in r['checks'] and inside(r['checks'][CHECK])]
        res.append((f'term extension bonus within {b} amendments', pip.analyse(sub, CHECK, lambda c: c['ext'])))
    return res


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('rows')
    p.add_argument('--changes', required=True)
    p.add_argument('--features', required=True)
    p.add_argument('--positive-labels', default=','.join(pip.POSITIVE))
    p.add_argument('--multi-bid', action='store_true')
    p.add_argument('--json')
    a = p.parse_args(argv)
    rows = load(a.rows, a.changes, a.features, tuple(a.positive_labels.split(',')), a.multi_bid)
    pos = [r for r in rows if 'combined' in r['groups']]
    print(f"{len(pos)} positive rows ({len({r['buyer'] for r in pos})} buyers); {sum('comparison' in r['groups'] for r in rows)} comparisons"
          f"{'; 2+ offers only' if a.multi_bid else ''}.\n")
    print('| Check | Hit rate, positives | Comparisons | LR+ shrunk [95 %] | Points [95 %] |')
    print('|---|---|---|---|---|')
    out = []
    for name, r in run(rows):
        def rate(g):
            x = r[g]
            return f"{x['rate'] * 100:.0f}% ({x['tender_hits']}/{x['tenders']}, {x['buyers']} buyers)" if x['buyers'] else 'NA'
        ci = f" [{r['lr_ci'][0]}, {r['lr_ci'][1]}]" if r.get('lr_ci') else ''
        pci = f" [{r['proposed_points_ci'][0]}, {r['proposed_points_ci'][1]}]" if r.get('proposed_points_ci') else ''
        print(f"| {name} | {rate('combined')} | {rate('comparison')} | {r['lr_shrunk']}{ci} | {r['proposed_points']}{pci} |")
        out.append(dict(r, check=name))
    if a.json:
        Path(a.json).write_text(json.dumps({'multi_bid': a.multi_bid, 'results': out}, indent=1) + '\n')


if __name__ == '__main__':
    main()
