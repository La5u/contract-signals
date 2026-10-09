"""Offline reconciliation: exact IDs, basis separation, privacy and immutable inputs."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('missing_amounts', ROOT / 'tools/review-missing-amounts.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ReviewTests(unittest.TestCase):
    def test_decision_basis_and_currency(self):
        row = {'amount': None, 'currency': None}
        contract = m.evidence('/contract/value', {'amount': 123, 'currency': 'GBP'}, 'contract')
        award = m.evidence('/award/value', {'amount': 123, 'currency': 'GBP'}, 'award_only')
        self.assertEqual(m.decide(row, 1, [contract], []), ('importer_lost_value', True))
        self.assertEqual(m.decide(row, 1, [award], []), ('raw_source_missing', False))
        self.assertEqual(m.decide(row, 2, [contract], []), ('ambiguous_mapping', False))
        self.assertEqual(m.decide(row, 1, [contract], ['conflict']), ('ambiguous_mapping', False))
        contract['currency'] = None
        self.assertEqual(m.decide(row, 1, [contract], []), ('source_positive_currency_unresolved', False))
        contract['numeric_amount'] = 0
        self.assertEqual(m.decide(row, 1, [contract], []), ('raw_source_zero', False))
        self.assertIsNone(m.numeric(True))
        self.assertIsNone(m.numeric('NaN'))

    def put(self, root, path, value):
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(value).encode()
        file.write_bytes(gzip.compress(payload) if path.endswith('.gz') else payload)
        return file

    def test_uk_multiple_contracts_and_exact_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = {'id': 'fts-123-1', 'noticeId': '123', 'awardId': 'award-1', 'procedureId': 'ocid', 'lotId': 'lot-1', 'amount': None}
            release = {'id': '123', 'ocid': 'ocid', 'awards': [{'id': 'award-1', 'relatedLots': ['lot-1'], 'value': {'amount': 99, 'currency': 'GBP'}}],
                       'contracts': [{'id': 'c1', 'awardID': 'award-1', 'value': {'amount': 100, 'currency': 'GBP'}}]}
            path = 'data/uk-fts/raw/notices/123.json.gz'
            file = self.put(root, path, {'releases': [release]})
            before = file.read_bytes()
            result = m.Review(root).reconcile('uk', row)
            self.assertTrue(result['recovery_candidate'])
            self.assertEqual(result['basis_conflicts'], ['contract_award_amount_or_currency_differs'])
            self.assertEqual(file.read_bytes(), before)
            release['contracts'].append({'id': 'c2', 'awardID': 'award-1'})
            self.put(root, path, {'releases': [release]})
            result = m.Review(root).reconcile('uk', row)
            self.assertEqual(result['status'], 'ambiguous_mapping')
            self.assertFalse(result['recovery_candidate'])
            release['id'] = 'other-notice'
            self.put(root, path, {'releases': [release]})
            self.assertEqual(m.Review(root).reconcile('uk', row)['exact_match_count'], 0)

    def test_ukraine_award_is_not_contract_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = {'id': 'prozorro-UA-test-abcdefgh', 'tenderID': 'UA-test', 'procedureId': 'internal',
                   'contractInternalId': 'abcdefgh999', 'contractId': 'signed-contract', 'awardId': 'award', 'amount': 50, 'currency': 'UAH'}
            tender = {'id': 'internal', 'tenderID': 'UA-test', 'contracts': [{'id': 'abcdefgh999', 'contractID': 'signed-contract', 'awardID': 'award'}],
                      'awards': [{'id': 'award', 'value': {'amount': 50, 'currency': 'UAH'}}]}
            self.put(root, 'data/prozorro/raw/records/UA-test.json.gz', {'data': tender})
            result = m.Review(root).reconcile('ukraine', row)
            self.assertTrue(result['award_fallback_observed'])
            self.assertEqual(result['status'], 'raw_source_missing')
            self.assertFalse(result['recovery_candidate'])

    def test_ted_plain_payable_without_currency_is_not_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / 'data/ted-czechia/raw/notices/123.xml.gz'
            file.parent.mkdir(parents=True)
            xml = b'''<Notice xmlns="urn:test"><NoticeResult>
              <LotResult><ID>RES-1</ID><TenderResultCode>selec-w</TenderResultCode><TenderLot><ID>LOT-1</ID></TenderLot><LotTender><ID>TEN-1</ID></LotTender></LotResult>
              <LotTender><ID>TEN-1</ID><LegalMonetaryTotal><PayableAmount>125</PayableAmount></LegalMonetaryTotal></LotTender>
              <TotalAmount currencyID="CZK">999</TotalAmount></NoticeResult></Notice>'''
            file.write_bytes(gzip.compress(xml))
            row = {'id': 'ted-123-lot-1', 'noticeId': '123', 'resultId': 'RES-1', 'lotId': 'LOT-1', 'contractId': None, 'amount': None}
            result = m.Review(root).reconcile('czechia', row)
            self.assertEqual(result['status'], 'source_positive_currency_unresolved')
            self.assertFalse(result['recovery_candidate'])
            self.assertEqual(result['source_values'][0]['basis'], 'notice_context_only')

    def test_colombia_exact_id_duplicate_and_no_person_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = {'buyers': [{'key': 'buyer', 'match': {'field': 'nit_entidad', 'value': 'buyer-id'}}], 'pages': [{'file': 'data/colombia-secop2/raw/page.json'}]}
            raw = {'nit_entidad': 'buyer-id', 'id_contrato': 'contract', 'proceso_de_compra': 'process', 'valor_del_contrato': '0',
                   'documento_proveedor': 'SECRET_PERSON_ID', 'proveedor_adjudicado': 'SECRET_NAME'}
            self.put(root, 'data/colombia-secop2/raw/manifest.json', manifest)
            self.put(root, 'data/colombia-secop2/raw/page.json', [raw])
            row = {'id': 'secop2-buyer-contract', 'contractId': 'contract', 'processId': 'process', 'amount': 0}
            result = m.Review(root).reconcile('colombia', row)
            self.assertEqual(result['status'], 'raw_source_zero')
            self.assertNotIn('SECRET', json.dumps(result))
            self.put(root, 'data/colombia-secop2/raw/page.json', [raw, raw])
            self.assertEqual(m.Review(root).reconcile('colombia', row)['status'], 'ambiguous_mapping')

    def boamp_fixture(self, root, node):
        result = {'efac:LotResult': {'cbc:ID': 'RES-1', 'cbc:TenderResultCode': 'selec-w',
                  'efac:TenderLot': {'cbc:ID': 'LOT-1'}, 'efac:LotTender': {'cbc:ID': 'TEN-1'},
                  'efac:SettledContract': {'cbc:ID': 'CON-1'}},
                  'efac:LotTender': {'cbc:ID': 'TEN-1', 'cac:LegalMonetaryTotal': {'cbc:PayableAmount': node}},
                  'cbc:TotalAmount': {'@currencyID': 'EUR', '#text': '999999'}}
        notice = {'EFORMS': {'ContractAwardNotice': {'ext:UBLExtensions': {'ext:UBLExtension':
                  {'ext:ExtensionContent': {'efext:EformsExtension': {'efac:NoticeResult': result}}}}}}}
        record = {'idweb': '25-test', 'donnees': json.dumps(notice), 'objet': 'SECRET_SUBJECT', 'nomacheteur': 'SECRET_NAME'}
        self.put(root, 'data/boamp-raw.json.gz', {'records': [record]})
        row = {'id': 'boamp-25-test-lot-1', 'noticeId': '25-test', 'lotId': 'LOT-1', 'contractId': 'CON-1', 'amount': None}
        return row, record, result, notice

    def test_boamp_exact_winner_and_ambiguities(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for node, status in [(None, 'raw_source_missing'), ({'@currencyID': 'EUR', '#text': '0'}, 'raw_source_zero'),
                                 ({'@currencyID': 'EUR', '#text': '-1'}, 'raw_source_negative'),
                                 ({'@currencyID': 'EUR', '#text': 'Infinity'}, 'raw_source_non_numeric'),
                                 ({'@currencyID': 'EUR', '#text': '1,25'}, 'raw_source_non_numeric'),
                                 ('125', 'source_positive_currency_unresolved'),
                                 ({'@currencyID': 'EUR', '#text': '125'}, 'importer_lost_value')]:
                row, record, result, notice = self.boamp_fixture(root, node)
                entry = m.Review(root).reconcile('boamp', row)
                self.assertEqual(entry['status'], status)
                self.assertEqual(entry['recovery_candidate'], status == 'importer_lost_value')
                self.assertNotIn('SECRET', json.dumps(entry))
            for mutation in ('duplicate_notice', 'duplicate_result', 'duplicate_tender', 'duplicate_amount', 'wrong_contract', 'non_winner', 'wrong_lot'):
                row, record, result, notice = self.boamp_fixture(root, {'@currencyID': 'EUR', '#text': '125'})
                if mutation == 'duplicate_result': result['efac:LotResult'] = [result['efac:LotResult']] * 2
                if mutation == 'duplicate_tender': result['efac:LotTender'] = [result['efac:LotTender']] * 2
                if mutation == 'duplicate_amount': result['efac:LotTender']['cac:LegalMonetaryTotal']['cbc:PayableAmount'] = ['125', '125']
                if mutation == 'wrong_contract': row['contractId'] = 'OTHER'
                if mutation == 'non_winner': result['efac:LotResult']['cbc:TenderResultCode'] = 'not-w'
                if mutation == 'wrong_lot': row['lotId'] = 'OTHER'
                record['donnees'] = json.dumps(notice)
                self.put(root, 'data/boamp-raw.json.gz', {'records': [record] * (2 if mutation == 'duplicate_notice' else 1)})
                entry = m.Review(root).reconcile('boamp', row)
                self.assertEqual(entry['status'], 'ambiguous_mapping', mutation)
                self.assertFalse(entry['recovery_candidate'])

    def test_decp_counterpart_sets_never_select_amount(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = {'id': 'decp-buyer-contract', 'buyerSiret': 'buyer', 'contractId': 'contract',
                   'amount': None, 'initialConflicts': ['amount']}
            for key, path in [('cities', 'data/decp-cities-raw.json'), ('decp', 'data/decp-history-raw.json.gz')]:
                for amounts in ([10, 20], [0, 'INX'], [10, 10], ['CDL', None]):
                    records = [{'acheteur_id': 'buyer', 'id': 'contract', 'montant': a, 'montantmodification': 1000,
                                'titulaire_id_1': 'SECRET_PERSON', 'objet': 'SECRET_SUBJECT'} for a in amounts]
                    records.append({'acheteur_id': 'OTHER', 'id': 'contract', 'montant': 777})
                    self.put(root, path, {'records': records})
                    entry = m.Review(root).reconcile(key, row)
                    self.assertEqual(entry['exact_match_count'], 2)
                    self.assertEqual(entry['status'], 'unresolved_initial_conflict' if amounts in ([10, 20], [0, 'INX']) else 'ambiguous_mapping')
                    self.assertFalse(entry['recovery_candidate'])
                    self.assertNotIn('SECRET', json.dumps(entry))

    def test_notice_scope_does_not_recover_linked_award(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for key, path, rid in [('tours', 'data/tours-notices/raw/api-records.json', 'tours-notice-25-test-LOT-1'),
                                  ('consultations', 'data/consultations-raw.json', 'boamp-consultation-25-test')]:
                records = [{'idweb': '25-test', 'amount': 999, 'objet': 'SECRET_SUBJECT'}, {'idweb': 'award', 'amount': 500}]
                self.put(root, path, records if key == 'tours' else {'records': records})
                entry = m.Review(root).reconcile(key, {'id': rid, 'noticeId': '25-test', 'lotId': 'LOT-1', 'amount': None})
                self.assertEqual(entry['status'], 'not_contract_amount_scope')
                self.assertEqual(entry['source_values'], [])
                self.assertFalse(entry['recovery_candidate'])
                self.assertNotIn('SECRET', json.dumps(entry))

    def test_real_inventory_complete_and_immutable(self):
        def hashes():
            return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (ROOT / 'data').rglob('*') if p.is_file()}
        before = hashes()
        report, queue = m.review(ROOT)
        self.assertEqual(hashes(), before)
        self.assertEqual(report['gap_rows_accounted_for'], 1098)  # DECP cohorts reconciled with buyer feeds (was 1537)
        self.assertEqual(len(queue), 1586)
        self.assertFalse(any(e['recovery_candidate'] for e in queue))
        self.assertEqual(sum(c['unreviewed_gap_rows'] for c in report['datasets'].values()), 0)
        self.assertEqual(report['datasets']['boamp']['statuses'], {'raw_source_missing': 751, 'raw_source_negative': 1, 'raw_source_zero': 102})
        self.assertEqual(report['datasets']['cities']['statuses'], {'all_sources_missing': 11, 'declared_zero': 28, 'placeholder_only': 2, 'sources_disagree_unresolved': 5})
        self.assertEqual(report['datasets']['decp']['statuses'], {'all_sources_missing': 27, 'declared_zero': 13, 'placeholder_only': 1})
        for path, digest in report['input_sha256'].items():
            self.assertEqual(digest, hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
        forbidden = {'buyer', 'supplier', 'buyerSiret', 'supplierIds', 'description', 'objet', 'subject', 'sourceRowVariants', 'initialAlternatives'}
        self.assertTrue(all(not forbidden.intersection(e) for e in queue))

    def test_repository_output_rejected(self):
        result = subprocess.run([sys.executable, str(ROOT / 'tools/review-missing-amounts.py'), '--review-dir', str(ROOT / 'data/private-review')], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'outside the repository', result.stderr)

    def test_private_queue_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'private'
            m.AUDIT.write_queue(directory, [{'id': 'procurement-id'}])
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            self.assertEqual((directory / 'review.jsonl').stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
