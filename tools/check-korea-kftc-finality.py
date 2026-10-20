#!/usr/bin/env python3
"""Research only: court outcome of the KFTC cases behind the Korean collusion labels.

Input: ~/.cache/contract-signals/korea/ftc-suits/decisions/*.xml.gz (tools/fetch-korea-lawgokr.py --target ftc-suits:
law.go.kr court rulings whose case name has 시정명령 / 과징금), ftc/decisions (decision number and date of each case),
ftc/extract/links.jsonl (which cases have linked tenders). A ruling belongs to a case when its text cites the
decision number (의결 제2015-075호, spacing and leading zeros ignored).

Outcome per ruling, from the disposition (주문): 청구를 기각 / 상고를 기각 + costs on the plaintiff = the finding
stands; 취소한다 with costs on the defendant = annulled; costs split or 부분 취소 = partly annulled (plan: the
finding survives, the fine is cut; checked by hand where it matters); 파기 = sent back (pending). Case status
(plan, "Finality"): `upheld` (a final Supreme Court ruling, or a first-instance ruling the KFTC won with no
appeal found 2+ years later), `pending` (a ruling with an appeal possibly open), `annulled-first-instance`,
`annulled` (Supreme Court confirmed an annulment), `none` (no ruling found). law.go.kr publishes only part of
the rulings, so `none` means "no challenge found", as the plan defines it.
Output: ftc-suits/finality.json (case -> status, rulings) and a summary on stdout.
"""
import datetime as dt
import gzip
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea'
LINKED = ('notice', 'amount', 'amount-buyer', 'buyer-name')
TODAY = dt.date(2026, 10, 20)


def field(text, tag):
    m = re.search(f'<{tag}>(?:<!\\[CDATA\\[)?(.*?)(?:\\]\\]>)?</{tag}>', text, re.S)
    return m.group(1).strip() if m else ''


def plain(s):
    return re.sub(r'\s+', ' ', re.sub(r'<br\s*/?>', ' ', s or ''))


def case_of(serial):
    """(decision number, decision date as courts write it: '2015. 4. 1.'), or None."""
    text = gzip.open(BASE / 'ftc/decisions' / f'{serial}.xml.gz', 'rt', encoding='utf-8').read()
    no = field(text, '결정번호')
    m = re.search(r'(\d{4})\s*-\s*(\d+)', no)
    kind = re.sub(r'[^가-힣]', '', no.split('제')[0])  # 의결, 결정, 재결, 의결약: numbered separately
    d = re.match(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})', field(text, '결정일자'))
    if not m or not d:
        return None
    return f'{kind} {m.group(1)}-{int(m.group(2)):03d}', f'{d.group(1)}. {int(d.group(2))}. {int(d.group(3))}.'


def outcome(text):
    body = plain(field(text, '판례내용'))
    m = re.search(r'【\s*주\s*문\s*】(.*?)(【|$)', body)
    order = m.group(1) if m else body[:400]
    if '파기' in order:
        return 'sent back', order
    plaintiff_pays = re.search(r'비용은?\s*(?:모두\s*)?원고(?:들)?(?:이|가)?\s*부담', order)
    defendant_pays = re.search(r'비용은?\s*(?:모두\s*)?피고(?:가|의)?\s*부담', order)
    split = re.search(r'각자\s*부담|중\s*[\d/분의 ]+(?:은|는)\s*원고|나머지는\s*(?:원고|피고)', order)
    if split or ('취소' in order and '기각' in order):
        return 'partly annulled', order
    if plaintiff_pays or re.search(r'청구를?\s*(?:모두\s*)?기각', order):
        return 'upheld', order
    if defendant_pays or '취소한다' in order:
        return 'annulled', order
    return 'unclear', order


def main():
    links = [json.loads(l) for l in open(BASE / 'ftc/extract/links.jsonl')]
    serials = sorted({l['serial'] for l in links if l['link'] in LINKED})
    cases = {s: case_of(s) for s in serials}
    dates = defaultdict(set)
    for c in cases.values():
        if c:
            dates[c[0]].add(c[1])
    wanted = set(dates)
    pattern = re.compile(r'제\s*(\d{4})\s*[-－–]\s*(\d{1,4})\s*호')
    rulings = defaultdict(list)
    for path in sorted((BASE / 'ftc-suits/decisions').glob('*.xml.gz')):
        text = gzip.open(path, 'rt', encoding='utf-8').read()
        body = plain(field(text, '판례내용'))
        # the same number can be another body's decision or notice: the KFTC decision's date must be cited too
        flat = re.sub(r'\s+', ' ', body)
        numbers = {f'{y}-{int(n):03d}' for y, n in pattern.findall(body)}
        cited = {c for c in wanted if c.split(' ')[1] in numbers and any(d in flat for d in dates[c])}
        if not cited:
            continue
        how, order = outcome(text)
        d = field(text, '선고일자')
        r = {'serial': path.name.split('.')[0], 'court': field(text, '법원명'), 'case_no': field(text, '사건번호'),
             'name': field(text, '사건명'), 'date': f'{d[:4]}-{d[4:6]}-{d[6:8]}' if len(d) == 8 else d,
             'outcome': how, 'order': order[:300]}
        for c in cited:
            rulings[c].append(r)
    result = {}
    for c in sorted(wanted):
        rs = sorted(rulings.get(c, []), key=lambda r: r['date'])
        if not rs:
            result[c] = {'status': 'none', 'rulings': []}
            continue
        supreme = [r for r in rs if r['court'] == '대법원']
        last = (supreme or rs)[-1]
        age = (TODAY - dt.date.fromisoformat(last['date'])).days / 365 if re.match(r'\d{4}-\d\d-\d\d', last['date']) else 0
        if supreme and last['outcome'] in ('upheld', 'partly annulled'):
            status = 'upheld'
        elif supreme and last['outcome'] == 'annulled':
            status = 'annulled'
        elif last['outcome'] in ('upheld', 'partly annulled'):
            status = 'upheld' if age >= 2 else 'pending'
        elif last['outcome'] == 'annulled':
            status = 'annulled-first-instance'
        else:
            status = 'pending'
        result[c] = {'status': status, 'rulings': rs}
    (BASE / 'ftc-suits/finality.json').write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n')
    print(f'{len(wanted)} cases with linked tenders; rulings citing them: {sum(len(v) for v in rulings.values())}')
    print('status:', dict(Counter(v['status'] for v in result.values())))
    print('ruling outcomes:', dict(Counter(r['outcome'] for v in rulings.values() for r in v)))
    for c, v in result.items():
        if v['status'] not in ('none',):
            print(c, v['status'], [(r['court'], r['case_no'], r['date'], r['outcome']) for r in v['rulings']])


if __name__ == '__main__':
    main()
