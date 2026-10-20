#!/usr/bin/env python3
"""Research only: K1/K2 (and other link checks) on AMCU cases split by the evidence the judgments cite.

The Antimonopoly Committee finds cartels through shared contacts, addresses, IP addresses and file metadata,
so the AMCU cohort overstates those checks. Rules fixed in research/calibration/bias-controls-plan.md, part 2:
each case's judgment texts are classified (contact, address, ip; evidence_classifier.py, validated on hand-read
cases); the decision basis is the LR on cases citing none of them, against the same comparisons.
A tender in several cases counts as citing if any of its cases does. Changes no score, weight or dataset.
"""
import argparse
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


pp = load('propose_indicator_points', 'tools/propose-indicator-points.py')
cand = load('candidates', 'tools/ukraine-candidate-indicators.py')
FEATURES = [ROOT / 'research/labels/ukraine-amcu-full-candidate-features.json',
            ROOT / 'research/labels/ukraine-amcu-full-related-candidate-features.json']
CASES = ROOT / 'research/labels/ukraine-amcu-candidates.json'
EVIDENCE = ROOT / 'research/labels/ukraine-amcu-case-evidence.json'
CHECKS = ['K1 shared-contact', 'K2 shared-address', 'K3 shared-document', 'K4 close-submission', 'K5 tight-bids',
          'K6 close-runner-up', 'K8 empty-cover-bid', 'R1 shared-owner']
SPLITS = {'all AMCU cases': lambda e: True,
          'none of contact, address, IP cited (decision basis)': lambda e: not e['any_link'],
          'contact, address or IP cited': lambda e: e['any_link'],
          'contact not cited': lambda e: not e['contact'],
          'address not cited': lambda e: not e['address']}


def merged_rows():
    rows = {}
    for path in FEATURES:
        for r in json.loads(path.read_text()):
            rows.setdefault(r['id'], dict(r, checks={})).get('checks').update(r['checks'])
    return list(rows.values())


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--evidence', default=str(EVIDENCE))
    p.add_argument('--json')
    args = p.parse_args(argv)
    evidence = json.loads(Path(args.evidence).read_text())
    cases_of = defaultdict(set)
    for v in json.loads(CASES.read_text())['verdicts']:
        cases_of[v['tender_id_normalised'][:20]].add(v['case_number'])
    tmp = ROOT / 'research/labels/.amcu-merged-features.tmp.json'
    tmp.write_text(json.dumps(merged_rows()))
    rows, skipped = pp.load_rows(tmp, None, ('collusion',))
    tmp.unlink()
    group_of = {r['id']: r['group'] for r in json.loads(FEATURES[0].read_text())}
    tender_ev, missing = {}, Counter()
    for r in rows:
        if 'combined' not in r['groups']:
            continue
        cs = cases_of.get(group_of[r['id']][:20], set())
        ev = [evidence[c] for c in cs if c in evidence]
        if not ev:
            missing['no classified case'] += 1
            continue
        tender_ev[r['id']] = {k: any(e[k] for e in ev) for k in ('contact', 'address', 'ip', 'any_link')}
    pos = [r for r in rows if r['id'] in tender_ev]
    print(f"{len(pos)} positive rows with classified cases ({len({r['buyer'] for r in pos})} buyers); {dict(missing)}; "
          f"cited per positive tender: {dict(Counter(k for e in tender_ev.values() for k, v in e.items() if v))}")
    print(f"cases: {len(evidence)}, cited: {dict(Counter(k for e in evidence.values() for k, v in e.items() if v))}\n")
    out = {}
    print('| Check | Basis | Hit rate, AMCU | Comparisons | LR shrunk [95 %] | LR at 25th pct | Decision points |')
    print('|---|---|---|---|---|---|---|')
    for check in CHECKS:
        out[check] = {}
        for name, keep in SPLITS.items():
            sub = [r for r in rows if 'comparison' in r['groups'] or (r['id'] in tender_ev and keep(tender_ev[r['id']]))]
            res = pp.analyse(sub, check)
            out[check][name] = res
            c, k = res['combined'], res['comparison']
            if not c['buyers']:
                continue
            ci = f"[{res['lr_ci'][0]:.2f}, {res['lr_ci'][1]:.2f}]" if res.get('lr_ci') else ''
            print(f"| {check} | {name} | {c['rate'] * 100:.1f}% ({c['tender_hits']}/{c['tenders']}, {c['buyers']} buyers) | "
                  f"{k['rate'] * 100:.2f}% | {res.get('lr_shrunk')} {ci} | {res.get('lr_confident')} | {res.get('decision_points')} |")
    if args.json:
        Path(args.json).write_text(json.dumps({'plan': 'research/calibration/bias-controls-plan.md', 'results': out}, indent=1) + '\n')


if __name__ == '__main__':
    main()
