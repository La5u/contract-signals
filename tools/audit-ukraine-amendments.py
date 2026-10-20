#!/usr/bin/env python3
"""Bounded opt-in public module audit; default is strict offline evidence replay."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import canonical, require, sha, without_hashes  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PLAN = Path.home() / '.cache/contract-signals/ukraine-public-audit/v1/plan.json'
OUTPUT = ROOT / 'data/ukraine-amendment-evidence.json'
LIMIT = 2097152
TYPES = {'priceReductionWithoutQuantity', 'qualityImprovement', 'fiscalYearExtension',
         'durationExtension', 'itemPriceVariation', 'taxRate', 'thirdParty', 'volumeCuts',
         'currencyRate', 'partyChange'}
STATUSES = {'active', 'pending', 'terminated', 'cancelled', 'unsuccessful'}

def load(path):
    return json.loads(Path(path).read_text())

def helper(root):
    spec = importlib.util.spec_from_file_location('frozen_prepare', root / 'tools/prepare-ukraine-public-audit.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def date_valid(value):
    if not isinstance(value, str) or len(value) > 40:
        return False
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is not None
    except ValueError:
        return False

def scalar(value, kind):
    if kind == 'id':
        return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value) else None
    if kind == 'date':
        return value if date_valid(value) else None
    if kind == 'status':
        return value if isinstance(value, str) and value in STATUSES else None

def inventory(root=ROOT, private_plan=None):
    root = Path(root)
    plan = load(root / 'data/ukraine-public-audit-plan.json')
    # Public offline replay must work in a fresh checkout without a private freeze.
    # Acquisition additionally requires the original external read-only freeze.
    if private_plan is not None:
        private_plan = Path(private_plan)
        require(not any(p.is_symlink() for p in (private_plan, *private_plan.parents)) and
                private_plan.stat().st_mode & 0o777 == 0o400, 'Private freeze permissions')
        require(without_hashes(load(private_plan)) == without_hashes(plan), 'Private freeze mismatch')
    require(without_hashes(helper(root).build(root)) == without_hashes(plan), 'Frozen selection/bindings changed')
    rows = load(root / 'data/prozorro.json')
    snapshot = load(root / 'data/prozorro-contract-changes.json')
    require(len(rows) == 488 and len({r['id'] for r in rows}) == 488, 'Row population mismatch')
    require(set(snapshot['contracts']) == {r['contractInternalId'] for r in rows} and not snapshot['failedIds'], 'Snapshot coverage mismatch')
    require(snapshot['source'] == 'https://public-api.prozorro.gov.ua/api/2.5/contracts/{id}', 'Snapshot endpoint mismatch')
    binds = []
    for i, row in enumerate(rows):
        path = 'data/prozorro/raw/records/' + row['tenderID'] + '.json.gz'
        tender = json.loads(gzip.decompress((root / path).read_bytes()))['data']
        contracts = [(j, c) for j, c in enumerate(tender.get('contracts', [])) if c.get('id') == row['contractInternalId']]
        awards = [(j, a) for j, a in enumerate(tender.get('awards', [])) if a.get('id') == row['awardId']]
        require(len(contracts) == len(awards) == 1, 'Ambiguous mapping')
        ci, contract = contracts[0]; ai, award = awards[0]
        require(tender['id'] == row['procedureId'] and tender['tenderID'] == row['tenderID'] and
                tender['procuringEntity']['identifier']['id'] == row['buyerId'] and
                contract['contractID'] == row['contractId'] and contract['awardID'] == award['id'] and
                award.get('lotID') == row.get('lotId'), 'Cached identity mismatch')
        if row.get('lotId') is not None:
            require(sum(l.get('id') == row['lotId'] for l in tender.get('lots', [])) == 1, 'Ambiguous lot')
        require(row['source'] == 'https://public-api.prozorro.gov.ua/api/2.5/tenders/' + tender['id'], 'Tender endpoint mismatch')
        old = snapshot['contracts'][row['contractInternalId']]
        require(type(old['changes']) is int and old['changes'] >= 0 and old['changes'] == row['contractChanges'], 'Snapshot count mismatch')
        require(old['rationaleTypes'] == row['contractChangeTypes'], 'Snapshot types mismatch')
        require(isinstance(old['changeDates'], list), 'Snapshot dates malformed')
        binds.append({'rowId': row['id'], 'rowPointer': '/' + str(i), 'rowSha256': sha(canonical(row)),
                      'rawPath': path, 'rawSha256': plan['rawSnapshotHashes'][path],
                      'contractPointer': '/data/contracts/' + str(ci), 'awardPointer': '/data/awards/' + str(ai),
                      **{k: row.get(k) for k in ('contractInternalId', 'contractId', 'awardId', 'buyerId', 'lotId', 'procedureId', 'tenderID')},
                      'snapshotPointer': '/contracts/' + row['contractInternalId'], 'snapshot': old,
                      'snapshotDateAnomalies': sum(not date_valid(d) for d in old['changeDates']),
                      'snapshotStatusAnomaly': old.get('status') not in STATUSES,
                      'snapshotTypeAnomalies': [t for t in old['rationaleTypes'] if t not in TYPES]})
    return plan, binds

def extract(payload, binding):
    data = payload.get('data')
    require(isinstance(data, dict), 'Missing module data')
    for field, key in [('id', 'contractInternalId'), ('contractID', 'contractId'), ('tender_id', 'tenderInternalId'), ('awardID', 'awardId')]:
        require(data.get(field) == binding[key], 'Module identity mismatch: ' + field)
    result = {'scalars': [], 'anomalies': [], 'changesState': 'unavailable', 'changeCount': None,
              'activeChangeCount': None, 'legalBasis': 'unknown', 'independentFinancialBasis': 'unknown'}
    def add(pointer, value):
        result['scalars'].append({'pointer': pointer, 'value': value})
    for key in ('id', 'contractID', 'tender_id', 'awardID'):
        add('/data/' + key, data[key])
    for key, kind in [('status', 'status'), ('dateSigned', 'date'), ('date', 'date')]:
        if key in data:
            v = scalar(data[key], kind)
            if v is not None:
                add('/data/' + key, v)
                if key == 'dateSigned' and v[:10] < binding['tenderID'][3:13]:
                    result['anomalies'].append('dateSigned:before-tender-id-calendar-date')
            else: result['anomalies'].append(key + ':invalid-or-unrecognized')
    value = data.get('value')
    if isinstance(value, dict):
        for key in ('amount', 'amountNet', 'valueAddedTaxIncluded', 'currency'):
            v = value.get(key)
            if ((key.startswith('amount') and type(v) in (int, float) and abs(v) < 1e16) or
                (key == 'valueAddedTaxIncluded' and type(v) is bool) or
                (key == 'currency' and isinstance(v, str) and re.fullmatch('[A-Z]{3}', v))):
                add('/data/value/' + key, v)
    changes = data.get('changes')
    if 'changes' not in data:
        result['anomalies'].append('changes:absent-no-schema-default-assumed')
    elif not isinstance(changes, list):
        result['anomalies'].append('changes:not-array')
    else:
        result.update(changesState='retrieved-empty-array' if not changes else 'retrieved-array', changeCount=len(changes), activeChangeCount=0)
        seen = set()
        for i, change in enumerate(changes):
            p = '/data/changes/' + str(i)
            if not isinstance(change, dict):
                result['anomalies'].append(p + ':not-object'); continue
            cid = scalar(change.get('id'), 'id')
            if cid is None or cid in seen: result['anomalies'].append(p + ':missing-invalid-or-duplicate-id')
            if cid is not None: seen.add(cid); add(p + '/id', cid)
            for key, kind in [('status', 'status'), ('date', 'date'), ('dateSigned', 'date')]:
                v = scalar(change.get(key), kind)
                if v is not None: add(p + '/' + key, v)
                else: result['anomalies'].append(p + '/' + key + ':missing-invalid-or-unrecognized')
            result['activeChangeCount'] += change.get('status') == 'active'
            types = change.get('rationaleTypes')
            if not isinstance(types, list): result['anomalies'].append(p + '/rationaleTypes:not-array')
            else:
                for j, category in enumerate(types):
                    if isinstance(category, str) and category in TYPES: add(p + '/rationaleTypes/' + str(j), category)
                    else: result['anomalies'].append(p + '/rationaleTypes/' + str(j) + ':unrecognized')
    # No names, descriptions, titles, free-form rationale, document URLs or tokens.
    for i, doc in enumerate(data.get('documents', []) if isinstance(data.get('documents'), list) else []):
        if not isinstance(doc, dict): continue
        for key in ('id', 'format', 'documentType'):
            v = doc.get(key)
            safe = scalar(v, 'id') if key == 'id' else (v if key == 'format' and isinstance(v, str) and re.fullmatch(r'[a-z0-9.+-]+/[a-z0-9.+-]+', v) else None)
            if key == 'documentType' and isinstance(v, str) and v in {'contractSigned', 'contractAnnexe', 'contractTermination', 'contractChanges'}: safe = v
            if safe is not None: add('/data/documents/' + str(i) + '/' + key, safe)
    return result

def private_directory(root=ROOT):
    parent = Path.home() / '.cache/contract-signals/ukraine-amendments'
    require(not any(p.is_symlink() for p in (parent, *parent.parents)), 'Symlinked private path')
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(parent.stat().st_mode & 0o077 == 0 and not parent.resolve().is_relative_to(Path(root).resolve()), 'Unsafe private directory')
    return Path(tempfile.mkdtemp(prefix='run-', dir=parent))

def fetch(plan, directory):
    ledger = []
    last = None
    for i, binding in enumerate(plan['selected']):
        if last is not None: time.sleep(max(0, 1 - (time.monotonic() - last)))
        url = binding['contractURL']
        require(url == 'https://public-api.prozorro.gov.ua/api/2.5/contracts/' + binding['contractInternalId'], 'Unapproved endpoint')
        path = directory / ('response-%02d.bin' % i)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        started = datetime.now(timezone.utc).isoformat(); last = time.monotonic()
        with os.fdopen(fd, 'wb') as stream:
            proc = subprocess.run(['curl', '-q', '--silent', '--proto', '=https', '--max-time', '15',
                                   '--max-filesize', str(LIMIT), '--retry', '0', '--max-redirs', '0',
                                   '--request', 'GET', '--write-out', '%{stderr}%{http_code}', url],
                                  stdout=stream, stderr=subprocess.PIPE, timeout=18)
        blob = path.read_bytes()
        require(len(blob) <= LIMIT, 'Response exceeded bound')
        status = int(proc.stderr[-3:]) if re.fullmatch(rb'\d{3}', proc.stderr[-3:]) else 0
        entry = {'rowId': binding['rowId'], 'binding': binding, 'url': url, 'method': 'GET',
                 'startedAt': started, 'finishedAt': datetime.now(timezone.utc).isoformat(),
                 'httpStatus': status, 'curlExit': proc.returncode, 'responseBytes': len(blob),
                 'responseSha256': sha(blob), 'responseComplete': proc.returncode == 0,
                 'rawPrivateFile': path.name, 'outcome': 'unavailable', 'extract': None}
        if status == 200 and proc.returncode == 0:
            try:
                entry['extract'] = extract(json.loads(blob), binding); entry['outcome'] = 'verified-module'
            except (ValueError, TypeError, KeyError):
                entry['outcome'] = 'invalid-json-or-identity'
        ledger.append(entry)
        if status in (403, 429): break
    return ledger

def evidence(plan, binds, ledger):
    body = {'schemaVersion': 'ukraine-amendment-evidence-v1', 'planSha256': plan['planSha256'],
            'inputHashes': plan['inputHashes'], 'rawSnapshotHashes': plan['rawSnapshotHashes'],
            'rows': binds, 'requests': ledger, 'requestCount': len(ledger),
            'supplementaryRequests': 0,
            'limitations': ['Old minimized snapshot lacks full module-body hashes and link fields; all 488 module links cannot be retrospectively independently proven.',
                            'Absent changes is unavailable, not zero; no published schema default validated.',
                            'Rationale categories are metadata, not legal findings; independent legal/financial basis unknown.',
                            'Response hashes bind private acquisition bytes, not independently recoverable public raw bodies.']}
    body['evidenceSha256'] = sha(canonical(body))
    return body

def replay(doc, plan, binds):
    requests = doc.get('requests', [])
    require(len(requests) <= 12 and doc.get('requestCount') == len(requests) and doc.get('supplementaryRequests') == 0, 'Request bounds')
    require(len(requests) == len(plan['selected']) or (requests and requests[-1]['httpStatus'] in (403, 429)), 'Incomplete request coverage without stop condition')
    stopped = False
    ledger_keys = {'rowId', 'binding', 'url', 'method', 'startedAt', 'finishedAt', 'httpStatus',
                   'curlExit', 'responseBytes', 'responseSha256', 'responseComplete', 'rawPrivateFile', 'outcome', 'extract'}
    for i, entry in enumerate(requests):
        require(set(entry) == ledger_keys and entry['outcome'] in {'unavailable', 'verified-module', 'invalid-json-or-identity'}, 'Non-allowlisted ledger fields')
        require(type(entry['httpStatus']) is int and (entry['httpStatus'] == 0 or 100 <= entry['httpStatus'] <= 599), 'Invalid HTTP status')
        require(type(entry['curlExit']) is int and entry['responseComplete'] == (entry['curlExit'] == 0), 'Invalid transport completion')
        require(entry['rawPrivateFile'] == 'response-%02d.bin' % i, 'Unsafe private file pointer')
        require(not stopped and without_hashes(entry['binding']) == without_hashes(plan['selected'][i]) and entry['rowId'] == plan['selected'][i]['rowId'] and entry['url'] == plan['selected'][i]['contractURL'] and entry['method'] == 'GET', 'Request selection mismatch')
        require(0 <= entry['responseBytes'] <= LIMIT, 'Response ledger invalid')
        require(date_valid(entry['startedAt']) and date_valid(entry['finishedAt']), 'Request dates invalid')
        duration = (datetime.fromisoformat(entry['finishedAt']) - datetime.fromisoformat(entry['startedAt'])).total_seconds()
        require(0 <= duration <= 18, 'Request duration outside bound')
        if i:
            require((datetime.fromisoformat(entry['startedAt']) - datetime.fromisoformat(requests[i - 1]['startedAt'])).total_seconds() >= 1, 'Request spacing violation')
        stopped = entry['httpStatus'] in (403, 429)
        require((entry['extract'] is not None) == (entry['outcome'] == 'verified-module'), 'Extraction outcome mismatch')
        if entry['extract'] is not None:
            require(entry['httpStatus'] == 200 and entry['responseComplete'] and entry['outcome'] == 'verified-module', 'Unsupported extraction')
            # Reconstruct only published scalar pointers and reapply the exact allowlist/identity checks.
            data = {}
            pointers = [s['pointer'] for s in entry['extract']['scalars']]
            require(len(pointers) == len(set(pointers)), 'Duplicate scalar pointer')
            for item in entry['extract']['scalars']:
                require(re.fullmatch(r'/data/(id|contractID|tender_id|awardID|status|date|dateSigned|value/(amount|amountNet|currency|valueAddedTaxIncluded)|changes/[0-9]{1,4}/(id|status|date|dateSigned|rationaleTypes/[0-9]{1,3})|documents/[0-9]{1,4}/(id|format|documentType))', item['pointer']), 'Unsafe scalar pointer')
                parts = item['pointer'].split('/')[2:]
                current = data
                for j, part in enumerate(parts[:-1]):
                    nxt = parts[j + 1]
                    if isinstance(current, list):
                        while len(current) <= int(part): current.append({})
                        current = current[int(part)]
                    else: current = current.setdefault(part, [] if nxt.isdigit() else {})
                if isinstance(current, list):
                    while len(current) <= int(parts[-1]): current.append(None)
                    current[int(parts[-1])] = item['value']
                else: current[parts[-1]] = item['value']
            state = entry['extract']['changesState']
            require(state in {'unavailable', 'retrieved-empty-array', 'retrieved-array'}, 'Unknown changes state')
            if state == 'retrieved-empty-array': data['changes'] = []
            checked = extract({'data': data}, entry['binding'])
            require(checked['scalars'] == entry['extract']['scalars'], 'Non-allowlisted scalar')
            require(checked == entry['extract'], 'Extraction status/date/count/anomaly mismatch')
    require(without_hashes(doc) == without_hashes(evidence(plan, binds, requests)), 'Stale evidence or incomplete row binds')
    return {'rows': len(binds), 'requests': len(requests), 'outcomes': dict(Counter(r['outcome'] for r in requests)),
            'snapshotCounts': dict(Counter(str(r['snapshot']['changes']) for r in binds)),
            'snapshotStatuses': dict(Counter(r['snapshot']['status'] for r in binds)),
            'snapshotTypes': dict(Counter(t for r in binds for t in r['snapshot']['rationaleTypes'])),
            'snapshotDateAnomalies': sum(r['snapshotDateAnomalies'] for r in binds)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    plan, binds = inventory(private_plan=PRIVATE_PLAN if args.fetch else None)
    if args.fetch:
        require(not OUTPUT.exists(), 'Evidence already exists; refusing repeat acquisition')
        directory = private_directory()
        doc = evidence(plan, binds, fetch(plan, directory))
        replay(doc, plan, binds)
        with OUTPUT.open('x') as stream: stream.write(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(replay(load(OUTPUT), plan, binds), indent=2))

if __name__ == '__main__':
    main()
