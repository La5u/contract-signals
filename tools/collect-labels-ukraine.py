#!/usr/bin/env python3
"""Collect contract-linked OUTCOME labels for the Ukraine (Prozorro) cohort from DASU monitoring.

Source: State Audit Service (DASU) monitorings, published through the OpenProcurement audit API
(https://audit-api.prozorro.gov.ua/api/2.5/monitorings). A monitoring object references the tender by
its internal id (cohort field procedureId); that identifier is the only join key.

Label targets (tri-state, null = unknown):
  audit_violation   true  -> a monitoring of the tender concluded violationOccurred=true
                    false -> monitored AND a conclusion says violationOccurred=false (reviewed negative,
                             conditional on DASU having selected the tender for monitoring)
                    null  -> not monitored, or monitored without a concluded result
  audit_violation_corruption_category
                    true  -> a concluded violation carries a violationType in DASU's "corruption*" taxonomy
                             (a procedural category of the audit checklist, not a finding of corruption)
                    false -> concluded monitoring without such a category; null otherwise

Method: the feed (ascending by dateModified, limit 1000, opt_fields=tender_id,status,dateCreated) is read
from the cohort's first tender-creation date to the present; entries whose tender_id belongs to the cohort
are fetched in full. Default mode prints the plan only; --fetch performs requests (serial, throttled,
cached outside git, hard budget); --from-cache rebuilds the output from the cache.

Stored output keeps only structured fields: no free-text findings, party names or documents.
"""
import argparse
import importlib.util
import json
import sys
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('collect_labels_colombia', ROOT / 'tools/collect-labels-colombia.py')
common = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(common)

API = 'https://audit-api.prozorro.gov.ua/api/2.5'
FEED_FIELDS = 'tender_id,status,dateCreated'
PAGE = 1000
DEFAULT_BUDGET = 600
CONCLUDED_STATUSES = {'addressed', 'completed', 'closed'}


def feed_url(offset):
    q = {'limit': PAGE, 'opt_fields': FEED_FIELDS, 'offset': offset}
    return f'{API}/monitorings?' + urllib.parse.urlencode(q)


def monitoring_url(mid):
    return f'{API}/monitorings/{mid}'


def tender_endpoint_url(tender_id):
    return f'{API}/tenders/{tender_id}/monitorings'


def start_offset(rows):
    first = min(r['tenderCreated'] for r in rows)
    return int(datetime.fromisoformat(first).replace(tzinfo=timezone.utc).timestamp())


def summarise_monitoring(m):
    """Structured, minimal view of a full monitoring object (no free text, parties or documents)."""
    c = m.get('conclusion') or {}
    period = m.get('monitoringPeriod') or {}
    return {'monitoring_id': m.get('monitoring_id'), 'id': m.get('id'), 'status': m.get('status'),
            'reasons': m.get('reasons'), 'procuring_stages': m.get('procuringStages'),
            'created': m.get('dateCreated'), 'monitoring_start': period.get('startDate'),
            'monitoring_end': period.get('endDate'), 'modified': m.get('dateModified'),
            'concluded': bool(c) and 'violationOccurred' in c,
            'conclusion_published': c.get('datePublished'),
            'violation_occurred': c.get('violationOccurred') if c else None,
            'violation_types': c.get('violationType') or [],
            'has_elimination_report': bool(m.get('eliminationReport')),
            'has_appeal': bool(m.get('appeal')), 'has_cancellation': bool(m.get('cancellation')),
            'liabilities_present': bool(m.get('liabilities')), 'restricted': m.get('restricted')}


def label_tender(monitorings):
    """Tri-state labels from the monitorings of one tender."""
    concluded = [m for m in monitorings if m['concluded']]
    if any(m['violation_occurred'] is True for m in concluded):
        violation = True
    elif any(m['violation_occurred'] is False for m in concluded):
        violation = False
    else:
        violation = None
    if violation is None:
        corruption = None
    else:
        corruption = any(t.startswith('corruption') for m in concluded if m['violation_occurred']
                         for t in m['violation_types'])
    return {'audit_violation': violation, 'audit_violation_corruption_category': corruption}


def build_rows(contracts, monitorings_by_tender):
    rows = []
    for c in contracts:
        ms = monitorings_by_tender.get(c['procedureId'], [])
        rows.append({'dataset': 'prozorro', 'id': c['id'], 'tenderID': c['tenderID'], 'procedureId': c['procedureId'],
                     'tenderCreated': c['tenderCreated'], 'monitored': bool(ms),
                     'labels': label_tender(ms), 'monitorings': ms,
                     'dates': sorted({d[:10] for m in ms for d in (m['monitoring_start'], m['conclusion_published'])
                                      if d})})
    return rows


