#!/usr/bin/env python3
"""Research only: test fixed Ukrainian candidate indicators against verdict or collusion cohorts.

The candidate list and decision rule were fixed before the first run in
research/calibration/ukraine-candidate-indicators-plan.md. Fields come from the cached official
tender and contracting-module records (cache only, no requests). Rates, likelihood ratios and
points follow tools/propose-indicator-points.py, on all buyers and on two fixed buyer halves.
Changes no score, weight or dataset.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import math
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pp = load('propose_indicator_points', 'tools/propose-indicator-points.py')
COHORT = ROOT / 'research/labels/ukraine-verdict-sweep-cohort.json.gz'
OUT = ROOT / 'research/labels/ukraine-candidate-features.json'
ABOVE_OPEN = ('aboveThreshold', 'aboveThresholdUA', 'aboveThresholdEU')
REJECTED = ('unsuccessful', 'invalid')
CANDIDATES = ['C1 two-bidders', 'C2 only-qualified-bidder', 'C3 two-plus-disqualified', 'C4 short-tender-period',
              'C5 complaint', 'C6 late-document-change', 'C7 december-award', 'C8 fast-signature',
              'C9 small-price-drop', 'C10 just-below-threshold', 'C11 price-change-amendment',
              'C12 term-extension-amendment', 'C13 quantity-cut-amendment', 'C14 early-termination',
              'C15 individual-supplier']
BID_CANDIDATES = ['K1 shared-contact', 'K2 shared-address', 'K3 shared-document', 'K4 close-submission',
                  'K5 tight-bids', 'K6 close-runner-up', 'K7 all-bids-near-expected', 'K8 empty-cover-bid']
CANDIDATES += BID_CANDIDATES
BID_DOCUMENTS = ('documents', 'financialDocuments', 'eligibilityDocuments', 'qualificationDocuments')
SHORT_PERIOD_MIN_COMPARISONS = 10


def day(value):
    return date.fromisoformat(value[:10]) if isinstance(value, str) and len(value) >= 10 else None


def status(flag):
    return 'unknown' if flag is None else 'signal' if flag else 'clear'


def bid_lot_ids(bid):
    return {lv.get('relatedLot') for lv in bid.get('lotValues') or []}


def bids_on_lot(tender, lot):
    bids = [b for b in tender.get('bids') or [] if b.get('status') not in ('deleted', 'draft')]
    return [b for b in bids if lot in bid_lot_ids(b)] if lot and tender.get('lots') else bids


def rejected(tender, bid, lot):
    if bid.get('status') in REJECTED:
        return True
    if any(lv.get('relatedLot') == lot and lv.get('status') in REJECTED for lv in bid.get('lotValues') or []):
        return True
    on_lot = lambda x: not lot or not tender.get('lots') or x.get('lotID') == lot
    return any(x.get('bid_id') == bid.get('id') and x.get('status') == 'unsuccessful' and on_lot(x)
               for x in (tender.get('awards') or []) + (tender.get('qualifications') or []))


def instant(value):
    """An ISO timestamp with an explicit timezone; absent or malformed dates are unknown."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed if parsed.utcoffset() is not None else None
    except ValueError:
        return None


def bid_documents(bid):
    # The API may omit empty document lists. Include the separate two-stage lists too.
    return [d for key in BID_DOCUMENTS for d in bid.get(key) or []]


def address_part(value):
    return ''.join(c for c in str(value or '').lower() if not c.isspace() and not unicodedata.category(c).startswith('P'))


