#!/usr/bin/env python3
"""Research only: Ukrainian N2 weekend signature and N3 long duration (research/calibration/untested-checks-plan.md).

Conviction cohort with linked tenders, one tender per court case for positives (as for the v3.5/3.6 points),
same buyers' comparisons. N2: the contract `date` (signing) falls on a Saturday or Sunday. N3: the declared
`durationMonths` is at least 36. Same statistics as tools/propose-indicator-points.py, buyer-half holdout.
"""
import datetime
import gzip
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


pp = load('pp', 'tools/propose-indicator-points.py')
cand = load('cand', 'tools/ukraine-candidate-indicators.py')
rob = load('rob', 'tools/ukraine-points-robustness.py')
COHORT = ROOT / 'research/labels/ukraine-verdict-plus-linked-cohort.json.gz'


def day(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def main():
    rows = json.loads(gzip.open(COHORT).read())['rows']
    cases = {v['reyestr_id']: v['case_number'] for p in (rob.REVIEWED, rob.LINKED) for v in json.loads(p.read_text())['verdicts']}
    keep = rob.one_per_case(rows, cases)
    out = []
    for r in rows:
        pos = r['label'] in pp.POSITIVE
        if (pos and (r['finality'] not in pp.ELIGIBLE or r['id'] not in keep)) or (not pos and r['label'] != 'comparison'):
            continue
        d, m = day(r.get('date')), r.get('durationMonths')
        st = lambda v: {'status': 'unknown' if v is None else 'signal' if v else 'clear'}
        out.append({'id': r['id'], 'buyer': r['buyerId'], 'groups': [r['label'], 'combined'] if pos else ['comparison'],
                    'checks': {'N2 weekend signature': st(None if d is None else d.weekday() >= 5),
                               'N3 long duration >= 36 months': st(None if not isinstance(m, (int, float)) else m >= 36)}})
    results = []
    for check in ('N2 weekend signature', 'N3 long duration >= 36 months'):
        res = {'candidate': check, 'all': pp.analyse(out, check)}
        for h in ('learn', 'check'):
            res[h + '_half'] = pp.analyse([r for r in out if cand.half(r['buyer']) == h], check)
        res['decision'] = pp.decide(res['all'])
        results.append(res)
    print(cand.table(results))


if __name__ == '__main__':
    main()
