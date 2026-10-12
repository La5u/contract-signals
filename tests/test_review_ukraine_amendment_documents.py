import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('review_documents', ROOT / 'tools/review-ukraine-amendment-documents.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Response(io.BytesIO):
    status = 200


class DocumentsTest(unittest.TestCase):
    def test_offline_actual(self):
        with patch.object(m.urllib.request, 'build_opener', side_effect=AssertionError('network forbidden')):
            result = m.verify(version=1)
        self.assertEqual(result['additionalRequestCount'], 0)
        self.assertEqual(result['overallRequestCount'], 28)
        self.assertEqual(result['legalBasis'], 'unknown')

    def test_plan_and_ledger_hash_metadata_is_ignored(self):
        def change_hashes(value, marker):
            if isinstance(value, dict):
                return {k: marker if k.lower().endswith('sha256') else
                        {name: marker for name in v} if k in ('inputHashes', 'rawSnapshotHashes') else
                        change_hashes(v, marker) for k, v in value.items()}
            if isinstance(value, list):
                return [change_hashes(v, marker) for v in value]
            return value
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = ['tools/audit-ukraine-amount-bases.py', 'data/prozorro.json',
                     'data/ukraine-public-audit-plan.json', m.MODULE, m.PLAN, m.EVIDENCE, m.PLAN_V2, m.EVIDENCE_V2]
            for i, name in enumerate(names):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                if name.endswith('.json'):
                    value = change_hashes(json.loads((ROOT / name).read_text()), 'ignored-' + str(i))
                    target.write_text(json.dumps(value))
                else:
                    target.write_bytes((ROOT / name).read_bytes())
            for version in (1, 2):
                self.assertEqual(m.verify(root, version), m.verify(version=version))
            plan = json.loads((root / m.PLAN_V2).read_text())
            plan['selected'][0]['relatedItem'] = 'wrong'
            (root / m.PLAN_V2).write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError, 'selection/order'):
                m.verify(root)

    def test_hosts_auth_redirect(self):
        for url in ['http://public-docs.prozorro.gov.ua/x', 'https://public-api.prozorro.gov.ua/x',
                    'https://public-docs.prozorro.gov.ua.evil/x', 'https://u:p@public-docs.prozorro.gov.ua/x',
                    'https://public-docs.prozorro.gov.ua:444/x', 'https://public-docs.prozorro.gov.ua/x#fragment']:
            self.assertFalse(m.allowed(url))
            with patch.object(m.urllib.request, 'build_opener') as opener:
                with self.assertRaises(ValueError):
                    m.bounded_get(url)
                opener.assert_not_called()
        self.assertTrue(m.allowed('https://public-docs.prozorro.gov.ua/x?accessSignature=published'))
        self.assertTrue(m.allowed('https://publisherdocservice.prozorro.gov.ua/x'))
        self.assertIsNone(m.NoRedirect().redirect_request(None, None, None, None))

    def test_stream_boundary(self):
        for size, outcome, complete in [(m.LIMIT, 'downloaded', True), (m.LIMIT + 1, 'oversized', False)]:
            opener = unittest.mock.Mock()
            opener.open.return_value = Response(b'%PDF-' + b'x' * (size - 5))
            with patch.object(m.urllib.request, 'build_opener', return_value=opener):
                r, raw = m.bounded_get('https://public-docs.prozorro.gov.ua/x')
            self.assertEqual(len(raw), size)
            self.assertEqual(r['outcome'], outcome)
            self.assertEqual(r['responseComplete'], complete)
            self.assertTrue(r['recognizedPDF'])
            opener.open.assert_called_once()
            m.date(r['startedAt']); m.date(r['finishedAt'])

    def test_no_retry_failed_status(self):
        for status in [302, 403, 429, 500]:
            opener = unittest.mock.Mock()
            opener.open.side_effect = urllib.error.HTTPError('private-url', status, 'error', {}, None)
            with patch.object(m.urllib.request, 'build_opener', return_value=opener):
                r, _ = m.bounded_get('https://public-docs.prozorro.gov.ua/x')
            self.assertEqual(r['httpStatus'], status)
            self.assertEqual(r['outcome'], 'http-failure')
            opener.open.assert_called_once()
            self.assertNotIn('private-url', json.dumps(r))

    def test_date_status_identity_and_selection(self):
        for value in ['2025-01-01', 'not a date', '2025-99-01T00:00:00+00:00']:
            with self.assertRaises((ValueError, TypeError)):
                m.date(value)
        b = {'rowId': 'row', 'buyerId': 'buyer', 'contractInternalId': 'c', 'contractId': 'full', 'tenderInternalId': 't', 'awardId': 'a'}
        d = {'id': 'c', 'contractID': 'full', 'tender_id': 't', 'awardID': 'a', 'buyer': {'identifier': {'id': 'buyer'}},
             'changes': [{'id': str(i), 'status': 'active'} for i in range(3)], 'documents': []}
        self.assertEqual(m.bind_module({'data': d}, b), d)
        d['awardID'] = 'wrong'
        with self.assertRaises(ValueError):
            m.bind_module({'data': d}, b)
        for i in range(4):
            d['documents'].append({'id': f'{i:032x}', 'documentOf': 'change', 'relatedItem': str(i % 3),
                                   'url': f'https://public-api.prozorro.gov.ua/{i}', 'format': 'application/pdf',
                                   'datePublished': '2025-01-01T00:00:00+00:00', 'dateModified': '2025-01-01T00:00:00+00:00'})
        ranked = sorted(d['documents'], key=lambda v: m.sha(m.canonical(['row', v['id']])))
        self.assertEqual([v['docId'] for v in m.select(d, b)], [v['id'] for v in ranked[:2]])
        d['changes'][0]['status'] = 'pending'
        with self.assertRaises(ValueError):
            m.select(d, b)

    def test_v2_offline_and_same_selection(self):
        with patch.object(m.urllib.request, 'build_opener', side_effect=AssertionError('network forbidden')):
            result = m.verify()
        self.assertLessEqual(result['additionalRequestCount'], 2)
        self.assertEqual(result['overallRequestCount'], 28 + result['additionalRequestCount'])
        old = json.loads((ROOT / m.PLAN).read_text())
        new = json.loads((ROOT / m.PLAN_V2).read_text())
        self.assertEqual([s['docId'] for s in old['selected']], [s['docId'] for s in new['selected']])
        self.assertTrue(all(s['publisherHostAllowed'] for s in new['selected']))

    def test_v2_exact_native_path_auth_query(self):
        b = {'contractInternalId': 'a' * 32}
        doc = 'b' * 32
        url = 'https://public-api.prozorro.gov.ua/api/2.5/contracts/' + b['contractInternalId'] + '/documents/' + doc
        self.assertTrue(m.allowed_v2(url + '?accessSignature=exact%2Bpublished', b, doc))
        for bad in [url.replace('https:', 'http:'), url.replace('public-api.', 'u:p@public-api.'),
                    url.replace('public-api.', '@public-api.'), url + '/', url + '#x',
                    url.replace('/api/2.5/', '/api/2.6/'), url.replace('a' * 32, 'a' * 31),
                    url.replace('public-api.prozorro.gov.ua', 'public-api.prozorro.gov.ua.evil'),
                    url.replace('documents/', 'documents/%2f'), url.replace('gov.ua/', 'gov.ua:444/')]:
            self.assertFalse(m.allowed_v2(bad, b, doc), bad)
        opener = unittest.mock.Mock()
        opener.open.side_effect = urllib.error.HTTPError('secret', 302, 'redirect', {'Location': 'secret'}, None)
        with patch.object(m.urllib.request, 'build_opener', return_value=opener):
            result, _ = m.bounded_get(url, lambda u: m.allowed_v2(u, b, doc))
        self.assertEqual(result['httpStatus'], 302)
        opener.open.assert_called_once()
        self.assertNotIn('secret', json.dumps(result))

    def test_v2_global_stop_and_no_replay(self):
        plan = json.loads((ROOT / m.PLAN_V2).read_text())
        # Synthetic private fixture; no private cache required by tests.
        urls = ['https://public-api.prozorro.gov.ua/api/2.5/contracts/' + plan['binding']['contractInternalId'] + '/documents/' + s['docId'] for s in plan['selected']]
        module = {'data': {'documents': [{} for _ in range(7)]}}
        for s, url in zip(plan['selected'], urls):
            module['data']['documents'][int(s['pointer'].rsplit('/', 1)[1])] = {'id': s['docId'], 'url': url}
        raw = m.canonical(module)
        plan['moduleResponseSha256'] = m.sha(raw); plan['moduleResponseBytes'] = len(raw)
        for s, url in zip(plan['selected'], urls):
            s['urlSha256'] = m.sha(url.encode())
        for status in [302, 403, 429, 500]:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / 'repo'; (root / 'data').mkdir(parents=True)
                private = Path(temp) / 'private'; private.mkdir(mode=0o700)
                cache = Path(temp) / 'module'; cache.write_bytes(raw)
                (root / m.PLAN_V2).write_text(json.dumps(plan))
                ev = {'requests': [], 'additionalRequestCount': 0, 'documents': [{'facts': []}, {'facts': []}], 'blockers': []}
                (root / m.EVIDENCE_V2).write_text(json.dumps(ev))
                m.private_write(private / 'plan.json', {'publicPlan': plan, 'rawModulePath': str(cache), 'urls': urls}, 0o400)
                req = {'method': 'GET', 'startedAt': m.now(), 'finishedAt': m.now(), 'httpStatus': status,
                       'outcome': 'http-failure', 'responseComplete': False, 'responseBytes': 0,
                       'responseSha256': m.sha(b''), 'recognizedPDF': False}
                with patch.object(m, 'verify'), patch.object(m, 'bind_module', return_value=module['data']), patch.object(m, 'bounded_get', return_value=(req, b'')) as get:
                    m.attempt_v2(root, private)
                    get.assert_called_once()
                    with self.assertRaises(ValueError):
                        m.attempt_v2(root, private)
                ev = json.loads((root / m.EVIDENCE_V2).read_text())
                self.assertEqual(ev['additionalRequestCount'], 1)
                self.assertEqual(ev['documents'][1]['outcome'], 'not-attempted-global-failure')
                self.assertEqual((private / 'request-1.json').stat().st_mode & 0o777, 0o600)

    def test_staleness_and_privacy(self):
        original, b, r, digest = m.load_source()
        with patch.object(m, 'load_source', return_value=(original, b, r, 'stale')):
            self.assertEqual(m.verify(version=1)['additionalRequestCount'], 0)
        changed = dict(b, buyerId='other')
        with patch.object(m, 'load_source', return_value=(original, changed, r, digest)):
            with self.assertRaisesRegex(ValueError, 'Stale supplemental source'):
                m.verify(version=1)
        for name in [m.PLAN, m.EVIDENCE, m.PLAN_V2, m.EVIDENCE_V2]:
            text = (ROOT / name).read_text()
            for forbidden in ['accessSignature=', 'Signature=', 'suppliers', 'title', 'telephone', 'address']:
                self.assertNotIn(forbidden, text)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'plan.json'
            m.private_write(path, {'private': 'exact-url'}, 0o400)
            self.assertEqual(path.stat().st_mode & 0o777, 0o400)
            with self.assertRaises(FileExistsError):
                m.private_write(path, {})


if __name__ == '__main__':
    unittest.main()
