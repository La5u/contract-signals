"""Reviewed dispositions must be reproducible and must not change contract facts."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('resolutions', ROOT / 'tools/review-link-resolutions.py')
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


class ResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decisions = json.loads((ROOT / r.DECISIONS).read_text())
        cls.result = r.build()

    def test_current_decisions_and_notice_resolution_counts(self):
        self.assertEqual(self.result['counts'], {'heuristicPairs': 9, 'activePairs': 7,
            'dismissedPairs': 2, 'confirmedDecpLinks': 0, 'ambiguousActivePairs': 0,
            'verifiedTedNoticeVersions': 3, 'unverifiedTedNoticeVersions': 2})
        self.assertTrue(all(not p['replacementLinkConfirmed'] for p in self.result['dismissedPairs']))
        self.assertTrue(all(not p['decpCrosswalkConfirmed'] for p in self.result['tedNotices']))
        self.assertEqual(sum(p['httpStatus'] == '429' for p in self.result['tedNotices']), 2)
        self.assertTrue(all(not any(w.startswith('multiple-') for w in p['activeWarnings'])
                            for p in self.result['activePairs']))

    def test_incorrect_pairings_are_not_reintroduced_as_active(self):
        dismissed = {(p['boampId'], p['decpId']) for p in self.result['dismissedPairs']}
        self.assertEqual(dismissed, {('boamp-25-21317-lot-0001', 'decp-21750001600019-2024S05079'),
                                    ('boamp-25-34782-lot-0003', 'decp-21440109300015-2025F00012')})
        self.assertFalse(dismissed & {(p['boampId'], p['decpId']) for p in self.result['activePairs']})
        self.assertTrue(all('replacement' in p['reason'].lower() and p['replacementLinkConfirmed'] is False
                            for p in self.result['dismissedPairs']))

    def test_stale_sources_rows_and_evidence_fail_closed(self):
        for kind in ['source', 'row', 'scalar', 'disposition', 'replacement', 'duplicate', 'external']:
            decisions = copy.deepcopy(self.decisions)
            item = decisions['decisions'][0]
            if kind == 'source': decisions['inputHashes'][r.RAW] = '0' * 64
            elif kind == 'row': item['boampRowSha256'] = '0' * 64
            elif kind == 'scalar': item['evidence'][0]['expected'] = 'invented'
            elif kind == 'disposition': item['disposition'] = 'confirmed'
            elif kind == 'replacement': item['replacementLinkConfirmed'] = True
            elif kind == 'duplicate': decisions['decisions'].append(copy.deepcopy(item))
            elif kind == 'external': item['evidence'][0]['source'] = '/tmp/private-evidence'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                r.build(decisions=decisions)

    def test_public_reproducible_read_only_and_without_private_cache(self):
        before = {p: (ROOT / p).read_bytes() for p in r.ROWS}
        original = Path.read_bytes
        def public_only(path):
            self.assertTrue(path.resolve().is_relative_to(ROOT))
            return original(path)
        with patch.object(Path, 'read_bytes', public_only):
            result = r.build()
        self.assertEqual(result, self.result)
        self.assertEqual(result, json.loads((ROOT / 'data/public-link-resolutions.json').read_text()))
        self.assertEqual(before, {p: (ROOT / p).read_bytes() for p in r.ROWS})
        self.assertNotIn('supplierProfiles', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
