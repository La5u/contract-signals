#!/usr/bin/env python3
"""Offline FTS accuracy gate. Reads saved inputs; never imports/fetches/rebuilds data.

Default stdout is aggregate JSON only. --private-dir optionally writes a minimized
exact-ID audit (all linked contracts, no names/contact text) outside the repository.
Ambiguous identities or multiple linked contracts are excluded, never resolved.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def exclusion(award):
    if award.get('status') != 'active':
        return 'inactive'
    if len(award.get('suppliers') or []) != 1:
        return 'supplier_multiplicity'
    if len(award.get('relatedLots') or []) > 1:
        return 'lot_multiplicity'
    return None


def day(value):
    return (value or '')[:10] or None


def value_pair(value):
    return ((value or {}).get('amount'), (value or {}).get('currency'))


def inspect_row(row, release, award):
    """Exact identity checks followed by enumeration, not a contracts dictionary."""
    flags = []
    buyers = [p.get('id') for p in release.get('parties') or []
              if 'buyer' in (p.get('roles') or [])]
    supplier_ids = [s.get('id') for s in award.get('suppliers') or []]
    published_supplier_ids = [s.get('id') for s in row.get('supplierIds') or []
                              if s.get('identifierType') == 'GB-FTS']
    lots = award.get('relatedLots') or []
    expected_id = f"fts-{release.get('id')}-{str(award.get('id')).rsplit('-', 1)[-1]}"
    checks = {
        'row_id': row.get('id') == expected_id,
        'procedure_id': row.get('procedureId') == release.get('ocid'),
        'buyer_id': len(buyers) == 1 and row.get('buyerId') == buyers[0],
        'supplier_id': len(supplier_ids) == 1 and supplier_ids == published_supplier_ids,
        'lot_id': len(lots) <= 1 and row.get('lotId') == (lots[0] if lots else None),
        'eligibility': exclusion(award) is None,
    }
    flags.extend('identity_' + k for k, ok in checks.items() if not ok)
    contracts = [c for c in release.get('contracts') or []
                 if c.get('awardID') == award.get('id')]
    # Last is inspected ONLY to diagnose the existing importer, not to choose truth.
    last = contracts[-1] if contracts else {}
    selected_value = last.get('value') or award.get('value') or {}
    amount_source = 'contract' if last.get('value') else 'award' if award.get('value') else 'missing'
    date_source = ('contract' if last.get('dateSigned') else
                   'award' if award.get('date') else 'release' if release.get('date') else 'missing')
    selected_date = day(last.get('dateSigned') or award.get('date') or release.get('date'))
    if value_pair(selected_value) != (row.get('amount'), row.get('currency')):
        flags.append('published_value_differs_from_importer_rule')
    if selected_date != row.get('date'):
        flags.append('published_date_differs_from_importer_rule')
    if day(release.get('date')) != row.get('publicationDate'):
        flags.append('publication_date_mismatch')
    if len(contracts) > 1:
        flags.append('multiple_contracts_excluded')
        if len({value_pair(c.get('value')) for c in contracts}) > 1:
            flags.append('multiple_contract_values_conflict')
        if len({day(c.get('dateSigned')) for c in contracts}) > 1:
            flags.append('multiple_contract_dates_conflict')
    if contracts and last.get('value') and award.get('value'):
        cv, av = value_pair(last['value']), value_pair(award['value'])
        if cv[0] != av[0]:
            flags.append('contract_award_amount_difference')
        if cv[1] != av[1]:
            flags.append('contract_award_currency_conflict')
    if selected_value.get('amount') is None and award.get('value', {}).get('amount') is not None and last.get('value'):
        flags.append('partial_contract_value_blocks_award_amount')
    if selected_value.get('amount') is not None and not selected_value.get('currency'):
        flags.append('selected_amount_without_currency')
    if selected_value.get('currency') and selected_value.get('amount') is None:
        flags.append('selected_currency_without_amount')
    if amount_source == 'award' and 'Contract value' in (row.get('amountBasis') or ''):
        flags.append('award_value_labelled_contract_basis')
    if selected_value.get('amount') == 0:
        flags.append('selected_zero')
    if selected_value.get('amount') is None:
        flags.append('selected_missing_amount')
    return {
        'rowId': row.get('id'), 'noticeId': release.get('id'), 'awardId': award.get('id'),
        'procedureId': release.get('ocid'), 'buyerId': row.get('buyerId'),
        'supplierIds': published_supplier_ids, 'lotId': row.get('lotId'),
        'identityChecks': checks, 'linkedContractCount': len(contracts),
        'linkedContracts': [{'id': c.get('id'), 'awardID': c.get('awardID'),
                             'value': dict(zip(('amount', 'currency'), value_pair(c.get('value')))),
                             'valuePresent': bool(c.get('value')), 'dateSigned': c.get('dateSigned')}
                            for c in contracts],
        'awardValue': dict(zip(('amount', 'currency'), value_pair(award.get('value')))),
        'awardValuePresent': bool(award.get('value')), 'awardDate': award.get('date'),
        'publishedValue': {'amount': row.get('amount'), 'currency': row.get('currency')},
        'publishedDate': row.get('date'), 'amountSource': amount_source, 'dateSource': date_source,
        'importerRuleValueMatches': value_pair(selected_value) == (row.get('amount'), row.get('currency')),
        'importerRuleDateMatches': selected_date == row.get('date'),
        'gateExcluded': bool(not all(checks.values()) or len(contracts) > 1), 'flags': flags,
    }


def audit(root=ROOT):
    root = Path(root)
    raw = root / 'data/uk-fts/raw'
    published_path = root / 'data/uk-fts.json'
    manifest_path = raw / 'manifest.json'
    rows = json.loads(published_path.read_bytes())
    manifest = json.loads(manifest_path.read_bytes())
    wanted = {b['id'] for b in manifest['buyers']}
    counts = Counter(published_rows=len(rows))
    raw_multiplicity, retained_multiplicity, excluded = Counter(), Counter(), Counter()
    index = defaultdict(list)
    eligible = Counter()
    raw_contract_inventory = []
    digest = hashlib.sha256()
    paths = sorted((raw / 'notices').glob('*.json.gz'))
    files = {p.name.removesuffix('.json.gz') for p in paths}
    counts['raw_files'] = len(paths)
    counts['manifest_notices'] = len(manifest['noticeIds'])
    counts['manifest_missing_files'] = len(set(manifest['noticeIds']) - files)
    counts['unmanifested_files'] = len(files - set(manifest['noticeIds']))
    for path in paths:
        content = path.read_bytes()
        digest.update(path.name.encode() + b'\0' + hashlib.sha256(content).digest())
        for release in json.loads(gzip.decompress(content))['releases']:
            counts['raw_releases'] += 1
            counts['release_filename_mismatch'] += release.get('id') != path.name.removesuffix('.json.gz')
            awards = release.get('awards') or []
            contracts = release.get('contracts') or []
            counts['raw_awards'] += len(awards)
            counts['raw_contracts'] += len(contracts)
            award_ids = Counter(a.get('id') for a in awards)
            counts['duplicate_award_ids'] += sum(n - 1 for n in award_ids.values())
            contract_ids = Counter(c.get('id') for c in contracts)
            counts['duplicate_contract_ids'] += sum(n - 1 for n in contract_ids.values())
            buyers = [p.get('id') for p in release.get('parties') or [] if 'buyer' in (p.get('roles') or [])]
            in_cohort = bool(buyers and buyers[0] in wanted)
            counts['other_buyer_releases'] += not in_cohort
            for c in contracts:
                counts['orphan_contracts'] += c.get('awardID') not in award_ids
                raw_contract_inventory.append({'noticeId': release.get('id'), 'contractId': c.get('id'),
                                               'awardID': c.get('awardID')})
            for award in awards:
                key = (release.get('id'), award.get('id'))
                index[key].append((release, award))
                n = sum(c.get('awardID') == award.get('id') for c in contracts)
                raw_multiplicity[n] += 1
                if in_cohort:
                    reason = exclusion(award)
                    if reason:
                        excluded[reason] += 1
                    else:
                        eligible[key] += 1
                        retained_multiplicity[n] += 1
    details = []
    row_keys = Counter((r.get('noticeId'), r.get('awardId')) for r in rows)
    row_ids = Counter(r.get('id') for r in rows)
    counts['duplicate_published_row_ids'] = sum(n - 1 for n in row_ids.values())
    counts['eligible_raw_awards'] = sum(eligible.values())
    counts['eligible_raw_awards_without_published_row'] = sum(n for k, n in eligible.items() if k not in row_keys)
    for row in rows:
        key = (row.get('noticeId'), row.get('awardId'))
        candidates = index[key]
        if len(candidates) != 1 or row_keys[key] != 1 or row_ids[row.get('id')] != 1:
            details.append({'rowId': row.get('id'), 'noticeId': key[0], 'awardId': key[1],
                            'gateExcluded': True, 'flags': ['nonunique_or_missing_exact_identity']})
            continue
        details.append(inspect_row(row, *candidates[0]))
    flags = Counter(f for d in details for f in d['flags'])
    summary = {
        'counts': dict(sorted(counts.items())),
        'raw_awards_by_linked_contract_count': dict(sorted(raw_multiplicity.items())),
        'eligible_awards_by_linked_contract_count': dict(sorted(retained_multiplicity.items())),
        'raw_exclusion_reasons_first_applicable': dict(sorted(excluded.items())),
        'published_by_linked_contract_count': dict(sorted(Counter(d.get('linkedContractCount', 'unmatched') for d in details).items(), key=lambda x: str(x[0]))),
        'published_amount_sources': dict(sorted(Counter(d.get('amountSource', 'unmatched') for d in details).items())),
        'published_date_sources': dict(sorted(Counter(d.get('dateSource', 'unmatched') for d in details).items())),
        'published_currencies': dict(sorted(Counter(r.get('currency') or 'missing' for r in rows).items())),
        'published_amount_basis_labels': dict(sorted(Counter(r.get('amountBasis') or 'missing' for r in rows).items())),
        'published_amount_categories': dict(sorted(Counter(
            'missing' if r.get('amount') is None else 'zero' if r['amount'] == 0 else
            'positive' if isinstance(r['amount'], (int, float)) and r['amount'] > 0 else 'other'
            for r in rows).items())),
        'published_awards_with_value_object': sum(d.get('awardValuePresent', False) for d in details),
        'published_contracts_with_value_object': sum(c['valuePresent'] for d in details for c in d.get('linkedContracts', [])),
        'published_rows_with_missing_date': sum(r.get('date') is None for r in rows),
        'flags': dict(sorted(flags.items())),
        'gate_excluded_rows': sum(d['gateExcluded'] for d in details),
        'importer_rule_value_matches': sum(d.get('importerRuleValueMatches', False) for d in details),
        'importer_rule_date_matches': sum(d.get('importerRuleDateMatches', False) for d in details),
        'sha256': {'published': hashlib.sha256(published_path.read_bytes()).hexdigest(),
                   'manifest': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                   'raw_files_name_nul_binary_sha256_sequence': digest.hexdigest()},
    }
    return summary, details, raw_contract_inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--private-dir', type=Path)
    args = parser.parse_args()
    summary, rows, contracts = audit(args.root)
    if args.private_dir:
        import os
        directory = args.private_dir.expanduser().resolve()
        cache = (Path.home() / '.cache/contract-signals/accuracy-review').resolve()
        if not directory.is_relative_to(cache) or directory.is_relative_to(args.root.resolve()):
            parser.error('--private-dir must be under ~/.cache/contract-signals/accuracy-review and outside the repo')
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
        # Exclusive creation: never overwrite earlier research/user files.
        path = directory / 'uk-contract-values.json'
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump({'summary': summary, 'rows': rows, 'rawContractLinks': contracts}, stream, indent=2)
            stream.write('\n')
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
