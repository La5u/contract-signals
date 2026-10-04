"""Optional offline scientific dependencies; production scoring is untouched."""
import importlib.util
import inspect
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
try:
    import numpy as np
    import scipy
    import sklearn
except ImportError:
    np = None


def load():
    spec = importlib.util.spec_from_file_location('comparison', ROOT / 'tools/compare-calibration-methods.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipIf(np is None, 'Optional numpy/scipy/sklearn unavailable')
class ComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load()

    def test_reproducible_and_filter_does_not_retune(self):
        both = self.module.run_one('missingness', 3)
        self.assertEqual(both, self.module.run_one('missingness', 3))
        for method in ('lr', 'logistic'):
            filtered = self.module.run_one('missingness', 3, method)
            self.assertEqual(filtered['methods'], {method: both['methods'][method]})
            self.assertEqual(filtered['means'], both['means'])
            self.assertEqual(filtered['paired_difference'], both['paired_difference'])

    def test_ties_and_paired_intervals(self):
        y = np.array([1, 0, 0, 1])
        result = self.module.base.metrics(y, np.ones(4), np.ones((4, 18)))
        self.assertEqual(result['AP'], .5)
        self.assertEqual(result['precision_top5'], .5)
        self.assertEqual(result['recall_top5'], .25)
        summary = self.module.paired_summary([-.1, .1] * 5, 'AP')
        self.assertTrue(summary['crosses_zero'])
        self.assertEqual(summary['classification'], 'inconclusive')
        self.assertEqual(summary, self.module.paired_summary([-.1, .1] * 5, 'AP'))
        self.assertEqual(self.module.paired_summary([.03] * 10, 'AP')['classification'],
                         'consistently larger difference')

    def test_train_validation_only_contract_and_assessed_means(self):
        self.assertEqual(list(inspect.signature(self.module.fit_pipelines).parameters),
                         ['train_x', 'train_known', 'train_labels', 'validation_x',
                          'validation_known', 'validation_labels'])
        x, known, _, labels, (train, val, _) = self.module.base.generate('independent', 1)
        fitted = self.module.fit_pipelines(x[train], known[train], labels[train],
                                          x[val], known[val], labels[val])
        np.testing.assert_allclose(fitted['means'], x[train].sum(0) / known[train].sum(0))
        self.assertTrue(all(w >= 0 for w in fitted['logistic']['weights']))

    def test_no_production_score_changes(self):
        # Importing/running this isolated offline tool cannot rewrite existing source.
        paths = [p for p in ROOT.rglob('*') if p.is_file() and
                 p.suffix in ('.js', '.ts', '.tsx') and 'node_modules' not in p.parts and '.git' not in p.parts]
        before = {p: p.read_bytes() for p in paths}
        self.module.run_one('independent', 0)
        self.assertTrue(all(p.read_bytes() == content for p, content in before.items()))


if __name__ == '__main__':
    unittest.main()
