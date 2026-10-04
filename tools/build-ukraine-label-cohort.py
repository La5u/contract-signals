#!/usr/bin/env python3
"""Research cohort: Prozorro tenders whose State Audit Service (DASU) outcome is known, plus comparison tenders.

NOT website data: the output feeds research analyses only (research/labels/ukraine-cohort.json.gz).

Label semantics (DASU monitoring status standard, github.com/ProzorroUKR/openprocurement.audit.api,
docs/source/monitoring/standard/monitoring.rst):
    addressed  conclusion published, violations found      completed  finished, violations found
    declined   conclusion published, no violations found   closed     finished, no violations found
    active / stopped / cancelled / draft                   no conclusion -> null
The feed's opt_fields cannot return the conclusion, so the label comes from the status; the full monitoring
is fetched only for tenders labelled true (violation types) and for a small spot-check that the status
mapping agrees with conclusion.violationOccurred.

Tender labels (tri-state; null = unknown, never "clean"):
    audit_violation   true  any monitoring created 2024-09-01..2026-09-01 ended with violations found
                      false no such monitoring and one ended with no violations (conditional on DASU selection)
                      null  monitored without a conclusion, or not monitored (comparison tenders)
    audit_violation_corruption_category   a violationType starting "corruption" (a DASU checklist category,
                      not a finding of corruption); null when the monitoring detail was not fetched.

Sample: seeded and deterministic (SHA-256 ranking), stratified by label; for each sampled monitored tender one
unmonitored comparison tender of the same buyer created within +-90 days (same procurementMethodType when
possible) from the public tender feed. Selection method is recorded per tender for a positive-unlabelled analysis.

Discipline: serial requests, >=1.0 s apart, 429/503 backoff honouring Retry-After, a 403 stops the run (no
bypass), hard cap on requests across resumed runs (counter persisted), raw responses cached gzipped outside git
under ~/.cache/contract-signals/labels/ukraine-cohort/. Default mode prints the plan; --fetch performs requests;
--from-cache builds from the cache only. Natural persons' identifiers are masked (tools/personal_ids.py);
supplier names, titles, free-text findings and contact data are never stored.
"""
import argparse
import base64
import gzip
import hashlib
import importlib.util
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ua = _load('collect_labels_ukraine', 'collect-labels-ukraine.py')
imp = _load('import_prozorro', 'import-prozorro.py')
common = ua.common

SEED = 'ukraine-audit-cohort-20261004'
COHORT_ID = 'ukraine-audit-label-cohort'
WINDOW_START, WINDOW_END = '2024-09-01', '2026-09-01'
PUBLIC_API = imp.API
AUDIT_API = ua.API
CACHE = common.CACHE / 'ukraine-cohort'
LEGACY_CACHE = common.CACHE / 'ukraine'
LEGACY_FEED_OFFSET = 1725840000          # offset of the previous collector run (2024-09-09 UTC)
HEAD_FEED_OFFSET = 1725148800            # 2024-09-01 UTC
SCAN_FIELDS = 'procuringEntity,procurementMethodType,dateCreated,tenderID,status'
SCAN_PAGE = 1000
HARD_CAP = 9000
PRIOR_REQUESTS = 11                      # exploratory probes made before the collector existed
MIN_INTERVAL = 1.0
USER_AGENT = 'contract-signals-label-research/1.0 (public open-data research)'
TRUE_STATUSES = {'addressed', 'completed'}
FALSE_STATUSES = {'declined', 'closed'}
COMPARISON_DAYS = 90
SPOT_CHECK = 30
RESERVE = 60
SCAN_BUDGET = 1800


class BudgetExceeded(RuntimeError):
    pass


class Blocked(RuntimeError):
    pass


class Throttled(RuntimeError):
    pass


