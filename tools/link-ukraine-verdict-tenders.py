#!/usr/bin/env python3
"""Research only: link verdicts that quote no tender ID to Prozorro tenders by the buyer's company code.

Rules fixed in research/calibration/ukraine-verdict-linking-plan.md before any link was made. Input: the
model review of local verdict texts (out-*.jsonl in the link work directory). For each procurement that
could become a label (conviction, the procurement is part of the scheme, 2016 or later, buyer code given)
the buyer's tenders of that year are listed (all procedure types, as the direct-contract census does),
shortlisted by value, CPV or date, fetched, and compared on supplier code, contract number, signature
date and amount. A link is kept only when exactly one tender matches.

  match     list, shortlist, fetch and compare (network with --download; cached Fetcher, serial)
  finality  register Review pages of the linked verdicts (date of entry into force), slow and serial
  labels    write research/labels/ukraine-verdict-linked.json in the reviewed-verdict format

Stores codes, numbers, dates and tender IDs only; no names. Changes no score, weight or dataset.
"""
import argparse
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vc = load('verdict_cohort', 'tools/build-ukraine-verdict-cohort.py')
census = load('direct_census', 'tools/ukraine-direct-contract-census.py')
sw = load('sweep', 'tools/sweep-ukraine-verdicts.py')
bc = vc.bc
WORK = Path.home() / '.cache/contract-signals/verdict-work/link'
CACHE = Path.home() / '.cache/contract-signals/labels/verdict-link'
MATCHES = ROOT / 'research/labels/ukraine-verdict-link-matches.json'
LINKED = ROOT / 'research/labels/ukraine-verdict-linked.json'
SHORTLIST = 15
VALUE_BAND = 0.25
DATE_DAYS = 7
AMOUNT_TOLERANCE = 0.01
TENDER_DAYS_BEFORE = 180        # shortlist by date: tendering ended at most this long before the contract date


def reviews(work=WORK):
    rows = []
    for path in sorted(Path(work).glob('out-*.jsonl')):
        for line in path.read_text().splitlines():
            if line.strip().startswith('{'):
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    seen, out = set(), []
    for r in rows:
        key = (str(r.get('doc_id')), r.get('n'))
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def code(value):
    digits = re.sub(r'\D', '', str(value or ''))
    return digits if len(digits) in (8, 10) else None


def number(value):
    s = re.sub(r'[\s№#]', '', str(value or '')).lower()
    return s.lstrip('0') or None


