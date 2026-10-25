#!/usr/bin/env python3
"""Research only: link KFTC rigged tenders that found no KONEPS notice to DAPA, LH and KOGAS records.

Input: ftc/extract/checked.jsonl and ftc/extract/links.jsonl (tools/match-korea-kftc-tenders.py); only tenders
with link `unmatched` there are tried. Agency records from the private cache:

- `dapa`: 방위사업청 contracts, domestic goods/services, facility works and foreign
  (tools/fetch-korea-dapa.py, dapa/contracts/<kind>/<YYYY-MM>.jsonl.gz). Winner name only, no business number.
- `lh`: 한국토지주택공사 contracts with the winner's business number (tools/fetch-korea-agencies.py,
  agencies/lh/<year>.jsonl.gz). Joint-venture members are separate rows.
- `kogas`: 한국가스공사 bid results with the winner's business number; `signed` is the award date (SUCCESS_DT).

Each record becomes a row of the same shape as an opnstd.sqlite version, and the tenders go through the same
`match` as the KONEPS matcher (winner + amount in the date window, amount + buyer, winner + buyer + similar name;
accepted only when one notice/contract is left), with stricter limits on winner + buyer + name (see `stricter`). The agency stands in for the buyer, so `buyer_name` carries the
names the KFTC decisions use for it and `demand_name` the ordering unit.
Output: ftc/extract/agency-links.jsonl (same fields as links.jsonl plus `source`), and a summary on stdout.
"""
import argparse
import gzip
import importlib.util
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import to_int  # noqa: E402

_spec = importlib.util.spec_from_file_location('kftc', Path(__file__).resolve().parent / 'match-korea-kftc-tenders.py')
kftc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kftc)
BASE = kftc.BASE
BUYERS = {'dapa': '방위사업청 국방부 국군 국방조달본부', 'lh': '한국토지주택공사 대한주택공사 한국토지공사 LH',
          'kogas': '한국가스공사'}


def iso(s):
    s = str(s or '').replace('-', '')[:8]
    return f'{s[:4]}-{s[4:6]}-{s[6:8]}' if len(s) == 8 and s.isdigit() else None


def row(source, **kw):
    r = dict.fromkeys(kftc.COLS)
    r.update(ord=0, buyer_name=BUYERS[source], **kw)
    r['cntrct_no'] = f'{source}:{r["cntrct_no"]}'
    return r


def dapa_rows(base):
    for f in sorted((base / 'dapa/contracts').glob('*/*.jsonl.gz')):
        kind = f.parent.name
        for line in gzip.open(f, 'rt'):
            d = json.loads(line)
            yield row('dapa', cntrct_no=f'{kind}:{d.get("cntrctNo")}', signed=iso(d.get('cntrctDate')),
                      name=d.get('cntrctNm'), notice_no=d.get('cntrwkNo') or '', amount=to_int(d.get('cntrctAmnt')),
                      total_amount=to_int(d.get('cntrctTotlCsrtBokpAmnt')),
                      reserve_price=to_int(d.get('cntrctPlanaAmnt')) or None, method=d.get('cntrctMth'),
                      business_type=d.get('cntrctDivs'), demand_name=d.get('ornt'),
                      supplier_name=d.get('cntrctEntrpsNm'), opening_date=iso(d.get('cntrctBidxDate')))


def lh_rows(base):
    for f in sorted((base / 'agencies/lh').glob('*.jsonl.gz')):
        for line in gzip.open(f, 'rt'):
            d = json.loads(line)
            yield row('lh', cntrct_no=f'{d.get("bidNum")}:{d.get("ctrctCntrctgDt")}', signed=iso(d.get('ctrctCntrctgDt')),
                      name=d.get('ctrctNm'), notice_no=f'lh:{d.get("bidNum")}' if d.get('bidNum') else '',
                      amount=to_int(d.get('ctrctAmt')), method=d.get('tndrCtrctMedNm'),
                      business_type=d.get('cstrtnJobGbNm'), joint=d.get('ctrctVndrTypeNm'),
                      demand_name=d.get('revertDeptNm'), supplier_name=d.get('ctrctVndrNm'),
                      supplier_bizrno=d.get('ctrctTaxregno'))


