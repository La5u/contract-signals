import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("audit_prozorro", ROOT / "tools/audit-prozorro.py")
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


class ProzorroAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit_module.audit(ROOT)

    def test_discovery_is_unique_and_complete_against_manifest(self):
        d = self.report["discovery"]
        self.assertEqual(d["manifestIDs"], 542)
        self.assertEqual(d["uniqueManifestIDs"], 542)
        self.assertEqual(d["rawFiles"], 542)
        self.assertEqual(d["uniqueRawTenderIDs"], 542)
        self.assertEqual(d["missingRawRecords"], [])
        self.assertEqual(d["unlistedRawRecords"], [])
        self.assertEqual(d["crossBuyerDuplicateTenderIDs"], [])
        self.assertTrue(all(b["searchListingCountConsistent"] for b in d["buyers"]))

    def test_date_buyer_match_and_known_exclusion_counts(self):
        m = self.report["matching"]
        self.assertEqual(m["inWindowBuyerMatchedTenders"], 526)
        self.assertEqual(len(m["listedBuyerMismatch"]), 16)
        self.assertEqual(m["outsideWindowByRecordDate"], [])
        self.assertEqual(m["tenderIdDateVsRecordDateMismatches"], [])

    def test_contract_award_supplier_joins_exclusions_and_offer_attribution(self):
        j = self.report["joinsAndExclusions"]
        self.assertEqual(j["retainedRawJoins"], 488)
        self.assertEqual(j["snapshotRows"], 488)
        self.assertEqual(j["missingSnapshotRows"], [])
        self.assertEqual(j["extraSnapshotRows"], [])
        self.assertEqual(j["excludedContracts"], {"contract status not signed: cancelled": 3, "contract status not signed: pending": 5})
        self.assertEqual(self.report["offers"]["competitiveRowsWithCount"], 64)
        self.assertEqual(self.report["offers"]["competitiveRowsUnknown"], 0)
        self.assertEqual(self.report["offers"]["snapshotOfferMismatches"], [])
        self.assertEqual(j["coverageMismatches"], {})

    def test_fixed_sample_contains_signalled_and_unflagged_source_records(self):
        samples = self.report["samples"]
        self.assertEqual(len(samples), 7)
        self.assertEqual(sum(s["sampleClass"] == "single-offer signal" for s in samples), 4)
        self.assertEqual(sum(s["sampleClass"] == "no single-offer signal" for s in samples), 3)
        self.assertEqual(len({s["tenderID"] for s in samples}), 7)
        self.assertEqual(self.report["summary"]["status"], "consistent-with-importer-exclusions")

    def test_saved_report_matches_offline_audit(self):
        saved = json.loads((ROOT / "data/prozorro-audit.json").read_text())
        saved["mode"] = "offline-snapshot-only"
        for sample in saved["samples"]:
            sample.pop("liveApi", None)
        self.assertEqual(saved, self.report)

    def fixture(self, root):
        data = root / "data/prozorro/raw"
        (data / "records").mkdir(parents=True)
        tid, buyer = "UA-2025-01-01-000001-a", "buyer"
        tender = {"id": "internal", "tenderID": tid, "dateCreated": "2025-01-01T00:00:00Z",
                  "procurementMethodType": "reporting", "procuringEntity": {"identifier": {"id": buyer}},
                  "awards": [{"id": "award", "status": "active", "suppliers": [{"identifier": {"id": "supplier"}}]}],
                  "contracts": [{"contractID": "contract", "awardID": "award", "status": "active"}]}
        (data / "records" / f"{tid}.json.gz").write_bytes(gzip.compress(json.dumps({"data": tender}).encode()))
        manifest = {"buyers": [{"code": buyer, "searchTotal": 1, "listedTenderIDs": 1, "tenderIDs": [tid]}]}
        (data / "manifest.json").write_text(json.dumps(manifest))
        row = {"id": "row", "tenderID": tid, "contractId": "contract", "awardId": "award", "buyerId": buyer, "offers": None}
        (root / "data/prozorro.json").write_text(json.dumps([row]))
        coverage = {"counts": {"tendersInWindow": 1, "tendersOutsideWindowByDateCreated": 0,
                    "tendersWithAnotherBuyer": 0, "procedureTypes": {"reporting": 1}, "retainedContracts": 1,
                    "excludedContracts": {}, "withOffers": 0}}
        (root / "data/prozorro-coverage.json").write_text(json.dumps(coverage))
        return data, manifest, tender, row, coverage

    def mutate_and_audit(self, change):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, manifest, tender, row, coverage = self.fixture(root)
            change(data, manifest, tender, row, coverage)
            (data / "manifest.json").write_text(json.dumps(manifest))
            (data / "records" / f"{tender['tenderID']}.json.gz").write_bytes(gzip.compress(json.dumps({"data": tender}).encode()))
            (root / "data/prozorro.json").write_text(json.dumps([row]))
            (root / "data/prozorro-coverage.json").write_text(json.dumps(coverage))
            return audit_module.audit(root)

    def test_mutations_fail_for_duplicate_ids_and_search_totals(self):
        def duplicate(data, manifest, tender, row, coverage): manifest["buyers"][0]["tenderIDs"].append(tender["tenderID"])
        def total(data, manifest, tender, row, coverage): manifest["buyers"][0]["searchTotal"] = 2
        self.assertIn("duplicate manifest IDs", self.mutate_and_audit(duplicate)["summary"]["failures"])
        self.assertIn("inconsistent search totals", self.mutate_and_audit(total)["summary"]["failures"])

    def test_mutations_fail_for_duplicate_join_keys_and_unmatched_awards(self):
        def duplicate(data, manifest, tender, row, coverage):
            tender["contracts"].append(dict(tender["contracts"][0]))
            row["id"] = "row-2"
        def unmatched(data, manifest, tender, row, coverage): tender["contracts"][0]["awardID"] = "missing"
        self.assertIn("duplicate join keys", self.mutate_and_audit(duplicate)["summary"]["failures"])
        report = self.mutate_and_audit(unmatched)
        self.assertIn("unmatched contract awards", report["summary"]["failures"])

    def test_coverage_procedure_and_exclusion_mutations_fail(self):
        def mismatch(data, manifest, tender, row, coverage):
            coverage["counts"]["procedureTypes"] = {"other": 1}
            coverage["counts"]["excludedContracts"] = {"contract not signed (pending)": 1}
        report = self.mutate_and_audit(mismatch)
        self.assertIn("coverage count/procedure/exclusion mismatches", report["summary"]["failures"])
        self.assertIn("procedureTypes", report["joinsAndExclusions"]["coverageMismatches"])
        self.assertIn("excludedContracts", report["joinsAndExclusions"]["coverageMismatches"])

    def test_live_api_check_is_bounded_and_reports_every_selected_field(self):
        from unittest.mock import patch
        current = {"id": "internal", "tenderID": "UA-x", "dateCreated": "d", "status": "complete",
                   "procurementMethodType": "reporting", "procuringEntity": {"identifier": {"id": "b"}},
                   "awards": [{"id": "a", "status": "active", "suppliers": [{"identifier": {"id": "s"}}]}],
                   "contracts": [{"contractID": "c", "awardID": "a"}], "bids": [{"status": "active"}]}
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps({"data": current}).encode()
        tender = {"id": "internal", "tenderID": "UA-x", "dateCreated": "d", "status": "complete",
                  "procurementMethodType": "reporting", "procuringEntity": {"identifier": {"id": "b"}},
                  "awards": current["awards"], "contracts": current["contracts"]}
        contract, award = current["contracts"][0], current["awards"][0]
        tender["bids"] = current["bids"]
        with patch.object(audit_module.urllib.request, "urlopen", return_value=Response()) as call:
            out = audit_module.live_check(tender, contract, award, 1)
        self.assertEqual(out["result"], "match")
        self.assertEqual(set(out["fields"]), {"tenderID", "internalId", "dateCreated", "buyerId", "contractId", "awardId", "supplierIds", "offerCount"})
        self.assertTrue(out["apiUrl"].endswith("/internal"))
        self.assertIn("checkedAt", out)
        self.assertEqual(call.call_args.kwargs["timeout"], 4)


if __name__ == "__main__":
    unittest.main()
