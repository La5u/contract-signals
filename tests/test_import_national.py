import gzip
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ted = load("ted", "import-ted-cohorts.py")
ua = load("ua", "import-prozorro.py")
uk = load("uk", "import-find-a-tender.py")


class TedTests(unittest.TestCase):
    def test_identifier_variants_cover_published_spellings(self):
        self.assertIn("505 187 531", ted.variants(ted.COHORTS["portugal"], "505187531"))
        self.assertIn("RO4288110", ted.variants(ted.COHORTS["romania"], "4288110"))

    def test_published_extracts_are_what_the_importer_builds(self):
        for key in ted.COHORTS:
            manifest = json.loads((ted.raw_dir(key) / "manifest.json").read_text(encoding="utf-8"))
            built = {}
            for buyer in manifest["buyers"]:
                for pub in buyer["publicationNumbers"]:
                    rows, _ = ted.notice_rows(ted.COHORTS[key], pub, gzip.decompress((ted.raw_dir(key) / "notices" / f"{pub}.xml.gz").read_bytes()))
                    built.update({r["id"]: r for r in rows})
            published = json.loads((ROOT / f"data/ted-{key}.json").read_text(encoding="utf-8"))
            for row in published:
                self.assertEqual(row, built[row["id"]], row["id"])

    def test_foreign_winner_numbers_are_not_national_identifiers(self):
        rows = json.loads((ROOT / "data/ted-portugal.json").read_text(encoding="utf-8"))
        for row in rows:
            for s in row["supplierIds"]:
                if s["identifierType"] == "NIF":
                    self.assertTrue(s["id"].isdigit())


class ProzorroTests(unittest.TestCase):
    def test_offers_are_counted_per_lot_and_unknown_without_bids(self):
        tender = {"bids": [{"status": "active", "lotValues": [{"relatedLot": "a"}, {"relatedLot": "b"}]},
                           {"status": "active", "lotValues": [{"relatedLot": "b"}]},
                           {"status": "deleted", "lotValues": [{"relatedLot": "a"}]}]}
        self.assertEqual(ua.offers_for(tender, "a"), 1)
        self.assertEqual(ua.offers_for(tender, "b"), 2)
        self.assertIsNone(ua.offers_for({}, "a"))

    def test_identifier_types(self):
        self.assertEqual(ua.supplier_identifier({"scheme": "UA-EDR", "id": "39502491"})["identifierType"], "EDRPOU")
        self.assertEqual(ua.supplier_identifier({"scheme": "UA-EDR", "id": "1234567890"})["identifierType"], "RNOKPP")

    def test_published_extract_is_what_the_importer_builds(self):
        manifest = json.loads((ua.RAW / "manifest.json").read_text(encoding="utf-8"))
        built = {}
        for buyer in manifest["buyers"]:
            for tender_id in buyer["tenderIDs"]:
                tender = ua.load_gz(ua.RAW / "records" / f"{tender_id}.json.gz")["data"]
                if tender["procuringEntity"]["identifier"].get("id") == buyer["code"]:
                    built.update({r["id"]: r for r in ua.contract_rows(tender)[0]})
        for row in json.loads(ua.EXTRACT.read_text(encoding="utf-8")):
            self.assertEqual(row, built[row["id"]], row["id"])



class FindATenderTests(unittest.TestCase):
    def test_offers_are_per_lot_and_unknown_without_statistics(self):
        release = {"bids": {"statistics": [{"measure": "bids", "relatedLot": "1", "value": 3}, {"measure": "smeBids", "relatedLot": "1", "value": 1},
                                           {"measure": "bids", "relatedLot": "2", "value": 1}]}}
        self.assertEqual(uk.offers_for(release, "1", False), 3)
        self.assertEqual(uk.offers_for(release, "2", False), 1)
        self.assertIsNone(uk.offers_for(release, "3", False))
        self.assertIsNone(uk.offers_for({}, "1", True))

    def test_published_extract_is_what_the_importer_builds(self):
        manifest = json.loads((uk.RAW / "manifest.json").read_text(encoding="utf-8"))
        built = {}
        for notice in manifest["noticeIds"]:
            for release in json.loads(gzip.decompress((uk.RAW / "notices" / f"{notice}.json.gz").read_bytes()))["releases"]:
                built.update({r["id"]: r for r in uk.notice_rows(release)[0]})
        published = json.loads(uk.EXTRACT.read_text(encoding="utf-8"))
        self.assertEqual(len(published), 1081)
        for row in published:
            self.assertEqual(row, built[row["id"]], row["id"])


if __name__ == "__main__":
    unittest.main()
