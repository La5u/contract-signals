import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('tours', ROOT/'tools/import-tours-notices.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
RAW = json.loads((ROOT/'data/tours-notices/raw/api-records.json').read_text())

def record(rid): return next(r for r in RAW if r['idweb']==rid)
def root(rid): return mod.root_notice(record(rid))[1]

class ToursNoticeParsing(unittest.TestCase):
    def test_buyer_role_is_not_name_or_supplier(self):
        bs=mod.buyers(root('25-102354'))
        self.assertFalse(any(b['siret']==mod.SIRET for b in bs))
        self.assertEqual(bs[0]['siret'],'20008510800013')

    def test_joint_buyers_are_preserved(self):
        bs=mod.buyers(root('25-127301'))
        self.assertGreater(len(bs),1)
        self.assertIn(mod.SIRET,[b['siret'] for b in bs])
        self.assertIn('24370075400035',[b['siret'] for b in bs])

    def test_criteria_only_from_current_lot(self):
        lots=mod.array(root('25-11990')['cac:ProcurementProjectLot'])
        for lot in lots:
            lid=mod.value(lot,'cbc:ID')
            extracted=mod.award_criteria(lot,lid,'https://example.org')
            self.assertTrue(extracted)
            self.assertTrue(all(c['lotId']==lid for c in extracted))
        a=copy.deepcopy(lots[0]);a['cac:TenderingTerms'].pop('cac:AwardingTerms')
        a['cac:TenderingTerms']['efac:SelectionCriteria']={'cbc:Description':'Not an award criterion'}
        self.assertEqual(mod.award_criteria(a,'LOT-X','https://example.org'),[])

    def test_numeric_weights_and_unknowns_not_zero(self):
        lot=root('25-127301')['cac:ProcurementProjectLot']
        criteria=mod.award_criteria(lot,'LOT-0001','https://example.org')
        self.assertEqual([c['parameters'][0]['rawValue'] for c in criteria],['40','30','20','10'])
        self.assertTrue(all(c['parameters'][0]['code']=='per-exa' for c in criteria))
        self.assertIsNone(mod.finite(None));self.assertIsNone(mod.finite('NaN'));self.assertEqual(mod.finite('0'),0)

    def test_index_initial_can_be_structured_correction(self):
        self.assertEqual(record('25-127197')['etat'],'INITIAL')
        refs=mod.references(root('25-127197'))
        self.assertTrue(any(r['kind']=='correction-of' and r['id'].startswith('34156a89-') for r in refs))

    def test_acceleration_unknown_vs_false(self):
        self.assertIsNone(mod.procedure(root('25-4887'),'https://example.org')['accelerated'])
        self.assertIs(mod.procedure(root('25-1120'),'https://example.org')['accelerated'],False)

    def test_procedure_explanation_not_lot_direct_award(self):
        p=mod.procedure(root('25-4887'),'https://example.org')
        self.assertIn('R2122-8',p['description'])
        self.assertEqual(p['type'],'open')
        self.assertEqual(p['justifications'],[])

    def test_deadline_requires_timezone_and_valid_day(self):
        def d(day,time): return mod.deadline({'cac:TenderingProcess':{'cac:TenderSubmissionDeadlinePeriod':{'cbc:EndDate':day,'cbc:EndTime':time}}})
        self.assertIsNone(d('2025-02-28','12:00:00')['iso'])
        self.assertIsNone(d('2025-02-30','12:00:00Z')['iso'])
        self.assertIsNone(d('2025-02-28+01:00','12:00:00+02:00')['iso'])
        self.assertEqual(d('2025-02-28+01:00','12:00:00+01:00')['iso'],'2025-02-28T12:00:00+01:00')

if __name__=='__main__':unittest.main()
