import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ukraine_prepare', ROOT / 'tools/prepare-ukraine-public-audit.py')
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = P.build()
        cls.public = json.loads((ROOT / 'data/ukraine-public-audit-plan.json').read_text())

    def test_public_plan_reproduces_before_new_acquisition(self):
        self.assertEqual(self.plan, self.public)
        P.verify(self.plan)
        self.assertEqual(len(self.plan['selected']), 12)
        self.assertEqual(len(self.plan['amountReviewQueue']), 11)
        self.assertEqual(self.plan['valueDifferenceInventory'], {'amount': 11, 'amount-currency-vat-tuple': 25})
        self.assertEqual(sum(s['population'] for s in self.plan['strata'].values()), 488)
        self.assertEqual(sum(r['scoreAtSelection'] > 0 for r in self.plan['selected']), 5)
        self.assertEqual(sum(r['scoreAtSelection'] == 0 for r in self.plan['selected']), 7)
        self.assertEqual(sum(r['contractChangesAtSelection'] >= 3 for r in self.plan['selected']), 1)
        self.assertEqual(len({r['rowId'] for r in self.plan['selected']}), 12)

    def test_selection_and_private_inputs_are_not_mutated(self):
        before = {p: (ROOT / p).stat().st_mtime_ns for p in self.plan['inputHashes']}
        self.assertEqual(P.build(), self.plan)
        self.assertEqual(before, {p: (ROOT / p).stat().st_mtime_ns for p in before})
        for binding in self.plan['selected'] + self.plan['amountReviewQueue']:
            self.assertFalse({'supplier', 'supplierIds', 'description', 'contactPoint', 'buyer'} & binding.keys())
            self.assertIn(binding['rawPath'], self.plan['rawSnapshotHashes'])
        self.assertEqual(self.plan['requestBudget']['overallCeiling'], 30)
        self.assertEqual(self.plan['requestBudget']['retryCount'], 0)
        self.assertEqual(self.plan['requestBudget']['redirectCount'], 0)

    def test_exclusive_readonly_private_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'v1/plan.json'
            self.assertTrue(P.freeze(self.plan, path))
            self.assertEqual(path.stat().st_mode & 0o777, 0o400)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            self.assertFalse(P.freeze(self.plan, path))
            changed = copy.deepcopy(self.plan)
            changed['maximum'] = 11
            changed['planSha256'] = P.sha(P.canonical({k: v for k, v in changed.items() if k != 'planSha256'}))
            with self.assertRaisesRegex(ValueError, 'Different existing freeze'):
                P.freeze(changed, path)
            self.assertEqual(json.loads(path.read_text()), self.plan)

    def test_unsafe_freezes_and_changed_hash_rejected(self):
        with self.assertRaises(ValueError):
            P.freeze(self.plan, ROOT / 'never-created-plan.json')
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'target').mkdir()
            (base / 'linked').symlink_to(base / 'target', target_is_directory=True)
            with self.assertRaises(ValueError):
                P.freeze(self.plan, base / 'linked/plan.json')
            bad = copy.deepcopy(self.plan)
            bad['selected'].reverse()
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                P.freeze(bad, base / 'bad/plan.json')
            self.assertFalse((base / 'bad/plan.json').exists())

    def test_unknown_and_invalid_population_protocol_fail_closed(self):
        scores = {r['id']: 0 for r in json.loads((ROOT / 'data/prozorro.json').read_text())}
        scores.pop(next(iter(scores)))
        with self.assertRaisesRegex(ValueError, 'score identities'):
            P.build(scores=scores)
        for maximum in (0, 13, True):
            with self.assertRaises(ValueError):
                P.build(maximum=maximum)


if __name__ == '__main__':
    unittest.main()
