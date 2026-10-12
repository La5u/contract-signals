"""Bounded, offline tests for public-document benchmark preparation."""
import copy
import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('public_document_benchmark', ROOT / 'tools/prepare-public-document-benchmark.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'repo'
        (self.root / 'data').mkdir(parents=True)
        self.b = {'id': 'boamp-one', 'dataFamily': 'boamp', 'buyerSiret': '21750001600019',
                  'noticeId': '25-1', 'lotId': 'LOT-0001', 'contractReference': '2025A'}
        self.d = {'id': 'decp-one', 'dataFamily': 'decp', 'buyerSiret': '21750001600019',
                  'contractId': '2025A'}
        self.link = {'boampId': self.b['id'], 'decpId': self.d['id'], 'status': 'confirmed',
                     'basis': ['buyer-published-contract-reference'], 'warnings': []}
        self.save()

    def save(self, links=None, boamp=None, history=None, cities=None):
        values = ({'schemaVersion': 1, 'links': links if links is not None else [self.link]},
                  boamp if boamp is not None else [self.b],
                  history if history is not None else [self.d], cities or [])
        for name, value in zip(M.INPUTS, values):
            (self.root / name).write_text(json.dumps(value))

    def plan(self):
        return M.build_plan(self.root)

    def test_current_public_snapshot_all_nine_blocked_no_network_or_cache(self):
        original_read = Path.read_bytes
        reads = []
        allowed = {(ROOT / name).resolve() for name in M.INPUTS} | {Path(M.__file__).resolve()}
        def public_only(path):
            self.assertIn(path.resolve(), allowed)
            reads.append(path.resolve())
            return original_read(path)
        with patch.object(Path, 'read_bytes', public_only), patch.object(
                socket, 'socket', side_effect=AssertionError('network forbidden')):
            plan = M.build_plan()
        self.assertEqual(set(reads), allowed)
        self.assertEqual(plan['counts'], {'investigationPairs': 9, 'blockedPairs': 9,
                                         'eligiblePairs': 0, 'factualAgreementDenominator': 0})
        self.assertEqual(len(plan['investigationQueue']), 9)
        self.assertEqual(plan['noticeLinkedAgreementQueue'], [])
        for row in plan['investigationCohort']:
            self.assertEqual(row['status'], 'blocked')
            self.assertIn('unconfirmed-link', row['blockedReasons'])
        self.assertEqual(sum('multiple-match' in r['blockedReasons']
                             for r in plan['investigationCohort']), 4)
        self.assertEqual(sum('different-cpv' in r['warnings']
                             for r in plan['investigationCohort']), 4)
        M.verify_hash(plan)

    def test_public_freeze_copy_reproduces_current_preparation(self):
        published = json.loads((ROOT / 'data/public-document-benchmark-plan.json').read_text())
        M.verify_hash(published)
        self.assertEqual(published, M.build_plan())
        self.assertEqual(published['counts']['factualAgreementDenominator'], 0)

    def test_exact_confirmed_admitted_but_not_measured(self):
        plan = self.plan()
        self.assertEqual(plan['counts']['eligiblePairs'], 1)
        self.assertEqual(plan['counts']['factualAgreementDenominator'], 0)
        self.assertEqual(plan['investigationCohort'][0]['status'], 'eligible-not-reviewed')
        self.assertEqual(len(plan['noticeLinkedAgreementQueue']), 1)

    def test_fail_closed_gates(self):
        mutations = [({'status': 'candidate'}, 'unconfirmed-link'),
                     ({'basis': ['buyer-holder-siret-same-date']}, 'no-exact-identifier-basis'),
                     ({'warnings': ['multiple-decp-matches']}, 'multiple-match'),
                     ({'warnings': ['multiple-boamp-matches']}, 'multiple-match'),
                     ({'warnings': ['unconfirmed-no-exact-reference']}, 'unconfirmed-reference-warning')]
        for mutation, reason in mutations:
            with self.subTest(mutation=mutation):
                link = dict(self.link, **mutation)
                self.save(links=[link])
                plan = self.plan()
                self.assertIn(reason, plan['investigationCohort'][0]['blockedReasons'])
                self.assertEqual(plan['noticeLinkedAgreementQueue'], [])

    def test_multiple_matches_detected_without_warning(self):
        second = dict(self.d, id='decp-two')
        link = dict(self.link, decpId=second['id'])
        self.save(links=[self.link, link], history=[self.d, second])
        self.assertTrue(all('multiple-match' in r['blockedReasons']
                            for r in self.plan()['investigationCohort']))

    def test_identity_and_nonunique_rows(self):
        for row in (dict(self.d, buyerSiret='00000000000000'),
                    dict(self.d, contractId='different')):
            self.save(history=[row])
            self.assertEqual(self.plan()['noticeLinkedAgreementQueue'], [])
        for history, cities in (([], []), ([self.d], [self.d])):
            self.save(history=history, cities=cities)
            self.assertIn('missing-or-nonunique-public-row',
                          self.plan()['investigationCohort'][0]['blockedReasons'])

    def test_local_contract_id_not_exact_reference(self):
        self.save(boamp=[dict(self.b, contractReference='CON-0001')],
                  history=[dict(self.d, contractId='CON-0001')])
        self.assertEqual(self.plan()['noticeLinkedAgreementQueue'], [])

    def test_exact_notice_lot_supported(self):
        link = dict(self.link, basis=['buyer-exact-notice-lot'])
        self.save(links=[link], history=[dict(self.d, noticeId='25-1', lotId='LOT-0001')])
        self.assertEqual(self.plan()['counts']['eligiblePairs'], 1)
        self.save(links=[link], history=[dict(self.d, noticeId='25-2', lotId='LOT-0001')])
        self.assertEqual(self.plan()['counts']['eligiblePairs'], 0)

    def test_deterministic_hash_snapshot_binding_and_minimization(self):
        self.b.update(supplierName='DO NOT COPY', amount=123456, description='PRIVATE PROSE')
        self.save()
        first = self.plan()
        self.assertEqual(first, self.plan())
        payload = M.canonical(first).decode()
        for value in ('DO NOT COPY', '123456', 'PRIVATE PROSE'):
            self.assertNotIn(value, payload)
        self.assertEqual(first['investigationQueue'][0]['selectionRankSha256'],
                         M.digest(M.canonical([M.VERSION, M.VERSION, self.b['id'], self.d['id']])))
        path = self.root / M.INPUTS[1]
        path.write_bytes(path.read_bytes() + b'\n')
        second = self.plan()
        self.assertNotEqual(first['planSha256'], second['planSha256'])
        self.assertEqual(first['investigationQueue'], second['investigationQueue'])
        self.assertEqual(first['investigationCohort'], second['investigationCohort'])

    def test_pair_order_independent_selection(self):
        b2 = dict(self.b, id='boamp-two', contractReference='2025B')
        d2 = dict(self.d, id='decp-two', contractId='2025B')
        l2 = dict(self.link, boampId=b2['id'], decpId=d2['id'])
        self.save(links=[self.link, l2], boamp=[self.b, b2], history=[self.d, d2])
        first = self.plan()
        self.save(links=[l2, self.link], boamp=[b2, self.b], history=[d2, self.d])
        second = self.plan()
        self.assertEqual(first['investigationQueue'], second['investigationQueue'])
        self.assertEqual(first['noticeLinkedAgreementQueue'], second['noticeLinkedAgreementQueue'])
        self.assertNotEqual(first['planSha256'], second['planSha256'])

    def test_duplicate_pairs_and_json_keys_rejected(self):
        self.save(links=[self.link, self.link])
        with self.assertRaises(ValueError):
            self.plan()
        with self.assertRaises(ValueError):
            M.load_json(b'{"x":1,"x":2}')

    def test_private_exclusive_freeze_and_tamper_detection(self):
        plan = self.plan()
        target = self.base / 'private' / 'plan.json'
        self.assertTrue(M.freeze(plan, target, self.root))
        self.assertEqual(target.stat().st_mode & 0o777, 0o400)
        self.assertEqual(target.parent.stat().st_mode & 0o777, 0o700)
        before = target.stat().st_mtime_ns
        self.assertFalse(M.freeze(plan, target, self.root))
        self.assertEqual(before, target.stat().st_mtime_ns)
        other = M.build_plan(self.root, seed='new-seed')
        with self.assertRaises(ValueError):
            M.freeze(other, target, self.root)
        invalid = copy.deepcopy(plan)
        invalid['counts']['eligiblePairs'] = 99
        with self.assertRaises(ValueError):
            M.freeze(invalid, self.base / 'invalid.json', self.root)
        target.chmod(0o600)
        target.write_text(json.dumps(invalid))
        target.chmod(0o400)
        with self.assertRaises(ValueError):
            M.freeze(plan, target, self.root)

    def test_unsafe_destinations_rejected(self):
        plan = self.plan()
        with self.assertRaises(ValueError):
            M.freeze(plan, self.root / 'plan.json', self.root)
        public = self.base / 'public'
        public.mkdir(mode=0o755)
        with self.assertRaises(ValueError):
            M.freeze(plan, public / 'plan.json', self.root)
        link = self.base / 'symlink'
        link.symlink_to(public, target_is_directory=True)
        with self.assertRaises(ValueError):
            M.freeze(plan, link / 'plan.json', self.root)


if __name__ == '__main__':
    unittest.main()
