#!/usr/bin/env python3
"""Research only: load the downloaded PPS open-standard contracts into one SQLite database, without personal fields.

Reads every complete week in ~/.cache/contract-signals/korea/opnstd-contracts/ (skips .part files) and writes
~/.cache/contract-signals/korea/opnstd.sqlite:

- `versions`: one row per contract version as published. `ord` 0 is the original contract, 1, 2, ... are later
  changes, each dated by its own `signed` date, so a change after 2026-09-01 is not in the data.
- `contracts`: one row per contract number, built from its versions: the original's date and amount when the
  original is in the period (`original_in_period`), the latest amount, the number of changes seen.
- `weeks`: which source files were loaded; rerunning loads only new or changed weeks, then rebuilds `contracts`.

Dropped: names, phone numbers and e-mails of buyer officials and of the supplier's representative or contact,
and the supplier's street address (only province and district are kept). `legal_ref` is the statute cited at the end of
`legal_basis` (Act, article, paragraph, item), so contracts can be grouped by legal ground. `supplier_kind` comes from the middle
two digits of the business registration number: 81, 82, 85-88 are corporations or their branches, 01-79 and
90-99 individual businesses (sole traders), whose trade name may be a person's name: decide before publishing.
"""
import argparse
import gzip
import json
import os
import re
import sqlite3
from pathlib import Path

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea'
COLUMNS = [  # (column, source field, type)
    ('unty_no', 'untyCntrctNo', 'TEXT PRIMARY KEY'), ('cntrct_no', 'cntrctNo', 'TEXT NOT NULL'), ('ord', 'cntrctOrd', 'INTEGER'),
    ('signed', 'cntrctCnclsDate', 'TEXT'), ('name', 'cntrctNm', 'TEXT'), ('business_type', 'bsnsDivNm', 'TEXT'),
    ('method', 'cntrctCnclsMthdNm', 'TEXT'), ('pricing', 'cntrctCnclsSttusNm', 'TEXT'), ('term_type', 'lngtrmCtnuDivNm', 'TEXT'),
    ('joint', 'cmmnCntrctYn', 'TEXT'), ('amount', 'cntrctAmt', 'INTEGER'), ('total_amount', 'ttalCntrctAmt', 'INTEGER'),
    ('period', 'cntrctPrd', 'TEXT'), ('contract_url', 'cntrctInfoUrl', 'TEXT'), ('notice_no', 'bidNtceNo', 'TEXT'),
    ('notice_ord', 'bidNtceOrd', 'TEXT'), ('notice_name', 'bidNtceNm', 'TEXT'), ('opening_date', 'opengDate', 'TEXT'),
    ('opening_time', 'opengTm', 'TEXT'), ('reserve_price', 'rsrvtnPrce', 'NUMERIC'), ('legal_basis', 'prvtcntrctRsn', 'TEXT'),
    ('notice_url', 'bidNtceUrl', 'TEXT'), ('buyer_type', 'cntrctInsttDivNm', 'TEXT'), ('buyer_name', 'cntrctInsttNm', 'TEXT'),
    ('buyer_code', 'cntrctInsttCd', 'TEXT'), ('buyer_dept', 'cntrctInsttChrgDeptNm', 'TEXT'), ('demand_type', 'dmndInsttDivNm', 'TEXT'),
    ('demand_name', 'dmndInsttNm', 'TEXT'), ('demand_code', 'dmndInsttCd', 'TEXT'), ('demand_dept', 'dmndInsttOfclDeptNm', 'TEXT'),
    ('supplier_name', 'rprsntCorpNm', 'TEXT'), ('supplier_bizrno', 'rprsntCorpBizrno', 'TEXT'), ('domestic', 'dmstcCorpYn', 'TEXT'),
    ('data_date', 'dataBssDate', 'TEXT'),
]
DERIVED = [('supplier_kind', 'TEXT'), ('supplier_region', 'TEXT'), ('legal_ref', 'TEXT'), ('week', 'TEXT NOT NULL')]
# The statute cited at the end of the legal-basis text, e.g. '[지방계약법 제25조제1항5호나목]' -> '지방계약법 제25조제1항5호나목'.
LEGAL_REF = re.compile(r'\[([^\[\]]*제\s*\d+\s*조[^\[\]]*)\]\s*$')
DROPPED = {'cntrctInsttOfclNm', 'cntrctInsttOfclTel', 'cntrctInsttOfcl', 'dmndInsttOfclNm', 'dmndInsttOfclTel',
           'dmndInsttOfclEmailAdrs', 'rprsntCorpCeoNm', 'rprsntCorpOfclNm', 'rprsntCorpContactTel', 'rprsntCorpAdrs'}
