#!/usr/bin/env python3
"""Research only: relative-size and legal-ceiling candidates R1-R3 (part 4 of the candidate plan).

Part 4 of research/calibration/ukraine-candidate-indicators-plan.md, rules fixed before this ran:
  R1 buyer-share          tender value >= 5 % of the buyer's completed-tender total that year (census)
  R2 increase-near-cap    current contract amount >= signed amount + 90 % of the 10 % reference ceiling (cohort)
  R3 just-under-threshold direct-contract report at 80-100 % of its open-tender threshold (census)
Offline: census listings come from the cached search pages, buyer kinds from cached tender records.
--fetch-categories downloads (serial, capped, cached) the tender records of direct-contract reports whose
listed title carries no CPV code and whose value lies in one of the R3 bands, so their category is known;
R3 then reads the category from the record (mainProcurementCategory, else the first item's CPV).
Changes no score, weight or dataset.
"""
import argparse
import gzip
import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


census_mod = load('census', 'tools/ukraine-direct-contract-census.py')
vc, pp, cand, bc = census_mod.vc, census_mod.pp, census_mod.cand, census_mod.bc
COHORT = ROOT / 'research/labels/ukraine-verdict-plus-linked-cohort.json.gz'
CHANGES = ROOT / 'research/labels/ukraine-verdict-plus-linked-contract-changes.json'
CENSUS = ROOT / 'research/labels/ukraine-direct-contract-census-plus-linked.json.gz'

SHARE, SHARE_SENSITIVITY = 0.05, (0.01, 0.10)
CEILING = 0.10                     # Law 922-VIII art. 41 part 5 point 2: unit price may rise by up to 10 %
NEAR = 0.9                         # "close to the ceiling": at least 90 % of it
BAND = (0.8, 1.0)                  # R3: 80 % to just under the threshold
# Law 922-VIII art. 3 part 1: (goods and services, works) in UAH
THRESHOLDS = {'general': (200_000, 1_500_000), 'special': (1_000_000, 5_000_000)}
KIND_CLASS = {'general': 'general', 'authority': 'general', 'central': 'general', 'social': 'general', 'special': 'special'}
TITLE_CPV = re.compile(r'^\s*(\d{8})-\d')


def uah(value):
    value = value or {}
    return value.get('amount') if value.get('currency') == 'UAH' and isinstance(value.get('amount'), (int, float)) else None


def buyer_kinds(f, rows):
    """Buyer -> procuringEntity.kind from any cached tender record of that buyer."""
    kinds = {}
    for r in rows:
        if r['buyerId'] in kinds:
            continue
        for url in (vc.bc.tender_url(r['tenderID']), f"https://prozorro.gov.ua/api/tenders/{r['tenderID']}/details"):
            hit = f.fetch(url)
            if hit and hit.get('body'):
                data = json.loads(hit['body'])
                kind = (data.get('data', data).get('procuringEntity') or {}).get('kind')
                if kind:
                    kinds[r['buyerId']] = kind
                    break
    return kinds


def in_band(value):
    return value is not None and any(BAND[0] * t <= value < BAND[1] * t for pair in THRESHOLDS.values() for t in pair)


def details_url(tender_id):
    # The site endpoint takes the public tender ID; the official API needs the internal id (404 otherwise).
    return f'https://prozorro.gov.ua/api/tenders/{tender_id}/details'


def record_cpv(f, tender_id):
    """'45…' for works, another CPV for goods and services, from a cached tender record; None if unknown."""
    hit = f.fetch(details_url(tender_id))
    if not hit or not hit.get('body'):
        return None
    data = json.loads(hit['body'])
    data = data.get('data', data)
    category = data.get('mainProcurementCategory')
    if category in ('goods', 'services', 'works'):
        return '45000000' if category == 'works' else '00000000'
    for item in data.get('items') or []:
        c = item.get('classification') or {}
        m = re.search(r'\b(\d{8})-\d', f"{c.get('id') or ''} {c.get('description') or ''}")
        if m:
            return m.group(1)
    return None


