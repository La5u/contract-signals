import copy
import importlib.util
import os
import shutil
import subprocess
import sys
import time
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('discovery', ROOT / 'tools/audit-ukraine-discovery.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class DiscoveryTests(unittest.TestCase):
    def test_public_replay_and_snapshot(self):
        evidence = json.loads(audit.EVIDENCE.read_text())
        self.assertEqual(evidence['snapshot'], audit.snapshot())
        self.assertEqual(len(evidence['snapshot']['excludedBuyerAssociations']), 16)
        self.assertEqual(evidence['snapshot']['searchTotal'], 500)
        self.assertEqual(len(evidence['snapshot']['inWindowTenderIDs']), 134)
        self.assertEqual(evidence['requestCount'], 5)
        audit.validate(evidence)
        self.assertEqual([(r['scope'], r['page']) for r in evidence['requests']],
                         [('all-time', 1), ('all-time', 25), ('all-time', 26),
                          ('fixed-window', 1), ('all-time', 27)])
        self.assertEqual([r['httpStatus'] for r in evidence['requests']], [200] * 5)
        self.assertEqual([r['rowCount'] for r in evidence['requests']], [20, 20, 6, 6, 0])
        self.assertFalse(audit.analyze(evidence['requests'])['historicalCompletenessCertified'])

    def evidence(self):
        return json.loads(audit.EVIDENCE.read_text())

    def reseal(self, evidence):
        evidence['analysis'] = audit.analyze(evidence['requests'])
        evidence['integrity']['evidenceSha256'] = audit.checksum(evidence)
        return evidence

    def test_failclosed_record_mutations(self):
        mutations = [
            lambda e: e.update(privateCache='/tmp/private'),
            lambda e: e['requests'][0].update(contactPoint={'name': 'private'}),
            lambda e: e['requests'][0].update(method='GET'),
            lambda e: e['requests'][0].update(url='https://example.com'),
            lambda e: e['requests'][0].update(scope='other'),
            lambda e: e['requests'][0].update(page=True),
            lambda e: e['requests'][0].update(sourceSha256='bad'),
            lambda e: e['requests'][0].update(bytesRead=audit.LIMIT + 1),
            lambda e: e['requests'][0].update(rowCount=19),
            lambda e: e['requests'][0].update(duplicateIDsWithinPage=['UA-2026-10-09-012340-a']),
            lambda e: e['requests'][0].update(inWindowByTenderID=0),
            lambda e: e['requests'][0]['tenderIDs'].__setitem__(0, 'UA-2026-99-09-012340-a'),
            lambda e: e['requests'][0]['pagination'].update(contact='private'),
            lambda e: e['requests'][0]['pagination'].update(total=True),
            lambda e: e['requests'][0]['pagination'].update(page=2),
            lambda e: e['requests'][1].update(retrievedAt=e['requests'][0]['retrievedAt']),
            lambda e: e['requests'][1].update(retrievedAt='2026-10-11T19:30:48+00:00'),
            lambda e: e['requests'][0].update(retrievedAt='2026-10-11T19:30:47'),
            lambda e: e.update(requestCount=4),
            lambda e: e['requests'].append(copy.deepcopy(e['requests'][-1])),
            lambda e: e['bounds'].update(maxRequests=6),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                e = self.evidence()
                mutation(e)
                self.reseal(e)  # a self-checksum cannot legitimize drift
                with self.assertRaises(ValueError):
                    audit.validate(e)

    def test_baseline_and_checksum_drift(self):
        for reseal in (False, True):
            e = self.evidence()
            e['requests'][0]['sourceSha256'] = 'a' * 64
            if reseal:
                self.reseal(e)
            with self.assertRaises(ValueError):
                audit.validate(e)
        e = self.evidence()
        e['analysis']['completenessCertified'] = True
        with self.assertRaises(ValueError):
            audit.validate(e)
        for key, value in [('searchTotal', 501), ('privateCache', '/tmp/raw'),
                           ('auditFileSha256', '0' * 64)]:
            e = self.evidence()
            e['snapshot'][key] = value
            self.reseal(e)
            with self.assertRaises(ValueError):
                audit.validate(e)

    def test_stale_local_sources(self):
        original = Path.read_bytes
        for suffix in ('data/prozorro/raw/manifest.json', 'data/prozorro-audit.json'):
            def read(path):
                body = original(path)
                return body + b' ' if str(path).endswith(suffix) else body
            with patch.object(Path, 'read_bytes', read):
                with self.assertRaises(ValueError):
                    audit.validate(self.evidence())

    def test_failure_must_be_last(self):
        e = self.evidence()
        e['bounds']['wallCapSeconds'] = 15
        r = e['requests'][0]
        for key in ('sourceSha256', 'bytesRead', 'pagination', 'rowCount', 'tenderIDs',
                    'duplicateIDsWithinPage', 'inWindowByTenderID'):
            del r[key]
        r.update(httpStatus=429, error='HTTP failure; stopped without redirect/retry')
        self.reseal(e)
        with self.assertRaises(ValueError):
            audit.validate(e, baseline=False)
        e['requests'] = [r]
        e['requestCount'] = 1
        audit.validate(self.reseal(e), baseline=False)

    def test_strict_json(self):
        for body in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(ValueError):
                audit.strict_json(body)

    def test_offline_fresh_without_private_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('tools/audit-ukraine-discovery.py', 'data/ukraine-discovery-evidence.json',
                         'data/prozorro/raw/manifest.json', 'data/prozorro-audit.json'):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
            # No raw response cache or tender records, and deny any socket use.
            code = ('import runpy,socket,urllib.request; socket.socket=lambda *a,**k: '
                    '(_ for _ in ()).throw(AssertionError("network forbidden")); '
                    'runpy.run_path("tools/audit-ukraine-discovery.py",run_name="__main__")')
            result = subprocess.run([sys.executable, '-c', code], cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), self.evidence())

    def test_unsafe_cache_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            (parent / 'link').symlink_to(parent, target_is_directory=True)
            for dest in (parent / 'link' / 'raw', parent / '..' / 'raw'):
                with self.assertRaises((ValueError, OSError)):
                    audit.Fetcher(dest)
            self.assertFalse((parent / 'raw').exists())
        for dest in (ROOT, ROOT.parent, Path('relative/raw')):
            with self.assertRaises(ValueError):
                audit.Fetcher(dest)

    def test_no_environment_proxy_or_auth(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
                'HTTPS_PROXY': 'http://user:secret@example.com', 'HTTP_PROXY': 'http://example.com'}):
            f = audit.Fetcher(Path(tmp) / 'raw')
            self.addCleanup(f.close)
            self.assertFalse(any(isinstance(h, audit.urllib.request.ProxyHandler) and h.proxies
                                 for h in f.opener.handlers))
            self.assertFalse(any('Auth' in type(h).__name__ or 'Cookie' in type(h).__name__
                                 for h in f.opener.handlers))

    def test_wall_alarm_covers_response_read(self):
        original_timer = audit.signal.setitimer
        def short_timer(which, seconds):
            return original_timer(which, 0.02 if seconds else 0)
        class Slow:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, count):
                time.sleep(0.1)
                return b'{"data":[]}'
        with tempfile.TemporaryDirectory() as tmp:
            f = audit.Fetcher(Path(tmp) / 'raw')
            self.addCleanup(f.close)
            previous = audit.signal.getsignal(audit.signal.SIGALRM)
            with patch.object(f.opener, 'open', return_value=Slow()), patch.object(audit.signal, 'setitimer', short_timer):
                result = f.fetch(1)
            self.assertEqual(result['error'], 'TimeoutError; stopped')
            self.assertTrue(f.stopped)
            self.assertEqual(list(f.path.iterdir()), [])
            self.assertEqual(audit.signal.getitimer(audit.signal.ITIMER_REAL)[0], 0)
            self.assertEqual(audit.signal.getsignal(audit.signal.SIGALRM), previous)
            f.stopped = False
            f.last = None
            with patch.object(f.opener, 'open', side_effect=PermissionError('private path omitted')):
                result = f.fetch(2)
            self.assertEqual(result['error'], 'OSError; stopped')
            self.assertNotIn('private path', json.dumps(result))

    def test_minimize_drops_names_contacts(self):
        body = json.dumps({'total': 1, 'page': 1, 'data': [{'tenderID': 'UA-2026-08-01-001-a',
                            'title': 'private', 'contactPoint': {'name': 'private'}}]}).encode()
        result = audit.minimize(body)
        self.assertNotIn('private', json.dumps(result))
        self.assertEqual(result['inWindowByTenderID'], 1)
        with self.assertRaises(ValueError):
            audit.minimize(b'{"data": [{"tenderID": "bad"}]}')

    def test_probe_adapts_page_size_and_budget(self):
        class Fake:
            count = 0
            stopped = False
            def fetch(self, page, window=False):
                self.count += 1
                return {'page': page, 'scope': 'fixed-window' if window else 'all-time',
                        'rowCount': 20, 'pagination': {'total': 506}, 'tenderIDs': []}
        f = Fake()
        result = audit.probe(f)
        self.assertEqual([r['page'] for r in result], [1, 25, 26, 27, 1])
        self.assertEqual(f.count, 5)
        self.assertEqual(result[-1]['scope'], 'fixed-window')

    def test_stop_on_403_429_no_retry(self):
        for code in (302, 400, 403, 429, 500, 503):
            with tempfile.TemporaryDirectory() as tmp:
                f = audit.Fetcher(Path(tmp) / 'raw')
                with patch.object(f.opener, 'open', side_effect=urllib.error.HTTPError(audit.url(1), code, '', {}, None)) as call:
                    records = audit.probe(f)
                    self.assertEqual(len(records), 1)
                    self.assertEqual(call.call_count, 1)
                    self.assertEqual(records[0]['httpStatus'], code)
                    with self.assertRaises(RuntimeError):
                        f.fetch(2)

    def test_private_exclusive_and_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'raw'
            f = audit.Fetcher(dest)
            self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o700)
            with self.assertRaises(FileExistsError):
                audit.Fetcher(dest)
            class Response:
                status = 200
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def read(self, count): return b'{"total":0,"data":[]}'
            with patch.object(f.opener, 'open', return_value=Response()) as call:
                f.fetch(1)
                self.assertEqual(call.call_args.kwargs['timeout'], 15)
                self.assertEqual(call.call_args.args[0].method, 'POST')
            self.assertEqual(stat.S_IMODE((dest / '01.json').stat().st_mode), 0o600)
        with self.assertRaises(ValueError):
            audit.Fetcher(ROOT / 'not-created')

    def test_oversize_stops_without_saving(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = audit.Fetcher(Path(tmp) / 'raw')
            class Response:
                status = 200
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def read(self, count): return b'x' * count
            with patch.object(f.opener, 'open', return_value=Response()):
                result = f.fetch(1)
            self.assertTrue(f.stopped)
            self.assertEqual(result['bytesRead'], audit.LIMIT + 1)
            self.assertEqual(list(f.path.iterdir()), [])
            e = self.evidence()
            e['requests'], e['requestCount'] = [result], 1
            e['bounds']['wallCapSeconds'] = 15
            audit.validate(self.reseal(e), baseline=False)

    def test_overlap_total_drift(self):
        records = [{'page': p, 'scope': 'all-time', 'tenderIDs': ['UA-2024-09-01-001-a'],
                    'pagination': {'total': p}} for p in (1, 2)]
        result = audit.analyze(records)
        self.assertTrue(result['totalChangedAcrossProbes'])
        self.assertEqual(len(result['pageOverlaps'][0]['sharedTenderIDs']), 1)

    def test_no_redirect(self):
        self.assertIsNone(audit.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com'))

    def test_spacing_and_hard_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = audit.Fetcher(Path(tmp) / 'raw')
            f.last = 10
            with patch.object(audit.time, 'monotonic', return_value=10.25), patch.object(audit.time, 'sleep') as sleep, patch.object(f.opener, 'open', side_effect=TimeoutError()):
                f.fetch(1)
                sleep.assert_called_once_with(0.75)
            f.stopped = False
            f.count = 5
            with self.assertRaises(RuntimeError):
                f.fetch(1)


if __name__ == '__main__':
    unittest.main()
