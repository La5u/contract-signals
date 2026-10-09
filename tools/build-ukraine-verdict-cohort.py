#!/usr/bin/env python3
"""Build a research-only verdict cohort; default is a bounded offline request plan.

Reuses the audit cohort's serial cached Fetcher (persisted cap, spacing, backoff,
403 stop) and importer-backed minimized rows. Comparison tenders come from the
prozorro.gov.ua buyer search (POST, as in tools/import-prozorro.py): same buyer, same
creation year read from the tenderID, seeded order. A page-capped listing of a large
buyer may be incomplete; this is recorded, never hidden.
One deterministically ranked signed-contract row represents each tender.
"""
import argparse
import calendar
import gzip
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
# Importing these modules performs no requests.
import importlib.util
spec = importlib.util.spec_from_file_location('verdict_label_cohort', ROOT / 'tools/build-ukraine-label-cohort.py')
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)
imp = bc.imp
CACHE = Path.home() / '.cache/contract-signals/labels/verdict-cohort'
COHORT_ID = 'ukraine-verdict-cohort'
LABELS = {'corruption (official involved)': 'corruption', 'procurement fraud (no official established)': 'fraud'}
ELIGIBLE = {'confirmed', 'presumed'}


def three_months_before(today):
    month = today.year * 12 + today.month - 1 - 3
    year, month = divmod(month, 12)
    month += 1
    return date(year, month, min(today.day, calendar.monthrange(year, month)[1]))


def classify_finality(verdicts, today):
    """Use explicit finality, not free-text appeal rights in verdict evidence.

    Decided appeals without an explicit final marker remain ineligible. Producers
    should set verification.finality to 'final …' after verifying entry into force.
    """
    states = [str((v.get('verification') or {}).get('finality') or '').lower().strip() for v in verdicts]
    if any(s.startswith('final') for s in states):
        return 'confirmed'
    appeals = [s for s in states if s.startswith(('appeal', 'pending-appeal'))]
    unresolved = ('pending', 'unavailable', 'undecided', 'not yet decided', 'not decided')
    # An appellate ruling enters into force when pronounced (CPC art. 532), so a conviction it keeps is final.
    upheld = ('convictions preserved', 'conviction upheld', 'upheld', 'replaced with conviction')
    if appeals and all(any(word in s for word in upheld) and not any(word in s for word in unresolved) for s in appeals):
        return 'confirmed'
    if appeals:
        return 'pending-appeal'
    if not appeals and any(bc.day(v.get('verdict_date')) and bc.day(v['verdict_date']) <= three_months_before(today) for v in verdicts):
        return 'presumed'
    return 'too-recent'


def positive_tenders(verdicts, today):
    grouped = defaultdict(list)
    for v in verdicts:
        if v.get('tender_id_normalised'):
            grouped[v['tender_id_normalised']].append(v)
    out = []
    for tid, vs in sorted(grouped.items()):
        positives = [v for v in vs if v.get('proposed_label') in LABELS]
        if not positives:
            continue
        label = 'corruption' if any(LABELS[v['proposed_label']] == 'corruption' for v in positives) else 'fraud'
        finality = classify_finality(vs, today)
        out.append({'tenderID': tid, 'label': label, 'finality': finality, 'positive': finality in ELIGIBLE,
                    'verdict_ids': sorted({str(v['reyestr_id']) for v in vs if v.get('reyestr_id') is not None}), 'group': tid})
    return out


def comparison_order(meta, candidates, excluded, used):
    """Same buyer, same creation year (a tenderID starts UA-YYYY-), seeded order; candidates are tenderIDs."""
    year = (meta.get('created') or '')[:4]
    options = {t for t in candidates.get(meta.get('buyerId'), ()) if year and t[3:7] == year
               and t not in excluded and t not in used and t != meta.get('tenderID')}
    return sorted(options, key=lambda t: (bc.rank('verdict-comparison', meta['procedureId'], t), t))


def search_url(buyer, page, year=None):
    query = {'buyer[]': buyer, 'page': page}
    if year:  # the site search filters on the tender date; the tenderID year is rechecked in comparison_order
        query.update({'date[tender][start]': f'{year}-01-01', 'date[tender][end]': f'{year}-12-31'})
    return imp.SEARCH + '?' + bc.urllib.parse.urlencode(query)


def opener(url):
    """The prozorro.gov.ua tender search answers POST only (empty body); everything else is a plain GET."""
    if not url.startswith(imp.SEARCH):
        return bc.Fetcher._urlopen(url)
    req = bc.urllib.request.Request(url, data=b'', method='POST', headers={'User-Agent': bc.USER_AGENT, 'Accept': 'application/json'})
    try:
        with bc.urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read(), dict(r.headers)
    except bc.urllib.error.HTTPError as e:
        return e.code, b'', dict(e.headers or {})


