#!/usr/bin/env python3
"""Synthetic, offline, bounded tests. No private records needed."""
import gzip
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('seap', Path(__file__).resolve().parents[1] / 'tools/import-romania-seap.py')
seap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seap)


def row(**kwargs):
    return dict({'buyer': 'Synthetic public buyer', 'buyer_cui': 'RO 4305857',
                 'winner': 'Synthetic published supplier', 'winner_cui': '1234567890123',
                 'contract_date': '2025-01-23 00:00:00', 'cpv': '45000000',
                 'concluded_by': 'Incheierea unui acord-cadru', 'value_ron_num': 999999,
                 'contract_no': 'TEST-1', 'source': '2025/Contracte-T1-2025.xlsx'}, **kwargs)


class SeapTest(unittest.TestCase):
    def test_exact_identity(self):
        self.assertEqual(seap.cui('RO-4305857'), '4305857')
        self.assertIsNone(seap.cui('buyer 4305857'))
        self.assertIsNone(seap.candidate(row(buyer_cui='999'), 1, 'a' * 64))

    def test_minimized_browse_only_framework(self):
        r = seap.candidate(row(), 1, 'a' * 64)
        self.assertEqual(r['dataStatus'], 'unverified')
        self.assertEqual(r['assessmentMode'], 'browse')
        self.assertIsNone(r['amount'])
        self.assertIsNone(r['currency'])
        self.assertIsNone(r['directAward'])
        self.assertEqual(r['supplier'], 'Synthetic published supplier')
        self.assertEqual(r['supplierIds'], [])
        self.assertNotIn('1234567890123', json.dumps(r))
        self.assertNotIn('value_ron_num', json.dumps(r))
        self.assertTrue(r['descriptionGenerated'])
        self.assertNotIn('score', r)
        self.assertNotIn('dataFamily', r)  # generic import; do not claim TED or an unregistered family
        self.assertEqual(r['date'], '2025-01-23')
        self.assertEqual(r['provenance']['normalizedLine'], 1)

    def test_date_is_not_inferred(self):
        self.assertIsNone(seap.iso_date('2025-02-30'))
        self.assertIsNone(seap.iso_date('23/01/2025'))
        self.assertIsNone(seap.iso_date(''))

    def test_repeat_rows_retained_not_summed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'quarter.gz'
            with gzip.open(p, 'wt') as f:
                for r in [row(), row(), row(buyer_cui='999')]:
                    f.write(json.dumps(r) + '\n')
            rows, m = seap.build(p)
            self.assertEqual(len(rows), 2)
            self.assertNotEqual(rows[0]['id'], rows[1]['id'])
            self.assertEqual(m['counts']['exactRepeatedSelectedRows'], 1)
            self.assertEqual(m['counts']['inputRows'], 3)
            self.assertIsNone(m['overlap']['confirmedRecordLinks'])
            self.assertNotIn('Synthetic published supplier', json.dumps(m))

    def test_budget_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'quarter.gz'
            with gzip.open(p, 'wt') as f:
                f.write(json.dumps(row()) + '\n')
            old = seap.MAX_ROWS
            try:
                seap.MAX_ROWS = 0
                with self.assertRaisesRegex(ValueError, 'budget'):
                    seap.build(p)
            finally:
                seap.MAX_ROWS = old

    def test_private_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'candidate.json'
            p.write_text('old')
            os.chmod(p, 0o644)
            seap.private_write(p, '[]')
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
