import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('link', ROOT / 'tools/link-ukraine-verdict-tenders.py')
link = importlib.util.module_from_spec(spec)
spec.loader.exec_module(link)

REVIEW = {'outcome': 'conviction', 'role': 'scheme', 'via_prozorro': 'yes', 'buyer_code': '04054903', 'supplier_code': '41234567',
          'contract_number': '№ 0143', 'contract_date': '2021-01-15', 'procurement_year': '2021', 'amount_uah': 100000, 'cpv': '09310000-5'}
TENDER = {'contracts': [{'status': 'active', 'contractNumber': '143', 'dateSigned': '2021-01-18T10:00:00+02:00',
                         'value': {'amount': 100500}, 'suppliers': [{'identifier': {'id': '41234567'}}]}],
          'awards': [{'status': 'active', 'value': {'amount': 100500}, 'suppliers': [{'identifier': {'id': '41234567'}}]}]}


class Eligible(unittest.TestCase):
    def test_label_candidate(self):
        self.assertIsNone(link.eligible(REVIEW))

    def test_context_or_acquittal_is_not_searched(self):
        self.assertEqual(link.eligible({**REVIEW, 'role': 'context'}), 'not a label')
        self.assertEqual(link.eligible({**REVIEW, 'outcome': 'acquittal'}), 'not a label')
        self.assertEqual(link.eligible({**REVIEW, 'via_prozorro': 'no'}), 'not a label')

    def test_needs_buyer_code_and_year(self):
        self.assertEqual(link.eligible({**REVIEW, 'buyer_code': None}), 'no buyer code or name')
        self.assertEqual(link.eligible({**REVIEW, 'buyer_code': '1234567890'}), 'no buyer code or name')
        self.assertIsNone(link.eligible({**REVIEW, 'buyer_code': None, 'buyer_name': 'Баштанська міська рада'}))
        self.assertEqual(link.eligible({**REVIEW, 'procurement_year': '2014', 'contract_date': None}), 'no year or before 2016')


class Evidence(unittest.TestCase):
    def test_all_four(self):
        self.assertEqual(link.evidence(REVIEW, TENDER), {'S', 'N', 'D', 'A'})

    def test_amount_tolerance_and_date_window(self):
        r = {**REVIEW, 'amount_uah': 98000, 'contract_date': '2021-02-01'}
        self.assertEqual(link.evidence(r, TENDER), {'S', 'N'})

    def test_supplier_by_name(self):
        r = {**REVIEW, 'supplier_code': None, 'supplier_name': 'ТОВ «Альфа-Буд»', 'contract_number': None, 'contract_date': None}
        t = {'contracts': [{**TENDER['contracts'][0], 'suppliers': [{'identifier': {'id': '1', 'legalName': 'ТОВ "АЛЬФА БУД"'}}]}], 'awards': []}
        self.assertEqual(link.evidence(r, t), {'S', 'A'})

    def test_match_rule(self):
        self.assertTrue(link.is_match({'S', 'A'}))
        self.assertTrue(link.is_match({'N', 'D'}))
        self.assertFalse(link.is_match({'S'}))
        self.assertFalse(link.is_match({'D', 'A'}))

    def test_cancelled_contract_ignored(self):
        t = {'contracts': [{**TENDER['contracts'][0], 'status': 'cancelled'}], 'awards': []}
        self.assertEqual(link.evidence(REVIEW, t), set())


class Shortlist(unittest.TestCase):
    def test_value_band_and_cpv_first(self):
        listed = [{'tenderID': 'far', 'value': {'amount': 300000, 'currency': 'UAH'}, 'title': 'x'},
                  {'tenderID': 'near', 'value': {'amount': 110000, 'currency': 'UAH'}, 'title': 'x'},
                  {'tenderID': 'cpv', 'value': {'amount': 900000, 'currency': 'UAH'}, 'title': 'ДК 021:2015 - 09310000-5 Електрична енергія'}]
        self.assertEqual(link.shortlist(REVIEW, listed), ['cpv', 'near'])

    def test_date_when_no_amount_or_cpv(self):
        r = {**REVIEW, 'amount_uah': None, 'cpv': None}
        listed = [{'tenderID': 'in', 'value': {}, 'tenderPeriod': {'endDate': '2020-12-20T00:00:00+02:00'}},
                  {'tenderID': 'late', 'value': {}, 'tenderPeriod': {'endDate': '2021-03-20T00:00:00+02:00'}}]
        self.assertEqual(link.shortlist(r, listed), ['in'])


DESC = {'doc_id': '1', 'n': 1, 'buyer_code': '04054903', 'bidder_codes': ['41234567', '3123456789', '123'], 'year': 2019,
        'date': '2019-05-10', 'cpv': None, 'expected_value_uah': None, 'via_prozorro': 'yes', 'collusion_found': 'yes'}


class PartB(unittest.TestCase):
    def test_eligible(self):
        self.assertIsNone(link.amcu_eligible(DESC))
        self.assertEqual(link.amcu_eligible({**DESC, 'collusion_found': 'no'}), 'not a label')
        self.assertEqual(link.amcu_eligible({**DESC, 'via_prozorro': 'no'}), 'not a label')
        self.assertEqual(link.amcu_eligible({**DESC, 'bidder_codes': ['41234567']}), 'fewer than 2 bidder codes')
        self.assertEqual(link.amcu_eligible({**DESC, 'year': 2015}), 'no year or before 2016')

    def test_bidders_from_bids_and_awards(self):
        t = {'bids': [{'tenderers': [{'identifier': {'id': '41234567'}}]}, {'tenderers': [{'identifier': {'id': '99999999'}}]}],
             'awards': [{'suppliers': [{'identifier': {'id': '3123456789'}}]}]}
        self.assertEqual(link.tender_bidders(t), {'41234567', '99999999', '3123456789'})
        self.assertEqual(set(link.bidder_codes(DESC)) & link.tender_bidders(t), {'41234567', '3123456789'})

    def test_shortlist_without_value_or_cpv(self):
        listed = [{'tenderID': 'far', 'kind': 'competitive', 'tenderPeriod': {'endDate': '2019-11-01T00:00:00+02:00'}},
                  {'tenderID': 'near', 'kind': 'competitive', 'tenderPeriod': {'endDate': '2019-05-01T00:00:00+02:00'}},
                  {'tenderID': 'direct', 'kind': 'reporting'}]
        self.assertEqual(link.amcu_shortlist(DESC, listed), ['near', 'far'])

    def test_shortlist_by_expected_value(self):
        listed = [{'tenderID': 'v', 'kind': 'competitive', 'value': {'amount': 105000, 'currency': 'UAH'}},
                  {'tenderID': 'x', 'kind': 'competitive', 'value': {'amount': 500000, 'currency': 'UAH'}}]
        self.assertEqual(link.amcu_shortlist({**DESC, 'expected_value_uah': 100000}, listed), ['v'])


if __name__ == '__main__':
    unittest.main()
