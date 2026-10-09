"""Standard-library tests: python -m unittest discover -s tests -p test_audit_data_quality.py."""
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

TOOL = Path(__file__).resolve().parents[1] / 'tools/audit-data-quality.py'
spec = importlib.util.spec_from_file_location('audit_data_quality', TOOL)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def row(**changes):
    return {'id': 'private-row-id', 'amount': 100, 'currency': 'EUR',
            'date': '2024-02-29', 'publicationDate': '2024-03-01T12:30:00Z',
            'buyer': 'PRIVATE BUYER', 'supplier': 'PRIVATE SUPPLIER',
            'description': 'PRIVATE DESCRIPTION', 'source': 'https://example.org/private',
            'dataStatus': 'verified', **changes}


class AuditTests(unittest.TestCase):
    def test_amount_null_zero_missing_boolean_and_nonfinite(self):
        missing = row()
        del missing['amount']
        rows = [missing] + [row(amount=v) for v in (None, 0, -0.0, -1, 2, True, False, '12', float('nan'), float('inf'))]
        counts, _ = audit.audit_rows(rows, 'data/example.json')
        self.assertEqual(counts['amounts'], {'missing': 1, 'null': 1, 'zero_declared': 2,
                                           'negative': 1, 'positive': 1, 'non_numeric': 5})

    def test_dates_strict_calendar_and_types(self):
        for value in ('2023-02-29', '2024-02-30', '2024-13-01', '2024-00-01',
                      '2024-1-01', '0000-01-01', True, 0, 'garbage'):
            with self.subTest(value=value):
                self.assertEqual(audit.date_category(value), 'invalid')
        for value in (None, '', '  '):
            self.assertEqual(audit.date_category(value), 'missing')
        self.assertEqual(audit.date_category('2024-02-29'), 'valid')
        self.assertEqual(audit.date_category('2024-02-29T12:30:00Z'), 'invalid')
        self.assertEqual(audit.date_category('2024-02-29T12:30:00.123+02:00', True), 'valid')
        for value in ('2024-02-30T12:30:00Z', '2024-02-29T24:00:00Z',
                      '2024-02-29T12:60:00Z', '2024-02-29T12:30:00+02:60',
                      '2024-02-29T12:30:00', '2024-02-29T12:30:00+24:00'):
            self.assertEqual(audit.date_category(value, True), 'invalid')

    def test_duplicates_and_conflict_union(self):
        rows = [row(dataFamily='decp', buyerSiret='private-buyer-id', contractId='private-contract-id',
                    initialConflicts=['amount'], modificationConflicts=[{'id': 'private-modification'}]),
                row(dataFamily='decp', buyerSiret='private-buyer-id', contractId='private-contract-id'),
                row(id='different'), row(id=None)]
        counts, queue = audit.audit_rows(rows, 'data/example.json')
        self.assertEqual(counts['record_ids'], {'missing_or_invalid': 1, 'duplicate_groups': 1,
                                              'duplicate_rows': 2, 'duplicate_excess': 1})
        self.assertEqual(counts['conflict_exclusions'], {'initial': 1, 'modification': 1,
                                                      'identity_ambiguous': 2, 'any': 2})
        self.assertIn('duplicate_record_id', queue[0]['reasons'])
        self.assertIsNone(queue[-1]['id'])
        encoded = json.dumps(counts)
        for private in ('private-row-id', 'PRIVATE BUYER', 'PRIVATE SUPPLIER',
                        'PRIVATE DESCRIPTION', 'private-buyer-id', 'private-contract-id', 'private-modification'):
            self.assertNotIn(private, encoded)
        for item in queue:
            self.assertEqual(set(item), {'id', 'dataset_path', 'reasons'})

    def test_text_currency_status_and_source(self):
        counts, _ = audit.audit_rows([
            row(description=' Objet non renseigné ', buyer='', supplier='SIRET 123 / SIREN 456', currency=None, source=None),
            row(id='b', description=True, supplier='unknown', currency='eur', dataStatus='PRIVATE STATUS', source='javascript:bad'),
            row(id='c', description='A real heading', supplier=None, currency='ZZZ', dataStatus=None),
        ], 'data/example.json')
        self.assertEqual(counts['text']['description']['placeholder'], 1)
        self.assertEqual(counts['text']['description']['non_text'], 1)
        self.assertEqual(counts['text']['supplier']['identifier_only'], 1)
        self.assertEqual(counts['text']['supplier']['placeholder'], 1)
        self.assertEqual(counts['text']['supplier']['empty'], 1)
        self.assertEqual(counts['currency'], {'missing': 1, 'invalid_syntax': 1,
                                            'declared': 1, 'legacy_ui_default_eur': 1})
        self.assertEqual(counts['source_urls'], {'missing': 1, 'invalid': 1, 'present': 1})
        self.assertEqual(counts['dataStatus']['other'], 1)
        self.assertNotIn('PRIVATE STATUS', json.dumps(counts))

    def fixture_root(self, root):
        (root / 'data').mkdir()
        (root / 'script.js').write_text("const datasets = {\n  example: { path: 'data/example.json', coverage: 'data/coverage.json' },\n  all: { combined: true, path: null },\n  local: { path: null },\n  };\nfetch('data/dataset-metadata.json');\n")
        (root / 'data/example.json').write_text(json.dumps([row(amount=0)]))
        for path in ('coverage.json', 'dataset-metadata.json', 'raw.json', 'supplier-identities.json'):
            (root / 'data' / path).write_text('not valid JSON; must not be loaded')

    def test_registry_skips_metadata_raw_coverage_and_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture_root(root)
            report, queue = audit.inventory(root)
            self.assertEqual(list(report['datasets']), ['example'])
            self.assertEqual(report['datasets']['example']['rows'], 1)
            self.assertEqual(queue[0]['id'], 'private-row-id')
            self.assertNotIn('private-row-id', json.dumps(report))
            self.assertEqual(audit.DEFAULT_QUEUE, Path.home() / '.cache/contract-signals/accuracy-review')

    def test_cli_default_private_permissions_and_opt_in_aggregate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture_root(root)
            private = root / 'private'
            cmd = [sys.executable, str(TOOL), '--root', str(root), '--review-dir', str(private)]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.assertIn('No aggregate JSON written', result.stdout)
            self.assertNotIn('private-row-id', result.stdout)
            queue = private / 'review.jsonl'
            self.assertEqual(stat.S_IMODE(private.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(queue.stat().st_mode), 0o600)
            self.assertEqual(len(queue.read_text().splitlines()), 1)
            output = root / 'aggregate.json'
            subprocess.run(cmd + ['--output', str(output)], check=True, capture_output=True)
            self.assertEqual(json.loads(output.read_text())['datasets']['example']['amounts']['zero_declared'], 1)
            self.assertNotIn('PRIVATE', output.read_text())
            subprocess.run(cmd, check=True, capture_output=True)
            self.assertEqual(len(queue.read_text().splitlines()), 1, 'rerun replaces rather than appends')

    def test_registry_drift_and_non_row_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'script.js').write_text('const datasets = {};')
            with self.assertRaises(ValueError):
                audit.published_datasets(root)
        for rows in ({'contracts': []}, [1], [None]):
            with self.assertRaises(ValueError):
                audit.audit_rows(rows, 'data/example.json')


if __name__ == '__main__':
    unittest.main()
