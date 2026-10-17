"""The browser copies in data/web/ (slim record files, first pages) must match what their
builders produce from the current data and script.js, and prefetch.js must list the same
datasets and files as script.js."""
import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('build_web_data', ROOT / 'tools' / 'build-web-data.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def prefetch_files():
    text = (ROOT / 'prefetch.js').read_text(encoding='utf-8')
    block = text[text.index('const files = {'):text.index('};', text.index('const files = {'))]
    return {key: re.findall(r"'([^']+)'", files) for key, files in re.findall(r"(\w+): \[([^\]]*)\]", block)}


def script_paths():
    text = (ROOT / 'script.js').read_text(encoding='utf-8')
    out = {}
    for key, value in re.findall(r"^    (\w+): \{ path: (\[[^\]]*\]|'[^']+')", text, re.M):
        out[key] = re.findall(r"'([^']+)'", value)
    return out


class WebData(unittest.TestCase):
    def test_copies_are_current(self):
        result = subprocess.run([sys.executable, str(ROOT / 'tools' / 'build-web-data.py'), '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_first_pages_are_current(self):
        result = subprocess.run(['node', str(ROOT / 'tools' / 'build-first-pages.cjs'), '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_prefetch_lists_script_datasets(self):
        web = prefetch_files()
        canonical = script_paths()
        self.assertEqual(set(web), set(canonical))
        for key, files in canonical.items():
            expected = [f'data/web/{Path(f).name}' if Path(f).name in build.DROP else f for f in files]
            self.assertEqual(web[key], expected, key)

    def test_dropped_fields_unused_by_explorer(self):
        code = ''.join((ROOT / name).read_text(encoding='utf-8') for name in ['script.js', 'import.js', 'indicator-evidence.js'])
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