INTEGER = {c for c, _, t in COLUMNS if t in ('INTEGER', 'NUMERIC')}


def supplier_kind(bizrno):
    digits = bizrno.replace('-', '')
    if len(digits) != 10 or not digits.isdigit():
        return 'unknown'
    mid = int(digits[3:5])
    return ('corporation' if mid in (81, 82, 85, 86, 87, 88) else 'public-body' if mid == 83 else 'foreign' if mid == 84
            else 'association' if mid in (80, 89) else 'individual')


def row_values(r, week, anomalies):
    unknown = set(r) - {f for _, f, _ in COLUMNS} - DROPPED
    if unknown:
        raise SystemExit(f'{week}: unexpected fields {sorted(unknown)}; update COLUMNS or DROPPED')
    values = []
    for column, field, _ in COLUMNS:
        v = (r.get(field) or '').strip()
        if column in INTEGER:
            if v.isdigit():
                v = int(v)
            else:
                try:
                    v = float(v) if v else None  # some reserve prices carry decimals (e.g. 472211.7)
                except ValueError:
                    anomalies[column] = anomalies.get(column, 0) + 1
                    v = None
        values.append(v if v != '' else None)
    address = (r.get('rprsntCorpAdrs') or '').split()
    ref = LEGAL_REF.search((r.get('prvtcntrctRsn') or '').strip())
    return values + [supplier_kind(r.get('rprsntCorpBizrno') or ''), ' '.join(address[:2]) or None,
                     re.sub(r'\s+', ' ', ref.group(1)).strip() if ref else None, week]


