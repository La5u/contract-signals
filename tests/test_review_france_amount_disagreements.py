import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('france_review', ROOT / 'tools/review-france-amount-disagreements.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def fixture():
    result = {'cbc:ID': 'RES-1', 'efac:LotTender': {'cbc:ID': 'TEN-1'},
              'efac:FrameworkAgreement': {'cbc:MaximumValueAmount': {'#text': '400', '@currencyID': 'EUR'}}}
    nr = {'cbc:TotalAmount': {'#text': '999999', '@currencyID': 'EUR'},
          'efac:LotResult': result,
          'efac:LotTender': {'cbc:ID': 'TEN-1', 'cbc:PayableAmount': {'#text': '100', '@currencyID': 'EUR'}},
          'efac:SettledContract': {'efac:ContractReference': {'cbc:ID': '2024ABC'},
                                  'efac:LotTender': {'cbc:ID': 'TEN-1'}}}
    ext = {'efac:NoticeResult': nr, 'efac:Organizations': {'efac:Organization': {
        'efac:Company': {'cac:PartyIdentification': {'cbc:ID': 'ORG-1'},
                        'cac:PartyLegalEntity': {'cbc:CompanyID': '21750001600019'}}}}}
    n = {'cbc:VersionID': '01', 'cac:ContractingParty': {'cac:Party': {
        'cac:PartyIdentification': {'cbc:ID': 'ORG-1'}}},
         'ext:UBLExtensions': {'ext:UBLExtension': {'ext:ExtensionContent': {'efext:EformsExtension': ext}}}}
    return {'idweb': '24-1', 'donnees': json.dumps({'EFORMS': {'ContractAwardNotice': n}})}, nr


class ReviewTest(unittest.TestCase):
    def test_numbers_reject_invalid_and_preserve_zero(self):
        for v in (None, True, 'NaN', 'Infinity', '-1', '1 000,00'):
            self.assertIsNone(review.number(v))
        self.assertEqual(review.number(0), '0')

    def test_scoped_semantics_not_procedure_total(self):
        record, _ = fixture()
        lots = review.notice_lots(record)
        self.assertEqual(len(lots), 1)
        self.assertEqual(lots[0]['buyers'], {'21750001600019'})
        self.assertEqual(lots[0]['reference'], '2024ABC')
        self.assertEqual({v['basis'] for v in lots[0]['values']}, {'maximum', 'tender_value_period_unknown'})
        self.assertNotIn('999999', [v['value'] for v in lots[0]['values']])
        self.assertTrue(all(v['pointer'].startswith('/NoticeResult/') for v in lots[0]['values']))

    def test_ambiguous_result_fails_closed(self):
        record, nr = fixture()
        n = json.loads(record['donnees'])
        target = n['EFORMS']['ContractAwardNotice']['ext:UBLExtensions']['ext:UBLExtension']['ext:ExtensionContent']['efext:EformsExtension']['efac:NoticeResult']
        target['efac:LotResult'] = [nr['efac:LotResult'], nr['efac:LotResult']]
        record['donnees'] = json.dumps(n)
        self.assertEqual(review.notice_lots(record), [])

    def test_reference_not_substring_join(self):
        record, _ = fixture()
        lot = review.notice_lots(record)[0]
        index = {(b, lot['reference']): lot for b in lot['buyers']}
        self.assertNotIn(('21750001600019', '2024AB'), index)
        self.assertNotIn(('wrong-buyer', '2024ABC'), index)

    def test_ratio_and_printed_match_never_resolve(self):
        row = {'id': 'x', 'buyerSiret': 'b', 'contractId': 'c', 'amount': 100,
               'durationMonths': 48, 'amountSources': [{'amount': 100}, {'amount': 400}]}
        record, _ = fixture()
        result = review.reconcile(row, [], review.notice_lots(record))
        self.assertEqual(result['max_min_ratio'], '4')
        self.assertTrue(result['over_2x'])
        self.assertFalse(result['resolved'])
        self.assertIn('annual_or_full_term_not_established', result['unknowns'])
        self.assertNotIn('replacement', result)

    def test_zero_does_not_generate_ratio(self):
        row = {'id': 'x', 'buyerSiret': 'b', 'contractId': 'c', 'amountSources': [{'amount': 0}, {'amount': 10}]}
        self.assertIsNone(review.reconcile(row, [], [])['max_min_ratio'])

    def test_missing_or_legacy_notice_not_invented(self):
        for record in ({}, {'donnees': '{}'}, {'donnees': 'not json'}):
            self.assertEqual(review.notice_lots(record), [])

    def test_current_offline_build_is_repeatable_and_read_only(self):
        paths = [ROOT / p for p in review.DATASETS]
        before = [review.digest(p.read_bytes()) for p in paths]
        queue, summary, provenance = review.build()
        again, summary_again, provenance_again = review.build()
        self.assertEqual((queue, summary, provenance), (again, summary_again, provenance_again))
        self.assertEqual(before, [review.digest(p.read_bytes()) for p in paths])
        self.assertEqual(summary['reviewed'], len(queue))
        self.assertEqual(summary['network_requests'], 0)
        self.assertTrue(all(not q['resolved'] for q in queue))
        self.assertTrue(all(not n['eligible_for_resolution'] for q in queue
                            for n in q['search_candidate_notice_evidence']))
        self.assertTrue(all(p['sha256'] for p in provenance))

    def test_basis_estimate_is_not_maximum(self):
        fields = review.money({'cbc:EstimatedOverallContractAmount': {'#text': '100', '@currencyID': 'EUR'},
                               'cbc:MaximumValueAmount': {'#text': '400', '@currencyID': 'EUR'}})
        self.assertEqual([f['basis'] for f in fields], ['estimate', 'maximum'])


if __name__ == '__main__':
    unittest.main()