def threshold(kind, cpv):
    cls = KIND_CLASS.get(kind)
    if cls is None or not cpv:
        return None
    goods, works = THRESHOLDS[cls]
    return works if cpv.startswith('45') else goods


def status(flag):
    return 'unknown' if flag is None else 'signal' if flag else 'clear'


def census_rows(rows, census, kinds, categories=None):
    """R1 and R3 rows: eligible positives against the census tenders of the same buyer-years."""
    positives = [r for r in rows if r['label'] in pp.POSITIVE and r['finality'] in pp.ELIGIBLE
                 and r['buyerId'] not in census_mod.PLACEHOLDER_BUYERS]
    years = {(b, y) for b, y in census['buyer_years']}
    positives = [r for r in positives if (r['buyerId'], r['tenderID'][3:7]) in years]
    totals = defaultdict(float)
    listed = census['tenders']
    for t in listed.values():
        if t.get('status') == 'complete' and uah(t.get('value')) is not None:
            totals[(t['buyer'], t['tenderID'][3:7])] += uah(t['value'])
    positive_ids = {r['tenderID'] for r in positives}
    out = []

    def checks(value, buyer, year, direct, cpv, extra):
        total = totals[(buyer, year)] + extra
        share = value / total if value is not None and total > 0 else None
        limit = threshold(kinds.get(buyer), cpv)
        # Outside every band R3 cannot fire, whatever the category or buyer kind.
        near = (None if not direct or value is None else False if not in_band(value)
                else None if limit is None else BAND[0] * limit <= value < BAND[1] * limit)
        c = {'R1 buyer-share': {'status': status(None if share is None else share >= SHARE)},
             'R3 just-under-threshold': {'status': 'clear' if not direct else status(near)}}
        for s in SHARE_SENSITIVITY:
            c[f'R1 sensitivity >= {s:.0%}'] = {'status': status(None if share is None else share >= s)}
        for name, keep in (('before 2022', year < '2022'), ('from 2022', year >= '2022')):
            c[f'R3 sensitivity {name}'] = c['R3 just-under-threshold'] if keep else {'status': 'unknown'}
        return c

    for r in positives:
        t = listed.get(r['tenderID'])
        value = uah(t.get('value')) if t else (r.get('amount') if r.get('currency') == 'UAH' else None)
        counted = t is not None and t.get('status') == 'complete' and uah(t.get('value')) is not None
        cpv = (r.get('cpv') or '') or ((TITLE_CPV.match(t.get('title') or '') or [None, None])[1] if t else None)
        out.append({'id': r['id'], 'buyer': r['buyerId'], 'groups': [r['label'], 'combined'],
                    'checks': checks(value, r['buyerId'], r['tenderID'][3:7], r.get('procedure') == 'reporting', cpv,
                                     0 if counted or value is None else value)})
    for tid, t in listed.items():
        if tid in positive_ids or t.get('status') != 'complete':
            continue
        m = TITLE_CPV.match(t.get('title') or '')
        cpv = m.group(1) if m else (categories or {}).get(tid)
        out.append({'id': tid, 'buyer': t['buyer'], 'groups': ['comparison'],
                    'checks': checks(uah(t.get('value')), t['buyer'], tid[3:7], t['kind'] == 'reporting', cpv, 0)})
    return out


def increase_rows(rows, changes):
    """R2 rows: cohort positives and comparisons with both contract amounts."""
    out = []
    for r in rows:
        if r['label'] in pp.POSITIVE and r['finality'] not in pp.ELIGIBLE:
            continue
        f = changes.get(r['id']) or {}
        signed, final = f.get('signedAmount'), f.get('finalAmount')
        rise = (final - signed) / signed if isinstance(signed, (int, float)) and isinstance(final, (int, float)) and signed > 0 else None
        c = {'R2 increase-near-cap': {'status': status(None if rise is None else rise >= NEAR * CEILING - 1e-12)},
             'R2 sensitivity any increase': {'status': status(None if rise is None else rise > 0)},
             'R2 sensitivity >= ceiling': {'status': status(None if rise is None else rise >= CEILING - 1e-12)}}
        groups = [r['label'], 'combined'] if r['label'] in pp.POSITIVE else ['comparison']
        out.append({'id': r['id'], 'buyer': r['buyerId'], 'groups': groups, 'checks': c})
    return out


