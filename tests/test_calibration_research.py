"""Safety checks for the current local public-record research snapshot."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'research' / 'calibration'


class ResearchSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.benchmark = json.loads((ROOT / 'benchmark.json').read_text())
        self.reviews = json.loads((ROOT / 'comparison-reviews.json').read_text())
        self.links = json.loads((ROOT / 'case-links.json').read_text())

    def test_manifest_provenance_and_no_premature_fit(self):
        self.assertEqual(self.benchmark['source_provenance']['case_manifest_sha256'],
                         hashlib.sha256((ROOT / 'case-links.json').read_bytes()).hexdigest())
        self.assertFalse(self.benchmark['ready_for_fit'])
        for target in self.benchmark['eligibility'].values():
            self.assertEqual(target['known_negatives'], 0)
            self.assertFalse(target['ready_for_fit'])

    def test_fact_reviews_do_not_become_negative_labels(self):
        candidates = {r['id']: r for r in self.benchmark['rows'] if r['membership'] == 'comparison-candidate'}
        self.assertEqual(set(candidates), {r['notice_id'] for r in self.reviews['rows']})
        for review in self.reviews['rows']:
            row = candidates[review['notice_id']]
            self.assertEqual(review['project_id'], row['project_id'])
            self.assertEqual(review['contract_reference'], row['bid_reference_no'])
            self.assertEqual(review['signing_date'], row['signing_date'])
            self.assertEqual(review['method_code'], row['method_code'])
            self.assertEqual(review['price'], row['signed_contract_price'])
            self.assertTrue(all(v is None for v in row['labels'].values()))
            self.assertTrue(all(v is None for v in review['labels'].values()))

    def test_corruption_document_is_not_an_award_notice_or_company_label(self):
        row = next(r for r in self.benchmark['rows'] if r['id'] == 'DOC-P155732-G3-2016')
        self.assertEqual(row['record_type'], 'documentary-contract')
        self.assertTrue(row['labels']['corruption'])
        self.assertIn('administrative', row['finding_standard'])
        self.assertIn('not criminal', row['finding_standard'])
        self.assertTrue(row['conflicting_source_values'])
        self.assertIsNone(row['notice_date'])
        for key in ('supplier_name', 'address', 'email', 'phone', 'notice_text'):
            self.assertNotIn(key, row)

    def test_pending_findings_and_fraud_are_not_automatic_corruption(self):
        bangladesh = next(r for r in self.benchmark['rows'] if r['id'] == 'OP00102403')
        self.assertTrue(all(v is None for v in bangladesh['labels'].values()))
        somalia = next(r for r in self.benchmark['rows'] if r['id'] == 'OP00104863')
        self.assertTrue(somalia['labels']['fraud'])
        self.assertIsNone(somalia['labels']['corruption'])
        remaining = json.loads((ROOT / 'remaining-link-reviews.json').read_text())
        for group in remaining['groups']:
            for record in group['records']:
                self.assertTrue(all(v is None for v in record['labels'].values()))


if __name__ == '__main__':
    unittest.main()
