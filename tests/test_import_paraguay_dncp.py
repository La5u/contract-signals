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

    def test_tenderers_amendments_and_portal_pages_are_copied_not_inferred(self):
        record = self.sample()
        release = record["compiledRelease"]
        release["tender"].update({"procurementMethod": "open", "procurementMethodDetails": "Menor cuantía nacional",
                                  "numberOfTenderers": 1, "tenderers": [{"id": "PY-RUC-123"}], "mainProcurementCategory": "works",
                                  "documents": [{"title": "URL de la Convocatoria", "url": mod.PORTAL + "convocatoria/x.html"},
                                                {"title": "Pliego", "url": "https://example.org/not-portal.html"}]})
        release["awards"][0]["documents"] = [{"title": "URL de la Adjudicación", "url": mod.PORTAL + "adjudicacion/x/resumen-adjudicacion.html"}]
        release["contracts"][0]["amendments"] = [{"id": "am1", "date": "2025-02-01T00:00:00-04:00", "description": "Ampliación de Monto",
                                                  "amendsAmount": {"amount": 20, "currency": "PYG"}, "financialCode": "AC-1"}]
        row, = mod.contract_rows(record)
        self.assertEqual((row["procurementMethod"], row["numberOfTenderers"], row["tenderersListed"], row["category"]), ("open", 1, 1, "works"))
        self.assertEqual(row["supplierIds"][0]["identifierType"], "RUC")
        self.assertEqual(row["amendments"], [{"id": "am1", "date": "2025-02-01", "description": "Ampliación de Monto", "amount": 20, "currency": "PYG", "entryId": "AC-1"}])
        self.assertEqual(row["callUrl"], mod.PORTAL + "convocatoria/x.html")
        self.assertTrue(row["awardUrl"].endswith("resumen-adjudicacion.html"))

    def test_missing_counts_and_pages_stay_missing(self):
        row, = mod.contract_rows(self.sample())
        self.assertIsNone(row["numberOfTenderers"])
        self.assertIsNone(row["tenderersListed"])
        self.assertIsNone(row["callUrl"])
        self.assertIsNone(row["awardUrl"])
        self.assertEqual(row["amendments"], [])

    def test_three_buyer_cohort_is_announced_and_bounded(self):
        cohort = mod.COHORTS["3buyers"]
        self.assertEqual([b["code"] for b in cohort["buyers"]], ["20", "81", "108"])
        self.assertEqual({b["level"] for b in cohort["buyers"]}, {"national", "departmental", "municipal"})
        url = mod.search_url(1, "108", cohort["start"], cohort["end"])
        self.assertIn("parties.identifier.id=108", url)
        self.assertIn("fecha_hasta=2026-08-31", url)
        self.assertNotEqual(cohort["raw"], mod.COHORTS["fernando"]["raw"])
        self.assertNotEqual(cohort["extract"], mod.COHORTS["fernando"]["extract"])

    def test_only_debarments_covering_the_award_date_are_attached(self):
        snap = {"retrievedAt": "2026-09-25T00:00:00", "suppliers": [{"id": "PY-RUC-1", "sanctions": [
            {"type": "INHABILITACION", "start": "2025-01-01", "end": "2025-06-30", "status": "Activo", "description": "x"},
            {"type": "INHABILITACION", "start": "2024-01-01", "end": "2024-06-30", "status": "Activo", "description": "old"},
            {"type": "AMONESTACION", "start": "2024-01-01", "end": None, "status": "Activo", "description": "warning"}]}]}
        row = {"supplierIds": [{"id": "PY-RUC-1"}], "awardDate": "2025-03-01"}
        self.assertEqual([s["description"] for s in mod.sanctions_in_force(row, snap)], ["x"])
        self.assertEqual(mod.sanctions_in_force(row | {"awardDate": "2025-07-01"}, snap), [])
        self.assertEqual(mod.sanctions_in_force(row | {"awardDate": None}, snap), [])
        self.assertEqual(mod.sanctions_in_force(row, None), [])

    def test_complaints_keep_no_participant_names(self):
        record = self.sample()
        record["compiledRelease"]["complaints"] = [{"id": "7", "events": [
            {"type": "Escrito de Protesta", "period": {"startDate": "2025-02-01T00:00:00-04:00"}},
            {"type": "Resolución de Cierre", "period": {"startDate": "2025-03-01T00:00:00-04:00"}}],
            "intervenients": [{"name": "Persona Privada", "roles": ["judge"]}],
            "documents": [{"title": "res.pdf", "url": "https://www.contrataciones.gov.py/documentos/download/marco-legal/1"}]}]
        row, = mod.contract_rows(record)
        self.assertEqual(row["complaints"][0]["kind"], "protest")
        self.assertTrue(row["complaints"][0]["closureRecorded"])
        self.assertNotIn("Persona Privada", str(row))


if __name__ == "__main__":
    unittest.main()
