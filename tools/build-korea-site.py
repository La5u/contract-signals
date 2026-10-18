#!/usr/bin/env python3
"""Build the static folder of Korean contracts that the explorer loads (published separately, not in git).

Reads the private database ~/.cache/contract-signals/korea/opnstd.sqlite (tools/normalize-korea-opnstd.py) and
writes ~/.cache/contract-signals/korea/site/:

- meta.json   source, licence, period, counts, code lists shared by every shard, column order
- buyers.json one entry per contracting institution: [code, name, type, contracts, shard] or, for a buyer too big for
              one file, [code, name, type, contracts, newest part, [parts oldest first]]
- s/NNNN.json contracts of a run of buyers (by code), about 1.5 MB each, rows as arrays; a big buyer gets shards of
              its own (parts of about 8 MB, under the host's 25 MiB per file), each holding a run of its rows by date
- _headers, robots.txt, index.html for the static host

Only the fields the explorer shows are kept; the full record is linked on KONEPS (나라장터). Individual businesses
(sole traders) keep their published trade name, flagged, but not their business registration number
(docs/personal-data.md). Hosting: a separate Cloudflare Pages project uploaded with wrangler, so the data never
enters the repository (memory note korea-hosting; HANDOFF).

    python tools/build-korea-site.py [--db PATH] [--out DIR] [--origin https://contracts.lasu.dev]
"""
import argparse
import json
import shutil
import sqlite3
from itertools import groupby
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

BASE = Path.home() / '.cache/contract-signals/korea'
SHARD_BYTES = 1_500_000
PART_BYTES = 8_000_000
COLUMNS = ['contractNo', 'date', 'dateIsFirstChange', 'name', 'demand', 'supplier', 'supplierBizrno', 'supplierKind',
           'originalAmount', 'latestAmount', 'versions', 'method', 'businessType', 'noticeNo', 'legalRef', 'joint',
           'linkContract', 'linkChangeOrder', 'linkKind']
KINDS = ['corporation', 'individual', 'public-body', 'association', 'foreign', 'unknown']
LINK = 'https://www.g2b.go.kr/link/FIUA027_01/single/?ctrtNo={}&ctrtChgOrd={}&prcmBsneSeCd={}&srchName=ctrtCrst&openUrl=Y'

QUERY = '''
select c.cntrct_no, c.signed, c.first_date_seen, c.original_in_period, c.last_name, v.demand_name,
       c.last_supplier_name, c.last_supplier_bizrno, c.last_supplier_kind, c.original_amount, c.last_amount, c.versions_seen,
       c.last_method, c.last_business_type, c.last_notice_no, c.last_legal_ref, c.last_joint, v.contract_url,
       c.last_buyer_code, c.last_buyer_name, c.last_buyer_type
from contracts c join versions v on v.cntrct_no = c.cntrct_no and v.ord = c.last_ord
order by c.last_buyer_code, coalesce(c.signed, c.first_date_seen), c.cntrct_no
'''


def index(values, value):
    if value is None:
        return None
    if value not in values:
        values.append(value)
    return values.index(value)


