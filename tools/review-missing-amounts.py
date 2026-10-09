#!/usr/bin/env python3
"""Offline exact-ID amount reconciliation; never rebuilds datasets or fetches URLs.

Default private queue: ~/.cache/contract-signals/missing-amounts-review/review.jsonl.
Aggregate stdout contains counts only. Scope: all Ukraine rows (fallback provenance),
zero/null/missing rows in every registered dataset. French notice-only rows are
outside contract-amount scope; DECP initial conflicts never select a value. Source/award/tender amounts are not interchangeable.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = Path.home() / '.cache/contract-signals/missing-amounts-review'


def load_audit():
    spec = importlib.util.spec_from_file_location('amount_audit', ROOT / 'tools/audit-data-quality.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUDIT = load_audit()


def numeric(value):
    if isinstance(value, str):
        try:
            value = float(value.replace(',', '').strip())
        except ValueError:
            return None
    return value if type(value) in (int, float) and math.isfinite(value) else None


def evidence(pointer, value, basis, currency=None, status=None):
    value = value if isinstance(value, dict) else {'amount': value, 'currency': currency}
    return {'pointer': pointer, 'source_amount': value.get('amount'),
            'numeric_amount': numeric(value.get('amount')), 'currency': value.get('currency'),
            'basis': basis, 'source_status': status,
            'vat_included': value.get('valueAddedTaxIncluded')}


def decide(row, matches, values, conflicts):
    """Only same-basis positive amounts can enter the recovery queue; no award substitution."""
    eligible = [v for v in values if v['basis'] in ('contract', 'secop_contract', 'winning_tender_payable')]
    if matches != 1 or conflicts:
        return 'ambiguous_mapping', False
    if len(eligible) != 1:
        return 'raw_source_missing', False
    if row.get('currency') and eligible[0]['currency'] and row['currency'] != eligible[0]['currency']:
        return 'currency_conflict', False
    amount = eligible[0]['numeric_amount']
    if amount is None:
        return 'raw_source_missing' if eligible[0]['source_amount'] is None else 'raw_source_non_numeric', False
    if amount == 0:
        return 'raw_source_zero', False
    if amount < 0:
        return 'raw_source_negative', False
    current = numeric(row.get('amount'))
    if current != amount:
        if not re.fullmatch('[A-Z]{3}', eligible[0]['currency'] or ''):
            return 'source_positive_currency_unresolved', False
        return 'importer_lost_value', True
    return 'retained_positive', False


class Review:
    def __init__(self, root):
        self.root = Path(root)
        self.cache = {}
        self.colombia = None
        self.indexes = {}

    def record_index(self, path, fields, array=False):
        """Retain every counterpart, including identical duplicates; never last-wins."""
        if path not in self.indexes:
            raw, digest = self.json_source(path)
            index = defaultdict(list)
            for i, record in enumerate(raw if array else raw['records']):
                index[tuple(str(record.get(f)) for f in fields)].append((i, record))
            self.indexes[path] = (index, digest)
        return self.indexes[path]

    @staticmethod
    def many(value):
        return value if isinstance(value, list) else [] if value is None else [value]

    @staticmethod
    def text(value):
        return value.get('#text') if isinstance(value, dict) else value

    def boamp_values(self, row, sources, values, conflicts):
        path = 'data/boamp-raw.json.gz'
        index, digest = self.record_index(path, ('idweb',))
        records = index.get((str(row.get('noticeId')),), [])
        matches = 0
        if len(records) != 1:
            conflicts.append('notice_reference_not_unique')
        for i, record in records:
            notice = json.loads(record['donnees']).get('EFORMS', {}).get('ContractAwardNotice', {})
            extensions = self.many(notice.get('ext:UBLExtensions', {}).get('ext:UBLExtension'))
            results = []
            for ext in extensions:
                result = ext.get('ext:ExtensionContent', {}).get('efext:EformsExtension', {}).get('efac:NoticeResult')
                results.extend(self.many(result))
            if len(results) != 1:
                conflicts.append('notice_result_not_unique')
            for result in results:
                for n, lot in enumerate(self.many(result.get('efac:LotResult'))):
                    lotrefs = self.many(lot.get('efac:TenderLot'))
                    if not any(self.text(x.get('cbc:ID')) == row.get('lotId') for x in lotrefs):
                        continue
                    matches += 1
                    pointer = f'/records/{i}/donnees/EFORMS/ContractAwardNotice/NoticeResult/LotResult/{n}'
                    sources.append({'path': path, 'sha256': digest, 'pointer': pointer})
                    if len(lotrefs) != 1 or row['id'] != f"boamp-{record['idweb']}-{row['lotId'].lower()}":
                        conflicts.append('lot_identity_mismatch')
                    if self.text(lot.get('cbc:TenderResultCode')) != 'selec-w':
                        conflicts.append('not_winning_lot_result')
                    refs = [self.text(x.get('cbc:ID')) for x in self.many(lot.get('efac:LotTender'))]
                    contracts = [self.text(x.get('cbc:ID')) for x in self.many(lot.get('efac:SettledContract'))]
                    if contracts != ([row['contractId']] if row.get('contractId') else []):
                        conflicts.append('contract_reference_mismatch')
                    tenders = [(j, t) for j, t in enumerate(self.many(result.get('efac:LotTender')))
                               if self.text(t.get('cbc:ID')) in refs]
                    if len(refs) != 1 or len(tenders) != 1:
                        conflicts.append('winning_tender_reference_not_unique')
                    for j, tender in tenders:
                        totals = self.many(tender.get('cac:LegalMonetaryTotal'))
                        nodes = [node for total in totals for node in self.many(total.get('cbc:PayableAmount'))]
                        if len(totals) > 1 or len(nodes) > 1:
                            conflicts.append('multiple_payable_amounts')
                        for node in nodes or [None]:
                            raw_amount = self.text(node)
                            item = evidence(f'/records/{i}/donnees/NoticeResult/LotTender/{j}/cac:LegalMonetaryTotal/cbc:PayableAmount',
                                            raw_amount, 'winning_tender_payable',
                                            node.get('@currencyID') if isinstance(node, dict) else None,
                                            self.text(lot.get('cbc:TenderResultCode')))
                            # eForms decimals: never reinterpret commas as grouping or decimals.
                            try:
                                amount = float(raw_amount) if type(raw_amount) in (str, int, float) else None
                            except (ValueError, TypeError):
                                amount = None
                            item['numeric_amount'] = amount if amount is not None and math.isfinite(amount) else None
                            values.append(item)
        return matches

    def read_source(self, relative):
        relative = Path(relative)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe raw path')
        if relative not in self.cache:
            blob = (self.root / relative).read_bytes()
            payload = gzip.decompress(blob) if relative.suffix == '.gz' else blob
            self.cache[relative] = (payload, hashlib.sha256(blob).hexdigest())
        return self.cache[relative]

    def json_source(self, path):
        payload, digest = self.read_source(path)
        return json.loads(payload), digest

    def colombia_index(self):
        index = defaultdict(list)
        manifest, _ = self.json_source('data/colombia-secop2/raw/manifest.json')
        for page in manifest['pages']:
            rows, digest = self.json_source(page['file'])
            for i, raw in enumerate(rows):
                buyers = [b for b in manifest['buyers'] if raw.get(b['match']['field']) == b['match']['value']]
                for buyer in buyers:
                    rid = f"secop2-{buyer['key']}-{raw.get('id_contrato') or raw.get('proceso_de_compra') or 'sans-id'}"
                    index[rid].append((page['file'], digest, i, raw))
        self.colombia = index

    def reconcile(self, key, row, duplicate_published_id=False):
        values, sources, conflicts, matches = [], [], [], 0
        if duplicate_published_id:
            conflicts.append('duplicate_published_id')
        for flag in ('initialConflicts', 'modificationConflicts', 'identityAmbiguous'):
            if row.get(flag):
                conflicts.append('published_' + flag)
        def source(path, digest, pointer):
            sources.append({'path': str(path), 'sha256': digest, 'pointer': pointer})
        classification = None
        try:
            if key == 'boamp':
                matches = self.boamp_values(row, sources, values, conflicts)
            elif key in ('cities', 'decp') and row.get('amountSources') is not None:
                # Reconciled with buyer feeds (tools/decp_feeds.py): every published amount is on the record.
                published = [s.get('amount') for s in row['amountSources']]
                for s in row['amountSources']:
                    item = evidence(f"/amountSources/{s['source']}", s.get('amount'), 'published_source_amount', 'EUR')
                    item['numeric_amount'] = s.get('amount')
                    values.append(item)
                known = [a for a in published if a is not None]
                matches = 1
                classification = ('all_sources_missing' if not known else
                                  'sources_disagree_unresolved' if any(a > 10 for a in known) else
                                  'placeholder_only' if any(0 < a <= 10 for a in known) else 'declared_zero')
            elif key in ('cities', 'decp'):
                path = 'data/decp-cities-raw.json' if key == 'cities' else 'data/decp-history-raw.json.gz'
                index, digest = self.record_index(path, ('acheteur_id', 'id'))
                counterparts = index.get((str(row.get('buyerSiret')), str(row.get('contractId'))), [])
                matches = len(counterparts)
                if row['id'] != f"decp-{row.get('buyerSiret')}-{row.get('contractId')}":
                    conflicts.append('importer_id_mismatch')
                parsed = []
                for i, raw in counterparts:
                    source(path, digest, f'/records/{i}')
                    value = raw.get('montant')
                    # Independent research semantics: CDL/INX/blank are unknown;
                    # no comma stripping, negative or nonfinite DECP amounts.
                    try:
                        amount = float(value) if value not in (None, '', 'CDL', 'INX') and type(value) is not bool else None
                    except (ValueError, TypeError):
                        amount = None
                    if amount is not None and (not math.isfinite(amount) or amount < 0):
                        amount = None
                    parsed.append(amount)
                    item = evidence(f'/records/{i}/montant', value, 'initial_counterpart_only', 'EUR')
                    item['numeric_amount'] = amount
                    values.append(item)
                    values.append(evidence(f'/records/{i}/montantmodification', raw.get('montantmodification'), 'modification_context_only', 'EUR'))
                if len(set(parsed)) > 1 and 'amount' in (row.get('initialConflicts') or []) and not duplicate_published_id and 'importer_id_mismatch' not in conflicts:
                    classification = 'unresolved_initial_conflict'
                # Even a unanimous counterpart set is not a DECP recovery candidate.
            elif key in ('tours', 'consultations'):
                path = 'data/tours-notices/raw/api-records.json' if key == 'tours' else 'data/consultations-raw.json'
                index, digest = self.record_index(path, ('idweb',), array=key == 'tours')
                counterparts = index.get((str(row.get('noticeId')),), [])
                matches = len(counterparts)
                for i, raw in counterparts:
                    source(path, digest, f'/{i}' if key == 'tours' else f'/records/{i}')
                expected = (f"tours-notice-{row.get('noticeId')}-{row.get('lotId') or 'unknown-lot'}" if key == 'tours'
                            else f"boamp-consultation-{row.get('noticeId')}")
                if row['id'] != expected:
                    conflicts.append('importer_id_mismatch')
                if matches == 1 and not conflicts:
                    classification = 'not_contract_amount_scope'
            elif key == 'ukraine':
                path = f"data/prozorro/raw/records/{row['tenderID']}.json.gz"
                package, digest = self.json_source(path)
                tender = package['data']
                contracts = [(i, c) for i, c in enumerate(tender.get('contracts') or [])
                             if c.get('id') == row.get('contractInternalId')]
                matches = len(contracts)
                if tender.get('id') != row.get('procedureId') or tender.get('tenderID') != row['tenderID']:
                    conflicts.append('tender_identity_mismatch')
                for i, contract in contracts:
                    pointer = f'/data/contracts/{i}'
                    source(path, digest, pointer)
                    if row['id'] != f"prozorro-{tender['tenderID']}-{contract['id'][:8]}":
                        conflicts.append('importer_id_mismatch')
                    if contract.get('contractID') != row.get('contractId') or contract.get('awardID') != row.get('awardId'):
                        conflicts.append('contract_award_identity_mismatch')
                    values.append(evidence(pointer + '/value', contract.get('value'), 'contract', status=contract.get('status')))
                    awards = [(j, a) for j, a in enumerate(tender.get('awards') or []) if a.get('id') == contract.get('awardID')]
                    if len(awards) != 1:
                        conflicts.append('award_reference_not_unique')
                    for j, award in awards:
                        values.append(evidence(f'/data/awards/{j}/value', award.get('value'), 'award_only', status=award.get('status')))
            elif key == 'uk':
                path = f"data/uk-fts/raw/notices/{row['noticeId']}.json.gz"
                package, digest = self.json_source(path)
                for i, release in enumerate(package.get('releases') or []):
                    if release.get('id') != row['noticeId']:
                        continue
                    if release.get('ocid') != row.get('procedureId'):
                        conflicts.append('procedure_identity_mismatch')
                    for j, award in enumerate(release.get('awards') or []):
                        if award.get('id') != row.get('awardId'):
                            continue
                        matches += 1
                        pointer = f'/releases/{i}/awards/{j}'
                        source(path, digest, pointer)
                        if row['id'] != f"fts-{release['id']}-{award['id'].rsplit('-', 1)[-1]}":
                            conflicts.append('importer_id_mismatch')
                        if (award.get('relatedLots') or [None]) != [row.get('lotId')]:
                            conflicts.append('lot_identity_mismatch')
                        values.append(evidence(pointer + '/value', award.get('value'), 'award_only', status=award.get('status')))
                        values.append(evidence(f'/releases/{i}/tender/value', (release.get('tender') or {}).get('value'), 'tender_only'))
                        contracts = [(n, c) for n, c in enumerate(release.get('contracts') or []) if c.get('awardID') == award['id']]
                        if len(contracts) > 1:
                            conflicts.append('multiple_contracts_for_award_importer_last_wins')
                        for n, contract in contracts:
                            values.append(evidence(f'/releases/{i}/contracts/{n}/value', contract.get('value'), 'contract', status=contract.get('status')))
            elif key == 'colombia':
                if self.colombia is None:
                    self.colombia_index()
                counterparts = self.colombia.get(row['id'], [])
                matches = len(counterparts)
                for path, digest, i, raw in counterparts:
                    source(path, digest, f'/{i}')
                    if raw.get('id_contrato') != row.get('contractId') or raw.get('proceso_de_compra') != row.get('processId'):
                        conflicts.append('contract_process_identity_mismatch')
                    values.append(evidence(f'/{i}/valor_del_contrato', raw.get('valor_del_contrato'), 'secop_contract', 'COP', raw.get('estado_contrato')))
                    for field in ('valor_pagado', 'valor_facturado', 'valor_pendiente_de_ejecucion'):
                        values.append(evidence(f'/{i}/{field}', raw.get(field), 'execution_context_only', 'COP'))
            elif key in ('portugal', 'czechia', 'romania'):
                path = f"data/ted-{key}/raw/notices/{row['noticeId']}.xml.gz"
                payload, digest = self.read_source(path)
                xml = ET.fromstring(payload)
                def children(node, name):
                    return node.findall('./{*}' + name)
                def text(node, name):
                    child = node.find('./{*}' + name)
                    return child.text.strip() if child is not None and child.text else None
                results = [r for r in xml.findall('.//{*}NoticeResult/{*}LotResult') if text(r, 'ID') == row.get('resultId')]
                matches = len(results)
                # Whole-notice context is NOT mapped to this lot/contract or eligible for recovery.
                for i, node in enumerate(xml.iter()):
                    tag = node.tag.rsplit('}', 1)[-1]
                    if tag.endswith('Amount') and tag != 'PayableAmount':
                        values.append(evidence(f'XML-document-order/{i}/{tag}', node.text,
                                               'notice_context_only', node.get('currencyID')))
                for result in results:
                    pointer = f"NoticeResult/LotResult[ID={row.get('resultId')}]"
                    source(path, digest, pointer)
                    lots = children(result, 'TenderLot')
                    if len(lots) != 1 or text(lots[0], 'ID') != row.get('lotId'):
                        conflicts.append('lot_identity_mismatch')
                    if row['id'] != f"ted-{row['noticeId']}-{row['lotId'].lower()}":
                        conflicts.append('importer_id_mismatch')
                    refs = [text(t, 'ID') for t in children(result, 'LotTender')]
                    contracts = [text(c, 'ID') for c in children(result, 'SettledContract')]
                    if contracts != ([row['contractId']] if row.get('contractId') else []):
                        conflicts.append('contract_reference_mismatch')
                    tenders = [t for t in xml.findall('.//{*}NoticeResult/{*}LotTender') if text(t, 'ID') in refs]
                    if len(refs) != 1 or len(tenders) != 1:
                        conflicts.append('winning_tender_reference_not_unique')
                    for tender in tenders:
                        nodes = tender.findall('./{*}LegalMonetaryTotal/{*}PayableAmount')
                        if len(nodes) > 1:
                            conflicts.append('multiple_payable_amounts')
                        for node in nodes or [None]:
                            values.append(evidence(f"NoticeResult/LotTender[ID={text(tender, 'ID')}]/LegalMonetaryTotal/PayableAmount",
                                                   node.text if node is not None else None, 'winning_tender_payable',
                                                   node.get('currencyID') if node is not None else None,
                                                   text(result, 'TenderResultCode')))
            else:
                conflicts.append('unsupported_dataset_mapping')
        except FileNotFoundError:
            conflicts.append('retained_source_file_missing')
        status, candidate = decide(row, matches, values, conflicts)
        if classification:
            status, candidate = classification, False
        contract_values = [v for v in values if v['basis'] == 'contract' and v['numeric_amount'] is not None]
        award_values = [v for v in values if v['basis'] == 'award_only' and v['numeric_amount'] is not None]
        basis_conflicts = ['contract_award_amount_or_currency_differs'] if any(
            (c['numeric_amount'], c['currency']) != (a['numeric_amount'], a['currency'])
            for c in contract_values for a in award_values) else []
        return {'dataset': key, 'id': row['id'], 'current_amount_category': AUDIT.amount_category(row),
                'current_amount': row.get('amount'), 'current_currency': row.get('currency'),
                'current_data_status': row.get('dataStatus'), 'current_contract_status': row.get('contractStatus'),
                'exact_match_count': matches, 'sources': sources, 'source_values': values,
                'conflicts': sorted(set(conflicts)), 'basis_conflicts': basis_conflicts,
                'status': status, 'recovery_candidate': candidate,
                'award_fallback_observed': any(v['basis'] == 'award_only' and v['numeric_amount'] == numeric(row.get('amount')) and v['numeric_amount'] is not None for v in values)
                and not any(v['basis'] == 'contract' and v['numeric_amount'] == numeric(row.get('amount')) for v in values)}


def review(root):
    audit, _ = AUDIT.inventory(root)
    helper, queue, counts = Review(root), [], {}
    scoped = set(audit['datasets'])
    hashes = {'script.js': hashlib.sha256((Path(root) / 'script.js').read_bytes()).hexdigest()}
    for key, dataset in audit['datasets'].items():
        payload = (Path(root) / dataset['path']).read_bytes()
        hashes[dataset['path']] = hashlib.sha256(payload).hexdigest()
        rows = json.loads(payload)
        gaps = [r for r in rows if AUDIT.amount_category(r) in ('missing', 'null', 'zero_declared')]
        selected = rows if key == 'ukraine' else gaps if key in scoped else []
        published_ids = Counter(r.get('id') for r in rows)
        entries = [helper.reconcile(key, row, published_ids[row.get('id')] > 1) for row in selected]
        queue.extend(entries)
        counts[key] = {'zero': dataset['amounts']['zero_declared'],
                       'absent': dataset['amounts']['missing'] + dataset['amounts']['null'],
                       'reviewed_rows': len(entries), 'unreviewed_gap_rows': len(gaps) if key not in scoped else 0,
                       'statuses': dict(sorted(Counter(e['status'] for e in entries).items())),
                       'exact_unique_matches': sum(e['exact_match_count'] == 1 and not e['conflicts'] for e in entries),
                       'recovery_candidates': sum(e['recovery_candidate'] for e in entries),
                       'award_fallback_observed': sum(e['award_fallback_observed'] for e in entries),
                       'contract_award_basis_disagreements': sum(bool(e['basis_conflicts']) for e in entries),
                       'rows_with_positive_excluded_context': sum(any(v['basis'] in ('award_only', 'tender_only', 'execution_context_only', 'notice_context_only')
                                                                    and v['numeric_amount'] is not None and v['numeric_amount'] > 0
                                                                    for v in e['source_values']) for e in entries)}
    hashes.update({str(path): digest for path, (_, digest) in helper.cache.items()})
    return {'schema_version': 2, 'scope': 'All registered zero/absent rows; additionally Ukraine all rows for fallback provenance',
            'basis_policy': 'No award, modification or ceiling substitution. BOAMP/TED winning-tender PayableAmount is its existing explicit basis, not a signed contract value. DECP counterpart sets never select values; Tours/consultations are notice-only.',
            'input_sha256': dict(sorted(hashes.items())),
            'gap_rows_accounted_for': sum(c['zero'] + c['absent'] - c['unreviewed_gap_rows'] for c in counts.values()),
            'datasets': counts}, queue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--review-dir', type=Path, default=DEFAULT_QUEUE)
    args = parser.parse_args()
    # Keep sensitive queue outside the repository / website, including alternate roots.
    directory = args.review_dir.expanduser().resolve()
    for root in (ROOT.resolve(), args.root.resolve()):
        if directory == root or root in directory.parents:
            parser.error('Private review directory must be outside the repository')
    report, queue = review(args.root)
    AUDIT.write_queue(args.review_dir, queue)
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
