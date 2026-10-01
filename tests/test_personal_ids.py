import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from personal_ids import is_personal, mask  # noqa: E402

PUBLISHED = ["colombia-secop2", "prozorro", "chile-mp", "paraguay-dncp", "paraguay-dncp-3buyers", "ted-portugal", "ted-romania", "ted-czechia", "uk-fts"]


class PersonalIdTests(unittest.TestCase):
    def test_rules(self):
        self.assertTrue(is_personal("Cédula de Ciudadanía", "1002543870"))
        self.assertTrue(is_personal("RNOKPP", "3128415087"))
        self.assertTrue(is_personal("CL-RUT", "123456789"))       # RUN 12,345,678-9: a person
        self.assertFalse(is_personal("CL-RUT", "760187054"))      # 76,018,705-4: a company
        self.assertTrue(is_personal("RUC", "PY-RUC-1683567-0"))
        self.assertFalse(is_personal("RUC", "PY-RUC-80010090-5"))
        self.assertFalse(is_personal("NIT", "890801052"))
        self.assertFalse(is_personal("RUC", "PY-RUC-DNCP-001874"))

    def test_mask_is_stable_and_idempotent(self):
        once = mask("Cédula de Ciudadanía", "1002543870")
        self.assertTrue(once.startswith("masked-"))
        self.assertEqual(once, mask("Cédula de Ciudadanía", "1002543870"))
        self.assertEqual(mask("Cédula de Ciudadanía", once), once)
        self.assertNotEqual(once, mask("RNOKPP", "1002543870"))

    def test_no_published_row_carries_a_personal_id(self):
        for name in PUBLISHED:
            for row in json.loads((ROOT / f"data/{name}.json").read_text(encoding="utf-8")):
                for s in row.get("supplierIds") or []:
                    self.assertFalse(is_personal(s.get("identifierType"), s.get("id")), f"{name}: {row['id']}")
        sanctions = json.loads((ROOT / "data/dncp-sanctions.json").read_text(encoding="utf-8"))
        for s in sanctions["suppliers"]:
            self.assertFalse(is_personal("RUC", s["id"]), s["id"][:12])


if __name__ == "__main__":
    unittest.main()
