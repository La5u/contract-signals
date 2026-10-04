import gzip
import importlib.util
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_ukraine_cohort', ROOT / 'tools/build-ukraine-label-cohort.py')
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)


def entry(i, tender, status, created='2025-03-01T10:00:00+02:00'):
    return {'id': f'm{i}', 'tender_id': tender, 'status': status, 'dateCreated': created, 'dateModified': created}


def tender(tid='t1', method='aboveThreshold', buyer='11111111', bids=2, supplier_id='12345678', lots=True, created='2025-03-01'):
    lot = [{'id': 'L1', 'title': 'x'}] if lots else []
    b = [{'id': f'b{k}', 'status': 'active', 'lotValues': [{'relatedLot': 'L1' if k < bids else 'L2'}]} for k in range(bids + 1)]
    return {'id': tid, 'tenderID': 'UA-' + tid, 'procurementMethodType': method, 'dateCreated': created + 'T09:00:00+02:00',
            'status': 'complete', 'mainProcurementCategory': 'goods', 'title': 'SECRET TITLE',
            'procuringEntity': {'name': 'Buyer', 'identifier': {'id': buyer, 'legalName': 'Buyer'}, 'contactPoint': {'email': 'a@b.c'}},
            'tenderPeriod': {'startDate': created + 'T09:00:00+02:00', 'endDate': '2025-03-11T09:00:00+02:00'},
            'lots': lot, 'items': [{'relatedLot': 'L1', 'classification': {'scheme': 'ДК021', 'id': '30190000-7'}}],
            'bids': b, 'awards': [{'id': 'a1', 'lotID': 'L1', 'status': 'active', 'date': '2025-04-01T00:00:00+02:00', 'bid_id': 'b0',
                                   'suppliers': [{'name': 'PRIVATE PERSON', 'identifier': {'scheme': 'UA-EDR', 'id': supplier_id, 'legalName': 'PRIVATE PERSON'}}]}],
            'contracts': [{'id': 'c1' + 'f' * 30, 'awardID': 'a1', 'status': 'active', 'contractID': 'C-1', 'dateSigned': '2025-04-10T00:00:00+02:00',
                           'value': {'amount': 100.0, 'currency': 'UAH'}, 'period': {'startDate': '2025-04-10T00:00:00+02:00', 'endDate': '2026-04-10T00:00:00+02:00'}}]}


class LabelTests(unittest.TestCase):
    def test_tristate_from_status(self):
        f = bc.label_from_statuses
        self.assertIs(f(['addressed']), True)
        self.assertIs(f(['completed']), True)
        self.assertIs(f(['declined']), False)
        self.assertIs(f(['closed']), False)
        self.assertIsNone(f(['active']))
        self.assertIsNone(f(['stopped', 'cancelled']))
        self.assertIs(f(['declined', 'addressed']), True)    # any concluded violation wins
        self.assertIs(f(['stopped', 'declined']), False)
        self.assertIsNone(f([]))

    def test_corruption_category_is_separate_and_unknown_without_detail(self):
        self.assertIs(bc.corruption_label(True, ['corruptionAwarded', 'other']), True)
        self.assertIs(bc.corruption_label(True, ['other']), False)
        self.assertIsNone(bc.corruption_label(True, None))
        self.assertIs(bc.corruption_label(False, None), False)
        self.assertIsNone(bc.corruption_label(None, None))

    def test_pool_uses_only_in_window_monitorings(self):
        entries = {e['id']: e for e in [entry(1, 'a', 'addressed'), entry(2, 'b', 'declined', '2024-08-31T10:00:00+03:00'),
                                        entry(3, 'c', 'stopped'), entry(4, 'a', 'declined', '2026-09-01T00:00:00+03:00')]}
        pool, monitored = bc.monitored_pool(entries)
        self.assertEqual(set(pool), {'a', 'c'})
        self.assertEqual(monitored, {'a', 'b', 'c'})        # all monitored ids stay excluded from comparisons
        self.assertIs(pool['a']['label'], True)
        self.assertIsNone(pool['c']['label'])