def evaluate(analysis, check):
    res = {'candidate': check, 'all': pp.analyse(analysis, check)}
    for name in ('learn', 'check'):
        res[name + '_half'] = pp.analyse([r for r in analysis if cand.half(r['buyer']) == name], check)
    res['decision'] = 'sensitivity only' if 'sensitivity' in check else pp.decide(res['all'])
    return res


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--cohort', default=str(COHORT))
    p.add_argument('--changes', default=str(CHANGES))
    p.add_argument('--census', default=str(CENSUS))
    p.add_argument('--cache', default=str(vc.CACHE))
    p.add_argument('--json', help='write results here')
    p.add_argument('--fetch-categories', action='store_true', help='download the records R3 needs (network)')
    p.add_argument('--budget', type=int, default=3000, help='new requests allowed for --fetch-categories')
    args = p.parse_args(argv)
    rows = json.loads(gzip.open(args.cohort).read())['rows']
    saved = json.loads(gzip.open(args.census).read())
    f = bc.Fetcher(Path(args.cache).expanduser(), network=False, prior=0, opener=vc.opener)
    tenders, incomplete = census_mod.census(f, {tuple(x) for x in saved['buyer_years']})
    if len(tenders) != len(saved['tenders']) or incomplete:
        raise SystemExit(f'cached listings do not replay the census: {len(tenders)} vs {len(saved["tenders"])} tenders')
    census = {'buyer_years': saved['buyer_years'], 'tenders': tenders}
    kinds = buyer_kinds(f, rows)
    need = sorted(tid for tid, t in tenders.items() if t['kind'] == 'reporting' and t.get('status') == 'complete'
                  and not TITLE_CPV.match(t.get('title') or '') and in_band(uah(t.get('value'))))
    if args.fetch_categories:
        net = bc.Fetcher(Path(args.cache).expanduser(), budget=f.requests + args.budget, network=True, prior=0, opener=vc.opener)
        try:
            for i, tid in enumerate(need):
                net.fetch(details_url(tid))
                net.responses.clear()
                if i % 200 == 0:
                    print(f'{i}/{len(need)} records', flush=True)
        except (bc.BudgetExceeded, bc.Blocked, bc.Throttled) as e:
            print(f'stopped: {e}')
    categories = {tid: record_cpv(f, tid) for tid in need}
    print(f'R3 band tenders without a title CPV: {len(need)}; category known for {sum(v is not None for v in categories.values())}')
    changes = {r['id']: r['features'] for r in json.loads(Path(args.changes).read_text())['rows'] if r.get('features')}
    a1, a2 = census_rows(rows, census, kinds, categories), increase_rows(rows, changes)
    results = [evaluate(a1 if check.startswith(('R1', 'R3')) else a2, check)
               for check in [*a1[0]['checks'], *a2[0]['checks']]]
    kinded = {b for b in {r['buyer'] for r in a1}}
    print(f"buyers with a known kind: {sum(1 for b in kinded if KIND_CLASS.get(kinds.get(b)))} of {len(kinded)}; "
          f"kinds {dict(sorted(defaultdict(int, {k: sum(1 for b in kinded if kinds.get(b) == k) for k in set(kinds.get(b) for b in kinded)}).items(), key=str))}")
    print(cand.table(results))
    if args.json:
        Path(args.json).write_text(json.dumps({'results': results}, indent=1) + '\n')


if __name__ == '__main__':
    main()