def run(args):
    contracts = json.loads(Path(args.contracts).read_text())
    cohort = {c['procedureId'] for c in contracts}
    offset0 = start_offset(contracts)
    fetcher = common.Fetcher(args.cache, budget=args.budget, network=args.fetch)
    if not args.fetch and not args.from_cache:
        print(f'PLAN (offline, no requests made): {len(contracts)} contracts, {len(cohort)} distinct tenders')
        off, cached = offset0, 0
        while fetcher.cached(feed_url(off)):
            page = json.loads(fetcher.get(feed_url(off))['body'])
            cached += 1
            if not page['data']:
                break
            off = page['next_page']['offset']
        print(f'  feed from offset {offset0} ({datetime.fromtimestamp(offset0, timezone.utc):%Y-%m-%d}): {cached} page(s) cached,'
              f' next: {feed_url(off)}')
        print(f'  then one request per cohort monitoring hit; max {args.budget} requests, spacing >= {common.MIN_INTERVAL}s')
        print('  rerun with --fetch to execute')
        return 0
    pages, hits, feed_total, statuses = [], {}, 0, Counter()
    offset = offset0
    while True:
        page = fetcher.get(feed_url(offset))
        body = json.loads(page['body'])
        pages.append({k: v for k, v in page.items() if k != 'body'})
        if not body['data']:
            break
        feed_total += len(body['data'])
        for e in body['data']:
            if e['tender_id'] in cohort:
                hits[e['id']] = e
        offset = body['next_page']['offset']
        if len(body['data']) < PAGE:
            # last (partial) page; one more call would return nothing new
            break
    by_tender, details = {}, []
    for mid, e in sorted(hits.items()):
        full = fetcher.get(monitoring_url(mid))
        details.append({k: v for k, v in full.items() if k != 'body'})
        m = json.loads(full['body'])['data']
        by_tender.setdefault(m['tender_id'], []).append(summarise_monitoring(m))
        statuses[m.get('status')] += 1
    rows = build_rows(contracts, by_tender)
    validation = None
    if args.spot_check:
        # cross-check the feed join with the per-tender endpoint: a positive control (a tender known from the
        # feed to be monitored) and a seeded random sample of cohort tenders
        import random
        control = next(iter(pages and json.loads(fetcher.get(pages[0]['url'])['body'])['data']))
        sample = random.Random(20261004).sample(sorted(cohort), min(args.spot_check, len(cohort)))
        def total(tid):
            return json.loads(fetcher.get(tender_endpoint_url(tid))['body']).get('total')
        validation = {'method': 'GET /tenders/{procedureId}/monitorings (total)',
                      'positive_control_total': total(control['tender_id']),
                      'sample_size': len(sample), 'sample_with_monitoring': [t for t in sample if total(t)],
                      'agrees_with_feed': all(bool(by_tender.get(t)) == bool(total(t)) for t in sample)}
    counts = {t: Counter(str(r['labels'][t]).lower().replace('none', 'null') for r in rows)
              for t in ('audit_violation', 'audit_violation_corruption_category')}
    type_counts = Counter(t for r in rows for m in r['monitorings'] if m['violation_occurred']
                          for t in m['violation_types'])
    tenders = {r['procedureId']: r for r in rows}
    out = {
        'target': 'prozorro', 'built_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'cohort': {'file': 'data/prozorro.json', 'contracts': len(contracts), 'distinct_tenders': len(cohort),
                   'tender_created_range': [min(c['tenderCreated'] for c in contracts), max(c['tenderCreated'] for c in contracts)]},
        'sources': {'api': f'{API}/monitorings', 'publisher': 'State Audit Service of Ukraine (DASU) via Prozorro audit API',
                    'licence': 'Prozorro open data; the API publishes no per-endpoint licence statement (to be confirmed with the publisher before redistribution beyond identifiers and structured fields)',
                    'code': 'https://github.com/ProzorroUKR/openprocurement.audit.api',
                    'feed': {'start_offset': offset0, 'fields': FEED_FIELDS, 'pages': pages,
                             'entries_read': feed_total},
                    'detail_responses': details},
        'join': {'key': 'monitoring.tender_id == cohort procedureId (exact)', 'name_matching': False,
                 'cohort_monitoring_entries': len(hits),
                 'cohort_tenders_with_monitoring': sum(1 for t in tenders.values() if t['monitored']),
                 'tenders_monitored_rate': sum(1 for t in tenders.values() if t['monitored']) / len(tenders),
                 'monitoring_status_counts': dict(statuses),
                 'notes': ['Monitoring applies to a whole tender; contracts of several lots share its label.',
                           'The feed ordering is by dateModified; entries are read from the first cohort tender-creation date.',
                           'Monitorings flagged restricted may be absent from the public feed; absence is not proof of no monitoring.']},
        'selection_caveat': ('DASU selects tenders for monitoring with its own risk indicators (see docs/indicators.md, sas-3-x), '
                             'which overlap the explorer indicators. A reviewed negative is conditional on selection; '
                             'unmonitored tenders are unknown, not clean.'),
        'summary': {'rows': len(rows), 'tender_level_counts': {t: dict(c) for t, c in counts.items()},
                    'violation_type_counts_in_concluded_violations': dict(type_counts),
                    'requests_made_this_run': fetcher.requests},
        'validation': validation,
        'rows': rows,
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print(f'wrote {args.output}: {dict(counts["audit_violation"])} (contract rows); requests this run {fetcher.requests}')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--contracts', default=str(ROOT / 'data/prozorro.json'))
    p.add_argument('--output', default=str(ROOT / 'research/labels/ukraine.json'))
    p.add_argument('--cache', default=str(common.CACHE / 'ukraine'))
    p.add_argument('--budget', type=int, default=DEFAULT_BUDGET)
    p.add_argument('--fetch', action='store_true', help='perform network requests (default: offline plan)')
    p.add_argument('--spot-check', type=int, default=0, help='cross-check N random cohort tenders via the per-tender endpoint')
    p.add_argument('--from-cache', action='store_true', help='build output from cached responses only')
    return run(p.parse_args(argv))


if __name__ == '__main__':
    sys.exit(main())
