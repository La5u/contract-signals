"""Offline synthetic failure cases plus a full saved-snapshot regression."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('audit_uk', ROOT / 'tools/audit-uk-contract-values.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ContractValuesTest(unittest.TestCase):
    def setUp(self):
        self.award = {'id': 'award-1', 'status': 'active', 'suppliers': [{'id': 's'}],
                      'relatedLots': ['lot'], 'date': '2025-01-02',
                      'value': {'amount': 200, 'currency': 'GBP'}}
        self.release = {'id': 'notice', 'ocid': 'procedure', 'date': '2025-01-01',
                        'parties': [{'id': 'b', 'roles': ['buyer']}],
                        'contracts': [{'id': 'c1', 'awardID': 'award-1',
                                       'dateSigned': '2025-01-03',
                                       'value': {'amount': 100, 'currency': 'GBP'}}]}
        self.row = {'id': 'fts-notice-1', 'noticeId': 'notice', 'awardId': 'award-1',
                    'procedureId': 'procedure', 'buyerId': 'b', 'lotId': 'lot',
                    'supplierIds': [{'id': 's', 'identifierType': 'GB-FTS'}],
                    'amount': 100, 'currency': 'GBP', 'date': '2025-01-03',
                    'publicationDate': '2025-01-01', 'amountBasis': 'Contract value'}

    def inspect(self):
        return audit.inspect_row(self.row, self.release, self.award)

    def test_contract_vs_award_difference_is_not_automatic_wrong_mapping(self):
        d = self.inspect()
        self.assertFalse(d['gateExcluded'])
        self.assertTrue(d['importerRuleValueMatches'])
        self.assertIn('contract_award_amount_difference', d['flags'])

    def test_multiple_contracts_last_matches_but_is_excluded(self):
        first = copy.deepcopy(self.release['contracts'][0])
        first.update(id='c0', dateSigned='2025-01-04', value={'amount': 50, 'currency': 'EUR'})
        self.release['contracts'].insert(0, first)
        d = self.inspect()
        self.assertEqual(len(d['linkedContracts']), 2)
        self.assertTrue(d['importerRuleValueMatches'])
        self.assertTrue(d['importerRuleDateMatches'])
        self.assertTrue(d['gateExcluded'])
        self.assertIn('multiple_contract_values_conflict', d['flags'])
        self.assertIn('multiple_contract_dates_conflict', d['flags'])

    def test_identical_multiple_contracts_still_excluded(self):
        self.release['contracts'].append(copy.deepcopy(self.release['contracts'][0]))
        self.assertTrue(self.inspect()['gateExcluded'])

    def test_award_fallback_is_label_conflict(self):
        self.release['contracts'][0].pop('value')
        self.row['amount'] = 200
        d = self.inspect()
        self.assertEqual(d['amountSource'], 'award')
        self.assertIn('award_value_labelled_contract_basis', d['flags'])

    def test_no_contract_uses_award_and_award_date(self):
        self.release['contracts'] = []
        self.row.update(amount=200, date='2025-01-02')
        d = self.inspect()
        self.assertEqual(d['linkedContractCount'], 0)
        self.assertEqual(d['dateSource'], 'award')
        self.assertTrue(d['importerRuleDateMatches'])

    def test_truthy_partial_value_blocks_award_not_fieldwise_fallback(self):
        self.release['contracts'][0]['value'] = {'currency': 'GBP'}
        self.row['amount'] = None
        d = self.inspect()
        self.assertTrue(d['importerRuleValueMatches'])
        self.assertIn('partial_contract_value_blocks_award_amount', d['flags'])
        self.assertIn('selected_currency_without_amount', d['flags'])

    def test_empty_value_falls_back_but_zero_does_not(self):
        self.release['contracts'][0]['value'] = {}
        self.assertEqual(self.inspect()['amountSource'], 'award')
        self.release['contracts'][0]['value'] = {'amount': 0, 'currency': 'GBP'}
        self.row['amount'] = 0
        d = self.inspect()
        self.assertEqual(d['amountSource'], 'contract')
        self.assertIn('selected_zero', d['flags'])

    def test_currency_conflict_and_wrong_published_value(self):
        self.award['value']['currency'] = 'EUR'
        self.row['currency'] = 'USD'
        d = self.inspect()
        self.assertIn('contract_award_currency_conflict', d['flags'])
        self.assertIn('published_value_differs_from_importer_rule', d['flags'])

    def test_identity_checks_do_not_use_names(self):
        for field in ('buyerId', 'procedureId', 'lotId', 'id'):
            original = self.row[field]
            self.row[field] = 'wrong'
            self.assertTrue(self.inspect()['gateExcluded'])
            self.row[field] = original
        self.row['supplierIds'][0]['id'] = 'wrong'
        self.assertTrue(self.inspect()['gateExcluded'])

    def test_missing_value_and_release_date_are_not_recovered(self):
        self.award.pop('value')
        self.award.pop('date')
        self.release['contracts'][0].pop('value')
        self.release['contracts'][0].pop('dateSigned')
        self.row.update(amount=None, currency=None, date='2025-01-01')
        d = self.inspect()
        self.assertEqual(d['amountSource'], 'missing')
        self.assertEqual(d['dateSource'], 'release')
        self.assertIn('selected_missing_amount', d['flags'])

    def test_full_snapshot(self):
        summary, rows, links = audit.audit(ROOT)
        self.assertEqual(summary['counts']['published_rows'], 1081)
        self.assertEqual(summary['counts']['raw_awards'], 1233)
        self.assertEqual(len(links), 1086)
        self.assertEqual(len(rows), 1081)
        self.assertEqual(summary['published_by_linked_contract_count'], {1: 1081})
        self.assertEqual(summary['gate_excluded_rows'], 0)
        self.assertEqual(summary['importer_rule_value_matches'], 1081)
        self.assertEqual(summary['importer_rule_date_matches'], 1081)
        self.assertEqual(summary['flags'], {'selected_missing_amount': 9})
        self.assertEqual(summary['published_awards_with_value_object'], 0)


if __name__ == '__main__':
    unittest.main()