def awarded_lot_bids(row, tender):
    """The awarded lot's bids (part 3 scope): (selected, {bidder id: (bid, lot value, tenderer)},
    unidentified), or None when the record has no bid list or the awarded lot cannot be told."""
    if tender is None or not isinstance(tender.get('bids'), list):
        return None
    award = next((a for a in tender.get('awards') or [] if a.get('id') == row.get('awardId')), None)
    lot = (award or {}).get('lotID')
    if tender.get('lots') and not lot:
        return None
    opening = instant((tender.get('tenderPeriod') or {}).get('endDate'))
    selected = []
    for bid in tender['bids']:
        lv = next((v for v in bid.get('lotValues') or [] if v.get('relatedLot') == lot), None) if tender.get('lots') else None
        if tender.get('lots') and lv is None:
            continue
        statuses = {bid.get('status'), (lv or {}).get('status')}
        if statuses & {'deleted', 'draft'}:
            continue
        disqualified = any(x.get('bid_id') == bid.get('id') and x.get('status') == 'unsuccessful'
                           and (not tender.get('lots') or x.get('lotID') == lot)
                           for x in (tender.get('awards') or []) + (tender.get('qualifications') or []))
        if not (statuses & {'active', *REJECTED} or disqualified):
            continue
        modified = instant((lv or {}).get('dateModified') or bid.get('dateModified'))
        if 'invalid' in statuses and not disqualified and opening and modified and modified < opening:
            continue
        selected.append((bid, lv))

    # A bidder counts once, even if the record repeats its bid. Keep the first cached bid.
    bidders = {}
    unidentified = False
    for bid, lv in selected:
        tenderer = (bid.get('tenderers') or [{}])[0]
        bidder = (tenderer.get('identifier') or {}).get('id')
        if not bidder:
            unidentified = True
        else:
            bidders.setdefault(bidder, (bid, lv, tenderer))
    return selected, bidders, unidentified


def bid_features(row, tender):
    """K1–K8 compare bidders in memory; only True/False/None leave this function."""
    out = dict.fromkeys(BID_CANDIDATES)
    scope = awarded_lot_bids(row, tender)
    if scope is None:
        return out
    selected, bidders, unidentified = scope
    bids = list(bidders.values())
    award = next((a for a in tender.get('awards') or [] if a.get('id') == row.get('awardId')), None)
    lot = (award or {}).get('lotID')

    def too_few(minimum):
        return len(selected) < minimum or (not unidentified and len(bids) < minimum)

    def shared(values):
        """Known matches win; missing fields cannot turn a potential match into clear."""
        if too_few(2):
            return False
        seen = set()
        missing = unidentified
        for tokens in values:
            if tokens is None:
                missing = True
            else:
                if seen & tokens:
                    return True
                seen.update(tokens)
        return None if missing else False

    contacts, addresses, hashes, dates = [], [], [], []
    own_hashes = {d['hash'] for d in tender.get('documents') or [] if d.get('hash')}
    for bid, lv, tenderer in bids:
        contact = tenderer.get('contactPoint') or {}
        tokens = set()
        phone = re.sub(r'[^0-9]', '', str(contact.get('telephone') or ''))
        if len(phone) >= 9:
            tokens.add(('phone', phone[-9:]))
        email = str(contact.get('email') or '').strip().lower()
        if email:
            tokens.add(('email', email))
        contacts.append(tokens if 'telephone' in contact or 'email' in contact else None)
        address = tenderer.get('address') or {}
        street, locality = address_part(address.get('streetAddress')), address_part(address.get('locality'))
        addresses.append({(street, locality)} if street and locality else
                         set() if 'streetAddress' in address and 'locality' in address else None)
        docs = bid_documents(bid)
        known_hashes = {d['hash'] for d in docs if d.get('hash')} - own_hashes
        # Keep known matches available even if another document has no hash.
        hashes.append(known_hashes)
        dates.append(instant(lv['date'] if lv is not None and 'date' in lv else bid.get('date')))
    out['K1 shared-contact'] = shared(contacts)
    out['K2 shared-address'] = shared(addresses)
    out['K3 shared-document'] = shared(hashes)
    if out['K3 shared-document'] is False and len(bids) >= 2 and any(not d.get('hash') for b, _, _ in bids for d in bid_documents(b)):
        out['K3 shared-document'] = None
    hit = any(abs((a - b).total_seconds()) < 600 for i, a in enumerate(dates) if a is not None
              for b in dates[i + 1:] if b is not None)
    out['K4 close-submission'] = False if too_few(2) else True if hit else None if unidentified or any(d is None for d in dates) else False

    values = [(lv['value'] if lv is not None and 'value' in lv else bid.get('value')) or {} for bid, lv, _ in bids]
    amounts = [v.get('amount') for v in values]
    # Do not estimate price dispersion or order from an incomplete set of bidder values.
    complete = not unidentified and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0 for v in amounts)
    for key, minimum in (('K5 tight-bids', 3), ('K6 close-runner-up', 2), ('K7 all-bids-near-expected', 2)):
        if too_few(minimum):
            out[key] = False
        elif not complete:
            out[key] = None
        elif key == 'K5 tight-bids':
            avg = mean(amounts)
            out[key] = pstdev(amounts) / avg < 0.03 if avg > 0 else None
        elif key == 'K6 close-runner-up':
            lowest, second = sorted(amounts)[:2]
            out[key] = second <= 1.01 * lowest
        else:
            expected = next((l.get('value') for l in tender['lots'] if l.get('id') == lot), None) if tender.get('lots') else tender.get('value')
            expected = expected or {}
            amount, currency = expected.get('amount'), expected.get('currency')
            if isinstance(amount, (int, float)) and not isinstance(amount, bool) and math.isfinite(amount) and amount > 0 and currency and all(v.get('currency') == currency for v in values):
                out[key] = all(v >= 0.97 * amount for v in amounts)

    winner = (award or {}).get('bid_id')
    if winner:
        winning_bid = next((b for b, _ in selected if b.get('id') == winner), {})
        winner_bidder = (((winning_bid.get('tenderers') or [{}])[0]).get('identifier') or {}).get('id')
        others = [b for identifier, (b, _, _) in bidders.items() if b.get('id') != winner and identifier != winner_bidder]
        hit = any(b.get('id') and len(bid_documents(b)) <= 2 for b in others)
        out['K8 empty-cover-bid'] = True if hit else None if unidentified or any(not b.get('id') for b in others) else False
    elif not selected:
        out['K8 empty-cover-bid'] = False
    return out