class RequestPlan:
    """Upper-bound slots, including dependency placeholders; never exceed remaining cap."""
    def __init__(self, fetcher):
        self.f, self.requests, self.omitted = fetcher, [], 0

    def add(self, url):
        if self.f.cached(url) or url in self.requests:
            return
        if len(self.requests) < max(0, self.f.budget - self.f.requests):
            self.requests.append(url)
        else:
            self.omitted += 1


def resolve(f, tid):
    r = f.fetch(imp.DETAILS.format(tender_id=tid))
    if not r or r['status'] != 200:
        return None
    internal = json.loads(r['body']).get('id')
    if not internal:
        return None
    tender, _ = bc.load_tender(f, internal)
    if tender and tender.get('tenderID') != tid:
        raise RuntimeError('tenderID mismatch for ' + tid)
    return tender


def search(f, metas, max_pages):
    """List each positive buyer's tenderIDs for the positive's year through the site search (pages start at 1),
    as tools/import-prozorro.py does; the listing is newest first, so the year filter is what reaches old tenders.

    Returns {buyerId: [tenderID, ...]}, the pages read, and whether every listing was complete.
    """
    candidates, pages, complete = {}, [], True
    for buyer, year in sorted({(m['buyerId'], (m.get('created') or '')[:4]) for m in metas if m.get('buyerId')}):
        ids, total = [], None
        for page in range(1, max_pages + 1):
            r = f.fetch(search_url(buyer, page, year or None))
            if not r or r['status'] != 200:
                break
            body = json.loads(r['body'])
            pages.append({k: r[k] for k in ('url', 'sha256', 'retrieved_at')})
            total = body.get('total', total)
            ids += [t['tenderID'] for t in body.get('data', []) if t.get('tenderID')]
            if not body.get('data') or (total is not None and len(ids) >= total):
                break
        if total is None or len(ids) < total:
            complete = False
        candidates.setdefault(buyer, []).extend(ids)
    return candidates, pages, complete


def representative_row(tender, info):
    rows, excluded = bc.tender_rows(tender)
    if not rows:
        return None, excluded
    row = min(rows, key=lambda r: (bc.rank('verdict-contract', tender['id'], r['id']), r['id']))
    row.update(info)
    row['cohortId'] = COHORT_ID
    # The engine requires display text; use constants rather than source names/titles.
    row['buyer'] = 'Prozorro buyer (name omitted)'
    row['description'] = 'Prozorro tender (title omitted)'
    # Supplier IDs were masked by the importer; mask a personal buyer ID too.
    buyer = imp.supplier_identifier((tender.get('procuringEntity') or {}).get('identifier'))
    if buyer:
        row['buyerId'] = imp.mask_ids([buyer])[0]['id']
    return row, excluded


def plan(f, positives, k, scan_pages):
    p = RequestPlan(f)
    for info in positives:
        if not info['positive']:
            continue
        tid = info['tenderID']
        url = imp.DETAILS.format(tender_id=tid)
        p.add(url)
        r = f.fetch(url)  # cache only
        internal = json.loads(r['body']).get('id') if r and r['status'] == 200 else None
        p.add(bc.tender_url(internal or '<internal-id-for-' + tid + '>'))
    eligible = [t for t in positives if t['positive']]
    if eligible and k:
        for info in eligible:
            for page in range(1, scan_pages + 1):
                p.add(search_url('<buyer-of-' + info['tenderID'] + '>', page, info['tenderID'][3:7]))
        for info in eligible:
            for i in range(k):
                p.add(imp.DETAILS.format(tender_id='<comparison-' + info['tenderID'] + '-' + str(i + 1) + '>'))
                p.add(bc.tender_url('<internal-id-of-comparison-' + info['tenderID'] + '-' + str(i + 1) + '>'))
    print(f'PLAN (offline); hard cap {f.budget}; already spent {f.requests}')
    for url in p.requests:
        print('GET ' + url)
    print(f'Planned request count (upper bound, retries consume the same cap): {len(p.requests)}; omitted slots: {p.omitted}')
    print('Angle-bracket slots depend on earlier responses; cache hits are free. Use --download to execute.')
    print(f'Positive tenders: {len(eligible)}; flagged/ineligible: {len(positives) - len(eligible)}')
    return p