def link_parts(url, kinds):
    q = parse_qs(urlsplit(url or '').query)
    try:
        return q['ctrtNo'][0], q['ctrtChgOrd'][0], index(kinds, q['prcmBsneSeCd'][0])
    except (KeyError, IndexError):
        return None, None, None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--db', default=str(BASE / 'opnstd.sqlite'))
    p.add_argument('--out', default=str(BASE / 'site'))
    p.add_argument('--origin', default='https://contracts.lasu.dev', help='the explorer allowed to read the files (CORS)')
    args = p.parse_args(argv)
    db = sqlite3.connect(f'file:{args.db}?mode=ro', uri=True)
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    (out / 's').mkdir(parents=True)

    methods, types, link_kinds = [], [], []
    buyers = {}
    first_date = last_date = None

    def contract_row(r):
        nonlocal first_date, last_date
        (no, signed, first_seen, original_in, name, demand, supplier, bizrno, kind, original, latest, versions,
         method, btype, notice, legal, joint, url, bcode, bname, btype_buyer) = r
        individual = kind == 'individual'
        date = signed or first_seen
        if date:
            first_date = min(first_date or date, date)
            last_date = max(last_date or date, date)
        buyers.setdefault(bcode, [bcode, bname, btype_buyer, 0, None])[3] += 1
        return [
            no, date, 0 if signed else 1, name, demand, supplier, None if individual else bizrno,
            KINDS.index(kind) if kind in KINDS else KINDS.index('unknown'),
            original if original_in else None, latest, versions, index(methods, method), index(types, btype),
            notice or None, legal, 1 if joint == 'Y' else 0, *link_parts(url, link_kinds)]

    # Pack consecutive buyers (by code) into shards of about SHARD_BYTES; per-shard lists for demand and legal ground.
    # Rows are streamed one buyer at a time (the full history does not fit in memory).
    shard, size, n = None, 0, 0
    def flush():
        nonlocal shard, n, size
        if shard:
            (out / 's' / f'{n:04d}.json').write_text(json.dumps(shard, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
            n += 1
        shard, size = None, 0

    def packed(rows, target):
        return [[*r[:4], index(target['demand'], r[4]), *r[5:14], index(target['legal'], r[14]), *r[15:]] for r in rows]

    for code, group in groupby(db.execute(QUERY), key=lambda r: r[18]):
        rows = [contract_row(r) for r in group]
        rough = len(json.dumps(rows, ensure_ascii=False, separators=(',', ':')).encode())
        if rough > PART_BYTES:
            # A big buyer: shards of its own, rows split by date order; the newest part is buyers.json's shard,
            # so a reader that loads a single shard still shows the latest contracts.
            flush()
            count = -(-rough // PART_BYTES)
            step = -(-len(rows) // count)
            parts = []
            for i in range(0, len(rows), step):
                shard = {'v': 1, 'demand': [], 'legal': [], 'buyers': {}}
                shard['buyers'][code] = packed(rows[i:i + step], shard)
                parts.append(n)
                flush()
            buyers[code][4:] = [parts[-1], parts]
            continue
        if shard is None:
            shard = {'v': 1, 'demand': [], 'legal': [], 'buyers': {}}
        shard['buyers'][code] = packed(rows, shard)
        buyers[code][4] = n
        size += rough
        if size >= SHARD_BYTES:
            flush()
    flush()

    built = datetime.now(timezone.utc).isoformat(timespec='seconds')
    ordered = sorted(buyers.values(), key=lambda b: -b[3])
    (out / 'buyers.json').write_text(json.dumps(ordered, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    meta = {
        'v': 1, 'built': built, 'contracts': sum(b[3] for b in ordered), 'buyers': len(ordered), 'shards': n,
        'period': [first_date, last_date],
        'source': 'Public Procurement Service (조달청), open-standard contract data (공공데이터 개방표준 계약정보), data.go.kr',
        'licence': 'data.go.kr: 이용허락범위 제한 없음 (no restriction on use); source attribution given',
        'columns': COLUMNS, 'methods': methods, 'businessTypes': types, 'supplierKinds': KINDS, 'linkKinds': link_kinds,
        'link': LINK,
        'notes': ['One row per contract number, from its latest version in the period. Original amount only when the original contract was signed in the period.',
                  'dateIsFirstChange = 1: the contract was signed before the period; the date is its first change in the period.',
                  'A buyer too big for one file has a sixth entry in buyers.json: its shards, oldest contracts first; the fifth entry is the newest part.',
                  'Individual businesses keep their published trade name; their business registration number is left out.',
                  'Officials, representatives, phone numbers, e-mails and street addresses are not included.'],
    }
    (out / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    (out / '_headers').write_text(
        '# Read by the explorer only; kept out of search engines (docs/personal-data.md).\n'
        f'/*\n  Access-Control-Allow-Origin: {args.origin}\n  Vary: Origin\n  X-Robots-Tag: noindex\n'
        '  X-Content-Type-Options: nosniff\n  Referrer-Policy: no-referrer\n', encoding='utf-8')
    (out / 'robots.txt').write_text('User-agent: *\nDisallow: /\n', encoding='utf-8')
    (out / 'index.html').write_text(
        '<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><title>Contract Signals · Korean data files</title>'
        f'<p>Data files for <a href="{args.origin}/#dataset=korea">Contract Signals</a>: South Korean public contracts '
        f'({meta["period"][0]} to {meta["period"][1]}), from the Public Procurement Service open data on data.go.kr. '
        'Use the explorer to browse them.</p>\n', encoding='utf-8')
    total = sum(f.stat().st_size for f in out.rglob('*') if f.is_file())
    files = sum(1 for f in out.rglob('*') if f.is_file())
    biggest = max((out / 's').iterdir(), key=lambda f: f.stat().st_size)
    split = sum(1 for b in ordered if len(b) > 5)
    print(f'{meta["contracts"]:,} contracts {meta["period"][0]}..{meta["period"][1]}, {meta["buyers"]:,} buyers ({split} split), '
          f'{n} shards; {files} files, {total / 1e6:.0f} MB; largest {biggest.name} {biggest.stat().st_size / 1e6:.1f} MB → {out}')
    if files > 20_000 or biggest.stat().st_size > 25 * 2 ** 20:
        raise SystemExit('over the Cloudflare Pages free limits (20,000 files, 25 MiB per file)')


if __name__ == '__main__':
    main()
