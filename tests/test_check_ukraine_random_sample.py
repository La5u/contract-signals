"""Published Prozorro rows must match their cached official records; the random sample stays frozen."""
import copy
import gzip
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('random_sample', ROOT / 'tools/check-ukraine-random-sample.py')
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


def raw(row):
    return json.loads(gzip.decompress((C.RAW / f"{row['tenderID']}.json.gz").read_bytes()))['data']


class RandomSampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((ROOT / C.ROWS).read_text())

    def test_plan_is_reproducible_and_frozen(self):
        self.assertEqual(json.loads(C.PLAN.read_text()), C.plan())

    def test_every_published_field_matches_cached_record(self):
        for row in self.rows:
            want = C.expected(raw(row), row)
            for f in C.FIELDS:
                self.assertEqual(row[f], want[f], f'{row["id"]} {f}')

    def test_corrupted_fields_are_detected(self):
        row = self.rows[0]
        want = C.expected(raw(row), row)
        for f in C.FIELDS:
            bad = copy.deepcopy(row)
            bad[f] = bad[f] + 1 if isinstance(bad[f], (int, float)) and not isinstance(bad[f], bool) else 'WRONG'
            self.assertNotEqual(bad[f], want[f], f)

    def test_results_bind_the_frozen_plan(self):
        res = json.loads(C.RESULTS.read_text())
        self.assertEqual(res['planSha256'], C.sha(C.PLAN.read_bytes()))
        self.assertEqual([r['rowId'] for r in res['results']], json.loads(C.PLAN.read_text())['selected'])
        self.assertEqual(res['totals'], {'importErrors': 0, 'sourceChangedSinceImport': 0, 'moduleDisagreements': 0})


if __name__ == '__main__':
    unittest.main()
