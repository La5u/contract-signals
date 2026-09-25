import gzip
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("import_boamp", ROOT / "tools/import-boamp-sample.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class BoampRebuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(gzip.decompress(mod.RAW.read_bytes()))
        cls.sample, cls.stats = mod.build(cls.raw)

    def test_processing_counts_match_the_recorded_download(self):
        self.assertEqual(self.raw["total"], 8386)
        self.assertEqual({k: self.stats[k] for k in ["unsupportedSchemaRecords", "eligible_awarded_supplier", "distinct_notice_lot_ids",
                                                     "conflicting_notice_lot_ids_excluded", "unique_eligible_lots"]},
                         {"unsupportedSchemaRecords": 2153, "eligible_awarded_supplier": 16002, "distinct_notice_lot_ids": 15432,
                          "conflicting_notice_lot_ids_excluded": 236, "unique_eligible_lots": 15196})

    def test_published_sample_is_what_the_importer_produces(self):
        published = [r for r in json.loads((ROOT / "data/contracts.json").read_text(encoding="utf-8"))
                     if r.get("dataFamily") == "boamp" and not r["id"].startswith("boamp-25-846-")]
        self.assertEqual(published, self.sample)

    def test_foreign_numbers_are_not_french_identifiers(self):
        row = next(r for r in self.sample if r["id"] == "boamp-25-39677-lot-0001")  # Dutch company, 14-digit number
        self.assertEqual(row["supplierIds"][0]["identifierType"], "identifiant publié")
        self.assertIsNone(row["supplierIds"][0]["siren"])

    def test_winner_identifier_comes_from_the_winning_tenderer(self):
        row = next(r for r in self.sample if r["id"] == "boamp-25-48061-lot-0001")
        self.assertEqual(row["supplier"], "COSTE ET FILS")
        self.assertEqual(row["supplierIds"], [{"id": "45341407000012", "identifierType": "SIRET", "siren": "453414070"}])


if __name__ == "__main__":
    unittest.main()
