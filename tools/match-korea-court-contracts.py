#!/usr/bin/env python3
"""Research only: link the contracts named in Korean court rulings to KONEPS notices and contracts.

Input: prec/extract/checked.jsonl (tools/extract-korea-court-rulings.py --check), bid openings in bids/bids/<type>/<day>
(tools/fetch-korea-bid-results.py) and opnstd.sqlite `versions`. Only relevant rulings, public buyers and contracts
from 2010 on (the KONEPS download) are matched; the same contract named under several findings is matched once.

Routes, in order (the first that leaves exactly one notice wins):
- `notice`: the ruling prints the notice number (KFTC matcher rule).
- `bid-opening`: the ruling gives the opening day; among that day's openings, the buyer matches and the name is
  similar (as `buyer-name` below) or a bid equals the ruling's amount. The notice found is then joined to contracts.
- `amount` / `amount-buyer` / `buyer-name`: the KFTC matcher on the contract records, with court masking
  (공소외 1 주식회사, 피고인 2 회사, ...) treated as an unknown supplier and a contract year as the date window
  when no day is given.
- `buyer-only`: supplier masked or not found: buyer + date window + contract name similarity ≥ 0.5 (≥ 0.4 when the
  ruling's amount equals the contract amount), the only candidate, or ≥ 0.6 and 0.2 ahead of the next.
Ties and misses are written as `ambiguous` / `unmatched` with their candidates, never guessed.
Output: prec/extract/links.jsonl, and a summary on stdout.
"""
import argparse
import datetime as dt
import gzip
import importlib.util
import json
import os
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('kmatch', HERE / 'match-korea-kftc-tenders.py')
km = importlib.util.module_from_spec(spec)
spec.loader.exec_module(km)

BASE = km.BASE
BID_TYPES = ('works', 'services', 'goods', 'foreign')
COURT_MASK = re.compile(r'공소외|피고인|피해자|성명불상|[A-Za-z]\s*(주식회사|회사|업체)|^[A-Z가-힣]$|[○◎◇◆□■△▲▽▼☆★●♤♡◈◐▤◁▷]')

kftc_masked = km.masked
km.masked = lambda s: kftc_masked(s) or bool(COURT_MASK.search(s or ''))
kftc_window = km.window


def window(t):
    if any(km.parse_date(t.get(k)) for k in ('contract_date', 'opening_date', 'notice_date')):
        return kftc_window(t)
    m = re.match(r'(\d{4})-(\d{1,2})', str(t.get('contract_date') or t.get('opening_date') or t.get('notice_date') or ''))
    if m:  # month only
        start = dt.date(int(m.group(1)), int(m.group(2)), 1)
        return start - dt.timedelta(days=10), start + dt.timedelta(days=62)
    if t.get('year'):
        return dt.date(t['year'], 1, 1), dt.date(t['year'], 12, 31) + dt.timedelta(days=30)
    return kftc_window(t)


km.window = window


def contract_year(c):
    if isinstance(c.get('year'), int):
        return c['year']
    for k in ('contract_date', 'opening_date', 'notice_date'):
        m = re.match(r'(\d{4})', str(c.get(k) or ''))
        if m:
            return int(m.group(1))


def load(path):
    """One tender-like dict per distinct contract named in a relevant ruling."""
    out = []
    for line in open(path):
        r = json.loads(line)
        res = r.get('result') or {}
        if not res.get('relevant'):
            continue
        case = res.get('case') or {}
        seen = {}
        for fi, f in enumerate(res.get('findings') or []):
            for c in f.get('contracts') or []:
                year = contract_year(c)
                if c.get('buyer_public') is False or not year or year < 2010:
                    continue
                key = (re.sub(r'\W', '', c.get('buyer') or ''), re.sub(r'\W', '', c.get('contract_name') or ''),
                       c.get('contract_date'), c.get('amount'), c.get('supplier'))
                if key in seen:  # e.g. the same contract under 뇌물수수 and 뇌물공여
                    seen[key]['findings'].append({'offence': f.get('offence'), 'proven': f.get('proven')})
                    continue
                t = {'serial': r['serial'], 'i': len(seen), 'case_no': case.get('case_no'), 'court': case.get('court'),
                     'level': case.get('level'), 'decision_date': case.get('decision_date'),
                     'outcome': case.get('outcome'), 'kind': case.get('kind'),
                     'lower_case_nos': case.get('lower_case_nos'), 'ruling_problems': r.get('problems'),
                     'findings': [{'offence': f.get('offence'), 'proven': f.get('proven')}],
                     'buyer': c.get('buyer'), 'buyer_public': c.get('buyer_public'),
                     'tender_name': c.get('contract_name'), 'contract_kind': c.get('contract_kind'),
                     'procedure': c.get('procedure'), 'notice_no': c.get('notice_no'),
                     'notice_date': c.get('notice_date'), 'opening_date': c.get('opening_date'),
                     'contract_date': c.get('contract_date'), 'year': year, 'award_amount': c.get('amount'),
                     'amount_kind': c.get('amount_kind'), 'winner': c.get('supplier'), 'quote': c.get('quote')}
                seen[key] = t
                out.append(t)
    return out


