"""Tiny offline tests: synthetic prefixes only, no archive scans or network."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('inspect_base', ROOT / 'tools/inspect-base-archives.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class BasePrefixTests(unittest.TestCase):
    def test_prefix_sampling_stops_before_partial_record(self):
        self.assertEqual(helper.sample_prefix(b'[{"id":"one"},{"id":"two"},{"id":"partial'), [{'id': 'one'}, {'id': 'two'}])

    def test_only_three_rows(self):
        rows = helper.sample_prefix(json.dumps([{'id': str(i)} for i in range(5)]).encode())
        self.assertEqual(len(rows), 3)

    def test_schema_report_has_no_personal_values(self):
        rows = [{'adjudicatarios': ['123456789 - Fictional Person'], 'dataPublicacao': '30/09/2026', 'PrecoTotalEfetivo': 0.0}]
        text = json.dumps(helper.summarize(rows))
        self.assertNotIn('123456789', text)
        self.assertNotIn('Fictional Person', text)
        self.assertNotIn('30/09/2026', text)
        self.assertIn('DD/MM/YYYY-shaped text', text)
        self.assertIn('nifNameShapedStringItems', text)

    def test_incomplete_utf8_tail_is_not_an_error(self):
        rows = helper.sample_prefix(b'\xef\xbb\xbf[{"name":"ok"},{"name":"' + b'\xc3')
        self.assertEqual(rows, [{'name': 'ok'}])

    def test_unrecognized_format_is_rejected(self):
        with self.assertRaises(ValueError):
            helper.sample_prefix(b'not a JSON array')


if __name__ == '__main__':
    unittest.main()
