import importlib.util
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publish_ukraine_labels', ROOT / 'tools/publish-ukraine-labels.py')
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)

TODAY = date(2026, 10, 14)


def verdict(tid, label, finality='', day='2020-01-01'):
    return {'reyestr_id': tid + day, 'tender_id_normalised': tid, 'verdict_date': day,
            'proposed_label': label, 'verification': {'finality': finality}}


class Publish(unittest.TestCase):
    def run_on(self, data):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'labels.json'
            path.write_text(json.dumps(data))
            counts = pub.process(path, TODAY, '2026-10-14')
            return counts, json.loads(path.read_text())

    def test_pending_appeal_label_is_noted_and_kept(self):
        data = {'status': 'proposed labels; not owner-approved', 'verdicts': [
            verdict('UA-A', 'corruption (official involved)', 'final 2021-01-01'),
            verdict('UA-B', 'procurement fraud (no official established)', 'appeal pending'),
            verdict('UA-C', 'exclude: tender is context', 'appeal pending')]}
        counts, out = self.run_on(data)
        labels = [v['proposed_label'] for v in out['verdicts']]
        self.assertEqual(labels, ['corruption (official involved)', 'procurement fraud (no official established)', 'exclude: tender is context'])
        self.assertEqual([v.get('finality_note') for v in out['verdicts']], [None, 'convicted; under appeal, not final', None])
        self.assertEqual(counts['noted'], 1)
        self.assertNotIn('not owner-approved', out['status'])
        self.assertIn('Published by the owner on 2026-10-14', out['status'])

    def test_recent_verdict_is_noted(self):
        _, out = self.run_on({'verdicts': [verdict('UA-A', 'bid rigging (AMCU decision upheld)', '', '2026-09-01')]})
        self.assertEqual(out['verdicts'][0]['proposed_label'], 'bid rigging (AMCU decision upheld)')
        self.assertIn('less than three months before 2026-10-14', out['verdicts'][0]['finality_note'])

    def test_cohort_tenders_and_rows(self):
        data = {'tenders': [{'label': 'corruption', 'finality': 'pending-appeal', 'positive': False},
                            {'label': 'fraud', 'finality': 'presumed', 'positive': True}],
                'rows': [{'label': 'collusion', 'finality': 'too-recent'}, {'label': 'comparison', 'finality': None}]}
        _, out = self.run_on(data)
        self.assertEqual([t['label'] for t in out['tenders']], ['corruption', 'fraud'])
        self.assertEqual([t.get('finality_note') for t in out['tenders']], ['convicted; under appeal, not final', None])
        self.assertEqual([r.get('finality_note') for r in out['rows']],
                         ['AMCU decision upheld by a court less than three months before 2026-10-14; an appeal may still be filed, not final', None])

    def test_snippets_and_individual_tax_numbers_removed(self):
        data = {'judgments': [{'tender_ids': {'UA-A': {'as_printed': 'UA-A', 'context': 'text naming a person'}}}],
                'procurements': [{'supplier_code': '2280412773'}, {'supplier_code': '12345678'}]}
        counts, out = self.run_on(data)
        self.assertNotIn('context', out['judgments'][0]['tender_ids']['UA-A'])
        self.assertEqual(out['procurements'][0]['supplier_code'], 'individual tax number (masked)')
        self.assertEqual(out['procurements'][1]['supplier_code'], '12345678')
        self.assertEqual(counts['scrubbed'], 2)

    def test_idempotent(self):
        data = {'status': 'x; not owner-approved', 'verdicts': [verdict('UA-B', 'corruption (official involved)', 'appeal pending')]}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'labels.json'
            path.write_text(json.dumps(data))
            pub.process(path, TODAY, '2026-10-14')
            first = path.read_text()
            self.assertEqual(pub.process(path, TODAY, '2026-10-14'), {'noted': 0, 'scrubbed': 0})
            self.assertEqual(path.read_text(), first)


if __name__ == '__main__':
    unittest.main()
