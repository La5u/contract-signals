import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dijon_holders', ROOT / 'tools/link-dijon-holders.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

SIRET = '12345678900011'


def register(siret=SIRET, siren='123456789', name='SARL EXEMPLE', postcode='21000', extra=()):
    est = {'siret': siret, 'code_postal': postcode, 'etat_administratif': 'A', 'liste_enseignes': None}
    return {'results': [{'siren': siren, 'nom_complet': name, 'matching_etablissements': [est, *extra]}]}


def candidate(index=0, lot='LOT-0001'):
    return {'ministryRowIndex': index, 'candidateCount': 1, 'technicalLotId': lot, 'printedLotNumber': '1'}


WINNERS = {'LOT-0001': [{'name': 'EXEMPLE', 'postcode': '21000'}]}


class HolderLinkageTests(unittest.TestCase):
    def test_exact_siret_name_and_postcode_link(self):
        e = m.link([candidate()], [SIRET], WINNERS, {SIRET: register()})[0]
        self.assertTrue(e['holderLinked'])

    def test_postcode_or_name_disagreement_blocks_link(self):
        for reg in [register(postcode='75001'), register(name='AUTRE SOCIETE')]:
            self.assertFalse(m.link([candidate()], [SIRET], WINNERS, {SIRET: reg})[0]['holderLinked'])

    def test_legal_form_tokens_alone_never_match(self):
        winners = {'LOT-0001': [{'name': 'SARL', 'postcode': '21000'}]}
        self.assertFalse(m.link([candidate()], [SIRET], winners, {SIRET: register()})[0]['holderLinked'])

    def test_siren_inconsistent_or_absent_establishment(self):
        self.assertFalse(m.link([candidate()], [SIRET], WINNERS, {SIRET: register(siren='999999999')})[0]['holderLinked'])
        self.assertFalse(m.link([candidate()], [SIRET], WINNERS, {SIRET: register(siret='12345678900099')})[0]['holderLinked'])
        self.assertFalse(m.link([candidate()], [SIRET], WINNERS, {})[0]['holderLinked'])

    def test_duplicate_register_establishment_is_ambiguous(self):
        dup = {'siret': SIRET, 'code_postal': '21000'}
        self.assertIsNone(m.register_entry(register(extra=[dup]), SIRET))

    def test_one_winner_cannot_absorb_two_rows(self):
        other = '98765432100011'
        responses = {SIRET: register(), other: register(siret=other, siren='987654321')}
        out = m.link([candidate(0), candidate(1)], [SIRET, other], WINNERS, responses)
        self.assertFalse(any(e['holderLinked'] for e in out))

    def test_rows_without_exactly_one_siret_are_unlinkable(self):
        rows = [{'titulaire_id_1': SIRET, 'titulaire_typeidentifiant_1': 'SIRET',
                 'titulaire_id_2': '98765432100011', 'titulaire_typeidentifiant_2': 'SIRET'},
                {'titulaire_id_1': 'CDL', 'titulaire_typeidentifiant_1': 'CDL'}]
        self.assertEqual(m.holder_sirets(rows), [None, None])

    def test_unmatched_candidate_or_multiple_winners_not_linked(self):
        c = candidate()
        c['candidateCount'] = 0
        self.assertFalse(m.link([c], [SIRET], WINNERS, {SIRET: register()})[0]['holderLinked'])
        two = {'LOT-0001': WINNERS['LOT-0001'] * 2}
        self.assertFalse(m.link([candidate()], [SIRET], two, {SIRET: register()})[0]['holderLinked'])

    def test_fetch_refuses_repository_output_and_overcap(self):
        with self.assertRaises(ValueError):
            m.fetch(ROOT / 'data/registry-test', [SIRET])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                m.fetch(Path(tmp) / 'r', [str(10 ** 13 + i) for i in range(7)])

    def test_output_omits_identifiers(self):
        out = m.link([candidate()], [SIRET], WINNERS, {SIRET: register()})
        self.assertNotIn(SIRET, json.dumps(out))
        self.assertNotIn('EXEMPLE', json.dumps(out))


if __name__ == '__main__':
    unittest.main()
