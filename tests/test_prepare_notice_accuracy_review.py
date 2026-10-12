"""Synthetic eligibility assertions test mechanics, not legal or factual truth."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('notice_review', Path(__file__).resolve().parents[1] / 'tools/prepare-notice-accuracy-review.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class NoticeReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'repo'
        self.root.mkdir()
        (self.root / 'data').mkdir()
        self.evidence = self.base / 'evidence'
        self.evidence.mkdir(mode=0o700)
        (self.evidence / 'proof.txt').write_bytes(b'SYNTHETIC PROOF - not legislation')
        (self.evidence / 'proof.txt').chmod(0o600)
        self.ref = {'path': 'proof.txt', 'sha256': m.digest((self.evidence / 'proof.txt').read_bytes()),
                    'url': 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014L0024',
                    'locator': 'synthetic article locator'}
        self.row = {'id': 'a', 'buyerSiret': '21210231300013', 'contractId': '2024TEST',
                    'procedure': m.OPEN, 'amount': 1, 'date': '2025-01-01',
                    'verification': {'status': 'sources-agree'}}
        self.entry = self.entry_for(self.row)
        self.write_rows([self.row])

    def entry_for(self, row):
        values = dict(m.FIXED, buyerCategory='subcentral', contractType='ordinary-services',
                      procurementStartDate='2023-12-31', estimatedValue='215000.01',
                      thresholdRule={'celex': '32021R1952', 'amountEUR': '215000',
                                     'primaryTextReviewed': True, 'applicabilityReviewed': True,
                                     'dateType': 'call-dispatch-or-procurement-commencement'},
                      identityLink={'buyerSiret': row['buyerSiret'], 'contractId': row['contractId'],
                                    'procedureId': 'exact-procedure', 'documentVersion': 'v1'})
        return {'dataset': m.DATASETS[0], 'rowId': row['id'], 'rowSha256': m.row_hash(row),
                'reviewedBy': 'synthetic reviewer', 'reviewedOn': '2026-10-10',
                'facts': {key: {'value': value, 'evidence': [copy.deepcopy(self.ref)]}
                          for key, value in values.items()}}

    def write_rows(self, rows):
        for i, dataset in enumerate(m.DATASETS):
            (self.root / dataset).write_text(json.dumps(rows if i == 0 else []))

    def write_manifest(self, entries=None):
        path = self.base / 'manifest.json'
        path.write_text(json.dumps({'schemaVersion': m.VERSION,
                                    'records': entries if entries is not None else [self.entry]}))
        path.chmod(0o600)
        return path

    def assess(self, entry=None, row=None):
        return m.eligibility(row or self.row, entry if entry is not None else self.entry,
                             self.evidence, self.root)

    def test_no_amount_inference_or_award_date_substitution(self):
        for amount in (None, 0, 999999999):
            row = dict(self.row, amount=amount)
            self.assertEqual(m.eligibility(row, None, None, self.root)[0], 'unknown')
        self.assertEqual(self.assess()[0], 'eligible')  # independently evidenced estimate, not amount=1
        self.entry['facts']['procurementStartDate']['value'] = '2026-01-01'
        self.assertEqual(self.assess()[0], 'unknown')

    def test_missing_every_required_fact_stays_unknown(self):
        for key in m.REQUIRED:
            with self.subTest(key=key):
                entry = copy.deepcopy(self.entry)
                del entry['facts'][key]
                self.assertEqual(self.assess(entry)[0], 'unknown')

    def test_empty_evidence_is_unknown(self):
        self.entry['facts']['noticeDuty']['evidence'] = []
        self.assertEqual(self.assess()[0], 'unknown')

    def test_exact_open_procedure_only(self):
        for procedure, expected in [(None, 'unknown'), ('Procédure adaptée', 'ineligible'),
                                    ('Open', 'ineligible'), ('Appel d’offres ouvert', 'ineligible')]:
            self.assertEqual(m.eligibility(dict(self.row, procedure=procedure), None, None, self.root)[0], expected)

    def test_unknown_type_buyer_and_identity(self):
        for key, value in [('buyerCategory', 'unknown'), ('contractType', 'social-services'),
                           ('identityLink', {'buyerSiret': 'wrong'})]:
            entry = copy.deepcopy(self.entry)
            entry['facts'][key]['value'] = value
            self.assertEqual(self.assess(entry)[0], 'unknown')

    def test_unsupported_scope_never_eligible(self):
        for key, value in [('regime', 'utilities'), ('awardKind', 'framework-call-off'),
                           ('lotTreatment', 'small-lot-exception'), ('exclusions', 'unknown'),
                           ('currency', 'USD'), ('valuationBasis', 'winning-tender-payable')]:
            entry = copy.deepcopy(self.entry)
            entry['facts'][key]['value'] = value
            self.assertEqual(self.assess(entry)[0], 'ineligible')

    def test_all_date_type_thresholds_and_strict_boundary(self):
        for year, (works, central, subcentral, celex) in m.THRESHOLDS.items():
            for category in ('central', 'subcentral'):
                for kind in ('works', 'supplies', 'ordinary-services'):
                    threshold = works if kind == 'works' else central if category == 'central' else subcentral
                    entry = copy.deepcopy(self.entry)
                    facts = entry['facts']
                    for key, value in [('buyerCategory', category), ('contractType', kind),
                                       ('procurementStartDate', f'{year}-01-01')]:
                        facts[key]['value'] = value
                    facts['thresholdRule']['value'].update(celex=celex, amountEUR=str(threshold))
                    for estimate, expected in [(str(threshold - 1), 'ineligible'),
                                               (str(threshold), 'ineligible'),
                                               (str(threshold + 1), 'eligible')]:
                        facts['estimatedValue']['value'] = estimate
                        self.assertEqual(self.assess(entry)[0], expected)

    def test_unreviewed_or_wrong_primary_rule_is_unknown(self):
        for key, value in [('primaryTextReviewed', False), ('amountEUR', '221000'),
                           ('dateType', 'award-date')]:
            entry = copy.deepcopy(self.entry)
            entry['facts']['thresholdRule']['value'][key] = value
            self.assertEqual(self.assess(entry)[0], 'unknown')
        self.entry['facts']['noticeDuty']['evidence'][0]['url'] = 'https://www.boamp.fr/example'
        self.assertEqual(self.assess()[0], 'unknown')

    def test_invalid_estimates_dates_stale_rows_fail(self):
        for estimate in (True, 1, 'NaN', 'Infinity', '-1', 'no'):
            entry = copy.deepcopy(self.entry)
            entry['facts']['estimatedValue']['value'] = estimate
            with self.assertRaises(ValueError):
                self.assess(entry)
        self.entry['rowSha256'] = 'wrong'
        with self.assertRaises(ValueError):
            self.assess()

    def test_evidence_tampering_and_bad_references_fail(self):
        for field, value in [('sha256', 'wrong'), ('path', '../escape'), ('locator', ''),
                             ('url', 'https://example.com/evidence'),
                             ('url', 'https://user:password@eur-lex.europa.eu/a')]:
            ref = dict(self.ref, **{field: value})
            with self.assertRaises(ValueError):
                m.reference(ref, self.evidence, self.root)
        (self.evidence / 'proof.txt').chmod(0o644)
        with self.assertRaises(ValueError):
            self.assess()

    def test_deterministic_order_independent_selection_and_hashes(self):
        rows = [dict(self.row, id=str(i)) for i in range(20)]
        entries = [self.entry_for(r) for r in rows]
        self.write_rows(rows)
        manifest = self.write_manifest(entries)
        plan = m.build_plan(self.root, manifest, self.evidence, per_stratum=3)
        self.assertEqual(len(plan['sample']), 3)
        self.assertEqual(plan, m.build_plan(self.root, manifest, self.evidence, per_stratum=3))
        self.write_rows(list(reversed(rows)))
        other = m.build_plan(self.root, manifest, self.evidence, per_stratum=3)
        self.assertEqual(plan['sample'], other['sample'])
        self.assertNotEqual(plan['planSha256'], other['planSha256'])
        self.assertNotEqual(plan['sourceSnapshots'], other['sourceSnapshots'])
        unknown = m.build_plan(self.root)
        self.assertEqual(unknown['sample'], [])
        self.assertEqual(unknown['strata']['sources-agree']['eligiblePopulation'], 0)

    def test_duplicate_and_unknown_manifest_ids_and_json_keys_fail(self):
        for entries in ([self.entry, self.entry], [dict(self.entry, rowId='absent')]):
            with self.assertRaises(ValueError):
                m.build_plan(self.root, self.write_manifest(entries), self.evidence)
        with self.assertRaises(ValueError):
            m.load_json(b'{"a":1,"a":2}')
        self.write_rows([self.row, self.row])
        with self.assertRaises(ValueError):
            m.build_plan(self.root)

    def test_freeze_exclusive_readonly_idempotent_and_tamper_detection(self):
        plan = m.build_plan(self.root)
        path = self.base / 'freeze' / 'plan.json'
        self.assertTrue(m.freeze(plan, path, self.root))
        before = path.stat()
        self.assertEqual(before.st_mode & 0o777, 0o400)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
        self.assertFalse(m.freeze(plan, path, self.root))
        self.assertEqual(before.st_mtime_ns, path.stat().st_mtime_ns)
        other = m.build_plan(self.root, seed='different')
        with self.assertRaises(ValueError):
            m.freeze(other, path, self.root)
        path.chmod(0o600)
        path.write_text('{}')
        path.chmod(0o400)
        with self.assertRaises(ValueError):
            m.freeze(plan, path, self.root)

    def test_public_repo_symlink_and_insecure_output_rejected(self):
        plan = m.build_plan(self.root)
        with self.assertRaises(ValueError):
            m.freeze(plan, self.root / 'private.json', self.root)
        public = self.base / 'public'
        public.mkdir(mode=0o755)
        with self.assertRaises(ValueError):
            m.freeze(plan, public / 'plan.json', self.root)
        link = self.base / 'link'
        link.symlink_to(self.evidence, target_is_directory=True)
        with self.assertRaises(ValueError):
            m.freeze(plan, link / 'plan.json', self.root)


if __name__ == '__main__':
    unittest.main()
