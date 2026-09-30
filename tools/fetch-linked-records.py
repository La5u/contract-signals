#!/usr/bin/env python3
"""Bounded, opt-in Prozorro contract linking. Defaults to a plan, never a crawl.

--download fetches at most three preselected contract records, serially, 3 seconds
apart. Exact URLs come from embedded contract IDs in the existing cohort, not names.
Cache is local/gitignored; do not publish it without privacy/reuse review.
"""
import argparse
import gzip
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data/.linked-cache'
MAX_BYTES = 5 * 1024 * 1024
INTERVAL = 3
BUDGET = 3


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # never follow a login, signed URL or different host


def plan(rows):
    candidates = sorted(rows, key=lambda r: hashlib.sha256(r['id'].encode()).hexdigest())
    selected, seen = [], set()
    for row in candidates:
        ident = row.get('contractInternalId')
        if not isinstance(ident, str) or not re.fullmatch(r'[a-f0-9]{32}', ident) or ident in seen:
            continue
        seen.add(ident)
        selected.append({'rowId': row['id'], 'tenderId': row['procedureId'], 'contractId': row['contractId'],
                         'internalId': ident, 'url': f'https://public-api.prozorro.gov.ua/api/2.5/contracts/{ident}'})
        if len(selected) == BUDGET:
            break
    return selected


def cooldown_until(headers, now):
    value = headers.get('Retry-After', '')
    try:
        seconds = int(value)
        return now + max(3600, seconds)
    except ValueError:
        try:
            return max(now + 3600, parsedate_to_datetime(value).timestamp())
        except (ValueError, TypeError, OverflowError):
            return now + 3600


def fetch_plan(items, cache=CACHE, opener=None, clock=time.time, sleep=time.sleep):
    """Budget includes errors; 403/429/503 stop the entire batch. No retries.

    Persist a host cooldown across runs; take a nonblocking process lock to avoid
    concurrent batches. Cached successes AND errors consume no further requests.
    """
    import fcntl
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    cache.chmod(0o700)
    with (cache / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        gate = cache / 'host-state.json'
        state = json.loads(gate.read_text()) if gate.exists() else {}
        if state.get('blocked'):
            raise RuntimeError('Host access refused previously; review terms/access before manually clearing local state.')
        if state.get('notBefore', 0) > clock():
            raise RuntimeError('Host cooldown in effect; no requests made.')
        open_url = opener or urllib.request.build_opener(NoRedirect()).open
        reports, requests = [], 0
        for item in items[:BUDGET]:
            url = item['url']
            if not re.fullmatch(r'https://public-api\.prozorro\.gov\.ua/api/2\.5/contracts/[a-f0-9]{32}', url):
                raise ValueError('URL outside the approved public contract endpoint')
            key = hashlib.sha256(url.encode()).hexdigest()
            meta, body = cache / (key + '.json'), cache / (key + '.json.gz')
            if meta.exists():
                reports.append(json.loads(meta.read_text()))
                continue
            delay = state.get('lastRequest', 0) + INTERVAL - clock()
            if delay > 0:
                sleep(delay)
            state['lastRequest'] = clock()
            gate.write_text(json.dumps(state))
            requests += 1
            report = {**item, 'retrievedAt': datetime.now(timezone.utc).isoformat()}
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'contract-signals/0.1 (+https://contracts.lasu.dev; bounded public-record research)', 'Accept': 'application/json'})
                with open_url(req, timeout=15) as response:
                    payload = response.read(MAX_BYTES + 1)
                    if len(payload) > MAX_BYTES:
                        raise ValueError('Response exceeds five-MiB budget')
                    record = json.loads(payload).get('data')
                    if not isinstance(record, dict):
                        raise ValueError('No data record')
                    report.update({'httpStatus': response.status, 'sha256': hashlib.sha256(payload).hexdigest(),
                                   'bytes': len(payload), 'cacheFile': body.name})
                    body.write_bytes(gzip.compress(payload, mtime=0))
            except urllib.error.HTTPError as error:
                report['httpStatus'] = error.code
                if error.code in (401, 403):
                    state['blocked'] = True
                if error.code in (429, 503):
                    state['notBefore'] = cooldown_until(error.headers, clock())
                error.close()
            except (OSError, ValueError) as error:
                report['error'] = type(error).__name__ + ': ' + str(error)[:160]
                state['notBefore'] = clock() + 3600
            meta.write_text(json.dumps(report, indent=2) + '\n')
            gate.write_text(json.dumps(state))
            reports.append(report)
            if state.get('blocked') or state.get('notBefore', 0) > clock():
                break
        return {'requestsMade': requests, 'records': reports}


def summarize(report, cache=CACHE):
    """Only exact tender + public contract + internal ID matches become links.

    Retain aggregate change counts, not supplier contacts, bank details, documents,
    or free-text descriptions. No amount/duration score from unverified history.
    """
    out = []
    for item in report['records']:
        entry = {k: item[k] for k in ('rowId', 'url', 'retrievedAt', 'tenderId', 'contractId', 'internalId')}
        entry['httpStatus'] = item.get('httpStatus')
        entry['status'] = 'unavailable'
        if item.get('cacheFile'):
            payload = gzip.decompress((cache / item['cacheFile']).read_bytes())
            if hashlib.sha256(payload).hexdigest() != item['sha256']:
                raise ValueError('Cache checksum mismatch')
            data = json.loads(payload)['data']
            match = data.get('id') == item['internalId'] and data.get('contractID') == item['contractId'] and data.get('tender_id') == item['tenderId']
            entry.update({'status': 'linked' if match else 'identity-mismatch', 'sourceSha256': item['sha256']})
            if match:
                entry['publishedChangeCount'] = len(data['changes']) if isinstance(data.get('changes'), list) else None
                entry['contractStatus'] = data.get('status')
                entry['changes'] = [{k: change.get(k) for k in ('id', 'status', 'date', 'dateSigned', 'rationaleTypes')}
                                    for change in data['changes']] if isinstance(data.get('changes'), list) else None
        out.append(entry)
    return {'selection': 'First three existing cohort rows ordered by SHA-256(row ID), unique embedded contract IDs; fixed before fetch.',
            'scope': 'Exact contract links and minimized published change metadata; no amendment scoring or personal-data enrichment.', 'records': out}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--offline', action='store_true', help='summarize cached responses only')
    parser.add_argument('--write', type=Path, help='write minimized link report, never raw responses')
    args = parser.parse_args()
    items = plan(json.loads((ROOT / 'data/prozorro.json').read_text()))
    if args.download and args.offline:
        parser.error('choose download or offline')
    if args.download:
        result = summarize(fetch_plan(items))
    elif args.offline:
        reports = []
        for item in items:
            path = CACHE / (hashlib.sha256(item['url'].encode()).hexdigest() + '.json')
            if not path.exists():
                raise SystemExit('Sample cache incomplete; keep the shipped link report. No network requests made.')
            reports.append(json.loads(path.read_text()))
        result = summarize({'records': reports})
    else:
        result = {'plan': items, 'maxRequests': BUDGET, 'minimumIntervalSeconds': INTERVAL}
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.write:
        args.write.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
