"""Offline tests for tools/polite_http.py and tools/fetch-documents.py: a fake transport, no network."""
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import polite_http  # noqa: E402
from polite_http import Disallowed, PoliteClient, Refused  # noqa: E402

spec = importlib.util.spec_from_file_location('fetch_documents', ROOT / 'tools/fetch-documents.py')
fetch_documents = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_documents)

INTERNAL = 'a' * 32
CONTRACT = 'c' * 32
TENDER = {'id': INTERNAL, 'tenderID': 'UA-2025-01-01-000001-a',
          'documents': [{'id': 'd1', 'title': 'notice v1', 'url': 'https://docs.example/get/1?Signature=x', 'dateModified': '2025-01-01'},
                        {'id': 'd1', 'title': 'notice v2', 'url': 'https://docs.example/get/2?Signature=y', 'dateModified': '2025-02-01'}],
          'bids': [{'documents': [{'id': 'b1', 'title': 'offer.pdf', 'url': 'https://docs.example/get/3'}]}],
          'contracts': [{'id': CONTRACT}]}
CONTRACT_RECORD = {'id': CONTRACT, 'documents': [{'id': 'k1', 'title': 'contract.pdf', 'url': 'https://docs.example/get/4',
                                                   'hash': 'md5:' + __import__('hashlib').md5(b'%PDF-1.7 x').hexdigest()}]}


class Fake:
    """Routes url → (status, headers, body); records calls."""
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append((method, url, headers))
        status, response_headers, data = self.routes[url] if url in self.routes else (404, {}, b'')
        return status, response_headers, io.BytesIO(data)


def client(routes, tmp, **kwargs):
    fake = Fake(routes)
    sleeps = []
    return PoliteClient(transport=fake, sleep=sleeps.append, lock_dir=Path(tmp) / 'locks', **kwargs), fake, sleeps


class PoliteHttpTests(unittest.TestCase):
    def test_honest_user_agent_and_spacing(self):
        with tempfile.TemporaryDirectory() as tmp:
            c, fake, sleeps = client({'https://h.example/a': (200, {}, b'1'), 'https://h.example/b': (200, {}, b'2')}, tmp)
            c.get('https://h.example/a'), c.get('https://h.example/b')
            self.assertTrue(all(h['User-Agent'] == polite_http.USER_AGENT and 'Mozilla' not in h['User-Agent'] for _, _, h in fake.calls))
            self.assertTrue(sleeps and all(0 < s <= polite_http.DEFAULT_INTERVAL for s in sleeps))

    def test_robots_disallow_is_obeyed(self):
        with tempfile.TemporaryDirectory() as tmp:
            c, fake, _ = client({'https://h.example/robots.txt': (200, {}, b'User-agent: *\nDisallow: /'),
                                 'https://h.example/x': (200, {}, b'no')}, tmp)
            with self.assertRaises(Disallowed):
                c.get('https://h.example/x')
            self.assertNotIn('https://h.example/x', [u for _, u, _ in fake.calls])

    def test_html_robots_page_and_missing_robots_allow(self):
        with tempfile.TemporaryDirectory() as tmp:
            c, _, _ = client({'https://h.example/robots.txt': (200, {}, b'<!doctype html><html>app</html>'),
                              'https://h.example/x': (200, {}, b'ok')}, tmp)
            self.assertEqual(c.get('https://h.example/x').body, b'ok')
            c, _, _ = client({'https://g.example/x': (200, {}, b'ok')}, tmp)
            self.assertEqual(c.get('https://g.example/x').body, b'ok')

    def test_refusal_is_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            c, fake, _ = client({'https://h.example/x': (403, {}, b'')}, tmp)
            with self.assertRaises(Refused):
                c.get('https://h.example/x')
            self.assertEqual([u for _, u, _ in fake.calls].count('https://h.example/x'), 1)

    def test_throttle_honours_retry_after_then_gives_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            c, fake, sleeps = client({'https://h.example/x': (429, {'retry-after': '7'}, b'')}, tmp)
            with self.assertRaises(Refused):
                c.get('https://h.example/x', max_throttles=2)
            self.assertEqual(sleeps.count(7), 2)

    def test_redirect_keeps_signed_query_and_checks_new_host(self):
        signed = 'https://swift.example/f?temp_url_sig=abc%2Bdef&temp_url_expires=9'
        with tempfile.TemporaryDirectory() as tmp:
            c, fake, _ = client({'https://docs.example/get/1?Signature=x': (302, {'location': signed}, b''),
                                 signed: (200, {}, b'%PDF')}, tmp)
            response = c.get('https://docs.example/get/1?Signature=x')
            self.assertEqual((response.url, response.body, len(response.hops)), (signed, b'%PDF', 1))
            self.assertIn('https://swift.example/robots.txt', [u for _, u, _ in fake.calls])

    def test_body_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            c, _, _ = client({'https://h.example/x': (200, {}, b'x' * 11)}, tmp, max_bytes=10)
            with self.assertRaises(ValueError):
                c.get('https://h.example/x')