def kogas_rows(base):
    for f in sorted((base / 'agencies/kogas').glob('*.jsonl.gz')):
        for line in gzip.open(f, 'rt'):
            d = json.loads(line)
            if d.get('CANCEL_YN') == 'Y' or not d.get('SUCCESS_CORP_NAME'):
                continue
            yield row('kogas', cntrct_no=d.get('NOTICE_CODE'), signed=iso(d.get('SUCCESS_DT')),
                      name=d.get('NOTICE_NAME'), notice_no=f'kogas:{d.get("NOTICE_CODE")}',
                      opening_date=iso(d.get('OPEN_DT')), amount=to_int(d.get('SUCCESS_AMT')),
                      method=d.get('CONT_METHOD_NAME'), business_type=d.get('WORK_TYPE_NAME'),
                      supplier_name=d.get('SUCCESS_CORP_NAME'), supplier_bizrno=d.get('SUCCESS_CORP_CODE'))


def index(records, tenders):
    """Same keys as kftc.scan: ('n', winner name) and ('a', amount) for rows that could belong to a tender."""
    names = {kftc.norm_name(t.get('winner')) for t in tenders if not kftc.masked(t.get('winner'))}
    amounts = {to_int(t.get('award_amount')) for t in tenders} - {None}
    rows, seen = defaultdict(list), Counter()
    for r in records:
        seen[r['cntrct_no'].split(':')[0]] += 1
        n = kftc.norm_name(str(r['supplier_name'] or ''))
        if n in names:
            rows[('n', n)].append(r)
        if r['amount'] in amounts:
            rows[('a', r['amount'])].append(r)
        if r['total_amount'] in amounts and r['total_amount'] != r['amount']:
            rows[('a', r['total_amount'])].append(r)
    return rows, seen


def stricter(t, how, cands):
    """Agency-only limits on `buyer-name`: agencies buy the same item every year under the same name, so the
    tender needs a date of its own (not the ten-year fallback before the decision), and a known award of
    1M KRW or more must be within 5 % of the record (smaller awards are unit prices and cannot be compared)."""
    if how != 'buyer-name':
        return how, None
    if not any(t.get(k) for k in ('contract_date', 'opening_date', 'notice_date')):
        return 'ambiguous', 'buyer-name without a tender date'
    award, amount = to_int(t.get('award_amount')), cands[0]['amount']
    if award and award >= 1_000_000 and amount and abs(award - amount) > 0.05 * amount:
        return 'ambiguous', f'buyer-name but award {award} vs {amount}'
    return how, None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--tenders', type=Path, default=BASE / 'ftc/extract/checked.jsonl')
    parser.add_argument('--links', type=Path, default=BASE / 'ftc/extract/links.jsonl')
    parser.add_argument('--out', type=Path, default=BASE / 'ftc/extract/agency-links.jsonl')
    args = parser.parse_args()
    unmatched = {(x['serial'], x['i']) for x in map(json.loads, open(args.links)) if x['link'] == 'unmatched'}
    tenders = [t for t in kftc.load_tenders(args.tenders) if (t['serial'], t['i']) in unmatched]
    for t in tenders:
        t['notice_no'] = None  # KONEPS numbers; agency numbering differs and the notice step would misfire
        if t.get('tender_name'):  # decisions append "구매입찰" / "입찰" / "군납"; agency records name the item only
            t['tender_name'] = re.sub(r'(군납|구매\s*입찰|입찰)\s*$', '', re.sub(r'군납', '', t['tender_name'])).strip()
    records = (r for gen in (dapa_rows, lh_rows, kogas_rows) for r in gen(BASE))
    rows, seen = index(records, tenders)
    counts, by_source = Counter(), Counter()
    with open(args.out, 'w') as f:
        for t in tenders:
            how, cands = kftc.match(t, rows)
            how, why = stricter(t, how, cands)
            if why:
                t.setdefault('problems', []).append(why)
            source = cands[0]['contracts'][0].split(':')[0] if cands and how != 'unmatched' else None
            counts[how] += 1
            if how not in ('unmatched', 'ambiguous'):
                by_source[source] += 1
            f.write(json.dumps({'serial': t['serial'], 'i': t['i'], 'case_no': t.get('case_no'),
                                'buyer': t.get('buyer'), 'tender_name': t.get('tender_name'),
                                'winner': t.get('winner'), 'award_amount': t.get('award_amount'),
                                'opening_date': t.get('opening_date'), 'problems': t.get('problems'),
                                'link': how, 'source': source, 'candidates': cands}, ensure_ascii=False) + '\n')
    print(json.dumps({'records_scanned': dict(seen), 'tenders': len(tenders), **counts,
                      'linked_by_source': dict(by_source)}, indent=1))


if __name__ == '__main__':
    main()
