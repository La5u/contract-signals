import importlib.util
from pathlib import Path
import unittest

# Offline calibration is optional; do not add scientific packages to the site's CI/runtime.
if any(importlib.util.find_spec(name) is None for name in ('numpy', 'scipy', 'sklearn')):
    raise unittest.SkipTest('Offline calibration needs optional numpy, scipy and sklearn')
import numpy as np

spec = importlib.util.spec_from_file_location('calibrate', Path(__file__).parents[1] / 'tools/calibrate-indicators.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class CalibrationTests(unittest.TestCase):
    def test_repeatability(self):
        self.assertEqual(c.run_one('independent', 2), c.run_one('independent', 2))

    def test_unknown_denominator_and_negative_lr(self):
        x = np.array([[1.], [0.], [0.], [0.]])
        known = np.array([[True], [False], [True], [False]])
        y = np.array([1, 1, 0, 0])
        self.assertAlmostEqual(c.lr_weights(x, known, y)[0], np.log(2))
        self.assertEqual(c.lr_weights(x, known, 1-y)[0], 0)

    def test_disjoint_groups(self):
        groups = np.repeat(np.arange(100), 40)
        parts = c.split_groups(groups, 10)
        self.assertEqual([len(p) for p in parts], [2400, 800, 800])
        sets = [set(groups[p]) for p in parts]
        self.assertFalse(sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])

    def test_ties_label_independent(self):
        y = np.r_[np.ones(5), np.zeros(95)]
        m = c.metrics(y, np.zeros(100), np.ones((100, 18), bool))
        self.assertAlmostEqual(m['precision_top5'], .05)
        self.assertAlmostEqual(m['AP'], .05)
        self.assertAlmostEqual(m['ROC_AUC'], .5)
        self.assertAlmostEqual(m['recall_top5'], .05)
        self.assertEqual(m, c.metrics(y[::-1], np.zeros(100), np.ones((100, 18), bool)))

    def test_boundary_ties(self):
        y = np.r_[1., 1., np.zeros(98)]
        scores = np.r_[2., np.ones(8), np.zeros(91)]
        m = c.metrics(y, scores, np.ones((100, 18), bool))
        self.assertAlmostEqual(m['precision_top5'], (1 + 4 / 8) / 5)
        self.assertAlmostEqual(m['AP'], (1 + 2 / 9) / 2)

    def test_family_bounds(self):
        x = np.ones((2, 18))
        self.assertTrue(np.all(c.family_score(x, np.full(18, 1000)) == 100))
        for family, cap in zip(c.FAMILY_NAMES, c.CAPS):
            isolated = x * (np.array(c.FAMILIES) == family)
            np.testing.assert_array_equal(c.family_score(isolated, np.full(18, 1000)), [cap, cap])
        x, known, _, labels, (train, val, _) = c.generate('independent', 0)
        fitted = c.fit_models(x[train], known[train], labels[train], x[val], labels[val], known[val])
        upper = np.array([c.CAPS[c.FAMILY_NAMES.index(f)] for f in c.FAMILIES])
        self.assertTrue(np.all((fitted['family'] >= 0) & (fitted['family'] <= upper)))
        self.assertTrue(any(fitted['selection']['logistic_converged']))

    def test_null_aggregates(self):
        self.assertEqual(c.summarize([None, None])['mean'], None)
        self.assertEqual(c.summarize([None, .5])['mean'], .5)
        m = c.metrics(np.zeros(10), np.zeros(10), np.ones((10, 18), bool))
        self.assertIsNone(m['AP'])
        self.assertIsNone(m['ROC_AUC'])

    def test_test_untouched(self):
        x, known, truth, discovery, (train, val, test) = c.generate('biased-discovery', 0)
        def fit():
            return c.fit_models(x[train], known[train], discovery[train], x[val], discovery[val], known[val])
        a = fit()
        x[test] = 1 - x[test]
        known[test] = False
        truth[test] = 1 - truth[test]
        discovery[test] = 1 - discovery[test]
        b = fit()
        for key in a:
            np.testing.assert_array_equal(a[key], b[key])

    def test_catalogue(self):
        import re
        script = (Path(__file__).parents[1] / 'script.js').read_text()
        block = script.split('const INDICATOR_KINDS = {', 1)[1].split('};', 1)[0]
        self.assertEqual(set(c.KINDS), set(re.findall(r"'([^']+)':", block)))
        self.assertEqual(len(c.KINDS), 18)
        np.testing.assert_array_equal(c.family_score(np.zeros((2, 18)), c.POINTS), [0, 0])


if __name__ == '__main__':
    unittest.main()
