#!/usr/bin/env python3
"""Research only: direct contracts among convicted tenders against a census of the same buyers' tenders.

Part 2 of research/calibration/ukraine-candidate-indicators-plan.md. For each buyer and year with an
eligible convicted tender, lists all of the buyer's tenders created that year from the prozorro.gov.ua
site search: competitive ones through the tender-date filter, direct contracts (reporting) and
negotiated procedures through the procedure-type filter, which has no year filter and lists newest
first, so the year is located by bisecting pages. Completed tenders only. Requests go through the
verdict cohort's serial, capped, cached Fetcher (default offline). Changes no score, weight or dataset.
"""
import argparse
import gzip
import json
import urllib.parse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


vc = load('verdict_cohort', 'tools/build-ukraine-verdict-cohort.py')
pp = load('propose_indicator_points', 'tools/propose-indicator-points.py')
cand = load('candidate_indicators', 'tools/ukraine-candidate-indicators.py')
bc, imp = vc.bc, vc.imp
COHORT = ROOT / 'research/labels/ukraine-verdict-sweep-cohort.json.gz'
OUT = ROOT / 'research/labels/ukraine-direct-contract-census.json.gz'
DIRECT_TYPES = ('reporting', 'negotiation', 'negotiation.quick')
NEGOTIATED = ('negotiation', 'negotiation.quick')
# Candidate: (procedure types that count, minimum UAH value). D4 is the scored ua-direct-award rule.
CANDIDATES = {'D1 direct-contract': (DIRECT_TYPES, 0), 'D2 direct-contract-200k': (DIRECT_TYPES, 200_000),
              'D3 direct-contract-1.5m': (DIRECT_TYPES, 1_500_000), 'D4 negotiated-procedure': (NEGOTIATED, 0)}
MAX_PAGES = 400                 # per buyer and listing; a longer listing is recorded as incomplete
PLACEHOLDER_BUYERS = {'00000000'}   # a code shared by many entities (e.g. withheld identities), not one buyer


def type_url(buyer, kind, page):
    return imp.SEARCH + '?' + urllib.parse.urlencode({'buyer[]': buyer, 'proc_type[]': kind, 'page': page})


def page(f, url):
    r = f.fetch(url)
    if not r or r['status'] != 200:
        raise RuntimeError(f"search page unavailable ({r and r['status']}): {url}")
    return json.loads(r['body'])


def year_of(t):
    return (t.get('tenderID') or '')[3:7]