def tender_features(row, tender, contract):
    """Candidate statuses for one cohort row: True, False or None (unknown)."""
    lot = row.get('lotId')
    award = next((a for a in tender.get('awards') or [] if a.get('id') == row.get('awardId')), None)
    signed = next((c for c in tender.get('contracts') or [] if c.get('contractID') == row.get('contractId')), None)
    offers = row.get('offers')
    out = row_features(row)
    if not isinstance(offers, int) or offers < 1 or not award:
        out['C2 only-qualified-bidder'] = None
    elif offers < 2:
        out['C2 only-qualified-bidder'] = False
    else:
        others = [b for b in bids_on_lot(tender, lot) if b.get('id') != award.get('bid_id')]
        out['C2 only-qualified-bidder'] = all(rejected(tender, b, lot) for b in others) if others else None
    out['C5 complaint'] = any(x.get('complaints') for x in [tender] + (tender.get('awards') or []) + (tender.get('qualifications') or []))
    period = tender.get('tenderPeriod') or {}
    start, end = period.get('startDate'), period.get('endDate')
    docs = [d for d in tender.get('documents') or [] if d.get('documentOf', 'tender') == 'tender']
    if not start or not end:
        out['C6 late-document-change'] = None
    else:
        s, e = day(start), day(end)
        late = lambda v: bool(v) and (day(v) - s).days >= 1 and 0 <= (e - day(v)).days < 3
        hit = any(late(d.get('datePublished')) or late(d.get('dateModified')) for d in docs)
        undated = any(not d.get('datePublished') and not d.get('dateModified') for d in docs)
        out['C6 late-document-change'] = True if hit else None if undated else False
    award_day = day(award.get('date')) if award else None
    out['C7 december-award'] = award_day.month == 12 if award_day else None
    if row.get('procedure') not in ABOVE_OPEN:
        out['C8 fast-signature'] = False
    else:
        signed_day = day((signed or {}).get('dateSigned'))
        out['C8 fast-signature'] = 0 <= (signed_day - award_day).days < 5 if signed_day and award_day else None
    # The lot's expected value when the tender has lots, the tender's otherwise (never a fallback).
    expected = next((l.get('value') for l in tender['lots'] if l.get('id') == lot), None) if tender.get('lots') else tender.get('value')
    won = (award or {}).get('value')
    if expected and won and expected.get('amount') and won.get('amount') is not None and expected.get('currency') == won.get('currency'):
        out['C9 small-price-drop'] = won['amount'] >= 0.98 * expected['amount']
    else:
        out['C9 small-price-drop'] = None
    value = tender.get('value') or {}
    cat = tender.get('mainProcurementCategory')
    works = cat == 'works' if cat else str(row.get('cpv') or '').startswith('45')
    threshold = 1_500_000 if works else 200_000
    if value.get('currency') == 'UAH' and value.get('amount') is not None:
        out['C10 just-below-threshold'] = 0.9 * threshold <= value['amount'] < threshold
    else:
        out['C10 just-below-threshold'] = None
    if contract is None:
        for k in ('C11 price-change-amendment', 'C12 term-extension-amendment', 'C13 quantity-cut-amendment', 'C14 early-termination'):
            out[k] = None
    else:
        active = [c for c in contract.get('changes') or [] if c.get('status') == 'active']
        types = {t for c in active for t in c.get('rationaleTypes') or []}
        untyped = any(not c.get('rationaleTypes') for c in active)
        for k, wanted in (('C11 price-change-amendment', {'itemPriceVariation', 'itemPriceChange'}),
                          ('C12 term-extension-amendment', {'durationExtension', 'fiscalYearExtension'}),
                          ('C13 quantity-cut-amendment', {'volumeCuts'})):
            out[k] = True if types & wanted else None if untyped else False
        if not contract.get('status'):
            out['C14 early-termination'] = None
        elif contract['status'] != 'terminated':
            out['C14 early-termination'] = False
        else:
            paid, val = (contract.get('amountPaid') or {}).get('amount'), (contract.get('value') or {}).get('amount')
            out['C14 early-termination'] = paid < 0.9 * val if paid is not None and val else None
    out.update(bid_features(row, tender))
    return out


