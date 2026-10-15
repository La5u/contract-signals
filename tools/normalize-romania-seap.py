#!/usr/bin/env python3
"""Research only: normalise Romanian SEAP/SICAP contract exports (data.gov.ro) to one record format.

Reads every file under ~/.cache/contract-signals/romania-seap/<year>/ (CSV with ^ , or ; and " or | quotes,
old XLS even when named .xlsx, real XLSX) and writes normalized/<year>/<file>.jsonl.gz, one contract per
line: buyer, buyer_cui, procedure, concluded_by, notice_init, notice_award, lot, offers, contract_no,
contract_date, title, cpv, value_ron, winner, winner_cui. Raw value strings are kept next to parsed numbers.
Resumable per file. Winner and buyer identities are organisations; no personal data is added.
"""
import csv
from collections import Counter
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
    'value': ['valoare'],          # amount in the contract currency (2017-2018 subsequent contracts leave ValoareRON NULL)
    'currency': ['moneda'],
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
    """Parse '1,478,296' (comma thousands), '1.478.296,50' (dot thousands, comma decimal), '123.45', '345000'.

    Commas or dots grouping digits in threes are thousands separators; a single separator followed by one,
    two or four or more digits is a decimal point."""
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s or '').strip().replace(' ', '').replace('\u00a0', '')
    if not s:
        return None
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
    elif re.fullmatch(r'-?\d{1,3}(,\d{3})+', s):
        s = s.replace(',', '')
    elif re.fullmatch(r'-?\d{1,3}(\.\d{3}){2,}', s):
        s = s.replace('.', '')
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
        # XLSX exports are also split over several sheets: read them all, skipping repeated headers.
        header = None
        for ws in openpyxl.load_workbook(path, read_only=True).worksheets:
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if header is None:
                    header = row
                    yield row
                elif i == 0 and [str(x).strip() for x in row] == [str(x).strip() for x in header]:
                    continue
                else:
                    yield row
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
        quote = '|' if first.startswith('|') else '"'
        delim = max('^,;\t' if quote == '|' else '^,;\t|', key=first.count)
        header = None
        if delim == '^':
            # Unquoted ^-separated exports (2017-2018) carry line breaks inside fields: join lines until a record
            # has the header's field count.
            lines = iter(text.splitlines())
            header = next(lines).split('^')
            yield header
            buf = ''
            for line in lines:
                buf = f'{buf}\n{line}' if buf else line
                if buf.count('^') >= len(header) - 1:
                    yield buf.split('^')
                    buf = ''
            return
        for row in csv.reader(io.StringIO(text, newline=''), delimiter=delim, quotechar=quote):
            if header is None:
                header = row
                yield row
            elif len(row) == len(header) or delim != ',' or quote != '"':
                yield row
            else:
                fixed = repair(row, header)
                STATS['repaired' if fixed else 'dropped'] += 1
                if fixed:
                    yield fixed


STATS = {'repaired': 0, 'dropped': 0}
CUI_RE = re.compile(r'^\s*(?:RO\s?)?\d{1,10}\s*$', re.I)
DATE_RE = re.compile(r'^\s*20\d\d-\d\d-\d\d')


def repair(tokens, header):
    """Rebuild a row of an unquoted comma export (2016) whose free-text fields contain commas.

    Anchors, left to right: the winner CUI ends the winner name; a field starting 'Anunt de atribuire' ends the
    address; the buyer CUI ends the buyer name; the first date after it is the award-notice date (the token
    before it is the notice number); the next date at least five fields on is the contract date; the contract
    value is the first number after it followed by a three-letter currency. Fields after the value are read in
    order and trailing free text is joined into the last column. None when an anchor is missing."""
    names = [key(h) for h in header]
    t = [x.strip() for x in tokens]
    try:
        k = next(i for i in range(1, len(t)) if CUI_RE.match(t[i]))
        j = next(i for i in range(k + 3, len(t)) if t[i].lower().startswith('anunt de atribuire'))
        m = next(i for i in range(j + 3, len(t)) if CUI_RE.match(t[i]))
        da = next(i for i in range(m + 2, len(t)) if DATE_RE.match(t[i]))
        dc = next(i for i in range(da + 6, len(t)) if DATE_RE.match(t[i]))
        v = next(i for i in range(dc + 1, len(t) - 1) if number(t[i]) is not None and re.fullmatch(r'[A-Z]{3}', t[i + 1]))
    except StopIteration:
        return None
    head = [','.join(t[:k]), t[k], t[k + 1], t[k + 2], ','.join(t[k + 3:j]), t[j], t[j + 1], t[j + 2], ','.join(t[j + 3:m]),
            t[m], ','.join(t[m + 1:da - 1]), '', t[da - 1], t[da]]
    middle = t[da + 1:da + 6]                                   # TipIncheiere .. Subcontractat
    row = head + middle + [','.join(t[da + 6:dc]), t[dc], ','.join(t[dc + 1:v])]
    rest = len(names) - len(row)
    tail = t[v:v + rest - 1] + [','.join(t[v + rest - 1:])]
    row += tail
    if len(row) != len(names):
        return None
    return row


EXCLUDE = {'2023/Contracte-publicate-T-IV-2023-xls.xls',   # same quarter as the CSV of that name
           '2019/Contracte-2019-T3.xlsx'}               # a copy of the Q2 file (17,504 of 17,560 rows identical); real Q3 2019 not published


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
            if rec['value_ron_num'] is None and str(rec.get('currency') or '').upper() == 'RON':
                rec['value_ron_num'] = number(rec.get('value'))
            rec['offers_num'] = number(rec.get('offers'))
            rec['source'] = f'{path.parent.name}/{path.name}'
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
            n += 1
    out.with_suffix('.tmp').replace(out)
    return n, sorted(m)


CAPS = {65000, 65001, 64999, 65535, 65536, 1048575, 1048576, 50000, 100000}
KEY_FIELDS = ('buyer_cui', 'value_ron_num', 'contract_date', 'winner_cui', 'procedure')


def audit(out, n):
    """Warn about silent data loss: a row count at a known export cap, or key fields mostly empty."""
    if n in CAPS:
        yield f'row count {n} equals a known export cap (more sheets or pages?)'
    empty = Counter()
    with gzip.open(out, 'rt', encoding='utf-8') as fh:
        for line in fh:
            r = json.loads(line)
            for k in KEY_FIELDS:
                empty[k] += r.get(k) in (None, '', 'NULL')
    for k, v in empty.items():
        if n and v / n > 0.2:
            yield f'{k} empty in {v / n:.0%} of rows (unmapped header or misaligned rows?)'


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
            extra = f"; repaired {STATS['repaired']}, dropped {STATS['dropped']}" if STATS['repaired'] or STATS['dropped'] else ''
            extra += ''.join(f'; WARNING {w}' for w in audit(out, n))
            print(f'{path.parent.name}/{path.name}: {n} rows; missing {missing}{extra}', flush=True)
            STATS.update(repaired=0, dropped=0)
        except Exception as e:
            print(f'{path.parent.name}/{path.name}: ERROR {e}', flush=True)


if __name__ == '__main__':
    main()
