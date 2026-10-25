#!/usr/bin/env python3
"""Research only: link KFTC rigged MAS second-stage tenders to shopping-mall delivery requests (납품요구).

Input: ftc/extract/checked.jsonl and ftc/extract/links.jsonl (only tenders left `unmatched` by the KONEPS matcher),
and datahub-items/<class>/<year>.csv.gz (tools/fetch-korea-datahub-items.py, report UI-ADOXFA-190R).

A delivery request is rebuilt from its original version (변경차수 00): its item lines are summed over every
downloaded goods class and year (a request for pipe, fittings and manholes spans three classes; a yearly file holds
the versions dated in that year). Only requests marked 이단계경쟁제안서제출여부 = Y (awarded through a second-stage
competition) are candidates. A tender is linked (`amount`) when exactly one request has the tender's award
amount (± 0.05 %, at least 10 KRW) and a tender-name similarity ≥ 0.3. Name similarity alone is not enough: sister
projects differ by one character (군산/온산 처리구역, both 1차분, amounts 2.5 % apart).
Requests include VAT; decisions print awards with VAT (15581) or without (14663), so both award and award × 1.1
are tried.

Supplier names in the report are today's names (한국화이바 = 스페이스프로, same business number), so the
winner is not compared by name; the summary lists winner name -> supplier pairs of the links for a hand check. Output: ftc/extract/mas-links.jsonl, and a summary on stdout.
"""
import argparse
import csv
import gzip
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

_spec = importlib.util.spec_from_file_location('kftc', Path(__file__).resolve().parent / 'match-korea-kftc-tenders.py')
kftc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kftc)
BASE = kftc.BASE


def num(s):
    s = re.sub(r'[^\d-]', '', s or '')
    return int(s) if s not in ('', '-') else 0


def load_requests(folder):
    """Delivery-request number -> original version: summed amount, name, supplier, date, buyer, second-stage flag."""
    reqs = {}
    lines = set()  # (number, item line): the same line can be listed under two classes
    for f in sorted(folder.glob('*/*.csv.gz')):
        with gzip.open(f, 'rt', encoding='utf-8', newline='') as fh:
            for r in csv.DictReader(fh, delimiter='\t'):
                if r['계약납품구분'] != '납품' or r['변경차수'] != '00':
                    continue
                no = r['계약(납품요구)번호']
                if (no, r['물품순번']) in lines:
                    continue
                lines.add((no, r['물품순번']))
                q = reqs.setdefault(no, {'number': no, 'amount': 0, 'two_stage': False, 'classes': set()})
                q['amount'] += num(r['공급금액'])
                q['two_stage'] |= r['이단계경쟁제안서제출여부'] == 'Y'
                q['classes'].add(r['물품분류번호'])
                q.update(name=r['계약(납품요구)명'], date=r['최초계약(납품요구)일자'] or r['계약(납품요구)일자'],
                         buyer=r['수요기관'], buyer_code=r['수요기관코드'], supplier=r['업체명'],
                         supplier_bizrno=r['사업자등록번호'], mas=r['MAS여부'])
    for q in reqs.values():
        q['classes'] = sorted(q['classes'])
    return reqs


def same_amount(award, amount, tolerance):
    """Delivery requests include VAT; decisions print the award with VAT (15581) or without it (14663)."""
    return bool(award) and any(abs(amount - base) <= max(10, tolerance * base) for base in (award, round(award * 1.1)))


def match(t, pool):
    award = kftc.to_int(t.get('award_amount'))
    name = t.get('tender_name')
    scored = sorted(((kftc.similarity(name, q['name']), q) for q in pool), key=lambda x: -x[0])
    exact = [(s, q) for s, q in scored if same_amount(award, q['amount'], 0.0005) and s >= 0.3]
    if len(exact) == 1:
        return 'amount', exact
    if len(exact) > 1:
        return 'ambiguous', exact[:5]
    top = [(s, q) for s, q in scored if s >= 0.5]
    if top:
        return 'ambiguous', top[:5]
    return 'unmatched', scored[:3]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--tenders', type=Path, default=BASE / 'ftc/extract/checked.jsonl')
    parser.add_argument('--links', type=Path, default=BASE / 'ftc/extract/links.jsonl')
    parser.add_argument('--items', type=Path, default=BASE / 'datahub-items')
    parser.add_argument('--serials', default='14663,15581,14711', help='KFTC decisions on MAS second-stage tenders')
    parser.add_argument('--out', type=Path, default=BASE / 'ftc/extract/mas-links.jsonl')
    args = parser.parse_args()
    serials = set(args.serials.split(','))
    unmatched = {(x['serial'], x['i']) for x in map(json.loads, open(args.links)) if x['link'] == 'unmatched'}
    tenders = [t for t in kftc.load_tenders(args.tenders) if t['serial'] in serials and (t['serial'], t['i']) in unmatched]
    reqs = load_requests(args.items)
    pool = [q for q in reqs.values() if q['two_stage']]
    results = [(t, *match(t, pool)) for t in tenders]
    counts, pairs = Counter(), Counter()
    with open(args.out, 'w') as f:
        for t, how, cands in results:
            counts[how] += 1
            if how == 'amount':
                pairs[f"{t.get('winner')} -> {cands[0][1]['supplier']} {cands[0][1]['supplier_bizrno']}"] += 1
            f.write(json.dumps({'serial': t['serial'], 'i': t['i'], 'case_no': t.get('case_no'),
                                'tender_name': t.get('tender_name'), 'winner': t.get('winner'),
                                'award_amount': t.get('award_amount'), 'problems': t.get('problems'), 'link': how,
                                'candidates': [{**q, 'similarity': round(s, 3)} for s, q in cands]},
                               ensure_ascii=False) + '\n')
    print(json.dumps({'requests': len(reqs), 'second_stage_requests': len(pool), 'tenders': len(tenders), **counts, 'winner_pairs': dict(pairs),
                      'by_serial': {s: dict(Counter(how for t, how, _ in results if t['serial'] == s))
                                                    for s in sorted(serials)}}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
