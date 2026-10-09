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


class BoampRobustnessTests(unittest.TestCase):
    def setUp(self):
        self.company = {
            "cac:PartyIdentification": {"cbc:ID": "ORG-1"},
            "cac:PartyName": {"cbc:Name": "Holder"},
            "cac:PartyLegalEntity": {"cbc:CompanyID": "45341407000012"},
            "cac:PostalAddress": {"cac:Country": {"cbc:IdentificationCode": "FRA"}},
        }
        self.party = {"cbc:ID": "TP-1", "efac:Tenderer": {"cbc:ID": "ORG-1"}}
        self.amount = {"@currencyID": "EUR", "#text": "12.5"}
        self.duration = {"@unitCode": "MONTH", "#text": "6"}
        self.contract = {"cbc:ID": "CON-1", "cbc:IssueDate": "2024-02-29"}
        self.result = {
            "cbc:ID": "RES-1", "cbc:TenderResultCode": "selec-w",
            "efac:LotTender": {"cbc:ID": "TEN-1"},
            "efac:SettledContract": {"cbc:ID": "CON-1"},
            "efac:TenderLot": {"cbc:ID": "LOT-1"},
        }
        self.ext = {
            "efac:Organizations": {"efac:Organization": [{"efac:Company": self.company}]},
            "efac:NoticeResult": {
                "efac:TenderingParty": self.party,
                "efac:LotTender": {"cbc:ID": "TEN-1", "efac:TenderingParty": {"cbc:ID": "TP-1"},
                                   "cac:LegalMonetaryTotal": {"cbc:PayableAmount": self.amount}},
                "efac:SettledContract": self.contract, "efac:LotResult": self.result,
            },
        }
        self.notice = {
            "ext:UBLExtensions": {"ext:UBLExtension": {"ext:ExtensionContent": {"efext:EformsExtension": self.ext}}},
            "cac:ProcurementProjectLot": {"cbc:ID": "LOT-1", "cac:ProcurementProject": {
                "cac:PlannedPeriod": {"cbc:DurationMeasure": self.duration}}},
        }
        self.record = {"idweb": "SYNTHETIC", "dateparution": "2025-03-01", "nomacheteur": "Buyer"}

    def rows(self):
        self.record["donnees"] = json.dumps({"EFORMS": {"ContractAwardNotice": self.notice}})
        return mod.lot_rows(self.record)

    def row(self):
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertNotIn("excluded", rows[0])
        # The normalized output must always be strict JSON.
        json.dumps(rows, allow_nan=False)
        return rows[0]

    def test_amount_and_duration_preserve_zero_and_finite_values(self):
        for value, expected in [("0", 0), (0, 0), ("12.5", 12.5)]:
            with self.subTest(value=value):
                self.amount["#text"] = self.duration["#text"] = value
                row = self.row()
                self.assertEqual(row["amount"], expected)
                self.assertEqual(row["durationMonths"], float(expected))
                self.assertIsInstance(row["durationMonths"], float)

    def test_amount_and_duration_reject_negative_nonfinite_and_malformed(self):
        for value in ["-1", "NaN", "Infinity", "-Infinity", "1e999", float("nan"),
                      float("inf"), float("-inf"), "bad", "", None, {}, []]:
            with self.subTest(value=value):
                self.amount["#text"] = self.duration["#text"] = value
                row = self.row()
                self.assertIsNone(row["amount"])
                self.assertIsNone(row["durationMonths"])
        del self.amount["#text"]
        del self.duration["#text"]
        self.assertIsNone(self.row()["amount"])
        self.assertIsNone(self.row()["durationMonths"])

    def test_currency_and_duration_units_are_not_inferred(self):
        self.amount["@currencyID"] = "CHF"
        self.duration["@unitCode"] = "DAY"
        row = self.row()
        self.assertIsNone(row["amount"])
        self.assertIsNone(row["durationMonths"])

    def test_valid_dates_and_timestamps(self):
        for value in ["2024-02-29", "2024-02-29Z", "2024-02-29+01:00", "2024-02-29-02:00",
                      "2024-02-29T23:30:00Z", "2024-02-29T23:30:00+02:00",
                      {"#text": "2024-02-29"}]:
            with self.subTest(value=value):
                self.contract["cbc:IssueDate"] = self.record["dateparution"] = value
                row = self.row()
                self.assertEqual(row["date"], "2024-02-29")
                self.assertEqual(row["publicationDate"], "2024-02-29")

    def test_impossible_and_nonstring_dates_are_unknown(self):
        for value in ["2025-02-30", "2025-02-29", "2025-13-01", "2025-00-01", "2025-01-00",
                      "2025-02-30T12:00:00Z", "2025-02-30+01:00", "2025-01-01+99:00",
                      "2025-01-01T25:00:00Z", "2025-01-01garbage",
                      "20250101", "", None, 20250101, [], {}, {"#text": 123}]:
            with self.subTest(value=value):
                self.contract["cbc:IssueDate"] = self.record["dateparution"] = value
                row = self.row()
                self.assertIsNone(row["date"])
                self.assertIsNone(row["publicationDate"])
        self.record["dateparution"] = "2025-03-01"
        del self.contract["cbc:IssueDate"]
        self.assertIsNone(self.row()["date"])  # publication is never a fallback

    def statistics(self, *values):
        self.result["efac:ReceivedSubmissionsStatistics"] = [
            {"efbc:StatisticsCode": {"#text": "tenders"}, "efbc:StatisticsNumeric": v} for v in values]

    def test_statistics_zero_text_nodes_and_identical_totals(self):
        for values, expected in [(["0"], 0), ([0], 0), ([{"#text": "0"}], 0),
                                 (["2", {"#text": "2"}, 2], 2)]:
            with self.subTest(values=values):
                self.statistics(*values)
                self.assertEqual(self.row()["offers"], expected)

    def test_conflicting_statistics_are_unknown_in_either_order(self):
        for values in [("1", "2"), ("2", "1"), ("0", {"#text": "1"}), ("1", "bad")]:
            with self.subTest(values=values):
                self.statistics(*values)
                self.assertIsNone(self.row()["offers"])

    def test_invalid_statistics_and_subset_codes_are_unknown(self):
        for value in [None, "", "bad", "-1", "1.5", "1.0", "NaN", "Infinity", {}, "²"]:
            with self.subTest(value=value):
                self.statistics(value)
                self.assertIsNone(self.row()["offers"])
        self.result["efac:ReceivedSubmissionsStatistics"] = {"efbc:StatisticsCode": "t-esubm", "efbc:StatisticsNumeric": "7"}
        self.assertIsNone(self.row()["offers"])
        self.statistics("0")
        self.result["efac:ReceivedSubmissionsStatistics"].append({"efbc:StatisticsCode": "t-sme", "efbc:StatisticsNumeric": "9"})
        self.assertEqual(self.row()["offers"], 0)

    def test_missing_first_middle_or_last_holder_reference_excludes_candidate(self):
        for refs in [["ORG-MISSING", "ORG-1"], ["ORG-1", "ORG-MISSING", "ORG-1"],
                     ["ORG-1", "ORG-MISSING"], [None, "ORG-1"], ["ORG-MISSING"]]:
            with self.subTest(refs=refs):
                self.party["efac:Tenderer"] = [{"cbc:ID": ref} for ref in refs]
                self.assertEqual(self.rows(), [{"excluded": "unresolved holder organization reference"}])
                sample, stats = mod.build({"records": [self.record]})
                self.assertEqual(sample, [])
                self.assertEqual(stats["excludedResults"], 1)
                self.assertEqual(stats["eligible_awarded_supplier"], 0)

    def test_resolved_holder_references_stay_paired_in_source_order(self):
        other = dict(self.company)
        other.update({"cac:PartyIdentification": {"cbc:ID": "ORG-2"},
                      "cac:PartyName": {"cbc:Name": "Other holder"},
                      "cac:PartyLegalEntity": {"cbc:CompanyID": "123456789"}})
        self.ext["efac:Organizations"]["efac:Organization"].append({"efac:Company": other})
        self.party["efac:Tenderer"] = [{"cbc:ID": "ORG-2"}, {"cbc:ID": "ORG-1"}]
        row = self.row()
        self.assertEqual(row["supplier"], "Other holder / Holder")
        self.assertEqual([v["id"] for v in row["supplierIds"]], ["123456789", "45341407000012"])
        self.assertIn("supplier organization ORG-2, ORG-1;", row["sourceReference"])


if __name__ == "__main__":
    unittest.main()
