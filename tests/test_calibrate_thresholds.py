"""Synthetic identification tests; no network or writes into the repository."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
try:
    import numpy as np
    import scipy  # noqa: F401
except ImportError:
    np = None

if np is not None:
    spec = importlib.util.spec_from_file_location(
        "calibrate_thresholds", Path(__file__).resolve().parents[1] / "tools/calibrate-thresholds.py")
    calibration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(calibration)


@unittest.skipIf(np is None, "numpy/scipy not installed")
class CalibrationTests(unittest.TestCase):
    @staticmethod
    def row(**changes):
        row = {"dataStatus": "verified", "dataFamily": "boamp", "directAward": False,
               "offers": 2, "buyerId": "buyer", "buyer_key": "buyer", "cpv": "45000000",
               "cpv2": "45", "year": "2025", "cohort": "synthetic", "amount": 1000,
               "currency": "EUR", "date": "2025-01-01", "publicationDate": "2025-01-10",
               "supplierIds": [{"id": "supplier", "identifierType": "test"}]}
        row.update(changes)
        return row

    def synthetic(self, rates):
        rng = np.random.default_rng(813)
        rows = []
        for buyer in range(40):
            for value, rate in zip([15, 45, 90, 160, 400, 900], rates):
                for _ in range(30):
                    # Same distributions across bins; variation in all controls.
                    row = self.row(buyer_key=f"b{buyer:02}", y=int(rng.random() < rate),
                                   amount=float(np.exp(rng.normal(9, 1))),
                                   cpv2="45" if rng.random() < .5 else "72",
                                   year="2024" if rng.random() < .5 else "2025",
                                   publication_delay_days=value)
                    rows.append(row)
        return rows

    def test_known_jump_recovered_with_controls_and_buyer_clustering(self):
        result = calibration.analyze_input(self.synthetic([.12, .12, .12, .6, .7, .8]), "publication_delay_days")
        self.assertEqual(result["recommendation"]["status"], "recommend")
        self.assertEqual(result["recommendation"]["threshold"], 121)
        self.assertEqual(result["models"]["with_buyer_fe"]["regularization_l2"], 0)
        self.assertIn("buyer-cluster", result["models"]["with_buyer_fe"]["covariance"])
        self.assertGreater(result["bins"][3]["ci95"][0], 1)
        self.assertIsNotNone(result["weight_hint"])

    def test_null_input_has_no_recommendation(self):
        result = calibration.analyze_input(self.synthetic([.25] * 6), "publication_delay_days")
        self.assertEqual(result["recommendation"]["status"], "no_association")
        self.assertIsNone(result["recommendation"]["threshold"])

    def test_short_submission_jump_uses_upper_edge(self):
        rows = self.synthetic([.8, .7, .6, .12, .12, .12])
        mapping = dict(zip([15, 45, 90, 160, 400, 900], [5, 12, 18, 25, 40, 60]))
        for row in rows:
            row["submission_period_days"] = mapping[row["publication_delay_days"]]
        result = calibration.analyze_input(rows, "submission_period_days")
        self.assertEqual(result["recommendation"]["status"], "recommend")
        self.assertEqual(result["recommendation"]["threshold"], 22)
        self.assertEqual(result["recommendation"]["operator"], "<")

    def test_sparse_bins_merge_adjacent_and_preserve_counts(self):
        values = [5] * 50 + [15] * 4 + [25] * 50
        y = [1] * 15 + [0] * 35 + [1, 0, 0, 0] + [1] * 15 + [0] * 35
        bins, merges = calibration.merge_bins(values, y, [0, 10, 20, 30])
        self.assertEqual(len(bins), 2)
        self.assertEqual(bins[0]["members"], [0, 1])
        self.assertEqual(len(bins[0]["indices"]), 54)
        self.assertEqual(sum(len(b["indices"]) for b in bins), 104)
        self.assertEqual(merges, [[[0], [1]]])
        bins, _ = calibration.merge_bins([5] * 8, [1] * 8, [0, 10, 20])
        self.assertEqual(len(bins), 1)

    def test_unknown_competitiveness_and_offers_excluded(self):
        self.assertEqual(calibration.outcome(self.row(offers=1)), (1, None))
        self.assertEqual(calibration.outcome(self.row(offers=3)), (0, None))
        for changes in [{"directAward": None}, {"directAward": True}, {"offers": None},
                        {"offers": 0}, {"offers": 1.5}, {"offers": True},
                        {"identityAmbiguous": True}, {"initialConflicts": ["amount"]},
                        {"modificationConflicts": ["duration"]}, {"dataStatus": "unverified"},
                        {"dataStatus": "synthetic"}, {"findingScope": "aggregate"}]:
            self.assertIsNone(calibration.outcome(self.row(**changes))[0], changes)
        national = self.row(dataFamily="ted", procedureDirect=False, offers=1)
        del national["directAward"]
        self.assertEqual(calibration.outcome(national), (1, None))
        national["procedureDirect"] = None
        self.assertIsNone(calibration.outcome(national)[0])

    def test_dncp_offer_normalization_and_multi_lot_exclusion(self):
        row = self.row(dataFamily="dncp", procurementMethod="open", numberOfTenderers=2,
                       tenderersListed=2, lotCount=1)
        self.assertEqual(calibration.outcome(row), (0, None))
        row["lotCount"] = 2
        self.assertIsNone(calibration.outcome(row)[0])
        row.update(numberOfTenderers=1, tenderersListed=1)
        self.assertEqual(calibration.outcome(row), (1, None))
        row["tenderersListed"] = 2
        self.assertIsNone(calibration.outcome(row)[0])

    def test_leave_one_out_concentration_is_cohort_specific(self):
        rows = [self.row(supplierIds=[{"id": "a" if i < 8 else "b", "identifierType": "test"}])
                for i in range(12)]
        other = [self.row(cohort="other") for _ in range(15)]
        calibration.derive_context(rows + other)
        self.assertAlmostEqual(rows[0]["supplier_concentration_share"], 7 / 11)
        self.assertAlmostEqual(rows[9]["supplier_concentration_share"], 3 / 11)
        rows[0]["offers"] = 1
        calibration.derive_context(rows)
        self.assertAlmostEqual(rows[0]["supplier_concentration_share"], 7 / 11)
        small = [self.row() for _ in range(10)]
        calibration.derive_context(small)
        self.assertTrue(all(r["supplier_concentration_share"] is None for r in small))

    def test_buyer_baseline_does_not_cross_cohorts(self):
        rows = [self.row(publicationDate="2025-01-10") for _ in range(10)]
        other = [self.row(cohort="other", publicationDate="2025-03-10") for _ in range(30)]
        calibration.derive_context(rows + other)
        self.assertEqual(rows[0]["buyer_relative_delay_days"], 0)

    def test_buyer_median_excludes_self_and_negative_delay(self):
        rows = [self.row(publicationDate=f"2025-01-{i + 2:02}") for i in range(10)]
        negative = self.row(publicationDate="2024-12-30")
        calibration.derive_context(rows + [negative])
        self.assertEqual(rows[0]["buyer_relative_delay_days"], 1 - 6)
        self.assertIsNone(negative["publication_delay_days"])
        self.assertIsNone(negative["buyer_relative_delay_days"])

    def test_duplicate_decp_identity_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            rows = [self.row(dataFamily="decp", buyerSiret="123", contractId="c") for _ in range(2)]
            (root / "data/cohort.json").write_text(json.dumps({"contracts": rows}))
            _, eligible, excluded, _ = calibration.load_country(root, ["cohort"])
            self.assertEqual(eligible, [])
            self.assertEqual(excluded, {"ambiguous_identity": 2})

    def test_small_cluster_count_withholds_threshold(self):
        rows = self.synthetic([.12, .12, .12, .6, .7, .8])
        for row in rows:
            row["buyer_key"] = "one"
        result = calibration.analyze_input(rows, "publication_delay_days")
        self.assertEqual(result["recommendation"]["status"], "insufficient_evidence")
        self.assertIsNone(result["weight_hint"])

    def test_amount_increase_unknown_without_amendment(self):
        row = self.row(dataFamily="decp", priceType="Définitif ferme", amount=100,
                       history=[{"kind": "initial", "date": "2025-01-01", "amount": 100}])
        self.assertIsNone(calibration.amount_increase(row))
        row["history"].append({"kind": "modification", "date": "2025-02-01", "amount": 125})
        self.assertEqual(calibration.amount_increase(row), 25)
        row["priceType"] = "Définitif révisable"
        self.assertIsNone(calibration.amount_increase(row))

    def test_determinism(self):
        rows = self.synthetic([.12, .12, .12, .6, .7, .8])
        first = calibration.serialize(calibration.analyze_input(rows, "publication_delay_days"))
        second = calibration.serialize(calibration.analyze_input(rows, "publication_delay_days"))
        self.assertEqual(first, second)
        self.assertNotIn("generated_at", first)


if __name__ == "__main__":
    unittest.main()