class SamplingTests(unittest.TestCase):
    def pool(self, n_true, n_false):
        p = {f't{i}': {'label': True, 'monitorings': []} for i in range(n_true)}
        p.update({f'f{i}': {'label': False, 'monitorings': []} for i in range(n_false)})
        p['z'] = {'label': None, 'monitorings': []}
        return p

    def test_deterministic_and_stratified(self):
        a = bc.sample_monitored(self.pool(100, 80), 40, 1)
        b = bc.sample_monitored(dict(reversed(list(self.pool(100, 80).items()))), 40, 1)
        self.assertEqual(a[0], b[0])
        self.assertEqual((len(a[0][True]), len(a[0][False]), len(a[0][None])), (20, 20, 1))
        self.assertEqual(a[2]['true'], 5.0)

    def test_short_stratum_is_topped_up(self):
        picks, sizes, _ = bc.sample_monitored(self.pool(100, 5), 40, 0)
        self.assertEqual((len(picks[True]), len(picks[False])), (35, 5))
        picks, _, _ = bc.sample_monitored(self.pool(3, 100), 40, 0)
        self.assertEqual((len(picks[True]), len(picks[False])), (3, 37))

    def test_comparison_same_buyer_window_method_and_unmonitored(self):
        meta = {'procedureId': 'm', 'buyerId': 'B', 'created': '2025-03-01', 'procedure': 'aboveThreshold'}
        cands = {'B': [{'id': 'near-other', 'created': '2025-03-05', 'procedure': 'reporting'},
                       {'id': 'same-far', 'created': '2025-07-01', 'procedure': 'aboveThreshold'},
                       {'id': 'same-1', 'created': '2025-04-01', 'procedure': 'aboveThreshold'},
                       {'id': 'same-2', 'created': '2025-01-15', 'procedure': 'aboveThreshold'},
                       {'id': 'm', 'created': '2025-03-01', 'procedure': 'aboveThreshold'}],
                 'C': [{'id': 'other-buyer', 'created': '2025-03-01', 'procedure': 'aboveThreshold'}]}
        order = bc.candidate_order(meta, cands, set())
        ids = [c['id'] for c, _ in order]
        self.assertEqual(set(ids[:2]), {'same-1', 'same-2'})
        self.assertEqual(ids[2], 'near-other')
        self.assertEqual(len(ids), 3)
        self.assertEqual(order[0][1], 'same_buyer_same_method_90d')
        self.assertEqual(order[2][1], 'same_buyer_other_method_90d')
        self.assertEqual(ids, [c['id'] for c, _ in bc.candidate_order(meta, cands, set())])
        self.assertNotIn('same-1', [c['id'] for c, _ in bc.candidate_order(meta, cands, {'same-1'})])


class RowTests(unittest.TestCase):
    def test_offers_attributed_per_lot_and_period_fields(self):
        rows, excluded = bc.tender_rows(tender(bids=2))
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r['offers'], 2)               # the third bid points to another lot
        self.assertIs(r['procedureDirect'], False)
        self.assertIs(r['reporting'], False)
        self.assertEqual((r['tenderPeriodDays'], r['tenderPeriodStart'], r['tenderPeriodEnd']), (10, '2025-03-01', '2025-03-11'))
        self.assertAlmostEqual(r['durationMonths'], 12.0, delta=0.05)
        self.assertEqual(r['awardDate'], '2025-04-01')
        self.assertEqual((r['buyerId'], r['cpv'], r['category'], r['currency'], r['lotCount']), ('11111111', '30190000', 'goods', 'UAH', 1))

    def test_reporting_has_unknown_offers_and_flag(self):
        t = tender(method='reporting', bids=0, lots=False)
        t['bids'] = []
        rows, _ = bc.tender_rows(t)
        self.assertIs(rows[0]['reporting'], True)
        self.assertIsNone(rows[0]['offers'])
        self.assertIsNone(rows[0]['procedureDirect'])

    def test_natural_person_masked_and_no_names_kept(self):
        rows, _ = bc.tender_rows(tender(supplier_id='1234567890'))
        text = json.dumps(rows, ensure_ascii=False)
        self.assertNotIn('1234567890', text)
        self.assertTrue(rows[0]['supplierIds'][0]['id'].startswith('masked-'))
        for secret in ('PRIVATE PERSON', 'SECRET TITLE', 'a@b.c'):
            self.assertNotIn(secret, text)
        rows, _ = bc.tender_rows(tender(supplier_id='12345678'))
        self.assertEqual(rows[0]['supplierIds'][0]['id'], '12345678')     # company EDRPOU stays

    def test_unsigned_contract_gives_no_row(self):
        t = tender()
        t['contracts'][0]['status'] = 'pending'
        rows, excluded = bc.tender_rows(t)
        self.assertEqual(rows, [])
        self.assertEqual(sum(excluded.values()), 1)


class FakeNet:
    def __init__(self, replies):
        self.replies, self.calls = replies, []

    def __call__(self, url):
        self.calls.append(url)
        r = self.replies.get(url, (200, b'{"data": []}', {}))
        if isinstance(r, list):
            r = r.pop(0)
        return r


