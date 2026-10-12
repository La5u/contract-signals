#!/usr/bin/env python3
"""Random-sample field accuracy check of published Prozorro rows against official records.

  --plan   freeze a seeded simple random sample of data/prozorro.json (refuses to overwrite)
  --fetch  one live tender GET + one contract-module GET per sampled row, into a private cache
  (default) compare every published field with the cached raw tender and the live records,
            write minimized results to data/ukraine-random-sample-results.json

Field values are re-derived here from the Prozorro standard, not by calling the importer, so an
importer mistake shows up as published != cached raw; later publisher edits as cached != live.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from personal_ids import mask  # noqa: E402

ROWS = 'data/prozorro.json'
RAW = ROOT / 'data/prozorro/raw/records'
PLAN = ROOT / 'data/ukraine-random-sample-plan.json'
RESULTS = ROOT / 'data/ukraine-random-sample-results.json'
CACHE = Path.home() / '.cache/contract-signals/ukraine-random-sample/v1'
API = 'https://public-api.prozorro.gov.ua/api/2.5'
SEED = 'ukraine-random-sample-2026-10-12'
SIZE = 40
LIMIT = 8 * 1024 * 1024
COMPETITIVE = {'aboveThreshold', 'aboveThresholdEU', 'aboveThresholdUA', 'belowThreshold', 'requestForProposal',
               'priceQuotation', 'competitiveOrdering', 'simple.defense', 'esco'}
FIELDS = ['tenderID', 'procedureId', 'contractId', 'awardId', 'lotId', 'lotCount', 'buyer', 'buyerId', 'supplier',
          'supplierIds', 'date', 'amount', 'currency', 'procedure', 'category', 'cpv', 'description', 'offers',
          'complaintCount', 'tenderCreated']


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def plan():
    blob = (ROOT / ROWS).read_bytes()
    ids = sorted(r['id'] for r in json.loads(blob))
    chosen = sorted(ids, key=lambda i: sha(f'{SEED}:{i}'.encode()))[:SIZE]
    return {'schemaVersion': 1, 'seed': SEED, 'method': 'simple random: rank row ids by sha256(seed:id), take first N',
            'population': len(ids), 'size': SIZE, 'rowsSha256': sha(blob), 'selected': chosen}


def expected(tender, row):
    """What each published field should be, read directly from an official tender record."""
    contract = next(c for c in tender.get('contracts') or [] if c['id'] == row['contractInternalId'])
    award = next(a for a in tender.get('awards') or [] if a['id'] == contract['awardID'])
    lot = award.get('lotID')
    entity = tender['procuringEntity']
    supplier = award['suppliers'][0]
    ident = supplier.get('identifier') or {}
    code = str(ident.get('id') or '')
    kind = ('EDRPOU' if len(code) == 8 else 'RNOKPP' if len(code) == 10 else 'UA-EDR') \
        if ident.get('scheme') == 'UA-EDR' and code.isdigit() else 'published identifier'
    items = [i for i in tender.get('items') or [] if not lot or i.get('relatedLot') == lot]
    cpvs = [i['classification']['id'] for i in items if (i.get('classification') or {}).get('scheme') in ('ДК021', 'CPV')]
    lots = {l['id']: l for l in tender.get('lots') or []}
    title = (tender.get('title') or '').strip()
    lot_title = ((lots.get(lot) or {}).get('title') or '').strip()
    value = contract.get('value') or award.get('value') or {}
    offers = None
    if tender['procurementMethodType'] in COMPETITIVE and tender.get('bids'):
        live = [b for b in tender['bids'] if b.get('status') not in ('deleted', 'draft')]
        offers = len([b for b in live if not lot or any(v.get('relatedLot') == lot for v in b.get('lotValues') or [])])
    return {
        'tenderID': tender['tenderID'], 'procedureId': tender['id'], 'contractId': contract.get('contractID'),
        'awardId': award['id'], 'lotId': lot, 'lotCount': len(lots),
        'buyer': (entity.get('identifier') or {}).get('legalName') or entity.get('name'),
        'buyerId': (entity.get('identifier') or {}).get('id'),
        'supplier': ident.get('legalName') or supplier.get('name'),
        'supplierIds': [{'id': mask(kind, code), 'identifierType': kind}] if code else [],
        'date': (contract.get('dateSigned') or contract.get('date') or '')[:10] or None,
        'amount': value.get('amount'), 'currency': value.get('currency'),
        'procedure': tender['procurementMethodType'], 'category': tender.get('mainProcurementCategory'),
        'cpv': cpvs[0].split('-')[0] if cpvs else None,
        'description': title if not lot_title or lot_title == title else f'{title} — {lot_title}',
        'offers': offers,
        'complaintCount': len(tender.get('complaints') or []) + sum(len(a.get('complaints') or []) for a in tender.get('awards') or []),
        'tenderCreated': (tender.get('dateCreated') or '')[:10] or None,
    }


def module_facts(module, row):
    """Cross-source facts from the separate contracting-module record."""
    d = module['data']
    value = d.get('value') or {}
    sup = (d.get('suppliers') or [{}])[0]
    return {'identity': d.get('id') == row['contractInternalId'] and d.get('contractID') == row['contractId']
                        and d.get('awardID') == row['awardId'],
            'amount': value.get('amount'), 'currency': value.get('currency'),
            'supplier': (sup.get('identifier') or {}).get('legalName') or sup.get('name'),
            'activeChanges': sum(c.get('status') == 'active' for c in d.get('changes') or []),
            'status': d.get('status')}


def get(url):
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'contract-signals-accuracy/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read(LIMIT + 1)
    if len(body) > LIMIT:
        raise RuntimeError('response over limit: ' + url)
    return body


def fetch(frozen, rows):
    CACHE.mkdir(parents=True, exist_ok=True)
    os.chmod(CACHE, 0o700)
    ledger = []
    for rid in frozen['selected']:
        row = rows[rid]
        for kind, url in [('tender', row['source']), ('module', f"{API}/contracts/{row['contractInternalId']}")]:
            path = CACHE / f"{rid}.{kind}.json"
            if path.exists():
                continue
            started = datetime.now(timezone.utc).isoformat()
            try:
                body, status = get(url), 200
            except urllib.error.HTTPError as e:
                body, status = b'', e.code
            if status == 200:
                path.write_bytes(body)
                os.chmod(path, 0o600)
            ledger.append({'rowId': rid, 'kind': kind, 'url': url, 'retrievedAt': started, 'httpStatus': status,
                           'bytes': len(body), 'sha256': sha(body) if body else None})
            if status in (403, 429):
                raise SystemExit(f'stopped on HTTP {status}; no retries')
            time.sleep(1)
    log = CACHE / 'ledger.json'
    old = json.loads(log.read_text()) if log.exists() else []
    log.write_text(json.dumps(old + ledger, ensure_ascii=False, indent=1))
    print(len(ledger), 'requests;', sum(r['httpStatus'] == 200 for r in ledger), 'HTTP 200')


def compare(frozen, rows):
    out, totals = [], {'importErrors': 0, 'sourceChangedSinceImport': 0, 'moduleDisagreements': 0}
    ledger = {(r['rowId'], r['kind']): r for r in json.loads((CACHE / 'ledger.json').read_text())}
    for rid in frozen['selected']:
        row = rows[rid]
        cached = json.loads(gzip.decompress((RAW / f"{row['tenderID']}.json.gz").read_bytes()))['data']
        live = json.loads((CACHE / f'{rid}.tender.json').read_bytes())['data']
        module = json.loads((CACHE / f'{rid}.module.json').read_bytes())
        want_cached, want_live, mod = expected(cached, row), expected(live, row), module_facts(module, row)
        fields = {}
        for f in FIELDS:
            entry = {'published': row[f] == want_cached[f], 'live': want_cached[f] == want_live[f]}
            if not entry['published']:
                entry['publishedValue'], entry['rawValue'] = row[f], want_cached[f]
                totals['importErrors'] += 1
            if not entry['live']:
                entry['liveValue'] = want_live[f] if f != 'supplierIds' else '(changed)'
                totals['sourceChangedSinceImport'] += 1
            fields[f] = entry
        checks = {'moduleIdentity': mod['identity'],
                  'moduleAmount': (mod['amount'], mod['currency']) == (row['amount'], row['currency']),
                  'moduleSupplier': mod['supplier'] == row['supplier'],
                  'moduleActiveChanges': mod['activeChanges'] == row.get('contractChanges')}
        totals['moduleDisagreements'] += sum(not v for v in checks.values())
        notes = {k: v for k, v in [('moduleAmount', [mod['amount'], mod['currency']]), ('moduleSupplier', mod['supplier']),
                                   ('moduleActiveChanges', mod['activeChanges'])] if not checks[k]}
        out.append({'rowId': rid, 'procedure': row['procedure'], 'moduleStatus': mod['status'],
                    'retrieved': {k: ledger[(rid, k)]['retrievedAt'] for k in ('tender', 'module') if (rid, k) in ledger},
                    'responseSha256': {k: ledger[(rid, k)]['sha256'] for k in ('tender', 'module') if (rid, k) in ledger},
                    'fields': fields, 'moduleChecks': checks, 'moduleValues': notes})
    return {'schemaVersion': 1, 'plan': str(PLAN.relative_to(ROOT)), 'planSha256': sha(PLAN.read_bytes()),
            'fieldsChecked': FIELDS, 'rows': len(out), 'fieldComparisons': len(out) * len(FIELDS),
            'totals': totals, 'results': out}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--plan', action='store_true')
    p.add_argument('--fetch', action='store_true')
    a = p.parse_args()
    if a.plan:
        if PLAN.exists():
            raise SystemExit('plan already frozen; never overwritten')
        PLAN.write_text(json.dumps(plan(), indent=1) + '\n')
        print('frozen', PLAN)
        return
    frozen = json.loads(PLAN.read_text())
    if frozen != plan():
        raise SystemExit('rows changed since the plan was frozen; make a new plan version')
    rows = {r['id']: r for r in json.loads((ROOT / ROWS).read_text())}
    if a.fetch:
        fetch(frozen, rows)
        return
    result = compare(frozen, rows)
    RESULTS.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(result['totals']))


if __name__ == '__main__':
    main()