def build_contracts(db):
    db.executescript('''
    DROP TABLE IF EXISTS contracts;
    CREATE TABLE contracts AS
    SELECT v.cntrct_no,
           MIN(v.ord) = 0 AS original_in_period,
           MAX(CASE WHEN v.ord = 0 THEN v.signed END) AS signed,
           MAX(CASE WHEN v.ord = 0 THEN v.amount END) AS original_amount,
           COUNT(*) AS versions_seen,
           SUM(v.ord > 0) AS changes_seen,
           MAX(v.ord) AS last_ord,
           MIN(v.signed) AS first_date_seen,
           MAX(v.signed) AS last_date_seen,
           COUNT(DISTINCT v.supplier_bizrno) > 1 AS supplier_changed
    FROM versions v GROUP BY v.cntrct_no;
    CREATE UNIQUE INDEX contracts_no ON contracts(cntrct_no);
    ''')
    # Latest version's fields (the highest ord seen), for the descriptive columns.
    for column in ('amount', 'total_amount', 'name', 'method', 'business_type', 'buyer_code', 'buyer_name', 'buyer_type',
                   'supplier_bizrno', 'supplier_name', 'supplier_kind', 'notice_no', 'legal_basis', 'legal_ref', 'joint'):
        db.execute(f'ALTER TABLE contracts ADD COLUMN last_{column}')
    db.execute('''UPDATE contracts SET (last_amount, last_total_amount, last_name, last_method, last_business_type, last_buyer_code,
                  last_buyer_name, last_buyer_type, last_supplier_bizrno, last_supplier_name, last_supplier_kind, last_notice_no,
                  last_legal_basis, last_legal_ref, last_joint) =
                  (SELECT amount, total_amount, name, method, business_type, buyer_code, buyer_name, buyer_type, supplier_bizrno,
                          supplier_name, supplier_kind, notice_no, legal_basis, legal_ref, joint
                   FROM versions v WHERE v.cntrct_no = contracts.cntrct_no AND v.ord = contracts.last_ord)''')
    db.executescript('''
    CREATE INDEX IF NOT EXISTS contracts_buyer ON contracts(last_buyer_code);
    CREATE INDEX IF NOT EXISTS contracts_supplier ON contracts(last_supplier_bizrno);
    CREATE INDEX IF NOT EXISTS contracts_signed ON contracts(signed);
    ''')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--source', type=Path, default=BASE / 'opnstd-contracts')
    parser.add_argument('--db', type=Path, default=BASE / 'opnstd.sqlite')
    args = parser.parse_args()
    db = sqlite3.connect(args.db)
    db.execute('PRAGMA journal_mode=WAL')
    columns = [(c, t) for c, _, t in COLUMNS] + DERIVED
    db.execute(f'CREATE TABLE IF NOT EXISTS versions ({", ".join(f"{c} {t}" for c, t in columns)})')
    db.execute('CREATE TABLE IF NOT EXISTS weeks (week TEXT PRIMARY KEY, size INTEGER, mtime REAL, rows INTEGER, summary TEXT)')
    for statement in ('CREATE INDEX IF NOT EXISTS versions_cntrct ON versions(cntrct_no, ord)',
                      'CREATE INDEX IF NOT EXISTS versions_week ON versions(week)'):
        db.execute(statement)
    loaded = {w: (s, m) for w, s, m in db.execute('SELECT week, size, mtime FROM weeks')}
    insert = f'INSERT INTO versions VALUES ({", ".join("?" * len(columns))})'
    changed = 0
    for path in sorted(args.source.glob('*.jsonl.gz')):
        week = path.name.removesuffix('.jsonl.gz')
        stat = path.stat()
        if loaded.get(week) == (stat.st_size, stat.st_mtime):
            continue
        anomalies = {}
        lo, hi = week.split('_')
        with db:
            db.execute('DELETE FROM versions WHERE week = ?', (week,))
            rows = 0
            with gzip.open(path, 'rt', encoding='utf-8') as source:
                batch = []
                for line in source:
                    r = json.loads(line)
                    if not lo <= r['cntrctCnclsDate'] <= hi:
                        raise SystemExit(f'{week}: {r["untyCntrctNo"]} dated {r["cntrctCnclsDate"]}, outside the week')
                    batch.append(row_values(r, week, anomalies))
                    if len(batch) == 5000:
                        db.executemany(insert, batch); rows += len(batch); batch = []
                db.executemany(insert, batch); rows += len(batch)
            summary_path = path.with_name(f'{week}.summary.json')
            summary = summary_path.read_text().strip() if summary_path.exists() else None
            db.execute('INSERT OR REPLACE INTO weeks VALUES (?, ?, ?, ?, ?)', (week, stat.st_size, stat.st_mtime, rows, summary))
        changed += 1
        print(f'{week}: {rows} versions' + (f', non-numeric {anomalies}' if anomalies else ''), flush=True)
    if changed or not db.execute("SELECT 1 FROM sqlite_master WHERE name = 'contracts'").fetchone():
        with db:
            build_contracts(db)
    weeks, versions = db.execute('SELECT COUNT(*), SUM(rows) FROM weeks').fetchone()
    contracts, originals = db.execute('SELECT COUNT(*), SUM(original_in_period) FROM contracts').fetchone()
    print(f'{weeks} weeks, {versions} versions, {contracts} contracts ({originals} signed in the period); {changed} weeks loaded now')


if __name__ == '__main__':
    main()
