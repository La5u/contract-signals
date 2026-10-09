"""Synthetic-only tests; no national cache or network needed."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:  # optional analysis dependency, absent from CI
    raise unittest.SkipTest('pyarrow unavailable: France 2023 backfill audit not tested')

SPEC = importlib.util.spec_from_file_location(
    'france_audit', Path(__file__).resolve().parents[1] / 'tools/audit-france-2023-backfill.py')
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
DIJON, TOURS = list(audit.CITIES)[0], list(audit.CITIES)[3]


def row(cid='private-contract', **changes):
    record = {f: None for f in audit.COLUMNS}
    record.update(acheteur_id=DIJON, id=cid, modification_id=0,
                  dateNotification='2023-06-01', montant=100.0,
                  titulaire_id='private-supplier', titulaire_typeIdentifiant='SIRET',
                  objet='private-subject', sourceDataset='source-a')
    record.update(changes)
    return record


def report(rows, city='Dijon'):
    return audit.audit(pa.Table.from_pylist(rows), batch_size=1)['cities'][city]


class BackfillAuditTests(unittest.TestCase):
    def test_duplicate_metadata_ignored_and_privacy(self):
        rows = [row(uid='one', sourceFile='one', donneesActuelles=False),
                row(uid='two', sourceFile='two', donneesActuelles=True,
                    sourceDataset='source-b')]
        result = audit.audit(pa.Table.from_pylist(rows), batch_size=1)
        city = result['cities']['Dijon']
        counts = city['candidate_groups_all_rows']
        self.assertEqual(counts['duplicate_initial_rows'], 1)
        self.assertEqual(counts['single_initial_state_in_window_groups'], 1)
        self.assertEqual(counts['conflicting_initial_groups'], 0)
        self.assertEqual(city['notification_2023']['sources'], {'source-a': 1, 'source-b': 1})
        output = json.dumps(result)
        for secret in ['private-contract', 'private-supplier', 'private-subject', DIJON]:
            self.assertNotIn(secret, output)

    def test_holder_amount_and_missing_conflicts(self):
        city = report([row('holder'), row('holder', titulaire_id='another-holder'),
                       row('amount'), row('amount', montant=200.0),
                       row('missing'), row('missing', montant=None),
                       row('zero', montant=0.0, attributionAvance=False)])
        self.assertEqual(city['candidate_groups_all_rows']['conflicting_initial_groups'], 3)
        fields = city['initial_field_diagnostics']
        self.assertEqual(fields['titulaire_id']['conflicting_populated_values_groups'], 1)
        self.assertEqual(fields['montant']['conflicting_populated_values_groups'], 1)
        self.assertEqual(fields['montant']['missing_and_populated_groups'], 1)
        self.assertEqual(fields['montant']['any_difference_groups'], 2)
        self.assertEqual(fields['attributionAvance']['populated_groups'], 1)

    def test_modifications_unversioned_and_cross_years(self):
        city = report([
            row('old', dateNotification='2022-12-31'),
            row('old', modification_id=1, montant=900.0),
            row('future'), row('future', dateNotification='2024-01-01'),
            row('unknown', modification_id=None),
            row('mod-only', modification_id=2),
            row(None), row('', modification_id=None),
            row('outside', dateNotification='2024-01-01'),
            row('other-buyer', acheteur_id='not-preregistered')])
        self.assertEqual(city['notification_2023']['rows'], 6)
        self.assertEqual(city['notification_2023']['distinct_buyer_contract_groups'], 4)
        self.assertEqual(city['notification_2023']['missing_identity_rows'], 2)
        self.assertIsNone(city['notification_2023']['missing_identity_groups'])
        counts = city['candidate_groups_all_rows']
        self.assertEqual(counts['groups_with_initial_outside_window'], 2)
        self.assertEqual(counts['groups_spanning_notification_years'], 2)
        self.assertEqual(counts['conflicting_initial_groups'], 1)
        self.assertEqual(counts['no_initial_groups'], 2)
        self.assertEqual(counts['unversioned_only_groups'], 1)
        self.assertEqual(counts['groups_with_modifications'], 2)
        self.assertEqual(counts['single_initial_state_in_window_groups'], 0)

    def test_tours_all_year_coverage(self):
        city = report([row('a', acheteur_id=TOURS, dateNotification='2024-02-01'),
                       row('b', acheteur_id=TOURS, dateNotification='2025-02-01'),
                       row('c', acheteur_id=TOURS, dateNotification=None)], 'Tours')
        self.assertEqual(city['notification_2023']['rows'], 0)
        self.assertEqual(city['all_years']['notification_years'],
                         {'2024': 1, '2025': 1, 'missing': 1})
        self.assertEqual(city['all_years']['distinct_buyer_contract_groups'], 3)

    def test_other_procurement_fields_and_parquet_stream(self):
        rows = [row(), row(techniques='changed'), row(techniques='changed')]
        table = pa.Table.from_pylist(rows)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.parquet'
            pq.write_table(table, path, row_group_size=1)
            self.assertEqual(audit.audit(path, batch_size=1), audit.audit(table))
        city = report(rows)
        self.assertEqual(city['candidate_groups_all_rows']['duplicate_initial_rows'], 1)
        self.assertEqual(city['candidate_groups_all_rows']['conflicting_initial_groups'], 1)
        self.assertEqual(city['initial_field_diagnostics']['techniques']['missing_and_populated_groups'], 1)


if __name__ == '__main__':
    unittest.main()
