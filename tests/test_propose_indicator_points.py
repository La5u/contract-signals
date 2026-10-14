import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('propose_indicator_points', ROOT / 'tools/propose-indicator-points.py')
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)


def row(buyer, groups, status, points=None):
    return {'id': f'{buyer}-{len(groups)}-{status}', 'buyer': buyer, 'groups': groups,
            'checks': {'x': {'status': status, 'points': points}}}


class Weighting(unittest.TestCase):
    def test_each_buyer_counts_once(self):
        rows = [row('b1', ['combined'], 'signal')] * 9 + [row('b2', ['combined'], 'clear')]
        hits, buyers, plain = pp.weighted(rows, 'x', 'combined')
        self.assertEqual((hits, buyers, plain), (1.0, 2, (9, 10)))

    def test_unknown_not_in_denominator(self):
        rows = [row('b1', ['combined'], 'signal'), row('b2', ['combined'], 'unknown'), row('b3', ['combined'], 'not-applicable')]
        self.assertEqual(pp.weighted(rows, 'x', 'combined')[:2], (1.0, 1))


class Shrinkage(unittest.TestCase):
    def test_no_evaluable_positives(self):
        self.assertIsNone(pp.shrunk_lr(0, 0, 3, 9))

    def test_shrinks_toward_one(self):
        raw = (5 / 10) / ((1 + 0.5) / (20 + 1))
        shrunk = pp.shrunk_lr(5, 10, 1, 20)
        self.assertTrue(1 < shrunk < raw)

    def test_points_scale(self):
        self.assertEqual(pp.points(2.0), pp.PDO)
        self.assertEqual(pp.points(0.5), 0.0)


class EndToEnd(unittest.TestCase):
    def test_eligibility_and_amendments(self):
        rows = [{'id': 'p1', 'label': 'corruption', 'finality': 'confirmed', 'buyerId': 'b1', 'checks': {'x': {'status': 'signal', 'points': 12}}},
                {'id': 'p2', 'label': 'fraud', 'finality': 'pending-appeal', 'buyerId': 'b2', 'checks': {'x': {'status': 'signal', 'points': 12}}},
                {'id': 'c1', 'label': 'comparison', 'finality': None, 'buyerId': 'b1', 'checks': {'x': {'status': 'clear', 'points': None}}}]
        changes = {'rows': [{'id': 'p1', 'features': {'changes': 4}}, {'id': 'c1', 'features': {'changes': 0}}]}
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'rows.json').write_text(json.dumps(rows))
            (Path(d) / 'changes.json').write_text(json.dumps(changes))
            loaded, skipped = pp.load_rows(Path(d) / 'rows.json', Path(d) / 'changes.json')
        self.assertEqual([r['id'] for r in loaded], ['p1', 'c1'])
        self.assertEqual(loaded[0]['checks'][pp.AMENDMENT_CHECK], {'status': 'signal', 'points': 6, 'changes': 4})
        res = pp.analyse(loaded, 'x')
        self.assertEqual(res['combined']['rate'], 1.0)
        self.assertTrue(str(res['proposed_points']).startswith('too few'))

    def test_non_competitive_left_out(self):
        rows = [{'id': 'p1', 'label': 'corruption', 'finality': 'confirmed', 'buyerId': 'b1', 'procedure': 'reporting', 'checks': {}},
                {'id': 'c1', 'label': 'comparison', 'finality': None, 'buyerId': 'b1', 'procedure': 'aboveThreshold', 'checks': {}}]
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'rows.json').write_text(json.dumps(rows))
            loaded, skipped = pp.load_rows(Path(d) / 'rows.json', None)
        self.assertEqual(([r['id'] for r in loaded], skipped), (['c1'], {'corruption': 1}))
        self.assertEqual(pp.analyse(loaded, 'ua-direct-award')['proposed_points'], 'NA')


if __name__ == '__main__':
    unittest.main()
