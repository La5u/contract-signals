#!/usr/bin/env python3
"""Offline, aggregate-only availability audit; run with the private cache venv.

No download, cohort export, amount sums, or conflict resolution. Only the six
preregistered buyers are retained in memory while the national parquet streams.
"""
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
import math
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / '.cache/contract-signals/decp-national'
CITIES = dict(zip(
    ['21210231300013', '21330063500017', '21350238800019',
     '21370261600011', '21380185500015', '21440109300015'],
    ['Dijon', 'Bordeaux', 'Rennes', 'Tours', 'Grenoble', 'Nantes']))
# Procurement state, not publication identity, current-state flag, names or
# geographic enrichment. Raw holder identity is significant (no SIREN collapse).
STATE_FIELDS = [
    'nature', 'objet', 'montant', 'codeCPV', 'procedure', 'techniques',
    'dureeMois', 'dureeRestanteMois', 'offresRecues', 'dateNotification',
    'datePublicationDonnees', 'formePrix', 'typesPrix', 'idAccordCadre',
    'titulaire_id', 'titulaire_typeIdentifiant', 'type', 'attributionAvance',
    'tauxAvance', 'marcheInnovant', 'modalitesExecution',
    'considerationsSociales', 'considerationsEnvironnementales', 'ccag',
    'sousTraitanceDeclaree', 'typeGroupementOperateurs', 'origineUE',
    'origineFrance', 'lieuExecution_code', 'lieuExecution_typeCode',
    'montant_rationalise', 'montant_anomalie', 'montant_anomalie_raisons']
COLUMNS = ['acheteur_id', 'id', 'modification_id', 'sourceDataset'] + STATE_FIELDS


def missing(value):
    return value is None or (isinstance(value, str) and not value.strip()) or (
        isinstance(value, float) and not math.isfinite(value))


def fingerprint(value):
    # Digests never leave memory or appear in output. Missing is distinct from
    # populated zero/False; empty strings and nonfinite numbers are missing.
    if missing(value):
        return None
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, default=str,
                                    allow_nan=False).encode()).digest()


def year(value):
    if missing(value):
        return 'missing'
    try:
        return str(date.fromisoformat(str(value)[:10]).year)
    except ValueError:
        return 'invalid'


def version(row):
    mid = row.get('modification_id')
    if mid == 0:
        return 'initial'
    if mid is not None and mid > 0:
        return 'modification'
    return 'unversioned'


def batches(source, batch_size):
    if isinstance(source, pa.Table):
        columns = [c for c in COLUMNS if c in source.column_names]
        yield from source.select(columns).to_batches(max_chunksize=batch_size)
    else:
        parquet = pq.ParquetFile(source)
        absent = set(COLUMNS) - set(parquet.schema_arrow.names)
        if absent:
            raise ValueError('Required parquet columns missing: ' + ', '.join(sorted(absent)))
        yield from parquet.iter_batches(batch_size=batch_size, columns=COLUMNS)


def counters():
    return {'rows': 0, 'row_types': Counter(), 'sources': Counter(),
            'notification_years': Counter(), 'missing_identity_rows': 0}


