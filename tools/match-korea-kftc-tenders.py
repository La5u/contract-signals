#!/usr/bin/env python3
"""Research only: link the rigged tenders extracted from KFTC decisions to KONEPS open-standard contracts.

Input: ftc/extract/checked.jsonl (tools/extract-korea-kftc-tenders.py --check) and opnstd.sqlite `versions`
(tools/normalize-korea-opnstd.py; contracts signed 2010-01..2026-09). One pass over the versions keeps the rows
whose supplier, amount or notice number could belong to a tender, then each tender is matched at the notice level
(one KONEPS notice, possibly several contracts: lots, long-term yearly contracts, changes):

- `notice`: the decision prints the KONEPS notice number and it is in the data.
- `amount`: winner name + award amount equal to the contract amount, signed within the tender's date window.
- `amount-buyer`: masked or unmatched winner name, but award amount + buyer + date window.
- `buyer-name`: winner + buyer (+ lot) + date window + similar tender name (character bigrams): the only candidate
  at similarity ≥ 0.4, or ≥ 0.5 and 0.15 ahead of the next.

Accepted only when exactly one notice is left (plan: korea-labels-plan.md, "accepted only when it leaves one
notice"); ties and misses are written as `ambiguous` / `unmatched` with their candidates, never guessed.
Output: ftc/extract/links.jsonl, and a summary on stdout.
"""
import argparse
import datetime as dt
import json
import os
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import to_int  # noqa: E402

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea'
COLS = ['cntrct_no', 'ord', 'signed', 'name', 'notice_no', 'notice_name', 'opening_date', 'amount', 'total_amount',
        'reserve_price', 'method', 'business_type', 'joint', 'buyer_name', 'buyer_code', 'demand_name',
        'demand_code', 'supplier_name', 'supplier_bizrno']
GENERIC = {'조달청', '지방조달청', '본청', '본부', '사업소', '사업본부', '건설본부', '교육청', '교육지원청', '주식회사',
           '공사', '공단', '한국', '특별시', '광역시', '특별자치시', '특별자치도', '시청', '군청', '구청', '도청'}
REGIONS = {'서울특별시', '부산광역시', '대구광역시', '인천광역시', '광주광역시', '대전광역시', '울산광역시', '세종특별자치시',
           '경기도', '강원도', '강원특별자치도', '충청북도', '충청남도', '전라북도', '전북특별자치도', '전라남도', '경상북도',
           '경상남도', '제주특별자치도', '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '경기', '강원', '충북',
           '충남', '전북', '전남', '경북', '경남', '제주'}


def norm_name(s):
    return re.sub(r'(주식회사|유한회사|합자회사|합명회사|\(주\)|\(유\)|\(합\)|㈜|컨소시엄|공동수급체|\W)', '', s or '')


def masked(s):
    return not norm_name(s) or bool(re.search(r'[☆★●○◎◇◆□■△▲▽▼]|^[A-Z가-힣]사$', s or ''))


def parse_date(s):
    m = re.match(r'(\d{4})[-.]\s*(\d{1,2})[-.]\s*(\d{1,2})', str(s or ''))
    if m:
        try:
            return dt.date(*map(int, m.groups()))
        except ValueError:
            return None


def window(t):
    """Dates a contract for this tender can be signed on."""
    d = parse_date(t.get('contract_date'))
    if d:
        return d - dt.timedelta(days=10), d + dt.timedelta(days=30)
    for key, before in (('opening_date', 3), ('notice_date', 0)):  # signed after the tender opened
        d = parse_date(t.get(key))
        if d:
            return d - dt.timedelta(days=before), d + dt.timedelta(days=400)
    decided = parse_date(t.get('decision_date'))
    if decided:  # no tender date read: anything in the ten years before the decision
        return decided - dt.timedelta(days=3650), decided
    return dt.date(2000, 1, 1), dt.date(2100, 1, 1)


def bigrams(s):
    s = re.sub(r'\W', '', s or '')
    return {s[i:i + 2] for i in range(len(s) - 1)}