class ProzorroTests(unittest.TestCase):
    def routes(self, docs_robots=b''):
        api = 'https://public-api.prozorro.gov.ua/api/2.5'
        return {'https://prozorro.gov.ua/api/tenders/UA-2025-01-01-000001-a/details': (200, {}, json.dumps({'id': INTERNAL}).encode()),
                f'{api}/tenders/{INTERNAL}': (200, {}, json.dumps({'data': TENDER}).encode()),
                f'{api}/contracts/{CONTRACT}': (200, {}, json.dumps({'data': CONTRACT_RECORD}).encode()),
                'https://docs.example/robots.txt': (200, {}, docs_robots),
                'https://docs.example/get/2?Signature=y': (200, {}, b'<html>login</html>'),
                'https://docs.example/get/3': (200, {}, b'0\x82\x01\x00sig'),
                'https://docs.example/get/4': (200, {}, b'%PDF-1.7 x')}

    def test_documents_latest_version_with_paths(self):
        docs = fetch_documents.Prozorro.documents({'tender': TENDER, f'contract-{CONTRACT}': CONTRACT_RECORD})
        self.assertEqual(sorted(d['title'] for d in docs), ['contract.pdf', 'notice v2', 'offer.pdf'])
        self.assertIn(f'contract-{CONTRACT}.documents[0]', [d['path'] for d in docs])

    def test_listing_only_downloads_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            c, fake, _ = client(self.routes(), tmp)
            manifest = fetch_documents.run('prozorro', 'UA-2025-01-01-000001-a', False, 50, 10**9, client=c, out_root=Path(tmp))
            self.assertEqual(manifest['counts'], {'listed': 3})
            self.assertFalse(any('docs.example' in u for _, u, _ in fake.calls))

    def test_download_sniffs_hashes_and_resumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            c, _, _ = client(self.routes(), tmp)
            manifest = fetch_documents.run('prozorro', 'UA-2025-01-01-000001-a', True, 50, 10**9, client=c, out_root=Path(tmp))
            by = {d['title']: d for d in manifest['documents']}
            self.assertEqual((by['contract.pdf']['sniffed'], by['contract.pdf']['hashMatches']), ('pdf', True))
            self.assertEqual(by['notice v2']['sniffed'], 'html')  # saved, but visibly not the declared document
            self.assertEqual(by['offer.pdf']['sniffed'], 'der')
            c2, fake2, _ = client(self.routes(), tmp)
            fetch_documents.run('prozorro', 'UA-2025-01-01-000001-a', True, 50, 10**9, client=c2, out_root=Path(tmp))
            self.assertFalse(any('/get/' in u for _, u, _ in fake2.calls))  # already saved: not fetched again

    def test_robots_disallowed_documents_are_listed_for_hand_opening(self):
        with tempfile.TemporaryDirectory() as tmp:
            c, fake, _ = client(self.routes(b'User-agent: *\nDisallow: /'), tmp)
            manifest = fetch_documents.run('prozorro', 'UA-2025-01-01-000001-a', True, 50, 10**9, client=c, out_root=Path(tmp))
            self.assertEqual(manifest['counts'], {'robots-disallowed': 3})
            self.assertTrue(all(d['openByHand'].startswith('https://prozorro.gov.ua/tender/') for d in manifest['documents']))
            self.assertFalse(any('/get/' in u for _, u, _ in fake.calls))

    def test_file_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            c, _, _ = client(self.routes(), tmp)
            manifest = fetch_documents.run('prozorro', 'UA-2025-01-01-000001-a', True, 1, 10**9, client=c, out_root=Path(tmp))
            self.assertEqual(manifest['counts'].get('over-budget'), 2)

    def test_self_test_fails_on_empty_document_list(self):
        routes = self.routes()
        empty = dict(TENDER, documents=[], bids=[], contracts=[])
        public, internal = fetch_documents.Prozorro.SELF_TEST
        routes = {f'https://prozorro.gov.ua/api/tenders/{public}/details': (200, {}, json.dumps({'id': internal}).encode()),
                  f'https://public-api.prozorro.gov.ua/api/2.5/tenders/{internal}': (200, {}, json.dumps({'data': dict(empty, tenderID=public)}).encode())}
        with tempfile.TemporaryDirectory() as tmp:
            c, _, _ = client(routes, tmp)
            with self.assertRaises(AssertionError):
                fetch_documents.self_test('prozorro', client=c)


if __name__ == '__main__':
    unittest.main()