def run(args):
    cache = Path(args.cache).expanduser().resolve()
    if cache == ROOT or ROOT in cache.parents:
        raise ValueError('raw cache must be outside the repository')
    verdicts = json.loads(Path(args.input).read_text())['verdicts']
    today = date.fromisoformat(args.run_date) if args.run_date else date.today()
    positives = positive_tenders(verdicts, today)
    excluded_ids = {v.get('tender_id_normalised') for v in verdicts}
    f = bc.Fetcher(cache, budget=args.budget, network=args.download, prior=0, opener=opener)
    if not args.download and not args.from_cache:
        plan(f, positives, args.k, args.scan_pages)
        return 0
    rows, records, notes, metas = [], [], [], []
    scan_pages, scan_complete = [], False
    try:
        for info in positives:
            records.append(dict(info))
            if not info['positive']:
                continue
            tender = resolve(f, info['tenderID'])
            if not tender:
                records[-1]['unavailable'] = 'missing_or_uncached_record'
                continue
            meta = bc.tender_meta(tender)
            records[-1]['created'] = meta['created']
            metas.append((info, meta))
            row, exclusions = representative_row(tender, info)
            records[-1].update({'contract_rows_excluded': exclusions, 'row_available': row is not None})
            if row:
                rows.append(row)
        # All requests, retries included, stay under the Fetcher's persisted cap.
        candidates, scan_pages, scan_complete = search(f, [m for _, m in metas], args.scan_pages) if args.k else ({}, [], False)
        used = set()
        for info, meta in metas:
            count = 0
            for cand in comparison_order(meta, candidates, excluded_ids, used):
                if count >= args.k:
                    break
                tender = resolve(f, cand)
                if not tender:
                    continue
                actual = bc.tender_meta(tender)
                if actual['buyerId'] != meta['buyerId'] or (actual['created'] or '')[:4] != (meta['created'] or '')[:4]:
                    continue
                comp = {'label': 'comparison', 'finality': None, 'positive': False, 'verdict_ids': [], 'group': info['tenderID']}
                row, _ = representative_row(tender, comp)
                if row:
                    used.add(cand)
                    rows.append(row)
                    records.append({'tenderID': cand, **comp})
                    count += 1
            notes.append({'group': info['tenderID'], 'comparisons': count, 'requested': args.k})
    except (bc.BudgetExceeded, bc.Blocked, bc.Throttled) as e:
        notes.append(str(e))
    # Preserve even positives not reached before a cap or block.
    recorded = {r['tenderID'] for r in records}
    records.extend({**p, 'unavailable': 'not_reached'} for p in positives if p['tenderID'] not in recorded)
    out = {'schema': 'ukraine-verdict-cohort/1', 'built_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
           'run_date': today.isoformat(), 'tenders': records, 'rows': rows,
           'summary': {'requests_total': f.requests, 'budget': f.budget, 'scan_complete': scan_complete, 'notes': notes},
           'provenance': {'public_api': imp.API, 'details': imp.DETAILS, 'scan_pages': scan_pages,
                          'selection': 'prozorro.gov.ua buyer search; same buyer identifier and tenderID creation year; SHA-256 rank; tenders without a signed contract skipped; no comparison reuse.',
                          'row_selection': 'One SHA-256 ranked signed-contract row per tender, using importer/minimize_row; no names or free text.',
                          'caveat': 'Comparisons are unlabelled, not clean. A page-capped buyer listing may be incomplete (summary.scan_complete). Presumed finality is a heuristic, not verified entry into force. Decided appeals without final marker remain ineligible.'}}
    imp.save_gz(Path(args.output), out)
    print(f'wrote {args.output}: {len(rows)} rows; {f.requests} requests spent; scan_complete={scan_complete}')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--input', default=str(ROOT / 'research/labels/ukraine-verdict-candidates.json'))
    p.add_argument('--output', default=str(ROOT / 'research/labels/ukraine-verdict-cohort.json.gz'))
    p.add_argument('--cache', default=str(CACHE))
    p.add_argument('--budget', type=int, default=300, help='hard request cap across resumed runs')
    p.add_argument('--k', type=int, default=3)
    p.add_argument('--scan-pages', type=int, default=10, help='maximum search pages per buyer (including cached pages)')
    p.add_argument('--run-date', help='override local run date, YYYY-MM-DD')
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--download', action='store_true')
    mode.add_argument('--from-cache', action='store_true', help='write cohort using cached responses only')
    args = p.parse_args(argv)
    if min(args.budget, args.k, args.scan_pages) < 0:
        p.error('budget, k and scan-pages must be nonnegative')
    return run(args)


if __name__ == '__main__':
    sys.exit(main())