def similarity(a, b):
    a, b = bigrams(a), bigrams(b)
    return len(a & b) / len(a | b) if a and b else 0.0


def name_overlap(t, c):
    """Share of the shorter name's bigrams found in the other (tender name vs contract or notice name); None if unknown."""
    a = bigrams(t.get('tender_name'))
    if not a:
        return None
    best = 0.0
    for name in (c.get('name'), c.get('notice_name')):
        b = bigrams(name)
        if b:
            best = max(best, len(a & b) / min(len(a), len(b)))
    return best


def plausible(t, c, award):
    """A notice-number or amount-only candidate must agree with the tender on something else."""
    overlap = name_overlap(t, c)
    if overlap is not None and overlap >= 0.3:
        return True
    if award and award in (c.get('amount'), c.get('total_amount')):
        return overlap is None
    return False


def unrelated(t, r):
    """Same winner and amount by coincidence: neither the buyer nor the tender name agrees."""
    overlap = name_overlap(t, r)
    return overlap is not None and overlap < 0.2 and not buyer_match(t, r)


def buyer_tokens(buyer):
    out = set()
    for tok in re.split(r'[\s/,()·]+', buyer or ''):
        tok = re.sub(r'\W', '', tok)
        if len(tok) >= 2 and tok not in GENERIC:
            out.add(tok)
    return out


def buyer_match(t, r):
    toks = buyer_tokens(t.get('buyer'))
    toks = toks - REGIONS or toks  # "충청남도 홍성군" must not match "충청남도 아산시"
    hay = re.sub(r'\W', '', (r['buyer_name'] or '') + (r['demand_name'] or ''))
    return bool(toks) and any(tok in hay for tok in toks)


def lot_filter(t, rows):
    """Keep rows whose contract or notice name carries the tender's lot (제1구역 must not match 제11구역)."""
    lot = t.get('lot')
    if not lot or not rows:
        return rows
    m = re.search(r'(\d+)\s*(구역|공구|권역|분류|분야|블록|단계|지구|구간|호선|권|군|조|차)', str(lot))
    if m:
        pattern = re.compile(rf'(?<!\d){m.group(1)}\s*{m.group(2)}')
    else:
        pattern = re.compile(re.escape(re.sub(r'\s', '', str(lot))))
    kept = [r for r in rows if pattern.search(re.sub(r'\s', '', (r['name'] or '') + '|' + (r['notice_name'] or '')))]
    return kept or rows


def load_tenders(path):
    tenders = []
    for line in open(path):
        t = json.loads(line)
        if t.get('tender_name') == 'UNLISTED' or t.get('buyer_public') is False:
            continue
        tenders.append(t)
    return tenders


def scan(db, tenders):
    names = {norm_name(t.get('winner')) for t in tenders if not masked(t.get('winner'))}
    amounts = {to_int(t.get('award_amount')) for t in tenders} - {None}
    notices = {str(t['notice_no']).split('-')[0].strip() for t in tenders if t.get('notice_no')}
    rows = defaultdict(list)  # key -> rows, keys: ('n', name) / ('a', amount) / ('no', notice)
    con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    seen = 0
    for rec in con.execute(f'SELECT {", ".join(COLS)} FROM versions'):
        seen += 1
        r = dict(zip(COLS, rec))
        n, a, no = norm_name(r['supplier_name']), r['amount'], (r['notice_no'] or '').strip()
        if n in names:
            rows[('n', n)].append(r)
        if a in amounts:
            rows[('a', a)].append(r)
        if no in notices:
            rows[('no', no)].append(r)
    return rows, seen


def in_window(r, lo, hi):
    d = parse_date(r['signed'])
    return bool(d) and lo <= d <= hi


def notice_key(r):
    return (r['notice_no'] or '').strip() or f'contract:{r["cntrct_no"]}'


