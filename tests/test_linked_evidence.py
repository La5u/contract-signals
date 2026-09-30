import copy
import importlib.util
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from tools.linked_evidence import bid_attrition, notice_change

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('linked_fetch', ROOT / 'tools/fetch-linked-records.py')
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)


class EvidenceTests(unittest.TestCase):
    def bids(self):
        winner = {'id': 'winner', 'bid_id': 'a', 'lotID': 'lot', 'status': 'active', 'qualified': True, 'eligible': True}
        loser = {'id': 'loser', 'bid_id': 'b', 'lotID': 'lot', 'status': 'unsuccessful', 'qualified': False}
        tender = {'status': 'complete', 'lots': [{'id': 'lot'}], 'bids': [
            {'id': b, 'lotValues': [{'relatedLot': 'lot'}]} for b in ['a', 'b']], 'awards': [winner, loser]}
        return tender, winner

    def test_attrition_requires_explicit_decisions_for_every_bid(self):
        t, a = self.bids()
        self.assertEqual(bid_attrition(t, a, True)['status'], 'signal')
        for mutate in [lambda t: t['awards'][1].pop('qualified'),
                       lambda t: t['awards'][1].update(status='pending'),
                       lambda t: t['awards'].append(dict(t['awards'][1])),
                       lambda t: t['bids'].append({'id': 'c', 'lotValues': [{'relatedLot': 'lot'}]}),
                       lambda t: t.update(status='active.awarded'),
                       lambda t: t['awards'][1].update(lotID='other')]:
            x = copy.deepcopy(t); mutate(x)
            self.assertEqual(bid_attrition(x, x['awards'][0], True)['status'], 'unknown')
        self.assertEqual(bid_attrition(t, a, False)['status'], 'not-applicable')

    def test_inconclusive_attrition_keeps_no_partial_decisions(self):
        t, a = self.bids()
        t['bids'].append({'id': 'c', 'lotValues': [{'relatedLot': 'lot'}]})
        t['awards'].append({'id': 'third', 'bid_id': 'c', 'lotID': 'lot', 'status': 'pending'})
        result = bid_attrition(t, a, True)
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(result['decisions'], [])
        self.assertEqual(len(bid_attrition(*self.bids(), True)['decisions']), 2)

    def test_no_cross_lot_transfer_or_single_offer_attrition(self):
        t, a = self.bids()
        t['bids'][1]['lotValues'][0]['relatedLot'] = 'other'
        self.assertEqual(bid_attrition(t, a, True)['status'], 'not-applicable')
        t['bids'] = []
        self.assertEqual(bid_attrition(t, a, True)['status'], 'unknown')

    def notices(self):
        p = {'description': 'Original', 'noticeEvidence': {'lotTitle': 'Original', 'kind': 'initial', 'procedureId': 'proc', 'lotId': 'lot',
             'noticeId': 'old', 'publicationDate': '2025-01-01', 'deadline': {'iso': '2025-01-20T12:00:00Z'}}}
        c = copy.deepcopy(p)
        c['description'] = 'Changed'
        c['noticeEvidence'].update(lotTitle='Changed', kind='correction', noticeId='new', publicationDate='2025-01-17')
        return c, p

    def test_notice_pair_window_extension_and_conflicts(self):
        c, p = self.notices()
        self.assertEqual(notice_change(c, p)['status'], 'signal')
        c['noticeEvidence']['deadline']['iso'] = '2025-01-21T12:00:00Z'
        self.assertEqual(notice_change(c, p)['status'], 'clear')
        for field, value in [('deadlineConflict', True), ('procedureId', 'other'), ('lotId', 'other')]:
            x = copy.deepcopy(c); x['noticeEvidence'][field] = value
            self.assertEqual(notice_change(x, p)['status'], 'unknown')
        self.assertEqual(notice_change(c, None)['status'], 'unknown')
        c, p = self.notices(); c['noticeEvidence']['lotTitle'] = p['noticeEvidence']['lotTitle']
        self.assertEqual(notice_change(c, p)['status'], 'unknown')
        c['noticeEvidence']['lotTitle'] = 'Changed'; c['noticeEvidence']['publicationDate'] = '2025-01-20'
        self.assertEqual(notice_change(c, p)['status'], 'unknown')  # same day could be after deadline


