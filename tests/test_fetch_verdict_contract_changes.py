import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fetch_verdict_contract_changes', ROOT / 'tools/fetch-verdict-contract-changes.py')
fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc)


def change(status='active', *types):
    return {'status': status, 'rationaleTypes': list(types)}


class FeatureTests(unittest.TestCase):
    def test_counts_only_active_changes_and_price_rationales(self):
        contract = {'value': {'amount': 110.0},
                    'changes': [change('active', 'itemPriceVariation'), change('pending', 'volumeCuts'), change('active', 'durationExtension'),
                                change('active', 'volumeCuts')]}
        x = fc.features(contract, 100.0)
        self.assertEqual(x['changes'], 3)
        self.assertEqual(x['increase'], 0.1)
        self.assertTrue(all(check(x) for check in fc.CHECKS.values()))

    def test_no_changes_and_unknown_signed_amount(self):
        x = fc.features({'value': {'amount': 50.0}}, None)
        self.assertEqual((x['changes'], x['increase']), (0, None))
        self.assertFalse(any(check(x) for check in fc.CHECKS.values()))

    def test_wilson_bounds(self):
        self.assertIsNone(fc.wilson(0, 0))
        low, high = fc.wilson(4, 13)
        self.assertAlmostEqual(low, 0.127, places=3)
        self.assertAlmostEqual(high, 0.576, places=3)


if __name__ == '__main__':
    unittest.main()