def summarize(rows):
    by = defaultdict(list)
    for r in rows:
        by[notice_key(r)].append(r)
    out = []
    for key, rs in by.items():
        first = min(rs, key=lambda r: (r['signed'] or '', r['ord'] or 0))
        out.append({'notice_no': key, 'contracts': sorted({r['cntrct_no'] for r in rs}),
                    'signed': first['signed'], 'name': first['name'], 'notice_name': first['notice_name'],
                    'amount': first['amount'], 'buyer': first['buyer_name'], 'buyer_code': first['buyer_code'],
                    'demand': first['demand_name'], 'supplier': first['supplier_name'],
                    'supplier_bizrno': first['supplier_bizrno'], 'method': first['method']})
    return out


def match(t, rows):
    lo, hi = window(t)
    winner, award = norm_name(t.get('winner')), to_int(t.get('award_amount'))
    notice = str(t.get('notice_no') or '').split('-')[0].strip()
    if notice:
        found = rows.get(('no', notice), [])
        hit = summarize(found)
        if hit and (any(plausible(t, c, award) for c in hit)
                    or (not award and not t.get('tender_name') and any(buyer_match(t, r) for r in found))):
            return 'notice', hit
        if hit:  # the printed number belongs to some other notice (misread, or a different numbering)
            t.setdefault('problems', []).append(f'notice {notice} in KONEPS but name/amount disagree')
    by_winner = [] if masked(t.get('winner')) else [r for r in rows.get(('n', winner), []) if in_window(r, lo, hi)]
    if award:
        exact = [r for r in by_winner if award in (r['amount'], r['total_amount']) and not unrelated(t, r)]
        cands = summarize(exact)
        if len(cands) == 1:
            return 'amount', cands
        if len(cands) > 1:
            narrowed = summarize(lot_filter(t, [r for r in exact if buyer_match(t, r)]))
            return ('amount', narrowed) if len(narrowed) == 1 else ('ambiguous', cands)
        by_amount = lot_filter(t, [r for r in rows.get(('a', award), []) if in_window(r, lo, hi) and buyer_match(t, r)])
        cands = [c for c in summarize(by_amount) if name_overlap(t, c) is None or name_overlap(t, c) >= 0.3]
        if len(cands) == 1:
            return 'amount-buyer', cands
        if len(cands) > 1:
            return 'ambiguous', cands
    pool = summarize(lot_filter(t, [r for r in by_winner if buyer_match(t, r)]))
    for c in pool:
        c['similarity'] = round(max(similarity(t.get('tender_name'), c['name']),
                                    similarity(t.get('tender_name'), c['notice_name'])), 3)
    pool.sort(key=lambda c: -c['similarity'])
    if len(pool) == 1 and pool[0]['similarity'] >= 0.4:
        return 'buyer-name', pool
    if len(pool) > 1 and pool[0]['similarity'] >= 0.5 and pool[0]['similarity'] - pool[1]['similarity'] >= 0.15:
        return 'buyer-name', pool[:1]
    if pool and pool[0]['similarity'] >= 0.3:
        return 'ambiguous', pool[:5]
    return 'unmatched', pool[:3]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--tenders', type=Path, default=BASE / 'ftc/extract/checked.jsonl')
    parser.add_argument('--db', type=Path, default=BASE / 'opnstd.sqlite')
    parser.add_argument('--out', type=Path, default=BASE / 'ftc/extract/links.jsonl')
    args = parser.parse_args()
    tenders = load_tenders(args.tenders)
    rows, seen = scan(args.db, tenders)
    counts = defaultdict(int)
    with open(args.out, 'w') as f:
        for t in tenders:
            how, cands = match(t, rows)
            counts[how] += 1
            f.write(json.dumps({'serial': t['serial'], 'i': t['i'], 'case_no': t.get('case_no'),
                                'buyer': t.get('buyer'), 'tender_name': t.get('tender_name'),
                                'winner': t.get('winner'), 'award_amount': t.get('award_amount'),
                                'opening_date': t.get('opening_date'), 'problems': t.get('problems'),
                                'link': how, 'candidates': cands}, ensure_ascii=False) + '\n')
    print(json.dumps({'versions_scanned': seen, 'tenders': len(tenders), **counts}, indent=1))


if __name__ == '__main__':
    main()
