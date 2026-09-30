import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "tools/audit-personal-data.py"
SPEC = importlib.util.spec_from_file_location("personal_data_audit", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class PersonalDataAuditTests(unittest.TestCase):
    def test_placeholder_values_are_not_meaningful(self):
        self.assertFalse(audit.is_meaningful("No Definido"))
        self.assertFalse(audit.is_meaningful("  NO APLICA "))
        self.assertFalse(audit.is_meaningful(""))
        self.assertTrue(audit.is_meaningful("123456789"))

    def test_scan_reports_counts_without_printing_values(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.json"
            source.write_text(json.dumps([
                {"numero_de_cuenta": "No Definido", "documento_proveedor": "90807060"},
                {"numero_de_cuenta": "No Definido", "documento_proveedor": "No Definido"},
            ]), encoding="utf-8")
            output = io.StringIO()
            with patch.object(audit, "ROOT", Path(directory)), patch.dict(
                audit.DATASETS, {"sample": ["sample.json"]}, clear=True
            ), contextlib.redirect_stdout(output):
                audit.main()

        report = output.getvalue()
        self.assertIn("numero_de_cuenta: field occurrences=2, nonempty=2, meaningful=0", report)
        self.assertIn("documento_proveedor: field occurrences=2, nonempty=2, meaningful=1", report)
        self.assertNotIn("90807060", report)
        self.assertNotIn("No Definido", report)


if __name__ == "__main__":
    unittest.main()
