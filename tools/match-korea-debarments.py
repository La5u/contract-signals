#!/usr/bin/env python3
"""Research only: link fraud-type Korean debarments (부정당제재) to the contracts they most likely concern.

Input: debarments/<date>.jsonl.gz (tools/snapshot-korea-debarments.py; current sanctions only, starting 2022-09)
and opnstd.sqlite `versions` (contracts signed 2010-01..2026-09).

Each sanction is classed by its legal ground (enforcement-rule item, else the law clause):
collusion (담합/협정), bribery (금품), forgery (위조/허위/거짓 서류), fraud (사기, 손해를 끼친), bad performance
(부실·조잡, 부정한 시공/행위). Non-performance, refusal to sign, subcontracting and paperwork grounds are left out:
they say nothing about how the contract was won. Rows of one decision (제재, 정지, 재개, 정정) are merged.

A debarment does not name its contract. Candidates are the contracts between the sanctioned firm (business number)
and the sanctioning institution (contracting office or demanding body by code, or a name starting with the institution's name, which catches
sub-units with codes of their own; for 조달청 any PPS office, codes 123xxxx),
signed in the five years before the notification. `single`: exactly one such contract, the link; `several`: the
firm-buyer pair is the label unit and the contracts are listed; `firm-only`: the firm has contracts, none with that
institution; `none`: no contract of the firm in the data.
Output: debarments/links-<date>.jsonl, and a summary on stdout.
"""
import argparse
import datetime as dt
import gzip
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
import os

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea'
FAMILIES = [('collusion', r'담합|협정'), ('bribery', r'금품'), ('forgery', r'위조|허위|거짓'),
            ('fraud', r'사기|손해를\s*끼친'), ('bad-performance', r'부실|조잡|부정한\s*(시공|행위)')]
COLS = ['cntrct_no', 'ord', 'signed', 'name', 'amount', 'method', 'business_type', 'notice_no', 'buyer_name',
        'buyer_code', 'demand_name', 'demand_code', 'supplier_name', 'supplier_bizrno']


def family(r):
    for text in (r.get('enfcPrvNm'), r.get('lawordArtclClauseCdNm')):
        for name, pattern in FAMILIES:
            if re.search(pattern, text or ''):
                return name
    return None


def digits(s):
    return re.sub(r'\D', '', str(s or ''))


def same_buyer(inst, inst_name, r):
    codes = {r['buyer_code'] or '', r['demand_code'] or ''}
    if inst == '1230000':  # 조달청 sanctions for contracts of every PPS office
        return any(c.startswith('123') for c in codes)
    if inst in codes:
        return True
    # sub-units have codes of their own (법무부 -> 법무부 서울구치소), but a province or metropolitan city does not
    # cover its cities, counties and districts (인천광역시 -> 인천광역시 강화군 is another government)
    name = (inst_name or '').strip()
    upper = re.search(r'(광역시|특별시|도|특별자치도)$', name)
    for n in (r['buyer_name'], r['demand_name']):
        n = (n or '').strip()
        if name and n.startswith(name):
            rest = n[len(name):].split()
            if not (upper and rest and re.search(r'(시|군|구)$', rest[0])):
                return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--snapshot', type=Path, default=max((BASE / 'debarments').glob('20*.jsonl.gz')))
    parser.add_argument('--db', type=Path, default=BASE / 'opnstd.sqlite')
    parser.add_argument('--years', type=int, default=5, help='contracts signed this many years before the notice')
    args = parser.parse_args()
    events = {}
    for line in gzip.open(args.snapshot, 'rt'):
        r = json.loads(line)
        fam = family(r)
        if not fam:
            continue
        key = (digits(r['bizno']), r['insttCd'], fam, (r.get('ntfcnDt') or r.get('rsttBgnDate') or '')[:10])
        e = events.setdefault(key, {'bizno': key[0], 'corp': r['corpNm'], 'institution': r['insttNm'],
                                    'institution_code': r['insttCd'], 'family': fam, 'notified': key[3],
                                    'ground': r.get('enfcPrvNm') or r.get('lawordArtclClauseCdNm'),
                                    'law': r.get('lawordNm'), 'document': r.get('unptRsttDocNm'),
                                    'start': r.get('rsttBgnDate'), 'months': r.get('rsttPrdMonthNum'), 'status': []})
        e['status'].append(r.get('rsttProgrsNm'))
    firms = {e['bizno'] for e in events.values()}
    rows = defaultdict(list)
    con = sqlite3.connect(f'file:{args.db}?mode=ro', uri=True)
    for rec in con.execute(f'SELECT {", ".join(COLS)} FROM versions'):
        r = dict(zip(COLS, rec))
        b = digits(r['supplier_bizrno'])
        if b in firms:
            rows[b].append(r)
    counts, by_family = Counter(), defaultdict(Counter)
    out = args.snapshot.parent / f'links-{args.snapshot.name.split(".")[0]}.jsonl'
    with open(out, 'w') as f:
        for e in sorted(events.values(), key=lambda e: (e['family'], e['notified'])):
            notified = dt.date.fromisoformat(e['notified']) if e['notified'] else dt.date.today()
            lo = (notified - dt.timedelta(days=365 * args.years)).isoformat()
            firm = rows.get(e['bizno'], [])
            pair = {}
            for r in firm:
                if same_buyer(e['institution_code'], e['institution'], r) and lo <= (r['signed'] or '') <= notified.isoformat():
                    first = pair.get(r['cntrct_no'])
                    if not first or (r['ord'] or 0) < (first['ord'] or 0):
                        pair[r['cntrct_no']] = r
            link = ('single' if len(pair) == 1 else 'several' if pair else 'firm-only' if firm else 'none')
            counts[link] += 1
            by_family[e['family']][link] += 1
            e.update(link=link, firm_contracts=len({r['cntrct_no'] for r in firm}),
                     contracts=sorted(pair.values(), key=lambda r: r['signed'] or ''))
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
    print(json.dumps({'sanction_decisions': len(events), 'firms': len(firms), **counts,
                      'by_family': {k: dict(v) for k, v in sorted(by_family.items())}, 'out': str(out)},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
