import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
spec = importlib.util.spec_from_file_location('decp_feeds', ROOT / 'tools/decp_feeds.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

B, H, H2 = '21750001600019', '12345678900011', '98765432100011'


def feed(cid='C1', amount=100.0, holder=H, date='2024-05-01', source='atexo_maximilien', mod=0, uid=None, objet='Objet'):
    return {'uid': uid or f'{B}{cid}_45000000', 'id': cid, 'acheteur_id': B, 'titulaire_id': holder, 'titulaire_typeIdentifiant': 'SIRET' if holder else None,
            'objet': objet, 'montant': amount, 'codeCPV': '45000000', 'procedure': 'Appel d\'offres ouvert', 'dureeMois': 12, 'offresRecues': 3,
            'dateNotification': date, 'datePublicationDonnees': '2024-06-01', 'formePrix': 'Forfaitaire', 'typesPrix': 'Définitif ferme',
            'nature': 'Marché', 'modalitesExecution': None, 'techniques': None, 'idAccordCadre': None, 'modification_id': mod,
            'sourceDataset': source, 'montant_anomalie': None}


def record(cid='C1', amount=100.0, holder=H, date='2024-05-01', **extra):
    return {'id': f'decp-{B}-{cid}', 'buyerSiret': B, 'contractId': cid, 'amount': amount, 'date': date, 'description': 'Objet',
            'supplierIds': [{'id': holder, 'identifierType': 'SIRET'}], 'history': [{'kind': 'initial', 'amount': amount}],
            'initialConflicts': [], 'initialAlternatives': [], **extra}


def build(contract, in_use):
    r = m.feed_fields(contract, {}, lambda p: False)
    r.update({'id': m.new_id(B, contract['initial']['id'], in_use), 'buyerSiret': B})
    return r


class DecideRule(unittest.TestCase):
    def test_feed_first_positive_over_zero_and_placeholders(self):
        self.assertEqual(m.decide([10.0], [600000.0]), 600000.0)        # placeholder replaced
        self.assertEqual(m.decide([39900.0], [0.0]), 39900.0)           # zero never hides money
        self.assertEqual(m.decide([3300000.0], [13200000.0]), 13200000.0)
        self.assertEqual(m.decide([5.0], []), None)                     # placeholder alone is unknown
        self.assertEqual(m.decide([0.0], []), 0.0)                      # declared zero stays
        self.assertEqual(m.decide([200.0], [100.0, 200.0]), 200.0)      # several feed values: Ministry arbitrates
        self.assertIsNone(m.decide([300.0], [100.0, 200.0]))
        self.assertIsNone(m.decide([100.0, 200.0], []))                 # unresolved Ministry pair


class Matching(unittest.TestCase):
    def test_match_paths(self):
        idx = m.Index([record('C1'), record('C2', amount=50.0, holder=H2)])
        self.assertEqual(idx.match(feed('C1', amount=999.0))[1], 'id-date-holder')
        self.assertEqual(idx.match(feed('LONGC2', amount=50.0, holder=H2))[1], 'holder-amount-date')
        self.assertEqual(idx.match(feed('X', amount=7.0, holder=H2, objet='objet'))[1], 'holder-date-object')
        self.assertEqual(idx.match(feed('Y', amount=50.0, holder=None))[1], 'amount-date-no-holder')
        self.assertEqual(idx.match(feed('C1', holder='11111111100011'))[1], 'co-holder')          # Ministry table dropped a holder
        self.assertEqual(idx.match(feed('C1', holder='11111111100011', objet='Autre'))[1], 'same-id-other-holder')
        self.assertEqual(idx.match(feed('C1', amount=1.0, holder='11111111100011', objet='Autre'))[1], 'absent')  # another contract, reused id
        self.assertEqual(idx.match(feed('Z', amount=1.0, holder='11111111100011'))[1], 'absent')

    def test_two_candidates_are_ambiguous(self):
        idx = m.Index([record('C1'), {**record('C1'), 'id': 'other'}])
        self.assertEqual(idx.match(feed('C1', amount=5.0)), (None, 'ambiguous'))


class Reconcile(unittest.TestCase):
    def test_pair_resolved_only_by_a_matching_feed_value(self):
        pair = record(amount=None, initialConflicts=['amount'], initialAlternatives=[{'amount': 65029.0}, {'amount': 200000.0}])
        m.reconcile_record(pair, [feed(amount=200000.0)])
        self.assertEqual((pair['amount'], pair['initialConflicts']), (200000.0, []))
        self.assertTrue(pair['verification']['resolvedPair'])
        other = record(amount=None, initialConflicts=['amount'], initialAlternatives=[{'amount': 1.5e5}, {'amount': 2e5}])
        m.reconcile_record(other, [feed(amount=3e5)])
        self.assertIsNone(other['amount'])
        self.assertEqual(other['initialConflicts'], ['amount'])

    def test_statuses_and_sources_kept(self):
        agree, differ, alone = record(), record(), record()
        m.reconcile_record(agree, [feed()])
        m.reconcile_record(differ, [feed(amount=400.0)])
        m.reconcile_record(alone, [])
        self.assertEqual([r['verification']['status'] for r in (agree, differ, alone)], ['sources-agree', 'sources-disagree', 'single-source'])
        self.assertEqual(differ['amount'], 400.0)
        self.assertEqual(differ['verification']['amountRange'], [100.0, 400.0])
        self.assertEqual([s['amount'] for s in differ['amountSources']], [100.0, 400.0])

    def test_placeholder_becomes_unknown(self):
        r = record(amount=10.0)
        m.reconcile_record(r, [])
        self.assertIsNone(r['amount'])
        self.assertTrue(r['verification']['placeholder'])


class Apply(unittest.TestCase):
    def test_missing_contract_added_once_and_linked_to_shared_id(self):
        data = {'records': [feed('C1'), feed('C1', amount=777.0, holder=H2, date='2025-02-01', uid='u2'),
                            feed('C1', amount=777.0, holder=H2, date='2025-02-01', uid='u3', source=m.SCRAPED),
                            feed('C1', amount=800.0, holder=H2, date='2025-02-01', uid='u2', mod=1)]}
        rows = [record('C1')]
        added, stats = m.apply(rows, data, {B}, build, 'cohort')
        self.assertEqual(len(added), 1)
        self.assertEqual(stats['feed.duplicateAcrossSources'], 1)
        new = added[0]
        self.assertEqual((new['amount'], new['verification']['addedFromFeed'], new['feedSource']), (777.0, True, 'atexo_maximilien'))
        self.assertEqual([e['amount'] for e in new['history']], [777.0, 800.0])
        ids = {rows[0]['id'], new['id']}
        self.assertEqual(set(rows[0]['procedureGroup']['members']), ids)
        self.assertEqual(set(new['procedureGroup']['members']), ids)


class Majority(unittest.TestCase):
    def test_routes_not_copies_are_counted(self):
        src = lambda source, amount: {'source': source, 'amount': amount}
        # Ministry + portal against the AWS profile and its scraped copy (one route): 2 routes to 1.
        self.assertEqual(m.majority([src('ministry', 27659.11), src('portal_bordeaux', 27659.11), src('aws_marches-publics.info', 670000.0),
                                     src(m.SCRAPED, 670000.0)])[0], 27659.11)
        self.assertIsNone(m.majority([src('ministry', 1.0e5), src('atexo_maximilien', 2.0e5)]))       # a tie decides nothing
        self.assertIsNone(m.majority([src('ministry', 5.0), src('portal_nantes', 5.0), src('atexo_nantes_metro', 900.0)]))  # placeholders never vote

    def test_majority_overrides_feed_first(self):
        r = record(amount=27659.11)
        m.reconcile_record(r, [{**feed(amount=670000.0), 'sourceDataset': 'aws_marches-publics.info'}, {**feed(amount=27659.11), 'sourceDataset': 'portal_bordeaux'}])
        self.assertEqual(r['amount'], 27659.11)
        self.assertEqual(r['verification']['majority'], {'amount': 27659.11, 'routes': 2, 'of': 3})


class PortalPhase(unittest.TestCase):
    def test_portal_row_confirms_a_feed_only_contract_instead_of_duplicating_it(self):
        data = {'records': [feed('NEW', amount=500.0, holder=H2, date='2025-03-01'),
                            {**feed('PORTAL-REF', amount=500.0, holder=H2, date='2025-03-01', objet='Autre libellé'), 'sourceDataset': 'portal_nantes', 'uid': 'p1'}]}
        added, stats = m.apply([record('C1')], data, {B}, build, 'cohort')
        self.assertEqual(len(added), 1)
        self.assertEqual(stats['portal.holder-amount-date'], 1)
        self.assertEqual(added[0]['verification']['status'], 'sources-agree')
        self.assertEqual(sorted(s['source'] for s in added[0]['amountSources']), ['atexo_maximilien', 'portal_nantes'])


if __name__ == '__main__':
    unittest.main()