def audit(source, batch_size=32768):
    cities = {b: {'all': counters(), 'window': counters(), 'groups': {}}
              for b in CITIES}
    for batch in batches(source, batch_size):
        selected = batch.filter(pc.is_in(batch.column('acheteur_id'),
                                       value_set=pa.array(list(CITIES))))
        for row in selected.to_pylist():
            city = cities[row['acheteur_id']]
            y, kind = year(row.get('dateNotification')), version(row)
            cid = row.get('id')
            no_id = missing(cid)
            src = row.get('sourceDataset')
            src = 'missing' if missing(src) else src
            for scope in ['all'] + (['window'] if y == '2023' else []):
                count = city[scope]
                count['rows'] += 1
                count['row_types'][kind] += 1
                count['sources'][src] += 1
                count['notification_years'][y] += 1
                count['missing_identity_rows'] += int(no_id)
            # Missing IDs are ungroupable, not silently combined into a contract.
            if no_id:
                continue
            group = city['groups'].setdefault(fingerprint(cid),
                {'years': set(), 'initial_years': set(), 'initial': [], 'types': Counter()})
            group['years'].add(y)
            group['types'][kind] += 1
            if kind == 'initial':
                group['initial_years'].add(y)
                group['initial'].append(tuple(fingerprint(row.get(f)) for f in STATE_FIELDS))

    result = {}
    for buyer, city in cities.items():
        groups = list(city['groups'].values())
        candidates = [g for g in groups if '2023' in g['years']]
        summary = Counter({k: 0 for k in [
            'initial_groups', 'no_initial_groups', 'unversioned_only_groups',
            'groups_with_modifications', 'single_initial_state_groups',
            'conflicting_initial_groups', 'duplicate_initial_rows',
            'groups_with_duplicate_initial_states', 'initial_rows_all_years',
            'groups_spanning_notification_years', 'groups_with_initial_outside_window',
            'groups_with_initial_in_window', 'groups_with_missing_or_invalid_initial_date',
            'single_initial_state_in_window_groups']})
        fields = {f: Counter({'missing_groups': 0, 'populated_groups': 0,
                              'missing_and_populated_groups': 0,
                              'conflicting_populated_values_groups': 0,
                              'any_difference_groups': 0}) for f in STATE_FIELDS}
        for group in candidates:
            initial = group['initial']
            states = set(initial)
            summary['initial_rows_all_years'] += len(initial)
            summary['initial_groups' if initial else 'no_initial_groups'] += 1
            summary['unversioned_only_groups'] += int(set(group['types']) == {'unversioned'})
            summary['groups_with_modifications'] += int(group['types']['modification'] > 0)
            summary['duplicate_initial_rows'] += len(initial) - len(states)
            summary['groups_with_duplicate_initial_states'] += int(len(initial) > len(states))
            summary['conflicting_initial_groups'] += int(len(states) > 1)
            summary['single_initial_state_groups'] += int(len(states) == 1)
            summary['single_initial_state_in_window_groups'] += int(
                len(states) == 1 and group['initial_years'] == {'2023'})
            summary['groups_with_initial_in_window'] += int('2023' in group['initial_years'])
            summary['groups_with_initial_outside_window'] += int(
                bool(group['initial_years'] - {'2023', 'missing', 'invalid'}))
            summary['groups_with_missing_or_invalid_initial_date'] += int(
                bool(group['initial_years'] & {'missing', 'invalid'}))
            summary['groups_spanning_notification_years'] += int(
                len(group['years'] - {'missing', 'invalid'}) > 1)
            if not initial:
                continue
            for i, field in enumerate(STATE_FIELDS):
                values = {s[i] for s in states}
                populated = values - {None}
                counts = fields[field]
                counts['missing_groups'] += int(None in values)
                counts['populated_groups'] += int(bool(populated))
                counts['missing_and_populated_groups'] += int(None in values and bool(populated))
                counts['conflicting_populated_values_groups'] += int(len(populated) > 1)
                counts['any_difference_groups'] += int(len(values) > 1)
        result[CITIES[buyer]] = {
            'all_years': {**city['all'], 'distinct_buyer_contract_groups': len(groups)},
            'notification_2023': {**city['window'],
                'distinct_buyer_contract_groups': len(candidates),
                # Each missing-ID row is an unresolved identity, not a unique contract.
                'missing_identity_groups': None if city['window']['missing_identity_rows'] else 0},
            'candidate_groups_all_rows': dict(summary),
            'initial_field_diagnostics': fields}
    return {
        'scope': 'Six preregistered municipalities; notification [2023-01-01, 2024-01-01)',
        'method': {
            'initial': 'modification_id=0; positive=modification; null/other=unversioned',
            'candidate': 'Known buyer+contract identity with any 2023 notification; all its rows inspected',
            'state': 'All listed procurement fields; supplier and subject fingerprinted privately; metadata ignored',
            'missing_identity_groups': 'Unknown (null) when IDs missing; rows counted separately, never deduplicated',
            'caution': 'Conflicts are not resolved; differing holders may be coholders or changed suppliers. No completeness claim, amount sums or cohort integration.',
            'field_counts': 'Initial candidate groups only; missing/populated overlap. Counts are not additive.'},
        'cities': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parquet', type=Path, default=CACHE / 'decp.parquet')
    parser.add_argument('--output', type=Path, default=CACHE / 'france-2023-backfill-audit.json')
    args = parser.parse_args()
    plan = json.loads((ROOT / 'data/expansion-plan.json').read_text())
    registered = next(w['buyerSirets'] for w in plan['workstreams'] if w['id'] == 'france-backfill')
    if set(registered) != set(CITIES):
        parser.error('Preregistered buyer scope differs; review explicitly before auditing')
    if args.output.resolve() == args.parquet.resolve():
        parser.error('Output must not overwrite input parquet')
    report = audit(args.parquet)
    with args.parquet.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    report['schema_version'] = 1
    report['source_snapshot'] = {'filename': args.parquet.name,
                                 'bytes': args.parquet.stat().st_size,
                                 'sha256': digest}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    args.output.chmod(0o600)
    print('Aggregate audit written to', args.output)


if __name__ == '__main__':
    main()
