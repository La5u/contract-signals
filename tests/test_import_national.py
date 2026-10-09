import gzip
import importlib.util
import json
import tempfile
import unittest
import urllib.error
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ted = load("ted", "import-ted-cohorts.py")
ua = load("ua", "import-prozorro.py")
uk = load("uk", "import-find-a-tender.py")
cl = load("cl", "import-chilecompra.py")


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
    def fixture(self, directory):
        raw = directory / "raw"
        raw.mkdir()
        tender = {"id": "tender-internal", "tenderID": "UA-2025-01-01-test",
                  "dateCreated": "2025-01-01", "procurementMethodType": "reporting",
                  "procuringEntity": {"identifier": {"id": ua.BUYERS[0]["code"]}},
                  "awards": [{"id": "award", "status": "active", "suppliers": [{"name": "Fixture"}]}],
                  "contracts": [{"id": "a", "contractID": "published-a", "status": "active", "awardID": "award"},
                                {"id": "b", "contractID": "published-b", "status": "terminated", "awardID": "award"},
                                {"id": "c", "contractID": "published-c", "status": "active", "awardID": "award"}]}
        manifest = {"buyers": [dict(b, tenderIDs=[tender["tenderID"]] if i == 0 else [],
                                    searchUrl="fixture", searchTotal=1 if i == 0 else 0,
                                    listedTenderIDs=1 if i == 0 else 0) for i, b in enumerate(ua.BUYERS)],
                    "window": {}, "retrievalStartedAt": "fixture"}
        (raw / "manifest.json").write_text(json.dumps(manifest))
        ua.save_gz(raw / "records" / f"{tender['tenderID']}.json.gz", {"data": tender})
        return patch.multiple(ua, RAW=raw, EXTRACT=directory / "extract.json",
                              COVERAGE=directory / "coverage.json", CHANGES=directory / "changes.json")

    def test_offline_merges_minimized_changes_and_preserves_unknown(self):
        with tempfile.TemporaryDirectory() as temp, self.fixture(Path(temp)):
            ua.CHANGES.write_text(json.dumps({"contracts": {
                "a": {"changes": 3, "rationaleTypes": ["priceReduction"]},
                "b": {"changes": 0, "rationaleTypes": []}}}))
            with patch.object(ua.urllib.request, "urlopen", side_effect=AssertionError("offline network call")):
                ua.offline()
            rows = {r["contractInternalId"]: r for r in json.loads(ua.EXTRACT.read_text())}
            self.assertEqual(rows["a"]["contractChanges"], 3)
            self.assertEqual(rows["a"]["contractChangeTypes"], ["priceReduction"])
            self.assertEqual(rows["b"]["contractChanges"], 0)
            self.assertNotIn("contractChanges", rows["c"])
            self.assertNotIn("contractChangeTypes", rows["c"])
            counts = json.loads(ua.COVERAGE.read_text())["counts"]
            self.assertEqual(counts["withContractChanges"], 2)
            self.assertEqual(counts["withoutContractChanges"], 1)
            ua.CHANGES.unlink()
            ua.offline()
            self.assertTrue(all("contractChanges" not in r for r in json.loads(ua.EXTRACT.read_text())))

    def test_fetch_minimizes_retries_and_resumes(self):
        with tempfile.TemporaryDirectory() as temp, self.fixture(Path(temp)):
            ua.CHANGES.write_text(json.dumps({"contracts": {"a": {"changes": 0, "rationaleTypes": [],
                                                                    "changeDates": [], "status": "active"}}}))
            body = {"data": {"id": "b", "status": "terminated", "name": "omit", "contactPoint": {}, "documents": [],
                             "changes": [{"status": "active", "dateSigned": "2025-03-01", "rationaleTypes": ["taxRate", "priceReduction"]},
                                         {"status": "pending", "rationaleTypes": ["omit"]},
                                         {"status": "active", "dateSigned": "2025-02-01", "rationaleTypes": ["taxRate"]}]}}
            responses = [urllib.error.HTTPError("fixture", 429, "throttled", {}, None),
                         urllib.error.HTTPError("fixture", 503, "unavailable", {}, None), StringIO(json.dumps(body)),
                         urllib.error.HTTPError("fixture", 404, "missing", {}, None)]
            with patch.object(ua.urllib.request, "urlopen", side_effect=responses) as fetch, patch.object(ua.time, "sleep") as sleep:
                ua.fetch_contract_changes()
            self.assertEqual([call.args[0].full_url for call in fetch.call_args_list],
                             [f"{ua.API}/contracts/b"] * 3 + [f"{ua.API}/contracts/c"])
            self.assertEqual([call.args[0] for call in sleep.call_args_list], [1, 1, 1, 2, 1, 1])
            snapshot = json.loads(ua.CHANGES.read_text())
            self.assertEqual(snapshot["contracts"]["b"], {"changes": 2, "rationaleTypes": ["priceReduction", "taxRate"],
                                                         "changeDates": ["2025-02-01", "2025-03-01"], "status": "terminated"})
            self.assertEqual(snapshot["failedIds"], ["c"])
            with patch.object(ua.urllib.request, "urlopen", return_value=StringIO(json.dumps({"data": {"id": "c", "status": "active"}}))) as fetch, patch.object(ua.time, "sleep"):
                ua.fetch_contract_changes()
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(json.loads(ua.CHANGES.read_text())["failedIds"], [])

    def test_fetch_stops_and_checkpoints_on_403(self):
        with tempfile.TemporaryDirectory() as temp, self.fixture(Path(temp)):
            with patch.object(ua.urllib.request, "urlopen", side_effect=urllib.error.HTTPError("fixture", 403, "blocked", {}, None)) as fetch, patch.object(ua.time, "sleep"):
                with self.assertRaises(SystemExit):
                    ua.fetch_contract_changes()
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(json.loads(ua.CHANGES.read_text())["failedIds"], ["a"])

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
        ua.merge_contract_changes(list(built.values()))
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



class ChileCompraTests(unittest.TestCase):
    def test_procedure_kind_from_published_name(self):
        self.assertIs(cl.tender_kind("Licitación Pública Menor a 100 UTM (L1)"), False)
        self.assertIs(cl.tender_kind("Licitación Privada Menor a 100 UTM."), False)
        self.assertIsNone(cl.tender_kind(None))

    def test_published_extract_is_what_the_importer_builds(self):
        manifest = json.loads((cl.RAW / "manifest.json").read_text(encoding="utf-8"))
        built = {}
        for buyer in manifest["buyers"]:
            for code in buyer["codes"]:
                apath, tpath = cl.RAW / "records" / "award" / f"{code}.json.gz", cl.RAW / "records" / "tender" / f"{code}.json.gz"
                if not apath.exists() or cl.api_error(apath) is not None:
                    continue
                package = cl.load_gz(apath)
                if not package.get("releases"):
                    continue
                tender = cl.load_gz(tpath)["releases"][0] if tpath.exists() and cl.api_error(tpath) is None else None
                built.update({r["id"]: r for r in cl.award_rows(code, tender, package)[0]})
        published = json.loads(cl.EXTRACT.read_text(encoding="utf-8"))
        self.assertEqual(len(published), 522)
        for row in published:
            self.assertEqual(row, built[row["id"]], row["id"])


if __name__ == "__main__":
    unittest.main()
