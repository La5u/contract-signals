"""Pinned vocabulary integration must be exact and rebuild-safe."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('decp_cpv_feeds', ROOT / 'tools/decp_feeds.py')
feeds = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(feeds)


class CpvIntegration(unittest.TestCase):
    def test_official_only_prefix_is_available(self):
        self.assertEqual(feeds.cpv_lookup([])['92521000'], '92521000-9')

    def test_exact_lookup_never_guesses(self):
        lookup = feeds.cpv_lookup([], vocabulary=['92521000-9'])
        self.assertNotIn('92521001', lookup)
        self.assertNotIn('00000000', lookup)

    def test_conflicting_published_digit_is_excluded(self):
        rows = [{'cpv': '92521000-8'}]
        self.assertNotIn('92521000', feeds.cpv_lookup(rows, vocabulary=['92521000-9']))

    def test_alternative_conflict_is_preserved(self):
        rows = [{'cpv': '92521000-9', 'initialAlternatives': [{'cpv': '92521000-8'}]}]
        self.assertNotIn('92521000', feeds.cpv_lookup(rows, vocabulary=['92521000-9']))

    def test_ambiguous_vocabulary_is_excluded(self):
        self.assertNotIn('92521000', feeds.cpv_lookup([], vocabulary=['92521000-9', '92521000-8']))

    def test_malformed_vocabulary_rejected(self):
        with self.assertRaises(ValueError):
            feeds.cpv_lookup([], vocabulary=['92521000'])

    def test_all_current_decp_codes_in_official_vocabulary(self):
        vocabulary = json.loads((ROOT / 'data/decp-cpv-vocabulary.json').read_text())
        codes = set(vocabulary['codes'])
        self.assertEqual(len(codes), 9454)
        rows = []
        for path in ('data/decp-cities.json', 'data/decp-history.json'):
            rows.extend(json.loads((ROOT / path).read_text()))
        self.assertEqual(len(rows), 5286)
        self.assertTrue(all(row['cpv'] in codes for row in rows))


if __name__ == '__main__':
    unittest.main()
