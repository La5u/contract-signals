import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('related', ROOT / 'tools' / 'ukraine-related-parties.py')
rp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp)

ROW = {'id': 'r', 'awardId': 'a1', 'supplierIds': [{'id': '11111111', 'identifierType': 'EDRPOU'}], 'tenderCreated': '2021-03-01'}


def bid(code, name='ТОВ', status='active'):
    return {'id': 'b' + code, 'status': status, 'tenderers': [{'identifier': {'id': code}, 'name': name}]}


def tender(bids, contact='Петренко Іван Іванович'):
    return {'bids': bids, 'awards': [{'id': 'a1', 'bid_id': bids[0]['id'] if bids else None, 'status': 'active', 'suppliers': [{'name': 'ТОВ'}]}],
            'procuringEntity': {'contactPoint': {'name': contact}}}


def entry(people=(), codes=(), registered='2015-01-01'):
    return {'registered': [registered], 'states': ['зареєстровано'], 'people': sorted(people), 'founderCodes': sorted(codes)}


class Names(unittest.TestCase):
    def test_register_forms(self):
        self.assertEqual(rp.person('БОРОДАЙ ЮРІЙ ВІКТОРОВИЧ; розмір частки - 100,00 грн.'), 'БОРОДАЙ ЮРІЙ ВІКТОРОВИЧ')
        self.assertEqual(rp.person('ЯКОВЕЦЬ ГАЛИНА ІВАНІВНА - керівник'), 'ЯКОВЕЦЬ ГАЛИНА ІВАНІВНА')
        self.assertEqual(rp.person('Дорошенко Іван Миколайович; громадянство: Україна'), 'ДОРОШЕНКО ІВАН МИКОЛАЙОВИЧ')
        self.assertEqual(rp.person("Мар’яненко Ольга Петрівна"), rp.person("МАР'ЯНЕНКО ОЛЬГА ПЕТРІВНА"))

    def test_not_a_full_name(self):
        self.assertIsNone(rp.person('НУР АХМАД; розмір частки - 1000,00 грн.'))   # two parts
        self.assertIsNone(rp.person('Петренко І.І.'))
        self.assertIsNone(rp.person('причина відсутності: Відсутні фізичні особи'))
        self.assertIsNone(rp.person('Відділ закупівель'))

    def test_latin_lookalikes(self):
        self.assertEqual(rp.person('IВАНОВ ОЛЕГ ПЕТРОВИЧ'), 'ІВАНОВ ОЛЕГ ПЕТРОВИЧ')


class Rules(unittest.TestCase):
    def test_r1_shared_founder(self):
        reg = {'11111111': entry(['ІВАНОВ ОЛЕГ ПЕТРОВИЧ']), '22222222': entry(['ІВАНОВ ОЛЕГ ПЕТРОВИЧ'])}
        self.assertTrue(rp.features(ROW, tender([bid('11111111'), bid('22222222')]), reg)['R1 shared-owner'])

    def test_r1_one_founds_the_other(self):
        reg = {'11111111': entry(codes=['22222222']), '22222222': entry()}
        self.assertTrue(rp.features(ROW, tender([bid('11111111'), bid('22222222')]), reg)['R1 shared-owner'])

    def test_r1_individual_entrepreneur_is_the_person(self):
        reg = {'11111111': entry(['ІВАНОВ ОЛЕГ ПЕТРОВИЧ'])}
        t = tender([bid('11111111'), bid('1234567890', name='ФОП Іванов Олег Петрович')])
        self.assertIsNone(rp.features(ROW, t, reg)['R1 shared-owner'])   # 'ФОП …' is not a bare full name
        t = tender([bid('11111111'), bid('1234567890', name='Іванов Олег Петрович')])
        self.assertTrue(rp.features(ROW, t, reg)['R1 shared-owner'])

    def test_r1_unknown_vs_clear(self):
        reg = {'11111111': entry(['ІВАНОВ ОЛЕГ ПЕТРОВИЧ']), '22222222': entry(['ПЕТРОВ ПЕТРО ПЕТРОВИЧ'])}
        self.assertFalse(rp.features(ROW, tender([bid('11111111'), bid('22222222')]), reg)['R1 shared-owner'])
        self.assertIsNone(rp.features(ROW, tender([bid('11111111'), bid('33333333')]), reg)['R1 shared-owner'])
        self.assertFalse(rp.features(ROW, tender([bid('11111111')]), {})['R1 shared-owner'])   # one bidder: clear

    def test_r2_contact_owns_winner(self):
        reg = {'11111111': entry(['ПЕТРЕНКО ІВАН ІВАНОВИЧ'])}
        self.assertTrue(rp.features(ROW, tender([bid('11111111')]), reg)['R2 official-owner'])
        self.assertFalse(rp.features(ROW, tender([bid('11111111')], contact='Сидоренко Ганна Петрівна'), reg)['R2 official-owner'])
        self.assertIsNone(rp.features(ROW, tender([bid('11111111')], contact='Відділ закупівель'), reg)['R2 official-owner'])
        self.assertIsNone(rp.features(ROW, tender([bid('11111111')]), {})['R2 official-owner'])

    def test_r3_young_winner(self):
        self.assertTrue(rp.features(ROW, tender([bid('11111111')]), {'11111111': entry(registered='2020-06-01')})['R3 young-winner'])
        self.assertFalse(rp.features(ROW, tender([bid('11111111')]), {'11111111': entry(registered='2019-06-01')})['R3 young-winner'])
        self.assertIsNone(rp.features(ROW, tender([bid('11111111')]), {})['R3 young-winner'])
        two = entry(registered='2020-06-01'); two['registered'].append('2010-01-01')
        self.assertIsNone(rp.features(ROW, tender([bid('11111111')]), {'11111111': two})['R3 young-winner'])


if __name__ == '__main__':
    unittest.main()