def row_features(row):
    """Candidates read from the cohort row itself, known even without the tender record."""
    offers, dq = row.get('offers'), row.get('disqualifiedBefore')
    kinds = {s.get('identifierType') for s in row.get('supplierIds') or []}
    return {'C1 two-bidders': None if not isinstance(offers, int) or offers < 1 else offers == 2,
            'C3 two-plus-disqualified': dq >= 2 if isinstance(dq, int) else None,
            'C15 individual-supplier': None if len(row.get('supplierIds') or []) != 1 or not kinds <= {'EDRPOU', 'RNOKPP'} else kinds == {'RNOKPP'}}


def short_period(rows):
    """C4 needs the comparison distribution per procedure type: filled in after all rows are read."""
    by_type = {}
    for r in rows:
        if r['label'] == 'comparison' and isinstance(r.get('tenderPeriodDays'), int):
            by_type.setdefault(r['procedure'], []).append(r['tenderPeriodDays'])
    cut = {}
    for kind, days in by_type.items():
        if len(days) >= SHORT_PERIOD_MIN_COMPARISONS:
            days.sort()
            cut[kind] = days[int(0.25 * (len(days) - 1))]
    return cut


def build(cohort_path, cache):
    vc = load('verdict_cohort', 'tools/build-ukraine-verdict-cohort.py')
    cc = load('verdict_changes', 'tools/fetch-verdict-contract-changes.py')
    f = vc.bc.Fetcher(Path(cache).expanduser(), budget=0, network=False, prior=0, opener=vc.opener)
    rows = json.loads(gzip.open(cohort_path).read())['rows']
    cut = short_period([r for r in rows if r.get('procedure') not in pp.NON_COMPETITIVE])
    out = []
    for row in rows:
        r = f.fetch(vc.bc.tender_url(row['procedureId']))
        tender = json.loads(r['body'])['data'] if r and r['status'] == 200 else None
        contract = None
        if tender:
            ids = [c['id'] for c in tender.get('contracts') or [] if c.get('contractID') == row['contractId']]
            cr = f.fetch(cc.contract_url(ids[0])) if len(ids) == 1 else None
            contract = json.loads(cr['body'])['data'] if cr and cr['status'] == 200 else None
        feats = tender_features(row, tender, contract) if tender else {**{k: None for k in CANDIDATES}, **row_features(row)}
        days = row.get('tenderPeriodDays')
        feats['C4 short-tender-period'] = days <= cut[row['procedure']] if row.get('procedure') in cut and isinstance(days, int) else None
        out.append({'id': row['id'], 'procedureId': row['procedureId'], 'procedure': row.get('procedure'), 'group': row.get('group'),
                    'label': row['label'], 'finality': row.get('finality'), 'buyerId': row.get('buyerId'),
                    'checks': {k: {'status': status(feats[k]), 'points': None} for k in CANDIDATES}})
    return out, cut


def half(buyer):
    return 'learn' if int(hashlib.sha256(str(buyer).encode()).hexdigest()[0], 16) % 2 == 0 else 'check'