def opening_days(tenders):
    return sorted({str(t['opening_date'])[:10] for t in tenders if km.parse_date(t.get('opening_date'))})


def bid_openings(day):
    """Openings of one day: notice -> {name, buyers, amounts}; None when the day is not downloaded."""
    found, any_file = {}, False
    for kind in BID_TYPES:
        f = BASE / 'bids/bids' / kind / f'{day}.jsonl.gz'
        if not f.exists():
            continue
        any_file = True
        with gzip.open(f, 'rt') as fh:
            for line in fh:
                b = json.loads(line)
                n = found.setdefault(b['bidNtceNo'], {'notice_no': b['bidNtceNo'], 'name': b.get('bidNtceNm'),
                                                      'buyer_name': b.get('ntceInsttNm'),
                                                      'demand_name': b.get('dmndInsttNm'), 'amounts': set(),
                                                      'bidders': 0})
                n['bidders'] += 1
                for k in ('bidprcAmt', 'fnlSucsfAmt'):
                    a = km.to_int(b.get(k))
                    if a:
                        n['amounts'].add(a)
    return found if any_file else None


def match_bids(t, day_openings):
    award = km.to_int(t.get('award_amount'))
    cands = []
    for n in day_openings.values():
        if not km.buyer_match(t, n):
            continue
        sim = km.similarity(t.get('tender_name'), n['name'])
        if (award and award in n['amounts']) or sim >= 0.4:
            cands.append({'notice_no': n['notice_no'], 'name': n['name'], 'buyer': n['buyer_name'],
                          'demand': n['demand_name'], 'bidders': n['bidders'], 'similarity': round(sim, 3),
                          'amount_in_bids': bool(award and award in n['amounts'])})
    cands.sort(key=lambda c: (-c['amount_in_bids'], -c['similarity']))
    if len(cands) == 1:
        return cands
    if len(cands) > 1 and (cands[0]['amount_in_bids'] and not cands[1]['amount_in_bids']
                           or cands[0]['similarity'] - cands[1]['similarity'] >= 0.15 and cands[0]['similarity'] >= 0.5):
        return cands[:1]
    return None


BUYER_CHUNK = 400  # tenders per buyer-only scan (one pass over the versions each)


def scan_buyers(db, tenders):
    """Contract rows of the tenders' buyers in their years, for the `buyer-only` route: (buyer, demand) pairs first,
    then one pass over the versions."""
    con = km.sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    pairs = con.execute('SELECT DISTINCT buyer_name, demand_name FROM versions').fetchall()
    want = defaultdict(set)  # pair -> tender indexes
    for i, t in enumerate(tenders):
        for b, d in pairs:
            if km.buyer_match(t, {'buyer_name': b, 'demand_name': d}):
                want[(b, d)].add(i)
    years = defaultdict(set)
    for pair, idx in want.items():
        for i in idx:
            years[pair] |= {str(tenders[i]['year'] + k) for k in (-1, 0, 1)}
    by_tender = defaultdict(list)
    for rec in con.execute(f'SELECT {", ".join(km.COLS)} FROM versions'):
        r = dict(zip(km.COLS, rec))
        pair = (r['buyer_name'], r['demand_name'])
        if pair in want and (r['signed'] or '')[:4] in years[pair]:
            for i in want[pair]:
                by_tender[i].append(r)
    return by_tender


