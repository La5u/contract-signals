#!/usr/bin/env python3
"""Research only: normalise Romanian SEAP/SICAP contract exports (data.gov.ro) to one record format.

Reads every file under ~/.cache/contract-signals/romania-seap/<year>/ (CSV with ^ , or ; and " or | quotes,
old XLS even when named .xlsx, real XLSX) and writes normalized/<year>/<file>.jsonl.gz, one contract per
line: buyer, buyer_cui, procedure, concluded_by, notice_init, notice_award, lot, offers, contract_no,
contract_date, title, cpv, value_ron, winner, winner_cui. Raw value strings are kept next to parsed numbers.
Resumable per file. Winner and buyer identities are organisations; no personal data is added.
"""
import csv
import gzip
import io
import json
import re
import sys
from pathlib import Path

import openpyxl
import xlrd

BASE = Path.home() / '.cache/contract-signals/romania-seap'
csv.field_size_limit(sys.maxsize)
FIELDS = {
    'buyer': ['autoritatecontractanta', 'denumireac'],
    'buyer_cui': ['autoritatecontractantacui', 'cuiac', 'cuiautoritateconractanta', 'cuiautoritatecontractanta', 'cui'],
    'procedure': ['tipprocedura'],
    'concluded_by': ['tipincheierecontract', 'incheiatprin', 'incheiarprin'],
    'notice_init': ['numaranuntparticipare', 'numaranuntinitiere', 'numaranuntai'],
    'notice_award': ['numaranuntatribuire'],
    'lot': ['numarlot'],
    'offers': ['numaroferteprimite', 'numaroferte'],
    'contract_no': ['numarcontract'],
    'contract_date': ['datacontract'],
    'title': ['titlucontract', 'denumirecontract'],
    'cpv': ['cpvcode', 'codcpv', 'cpvcodeid'],
    'value_ron': ['valoareron', 'valoarecontractron', 'valoarecontract', 'valoareatribuitaron'],
    'winner': ['castigator', 'catigator', 'ofertant', 'ofertantcastigator', 'denumirecastigator'],
    'winner_cui': ['castigatorcui', 'cuiofertant', 'cuicastigator', 'cuiof', 'cuiofertantcastigator'],
}


def key(h):
    return re.sub(r'[^a-z0-9]', '', str(h).lower())


def mapping(header):
    keys = [key(h) for h in header]
    out = {}
    for field, names in FIELDS.items():
        for name in names:   # first matching candidate wins; the first column of that name
            if name in keys:
                out[field] = keys.index(name)
                break
    return out


def number(s):
    s = str(s or '').strip().replace(' ', '')
    if not s:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


def rows(path):
    head = path.read_bytes()[:8]
    if head.startswith(b'\xd0\xcf\x11\xe0'):
        # Old XLS holds at most 65,536 rows per sheet: large quarters continue on further sheets.
        book = xlrd.open_workbook(str(path), on_demand=True)
        header = None
        for k in range(book.nsheets):
            sheet = book.sheet_by_index(k)
            for i in range(sheet.nrows):
                row = sheet.row_values(i)
                if header is None:
                    header = row
                    yield row
                elif i == 0 and [str(x).strip() for x in row] == [str(x).strip() for x in header]:
                    continue
                else:
                    yield row
    elif head.startswith(b'PK'):
        ws = openpyxl.load_workbook(path, read_only=True).worksheets[0]
        yield from ws.iter_rows(values_only=True)
    else:
        raw = path.read_bytes()
        text = None
        for enc in ('utf-8-sig', 'cp1250'):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if text is None:   # 2012-2016 exports: Windows-1250 with a few stray bytes
            text = raw.decode('cp1250', errors='replace')
        first = text[:text.find('\n')]
        delim = max('^,;\t', key=first.count)
        quote = '|' if first.startswith('|') else '"'
        yield from csv.reader(io.StringIO(text, newline=''), delimiter=delim, quotechar=quote)


EXCLUDE = {'2023/Contracte-publicate-T-IV-2023-xls.xls'}   # same quarter as the CSV of that name


def normalise(path, out):
    it = rows(path)
    for header in it:   # some files open with a title row: the header is the first row naming 5+ known fields
        m = mapping(header)
        if len(m) >= 5:
            break
    n = 0
    with gzip.open(out.with_suffix('.tmp'), 'wt', encoding='utf-8') as fh:
        for r in it:
            if not r or all(v in (None, '') for v in r):
                continue
            rec = {f: (r[i] if i < len(r) else None) for f, i in m.items()}
            if isinstance(rec.get('contract_date'), float) and 20000 < rec['contract_date'] < 80000:   # Excel serial date
                rec['contract_date'] = xlrd.xldate.xldate_as_datetime(rec['contract_date'], 0).strftime('%Y-%m-%d')
            rec = {f: (str(v).strip() if v is not None else None) for f, v in rec.items()}
            rec['value_ron_num'] = number(rec.get('value_ron'))
            rec['offers_num'] = number(rec.get('offers'))
            rec['source'] = f'{path.parent.name}/{path.name}'
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
            n += 1
    out.with_suffix('.tmp').replace(out)
    return n, sorted(m)


def main():
    for path in sorted(p for p in BASE.glob('20*/*') if p.is_file() and p.stat().st_size > 1000):
        out = BASE / 'normalized' / path.parent.name / (path.name + '.jsonl.gz')
        if f'{path.parent.name}/{path.name}' in EXCLUDE:
            out.unlink(missing_ok=True)
            continue
        if out.exists():
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            n, fields = normalise(path, out)
            missing = sorted(set(FIELDS) - set(fields))
            print(f'{path.parent.name}/{path.name}: {n} rows; missing {missing}', flush=True)
        except Exception as e:
            print(f'{path.parent.name}/{path.name}: ERROR {e}', flush=True)


if __name__ == '__main__':
    main()
