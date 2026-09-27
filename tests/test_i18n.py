"""The Spanish and French dictionaries are generated from tools/i18n_table.py and must match it."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from i18n_table import EXACT, PATTERNS  # noqa: E402

SLOT = __import__("re").compile(r"\{[a-z0-9]+\}")


class I18nTable(unittest.TestCase):
    def test_generated_files_are_current(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools" / "i18n-strings.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_every_row_has_both_languages(self):
        for row in EXACT + PATTERNS:
            self.assertEqual(len(row), 3, row[0])
            self.assertTrue(all(isinstance(t, str) and t.strip() for t in row), row[0])

    def test_patterns_keep_every_slot(self):
        # A dropped slot would silently remove a published value (a name, an amount) from the page.
        for en, es, fr in PATTERNS:
            slots = sorted(SLOT.findall(en))
            self.assertTrue(slots, en)
            self.assertEqual(sorted(SLOT.findall(es)), slots, en)
            self.assertEqual(sorted(SLOT.findall(fr)), slots, en)


if __name__ == "__main__":
    unittest.main()