def match_buyer_only(t, rows):
    """Buyer + date window + similar contract name (+ the amount when the ruling gives one), supplier unknown."""
    lo, hi = window(t)
    award = km.to_int(t.get('award_amount'))
    rs = [r for r in rows if km.in_window(r, lo, hi) and (not award or award in (r['amount'], r['total_amount']))]
    pool = km.summarize(km.lot_filter(t, rs))
    for c in pool:
        c['similarity'] = round(max(km.similarity(t.get('tender_name'), c['name']),
                                    km.similarity(t.get('tender_name'), c['notice_name'])), 3)
    pool.sort(key=lambda c: -c['similarity'])
    if len(pool) == 1 and pool[0]['similarity'] >= (0.4 if award else 0.5):
        return 'buyer-only', pool
    if len(pool) > 1 and pool[0]['similarity'] >= 0.6 and pool[0]['similarity'] - pool[1]['similarity'] >= 0.2:
        return 'buyer-only', pool[:1]
    if pool and pool[0]['similarity'] >= 0.4:
        return 'ambiguous', pool[:5]
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rulings', type=Path, default=BASE / 'prec/extract/checked.jsonl')
    parser.add_argument('--db', type=Path, default=BASE / 'opnstd.sqlite')
    parser.add_argument('--out', type=Path, default=BASE / 'prec/extract/links.jsonl')
    parser.add_argument('--days-out', type=Path, default=BASE / 'bids-court-days.txt',
                        help='opening days named by rulings, for fetch-korea-bid-results.py bids --days')
    args = parser.parse_args()
    tenders = load(args.rulings)
    days = opening_days(tenders)
    args.days_out.write_text(''.join(d + '\n' for d in days))
    bid_hits, missing_days = {}, set()
    for day in days:
        openings = bid_openings(day)
        if openings is None:
            missing_days.add(day)
            continue
        for t in tenders:
            if str(t.get('opening_date') or '')[:10] == day and not t.get('notice_no'):
                hit = match_bids(t, openings)
                if hit:
                    bid_hits[(t['serial'], t['i'])] = hit[0]
                    t['notice_no'] = hit[0]['notice_no']
                    t['notice_from_bids'] = True
    rows, seen = km.scan(args.db, tenders)
    first = [km.match(t, rows) for t in tenders]
    # The buyer-only route keeps every contract of a tender's buyer in its years, so it runs only for the tenders the
    # other routes left open, in chunks: all at once ran out of memory on 5,838 audit contracts (2026-10-24).
    need = [ti for ti, (how, _) in enumerate(first) if how in ('unmatched', 'ambiguous') and tenders[ti].get('tender_name')]
    buyer_rows = {}
    for k in range(0, len(need), BUYER_CHUNK):
        part = need[k:k + BUYER_CHUNK]
        got = scan_buyers(args.db, [tenders[ti] for ti in part])
        for j, ti in enumerate(part):
            if j in got:
                buyer_rows[ti] = got[j]
        for ti in part:   # matched right away, then dropped, so memory holds one chunk
            alt = match_buyer_only(tenders[ti], buyer_rows.pop(ti, []))
            buyer_rows[ti] = alt
    counts = defaultdict(int)
    with open(args.out, 'w') as f:
        for ti, t in enumerate(tenders):
            how, cands = first[ti]
            if how in ('unmatched', 'ambiguous') and t.get('tender_name'):
                alt = buyer_rows.get(ti)
                if alt and (alt[0] == 'buyer-only' or how == 'unmatched'):
                    how, cands = alt
            if t.get('notice_from_bids'):
                if how == 'notice':
                    how = 'bid-opening'
                else:  # the opening has no contract in the data (or the name disagreed): keep the notice
                    how, cands = 'bid-opening-no-contract', [bid_hits[(t['serial'], t['i'])]] + (cands or [])
            counts[how] += 1
            f.write(json.dumps({**{k: t.get(k) for k in (
                'serial', 'i', 'case_no', 'court', 'level', 'decision_date', 'outcome', 'findings', 'buyer',
                'tender_name', 'winner', 'award_amount', 'amount_kind', 'contract_date', 'opening_date', 'year',
                'procedure', 'quote', 'ruling_problems', 'problems')}, 'link': how, 'candidates': cands},
                ensure_ascii=False) + '\n')
    print(json.dumps({'versions_scanned': seen, 'contracts': len(tenders),
                      'rulings': len({t['serial'] for t in tenders}), 'opening_days': len(days),
                      'opening_days_not_downloaded': len(missing_days), **counts}, indent=1))


if __name__ == '__main__':
    main()
