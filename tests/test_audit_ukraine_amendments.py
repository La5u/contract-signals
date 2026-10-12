import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('amendments', ROOT / 'tools/audit-ukraine-amendments.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan, cls.binds = A.inventory()
        cls.doc = A.load(A.OUTPUT)

    def rejected(self, change):
        doc = copy.deepcopy(self.doc)
        change(doc)
        with self.assertRaises(ValueError):
            A.replay(doc, self.plan, self.binds)

    def payload(self):
        b = self.plan['selected'][0]
        return {'data': {'id': b['contractInternalId'], 'contractID': b['contractId'],
                         'tender_id': b['tenderInternalId'], 'awardID': b['awardId'], 'status': 'active'}}

    def test_offline_full_population_and_no_source_writes(self):
        sources = {**self.plan['inputHashes'], **self.plan['rawSnapshotHashes']}
        before = {p: (ROOT / p).stat().st_mtime_ns for p in sources}
        with patch.object(A, 'fetch', side_effect=AssertionError('Offline network')):
            result = A.replay(self.doc, self.plan, self.binds)
        self.assertEqual(result['rows'], 488)
        self.assertEqual(result['requests'], 12)
        self.assertEqual(result['snapshotCounts'], {'0': 469, '1': 13, '2': 5, '3': 1})
        self.assertEqual(before, {p: (ROOT / p).stat().st_mtime_ns for p in sources})

    def test_default_inventory_needs_no_private_freeze(self):
        original = A.load
        def public_only(path):
            if Path(path) == A.PRIVATE_PLAN:
                raise AssertionError('Offline replay accessed private freeze')
            return original(path)
        with patch.object(A, 'load', side_effect=public_only):
            plan, binds = A.inventory()
            self.assertEqual(plan, self.plan)
            self.assertEqual(binds, self.binds)
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / 'missing-private-plan.json'
            with self.assertRaises(FileNotFoundError):
                A.inventory(private_plan=missing)

    def test_source_formatting_changes_do_not_invalidate_inventory(self):
        original = Path.read_bytes
        def changed(path):
            value = original(path)
            return value + b' ' if path == ROOT / 'data/prozorro.json' else value
        with patch.object(Path, 'read_bytes', changed):
            plan, binds = A.inventory()
        self.assertEqual(A.without_hashes(plan), A.without_hashes(self.plan))
        self.assertEqual(A.without_hashes(binds), A.without_hashes(self.binds))

    def test_stale_evidence_and_incomplete_binds(self):
        self.rejected(lambda d: d['rows'].pop())

    def test_hash_metadata_is_ignored(self):
        doc = copy.deepcopy(self.doc)
        doc.update(planSha256='ignored', evidenceSha256='ignored', inputHashes={}, rawSnapshotHashes={})
        doc['rows'][0].update(rowSha256='ignored', rawSha256='ignored')
        doc['requests'][0]['binding'].update(rowSha256='ignored', selectionRankSha256='ignored')
        doc['requests'][0]['responseSha256'] = 'ignored'
        self.assertEqual(A.replay(doc, self.plan, self.binds), A.replay(self.doc, self.plan, self.binds))

    def test_duplicate_selection_wrong_ids_endpoints(self):
        self.rejected(lambda d: d['requests'].__setitem__(1, copy.deepcopy(d['requests'][0])))
        self.rejected(lambda d: d['requests'][0]['binding'].update(awardId='wrong'))
        self.rejected(lambda d: d['requests'][0].update(url='https://example.org'))
        for key in ('id', 'contractID', 'tender_id', 'awardID'):
            p = self.payload(); p['data'][key] = 'wrong'
            with self.assertRaisesRegex(ValueError, 'identity'):
                A.extract(p, self.plan['selected'][0])

    def test_missing_is_not_empty_or_zero(self):
        p = self.payload()
        missing = A.extract(p, self.plan['selected'][0])
        self.assertEqual(missing['changesState'], 'unavailable')
        self.assertIsNone(missing['changeCount'])
        p['data']['changes'] = []
        empty = A.extract(p, self.plan['selected'][0])
        self.assertEqual(empty['changesState'], 'retrieved-empty-array')
        self.assertEqual(empty['changeCount'], 0)
        p['data']['changes'] = None
        self.assertIsNone(A.extract(p, self.plan['selected'][0])['changeCount'])
        self.rejected(lambda d: d['requests'][0]['extract'].update(changeCount=0))
        self.rejected(lambda d: d['requests'][0]['extract'].update(changesState='retrieved-empty-array'))

    def test_change_status_dates_duplicates_and_types_explicit(self):
        p = self.payload()
        p['data']['changes'] = [{'id': 'abc', 'status': 'active', 'dateSigned': 'bad',
                                'date': '2025-01-01T00:00:00+00:00', 'rationaleTypes': ['qualityImprovement']},
                               {'id': 'abc', 'status': 'pending', 'rationaleTypes': ['secret free text']}]
        e = A.extract(p, self.plan['selected'][0])
        self.assertEqual(e['changeCount'], 2)
        self.assertEqual(e['activeChangeCount'], 1)
        self.assertTrue(any('duplicate-id' in x for x in e['anomalies']))
        self.assertTrue(any('dateSigned' in x for x in e['anomalies']))
        self.assertNotIn('secret free text', json.dumps(e))
        self.assertEqual(e['legalBasis'], 'unknown')
        self.rejected(lambda d: d['requests'][2]['extract'].update(activeChangeCount=0))
        self.rejected(lambda d: d['requests'][2]['extract']['anomalies'].append('invented'))
        def change_date(d):
            s = next(s for s in d['requests'][2]['extract']['scalars'] if s['pointer'].endswith('/dateSigned'))
            s['value'] = 'not a date'
        self.rejected(change_date)
        def change_type(d):
            s = next(s for s in d['requests'][2]['extract']['scalars'] if '/rationaleTypes/' in s['pointer'])
            s['value'] = 'free-form private rationale'
        self.rejected(change_type)

    def test_privacy_allowlist_and_pointer_rejection(self):
        p = self.payload()
        p['data'].update(suppliers=[{'name': 'SECRET PERSON'}], rationale='SECRET PERSON', title='SECRET PERSON',
                         documents=[{'id': 'abc', 'title': 'SECRET PERSON', 'url': 'https://private/?token=SECRET',
                                     'format': 'application/pdf', 'documentType': 'contractSigned'}])
        e = A.extract(p, self.plan['selected'][0])
        self.assertNotIn('SECRET', json.dumps(e))
        self.rejected(lambda d: d['requests'][0]['extract']['scalars'].append({'pointer': '/data/name', 'value': 'SECRET'}))
        self.rejected(lambda d: d['requests'][0]['extract']['scalars'].append(copy.deepcopy(d['requests'][0]['extract']['scalars'][0])))
        self.rejected(lambda d: d['requests'][0]['extract'].update(legalBasis='legal'))

    def test_ledger_bounds_stop_and_spacing(self):
        self.rejected(lambda d: d['requests'][0].update(responseBytes=A.LIMIT + 1))
        self.rejected(lambda d: d['requests'][0].update(httpStatus=403))
        self.rejected(lambda d: d['requests'][0].update(httpStatus=429))
        self.rejected(lambda d: d['requests'][1].update(startedAt=d['requests'][0]['startedAt']))
        self.rejected(lambda d: d.update(supplementaryRequests=3))
        def truncate(d):
            d['requests'].pop(); d['requestCount'] -= 1
        self.rejected(truncate)
        self.rejected(lambda d: d['requests'][0].update(rawBody='PRIVATE'))
        self.rejected(lambda d: d['requests'][0].update(rawPrivateFile='/unsafe/raw'))

    def test_fetch_stop_no_redirect_retry_and_private_files(self):
        for status in (403, 429):
            with tempfile.TemporaryDirectory() as temp:
                def run(argv, **kwargs):
                    self.assertNotIn('--location', argv)
                    self.assertEqual(argv[argv.index('--retry') + 1], '0')
                    self.assertEqual(argv[argv.index('--max-time') + 1], '15')
                    self.assertEqual(argv[argv.index('--max-filesize') + 1], str(A.LIMIT))
                    kwargs['stdout'].write(b'blocked')
                    return types.SimpleNamespace(returncode=0, stderr=str(status).encode())
                with patch.object(A.subprocess, 'run', side_effect=run) as mocked:
                    ledger = A.fetch(self.plan, Path(temp))
                self.assertEqual(mocked.call_count, 1)
                self.assertEqual(len(ledger), 1)
                file = Path(temp) / ledger[0]['rawPrivateFile']
                self.assertEqual(file.stat().st_mode & 0o777, 0o600)
                with self.assertRaises(FileExistsError), patch.object(A.subprocess, 'run'):
                    A.fetch(self.plan, Path(temp))

    def test_private_directory_permissions_and_external(self):
        with tempfile.TemporaryDirectory() as home:
            with patch.object(A.Path, 'home', return_value=Path(home)):
                directory = A.private_directory()
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            self.assertFalse(directory.resolve().is_relative_to(ROOT))


if __name__ == '__main__':
    unittest.main()
