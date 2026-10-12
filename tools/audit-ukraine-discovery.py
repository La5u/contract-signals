#!/usr/bin/env python3
"""Bounded public search audit; default replays committed minimized evidence offline."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'data/ukraine-discovery-evidence.json'
SEARCH = 'https://prozorro.gov.ua/api/search/tenders'
BUYER = '20089290'
START, END = '2024-09-01', '2026-09-01'
LIMIT = 2 * 1024 * 1024
PAGINATION = {'total', 'page', 'per_page', 'perPage', 'last_page', 'lastPage', 'limit', 'count'}
TENDER_ID = r'UA-\d{4}-\d{2}-\d{2}-\d+-[a-zA-Z0-9]+'
INTEGRITY_LABEL = 'local minimized evidence integrity; not remote authentication'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode()


def checksum(result):
    return digest(canonical({k: v for k, v in result.items() if k != 'integrity'}))


def without_hashes(value):
    if isinstance(value, dict):
        return {k: without_hashes(v) for k, v in value.items()
                if k not in ('inputHashes', 'rawSnapshotHashes', 'checksum') and not k.lower().endswith('sha256')}
    if isinstance(value, list):
        return [without_hashes(v) for v in value]
    return value


def strict_json(body):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('non-finite JSON value')
    return json.loads(body, object_pairs_hook=pairs, parse_constant=invalid)


@contextmanager
def wall_cap():
    # POSIX main-thread timer covers DNS, connect, headers, streaming and processing.
    if signal.getitimer(signal.ITIMER_REAL)[0]:
        raise ValueError('existing wall alarm; refusing fetch')
    def expired(*args):
        raise TimeoutError('15-second wall cap')
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 15)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def private_directory(value):
    p = Path(value).expanduser()
    if not p.is_absolute() or '..' in p.parts:
        raise ValueError('private directory requires absolute path without parent traversal')
    if p == ROOT or ROOT in p.parents or p in ROOT.parents:
        raise ValueError('private directory must be outside and not an ancestor of repository')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open('/', flags)
    try:
        for part in p.parts[1:-1]:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        os.mkdir(p.name, mode=0o700, dir_fd=fd)
        child = os.open(p.name, flags, dir_fd=fd)
        os.fchmod(child, 0o700)
        return p, child
    finally:
        os.close(fd)


def digest(body):
    return hashlib.sha256(body).hexdigest()


def url(page, window=False):
    q = {'buyer[]': BUYER, 'page': page}
    if window:
        # Portal end filter is not assumed exclusive: use preceding calendar day.
        q.update({'date[tender][start]': START, 'date[tender][end]': '2026-08-31'})
    return SEARCH + '?' + urllib.parse.urlencode(q)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def minimize(body):
    obj = strict_json(body)
    if not isinstance(obj, dict):
        raise ValueError('search body is not an object')
    rows = obj.get('data')
    if not isinstance(rows, list):
        raise ValueError('search data is not a list')
    ids = []
    for row in rows:
        tid = row.get('tenderID') if isinstance(row, dict) else None
        if not isinstance(tid, str) or not re.fullmatch(TENDER_ID, tid):
            raise ValueError('unrecognized published tenderID')
        datetime.strptime(tid[3:13], '%Y-%m-%d')
        ids.append(tid)
    for key in PAGINATION & obj.keys():
        value = obj[key]
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError('invalid scalar pagination')
    # Only scalar pagination metadata; never copy arbitrary response fields.
    pagination = {k: obj[k] for k in ('total', 'page', 'per_page', 'perPage', 'last_page', 'lastPage', 'limit', 'count')
                  if isinstance(obj.get(k), (int, float)) and not isinstance(obj[k], bool)
                  and math.isfinite(obj[k]) and obj[k] >= 0}
    return {'pagination': pagination, 'rowCount': len(rows), 'tenderIDs': ids,
            'duplicateIDsWithinPage': sorted({x for x in ids if ids.count(x) > 1}),
            'inWindowByTenderID': sum(START <= x[3:13] < END for x in ids)}


class Fetcher:
    def __init__(self, private_dir):
        self.path, self.dir_fd = private_directory(private_dir)
        self.count, self.stopped, self.last = 0, False, None
        # Explicitly disable environment proxies; no cookie/auth handlers or credentials.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def close(self):
        if self.dir_fd is not None:
            os.close(self.dir_fd)
            self.dir_fd = None

    def fetch(self, page, window=False):
        if type(page) is not int or page <= 0 or type(window) is not bool or (window and page != 1):
            raise ValueError('invalid page/scope')
        if self.stopped or self.count >= 5:
            raise RuntimeError('request budget exhausted or run stopped')
        if self.last is not None:
            time.sleep(max(0, 1 - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        self.count += 1
        record = {'requestNumber': self.count, 'url': url(page, window), 'method': 'POST',
                  'page': page, 'scope': 'fixed-window' if window else 'all-time',
                  'retrievedAt': datetime.now(timezone.utc).isoformat()}
        request = urllib.request.Request(record['url'], data=b'', method='POST',
                                        headers={'User-Agent': 'contract-signals-discovery-audit/1.0 (public research)', 'Accept': 'application/json'})
        try:
            with wall_cap(), self.opener.open(request, timeout=15) as response:
                record['httpStatus'] = response.status
                if response.status != 200:
                    raise ValueError('non-200 response')
                body = response.read(LIMIT + 1)
                record['bytesRead'] = len(body)
                if len(body) > LIMIT:
                    raise ValueError('response exceeds 2 MiB')
                minimized = minimize(body)
                fd = os.open(f'{self.count:02d}.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=self.dir_fd)
                with os.fdopen(fd, 'wb') as out:
                    out.write(body)
                record['sourceSha256'] = digest(body)
                record.update(minimized)
        except urllib.error.HTTPError as exc:
            record['httpStatus'] = exc.code
            exc.close()
            self.stopped = True  # also stop other HTTP failures; no retries
            record['error'] = 'HTTP failure; stopped without redirect/retry'
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            self.stopped = True
            category = ('URLError' if isinstance(exc, urllib.error.URLError) else
                        'TimeoutError' if isinstance(exc, TimeoutError) else
                        'ValueError' if isinstance(exc, ValueError) else 'OSError')
            record['error'] = category + '; stopped'
        return record


def probe(fetcher):
    records = [fetcher.fetch(1)]
    first = records[0]
    size = first.get('rowCount', 0)
    if fetcher.stopped or not size:
        return records
    beyond = 500 // size + 1
    # Boundary control immediately before precise beyond-500 page.
    pages = [beyond - 1, beyond]
    total = first.get('pagination', {}).get('total')
    reported = first.get('pagination', {}).get('last_page', first.get('pagination', {}).get('lastPage'))
    last = reported if isinstance(reported, int) and reported > 0 else math.ceil(total / size) if isinstance(total, (int, float)) and total > 0 else None
    if last and last not in [1] + pages:
        pages.append(last)
    if last and len(set([1] + pages)) < 4:
        pages.append(last + 1)  # empty-page control, budget permitting
    for page in pages:
        if fetcher.stopped or fetcher.count >= 4:
            break
        if page > 0 and page != 1:
            records.append(fetcher.fetch(page))
    if not fetcher.stopped and fetcher.count < 5:
        records.append(fetcher.fetch(1, True))
    return records


def analyze(records):
    successful = [r for r in records if 'tenderIDs' in r]
    alltime = [r for r in successful if r['scope'] == 'all-time']
    overlaps = []
    for i, left in enumerate(alltime):
        for right in alltime[i + 1:]:
            overlaps.append({'pages': [left['page'], right['page']],
                             'sharedTenderIDs': sorted(set(left['tenderIDs']) & set(right['tenderIDs']))})
    totals = [r['pagination'].get('total') for r in alltime]
    fixed = [r for r in successful if r['scope'] == 'fixed-window']
    return {'successfulPages': len(successful), 'allTimeTotals': totals,
            'fixedWindowTotals': [r['pagination'].get('total') for r in fixed],
            'dateFilterSemanticsCertified': False,
            'totalChangedAcrossProbes': len(set(totals)) > 1,
            'pageOverlaps': overlaps, 'completenessCertified': False,
            'historicalCompletenessCertified': False}


def snapshot():
    manifest_path = ROOT / 'data/prozorro/raw/manifest.json'
    body = manifest_path.read_bytes()
    audit_body = (ROOT / 'data/prozorro-audit.json').read_bytes()
    m = strict_json(body)
    b = next(b for b in m['buyers'] if b['code'] == BUYER)
    audit = strict_json(audit_body)
    buyer = next(b for b in audit['discovery']['buyers'] if b['buyerId'] == BUYER)
    if (buyer['searchTotal'], buyer['listedTenderIDs'], buyer['manifestWindowIDs']) != (
            b['searchTotal'], b['listedTenderIDs'], len(b['tenderIDs'])):
        raise ValueError('manifest/audit buyer binding mismatch')
    return {'manifestSha256': digest(body), 'auditFileSha256': digest(audit_body), 'retrievalStartedAt': m['retrievalStartedAt'],
            'retrievalFinishedAt': m.get('retrievalFinishedAt'), 'buyerID': BUYER,
            'searchUrl': b['searchUrl'], 'searchTotal': b['searchTotal'], 'listedTenderIDs': b['listedTenderIDs'],
            'window': m['window'], 'inWindowTenderIDs': b['tenderIDs'],
            'excludedBuyerAssociations': audit['matching']['listedBuyerMismatch'],
            'stoppingRule': 'Stop when accumulated rows >= first total or page empty; reject total drift, count inequality or duplicate IDs. No page beyond reported total is tested.',
            'missingEvidence': ['original page bodies', 'original page size', 'all-time IDs outside window', 'original last/beyond-total control']}


def validate(result, baseline=True):
    """Fail closed before emitting anything; replay never opens raw/private bodies."""
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    require(isinstance(result, dict) and set(result) == {
        'schemaVersion', 'snapshot', 'requests', 'requestCount', 'bounds', 'analysis', 'integrity'},
        'unexpected evidence fields')
    require(type(result['schemaVersion']) is int and result['schemaVersion'] == 1, 'schema')
    require(without_hashes(result['snapshot']) == without_hashes(snapshot()), 'stale/drifted snapshot')
    expected_bounds = {'maxRequests': 5, 'timeoutSeconds': 15, 'maxResponseBytes': LIMIT,
                       'spacingSeconds': 1, 'redirects': False, 'retries': False}
    if not baseline:
        expected_bounds['wallCapSeconds'] = 15
    require(canonical(result['bounds']) == canonical(expected_bounds), 'bounds drift')
    records = result['requests']
    require(isinstance(records, list) and 1 <= len(records) <= 5, 'request cap')
    require(type(result['requestCount']) is int and result['requestCount'] == len(records), 'request count')
    previous = None
    stopped = False
    base = {'requestNumber', 'url', 'method', 'page', 'scope', 'retrievedAt'}
    success = {'httpStatus', 'bytesRead', 'sourceSha256', 'pagination', 'rowCount',
               'tenderIDs', 'duplicateIDsWithinPage', 'inWindowByTenderID'}
    errors = {'HTTP failure; stopped without redirect/retry', 'URLError; stopped',
              'TimeoutError; stopped', 'ValueError; stopped', 'OSError; stopped'}
    for number, r in enumerate(records, 1):
        require(not stopped and isinstance(r, dict), 'request after failure')
        require(base <= set(r) and set(r) <= base | success | {'error'}, 'unexpected request fields')
        require(type(r['requestNumber']) is int and r['requestNumber'] == number, 'request numbering')
        require(type(r['page']) is int and r['page'] > 0, 'page')
        require(r['scope'] in ('all-time', 'fixed-window'), 'scope')
        require(r['scope'] != 'fixed-window' or r['page'] == 1, 'fixed-window page')
        require(r['method'] == 'POST' and r['url'] == url(r['page'], r['scope'] == 'fixed-window'), 'method/URL')
        require(isinstance(r['retrievedAt'], str), 'timestamp')
        timestamp = datetime.fromisoformat(r['retrievedAt'])
        require(timestamp.utcoffset() is not None and timestamp.utcoffset().total_seconds() == 0, 'UTC timestamp')
        require(previous is None or (timestamp - previous).total_seconds() >= 1, 'chronology/spacing')
        previous = timestamp
        if 'httpStatus' in r:
            require(type(r['httpStatus']) is int and 100 <= r['httpStatus'] <= 599, 'HTTP status')
        if 'bytesRead' in r:
            require(type(r['bytesRead']) is int and 0 <= r['bytesRead'] <= LIMIT + (1 if 'error' in r else 0), 'body bound')
        if 'error' in r:
            require(r['error'] in errors and not (set(r) & (success - {'httpStatus', 'bytesRead'})), 'error record')
            require(r.get('httpStatus') == 200 or 'httpStatus' not in r or
                    r['error'] == 'HTTP failure; stopped without redirect/retry' or
                    r['error'] == 'ValueError; stopped', 'HTTP stop')
            stopped = True
            continue
        require(set(r) == base | success and r['httpStatus'] == 200, 'successful record')
        ids = r['tenderIDs']
        require(isinstance(ids, list) and all(isinstance(x, str) and re.fullmatch(TENDER_ID, x) for x in ids), 'IDs')
        for tid in ids:
            datetime.strptime(tid[3:13], '%Y-%m-%d')
        require(type(r['rowCount']) is int and r['rowCount'] == len(ids), 'row count')
        require(r['duplicateIDsWithinPage'] == sorted({x for x in ids if ids.count(x) > 1}), 'within-page duplicates')
        require(type(r['inWindowByTenderID']) is int and r['inWindowByTenderID'] ==
                sum(START <= x[3:13] < END for x in ids), 'window count')
        pagination = r['pagination']
        require(isinstance(pagination, dict) and set(pagination) <= PAGINATION, 'pagination fields')
        require(all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in pagination.values()), 'scalar pagination')
        require('page' not in pagination or pagination['page'] == r['page'], 'pagination page')
        for key in ('per_page', 'perPage', 'limit'):
            require(key not in pagination or pagination[key] >= len(ids), 'page size')
    require(canonical(result['analysis']) == canonical(analyze(records)), 'analysis drift')
    require(without_hashes(result['integrity']) == {'label': INTEGRITY_LABEL}, 'integrity label')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fetch', action='store_true')
    p.add_argument('--private-dir', help='required new exclusive directory outside repository for raw bodies')
    p.add_argument('--public-replay', type=Path, default=EVIDENCE, help='minimized public JSON; no private cache needed')
    p.add_argument('--write', type=Path)
    args = p.parse_args()
    if args.fetch:
        if not args.private_dir:
            p.error('--fetch requires --private-dir')
        baseline_snapshot = snapshot()  # fail closed before any outward request
        f = Fetcher(args.private_dir)
        try:
            records = probe(f)
        finally:
            f.close()
        result = {'schemaVersion': 1, 'snapshot': baseline_snapshot, 'requests': records,
                  'requestCount': f.count, 'bounds': {'maxRequests': 5, 'timeoutSeconds': 15, 'wallCapSeconds': 15, 'maxResponseBytes': LIMIT, 'spacingSeconds': 1,
                  'redirects': False, 'retries': False}, 'analysis': analyze(records)}
        result['integrity'] = {'label': INTEGRITY_LABEL, 'evidenceSha256': checksum(result)}
        validate(result, baseline=False)
    else:
        result = strict_json(args.public_replay.read_bytes())
        validate(result)
        result['analysis'] = analyze(result['requests'])
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.write:
        args.write.write_text(text)
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