def day(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def year_of(r):
    y = str(r.get('procurement_year') or '')[:4] or str(r.get('contract_date') or '')[:4]
    return y if re.fullmatch(r'20\d\d', y) else None


def name(value):
    """Organisation name for equality: lower case, quotes, punctuation and spaces removed."""
    return ''.join(c for c in str(value or '').lower() if c.isalnum()) or None


def buyer_code(r):
    c = code(r.get('buyer_code'))
    return c if c and len(c) == 8 else None


def eligible(r):
    """A procurement that could become a label and can be searched."""
    if r.get('outcome') not in sw.CONVICTED or r.get('role') != 'scheme' or r.get('via_prozorro') == 'no':
        return 'not a label'
    if not buyer_code(r) and not name(r.get('buyer_name')):
        return 'no buyer code or name'
    if not year_of(r) or year_of(r) < '2016':
        return 'no year or before 2016'
    return None


def amount(r):
    a = r.get('amount_uah')
    return float(a) if isinstance(a, (int, float)) and not isinstance(a, bool) and a > 0 else None


def cpv5(text):
    m = re.search(r'\b(\d{5})\d{3}-\d\b', str(text or ''))
    return m.group(1) if m else None


def shortlist(r, listed):
    """Listed tenders worth fetching, nearest value first."""
    a, cpv, signed = amount(r), cpv5(r.get('cpv')), day(r.get('contract_date'))
    picked = []
    for t in listed:
        v = census.uah(t)
        near = a is not None and v is not None and abs(v - a) <= VALUE_BAND * a
        same_cpv = cpv is not None and cpv5(t.get('title')) == cpv
        end = day(((t.get('tenderPeriod') or {}).get('endDate')) or ((t.get('enquiryPeriod') or {}).get('endDate')))
        timely = signed is not None and end is not None and signed - timedelta(days=TENDER_DAYS_BEFORE) <= end <= signed
        if near or same_cpv or (timely and a is None and cpv is None):
            gap = abs(math.log(v / a)) if a and v else 9.0
            picked.append((not same_cpv, gap, t['tenderID']))
    return [tid for *_, tid in sorted(picked)[:SHORTLIST]]


def resolve_buyer(f, buyer_name, hits=3):
    """The buyer's code from its name: up to `hits` tenders whose buyer name equals it must agree on one code."""
    url = census.imp.SEARCH + '?' + census.urllib.parse.urlencode({'text': buyer_name, 'page': 1})
    r = f.fetch(url)
    if not r or r['status'] != 200:
        return None
    same = [t['tenderID'] for t in json.loads(r['body']).get('data') or []
            if name((t.get('procuringEntity') or {}).get('name')) == name(buyer_name)][:hits]
    codes = set()
    for tid in same:
        tender = vc.resolve(f, tid)
        codes.add(code((((tender or {}).get('procuringEntity') or {}).get('identifier') or {}).get('id')))
    codes.discard(None)
    return codes.pop() if len(codes) == 1 else None


def evidence(r, tender):
    """Which of S, N, D, A hold for this tender record."""
    supplier, num, signed, a = code(r.get('supplier_code')), number(r.get('contract_number')), day(r.get('contract_date')), amount(r)
    supplier_name = name(r.get('supplier_name'))
    parties, numbers, dates, values = set(), set(), [], []
    for c in tender.get('contracts') or []:
        if c.get('status') in ('cancelled',):
            continue
        parties |= {code((s.get('identifier') or {}).get('id')) for s in c.get('suppliers') or []}
        parties |= {('name', name((s.get('identifier') or {}).get('legalName') or s.get('name'))) for s in c.get('suppliers') or []}
        numbers.add(number(c.get('contractNumber')))
        dates.append(day(c.get('dateSigned')))
        values.append((c.get('value') or {}).get('amount'))
    for aw in tender.get('awards') or []:
        if aw.get('status') == 'active':
            parties |= {code((s.get('identifier') or {}).get('id')) for s in aw.get('suppliers') or []}
            parties |= {('name', name((s.get('identifier') or {}).get('legalName') or s.get('name'))) for s in aw.get('suppliers') or []}
            values.append((aw.get('value') or {}).get('amount'))
    hits = set()
    if (supplier and supplier in parties) or (supplier_name and ('name', supplier_name) in parties):
        hits.add('S')
    if num and num in numbers:
        hits.add('N')
    if signed and any(d and abs((d - signed).days) <= DATE_DAYS for d in dates):
        hits.add('D')
    if a and any(isinstance(v, (int, float)) and abs(v - a) <= AMOUNT_TOLERANCE * a for v in values):
        hits.add('A')
    return hits


def is_match(hits):
    return ('S' in hits and hits & {'N', 'D', 'A'}) or {'N', 'D'} <= hits or {'N', 'A'} <= hits


def match(args):
    f = bc.Fetcher(CACHE, budget=args.budget, network=args.download, prior=0, opener=vc.opener, min_interval=args.interval)
    out, stats = [], Counter()
    listings, names = {}, {}
    try:
        for r in reviews(args.work):
            why = eligible(r)
            rec = {k: r.get(k) for k in ('doc_id', 'n', 'outcome', 'role', 'official_involved', 'stage', 'buyer_code', 'buyer_name', 'supplier_code', 'supplier_name',
                                         'contract_number', 'contract_date', 'procurement_year', 'amount_uah', 'cpv', 'via_prozorro')}
            if why:
                stats[why] += 1
                continue
            buyer, year = buyer_code(r), year_of(r)
            rec['buyer_code_from'] = 'verdict' if buyer else 'name search'
            if not buyer:
                if r.get('buyer_name') not in names:
                    names[r.get('buyer_name')] = resolve_buyer(f, r['buyer_name'])
                buyer = names[r.get('buyer_name')]
                rec['buyer_code'] = buyer
            if not buyer:
                stats['buyer name not resolved'] += 1
                out.append({**rec, 'state': 'buyer name not resolved', 'matches': []})
                continue
            years = [year]
            signed = day(r.get('contract_date'))
            if signed and signed.month <= 3 and str(signed.year) == year:
                years.append(str(signed.year - 1))
            listed, complete = [], True
            for y in years:
                if (buyer, y) not in listings:
                    try:
                        listings[buyer, y] = census.census(f, {(buyer, y)})
                    except RuntimeError as e:     # a search page that does not answer: no listing
                        print(f'listing failed {buyer} {y}: {e}', file=sys.stderr)
                        listings[buyer, y] = ({}, [(buyer, y, 'error')])
                tenders, incomplete = listings[buyer, y]
                listed += list(tenders.values())
                complete = complete and not incomplete
            matched = []
            for tid in shortlist(r, listed):
                tender = vc.resolve(f, tid)
                hits = evidence(r, tender) if tender else set()
                if is_match(hits):
                    matched.append({'tenderID': tid, 'evidence': ''.join(sorted(hits))})
            state = 'linked' if len(matched) == 1 else 'ambiguous' if matched else 'no match'
            stats[state] += 1
            out.append({**rec, 'listed': len(listed), 'listing_complete': complete, 'state': state, 'matches': matched})
    except (bc.BudgetExceeded, bc.Blocked, bc.Throttled) as e:
        print(f'stopped: {e}', file=sys.stderr)
        stats['stopped'] += 1
    MATCHES.write_text(json.dumps({'status': 'research links by buyer code; rules in research/calibration/ukraine-verdict-linking-plan.md; '
                                   'not owner-approved', 'generated': sw.now(), 'counts': dict(stats), 'requests': f.requests,
                                   'procurements': out}, ensure_ascii=False, indent=1) + '\n')
    print(dict(stats), f'requests {f.requests}')


# Part B: AMCU bid-rigging judgments without a tender ID, linked by the colluding bidders' codes.
AMCU_WORK = Path.home() / '.cache/contract-signals/verdict-work/amcu-link'
AMCU_MATCHES = ROOT / 'research/labels/ukraine-amcu-link-matches.json'
AMCU_LINKED = ROOT / 'research/labels/ukraine-amcu-linked.json'
MIN_BIDDERS = 2
AMCU_COMPETITIVE_CAP = 40      # shortlist when a description gives neither expected value nor CPV


def bidder_codes(desc):
    return sorted({c for c in map(code, desc.get('bidder_codes') or []) if c})


def amcu_eligible(desc):
    """A tender description that could become a bid-rigging label and can be searched."""
    if desc.get('collusion_found') != 'yes' or desc.get('via_prozorro') == 'no':
        return 'not a label'
    if len(bidder_codes(desc)) < MIN_BIDDERS:
        return 'fewer than 2 bidder codes'
    if not buyer_code(desc) and not name(desc.get('buyer_name')):
        return 'no buyer code or name'
    y = str(desc.get('year') or desc.get('date') or '')[:4]
    if not re.fullmatch(r'20\d\d', y) or y < '2016':
        return 'no year or before 2016'
    return None


def as_procurement(desc):
    """The description in part A's terms, so the same shortlist applies (expected value as the amount)."""
    return {'amount_uah': desc.get('expected_value_uah'), 'cpv': desc.get('cpv'), 'contract_date': None}


def amcu_shortlist(desc, listed):
    """Part A's shortlist by value or CPV; with neither, the buyer-year's competitive tenders, nearest the printed date first."""
    if amount(as_procurement(desc)) is not None or cpv5(desc.get('cpv')):
        return shortlist(as_procurement(desc), listed)
    when = day(desc.get('date'))
    picked = []
    for t in listed:
        if t.get('kind') != 'competitive':
            continue
        end = day(((t.get('tenderPeriod') or {}).get('endDate')) or ((t.get('enquiryPeriod') or {}).get('endDate')))
        picked.append((abs((end - when).days) if when and end else 0, t['tenderID']))
    return [tid for _, tid in sorted(picked)[:AMCU_COMPETITIVE_CAP]]


def tender_bidders(tender):
    out = set()
    for b in tender.get('bids') or []:
        out |= {code((t.get('identifier') or {}).get('id')) for t in b.get('tenderers') or []}
    for aw in tender.get('awards') or []:
        out |= {code((s.get('identifier') or {}).get('id')) for s in aw.get('suppliers') or []}
    out.discard(None)
    return out


def amcu_match(args):
    f = bc.Fetcher(CACHE, budget=args.budget, network=args.download, prior=0, opener=vc.opener, min_interval=args.interval)
    cases = {}
    for line in (Path(args.work) / 'items.jsonl').read_text().splitlines():
        item = json.loads(line)
        cases[str(item['doc_id'])] = item
    out, stats = [], Counter()
    listings, names = {}, {}
    try:
        for desc in reviews(args.work):
            item = cases.get(str(desc.get('doc_id')))
            why = 'not a reviewed case' if not item else amcu_eligible(desc)
            rec = {k: desc.get(k) for k in ('doc_id', 'n', 'buyer_code', 'buyer_name', 'year', 'date', 'cpv', 'expected_value_uah', 'via_prozorro')}
            rec['bidder_codes'] = bidder_codes(desc)
            if why:
                stats[why] += 1
                continue
            buyer, year = buyer_code(desc), str(desc.get('year') or desc.get('date'))[:4]
            rec['buyer_code_from'] = 'judgment' if buyer else 'name search'
            if not buyer:
                if desc.get('buyer_name') not in names:
                    names[desc.get('buyer_name')] = resolve_buyer(f, desc['buyer_name'])
                buyer = rec['buyer_code'] = names[desc.get('buyer_name')]
            if not buyer:
                stats['buyer name not resolved'] += 1
                out.append({**rec, 'state': 'buyer name not resolved', 'matches': []})
                continue
            if (buyer, year) not in listings:
                try:
                    listings[buyer, year] = census.census(f, {(buyer, year)})
                except RuntimeError as e:
                    print(f'listing failed {buyer} {year}: {e}', file=sys.stderr)
                    listings[buyer, year] = ({}, [(buyer, year, 'error')])
            tenders, incomplete = listings[buyer, year]
            named, matched = set(rec['bidder_codes']), []
            for tid in amcu_shortlist(desc, list(tenders.values())):
                tender = vc.resolve(f, tid)
                common = named & tender_bidders(tender) if tender else set()
                if len(common) >= MIN_BIDDERS:
                    matched.append({'tenderID': tid, 'bidders_found': len(common)})
            state = 'linked' if len(matched) == 1 else 'ambiguous' if matched else 'no match'
            stats[state] += 1
            out.append({**rec, 'case_number': item['case_number'], 'listed': len(tenders), 'listing_complete': not incomplete,
                        'state': state, 'matches': matched})
    except (bc.BudgetExceeded, bc.Blocked, bc.Throttled) as e:
        print(f'stopped: {e}', file=sys.stderr)
        stats['stopped'] += 1
    AMCU_MATCHES.write_text(json.dumps({'status': 'research links by bidder codes; rules in research/calibration/ukraine-verdict-linking-plan.md '
                                        'part B; not owner-approved', 'generated': sw.now(), 'counts': dict(stats), 'requests': f.requests,
                                        'descriptions': out}, ensure_ascii=False, indent=1) + '\n')
    print(dict(stats), f'requests {f.requests}')


def amcu_labels(args):
    am = load('amcu_cases', 'tools/sweep-ukraine-amcu-cases.py')
    courts = {r['doc_id']: r['court'] for r in am.load_selected()}
    cases = {}
    for line in (Path(args.work) / 'items.jsonl').read_text().splitlines():
        item = json.loads(line)
        cases[str(item['doc_id'])] = item
    out, seen = [], set()
    for d in json.loads(AMCU_MATCHES.read_text())['descriptions']:
        if d['state'] != 'linked':
            continue
        item, tid = cases[str(d['doc_id'])], d['matches'][0]['tenderID']
        if (item['case_number'], tid) in seen:
            continue
        seen.add((item['case_number'], tid))
        top = {'instance': item['decisive_instance'], 'adjudication_date': item['decisive_date']}
        out.append({'reyestr_id': item['decisive_doc_id'], 'case_number': item['case_number'], 'court': courts.get(item['decisive_doc_id'], ''),
                    'verdict_date': item['decisive_date'], 'tender_id_normalised': tid, 'proposed_label': am.LABEL,
                    'source': 'commercial-court judgment on an AMCU decision', 'linked': 'bidder codes',
                    'link_evidence': f"{d['matches'][0]['bidders_found']} named bidders", 'reviewed_judgment': str(d['doc_id']),
                    'verification': {'finality': am.finality_text(top), 'stage': 'award (collusion)'}})
    AMCU_LINKED.write_text(json.dumps({'status': 'proposed research labels: AMCU bid-rigging judgments without a tender ID linked by bidder codes '
                                       '(model extraction, rule-based match); not owner-approved', 'generated': sw.now(),
                                       'counts': {'tender labels': len(out), 'cases': len({v['case_number'] for v in out})},
                                       'verdicts': out}, ensure_ascii=False, indent=1) + '\n')
    print(len(out), 'linked tenders from', len({v['case_number'] for v in out}), 'cases')


def linked_rows():
    data = json.loads(MATCHES.read_text())['procurements']
    return [p for p in data if p['state'] == 'linked']


def finality(args):
    path = sw.BASE / 'finality.json'
    pages = json.loads(path.read_text()) if path.exists() else {}
    f = bc.Fetcher(sw.PAGES, budget=args.budget, network=True, min_interval=args.interval, opener=sw.opener('text/html'), prior=0)
    try:
        for doc in sorted({str(p['doc_id']) for p in linked_rows()}):
            if doc in pages:
                continue
            hit = f.fetch(f'https://reyestr.court.gov.ua/Review/{doc}')
            body = sw.decode(hit['body']) if hit and hit['body'] else ''
            m = sw.FORCE_RE.search(body)
            pages[doc] = f'{m.group(3)}-{m.group(2)}-{m.group(1)}' if m else ('no date shown' if 'Review' in body or 'реєстр' in body else 'page unreadable')
            path.write_text(json.dumps(pages, indent=1))
    except (bc.BudgetExceeded, bc.Blocked, bc.Throttled) as e:
        print(f'stopped: {e}')


def labels(args):
    pages = json.loads((sw.BASE / 'finality.json').read_text()) if (sw.BASE / 'finality.json').exists() else {}
    selected = {r['doc_id']: r for r in sw.load_selected(only_verdicts=True)}
    higher = sw.appeals(sw.stream_selected())
    out = []
    for p in linked_rows():
        s = selected[str(p['doc_id'])]
        verdict = {'verdict_date': s['adjudication_date'],
                   'later_higher_court_decisions': [d for d in higher.get(s['cause_num'], []) if d['adjudication_date'] >= s['adjudication_date'] and d['doc_id'] != s['doc_id']]}
        row = {'outcome': p['outcome'], 'tender_role': p['role'], 'official_involved': p['official_involved']}
        out.append({'reyestr_id': s['doc_id'], 'reyestr_url': f'https://reyestr.court.gov.ua/Review/{s["doc_id"]}', 'case_number': s['cause_num'],
                    'court': s['court'], 'verdict_date': s['adjudication_date'], 'articles': [s['article']], 'outcome': p['outcome'],
                    'tender_id_normalised': p['matches'][0]['tenderID'], 'tender_role': p['role'], 'linked': 'buyer code',
                    'link_evidence': p['matches'][0]['evidence'], 'entry_into_force': pages.get(s['doc_id']),
                    'verification': {'finality': sw.finality_state(verdict, pages.get(s['doc_id'])), 'official_involved': p['official_involved'],
                                     'stage': p['stage']},
                    'proposed_label': sw.proposed_label(row)})
    LINKED.write_text(json.dumps({'status': 'proposed labels: verdicts without a tender ID linked by buyer code (model extraction, '
                                  'rule-based match); not owner-approved', 'generated': sw.now(),
                                  'counts': dict(Counter(v['proposed_label'] for v in out)), 'verdicts': out}, ensure_ascii=False, indent=1) + '\n')
    print(len(out), 'linked tenders', Counter(v['proposed_label'] for v in out))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    mp = sub.add_parser('match')
    mp.add_argument('--work', default=str(WORK))
    mp.add_argument('--download', action='store_true')
    mp.add_argument('--budget', type=int, default=40_000)
    mp.add_argument('--interval', type=float, default=1.0)
    fp = sub.add_parser('finality')
    fp.add_argument('--budget', type=int, default=sw.PAGE_CAP)
    fp.add_argument('--interval', type=float, default=sw.PAGE_INTERVAL)
    sub.add_parser('labels')
    ap = sub.add_parser('amcu-match')
    ap.add_argument('--work', default=str(AMCU_WORK))
    ap.add_argument('--download', action='store_true')
    ap.add_argument('--budget', type=int, default=40_000)
    ap.add_argument('--interval', type=float, default=1.0)
    al = sub.add_parser('amcu-labels')
    al.add_argument('--work', default=str(AMCU_WORK))
    args = p.parse_args(argv)
    {'match': match, 'finality': finality, 'labels': labels, 'amcu-match': amcu_match, 'amcu-labels': amcu_labels}[args.cmd](args)


if __name__ == '__main__':
    main()
