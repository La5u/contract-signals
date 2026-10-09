import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dijon_project', ROOT / 'tools/reconcile-dijon-project.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

SIRET = '12345678900011'


def simple(text, title='Relance du lot 12 : Sols'):
    return {'idweb': '25-1', 'donnees': json.dumps({'FNSimple': {'attribution': {'attributionMarche': text, 'natureMarche': {'intitule': title}}}})}


def entry(cid='P1', siret=SIRET, amount=100.0, matches=1, linked=True, in_project=True, decp=2, notice=2, ref='p101', lot='1'):
    return {'contractId': cid, 'holderSiret': siret, 'amount': amount, 'date': '2024-06-27', 'decpOffers': decp, 'joint': False,
            'inProject': in_project, 'matches': matches, 'holderLinked': linked, 'noticeId': '24-1', 'lotNumber': lot,
            'lotTitle': f'Lot n°{lot}', 'contractReference': ref, 'noticeOffers': notice, 'offersDisagree': decp != notice}


class DijonProjectTests(unittest.TestCase):
    def test_simple_attribution_parses_nbsp_amount_and_title_lot(self):
        text = "Nombre d'offres reçues : 6\nDate d'attribution : 25/03/25\nMarché n° : 2024vdpa660000\nTachin, 1 Rue X, 21110 Genlis\nMontant Ht  : 194\xa0000,00 Euros"
        [r] = m.simple_results(simple(text))
        self.assertEqual((r['amount'], r['date'], r['offers'], r['lotNumber']), (194000, '2025-03-25', 6, '12'))
        self.assertEqual(r['winners'], [{'name': 'Tachin', 'postcode': '21110'}])

    def test_simple_attribution_ambiguity_refused(self):
        text = "Nombre d'offres reçues : 6\nNombre d'offres reçues : 7\nDate d'attribution : 25/03/25\nMarché n° : x\nA, 1 Rue X, 21110 G\nMontant Ht : 1 Euros"
        with self.assertRaises(ValueError):
            m.simple_results(simple(text))

    def test_split_requires_every_row_linked(self):
        rows = [entry(), entry(siret='98765432100011', amount=200.0, ref='p102', lot='2', linked=False)]
        cur = m.curated(rows, [])
        self.assertEqual(cur['procedureSplits'], [])
        self.assertEqual(cur['unresolvedGroups'][0]['contractId'], 'P1')

    def test_split_of_linked_lots_keeps_both_offer_values(self):
        rows = [entry(decp=2, notice=4), entry(siret='98765432100011', amount=200.0, ref='p102', lot='2')]
        [split] = m.curated(rows, [])['procedureSplits']
        self.assertEqual([(l['decpOffers'], l['noticeOffers']) for l in split['lots']], [(2, 4), (2, 2)])

    def test_two_rows_on_one_notice_lot_unresolved(self):
        rows = [entry(), entry(siret='98765432100011', amount=200.0)]  # same contract reference
        self.assertEqual(m.curated(rows, [])['unresolvedGroups'][0]['reason'], 'two rows attached to one notice lot')

    def test_unmatched_project_row_is_not_split_as_distinct(self):
        rows = [entry(), entry(siret='98765432100011', amount=200.0, matches=0, linked=False)]
        self.assertEqual(len(m.curated(rows, [])['unresolvedGroups']), 1)

    def test_offer_conflict_only_on_disagreement_and_project_membership(self):
        cur = m.curated([entry(cid='A', decp=1, notice=2), entry(cid='B'), entry(cid='C', in_project=False, matches=0, linked=False)], [])
        self.assertEqual([c['contractId'] for c in cur['offerConflicts']], ['A'])
        self.assertEqual(cur['projects'][0]['contractIds'], ['A', 'B'])


class ImporterSplitTests(unittest.TestCase):
    spec = importlib.util.spec_from_file_location('decp_cities', ROOT / 'tools/import-decp-cities.py')
    imp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imp)

    def row(self, siret, amount):
        return {'acheteur_id': '21210231300013', 'id': 'P1', 'datenotification': '2024-06-27', 'montant': amount,
                'titulaire_id_1': siret, 'titulaire_typeidentifiant_1': 'SIRET', 'idmodification': 'CDL'}

    def test_stale_curation_stops_import(self):
        split = {'lots': [{'holderSiret': SIRET, 'amount': 100.0, 'date': '2024-06-27'}]}
        units = self.imp.split_units('b', 'P1', [self.row(SIRET, 100.0)], split)
        self.assertEqual(len(units), 1)
        for rows in ([self.row(SIRET, 101.0)], [self.row(SIRET, 100.0), self.row(SIRET, 100.0) | {'objet': 'x'}], []):
            with self.assertRaises(ValueError):
                self.imp.split_units('b', 'P1', rows, split)
        modified = self.row(SIRET, 100.0) | {'idmodification': '1'}
        with self.assertRaises(ValueError):
            self.imp.split_units('b', 'P1', [modified], split)


if __name__ == '__main__':
    unittest.main()
