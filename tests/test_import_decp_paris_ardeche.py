import gzip
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("import_paris", ROOT / "tools/import-decp-paris-ardeche.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ParisArdecheRebuildTests(unittest.TestCase):
    def test_published_file_is_what_the_importer_produces(self):
        raw = json.loads(gzip.decompress(mod.RAW.read_bytes()))
        rows = {r["id"]: r for r in mod.normalize(raw)}
        published = json.loads((ROOT / "data/decp-history.json").read_text(encoding="utf-8"))
        curated = json.loads(mod.CURATED.read_text(encoding="utf-8"))["rows"]
        self.assertEqual(len(rows), len(published))
        for row in published:
            expected = {k: v for k, v in row.items() if k != "supplierProfiles" and k not in curated.get(row["id"], {})}
            self.assertEqual({k: rows[row["id"]][k] for k in expected}, expected, row["id"])

    def test_raw_snapshot_is_complete(self):
        raw = json.loads(gzip.decompress(mod.RAW.read_bytes()))
        self.assertEqual(raw["totals"], {"21750001600019": 2395, "22070001700019": 554})
        self.assertEqual(len(raw["records"]), 2949)

    def test_curated_fields_are_limited_to_the_dossier_rows(self):
        curated = json.loads(mod.CURATED.read_text(encoding="utf-8"))["rows"]
        self.assertEqual(len(curated), 3)
        for fields in curated.values():
            self.assertLessEqual(set(fields), {"supplier", "supplierNameSource", "project", "frameworkId"})

    def test_dialogue_competitif_is_competitive_and_unknown_labels_stay_unknown(self):
        self.assertIs(mod.direct("Dialogue compétitif"), False)
        self.assertIs(mod.direct("Marché passé sans publicité ni mise en concurrence préalable"), True)
        self.assertIsNone(mod.direct("Procédure adaptée"))


if __name__ == "__main__":
    unittest.main()
