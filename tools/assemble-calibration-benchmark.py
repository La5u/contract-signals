#!/usr/bin/env python3
"""Assemble a local, nonrepresentative review benchmark; never fetch or fit."""
import argparse
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

TARGETS = ('corruption', 'fraud', 'irregularity')
STATUSES = {'corroborated-multi-field-match', 'tentative-multi-field-match'}
FIELDS = ('id', 'project_id', 'bid_reference_no', 'procurement_group',
          'method_code', 'method_name', 'signing_date', 'source_url', 'public_source_url', 'response_url',
          'record_type', 'notice_date', 'source_documents', 'conflicting_source_values')


def measurements(row):
    price = row.get('signed_contract_price') or {}
    raw = price.get('amount')
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float, Decimal)) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', str(raw)):
        raise ValueError('amount-missing-or-malformed')
    try:
        amount = Decimal(str(raw))
    except InvalidOperation:
        raise ValueError('amount-missing-or-malformed') from None
    if not amount.is_finite() or amount <= 0:
        raise ValueError('amount-not-positive')
    currency = price.get('currency')
    if not isinstance(currency, str) or not re.fullmatch(r'[A-Z]{3}', currency):
        raise ValueError('currency-missing-or-malformed')
    raw_date = row.get('signing_date')
    if not isinstance(raw_date, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw_date):
        raise ValueError('signing-date-missing-or-malformed')
    try:
        day = date.fromisoformat(raw_date)
    except ValueError:
        raise ValueError('signing-date-missing-or-malformed') from None
    return amount, currency, day


