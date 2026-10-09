"""Keep basic help separate from technical documentation."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ConciseUI(unittest.TestCase):
    def test_help_is_short_and_links_to_method(self):
        html = (ROOT / "index.html").read_text()
        help_panel = re.search(r'<dialog id="help-dialog".*?</dialog>', html, re.S).group()
        text = re.sub(r"<[^>]+>", " ", help_panel)
        self.assertLess(len(" ".join(text.split())), 1800)
        self.assertIn('href="docs/score-v3.md"', help_panel)
        self.assertIn('href="docs/indicators.md"', help_panel)
        self.assertIn("Missing values are shown as unknown", text)
        self.assertNotIn('class="method"', help_panel)
        self.assertNotIn("not an accusation", text)
        self.assertNotIn("Always read the source document", html)

    def test_dataset_descriptions_stay_short_and_translated(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        from i18n_table import EXACT
        translations = {row[0] for row in EXACT}
        script = (ROOT / "script.js").read_text()
        definitions = script.split("const datasets = {", 1)[1].split("let datasetMetadata", 1)[0]
        notes = re.findall(r"note: '([^']*)'", definitions)
        self.assertEqual(len(notes), 14)  # the two DECP datasets are one since 2026-10-08
        for note in notes:
            self.assertLess(len(note), 400, note)
            self.assertIn(note, translations)

    def test_import_and_notes_have_dedicated_dialogs(self):
        html = (ROOT / "index.html").read_text()
        self.assertIn('id="import-dialog"', html)
        self.assertIn('id="notes-dialog"', html)
        self.assertEqual(html.count('id="file"'), 1)
        self.assertNotIn('<summary>Import a dataset</summary>', html)
        self.assertIn('id="review-filters" hidden', html)
        self.assertIn('id="sort-field"', html)
        self.assertIn('id="sort-direction"', html)
        self.assertNotIn('class="reading-hint"', html)

    def test_sources_keep_provenance_not_rebuild_instructions(self):
        script = (ROOT / "script.js").read_text()
        sources = script.split("function renderSources(selected) {", 1)[1].split("const provenance", 1)[0]
        self.assertIn("s.publisher", sources)
        self.assertIn("s.licence", sources)
        self.assertIn("selected.coverage", sources)
        self.assertIn("docs/data-sources.md", sources)
        self.assertNotIn("s.reproduce", sources)
        self.assertNotIn("s.raw", sources)


if __name__ == "__main__":
    unittest.main()