class Fetcher:
    """Serial, throttled, gzip-cached GET with a request cap that survives restarts."""

    def __init__(self, cache_dir, budget=HARD_CAP, network=False, min_interval=MIN_INTERVAL, opener=None,
                 sleep=time.sleep, clock=time.monotonic, legacy_dir=None, prior=PRIOR_REQUESTS):
        self.dir = Path(cache_dir)
        self.budget, self.network, self.min_interval = budget, network, min_interval
        self.opener, self.sleep, self.clock = opener or self._urlopen, sleep, clock
        self.legacy_dir = Path(legacy_dir) if legacy_dir else None
        self.last = None
        self.dir.mkdir(parents=True, exist_ok=True) if network else None
        self.state_path = self.dir / 'state.json'
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {'requests': prior, 'throttled': 0}
        self.start = self.state['requests']
        self.responses = {}

    @property
    def requests(self):
        return self.state['requests']

    @staticmethod
    def _urlopen(url):
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, b'', dict(e.headers or {})

    def _key(self, url):
        return hashlib.sha256(url.encode()).hexdigest()[:32]

    def _save_state(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.state))
        tmp.replace(self.state_path)

    def cached(self, url):
        k = self._key(url)
        return (self.dir / (k + '.meta.json')).exists() or bool(self.legacy_dir and (self.legacy_dir / (k + '.json')).exists())

    def _read(self, url):
        k = self._key(url)
        meta_path = self.dir / (k + '.meta.json')
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            body = gzip.decompress((self.dir / (k + '.gz')).read_bytes()) if meta['status'] == 200 else None
            return {**meta, 'body': body, 'cached': True}
        if self.legacy_dir and (self.legacy_dir / (k + '.json')).exists():
            meta = json.loads((self.legacy_dir / (k + '.json')).read_text())
            return {'url': url, 'status': meta.get('status', 200), 'sha256': meta['sha256'], 'retrieved_at': meta['retrieved_at'],
                    'body': bytes.fromhex(meta['body_hex']), 'cached': True, 'legacy': True}
        return None

    def fetch(self, url):
        """Response dict, or None when the URL is not cached and the network is disabled."""
        hit = self._read(url)
        if hit is not None:
            self.responses[url] = hit
            return hit
        if not self.network:
            return None
        for attempt in range(6):
            if self.state['requests'] >= self.budget:
                raise BudgetExceeded(f'request cap {self.budget} reached; rerun to resume from cache')
            if self.last is not None:
                wait = self.min_interval - (self.clock() - self.last)
                if wait > 0:
                    self.sleep(wait)
            self.state['requests'] += 1
            self.last = self.clock()
            self._save_state()
            try:
                status, body, headers = self.opener(url)
            except (TimeoutError, urllib.error.URLError, ConnectionError):
                if attempt < 3:
                    self.sleep(5 * 2 ** attempt)
                    continue
                raise Throttled(f'network failure for {url}')
            if status in (429, 503):
                self.state['throttled'] += 1
                retry = {k.lower(): v for k, v in (headers or {}).items()}.get('retry-after')
                self.sleep(min(float(retry) if retry and retry.strip().isdigit() else 5 * 2 ** attempt, 600))
                continue
            if status in (401, 403):
                raise Blocked(f'HTTP {status} for {url}: stopping, no bypass')
            if status in (404, 410):
                body = None
            elif status != 200:
                raise RuntimeError(f'HTTP {status} for {url}')
            break
        else:
            raise Throttled(f'still throttled after retries: {url}')
        meta = {'url': url, 'status': status, 'sha256': hashlib.sha256(body or b'').hexdigest(),
                'retrieved_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
        k = self._key(url)
        self.dir.mkdir(parents=True, exist_ok=True)
        if body is not None:
            (self.dir / (k + '.gz')).write_bytes(gzip.compress(body, mtime=0))
        (self.dir / (k + '.meta.json')).write_text(json.dumps(meta))
        resp = {**meta, 'body': body, 'cached': False}
        self.responses[url] = resp
        return resp


# ---------------------------------------------------------------- URLs and small helpers

def tender_url(tender_id):
    return f'{PUBLIC_API}/tenders/{tender_id}'


def scan_url(offset):
    return f'{PUBLIC_API}/tenders?' + urllib.parse.urlencode({'limit': SCAN_PAGE, 'opt_fields': SCAN_FIELDS, 'offset': offset})


def rank(*parts):
    """Deterministic pseudo-random order key (SHA-256 of the seed and the parts)."""
    return hashlib.sha256('|'.join((SEED,) + tuple(str(p) for p in parts)).encode()).hexdigest()


def day(value):
    try:
        return date.fromisoformat((value or '')[:10])
    except ValueError:
        return None


def in_window(created):
    return bool(created) and WINDOW_START <= created[:10] < WINDOW_END


def label_from_statuses(statuses):
    """audit_violation from the statuses of one tender's monitorings (feed semantics, see module doc)."""
    s = set(statuses)
    if s & TRUE_STATUSES:
        return True
    if s & FALSE_STATUSES:
        return False
    return None


def corruption_label(violation, violation_types):
    """violation_types: list when the detail was fetched, else None (unknown)."""
    if violation is False:
        return False
    if violation is True and violation_types is not None:
        return any(t.startswith('corruption') for t in violation_types)
    return None


# ---------------------------------------------------------------- phase 1: monitoring feed

def read_feed(f):
    """All feed entries from 2024-09-01 (by dateModified), the previous run's cache reused, then a fresh tail."""
    entries, pages = {}, []

    def take(page):
        body = json.loads(page['body'])
        pages.append({k: page[k] for k in ('url', 'sha256', 'retrieved_at')})
        for e in body['data']:
            entries[e['id']] = {k: e.get(k) for k in ('id', 'tender_id', 'status', 'dateCreated', 'dateModified')}
        return body

    offset = HEAD_FEED_OFFSET
    while offset < LEGACY_FEED_OFFSET:
        page = f.fetch(ua.feed_url(offset))
        if page is None or page['status'] != 200:
            break
        body = take(page)
        if not body['data']:
            break
        offset = body['next_page']['offset']
    offset = LEGACY_FEED_OFFSET
    while True:
        page = f.fetch(ua.feed_url(offset))
        if page is None or page['status'] != 200:
            break
        body = take(page)
        if not body['data']:
            break
        offset = body['next_page']['offset']
        if len(body['data']) < ua.PAGE and not page['cached']:
            break
    return entries, pages


def monitored_pool(entries):
    """tender_id -> {'monitorings': [...in-window monitorings], 'label'}; plus every monitored tender id."""
    by_tender = defaultdict(list)
    for e in entries.values():
        by_tender[e['tender_id']].append(e)
    pool = {}
    for tid, ms in by_tender.items():
        inside = [m for m in ms if in_window(m['dateCreated'])]
        if inside:
            inside.sort(key=lambda m: (m['dateCreated'], m['id']))
            pool[tid] = {'monitorings': inside, 'label': label_from_statuses(m['status'] for m in inside)}
    return pool, set(by_tender)


def sample_monitored(pool, n_concluded, n_null, seed_ranker=rank):
    """Seeded, stratified (true/false) sample of concluded tenders + a few unconcluded ones."""
    strata = {k: sorted((t for t, v in pool.items() if v['label'] is k), key=lambda t: seed_ranker('monitored', t))
              for k in (True, False, None)}
    half = n_concluded // 2
    want_true, want_false = min(len(strata[True]), half), min(len(strata[False]), half)
    spare = n_concluded - want_true - want_false
    want_true += min(spare, len(strata[True]) - want_true)
    want_false += min(n_concluded - want_true - want_false, len(strata[False]) - want_false)
    picks = {True: strata[True][:want_true], False: strata[False][:want_false], None: strata[None][:n_null]}
    weights = {str(k).lower().replace('none', 'null'): (len(strata[k]) / len(picks[k]) if picks[k] else None) for k in strata}
    sizes = {str(k).lower().replace('none', 'null'): {'pool': len(strata[k]), 'sampled': len(picks[k])} for k in strata}
    return picks, sizes, weights


# ---------------------------------------------------------------- rows from tender records

def minimize_row(row, tender, contract):
    period = tender.get('tenderPeriod') or {}
    start, end = day(period.get('startDate')), day(period.get('endDate'))
    cperiod = contract.get('period') or {}
    cstart, cend = day(cperiod.get('startDate')), day(cperiod.get('endDate'))
    award = next((a for a in tender.get('awards') or [] if a.get('id') == row['awardId']), {})
    keep = ['id', 'dataFamily', 'country', 'dataStatus', 'date', 'buyerId', 'supplierIds', 'amount', 'currency', 'procedure',
            'procedureDirect', 'category', 'cpv', 'offers', 'disqualifiedBefore', 'lotId', 'lotCount', 'contractId', 'awardId',
            'procedureId', 'tenderID', 'tenderCreated', 'complaintCount', 'source', 'portalUrl']
    out = {k: row.get(k) for k in keep}
    out['cohortId'] = COHORT_ID
    out.update({
        'reporting': tender.get('procurementMethodType') == 'reporting',
        'tenderPeriodStart': start.isoformat() if start else None,
        'tenderPeriodEnd': end.isoformat() if end else None,
        'tenderPeriodDays': (end - start).days if start and end and end >= start else None,
        'awardDate': (award.get('date') or '')[:10] or None,
        'durationMonths': round((cend - cstart).days / 30.4375, 2) if cstart and cend and cend >= cstart else None,
        'tenderStatus': tender.get('status'),
    })
    return out


def tender_rows(tender):
    """Rows built with the importer's own functions (offers per lot, procedureDirect, masking), minimized."""
    rows, excluded = imp.contract_rows(tender)
    contracts = {c['id']: c for c in tender.get('contracts') or []}
    out = [minimize_row(r, tender, contracts.get(r['contractInternalId'], {})) for r in rows]
    return out, excluded


def tender_meta(tender):
    buyer = (tender.get('procuringEntity') or {}).get('identifier') or {}
    return {'tenderID': tender.get('tenderID'), 'procedureId': tender.get('id'), 'created': (tender.get('dateCreated') or '')[:10] or None,
            'procedure': tender.get('procurementMethodType'), 'buyerId': buyer.get('id'), 'tenderStatus': tender.get('status')}


# ---------------------------------------------------------------- phases 2-5

def load_tender(f, tender_id):
    """(tender dict or None, response meta or None)."""
    r = f.fetch(tender_url(tender_id))
    if r is None or r['status'] != 200 or r['body'] is None:
        return None, r
    data = json.loads(r['body']).get('data')
    if not data or data.get('id') != tender_id:
        return None, r
    return data, r


def scan_candidates(f, buyers, monitored_ids, max_requests):
    """Page the public tender feed (dateModified order) from 2024-09-01; keep unmonitored 'complete' tenders created in
    the window for the given buyers. A tender created >= 2024-09-01 has dateModified >= that date, so the scan sees it,
    and any monitoring of it would be in the monitoring feed read from the same date."""
    cands, pages, n, finished = defaultdict(list), [], 0, False
    offset = '2024-09-01T00:00:00'
    while n < max_requests:
        page = f.fetch(scan_url(offset))
        if page is None or page['status'] != 200:
            break
        n += 0 if page['cached'] else 1
        body = json.loads(page['body'])
        pages.append({k: page[k] for k in ('url', 'sha256', 'retrieved_at')})
        for t in body['data']:
            b = ((t.get('procuringEntity') or {}).get('identifier') or {}).get('id')
            if b in buyers and in_window(t.get('dateCreated')) and t['id'] not in monitored_ids and t.get('status', 'complete') == 'complete':
                cands[b].append({'id': t['id'], 'tenderID': t.get('tenderID'), 'created': t['dateCreated'][:10],
                                 'procedure': t.get('procurementMethodType')})
        if len(body['data']) < SCAN_PAGE:
            finished = True
            break
        offset = body['next_page']['offset']
    return cands, pages, finished


def candidate_order(meta, cands, used):
    """Same buyer, created within +-90 days, unmonitored: same procurement method first, then others; seeded order."""
    c0 = day(meta['created'])
    options = []
    for c in cands.get(meta['buyerId'], []):
        if c['id'] in used or c['id'] == meta['procedureId'] or not c0:
            continue
        if abs((day(c['created']) - c0).days) <= COMPARISON_DAYS:
            same = c['procedure'] == meta['procedure']
            options.append((0 if same else 1, rank('comparison', meta['procedureId'], c['id']), c, same))
    options.sort(key=lambda o: o[:2])
    return [(c, 'same_buyer_same_method_90d' if same else 'same_buyer_other_method_90d') for _, _, c, same in options]


def run(args):
    plan = not (args.fetch or args.from_cache)
    f = Fetcher(Path(args.cache), budget=args.budget, network=args.fetch, legacy_dir=LEGACY_CACHE)
    started = f.requests
    notes = []
    entries, feed_pages = read_feed(f)
    pool, monitored_ids = monitored_pool(entries)
    picks, sizes, weights = sample_monitored(pool, args.n, args.null_extra)
    if plan:
        print(f'PLAN (offline, no requests made); cap {args.budget}, requests already spent {f.requests}')
        print(f'  monitoring feed entries available from cache: {len(entries)}; pool of tenders with an in-window monitoring: {len(pool)}')
        print(f'  strata: {json.dumps(sizes)}')
        todo = sum(1 for t in sum(picks.values(), []) if not f.cached(tender_url(t)))
        print(f'  monitored tender fetches pending: {todo}; monitoring details for violation=true tenders: <= {len(picks[True])} + spot-check {SPOT_CHECK}')
        print(f'  public tender feed scan: up to {SCAN_BUDGET} pages; comparison tender fetches: ~{sum(len(v) for v in picks.values())}')
        print('  rerun with --fetch to execute (background run recommended; multi-hour)')
        return 0

    # requests still owed to the monitoring-detail phase (uncached details of the sampled true tenders) are kept in reserve
    owed = sum(1 for t in picks[True] if not f.cached(ua.monitoring_url(next(m for m in pool[t]['monitorings'] if m['status'] in TRUE_STATUSES)['id'])))

    stopped = None
    tenders = {}
    order = [(k, t) for k in (True, False, None) for t in picks[k]]
    try:
        # ---- monitored tenders
        for k, tid in order:
            if f.network and f.requests >= f.budget - RESERVE - owed:
                raise BudgetExceeded('reserve for details reached')
            data, resp = load_tender(f, tid)
            tenders[tid] = {'data': data, 'resp': resp}
        # ---- scan and comparisons
        buyers = {tender_meta(v['data'])['buyerId'] for v in tenders.values() if v['data']} - {None}
        cands, scan_pages, scan_done = scan_candidates(f, buyers, monitored_ids, args.scan_budget)
        if not scan_done:
            notes.append('public tender feed scan incomplete (budget); comparisons cover only the scanned period')
    except (BudgetExceeded, Throttled) as e:
        stopped = str(e)
        notes.append('stopped early: ' + stopped)
        cands, scan_pages, scan_done = defaultdict(list), [], False
    except Blocked as e:
        print('BLOCKED:', e, file=sys.stderr)
        return 3

    records, comparisons_missing = [], Counter()
    used = set()
    try:
        for k, tid in order:
            v = tenders.get(tid)
            if not v or not v['data']:
                records.append({'role': 'monitored', 'procedureId': tid, 'unavailable': 'not_fetched' if not v else 'missing_or_mismatched_record',
                                'rows': [], 'excluded': {}})
                continue
            meta = tender_meta(v['data'])
            rows, excluded = tender_rows(v['data'])
            records.append({'role': 'monitored', 'meta': meta, 'rows': rows, 'excluded': excluded,
                            'monitorings': pool[tid]['monitorings'], 'stratum_label': pool[tid]['label'],
                            'response': {x: v['resp'][x] for x in ('sha256', 'retrieved_at')}})
        # comparisons, in deterministic order of the monitored tender id
        if not stopped:
            for rec in sorted((r for r in records if r['role'] == 'monitored' and r.get('meta')), key=lambda r: r['meta']['procedureId']):
                if rec['stratum_label'] is None:
                    continue    # unconcluded monitored tenders are not matched
                options = candidate_order(rec['meta'], cands, used)
                done = False
                for c, how in options[:3]:
                    if f.network and f.requests >= f.budget - RESERVE - owed:
                        raise BudgetExceeded('reserve for details reached')
                    data, resp = load_tender(f, c['id'])
                    used.add(c['id'])
                    if not data:
                        continue
                    rows, excluded = tender_rows(data)
                    if not rows:
                        continue
                    records.append({'role': 'comparison', 'meta': tender_meta(data), 'rows': rows, 'excluded': excluded,
                                    'matched_to': rec['meta']['tenderID'], 'selection': how,
                                    'candidates_available': len(options),
                                    'response': {x: resp[x] for x in ('sha256', 'retrieved_at')}})
                    done = True
                    break
                if not done:
                    comparisons_missing['no_candidate' if not options else 'no_candidate_with_signed_contract'] += 1
    except (BudgetExceeded, Throttled) as e:
        stopped = stopped or str(e)
        notes.append('comparisons stopped early: ' + str(e))
    except Blocked as e:
        print('BLOCKED:', e, file=sys.stderr)
        return 3

    # ---- monitoring details: violation types for true tenders + status-mapping spot check
    details, mismatches = {}, []
    try:
        true_recs = [r for r in records if r['role'] == 'monitored' and r.get('meta') and r['stratum_label'] is True]
        false_recs = [r for r in records if r['role'] == 'monitored' and r.get('meta') and r['stratum_label'] is False]
        targets = [(r, next(m for m in r['monitorings'] if m['status'] in TRUE_STATUSES)) for r in true_recs]
        targets += [(r, next(m for m in r['monitorings'] if m['status'] in FALSE_STATUSES))
                    for r in sorted(false_recs, key=lambda r: rank('spot', r['meta']['procedureId']))[:SPOT_CHECK]]
        for r, m in targets:
            resp = f.fetch(ua.monitoring_url(m['id']))
            if resp is None or resp['status'] != 200:
                continue
            s = ua.summarise_monitoring(json.loads(resp['body'])['data'])
            details[m['id']] = {'status': s['status'], 'concluded': s['concluded'], 'violation_occurred': s['violation_occurred'],
                                'violation_types': s['violation_types'], 'conclusion_published': s['conclusion_published'],
                                'reasons': s['reasons'], 'procuring_stages': s['procuring_stages'],
                                'monitoring_start': s['monitoring_start'], 'monitoring_end': s['monitoring_end'],
                                'has_elimination_report': s['has_elimination_report'],
                                'sha256': resp['sha256'], 'retrieved_at': resp['retrieved_at']}
            expected = m['status'] in TRUE_STATUSES
            if s['concluded'] and s['violation_occurred'] is not expected:
                mismatches.append(m['id'])
    except (BudgetExceeded, Throttled) as e:
        stopped = stopped or str(e)
        notes.append('monitoring details stopped early: ' + str(e))
    except Blocked as e:
        print('BLOCKED:', e, file=sys.stderr)
        return 3

    out = assemble(records, details, mismatches, sizes, weights, f, feed_pages, scan_pages, scan_done, started, notes, stopped,
                   comparisons_missing, entries, pool)
    write_outputs(out, args)
    return 0


def assemble(records, details, mismatches, sizes, weights, f, feed_pages, scan_pages, scan_done, started, notes, stopped,
             comparisons_missing, entries, pool):
    tenders, rows, hashes = [], [], []
    for rec in records:
        if rec.get('unavailable'):
            tenders.append({'role': rec['role'], 'procedureId': rec['procedureId'], 'unavailable': True})
            continue
        meta = rec['meta']
        if rec['role'] == 'monitored':
            ms = []
            types, fetched = [], False
            for m in rec['monitorings']:
                d = details.get(m['id'])
                fetched = fetched or bool(d)
                ms.append({'monitoring_id': m['id'], 'status': m['status'], 'created': m['dateCreated'], 'modified': m['dateModified'],
                           **({'detail': d} if d else {})})
                if d and d['concluded'] and d['violation_occurred']:
                    types += d['violation_types']
            violation = rec['stratum_label']
            concluded = [d for m in rec['monitorings'] if (d := details.get(m['id'])) and d['concluded']]
            if concluded and any(d['violation_occurred'] for d in concluded):
                violation = True
            types = sorted(set(types))
            has_types = violation is True and any(details.get(m['id']) for m in rec['monitorings'] if m['status'] in TRUE_STATUSES)
            labels = {'audit_violation': violation,
                      'audit_violation_corruption_category': corruption_label(violation, types if has_types else None)}
            t = {**meta, 'role': 'monitored', 'labels': labels, 'violation_types': types if has_types else None, 'monitorings': ms,
                 'selection': {'method': 'seeded stratified sample of tenders with a DASU monitoring created in window',
                               'stratum': str(rec['stratum_label']).lower().replace('none', 'null'),
                               'sampling_weight': weights[str(rec['stratum_label']).lower().replace('none', 'null')]}}
        else:
            labels = {'audit_violation': None, 'audit_violation_corruption_category': None}
            t = {**meta, 'role': 'comparison', 'labels': labels, 'matched_to': rec['matched_to'],
                 'selection': {'method': rec['selection'], 'candidates_available': rec['candidates_available'],
                               'monitored': 'not in the DASU monitoring feed read from 2024-09-01 (absence is not proof of no monitoring)'}}
        t['row_count'] = len(rec['rows'])
        t['excluded_contracts'] = rec['excluded']
        tenders.append(t)
        hashes.append({'kind': rec['role'], 'tenderID': meta['tenderID'], **rec['response']})
        for r in rec['rows']:
            rows.append({**r, 'role': rec['role'], 'labels': labels, 'matchedTo': t.get('matched_to'), 'violationTypes': t.get('violation_types')})
    mon = [t for t in tenders if t.get('role') == 'monitored' and not t.get('unavailable')]
    comp = [t for t in tenders if t.get('role') == 'comparison']
    count = lambda ts: dict(Counter(str(t['labels']['audit_violation']).lower().replace('none', 'null') for t in ts))
    type_counts = Counter(x for t in mon for x in (t.get('violation_types') or []))
    summary = {
        'requests_total_including_prior': f.requests, 'requests_this_run': f.requests - started, 'request_cap': f.budget,
        'monitoring_feed': {'entries_read': len(entries), 'pool_tenders_with_in_window_monitoring': len(pool), 'strata': sizes},
        'monitored_tenders_sampled': len(mon) + sum(1 for t in tenders if t.get('unavailable')),
        'monitored_unavailable': sum(1 for t in tenders if t.get('unavailable')),
        'monitored_by_label': count(mon),
        'monitored_with_rows_by_label': dict(Counter(str(t['labels']['audit_violation']).lower().replace('none', 'null') for t in mon if t['row_count'])),
        'comparison_tenders': len(comp), 'comparison_selection': dict(Counter(t['selection']['method'] for t in comp)),
        'comparisons_missing': dict(comparisons_missing),
        'rows': len(rows), 'rows_by_role': dict(Counter(r['role'] for r in rows)),
        'rows_by_procedure_role': {k: dict(v) for k, v in _nested(rows).items()},
        'buyers_monitored': len({t['buyerId'] for t in mon}), 'buyers_comparison': len({t['buyerId'] for t in comp}),
        'buyers_total': len({t['buyerId'] for t in mon + comp}),
        'violation_types_in_true_tenders': dict(type_counts.most_common()),
        'violation_type_detail_fetched_tenders': sum(1 for t in mon if t.get('violation_types') is not None),
        'corruption_category_tenders': sum(1 for t in mon if t['labels']['audit_violation_corruption_category'] is True),
        'status_mapping_spot_check': {'details_fetched': len(details), 'concluded': sum(1 for d in details.values() if d['concluded']),
                                      'mismatches': len(mismatches)},
        'scan_complete': scan_done, 'stopped_early': stopped, 'notes': notes,
    }
    out = {
        'schema': 'ukraine-label-cohort/1', 'cohort_id': COHORT_ID,
        'built_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'purpose': 'Research only (label-first cohort); not website data. No claim of corruption.',
        'provenance': {
            'audit_feed': f'{AUDIT_API}/monitorings (opt_fields {ua.FEED_FIELDS}; offsets from 2024-09-01 by dateModified)',
            'public_api': f'{PUBLIC_API}/tenders/{{id}} (official records), tender feed {PUBLIC_API}/tenders?opt_fields={SCAN_FIELDS}',
            'status_semantics': 'github.com/ProzorroUKR/openprocurement.audit.api docs/source/monitoring/standard/monitoring.rst',
            'licence': 'Prozorro open-data reuse terms (https://prozorro.gov.ua/openprocurement): source attribution; no named licence for API records',
            'window': {'monitoring_created': [WINDOW_START, WINDOW_END]}, 'seed': SEED,
            'minimization': 'No supplier/buyer names, titles, free text, contact data; natural persons identifiers masked (tools/personal_ids.py); raw responses stay in the local cache outside git.',
            'feed_pages': feed_pages, 'scan_pages': {'count': len(scan_pages), 'first': scan_pages[:1], 'last': scan_pages[-1:],
                                                     'sha256_of_hashes': hashlib.sha256(''.join(p['sha256'] for p in scan_pages).encode()).hexdigest()},
            'responses': hashes,
        },
        'selection_diagnostics': {'strata': sizes, 'weights': weights, 'comparison': dict(Counter(t['selection']['method'] for t in comp)),
                                  'comparisons_missing': dict(comparisons_missing),
                                  'caveat': 'DASU selects tenders with its own risk indicators, which overlap the explorer indicators; a reviewed negative is conditional on selection; unmonitored comparison tenders are unlabelled (null), not clean; restricted monitorings may be absent from the public feed.'},
        'summary': summary, 'tenders': tenders, 'rows': rows,
    }
    return out


def _nested(rows):
    d = defaultdict(Counter)
    for r in rows:
        d[r['role']][r['procedure']] += 1
    return d


def write_outputs(out, args):
    data = (json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(data, mtime=0))
    summary = {**out['summary'], 'built_at': out['built_at'], 'cohort_file': path.name,
               'cohort_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'selection_caveat': out['selection_diagnostics']['caveat']}
    Path(args.summary).write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n')
    print(f'wrote {path} ({len(out["rows"])} rows, {len(out["tenders"])} tenders); requests total {out["summary"]["requests_total_including_prior"]}')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--output', default=str(ROOT / 'research/labels/ukraine-cohort.json.gz'))
    p.add_argument('--summary', default=str(ROOT / 'research/labels/ukraine-cohort-summary.json'))
    p.add_argument('--cache', default=str(CACHE))
    p.add_argument('--budget', type=int, default=HARD_CAP, help='hard cap on requests across resumed runs')
    p.add_argument('--scan-budget', type=int, default=SCAN_BUDGET, help='max new tender-feed pages')
    p.add_argument('--n', type=int, default=2500, help='concluded monitored tenders to sample')
    p.add_argument('--null-extra', type=int, default=100, help='monitored but unconcluded tenders to add')
    p.add_argument('--fetch', action='store_true', help='perform network requests (default: offline plan)')
    p.add_argument('--from-cache', action='store_true', help='build from cached responses only')
    return run(p.parse_args(argv))


if __name__ == '__main__':
    sys.exit(main())
