#!/usr/bin/env python3
"""Offline exact amount-basis audit. Network acquisition is explicit and bounded."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'data/ukraine-amount-basis-evidence.json'
PLAN = ROOT / 'data/ukraine-public-audit-plan.json'
PRIVATE_PLAN = Path.home() / '.cache/contract-signals/ukraine-public-audit/v1/plan.json'
API = 'https://public-api.prozorro.gov.ua/api/2.5/'
LIMIT = 2097152
FIELDS = ('amount', 'currency', 'valueAddedTaxIncluded')


def canonical(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def sha(x):
    return hashlib.sha256(x).hexdigest()


def without_hashes(value):
    if isinstance(value, dict):
        return {k: without_hashes(v) for k, v in value.items()
                if k not in ('inputHashes', 'rawSnapshotHashes', 'checksum') and not k.lower().endswith('sha256')}
    if isinstance(value, list):
        return [without_hashes(v) for v in value]
    return value


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pointer(obj, path):
    for key in path.strip('/').split('/'):
        obj = obj[int(key)] if isinstance(obj, list) else obj[key]
    return obj


def tuple_diff(c, a):
    # Presence matters: absent/null is not false or zero.
    return [k for k in FIELDS if (k in c, c.get(k)) != (k in a, a.get(k))]


def explanation(c, a):
    if not tuple_diff(c, a):
        return 'same-published-tuple'
    if ('amountNet' in c and c.get('currency') == a.get('currency') and
            c.get('currency') is not None and c.get('valueAddedTaxIncluded') is True and
            a.get('valueAddedTaxIncluded') is False and 'amount' in a and
            c['amountNet'] == a['amount'] and 'amount' in c and c['amount'] != a['amount']):
        return 'explicit-contract-net-equals-award-excluding-vat'
    return 'unresolved-field-difference'


def normalized(c, a):
    # Reproduce the existing importer, never repair it or replace values here.
    basis = 'contract' if c else 'award-fallback' if a else 'absent'
    value = c or a or {}
    return {'basis': basis, 'amount': value.get('amount'), 'currency': value.get('currency'),
            'vatPublishedInNormalizedRow': False}


def bind(row, tender):
    require(tender.get('id') == row['procedureId'] and tender.get('tenderID') == row['tenderID'], 'Tender identity mismatch')
    require(tender.get('procuringEntity', {}).get('identifier', {}).get('id') == row['buyerId'], 'Buyer mismatch')
    cs = [(i, c) for i, c in enumerate(tender.get('contracts', [])) if c.get('id') == row['contractInternalId']]
    aws = [(i, a) for i, a in enumerate(tender.get('awards', [])) if a.get('id') == row['awardId']]
    require(len(cs) == len(aws) == 1, 'Ambiguous or missing contract/award; no heuristic fallback')
    ci, c = cs[0]
    ai, a = aws[0]
    require(c.get('contractID') == row['contractId'] and c.get('awardID') == a.get('id'), 'Contract linkage mismatch')
    require(a.get('lotID') == row.get('lotId'), 'Lot linkage mismatch')
    lots = tender.get('lots', [])
    require(not row.get('lotId') or sum(l.get('id') == row['lotId'] for l in lots) == 1, 'Ambiguous/missing lot')
    require(row['source'] == API + 'tenders/' + row['procedureId'] and
            row['portalUrl'] == 'https://prozorro.gov.ua/tender/' + row['tenderID'], 'Endpoint mismatch')
    return ci, c, ai, a


def extract(row, obj):
    ci, c, ai, a = bind(row, obj['data'])
    scalars = {}
    def add(path, value):
        require(value is None or type(value) in (str, int, float, bool), 'Non-scalar metadata')
        key = path.rsplit('/', 1)[-1]
        if value is not None and key in ('date', 'dateCreated', 'dateModified', 'dateSigned'):
            require(isinstance(value, str) and len(value) <= 40, 'Invalid date metadata')
            datetime.fromisoformat(value)
        if key == 'status':
            require(value in ('active', 'terminated', 'cancelled', 'pending', 'pending.waiting', 'pending.signing', 'unsuccessful', 'draft'), 'Unknown status metadata')
        if '/changes/' in path and key == 'id':
            require(isinstance(value, str) and re.fullmatch('[0-9a-f]{32}', value), 'Invalid change ID')
        scalars[path] = value
    for path in ('/data/id', '/data/tenderID', '/data/procuringEntity/identifier/id'):
        add(path, pointer(obj, path))
    for key in ('date', 'dateCreated', 'dateModified'):
        if key in obj['data']:
            add('/data/' + key, obj['data'][key])
    for kind, index, record, keys in (
        ('contracts', ci, c, ('id', 'contractID', 'awardID', 'date', 'dateSigned', 'dateModified', 'status')),
        ('awards', ai, a, ('id', 'lotID', 'date', 'dateModified', 'status'))):
        prefix = f'/data/{kind}/{index}'
        for key in keys:
            if key in record:
                add(prefix + '/' + key, record[key])
        value = record.get('value') or {}
        for key in (*FIELDS, 'amountNet'):
            if key in value:
                v = value[key]
                require(v is None or (type(v) in (int, float) if key in ('amount', 'amountNet') else
                                      type(v) is bool if key == 'valueAddedTaxIncluded' else
                                      isinstance(v, str) and re.fullmatch('[A-Z]{3}', v)), 'Invalid financial scalar')
                add(prefix + '/value/' + key, v)
        # No rationale text, documents, names, supplier IDs, or titles.
        for j, change in enumerate(record.get('changes') or []):
            for key in ('id', 'date', 'dateSigned', 'dateModified', 'status'):
                if key in change:
                    add(prefix + f'/changes/{j}/' + key, change[key])
    for j, lot in enumerate(obj['data'].get('lots', [])):
        if lot.get('id') == row.get('lotId'):
            add(f'/data/lots/{j}/id', lot['id'])
    states = {kind: 'absent' if 'value' not in record else 'null' if record['value'] is None else
              'empty-object' if record['value'] == {} else 'object'
              for kind, record in (('contract', c), ('award', a))}
    return {'contractPointer': f'/data/contracts/{ci}', 'awardPointer': f'/data/awards/{ai}',
            'rawValueStates': states, 'scalars': scalars, 'scalarSha256': sha(canonical(scalars))}


def values(ex, kind):
    prefix = ex[kind + 'Pointer'] + '/value/'
    return {k[len(prefix):]: v for k, v in ex['scalars'].items() if k.startswith(prefix)}


def validate_plan(root=ROOT, plan_path=PLAN, private_plan=None):
    plan = json.loads(Path(plan_path).read_text())
    if private_plan is not None:
        require(without_hashes(json.loads(Path(private_plan).expanduser().read_text())) == without_hashes(plan), 'Private freeze mismatch')
    rows = json.loads((Path(root) / 'data/prozorro.json').read_text())
    require(len(rows) == 488 and len({r['id'] for r in rows}) == 488, 'Population identity mismatch')
    by_id = {r['id']: r for r in rows}
    for b in plan['selected'] + plan['amountReviewQueue']:
        row = by_id[b['rowId']]
        require(pointer(rows, b['rowPointer']) == row, 'Stale row')
        for bk, rk in [('buyerId', 'buyerId'), ('tenderID', 'tenderID'), ('tenderInternalId', 'procedureId'),
                       ('contractInternalId', 'contractInternalId'), ('contractId', 'contractId'), ('awardId', 'awardId'), ('lotId', 'lotId')]:
            require(b[bk] == row.get(rk), 'Frozen mapping mismatch')
        require(b['tenderURL'] == row['source'] and b['contractURL'] == API + 'contracts/' + row['contractInternalId'] and
                b['portalURL'] == row['portalUrl'] and b['rawPath'] == 'data/prozorro/raw/records/' + row['tenderID'] + '.json.gz', 'Frozen endpoint/path mismatch')
    queue = plan['amountReviewQueue']
    require(len(queue) == len({b['tenderURL'] for b in queue}) == 11, 'Amount request inventory mismatch')
    require(plan['requestBudget']['amountTenderRecords'] == 11, 'Budget mismatch')
    return plan, rows


def baseline(root=ROOT, plan_path=PLAN, private_plan=None):
    plan, rows = validate_plan(root, plan_path, private_plan)
    amendment_path = 'data/prozorro-contract-changes.json'
    amendments = json.loads((Path(root) / amendment_path).read_text())
    cases = []
    bindings = {b['rowId']: b for b in plan['selected'] + plan['amountReviewQueue']}
    for i, row in enumerate(rows):
        path = 'data/prozorro/raw/records/' + row['tenderID'] + '.json.gz'
        require(path in plan['rawSnapshotHashes'], 'Unplanned raw source')
        raw_blob = (Path(root) / path).read_bytes()
        blob = gzip.decompress(raw_blob)
        ex = extract(row, json.loads(blob))
        if row['id'] in bindings:
            b = bindings[row['id']]
            require(ex['contractPointer'] == b['contractPointer'] and ex['awardPointer'] == b['awardPointer'], 'Frozen pointer mismatch')
        c, a = values(ex, 'contract'), values(ex, 'award')
        norm = normalized(c, a)
        norm['sourceValuePointer'] = ex['contractPointer'] + '/value' if norm['basis'] == 'contract' else ex['awardPointer'] + '/value' if norm['basis'] == 'award-fallback' else None
        require(row.get('amount') == norm['amount'] and row.get('currency') == norm['currency'], 'Normalized value mismatch')
        cases.append({'rowId': row['id'], 'rowPointer': '/' + str(i), 'rowSha256': sha(canonical(row)),
                      'sourceURL': row['source'], 'rawPath': path, 'rawGzipSha256': plan['rawSnapshotHashes'][path],
                      'sourceByteSha256': sha(blob), 'sourceByteSize': len(blob), 'extract': ex, 'normalized': norm,
                      'differenceFields': tuple_diff(c, a), 'explanation': explanation(c, a),
                      'amendmentMetadata': {
                          'sourcePath': amendment_path, 'sourceSha256': plan['inputHashes'][amendment_path],
                          'pointer': '/contracts/' + row['contractInternalId'],
                          'retrievedAt': amendments['retrievedAt'],
                          'published': amendments['contracts'].get(row['contractInternalId']),
                          'limitation': 'Minimized contracting-module summary, not historical financial versions or causal proof.'}})
    amount_ids = sorted(c['rowId'] for c in cases if 'amount' in c['differenceFields'])
    require(amount_ids == sorted(b['rowId'] for b in plan['amountReviewQueue']), 'Queue no longer matches amount differences')
    return {'schemaVersion': 1, 'planSha256': plan['planSha256'], 'inputHashes': plan['inputHashes'],
            'hashLimit': 'Public scalar extracts reproduce analysis, not full response byte hashes. Original gzip snapshots are reverified locally; live full-byte hashes require the private bodies.',
            'cases': cases, 'requests': []}


def analyze(evidence):
    cases = evidence['cases']
    return {'exactMappings': len(cases), 'amountDifferences': sum('amount' in c['differenceFields'] for c in cases),
            'tupleDifferences': sum(bool(c['differenceFields']) for c in cases),
            'otherTupleDifferences': sum(bool(c['differenceFields']) and 'amount' not in c['differenceFields'] for c in cases),
            'explanations': dict(Counter(c['explanation'] for c in cases)),
            'liveAttempts': len(evidence['requests']),
            'liveOutcomes': [{
                'rowId': r['rowId'], 'httpStatus': r['httpStatus'], 'error': r.get('error'),
                'explanation': r.get('explanation'), 'differenceFields': r.get('differenceFields'),
                'financialSnapshotChanged': any(values(r['extract'], kind) != values(next(c['extract'] for c in cases if c['rowId'] == r['rowId']), kind)
                                                for kind in ('contract', 'award')) if 'extract' in r else None
            } for r in evidence['requests']], 'paidCertified': False,
            'scope': 'Known snapshot differences; nonrepresentative, not a new random accuracy benchmark. No tax conversion, currency sums, replacement, scores, weights or corruption labels.'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Fetcher:
    def __init__(self, private_dir, rows, plan):
        p = Path(private_dir).expanduser().absolute()
        require(not p.resolve().is_relative_to(ROOT.resolve()) and not any(x.is_symlink() for x in (p, *p.parents)), 'Cache must be external and not symlinked')
        p.mkdir(mode=0o700)  # exclusive; existing directory is never reused
        os.chmod(p, 0o700)
        self.path, self.count, self.last, self.stopped = p, 0, None, False
        self.allowed = {b['tenderURL']: b['rowId'] for b in plan['amountReviewQueue']}
        self.rows = {r['id']: r for r in rows}
        self.used = set()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def save(self, name, blob):
        fd = os.open(self.path / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(blob)

    def fetch(self, url):
        require(not self.stopped and self.count < 11 and url in self.allowed and url not in self.used, 'Stopped, unplanned, duplicate or over-budget request')
        if self.last is not None:
            time.sleep(max(0, 1 - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        self.count += 1
        self.used.add(url)
        rec = {'method': 'GET', 'url': url, 'rowId': self.allowed[url], 'requestNumber': self.count,
               'retrievedAt': datetime.now(timezone.utc).isoformat(), 'httpStatus': None, 'bytesRead': 0,
               'fullByteSha256': None, 'completeBody': False}
        body = b''
        # A wall-clock alarm also bounds DNS/connect and repeated socket reads.
        def deadline(signum, frame):
            raise TimeoutError('Attempt time cap')
        previous_handler = signal.signal(signal.SIGALRM, deadline)
        previous_timer = signal.setitimer(signal.ITIMER_REAL, 15)
        try:
            req = urllib.request.Request(url, method='GET', headers={'Accept': 'application/json', 'User-Agent': 'contract-signals-amount-audit/1.0'})
            try:
                response = self.opener.open(req, timeout=15)
            except urllib.error.HTTPError as exc:
                response = exc
            with response:
                rec['httpStatus'] = response.code if isinstance(response, urllib.error.HTTPError) else response.status
                chunks = []
                while True:
                    remaining = 15 - (time.monotonic() - self.last)
                    require(remaining > 0, 'Attempt time cap')
                    # Bound every socket read by remaining wall-time, not just initial connection.
                    sock = getattr(getattr(getattr(response, 'fp', None), 'raw', None), '_sock', None)
                    if sock is not None:
                        sock.settimeout(remaining)
                    chunk = response.read(min(65536, LIMIT + 1 - sum(map(len, chunks))))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    body = b''.join(chunks)
                    require(len(body) <= LIMIT, 'Response size cap')
                require(time.monotonic() - self.last <= 15, 'Attempt time cap')
                rec['completeBody'] = True
                rec['fullByteSha256'] = sha(body)
                if rec['httpStatus'] != 200:
                    self.stopped = True
                    rec['error'] = 'HTTP failure; stopped, no retries or redirects'
                else:
                    rec['extract'] = extract(self.rows[rec['rowId']], json.loads(body))
                    c, a = values(rec['extract'], 'contract'), values(rec['extract'], 'award')
                    rec['differenceFields'] = tuple_diff(c, a)
                    rec['explanation'] = explanation(c, a)
        except (ValueError, KeyError, TypeError, OSError, urllib.error.URLError) as exc:
            self.stopped = True
            rec['error'] = type(exc).__name__ + '; stopped'
        finally:
            signal.setitimer(signal.ITIMER_REAL, *previous_timer)
            signal.signal(signal.SIGALRM, previous_handler)
        rec['bytesRead'] = len(body)
        if body:
            self.save(f'{self.count:02d}.body', body)
        self.save(f'{self.count:02d}.ledger.json', canonical(rec) + b'\n')
        return rec


def replay(path=EVIDENCE, root=ROOT):
    expected = baseline(root)
    evidence = json.loads(Path(path).read_text())
    require(without_hashes({k: v for k, v in evidence.items() if k not in ('requests', 'analysis')}) ==
            without_hashes({k: v for k, v in expected.items() if k != 'requests'}), 'Stale or modified public baseline')
    plan, rows = validate_plan(root)
    allowed = {b['tenderURL']: b['rowId'] for b in plan['amountReviewQueue']}
    seen = set()
    stopped = False
    for i, r in enumerate(evidence['requests']):
        require(not stopped and i < 11 and r['url'] in allowed and r['url'] not in seen and
                r['method'] == 'GET' and r['rowId'] == allowed[r['url']] and r['requestNumber'] == i + 1, 'Invalid live ledger')
        seen.add(r['url'])
        require(0 <= r['bytesRead'] <= LIMIT + 1, 'Invalid body size')
        require(type(r['completeBody']) is bool, 'Invalid body completion')
        require(not r['completeBody'] or r['bytesRead'] <= LIMIT, 'Oversized complete body')
        require('extract' not in r or (r['httpStatus'] == 200 and r['completeBody'] and not r.get('error')), 'Extract from failed request')
        stopped = bool(r.get('error')) or r['httpStatus'] != 200
        if 'extract' in r:
            ex = r['extract']
            # Reconstruct only whitelisted source structure and re-run full linkage/minimization.
            obj = {'data': {}}
            for path, value in ex['scalars'].items():
                keys = path.strip('/').split('/')
                target = obj
                for j, key in enumerate(keys[:-1]):
                    if isinstance(target, list):
                        index = int(key)
                        while len(target) <= index:
                            target.append({})
                        target = target[index]
                    else:
                        target = target.setdefault(key, [] if keys[j + 1].isdigit() else {})
                target[keys[-1]] = value
            row = next(rw for rw in rows if rw['id'] == r['rowId'])
            for kind in ('contract', 'award'):
                state = ex['rawValueStates'][kind]
                record = pointer(obj, ex[kind + 'Pointer'])
                if state == 'null':
                    record['value'] = None
                elif state == 'empty-object':
                    record['value'] = {}
                else:
                    require(state in ('object', 'absent'), 'Invalid raw value state')
            require(without_hashes(extract(row, obj)) == without_hashes(ex), 'Invalid or excessive live scalar pointers')
            c, a = values(ex, 'contract'), values(ex, 'award')
            require(r['differenceFields'] == tuple_diff(c, a) and r['explanation'] == explanation(c, a), 'Modified live analysis')
    evidence['analysis'] = analyze(evidence)
    return evidence


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fetch', action='store_true')
    p.add_argument('--private-dir', type=Path)
    p.add_argument('--public-replay', type=Path, default=EVIDENCE)
    p.add_argument('--write', action='store_true', help='explicitly write cached baseline artifact')
    p.add_argument('--live-evidence', action='store_true', help='explicitly write acquisition to public artifact')
    args = p.parse_args()
    if args.fetch:
        if not args.private_dir or args.write:
            p.error('--fetch requires --private-dir; use --live-evidence rather than --write')
        result = baseline(private_plan=PRIVATE_PLAN)
        plan, rows = validate_plan(private_plan=PRIVATE_PLAN)
        f = Fetcher(args.private_dir, rows, plan)
        for b in plan['amountReviewQueue']:
            result['requests'].append(f.fetch(b['tenderURL']))
            if f.stopped:
                break
    else:
        if args.live_evidence or args.private_dir:
            p.error('--live-evidence/--private-dir require --fetch')
        result = baseline() if args.write else replay(args.public_replay)
    result['analysis'] = analyze(result)
    if args.write or args.live_evidence:
        EVIDENCE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result['analysis'], indent=2))


if __name__ == '__main__':
    main()
