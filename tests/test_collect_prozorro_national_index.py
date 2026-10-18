import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('national_feed', Path(__file__).resolve().parents[1] / 'tools/collect-prozorro-national-index.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
START = f.iso('2024-09-01T00:00:00+03:00')
END = f.iso('2026-09-01T00:00:00+03:00')


def page(ids, cursor='next'):
    return json.dumps({'data': [{'id': ident, 'dateModified': day} for ident, day in ids],
                       'next_page': {'uri': f.API + '?limit=500&offset=' + cursor}}).encode()


class FeedTests(unittest.TestCase):
    def test_fail_closed_continuation(self):
        for url in ['https://example.org/api/2.5/tenders?offset=x', f.API + '/id?offset=x', f.API + '?descending=1', f.API + '?offset=x&offset=y']:
            with self.assertRaises(ValueError):
                f.validate_url(url)

    def test_modification_not_creation_and_upper_bound(self):
        rows, _, beyond, _ = f.parse_page(page([('a'*32, '2025-01-01T00:00:00Z'), ('b'*32, '2026-10-01T00:00:00Z')]), START, END)
        self.assertEqual(len(rows), 1)
        self.assertTrue(beyond)
        with self.assertRaises(ValueError):
            f.iso('2025-01-01')

    def test_bounded_resume_and_deduplicate(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'index.sqlite'
            first = f.collect(path, START, END, max_pages=1, fetch=lambda *_: page([('a'*32, '2025-01-01T00:00:00Z')]))
            self.assertEqual(first['uniqueTenderIds'], 1)
            seen = []
            def fetch(url, limit):
                seen.append(url)
                return page([('a'*32, '2025-01-02T00:00:00Z'), ('b'*32, '2025-02-01T00:00:00Z')], 'next2')
            result = f.collect(path, START, max_pages=1, fetch=fetch)
            self.assertEqual(result['uniqueTenderIds'], 2)
            self.assertEqual(result['totalPages'], 2)
            self.assertIn('offset=next', seen[0])
            self.assertFalse(result['nationalContractCompletenessEstablished'])
            self.assertEqual(result['fullTenderDetails'], 0)
            with self.assertRaises(ValueError):
                f.collect(path, f.iso('2025-01-01T00:00:00Z'), fetch=fetch)

    def test_no_partial_response_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'index.sqlite'
            result = f.collect(path, START, END, max_bytes=10, fetch=lambda *_: b'x'*11)
            self.assertEqual(result['totalPages'], 0)
            self.assertEqual(result['uniqueTenderIds'], 0)
            self.assertEqual(result['stopReason'], 'response-budget')

    def test_out_of_order_dates_allowed_bad_ids_rejected(self):
        rows, *_ = f.parse_page(page([('a'*32, '2025-02-01T00:00:00Z'), ('b'*32, '2025-01-01T00:00:00Z')]), START, END)
        self.assertEqual(len(rows), 2)
        with self.assertRaises(ValueError):
            f.parse_page(page([('wrong', '2025-01-01T00:00:00Z')]), START, END)

    def test_creation_fields_kept_and_opt_fields_pinned(self):
        body = json.dumps({'data': [{'id': 'a'*32, 'dateModified': '2025-01-02T00:00:00+02:00', 'dateCreated': '2024-08-30T10:00:00+03:00',
                                     'procurementMethodType': 'reporting', 'status': 'complete'}],
                           'next_page': {'uri': f.API + '?limit=1000&opt_fields=' + f.OPT_FIELDS + '&offset=n'}}).encode()
        rows, *_ = f.parse_page(body, START, END)
        self.assertEqual(rows[0][2:], ('2024-08-30T07:00:00+00:00', 'reporting', 'complete'))
        with self.assertRaises(ValueError):
            f.validate_url(f.API + '?offset=x&opt_fields=procuringEntity')

    def test_upper_bound_not_contract_census(self):
        with tempfile.TemporaryDirectory() as temp:
            result = f.collect(Path(temp)/'i.sqlite', START, END, max_pages=1,
                               fetch=lambda *_: page([('a'*32, '2026-10-01T00:00:00Z')]))
            self.assertEqual(result['phase'], 'partial')
            self.assertFalse(result['nationalContractCompletenessEstablished'])


if __name__ == '__main__':
    unittest.main()
