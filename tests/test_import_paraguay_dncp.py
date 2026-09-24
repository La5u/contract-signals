import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("import_paraguay", Path(__file__).parents[1] / "tools/import-paraguay-dncp.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class DncpImportTests(unittest.TestCase):
    def sample(self):
        return {"ocid": "ocds-test-1", "releases": [{"id": "a"}], "compiledRelease": {
            "buyer": {"id": mod.BUYER, "name": "Municipalidad de Fernando de la Mora"},
            "tender": {"title": "Obra", "datePublished": "2024-10-01T00:00:00-04:00"},
            "awards": [{"id": "award1", "suppliers": [{"id": "PY-RUC-123", "name": "Empresa"}]}],
            "contracts": [{"id": "contract1", "awardID": "award1", "status": "active",
                           "period": {"startDate": "2025-01-02T00:00:00-04:00"},
                           "value": {"amount": 123, "currency": "PYG"},
                           "documents": [{"documentType": "contractSigned", "url": "https://www.contrataciones.gov.py/test"}]}],
        }}

    def test_contract_award_link_no_invented_signature(self):
        row, = mod.contract_rows(self.sample())
        self.assertEqual(row["contractId"], "contract1")
        self.assertEqual(row["awardId"], "award1")
        self.assertEqual(row["supplierIds"][0]["id"], "PY-RUC-123")
        self.assertEqual(row["date"], "2025-01-02")
        self.assertIsNone(row["signatureDate"])
        self.assertEqual(len(row["signedDocumentUrls"]), 1)

    def test_unlinked_unknown_supplier_or_other_currency_is_not_a_contract_row(self):
        record = self.sample()
        contract = record["compiledRelease"]["contracts"][0]
        contract["awardID"] = "missing"
        self.assertEqual(mod.contract_rows(record), [])
        contract["awardID"] = "award1"
        record["compiledRelease"]["awards"][0]["suppliers"] = []
        self.assertEqual(mod.contract_rows(record), [])
        record["compiledRelease"]["awards"][0]["suppliers"] = [{"id": "PY-RUC-123"}]
        contract["value"]["currency"] = "USD"
        self.assertEqual(mod.contract_rows(record), [])

    def test_wrong_buyer_rejected(self):
        record = self.sample()
        record["compiledRelease"]["buyer"]["id"] = "DNCP-SICP-CODE-999"
        with self.assertRaisesRegex(ValueError, "Buyer mismatch"):
            mod.contract_rows(record)

    def test_query_is_bounded_and_source_date_is_call_publication(self):
        url = mod.search_url(1)
        self.assertIn("parties.identifier.id=66", url)
        self.assertIn("2024-09-01", url)
        self.assertIn("2025-08-31", url)
        self.assertIn("tipo_fecha=publicacion_llamado", url)


if __name__ == "__main__":
    unittest.main()