def evaluate(rows):
    results = []
    for check in CANDIDATES:
        res = {'candidate': check, 'all': pp.analyse(rows, check)}
        for name in ('learn', 'check'):
            res[name + '_half'] = pp.analyse([r for r in rows if half(r['buyer']) == name], check)
        res['decision'] = pp.decide(res['all'])
        results.append(res)
    return results


def table(results):
    def rate(x, g):
        y = x[g]
        return f"{y['rate'] * 100:.0f}% ({y['tender_hits']}/{y['tenders']})" if y['buyers'] else 'NA'

    def lr(x):
        ci = f" [{x['lr_ci'][0]:.2f}, {x['lr_ci'][1]:.2f}]" if x.get('lr_ci') else ''
        return f"{x['lr_shrunk']:.2f}{ci}" if x.get('lr_shrunk') else 'NA'
    lines = ['| Candidate | Hit rate, convicted | Corruption | Fraud | Comparisons | LR+ all [95 %] | LR+ learn half [95 %] | LR+ check half | Points (all) [95 %] | Decision |',
             '|---|---|---|---|---|---|---|---|---|---|']
    for r in sorted(results, key=lambda r: -(r['all']['combined']['rate'] or 0)):
        a = r['all']
        pci = f" [{a['proposed_points_ci'][0]}, {a['proposed_points_ci'][1]}]" if a.get('proposed_points_ci') else ''
        lines.append(f"| {r['candidate']} | {rate(a, 'combined')} | {rate(a, 'corruption')} | {rate(a, 'fraud')} | {rate(a, 'comparison')} | "
                     f"{lr(a)} | {lr(r['learn_half'])} | {lr(r['check_half'])} | {a['proposed_points']}{pci} | {r['decision']} |")
    return '\n'.join(lines)


def multi_bid_ids(path):
    """Row IDs whose single-offer check is clear: the awarded lot had 2+ bids."""
    data = json.loads(Path(path).read_text())
    rows = data['rows'] if isinstance(data, dict) else data
    return {r['id'] for r in rows if (r.get('checks', {}).get('ua-single-offer') or {}).get('status') == 'clear'}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--cohort', default=str(COHORT))
    p.add_argument('--cache', default=str(Path.home() / '.cache/contract-signals/labels/verdict-cohort'))
    p.add_argument('--features', default=str(OUT), help='write per-row candidate statuses here')
    p.add_argument('--json', help='write full results here')
    p.add_argument('--positive-labels', default=','.join(pp.POSITIVE), help='labels pooled as positives (collusion for the AMCU cohort)')
    p.add_argument('--reuse-features', action='store_true', help='read --features as written by an earlier run instead of rebuilding it')
    p.add_argument('--multi-bid', metavar='ROWS', help='sensitivity check: keep only tenders with 2+ bids (ua-single-offer clear in these '
                                                        'per-row checks from analyze-ukraine-verdict-cohort.cjs)')
    args = p.parse_args(argv)
    if args.reuse_features:
        cut = 'not recomputed (features reused)'
    else:
        feature_rows, cut = build(args.cohort, args.cache)
        Path(args.features).write_text(json.dumps(feature_rows) + '\n')
    rows, skipped = pp.load_rows(args.features, None, tuple(args.positive_labels.split(',')))
    if args.multi_bid:
        multi = multi_bid_ids(args.multi_bid)
        rows = [r for r in rows if r['id'] in multi]
        print('Sensitivity check: tenders with 2+ bids only (single offer clear).')
    positives = [r for r in rows if 'combined' in r['groups']]
    print(f"{len(positives)} eligible positive rows ({len({r['buyer'] for r in positives})} buyers); "
          f"{sum('comparison' in r['groups'] for r in rows)} comparison rows; left out (non-competitive): {skipped}.")
    for name in ('learn', 'check'):
        sub = [r for r in rows if half(r['buyer']) == name]
        print(f"  {name} half: {sum('combined' in r['groups'] for r in sub)} positive rows, "
              f"{len({r['buyer'] for r in sub if 'combined' in r['groups']})} positive buyers, {sum('comparison' in r['groups'] for r in sub)} comparisons")
    print(f'C4 cut-offs (days, 25th percentile of comparisons): {cut}\n')
    results = evaluate(rows)
    print(table(results))
    if args.json:
        Path(args.json).write_text(json.dumps({'plan': 'research/calibration/ukraine-candidate-indicators-plan.md',
                                               'short_period_cutoffs': cut, 'results': results}, indent=1) + '\n')


if __name__ == '__main__':
    main()