class FetcherTests(unittest.TestCase):
    def make(self, net, **kw):
        d = tempfile.mkdtemp()
        sleeps = []
        f = bc.Fetcher(d, network=True, opener=net, sleep=sleeps.append, clock=lambda: 0.0, prior=0, **kw)
        return f, d, sleeps

    def test_budget_cap_survives_restart_and_cache_is_free(self):
        net = FakeNet({})
        f, d, _ = self.make(net, budget=2)
        f.fetch('u1')
        f.fetch('u2')
        f.fetch('u1')                                   # cached: no request
        with self.assertRaises(bc.BudgetExceeded):
            f.fetch('u3')
        self.assertEqual(len(net.calls), 2)
        g = bc.Fetcher(d, budget=2, network=True, opener=net, sleep=lambda s: None, prior=0)
        self.assertEqual(g.requests, 2)
        with self.assertRaises(bc.BudgetExceeded):
            g.fetch('u4')

    def test_backoff_honours_retry_after_and_counts_attempts(self):
        net = FakeNet({'u': [(429, b'', {'Retry-After': '7'}), (503, b'', {}), (200, b'{"data": [1]}', {})]})
        f, _, sleeps = self.make(net, budget=10)
        r = f.fetch('u')
        self.assertEqual(r['status'], 200)
        self.assertEqual(f.requests, 3)
        self.assertEqual([s for s in sleeps if s != 1.0], [7.0, 10])

    def test_forbidden_stops_and_missing_is_cached(self):
        f, _, _ = self.make(FakeNet({'b': (403, b'', {}), 'n': (404, b'', {})}), budget=10)
        with self.assertRaises(bc.Blocked):
            f.fetch('b')
        self.assertEqual(f.fetch('n')['status'], 404)
        self.assertEqual(f.fetch('n')['cached'], True)
        self.assertEqual(f.requests, 2)

    def test_spacing_between_requests(self):
        ticks = iter([0.0, 0.2, 0.2, 0.2, 5.0, 5.0, 5.0])
        d = tempfile.mkdtemp()
        sleeps = []
        f = bc.Fetcher(d, network=True, opener=FakeNet({}), sleep=sleeps.append, clock=lambda: next(ticks), prior=0)
        f.fetch('a')
        f.fetch('b')
        self.assertEqual(len(sleeps), 1)
        self.assertAlmostEqual(sleeps[0], 0.8)

    def test_gzip_cache_and_hash(self):
        f, d, _ = self.make(FakeNet({'u': (200, b'{"data": []}', {})}), budget=5)
        r = f.fetch('u')
        files = sorted(p.name for p in Path(d).iterdir())
        self.assertTrue(any(n.endswith('.gz') for n in files))
        gz = next(p for p in Path(d).iterdir() if p.suffix == '.gz')
        self.assertEqual(gzip.decompress(gz.read_bytes()), b'{"data": []}')
        self.assertEqual(len(r['sha256']), 64)

    def test_offline_returns_none_when_uncached(self):
        f = bc.Fetcher(tempfile.mkdtemp(), network=False)
        self.assertIsNone(f.fetch('x'))


class EndToEnd(unittest.TestCase):
    def test_assemble_labels_and_nulls(self):
        t1, t2 = tender('t1'), tender('t2', buyer='22222222')
        rows1, ex1 = bc.tender_rows(t1)
        rows2, ex2 = bc.tender_rows(t2)
        mon = [{'id': 'm1', 'status': 'addressed', 'dateCreated': '2025-03-02T00:00:00+02:00', 'dateModified': '2025-03-05T00:00:00+02:00'}]
        resp = {'sha256': 'h', 'retrieved_at': 'now'}
        records = [{'role': 'monitored', 'meta': bc.tender_meta(t1), 'rows': rows1, 'excluded': ex1, 'monitorings': mon,
                    'stratum_label': True, 'response': resp},
                   {'role': 'comparison', 'meta': bc.tender_meta(t2), 'rows': rows2, 'excluded': ex2, 'matched_to': 'UA-t1',
                    'selection': 'same_buyer_other_method_90d', 'candidates_available': 3, 'response': resp},
                   {'role': 'monitored', 'procedureId': 'gone', 'unavailable': 'missing_or_mismatched_record', 'rows': [], 'excluded': {}}]
        details = {'m1': {'status': 'addressed', 'concluded': True, 'violation_occurred': True, 'violation_types': ['corruptionAwarded'],
                          'sha256': 'x', 'retrieved_at': 'now'}}
        f = bc.Fetcher(tempfile.mkdtemp(), network=False)
        out = bc.assemble(records, details, [], {'true': {}}, {'true': 2.0, 'false': 1.0, 'null': None}, f, [], [], True, 0, [], None,
                          {}, {}, {})
        by = {t.get('tenderID') or t['procedureId']: t for t in out['tenders']}
        self.assertIs(by['UA-t1']['labels']['audit_violation'], True)
        self.assertIs(by['UA-t1']['labels']['audit_violation_corruption_category'], True)
        self.assertIsNone(by['UA-t2']['labels']['audit_violation'])          # comparison: unknown, not clean
        self.assertEqual(by['UA-t2']['selection']['method'], 'same_buyer_other_method_90d')
        self.assertTrue(by['gone']['unavailable'])
        self.assertEqual(out['summary']['monitored_by_label'], {'true': 1})
        self.assertEqual(out['summary']['monitored_unavailable'], 1)
        self.assertEqual({r['role'] for r in out['rows']}, {'monitored', 'comparison'})


if __name__ == '__main__':
    unittest.main()
