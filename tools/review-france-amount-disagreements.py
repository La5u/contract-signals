#!/usr/bin/env python3
"""Offline, read-only review of French sources-disagree records.

No network, replacements, ranking changes, annualisation or financial equivalence.
Detailed queue and provenance are written exclusively to a new private cache run.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / '.cache/contract-signals'
DATASETS = ('data/decp-history.json', 'data/decp-cities.json')


def many(value):
    return value if isinstance(value, list) else [] if value is None else [value]


def text(value):
    return value.get('#text') if isinstance(value, dict) else value


def number(value):
    try:
        if isinstance(value, bool) or value is None:
            return None
        n = Decimal(str(text(value)))
        return str(n) if n.is_finite() and n >= 0 else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def money(node, path=''):
    """Keep field semantics and scope; never flatten all printed numbers together."""
    out = []
    if isinstance(node, dict):
        for key, value in node.items():
            pointer = path + '/' + key
            if 'Amount' in key:
                basis = ('maximum' if 'Maximum' in key else 'estimate' if 'Estimated' in key
                         else 'tender_value_period_unknown' if key == 'cbc:PayableAmount'
                         else 'unknown')
                out.append({'pointer': pointer, 'value': number(value),
                            'currency': value.get('@currencyID') if isinstance(value, dict) else None,
                            'basis': basis})
            else:
                out.extend(money(value, pointer))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            out.extend(money(value, path + '/' + str(i)))
    return out


def notice_lots(record):
    """Exact buyer role + settled-contract reference; no names or substring joins."""
    try:
        n = json.loads(record['donnees'])['EFORMS']['ContractAwardNotice']
        ext = n['ext:UBLExtensions']['ext:UBLExtension']['ext:ExtensionContent']['efext:EformsExtension']
        nr = ext.get('efac:NoticeResult') or {}
        orgs = {text(o['efac:Company']['cac:PartyIdentification']['cbc:ID']): o['efac:Company']
                for o in many(ext.get('efac:Organizations', {}).get('efac:Organization'))}
        buyers = set()
        for party in many(n.get('cac:ContractingParty')):
            ref = text(party.get('cac:Party', {}).get('cac:PartyIdentification', {}).get('cbc:ID'))
            for legal in many(orgs.get(ref, {}).get('cac:PartyLegalEntity')):
                buyers.add(str(text(legal.get('cbc:CompanyID'))))
        tenders = {text(t.get('cbc:ID')): (i, t) for i, t in enumerate(many(nr.get('efac:LotTender')))}
        results = many(nr.get('efac:LotResult'))
        out = []
        for ci, contract in enumerate(many(nr.get('efac:SettledContract'))):
            reference = text(contract.get('efac:ContractReference', {}).get('cbc:ID'))
            tid = text(contract.get('efac:LotTender', {}).get('cbc:ID'))
            linked = [(i, r) for i, r in enumerate(results)
                      if any(text(t.get('cbc:ID')) == tid for t in many(r.get('efac:LotTender')))]
            if not reference or not tid or tid not in tenders or len(linked) != 1:
                continue
            ti, tender = tenders[tid]
            ri, result = linked[0]
            values = money(tender, '/NoticeResult/LotTender/' + str(ti)) + money(result, '/NoticeResult/LotResult/' + str(ri))
            # Procedure totals are explicitly excluded, not compared to a lot's DECP value.
            out.append({'buyers': buyers, 'reference': str(reference), 'notice_id': record.get('idweb'),
                        'notice_version': text(n.get('cbc:VersionID')), 'contract_index': ci,
                        'result_id': text(result.get('cbc:ID')), 'tender_id': tid,
                        'date': text(contract.get('cbc:IssueDate')), 'values': values})
        return out
    except (KeyError, TypeError, ValueError, AttributeError):
        return []


def reconcile(row, declarations, notices):
    vals = [Decimal(v) for s in row.get('amountSources', []) if (v := number(s.get('amount'))) is not None]
    distinct = set(vals)
    ratio = str(max(vals) / min(vals)) if vals and min(vals) > 0 else None
    # A ratio is a queue diagnostic only; it cannot establish an annual/full-term basis.
    return {'id': row['id'], 'buyer_siret': row['buyerSiret'], 'contract_id': row['contractId'],
            'buyer': row.get('buyer'),
            'published_amount': row.get('amount'), 'published_range': row.get('amountRange'),
            'amount_sources': row.get('amountSources', []), 'duration_months': row.get('durationMonths'),
            'distinct_declared_values': len(distinct), 'max_min_ratio': ratio,
            'over_2x': bool(vals and min(vals) > 0 and max(vals) > 2 * min(vals)),
            'buyer_declarations': declarations, 'notice_evidence': notices,
            'status': 'exact_notice_requires_basis_review' if notices else 'no_exact_notice_in_reviewed_cache',
            'resolved': False,
            'unknowns': ['annual_or_full_term_not_established', 'signed_contract_and_actual_spend_not_verified',
                         'declaration_tax_and_period_not_independently_verified',
                         'source_routes_not_independent_votes', 'no_amount_precedence_established']}


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def build(root=ROOT, cache=CACHE):
    provenance = []
    def load(path):
        blob = path.read_bytes()
        provenance.append({'path': str(path), 'sha256': digest(blob), 'bytes': len(blob)})
        value = json.loads(gzip.decompress(blob) if path.suffix == '.gz' else blob)
        if isinstance(value, dict):
            provenance[-1]['source_metadata'] = {k: value[k] for k in
                ('source', 'sources', 'retrievedAt') if k in value}
        return value
    rows = []
    populations = {}
    for rel in DATASETS:
        data = load(root / rel)
        populations[rel] = len(data)
        rows.extend((rel, r) for r in data if r.get('verification', {}).get('status') == 'sources-disagree')
    declarations = defaultdict(list)
    for rel in ('data/decp-feeds-raw.json.gz', 'data/city-portals-raw.json.gz'):
        raw = load(root / rel)
        for i, r in enumerate(raw['records']):
            declarations[(str(r.get('acheteur_id')), str(r.get('id')))].append({
                'file': rel, 'pointer': '/records/' + str(i), 'source': r.get('sourceDataset'),
                'source_url': r.get('sourceFile'), 'value': number(r.get('montant')),
                'basis': 'declared_initial_period_unknown', 'modification_id': r.get('modification_id'),
                'current': r.get('donneesActuelles'), 'duration_months': r.get('dureeMois')})
    for rel in ('data/decp-cities-raw.json', 'data/decp-history-raw.json.gz'):
        raw = load(root / rel)
        for i, r in enumerate(raw['records']):
            declarations[(str(r.get('acheteur_id')), str(r.get('id')))].append({
                'file': rel, 'pointer': '/records/' + str(i), 'source': 'ministry',
                'source_url': raw.get('source'), 'retrieved_at': raw.get('retrievedAt'),
                'value': number(r.get('montant')), 'basis': 'declared_initial_period_unknown',
                'duration_months': r.get('dureemois'),
                'modification_value': number(r.get('montantmodification')),
                'modification_basis': 'revised_declared_total_not_increment'})
    notice_index = defaultdict(list)
    def index(records, source):
        for i, record in enumerate(records):
            for lot in notice_lots(record):
                buyers = lot.pop('buyers')
                for buyer in buyers:
                    notice_index[(buyer, lot['reference'])].append({**lot, 'file': source, 'record_index': i})
    raw = load(root / 'data/boamp-raw.json.gz')
    index(raw['records'], 'data/boamp-raw.json.gz')
    sample_candidates = defaultdict(list)
    rejected = 0
    # Explicit bounded cache inventory; never indiscriminately scan private history.
    directories = sorted((cache / 'accuracy-sample-20261008').glob('responses*'))
    directories += [cache / 'paris-pairs-20261008',
                    cache / 'decp-conflict-dijon/project-notices-20261008']
    for directory in directories:
        manifest = directory / 'fetch-manifest.json'
        if not manifest.exists():
            continue
        meta = load(manifest)
        for entry in meta['entries']:
            if entry.get('status') != 200 or entry.get('truncated'):
                rejected += 1
                continue
            path = directory / entry['file']
            if path.resolve().parent != directory.resolve():
                raise ValueError('Response escaped manifest directory')
            blob = path.read_bytes()
            if digest(blob) != entry.get('sha256'):
                raise ValueError('Cached response hash mismatch')
            payload = load(path)
            provenance[-1]['retrieval'] = entry
            index(payload.get('results', []), str(path))
            for record in payload.get('results', []):
                for lot in notice_lots(record):
                    buyers = lot.pop('buyers')
                    sample_candidates[entry['label']].append({**lot, 'file': str(path),
                        'buyer_ids': sorted(buyers), 'linkage': 'search_candidate_not_exact_contract',
                        'eligible_for_resolution': False})
    queue = []
    for rel, row in rows:
        key = (row['buyerSiret'], row['contractId'])
        item = reconcile(row, declarations[key], notice_index[key])
        item['dataset'] = rel
        item['search_candidate_notice_evidence'] = sample_candidates[row['id']]
        # Preserve dataset order; do not change or propose a production sorting value.
        queue.append(item)
    summary = {'reviewed': len(queue), 'populations': populations,
               'by_dataset': dict(Counter(q['dataset'] for q in queue)),
               'by_buyer': dict(Counter(q['buyer'] for q in queue)),
               'statuses': dict(Counter(q['status'] for q in queue)),
               'over_2x': sum(q['over_2x'] for q in queue),
               'over_2x_by_dataset': dict(Counter(q['dataset'] for q in queue if q['over_2x'])),
               'search_candidates_by_dataset': dict(Counter(q['dataset'] for q in queue if q['search_candidate_notice_evidence'])),
               'with_buyer_portal_declarations': sum(any(d['file'] == 'data/city-portals-raw.json.gz' for d in q['buyer_declarations']) for q in queue),
               'with_exact_buyer_declarations': sum(bool(q['buyer_declarations']) for q in queue),
               'with_search_candidates': sum(bool(q['search_candidate_notice_evidence']) for q in queue),
               'candidate_basis_fields': dict(Counter(v['basis'] for q in queue for n in q['search_candidate_notice_evidence'] for v in n['values'])),
               'notice_basis_fields': dict(Counter(v['basis'] for q in queue for n in q['notice_evidence'] for v in n['values'])),
               'rejected_cached_responses': rejected, 'resolved': 0, 'network_requests': 0,
               'policy': 'Exact buyer role and whole contract reference only; no arithmetic equivalence or replacements'}
    return queue, summary, provenance


def private_run(cache=CACHE):
    base = cache / 'france-amount-disagreements'
    for p in (cache.parent, cache, base):
        if p.is_symlink():
            raise ValueError('Symlinked private output directory')
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not base.resolve().is_relative_to(Path.home().resolve() / '.cache') or base.resolve().is_relative_to(ROOT):
        raise ValueError('Output must be outside repository in home cache')
    base.chmod(0o700)
    return Path(tempfile.mkdtemp(prefix='run-', dir=base))


def save(path, blob):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(blob)


def main():
    queue, summary, provenance = build()
    directory = private_run()
    save(directory / 'queue.jsonl', ''.join(json.dumps(q, ensure_ascii=True) + '\n' for q in queue))
    save(directory / 'summary.json', json.dumps(summary, indent=2) + '\n')
    save(directory / 'provenance.json', json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
