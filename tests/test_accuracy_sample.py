import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('accuracy_sample', ROOT / 'tools/accuracy-sample.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def notice(lots):
    """Minimal eForms award notice: lots = [(reference, date, siret, name, amount)]."""
    orgs, tenders, parties, contracts, results = [], [], [], [], []
    for n, (ref, date, siret, name, amount) in enumerate(lots):
        orgs.append({'efac:Company': {'cac:PartyIdentification': {'cbc:ID': f'ORG-{n}'}, 'cac:PartyLegalEntity': {'cbc:CompanyID': siret},
                                      'cac:PartyName': {'cbc:Name': name}}})
        parties.append({'cbc:ID': f'TPA-{n}', 'efac:Tenderer': {'cbc:ID': f'ORG-{n}'}})
        tender = {'cbc:ID': f'TEN-{n}', 'efac:TenderingParty': {'cbc:ID': f'TPA-{n}'}}
        if amount is not None:
            tender['cac:LegalMonetaryTotal'] = {'cbc:PayableAmount': {'@currencyID': 'EUR', '#text': str(amount)}}
        tenders.append(tender)
        contracts.append({'cbc:ID': f'CON-{n}', 'efac:LotTender': {'cbc:ID': f'TEN-{n}'}, 'cbc:IssueDate': date + '+02:00',
                          'efac:ContractReference': {'cbc:ID': ref}})
        results.append({'efac:LotTender': {'cbc:ID': f'TEN-{n}'}})
    ext = {'efac:Organizations': {'efac:Organization': orgs},
           'efac:NoticeResult': {'efac:LotTender': tenders, 'efac:TenderingParty': parties, 'efac:SettledContract': contracts, 'efac:LotResult': results}}
    donnees = {'EFORMS': {'ContractAwardNotice': {'ext:UBLExtensions': {'ext:UBLExtension': {'ext:ExtensionContent': {'efext:EformsExtension': ext}}}}}}
    return {'results': [{'idweb': '24-1', 'donnees': json.dumps(donnees)}]}


def row(cid='2024S05075', amount=200000.0, siret='12345678900011', date='2024-07-10', **extra):
    return {'contractId': cid, 'amount': amount, 'date': date, 'supplierIds': [{'id': siret}], 'amountSources': [], **extra}


class EvaluateTests(unittest.TestCase):
    def test_reference_link_confirms_only_the_linked_lot(self):
        r = m.evaluate(row(), notice([('20242024S05075', '2024-07-10', '0', 'A', 200000), ('20242024S05079', '2024-07-10', '0', 'B', 150000)]))
        self.assertEqual((r['outcome'], r['noticeAmounts']), ('confirmed', [200000.0]))

    def test_identifier_in_several_references_needs_the_holder(self):
        lots = [('2023vdao164201', '2024-06-27', '0', 'A', 1), ('2023vdao164207', '2024-06-27', '0', 'B', 2)]
        self.assertEqual(m.evaluate(row('2023VDAO1642', 2.0, date='2024-06-27'), notice(lots))['outcome'], 'no-notice')
        r = m.evaluate(row('2023VDAO1642', 2.0, date='2024-06-27', procedureGroup={'contractReference': '2023vdao164207'}), notice(lots))
        self.assertEqual(r['outcome'], 'confirmed')

    def test_register_name_link_requires_same_date_and_amount_is_not_a_link_key(self):
        lots = [('X', '2024-07-10', '0', 'SARL EXEMPLE', 300000)]
        named = row(cid='Q1', supplierProfiles=[{'name': 'EXEMPLE'}])
        self.assertEqual(m.evaluate(named, notice(lots))['outcome'], 'contradicted')
        self.assertEqual(m.evaluate({**named, 'date': '2024-07-11'}, notice(lots))['outcome'], 'no-notice')
        self.assertEqual(m.evaluate(row(cid='Q1'), notice([('X', '2024-07-10', '0', 'Other', 200000)]))['outcome'], 'no-notice')

    def test_notice_without_amount_and_other_source_flag(self):
        self.assertEqual(m.evaluate(row(), notice([('20242024S05075', '2024-07-10', '0', 'A', None)]))['outcome'], 'notice-without-amount')
        r = m.evaluate(row(amount=5e6, amountSources=[{'amount': 1e7}, {'amount': 5e6}]), notice([('2024S05075', '2024-07-10', '0', 'A', 1e7)]))
        self.assertEqual((r['outcome'], r['otherSourceMatchesNotice']), ('contradicted', True))

    def test_sample_is_seeded_and_stratified(self):
        rows = [{'id': f'r{i}', 'date': '2024-01-01', 'verification': {'status': 'sources-agree' if i % 2 else 'single-source'}} for i in range(100)]
        a, b = m.sample(rows), m.sample(rows)
        self.assertEqual(a, b)
        self.assertEqual({k: len(v) for k, v in a.items()}, {'notice-checked': 0, 'sources-agree': 30, 'sources-disagree': 0, 'single-source': 30})


if __name__ == '__main__':
    unittest.main()
