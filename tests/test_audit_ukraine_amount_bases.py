import copy
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('amount_bases', ROOT / 'tools/audit-ukraine-amount-bases.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class Response:
    status = 200
    def __init__(self, body):
        self.body = body
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, count):
        chunk, self.body = self.body[:count], self.body[count:]
        return chunk


class AmountBasisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan, cls.rows = audit.validate_plan()
        cls.base = audit.baseline()

    def test_offline_inventory_and_source_immutability(self):
        hashes = {p: audit.sha((ROOT / p).read_bytes()) for p in self.plan['inputHashes']}
        evidence = audit.replay()
        result = evidence['analysis']
        self.assertEqual((result['exactMappings'], result['amountDifferences'], result['tupleDifferences'], result['otherTupleDifferences']), (488, 11, 25, 14))
        self.assertEqual(result['explanations']['explicit-contract-net-equals-award-excluding-vat'], 7)
        self.assertEqual(self.base['requests'], [])
        self.assertEqual(len(evidence['requests']), 11)
        self.assertTrue(all(r['httpStatus'] == 200 for r in evidence['requests']))
        self.assertTrue(all(r['financialSnapshotChanged'] is False for r in result['liveOutcomes']))
        self.assertFalse(result['paidCertified'])
        self.assertEqual(hashes, {p: audit.sha((ROOT / p).read_bytes()) for p in hashes})
        for c in evidence['cases']:
            scalars = c['extract']['scalars']
            self.assertFalse(any(any(word in k for word in ('supplier', 'title', 'contact', 'description')) for k in scalars))

    def test_default_offline_does_not_fetch_or_rewrite(self):
        before = audit.EVIDENCE.read_bytes()
        with patch('sys.argv', ['audit']), patch('sys.stdout', new_callable=io.StringIO), patch.object(urllib.request.OpenerDirector, 'open', side_effect=AssertionError('network forbidden')):
            audit.main()
        self.assertEqual(audit.EVIDENCE.read_bytes(), before)

    def test_cached_amendment_metadata_is_not_financial_version_proof(self):
        cases = [c for c in self.base['cases'] if 'amount' in c['differenceFields']]
        self.assertEqual(sorted(c['amendmentMetadata']['published']['changes'] for c in cases), [0] * 8 + [1, 2, 2])
        for c in cases:
            s, ex = c['extract']['scalars'], c['extract']
            self.assertNotIn(ex['contractPointer'] + '/dateSigned', s)
            self.assertGreater(s[ex['contractPointer'] + '/date'], s[ex['awardPointer'] + '/date'])
            if c['explanation'] == 'unresolved-field-difference':
                self.assertEqual(c['amendmentMetadata']['published']['changes'], 0)

    def test_raw_value_presence_is_preserved(self):
        row, obj = self.source()
        contract = obj['data']['contracts'][0]
        for state, value in [('absent', 'delete'), ('null', None), ('empty-object', {})]:
            if value == 'delete': contract.pop('value', None)
            else: contract['value'] = value
            self.assertEqual(audit.extract(row, obj)['rawValueStates']['contract'], state)

    def test_zero_absent_null_and_vat_false(self):
        self.assertIn('amount', audit.tuple_diff({'amount': 0}, {}))
        self.assertIn('amount', audit.tuple_diff({'amount': None}, {}))
        self.assertIn('valueAddedTaxIncluded', audit.tuple_diff({}, {'valueAddedTaxIncluded': False}))
        self.assertIn('valueAddedTaxIncluded', audit.tuple_diff({'valueAddedTaxIncluded': None}, {'valueAddedTaxIncluded': False}))
        self.assertEqual(audit.tuple_diff({'amount': 0}, {'amount': 0.0}), [])
        self.assertEqual(audit.normalized({'amount': 0}, {'amount': 9})['amount'], 0)

    def test_currency_vat_and_explicit_net_basis(self):
        c = {'amount': 120, 'amountNet': 100, 'currency': 'UAH', 'valueAddedTaxIncluded': True}
        a = {'amount': 100, 'currency': 'UAH', 'valueAddedTaxIncluded': False}
        self.assertEqual(audit.explanation(c, a), 'explicit-contract-net-equals-award-excluding-vat')
        for update in ({'currency': 'EUR'}, {'valueAddedTaxIncluded': None}, {'amount': 99}):
            self.assertEqual(audit.explanation(c, a | update), 'unresolved-field-difference')
        self.assertEqual(audit.explanation({k: v for k, v in c.items() if k != 'amountNet'}, a), 'unresolved-field-difference')
        self.assertEqual(audit.explanation(c, {k: v for k, v in a.items() if k != 'valueAddedTaxIncluded'}), 'unresolved-field-difference')
        self.assertEqual(audit.tuple_diff({'currency': 'EUR'}, {'currency': 'UAH'}), ['currency'])

    def test_fallback_is_explicit_not_replacement(self):
        self.assertEqual(audit.normalized({}, {'amount': 9})['basis'], 'award-fallback')
        self.assertEqual(audit.normalized({'currency': 'UAH'}, {'amount': 9})['amount'], None)
        self.assertEqual(audit.normalized({}, {})['basis'], 'absent')

    def source(self):
        b = self.plan['amountReviewQueue'][0]
        import gzip
        return self.rows[int(b['rowPointer'][1:])], json.loads(gzip.decompress((ROOT / b['rawPath']).read_bytes()))

    def test_full_identity_ambiguity_and_no_heuristics(self):
        row, obj = self.source()
        for mutation in ('duplicate-contract', 'duplicate-award', 'buyer', 'lot', 'contractID', 'awardID', 'tenderID', 'endpoint'):
            r, o = copy.deepcopy(row), copy.deepcopy(obj)
            t = o['data']
            if mutation == 'duplicate-contract': t['contracts'].append(copy.deepcopy(t['contracts'][0]))
            elif mutation == 'duplicate-award': t['awards'].append(copy.deepcopy(t['awards'][0]))
            elif mutation == 'buyer': t['procuringEntity']['identifier']['id'] = 'other'
            elif mutation == 'lot': t['awards'][0]['lotID'] = 'other'
            elif mutation == 'contractID': t['contracts'][0]['contractID'] = 'other'
            elif mutation == 'awardID': t['contracts'][0]['awardID'] = 'other'
            elif mutation == 'tenderID': t['tenderID'] = 'other'
            else: r['source'] += '?redirect=1'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): audit.extract(r, o)

    def test_minimization_and_pointer_hash(self):
        row, obj = self.source()
        obj['data']['title'] = 'SECRET'
        obj['data']['contracts'][0]['documents'] = [{'title': 'SECRET'}]
        ex = audit.extract(row, obj)
        self.assertNotIn('SECRET', json.dumps(ex))
        self.assertEqual(ex['scalarSha256'], audit.sha(audit.canonical(ex['scalars'])))
        self.assertIn('amountNet', audit.values(ex, 'contract'))

    def test_staleness_plan_and_public_extract_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'plan.json'
            p = copy.deepcopy(self.plan)
            p['amountReviewQueue'][0]['tenderURL'] += '/wrong'
            path.write_text(json.dumps(p))
            with self.assertRaisesRegex(ValueError, 'plan hash'): audit.validate_plan(plan_path=path)
            (Path(tmp) / 'data').mkdir()
            (Path(tmp) / 'data/prozorro.json').write_text('[]')
            with self.assertRaisesRegex(ValueError, 'Stale source'): audit.validate_plan(root=tmp)
            ev = copy.deepcopy(self.base)
            ev['cases'][0]['normalized']['amount'] = 0
            path.write_text(json.dumps(ev))
            with self.assertRaisesRegex(ValueError, 'modified public'): audit.replay(path)

    def fetcher(self, tmp):
        return audit.Fetcher(Path(tmp) / 'new', self.rows, self.plan)

    def test_exclusive_cache_modes_no_redirect_no_auth(self):
        row, obj = self.source()
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fetcher(tmp)
            self.assertEqual(stat.S_IMODE(f.path.stat().st_mode), 0o700)
            with self.assertRaises(FileExistsError): self.fetcher(tmp)
            with patch.object(f.opener, 'open', return_value=Response(audit.canonical(obj))) as call:
                rec = f.fetch(row['source'])
            self.assertEqual(call.call_args.kwargs['timeout'], 15)
            request = call.call_args.args[0]
            self.assertEqual(request.method, 'GET')
            self.assertNotIn('Authorization', request.headers)
            self.assertTrue(rec['completeBody'])
            self.assertEqual(rec['fullByteSha256'], audit.sha(audit.canonical(obj)))
            self.assertTrue(all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in f.path.iterdir()))
            with self.assertRaises(ValueError): f.fetch(row['source'])
        self.assertIsNone(audit.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other'))
        with self.assertRaises(ValueError): audit.Fetcher(ROOT / 'not-created', self.rows, self.plan)

    def test_stop_403_429_and_redirects(self):
        for status in (403, 429, 302):
            with tempfile.TemporaryDirectory() as tmp:
                f = self.fetcher(tmp)
                url = self.plan['amountReviewQueue'][0]['tenderURL']
                with patch.object(f.opener, 'open', side_effect=urllib.error.HTTPError(url, status, '', {}, None)) as call:
                    rec = f.fetch(url)
                    self.assertEqual(call.call_count, 1)
                self.assertEqual(rec['httpStatus'], status)
                self.assertTrue(f.stopped)
                self.assertEqual(len(list(f.path.glob('*.ledger.json'))), 1)
                with self.assertRaises(ValueError): f.fetch(self.plan['amountReviewQueue'][1]['tenderURL'])

    def test_caps_spacing_unplanned_and_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fetcher(tmp)
            url = self.plan['amountReviewQueue'][0]['tenderURL']
            with self.assertRaises(ValueError): f.fetch(url + '?x=1')
            self.assertEqual(f.count, 0)
            f.last = 10
            with patch.object(audit.time, 'monotonic', return_value=10.25), patch.object(audit.time, 'sleep') as sleep, patch.object(f.opener, 'open', side_effect=TimeoutError()):
                rec = f.fetch(url)
                sleep.assert_called_once_with(0.75)
            self.assertTrue(f.stopped)
            self.assertIsNone(rec['fullByteSha256'])
            f.stopped = False
            f.count = 11
            with self.assertRaises(ValueError): f.fetch(self.plan['amountReviewQueue'][1]['tenderURL'])
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fetcher(tmp)
            with patch.object(f.opener, 'open', return_value=Response(b'x' * (audit.LIMIT + 1))):
                rec = f.fetch(url)
            self.assertEqual(rec['bytesRead'], audit.LIMIT + 1)
            self.assertFalse(rec['completeBody'])
            self.assertIsNone(rec['fullByteSha256'])
            self.assertTrue(f.stopped)

    def test_live_public_replay_without_private_cache(self):
        row, obj = self.source()
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fetcher(tmp)
            with patch.object(f.opener, 'open', return_value=Response(audit.canonical(obj))):
                rec = f.fetch(row['source'])
            evidence = copy.deepcopy(self.base)
            evidence['requests'] = [rec]
            path = Path(tmp) / 'public.json'
            path.write_text(json.dumps(evidence))
            # Replay does not inspect the private bodies or private freeze.
            with patch.object(audit.PRIVATE_PLAN.__class__, 'exists', side_effect=AssertionError('no private check')):
                self.assertEqual(audit.replay(path)['analysis']['liveAttempts'], 1)
            evidence['requests'][0]['extract']['scalars']['/data/title'] = 'SECRET'
            ex = evidence['requests'][0]['extract']
            ex['scalarSha256'] = audit.sha(audit.canonical(ex['scalars']))
            path.write_text(json.dumps(evidence))
            with self.assertRaises(ValueError): audit.replay(path)


if __name__ == '__main__':
    unittest.main()
