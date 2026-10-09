import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('conflict_fetch', Path(__file__).resolve().parents[1] / 'tools/fetch-decp-conflict-evidence.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Response:
    def __init__(self, status=200, body=b'{"total_count":0,"results":[]}'):
        self.code, self.body, self.headers = status, body, {'Content-Type': 'application/json'}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, limit):
        return self.body[:limit]


class ConflictFetchTests(unittest.TestCase):
    def test_fixed_official_exact_scope_and_discovery_separate(self):
        req = m.requests()
        self.assertEqual(len(req), 3)
        self.assertIn(m.BUYER, req[0]['url'])
        self.assertIn(m.CONTRACT, req[0]['url'])
        self.assertEqual(req[2]['label'], 'boamp-project-discovery')
        self.assertTrue(all('data.economie.gouv.fr/' in r['url'] or 'www.boamp.fr/' in r['url'] for r in req))
        self.assertIsNone(m.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.invalid'))

    def test_private_manifest_and_no_repeat_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'evidence'
            with patch.object(m.urllib.request, 'build_opener') as build, patch.object(m.time, 'sleep'):
                build.return_value.open.return_value = Response()
                m.fetch(root)
                self.assertEqual(build.return_value.open.call_count, 3)
                manifest = json.loads((root / 'fetch-manifest.json').read_text())
                self.assertEqual(len(manifest['entries']), 3)
                self.assertEqual(root.stat().st_mode & 0o777, 0o700)
                self.assertEqual((root / 'ministry-exact.response').stat().st_mode & 0o777, 0o600)
                with self.assertRaises(FileExistsError):
                    m.fetch(root)
                self.assertEqual(build.return_value.open.call_count, 3)

    def test_refusal_and_oversize_stop_collection(self):
        for response in [Response(429), Response(403), Response(503), Response(body=b'x' * (m.MAX_BYTES + 1))]:
            with tempfile.TemporaryDirectory() as tmp, patch.object(m.urllib.request, 'build_opener') as build:
                build.return_value.open.return_value = response
                m.fetch(Path(tmp) / 'evidence')
                self.assertEqual(build.return_value.open.call_count, 1)

    def test_repository_output_refused_before_network(self):
        with patch.object(m.urllib.request, 'build_opener') as build:
            with self.assertRaises(ValueError):
                m.fetch(m.ROOT / 'private-evidence')
            build.assert_not_called()


if __name__ == '__main__':
    unittest.main()