def listing_year(f, buyer, kind, year):
    """All tenders of one type and creation year from a newest-first listing. Returns (tenders, complete)."""
    first = page(f, type_url(buyer, kind, 1))
    total, per = first.get('total') or 0, first.get('per_page') or 20
    last = min(MAX_PAGES, -(-total // per)) if total else 0
    if not last:
        return [], True
    # Smallest page whose last item is in or before the year: the year starts on that page.
    lo, hi = 1, last
    while lo < hi:
        mid = (lo + hi) // 2
        data = page(f, type_url(buyer, kind, mid)).get('data') or []
        if data and year_of(data[-1]) <= year:
            hi = mid
        else:
            lo = mid + 1
    out, p, empty = [], lo, 0
    while p <= last:
        data = page(f, type_url(buyer, kind, p)).get('data') or []
        hits = [t for t in data if year_of(t) == year]
        out += hits
        empty = 0 if hits else empty + 1
        # A listing that is not strictly newest first must not be read to its end.
        if not data or year_of(data[-1]) < year or empty >= 2:
            break
        p += 1
    complete = total <= MAX_PAGES * per or p < last
    return out, complete


def listing_competitive(f, buyer, year):
    out, p, total = [], 1, None
    while p <= MAX_PAGES:
        body = page(f, vc.search_url(buyer, p, year))
        total = body.get('total', total)
        out += body.get('data') or []
        if not body.get('data') or (total is not None and len(out) >= total):
            break
        p += 1
    return [t for t in out if year_of(t) == year], total is not None and len(out) >= total


def census(f, buyer_years):
    tenders, incomplete = {}, []
    for buyer, year in sorted(buyer_years):
        found, ok = listing_competitive(f, buyer, year)
        for t in found:
            tenders.setdefault(t['tenderID'], {**t, 'kind': 'competitive', 'buyer': buyer})
        if not ok:
            incomplete.append((buyer, year, 'competitive'))
        for kind in DIRECT_TYPES:
            found, ok = listing_year(f, buyer, kind, year)
            for t in found:   # a type listing overrides the date listing: it names the procedure
                tenders[t['tenderID']] = {**t, 'kind': kind, 'buyer': buyer}
            if not ok:
                incomplete.append((buyer, year, kind))
    return tenders, incomplete


def uah(t):
    v = t.get('value') or {}
    return v.get('amount') if v.get('currency') == 'UAH' else None


def status(direct, value, floor):
    if not direct:
        return 'clear'
    if not floor:
        return 'signal'
    return 'unknown' if value is None else 'signal' if value >= floor else 'clear'


def rows_for_analysis(cohort_rows, tenders):
    positives = [r for r in cohort_rows if r['label'] in pp.POSITIVE and r['finality'] in pp.ELIGIBLE and r['buyerId'] not in PLACEHOLDER_BUYERS]
    positive_ids = {r['tenderID'] for r in positives}
    out = []
    for r in positives:
        listed = tenders.get(r['tenderID'])
        value = uah(listed) if listed else (r.get('amount') if r.get('currency') == 'UAH' else None)
        out.append({'id': r['id'], 'buyer': r['buyerId'], 'groups': [r['label'], 'combined'],
                    'checks': {k: {'status': status(r.get('procedure') in types, value, floor)} for k, (types, floor) in CANDIDATES.items()}})
    for tid, t in tenders.items():
        if tid in positive_ids or t.get('status') != 'complete':
            continue
        out.append({'id': tid, 'buyer': t['buyer'], 'groups': ['comparison'],
                    'checks': {k: {'status': status(t['kind'] in types, uah(t), floor)} for k, (types, floor) in CANDIDATES.items()}})
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--cohort', default=str(COHORT))
    p.add_argument('--cache', default=str(vc.CACHE))
    p.add_argument('--budget', type=int, default=12_000, help='hard request cap shared with the cohort builder cache')
    p.add_argument('--download', action='store_true')
    p.add_argument('--output', default=str(OUT))
    p.add_argument('--json', help='write analysis results here')
    p.add_argument('--limit', type=int, help='trial: only the first N buyer-years')
    args = p.parse_args(argv)
    rows = json.loads(gzip.open(args.cohort).read())['rows']
    positives = [r for r in rows if r['label'] in pp.POSITIVE and r['finality'] in pp.ELIGIBLE]
    buyer_years = {(r['buyerId'], r['tenderID'][3:7]) for r in positives if r['buyerId'] not in PLACEHOLDER_BUYERS}
    if args.limit:
        buyer_years = set(sorted(buyer_years)[:args.limit])
    f = bc.Fetcher(Path(args.cache).expanduser(), budget=args.budget, network=args.download, prior=0, opener=vc.opener)
    start = f.requests
    tenders, incomplete = census(f, buyer_years)
    kinds = {}
    for t in tenders.values():
        kinds[t['kind']] = kinds.get(t['kind'], 0) + (t.get('status') == 'complete')
    with gzip.open(args.output, 'wt', encoding='utf-8') as fh:
        fh.write(json.dumps({'schema': 'ukraine-direct-contract-census/1', 'buyer_years': sorted(buyer_years),
                                             'incomplete': incomplete, 'completed_by_kind': kinds,
                                             'tenders': [{'tenderID': k, 'buyer': v['buyer'], 'kind': v['kind'], 'status': v.get('status'),
                                                          'value': v.get('value')} for k, v in sorted(tenders.items())]}) + '\n')
    print(f'{len(buyer_years)} buyer-years; {f.requests - start} requests this run; completed tenders by kind: {kinds}; incomplete listings: {len(incomplete)}')
    analysis = rows_for_analysis(rows, tenders)
    results = []
    for check in CANDIDATES:
        res = {'candidate': check, 'all': pp.analyse(analysis, check)}
        for name in ('learn', 'check'):
            res[name + '_half'] = pp.analyse([r for r in analysis if cand.half(r['buyer']) == name], check)
        res['decision'] = pp.decide(res['all'])
        results.append(res)
    print(cand.table(results))
    if args.json:
        Path(args.json).write_text(json.dumps({'results': results, 'incomplete': incomplete}, indent=1) + '\n')


if __name__ == '__main__':
    main()
