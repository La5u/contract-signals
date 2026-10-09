import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dijon_reconcile', ROOT / 'tools/reconcile-dijon-conflict.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture():
    company = lambda ref, legal: {'efac:Company': {'cac:PartyIdentification': {'cbc:ID': ref}, 'cac:PartyLegalEntity': {'cbc:CompanyID': legal}}}
    tender = {'cbc:ID': 'TEN-1', 'efac:TenderLot': {'cbc:ID': 'LOT-0001'},
              'efac:TenderingParty': {'cbc:ID': 'TPA-1'},
              'cac:LegalMonetaryTotal': {'cbc:PayableAmount': {'@currencyID': 'EUR', '#text': '456516.27'}}}
    contract = {'cbc:ID': 'CON-1', 'efac:LotTender': {'cbc:ID': 'TEN-1'},
                'cbc:IssueDate': '2024-06-11+02:00', 'efac:ContractReference': {'cbc:ID': '2023vdao164201'}}
    result = {'efac:TenderLot': {'cbc:ID': 'LOT-0001'}, 'efac:LotTender': {'cbc:ID': 'TEN-1'},
              'efac:SettledContract': {'cbc:ID': 'CON-1'},
              'efac:ReceivedSubmissionsStatistics': [{'efbc:StatisticsCode': 'tenders', 'efbc:StatisticsNumeric': '4'}, {'efbc:StatisticsCode': 't-esubm', 'efbc:StatisticsNumeric': '8'}]}
    nr = {'efac:LotTender': [tender], 'efac:SettledContract': [contract], 'efac:LotResult': [result],
          'efac:TenderingParty': [{'cbc:ID': 'TPA-1', 'efac:Tenderer': {'cbc:ID': 'ORG-W'}}]}
    ext = {'efac:Organizations': {'efac:Organization': [company('ORG-B', m.BUYER), company('ORG-W', '0')]}, 'efac:NoticeResult': nr}
    notice = {'cbc:ID': 'uuid-test', 'cbc:VersionID': '01', 'cac:ProcurementProject': {'cbc:ID': m.PROCEDURE},
              'cac:ContractingParty': {'cac:Party': {'cac:PartyIdentification': {'cbc:ID': 'ORG-B'}}},
              'cac:ProcurementProjectLot': [{'cbc:ID': 'LOT-0001', 'cac:ProcurementProject': {'cbc:ID': '1'}}],
              'ext:UBLExtensions': {'ext:UBLExtension': {'ext:ExtensionContent': {'efext:EformsExtension': ext}}}}
    record = {'idweb': m.NOTICE, 'donnees': json.dumps({'EFORMS': {'ContractAwardNotice': notice}})}
    row = {'acheteur_id': m.BUYER, 'id': m.PROCEDURE, 'montant': 456516.27, 'datenotification': '2024-06-11',
           'offresrecues': '2', 'titulaire_id_1': '12345678901234', 'titulaire_typeidentifiant_1': 'SIRET'}
    return row, record, notice, ext, result


class DijonReconciliationTests(unittest.TestCase):
    def test_candidate_not_verified_and_offers_disagreement(self):
        row, record, *_ = fixture()
        findings = m.reconcile([row], record)
        c = findings['candidates'][0]
        self.assertEqual(c['candidateCount'], 1)
        self.assertEqual(c['status'], 'candidate_lot_match_not_verified')
        self.assertTrue(c['offersDisagree'])
        self.assertFalse(c['holderIdentityConfirmed'])
        self.assertNotIn('12345678901234', json.dumps(findings, default=str))
        self.assertEqual(findings['publicationAction'], 'none; grouped DECP row remains excluded')

    def test_amount_alone_insufficient(self):
        row, record, *_ = fixture()
        row['datenotification'] = '2024-06-27'
        self.assertEqual(m.reconcile([row], record)['candidates'][0]['candidateCount'], 0)
        row['acheteur_id'] = '999'
        with self.assertRaises(ValueError):
            m.reconcile([row], record)

    def test_exact_buyer_and_procedure_required(self):
        for field in ['buyer', 'procedure']:
            row, record, notice, ext, _ = fixture()
            if field == 'buyer':
                ext['efac:Organizations']['efac:Organization'][0]['efac:Company']['cac:PartyLegalEntity']['cbc:CompanyID'] = 'wrong'
            else:
                notice['cac:ProcurementProject']['cbc:ID'] = 'wrong'
            record['donnees'] = json.dumps({'EFORMS': {'ContractAwardNotice': notice}})
            with self.assertRaises(ValueError):
                m.reconcile([row], record)

    def test_duplicate_relationships_and_source_rows_not_resolved(self):
        row, record, notice, ext, _ = fixture()
        findings = m.reconcile([row, copy.deepcopy(row)], record)
        self.assertTrue(all(c['status'] == 'non_unique_source_to_lot_mapping' for c in findings['candidates']))
        ext['efac:NoticeResult']['efac:LotTender'] *= 2
        record['donnees'] = json.dumps({'EFORMS': {'ContractAwardNotice': notice}})
        with self.assertRaises(ValueError):
            m.reconcile([row], record)

    def test_conflicting_total_stats_unknown_and_electronic_not_total(self):
        _, _, _, _, result = fixture()
        self.assertEqual(m.offer_total(result), 4)
        result['efac:ReceivedSubmissionsStatistics'].append({'efbc:StatisticsCode': 'tenders', 'efbc:StatisticsNumeric': '5'})
        self.assertIsNone(m.offer_total(result))
        result['efac:ReceivedSubmissionsStatistics'] = [{'efbc:StatisticsCode': 't-esubm', 'efbc:StatisticsNumeric': '8'}]
        self.assertIsNone(m.offer_total(result))

    def test_pdf_corroboration_is_exact_result_and_version(self):
        row, record, *_ = fixture()
        findings = m.reconcile([row], record)
        doc = f'''Annonce n° {m.NOTICE}
Identifiant interne : {m.PROCEDURE}
Identifiant/version : uuid-test - 01
6.1 Résultat – Identifiants des lots : LOT-0001
Valeur du résultat : 456,516.27 Euro
Identifiant du marché : 2023vdao164201
Date de conclusion du marché : 11/06/2024
Type de soumissions reçues : Offres
Nombre d’offres ou de demandes de participation reçues : 4
'''
        checks = m.corroborate_pdf(doc, findings)['candidates'][0]['pdfCorroboration']
        self.assertTrue(all(checks[k] for k in ['amount', 'contractReference', 'conclusionDate', 'offers']))
        with self.assertRaises(ValueError):
            m.corroborate_pdf(doc.replace('uuid-test - 01', 'uuid-test - 02'), findings)
        with self.assertRaises(ValueError):
            m.corroborate_pdf(doc.replace('LOT-0001', 'LOT-0002'), findings)

    def test_numeric_zero_and_unknown_distinguished(self):
        self.assertEqual(m.amount('0'), 0)
        for value in [None, True, 'NaN', 'Infinity', '-1']:
            self.assertIsNone(m.amount(value))


if __name__ == '__main__':
    unittest.main()
