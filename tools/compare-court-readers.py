#!/usr/bin/env python3
"""Compare two readings of the same court rulings (dir A vs dir B, each <serial>/result.json).
Prints one line per differing ruling: relevance, outcome, proven contract counts and amounts.
Usage: compare-court-readers.py DIR_A DIR_B [SERIALS_FILE]   (SERIALS_FILE: whitespace-separated serials; when
omitted, the subdirectory names of DIR_B are used).
stderr gets two lines: `agree X, differ Y, missing Z` and `differing: relevance R, outcome O, count C, amounts M`
(rulings where relevance / outcome / number of proven contracts / set of proven amounts differ; one ruling can count in several)."""
import json, re, sys
from pathlib import Path

def load(d, s):
    f = Path(d) / s / 'result.json'
    try:
        return json.loads(f.read_text())
    except Exception:
        return None

def summary(r):
    if r is None:
        return None
    proven, other = set(), set()
    for fd in r.get('findings') or []:
        for c in fd.get('contracts') or []:
            key = (c.get('amount'), re.sub(r'\s+', '', c.get('contract_name') or '')[:20])
            (proven if fd.get('proven') else other).add(key)
    return {'rel': bool(r.get('relevant')), 'out': (r.get('case') or {}).get('outcome'),
            'proven': proven, 'other': other}

a, b = sys.argv[1], sys.argv[2]
serials = Path(sys.argv[3]).read_text().split() if len(sys.argv) > 3 else sorted(p.name for p in Path(b).iterdir() if p.is_dir())
agree = diff = missing = 0
n_rel = n_out = n_cnt = n_amt = 0
for s in serials:
    x, y = summary(load(a, s)), summary(load(b, s))
    if x is None or y is None:
        missing += 1
        continue
    amts = lambda z: {k[0] for k in z['proven'] if k[0]}
    n_rel += x['rel'] != y['rel']
    n_out += x['out'] != y['out']
    n_cnt += len(x['proven']) != len(y['proven'])
    n_amt += amts(x) != amts(y)
    same = x['rel'] == y['rel'] and x['out'] == y['out'] and len(x['proven']) == len(y['proven']) and amts(x) == amts(y)
    if same:
        agree += 1
        continue
    diff += 1
    print(f"{s}\trel {x['rel']}/{y['rel']}\tout {x['out']}/{y['out']}\tproven {len(x['proven'])}/{len(y['proven'])}"
          f"\tamounts shared {len(amts(x) & amts(y))} only-A {len(amts(x) - amts(y))} only-B {len(amts(y) - amts(x))}")
print(f'agree {agree}, differ {diff}, missing {missing}', file=sys.stderr)
print(f'differing: relevance {n_rel}, outcome {n_out}, count {n_cnt}, amounts {n_amt}', file=sys.stderr)
