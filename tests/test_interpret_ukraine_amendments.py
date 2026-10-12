"""Omitted amendment lists read as zero only by the cited publisher rule; evidence stays untouched."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('interpret', ROOT / 'tools/interpret-ukraine-amendments.py')
I = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(I)


class InterpretTests(unittest.TestCase):
    def setUp(self):
        self.evidence = json.loads((ROOT / I.EVIDENCE).read_text())

    def run_on(self, evidence):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / I.EVIDENCE
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps(evidence))
            return I.interpret(Path(d))

    def test_committed_overlay_is_current(self):
        self.assertEqual(I.without_hashes(json.loads((ROOT / I.OUTPUT).read_text())), I.without_hashes(I.interpret()))

    def test_default_replay_ignores_hashes_and_does_not_write(self):
        overlay = json.loads((ROOT / I.OUTPUT).read_text())
        overlay.update(evidenceFileSha256='ignored', evidenceSha256='ignored')
        with patch('sys.argv', ['interpret']), patch('sys.stdout', new_callable=io.StringIO), patch.object(Path, 'read_text', return_value=json.dumps(overlay)), patch.object(Path, 'write_text', side_effect=AssertionError('offline write')):
            I.main()
        overlay['rows'][0]['activeChangeCount'] += 1
        with patch('sys.argv', ['interpret', '--check']), patch.object(Path, 'read_text', return_value=json.dumps(overlay)):
            with self.assertRaisesRegex(ValueError, 'Stale amendment-count'):
                I.main()

    def test_six_omitted_lists_are_zero_and_all_agree(self):
        body = I.interpret()
        self.assertEqual(body['counts'], {'rows': 12, 'agreeWithSnapshot': 12, 'byBasis': {
            'omitted-field-publisher-omits-empty-lists': 6, 'published-array': 6}})
        omitted = [r for r in body['rows'] if r['observedState'] == 'unavailable']
        self.assertTrue(all(r['activeChangeCount'] == 0 for r in omitted))
        self.assertEqual(body['publisherRule']['commit'], I.COMMIT)

    def test_evidence_is_not_rewritten(self):
        e = self.evidence
        self.assertEqual(sum(r['extract']['changesState'] == 'unavailable' for r in e['requests']), 6)
        self.assertTrue(all(r['extract']['changeCount'] is None for r in e['requests']
                            if r['extract']['changesState'] == 'unavailable'))

    def test_null_or_malformed_changes_stay_unknown(self):
        e = copy.deepcopy(self.evidence)
        r = next(r for r in e['requests'] if r['extract']['changesState'] == 'unavailable')
        r['extract']['anomalies'] = ['changes:not-array']
        with self.assertRaisesRegex(ValueError, 'Unrecognized changes state'):
            self.run_on(e)

    def test_unverified_module_rejected(self):
        e = copy.deepcopy(self.evidence)
        e['requests'][0]['outcome'] = 'unavailable'
        with self.assertRaisesRegex(ValueError, 'Unverified module'):
            self.run_on(e)


if __name__ == '__main__':
    unittest.main()
