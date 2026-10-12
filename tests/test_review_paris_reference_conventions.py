import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('paris_review', ROOT / 'tools/review-paris-reference-conventions.py')
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


class ParisReferenceReviewTests(unittest.TestCase):
    def test_literal_only(self):
        self.assertEqual(review.scalar_hits({'id': '2025F02648', 'uid': 'x2025F026480000'},
                                            {'2025F026480000'}), [])
        self.assertEqual(review.scalar_hits({'a/b': '2025F026480000'}, {'2025F026480000'}),
                         [{'pointer': '/a~1b', 'value': '2025F026480000'}])

    def test_public_snapshot_reproduces(self):
        evidence = json.loads((ROOT / 'data/paris-reference-convention-evidence.json').read_text())
        snapshot = review.build()
        self.assertEqual(snapshot, evidence['repositorySnapshot'])
        self.assertEqual(len(snapshot['pairs']), 9)
        self.assertFalse(snapshot['automaticNormalizationAuthorized'])
        self.assertEqual(snapshot['literalFullReferenceScan']['hits'], {'feed': [], 'ministry': []})
        self.assertIn('20242024S05079', snapshot['literalFullReferenceScan']['references'])
        for pair in snapshot['pairs']:
            self.assertFalse(pair['linkageSufficient'])
            if 'feedShortIdRows' in pair:
                self.assertTrue(pair['feedShortIdRows'])
                self.assertTrue(pair['ministryShortIdRows'])
                self.assertEqual(pair['feedExactFullReferenceHits'], [])
                self.assertEqual(pair['ministryExactFullReferenceHits'], [])

    def test_bounded_acquisitions(self):
        evidence = json.loads((ROOT / 'data/paris-reference-convention-evidence.json').read_text())
        self.assertLessEqual(len(evidence['liveRequests']), 8)
        for request in evidence['liveRequests']:
            self.assertLessEqual(request['bodyBytes'], 2 * 1024 * 1024)
            self.assertTrue(request['url'].startswith('https://'))


if __name__ == '__main__':
    unittest.main()