def assemble(manifest, pool, pool_sha256, case_manifest_sha256=None):
    documents = manifest.get('documentary_records', [])
    if not isinstance(documents, list):
        raise ValueError('documentary_records must be a list')
    for record in documents:
        if not isinstance(record, dict) or any(not isinstance(record.get(k), str) or not record[k].strip() for k in ('id', 'project_id', 'bid_reference_no')) or record.get('record_type') != 'documentary-contract':
            raise ValueError('invalid documentary record identity/type')
        sources = record.get('source_documents')
        if not isinstance(sources, list) or not sources:
            raise ValueError('documentary record requires source_documents')
        for source_document in sources:
            if not isinstance(source_document, dict):
                raise ValueError('invalid documentary source')
            url = source_document.get('url', source_document.get('source_url'))
            citation = source_document.get('citation')
            if not isinstance(url, str) or not re.fullmatch(r'https?://[^\s]+', url) or not isinstance(citation, str) or not citation.strip():
                raise ValueError('documentary source requires URL and citation')
    source = sorted(pool['rows'] + documents, key=lambda r: (str(r.get('id')), json.dumps(r, sort_keys=True)))
    cases = manifest['cases']

    def case_record_id(case):
        return case.get('record_id') if 'record_id' in case else case.get('notice_id')

    excluded = {case_record_id(c) for c in cases if case_record_id(c) is not None}
    counts = Counter(r.get('id') for r in source if r.get('id') is not None)
    def event(r):
        return tuple(r.get(k) for k in ('project_id', 'bid_reference_no', 'signing_date'))

    events = Counter(event(r) for r in source if all(event(r)))
    declared_members = set()
    declared_keys = set()
    for group in pool.get('duplicate_groups', []):
        if not isinstance(group, dict):
            continue  # No identifiable affected rows: do not implicate unrelated rows.
        key = group.get('key')
        if isinstance(key, list) and len(key) == 3 and all(key):
            declared_keys.add(tuple(key))
        for index in group.get('row_indices', []):
            if type(index) is int and 0 <= index < len(pool['rows']):
                declared_members.add(id(pool['rows'][index]))
        for notice in group.get('ids', group.get('notice_ids', [])):
            declared_members.update(id(r) for r in source if r.get('id') == notice)
    case_counts = Counter(case_record_id(c) for c in cases if case_record_id(c) is not None)

    def ambiguity(r):
        reasons = []
        if counts[r.get('id')] > 1 or case_counts[r.get('id')] > 1:
            reasons.append('duplicate-notice')
        if all(event(r)) and events[event(r)] > 1:
            reasons.append('duplicate-contract-event')
        if any('duplicat' in str(f).lower() or 'group' in str(f).lower() or 'unresolved' in str(f).lower() for f in r.get('validation_flags', [])) or r.get('unresolved_grouping'):
            reasons.append('unresolved-grouping')
        # External duplicate-group declarations cannot be assumed resolved.
        if id(r) in declared_members or event(r) in declared_keys:
            reasons.append('pool-duplicate-grouping-unresolved')
        return reasons

    rows, pending, rejections = [], [], []
    candidates = {}
    for case in sorted(cases, key=lambda c: c['case_id']):
        resolved_id = case_record_id(case)
        matches = [r for r in source if resolved_id is not None and r.get('id') == resolved_id]
        documentary = any(r.get('record_type') == 'documentary-contract' for r in matches)
        supported = case.get('link_status') in STATUSES and (not documentary or case.get('link_status') == 'corroborated-multi-field-match')
        if not supported or not matches:
            pending.append({k: case.get(k) for k in ('case_id', 'record_id', 'notice_id', 'project_id', 'borrower_contract_reference', 'link_status')} | {'reason': 'unsupported-link-status' if not supported else 'notice-not-in-local-pool'})
            continue
        for r in matches:
            if r.get('project_id') != case.get('project_id') or not case.get('borrower_contract_reference') or r.get('bid_reference_no') != case['borrower_contract_reference']:
                raise ValueError(f"{case['case_id']}: project/reference conflict for {resolved_id}")
        for record in matches:
            if case.get('expected_signing_date') is not None and case['expected_signing_date'] != record.get('signing_date'):
                raise ValueError(f"{case['case_id']}: expected signing date conflict")
        r = sorted(matches, key=lambda x: json.dumps(x, sort_keys=True))[0]
        flags = ambiguity(r)
        labels = {t: None for t in TARGETS}
        if case['link_status'] == 'corroborated-multi-field-match' and not flags:
            for t in TARGETS:
                value = case.get('labels', {}).get(t)
                if value is not None and type(value) is not bool:
                    raise ValueError(f"{case['case_id']}: invalid {t} label")
                labels[t] = value
        out = {k: r.get(k) for k in FIELDS}
        out.update(membership='case', case_id=case['case_id'], link_status=case['link_status'], labels=labels, grouping_flags=flags,
                   signed_contract_price=r.get('signed_contract_price'), decision_url=case.get('decision_url'))
        out.update({k: case.get(k) for k in ('review_scope', 'finding_standard', 'finding_scope', 'limitations', 'link_basis', 'decision_paragraphs')})
        rows.append(out)
        try:
            amount, currency, day = measurements(r)
        except ValueError as exc:
            rejections.append({'case_id': case['case_id'], 'notice_id': r['id'], 'reason': str(exc)})
            continue
        eligible = []
        for candidate in source:
            if candidate.get('id') in excluded or candidate.get('bid_reference_no') == r.get('bid_reference_no'):
                continue
            if candidate.get('project_id') != r.get('project_id') or not r.get('procurement_group') or candidate.get('procurement_group') != r['procurement_group']:
                continue
            if candidate.get('review_status') != 'unreviewed-comparison-candidate':
                continue
            try:
                other, cur, signed = measurements(candidate)
            except ValueError as exc:
                rejections.append({'case_id': case['case_id'], 'notice_id': candidate.get('id'), 'reason': str(exc)})
                continue
            ratio, days = other / amount, abs((signed - day).days)
            if cur != currency or not Decimal('0.25') <= ratio <= Decimal('4') or days > 366:
                continue
            eligible.append((abs(ratio.ln()), days, candidate['id'], json.dumps(candidate, sort_keys=True), candidate))
        seen = set()
        for _, days, notice, _, candidate in sorted(eligible):
            if notice in seen:
                continue
            seen.add(notice)
            out = candidates.setdefault(notice, {k: candidate.get(k) for k in FIELDS} | {
                'membership': 'comparison-candidate', 'labels': {t: None for t in TARGETS},
                'signed_contract_price': candidate['signed_contract_price'], 'grouping_flags': ambiguity(candidate), 'matched_cases': []})
            out['matched_cases'].append({'case_id': case['case_id'], 'price_ratio': str(measurements(candidate)[0] / amount), 'date_distance_days': days})
            if len(seen) == 12:
                break
    rows.extend(candidates[k] for k in sorted(candidates))
    eligibility = {}
    for t in TARGETS:
        positive = sum(r['labels'][t] is True for r in rows)
        negative = sum(r['labels'][t] is False for r in rows)
        eligibility[t] = {'known_positives': positive, 'known_negatives': negative, 'unknown': len(rows) - positive - negative, 'has_both_label_classes': bool(positive and negative), 'ready_for_fit': False,
                          'readiness_reason': 'Benchmark requirements not specified or reviewed; comparisons unreviewed and class/sample adequacy not validated.'}
    return {'schema_version': 1, 'rows': rows, 'row_count': len(rows), 'pending_links': pending,
            'selection_rejections': rejections, 'eligibility': eligibility,
            'ready_for_fit': False,
            'readiness_reason': 'Benchmark requirements not specified or reviewed; comparisons unreviewed and class/sample adequacy not validated.',
            'source_provenance': {'pool_sha256': pool_sha256, 'case_manifest_sha256': case_manifest_sha256, 'responses': [{k: r.get(k) for k in ('url', 'retrieved_at_utc', 'sha256_raw_response')} for r in pool.get('responses', [])], 'documentary_records': [{'id': r['id'], 'source_documents': r['source_documents']} for r in documents]},
            'limitations': ['Local inputs only; no network and no model fit.', 'Nonrepresentative selection: selected pages, not all project contracts.', 'Unreviewed comparisons have unknown outcomes, never clean/negative by absence of a case.', 'No procurement-method matching; explicit methods retained for later review.', 'Duplicate/grouping flags prevent case outcome attribution; no certified unique-event count.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cases', 'pool', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    raw = Path(args.pool).read_bytes()
    case_raw = Path(args.cases).read_bytes()
    try:
        result = assemble(json.loads(case_raw), json.loads(raw), hashlib.sha256(raw).hexdigest(), hashlib.sha256(case_raw).hexdigest())
    except ValueError as exc:
        parser.error(str(exc))
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'rows': result['row_count'], 'cases': sum(r['membership'] == 'case' for r in result['rows']), 'candidates': sum(r['membership'] == 'comparison-candidate' for r in result['rows']), 'pending_links': len(result['pending_links']), 'ready_for_fit': result['ready_for_fit']}))


if __name__ == '__main__':
    main()
