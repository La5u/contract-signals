import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('recheck', ROOT / 'tools/recheck-amount-gaps.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def colombia():
    return {'dataset': 'colombia', 'row': {'id': 'secop2-test-full', 'contractId': 'CO1.PCCNTR.full',
            'processId': 'process', 'currency': 'COP', 'amount': 0},
            'original_reconciled': {'source_values': []}, 'url': M.COLOMBIA}


class RecheckTests(unittest.TestCase):
    def test_exact_minimized_queries(self):
        from urllib.parse import parse_qs, urlsplit
        item = colombia()
        query = parse_qs(urlsplit(M.url_for('colombia', item['row'])).query)
        self.assertEqual(query['$where'], ["id_contrato = 'CO1.PCCNTR.full'"])
        self.assertEqual(query['$limit'], ['2'])
        self.assertEqual(query['$select'], ['id_contrato,proceso_de_compra,valor_del_contrato,estado_contrato'])
        query = parse_qs(urlsplit(M.url_for('boamp', {'noticeId': '25-123'})).query)
        self.assertEqual(query, {'where': ['idweb="25-123"'], 'limit': ['2']})

    def test_current_candidate_not_update_and_exact_process(self):
        payload = [{'id_contrato': 'CO1.PCCNTR.full', 'proceso_de_compra': 'process', 'valor_del_contrato': '123'}]
        result = M.compare(colombia(), payload)
        self.assertTrue(result['candidate_only'])
        self.assertEqual(result['status'], 'current_positive_candidate')
        payload[0]['proceso_de_compra'] = 'other'
        self.assertFalse(M.compare(colombia(), payload)['candidate_only'])
        self.assertFalse(M.compare(colombia(), payload * 2)['candidate_only'])

    def test_freeze_deterministic_order_and_normalized_exact_id(self):
        queue = []
        rows = {'boamp': [], 'colombia': []}
        class Helper:
            def reconcile(self, dataset, row):
                status = next(x['status'] for x in queue if x['id'] == row['id'])
                return {'status': status, 'conflicts': [], 'exact_match_count': 1}
            def json_source(self, path):
                return {'records': []}, 'hash'
        for dataset, status in M.SELECTIONS:
            for suffix in ('z', 'a'):
                rid = status + '-' + suffix
                queue.append({'dataset': dataset, 'status': status, 'id': rid})
                rows[dataset].append({'id': rid, 'noticeId': '25-123', 'contractId': 'full', 'processId': 'process'})
        with patch.object(M, 'boamp_identity', return_value={'result_id': 'RES', 'tender_ids': ['TEN']}):
            plan = M.freeze(json.dumps(queue[0]).encode() + b'\n' + b'\n'.join(json.dumps(x).encode() for x in queue[1:]), rows, Helper())
        self.assertEqual([x['row']['id'] for x in plan['entries']], [status + '-a' for _, status in M.SELECTIONS])
        self.assertEqual(len(plan['entries']), 3)

    def test_failures_stop_and_are_private(self):
        for code in (403, 429, 500, 302):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as tmp:
                calls = []
                def requester(url):
                    calls.append(url)
                    return code, b'error'
                summary = M.fetch_plan({'entries': [colombia()] * 3}, Path(tmp), requester, lambda _: None)
                self.assertEqual(len(calls), 1)
                self.assertEqual(summary['failed'], 1)
                self.assertEqual(summary['unattempted'], 2)
                for path in Path(tmp).iterdir():
                    self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                meta = json.loads((Path(tmp) / 'retrieval-0.json').read_text())
                self.assertEqual(meta['sha256'], M.sha(b'error'))
                self.assertEqual(meta['bytes'], 5)
                self.assertIn('retrieved_utc', meta)

    def test_cap_serial_delay_and_max_three(self):
        with tempfile.TemporaryDirectory() as tmp:
            delays = []
            payload = json.dumps([{'id_contrato': 'CO1.PCCNTR.full', 'proceso_de_compra': 'process', 'valor_del_contrato': '0'}]).encode()
            summary = M.fetch_plan({'entries': [colombia()] * 3}, Path(tmp), lambda _: (200, payload), delays.append)
            self.assertEqual(summary['completed'], 3)
            self.assertEqual(delays, [2, 2])
        with tempfile.TemporaryDirectory() as tmp:
            summary = M.fetch_plan({'entries': [colombia()] * 3}, Path(tmp), lambda _: (200, b'x' * M.MAX_BYTES), lambda _: None)
            self.assertEqual(summary['attempted'], 1)
            self.assertEqual(summary['failed'], 1)

    def test_boamp_original_winning_identity_and_payable_only(self):
        row = {'id': 'boamp-25-123-lot-0001', 'noticeId': '25-123', 'lotId': 'LOT-0001',
               'contractId': 'CON-1', 'amount': 0, 'currency': 'EUR'}
        result = {'efac:LotResult': {'cbc:ID': 'RES-1', 'cbc:TenderResultCode': 'selec-w',
                  'efac:TenderLot': {'cbc:ID': 'LOT-0001'}, 'efac:LotTender': {'cbc:ID': 'TEN-1'},
                  'efac:SettledContract': {'cbc:ID': 'CON-1'}},
                  'efac:LotTender': {'cbc:ID': 'TEN-1', 'cac:LegalMonetaryTotal': {
                      'cbc:PayableAmount': {'#text': '42', '@currencyID': 'EUR'}}}}
        record = {'idweb': '25-123', 'donnees': json.dumps({'EFORMS': {'ContractAwardNotice': {
                  'ext:UBLExtensions': {'ext:UBLExtension': {'ext:ExtensionContent': {
                      'efext:EformsExtension': {'efac:NoticeResult': result}}}}}}})}
        item = {'dataset': 'boamp', 'row': row, 'original_reconciled': {'source_values': []},
                'original_identity': M.boamp_identity(row, [record])}
        payload = {'total_count': 1, 'results': [record]}
        self.assertTrue(M.compare(item, payload)['candidate_only'])
        item['original_identity']['tender_ids'] = ['OTHER']
        self.assertFalse(M.compare(item, payload)['candidate_only'])
        self.assertIn('original_result_tender_identity_changed', M.compare(item, payload)['conflicts'])
        item['original_identity'] = M.boamp_identity(row, [record])
        result['efac:LotTender']['cac:LegalMonetaryTotal']['cbc:PayableAmount']['@currencyID'] = 'USD'
        notice = json.loads(record['donnees'])
        notice['EFORMS']['ContractAwardNotice']['ext:UBLExtensions']['ext:UBLExtension']['ext:ExtensionContent']['efext:EformsExtension']['efac:NoticeResult'] = result
        record['donnees'] = json.dumps(notice)
        self.assertFalse(M.compare(item, payload)['candidate_only'])

    def test_redirect_disabled(self):
        self.assertIsNone(M.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com'))


if __name__ == '__main__':
    unittest.main()
