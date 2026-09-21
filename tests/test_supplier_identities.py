import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('supplier_enrichment', Path(__file__).parents[1] / 'tools/enrich-city-suppliers.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SupplierIdentities(unittest.TestCase):
    def clean(self, results):
        return mod.clean_result('123456789', mod.query_url('123456789'), {'results':results}, '2026-09-15T00:00:00Z')

    def test_exact_identifier_required(self):
        p=self.clean([{'siren':'987654321','statut_diffusion':'O','nom_complet':'Similar name'}])
        self.assertEqual(p['status'],'unavailable')
        self.assertIsNone(p['name'])

    def test_missing_or_restricted_diffusion(self):
        for diffusion in [None,'P','N']:
            p=self.clean([{'siren':'123456789','statut_diffusion':diffusion,'nom_complet':'Do not retain'}])
            self.assertIsNone(p['name'])
            self.assertIsNone(p['administrativeState'])

    def test_minimal_public_snapshot_only(self):
        p=self.clean([{'siren':'123456789','statut_diffusion':'O','nom_complet':'PUBLIC NAME','etat_administratif':'A','adresse':'private detail','dirigeants':[{'nom':'private detail'}]}])
        self.assertEqual(p['name'],'PUBLIC NAME')
        self.assertNotIn('adresse',p)
        self.assertNotIn('dirigeants',p)

    def test_ambiguous_results_excluded(self):
        r={'siren':'123456789','statut_diffusion':'O','nom_complet':'NAME'}
        self.assertEqual(self.clean([r,{**r,'nom_complet':'OTHER'}])['status'],'unavailable')

    def test_selection_ignores_score_and_names(self):
        rows=[{'supplierIds':[{'identifierType':'SIRET','id':f'{i:09d}00011'}],'score':i,'supplier':str(i)} for i in range(120)]
        original=mod.selection(rows)[1]
        self.assertEqual(original,mod.selection([{**r,'score':1000,'supplier':'same'} for r in reversed(rows)])[1])
        self.assertEqual(len(original),100)
        self.assertEqual(mod.suppliers([{'supplierIds':[{'identifierType':'foreign','id':'12345678900011'}]}]),{})

if __name__=='__main__':
    unittest.main()