class FetchTests(unittest.TestCase):
    def items(self, n=5):
        return [{'url': f'https://public-api.prozorro.gov.ua/api/2.5/contracts/{i:032x}'} for i in range(n)]

    def test_budget_cache_pacing_and_no_retries(self):
        calls, sleeps = [], []
        class Response(io.BytesIO):
            status = 200
        def opener(req, timeout):
            calls.append(req.full_url)
            self.assertEqual(timeout, 15)
            return Response(b'{"data": {"id": "record"}}')
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            report = fetch.fetch_plan(self.items(), cache, opener, clock=lambda: 100, sleep=sleeps.append)
            self.assertEqual(report['requestsMade'], 3)
            self.assertEqual(sleeps, [3, 3])
            again = fetch.fetch_plan(self.items(), cache, opener, clock=lambda: 100, sleep=sleeps.append)
            self.assertEqual(again['requestsMade'], 0)
            self.assertEqual(len(calls), 3)

    def test_retry_after_and_access_denial_stop_across_runs(self):
        for status, headers in [(429, {'Retry-After': '7200'}), (503, {}), (403, {})]:
            calls = []
            def opener(req, timeout):
                calls.append(req.full_url)
                raise urllib.error.HTTPError(req.full_url, status, 'stop', headers, None)
            with tempfile.TemporaryDirectory() as tmp:
                cache = Path(tmp)
                result = fetch.fetch_plan(self.items(), cache, opener, clock=lambda: 100, sleep=lambda _: None)
                self.assertEqual(result['requestsMade'], 1)
                with self.assertRaises(RuntimeError):
                    fetch.fetch_plan(self.items(), cache, opener, clock=lambda: 101, sleep=lambda _: None)
                self.assertEqual(len(calls), 1)
        self.assertEqual(fetch.cooldown_until({'Retry-After': '7200'}, 100), 7300)

    def test_endpoint_allowlist_and_redirect_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                fetch.fetch_plan([{'url': 'https://example.com/private'}], Path(tmp))
        self.assertIsNone(fetch.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com'))

    def test_oversized_response_stops_batch(self):
        class Response(io.BytesIO):
            status = 200
        with tempfile.TemporaryDirectory() as tmp:
            r = fetch.fetch_plan(self.items(), Path(tmp), lambda *a, **k: Response(b'x' * (fetch.MAX_BYTES + 1)))
            self.assertEqual(r['requestsMade'], 1)
            self.assertIn('budget', r['records'][0]['error'])

    def test_link_requires_all_three_ids_and_minimizes_metadata(self):
        import gzip
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            source = {'id': 'internal', 'contractID': 'public', 'tender_id': 'tender',
                      'suppliers': [{'contactPoint': {'telephone': 'private'}}],
                      'changes': [{'id': 'change', 'status': 'active', 'date': '2025-01-01',
                                   'rationaleTypes': ['priceReductionWithoutQuantity'], 'rationale': 'unnecessary personal details'}]}
            def summary(record):
                payload = json.dumps({'data': record}).encode()
                (cache / 'body.gz').write_bytes(gzip.compress(payload))
                item = {'rowId': 'r', 'url': 'https://source', 'retrievedAt': '2026-09-28',
                        'tenderId': 'tender', 'contractId': 'public', 'internalId': 'internal',
                        'httpStatus': 200, 'cacheFile': 'body.gz', 'sha256': hashlib.sha256(payload).hexdigest()}
                return fetch.summarize({'records': [item]}, cache)['records'][0]
            linked = summary(source)
            self.assertEqual(linked['status'], 'linked')
            self.assertEqual(linked['publishedChangeCount'], 1)
            self.assertNotIn('rationale', linked['changes'][0])
            self.assertNotIn('suppliers', linked)
            for key in ['id', 'contractID', 'tender_id']:
                wrong = dict(source); wrong[key] = 'other'
                self.assertEqual(summary(wrong)['status'], 'identity-mismatch')
            absent = dict(source); absent.pop('changes')
            self.assertIsNone(summary(absent)['publishedChangeCount'])

    def test_plan_is_bounded_unique_and_identifier_only(self):
        rows = [{'id': str(i), 'contractInternalId': f'{i:032x}', 'procedureId': 't', 'contractId': 'c'} for i in range(10)]
        self.assertEqual(len(fetch.plan(rows)), 3)
        self.assertEqual(fetch.plan(rows), fetch.plan(list(reversed(rows))))
        rows[0]['contractInternalId'] = '../private'
        self.assertTrue(all('../' not in x['url'] for x in fetch.plan(rows)))


if __name__ == '__main__':
    unittest.main()
