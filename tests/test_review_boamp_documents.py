import importlib.util
from pathlib import Path
import unittest
from decimal import Decimal

spec = importlib.util.spec_from_file_location('review_docs', Path(__file__).resolve().parents[1] / 'tools/review-boamp-documents.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class DocumentReviewTests(unittest.TestCase):
    def section(self, lot='LOT-0001', value='138,555', statistic='Offres'):
        return f'''6.1 Résultat – Identifiants des lots : {lot}
Valeur du résultat : {value} Euro
Identifiant du marché : Ref 1
Date de conclusion du marché : 09/09/2024
6.1.4 Informations statistiques
Type de soumissions reçues : {statistic}
Nombre d’offres ou de demandes de participation reçues : 1
'''

    def test_exact_lot_not_other_lot_or_notice_total(self):
        doc = 'Valeur de tous les contrats : 999,999 Euro\n' + self.section() + self.section('LOT-0002', '90')
        result = m.inspect(doc, 'LOT-0001')
        self.assertEqual(result['payable'], Decimal('138555'))
        self.assertEqual(result['conclusion_date'], '2024-09-09')
        self.assertEqual(result['total_offers'], 1)
        self.assertEqual(result['tax_basis'], 'unresolved')

    def test_zero_not_missing(self):
        self.assertEqual(m.inspect(self.section(value='0'), 'LOT-0001')['payable'], Decimal(0))
        doc = self.section().replace('Valeur du résultat : 138,555 Euro\n', '')
        self.assertIsNone(m.inspect(doc, 'LOT-0001')['payable'])

    def test_framework_ceiling_not_substitution(self):
        doc = self.section().replace('Valeur du résultat : 138,555 Euro', 'Valeur maximale de l’accord-cadre : 1,000,000 Euro')
        result = m.inspect(doc, 'LOT-0001')
        self.assertIsNone(result['payable'])
        self.assertEqual(result['framework_ceiling'], Decimal('1000000'))

    def test_electronic_submissions_not_total_offers(self):
        result = m.inspect(self.section(statistic='Offres présentées par voie électronique'), 'LOT-0001')
        self.assertIsNone(result['total_offers'])

    def test_missing_duplicate_lot_and_fields_refused(self):
        for doc in [self.section('LOT-0002'), self.section() + self.section(), self.section() + 'Valeur du résultat : 1 Euro\n']:
            with self.assertRaises(ValueError):
                m.inspect(doc, 'LOT-0001')

    def test_invalid_dates_and_number_conventions_refused(self):
        with self.assertRaises(ValueError):
            m.inspect(self.section().replace('09/09/2024', '30/02/2024'), 'LOT-0001')
        for value in ['1,25', '-1', 'Infinity', '1.000,00']:
            with self.assertRaises(ValueError):
                m.euro_number(value)
        self.assertEqual(m.euro_number('199,342.3'), Decimal('199342.3'))


if __name__ == '__main__':
    unittest.main()
