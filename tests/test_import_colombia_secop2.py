import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("import_colombia", Path(__file__).parents[1] / "tools/import-colombia-secop2.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def raw(**overrides):
    row = {
        "id_contrato": "CTR-1",
        "proceso_de_compra": "PROC-1",
        "urlproceso": {"url": "https://www.secop.gov.co/notice/1"},
        "nombre_entidad": "MINISTERIO DE EDUCACION NACION (MEN)",
        "nit_entidad": "899999001",
        "orden": "Nacional",
        "departamento": "BOGOTA D.C.",
        "ciudad": "BOGOTA D.C.",
        "fecha_de_firma": "2025-03-15T00:00:00.000",
        "proveedor_adjudicado": "PROVEEDOR EJEMPLO SAS",
        "tipodocproveedor": "NIT",
        "documento_proveedor": "900123456",
        "es_grupo": "No",
        "es_pyme": "Si",
        "objeto_del_contrato": "Prestacion de servicios educativos",
        "modalidad_de_contratacion": "Contratación directa",
        "justificacion_modalidad_de": "Servicios profesionales y apoyo a la gestión",
        "estado_contrato": "En ejecución",
        "tipo_de_contrato": "Prestación de servicios",
        "sector": "Educación",
        "destino_gasto": "03 Servicios educativos",
        "valor_del_contrato": "1,500,000",
        "valor_pagado": 1000000,
        "valor_facturado": 1000000,
        "valor_amortizado": 0,
        "valor_pendiente_de_pago": 500000,
        "valor_pendiente_de_ejecucion": 0,
        "duraci_n_del_contrato": "6 Mes(es)",
        "fecha_de_inicio_del_contrato": "2025-04-01T00:00:00.000",
        "fecha_de_fin_del_contrato": "2025-10-01T00:00:00.000",
        "ultima_actualizacion": "2025-11-01",
        "espostconflicto": "No",
        "reversion": "No",
        "liquidaci_n": "No",
    }
    row.update(overrides)
    return row


class NormalizeRowRegression(unittest.TestCase):
    def buyer(self):
        return mod.BUYERS[0]

    def test_liquidaci_n_accented_key_is_read(self):
        # Regression: the Socrata field is liquidaci_n, never "liquidación".
        row = mod.normalize_row(raw(liquidaci_n="Si"), self.buyer())
        self.assertEqual(row["liquidation"], "Si")
        row = mod.normalize_row(raw(liquidaci_n="No"), self.buyer())
        self.assertEqual(row["liquidation"], "No")

    def test_missing_liquidaci_n_is_null(self):
        row = mod.normalize_row({k: v for k, v in raw().items() if k != "liquidaci_n"}, self.buyer())
        self.assertIsNone(row["liquidation"])

    def test_row_identity_and_cohort(self):
        row = mod.normalize_row(raw(), self.buyer())
        self.assertEqual(row["id"], "secop2-men-CTR-1")
        self.assertEqual(row["cohortId"], "secop2-three-buyers-2024-2026")
        self.assertEqual(row["dataFamily"], "secop2")
        self.assertEqual(row["currency"], "COP")
        self.assertEqual(row["date"], "2025-03-15")
        self.assertEqual(row["buyerLevel"], "Nacional")

    def test_amount_with_thousands_separator(self):
        row = mod.normalize_row(raw(valor_del_contrato="271,315,944,244"), self.buyer())
        self.assertEqual(row["amount"], 271315944244.0)

    def test_unusable_amount_is_null(self):
        row = mod.normalize_row(raw(valor_del_contrato="n/a"), self.buyer())
        self.assertIsNone(row["amount"])

    def test_supplier_identifier_single_entry(self):
        row = mod.normalize_row(raw(), self.buyer())
        self.assertEqual(row["supplierIds"], [{"identifierType": "NIT", "id": "900123456"}])
        row = mod.normalize_row(raw(documento_proveedor=""), self.buyer())
        self.assertEqual(row["supplierIds"], [])

    def test_placeholder_supplier_document_is_unknown(self):
        for value in (None, "", "  ", "No Definido", " no definido ", "N/A"):
            with self.subTest(value=value):
                self.assertEqual(mod.normalize_row(raw(documento_proveedor=value), self.buyer())["supplierIds"], [])

    def test_duplicate_extract_ids_are_rejected(self):
        first = mod.normalize_row(raw(), self.buyer())
        second = mod.normalize_row(raw(), self.buyer())
        with self.assertRaisesRegex(ValueError, "duplicate ID"):
            mod.require_unique_ids([first, second])
        mod.require_unique_ids([first, mod.normalize_row(raw(id_contrato="CTR-2"), self.buyer())])

    def test_url_object_is_unwrapped(self):
        row = mod.normalize_row(raw(urlproceso={"description": "https://example.org/p"}), self.buyer())
        self.assertEqual(row["processUrl"], "https://example.org/p")

    def test_date_is_truncated_to_day(self):
        # The signature window is enforced by the download query (window_where),
        # not by normalize_row, which only normalizes the timestamp to a day.
        row = mod.normalize_row(raw(fecha_de_firma="2024-08-31T00:00:00.000"), self.buyer())
        self.assertEqual(row["date"], "2024-08-31")
        row = mod.normalize_row(raw(fecha_de_firma="not-a-date"), self.buyer())
        self.assertIsNone(row["date"])

    def test_liquidation_counts_on_extract_shape(self):
        rows = [mod.normalize_row(raw(liquidaci_n="Si"), self.buyer()),
                mod.normalize_row(raw(id_contrato="CTR-2", liquidaci_n="No"), self.buyer()),
                mod.normalize_row({k: v for k, v in raw(id_contrato="CTR-3").items() if k != "liquidaci_n"}, self.buyer())]
        self.assertEqual(mod.liquidation_counts(rows), {"Si": 1, "No": 1, "unknown": 1})


if __name__ == "__main__":
    unittest.main()
