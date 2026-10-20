"""The browser copies in data/web/ (slim record files, first pages) must match what their
builders produce from the current data and engine, and each dataset's browser files in
datasets.js must be the copies of its published files."""
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('build_web_data', ROOT / 'tools' / 'build-web-data.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
sys.path.insert(0, str(ROOT / 'tools'))
from common import datasets, engine_files  # noqa: E402


class WebData(unittest.TestCase):
    def test_copies_are_current(self):
        result = subprocess.run([sys.executable, str(ROOT / 'tools' / 'build-web-data.py'), '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_first_pages_are_current(self):
        result = subprocess.run(['node', str(ROOT / 'tools' / 'build-first-pages.cjs'), '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_browser_files_are_the_copies(self):
        for key, entry in datasets(ROOT).items():
            if 'path' not in entry:
                continue
            files = [entry['path']] if isinstance(entry['path'], str) else entry['path']
            expected = [f'data/web/{Path(f).name}' if Path(f).name in build.DROP else f for f in files]
            self.assertEqual(entry.get('web', files), expected, key)

    def test_dropped_fields_unused_by_explorer(self):
        code = ''.join((ROOT / name).read_text(encoding='utf-8') for name in [*engine_files(ROOT), 'script.js', 'import.js', 'indicator-evidence.js'])
        for name, fields in build.DROP.items():
            for field in fields:
                self.assertNotRegex(code, rf"\.{field}\b|'{field}'|\"{field}\"", f'{field} ({name}) is read by the explorer')

    def test_copies_keep_every_other_field(self):
        for name, fields in build.DROP.items():
            full = json.loads((ROOT / 'data' / name).read_text(encoding='utf-8'))
            web = json.loads((ROOT / 'data' / 'web' / name).read_text(encoding='utf-8'))
            self.assertEqual(len(full), len(web))
            for a, b in zip(full, web):
                self.assertEqual(build.slim_row(name, a), b)
                self.assertEqual({k: v for k, v in a.items() if k not in fields}, {k: v for k, v in b.items() if k != 'operatorGrouping'})


if __name__ == '__main__':
    unittest.main()
