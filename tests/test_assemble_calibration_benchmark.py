import copy
import importlib.util
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('assembler', Path(__file__).resolve().parents[1] / 'tools/assemble-calibration-benchmark.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def row(notice='case', **changes):
    result = dict(id=notice, project_id='P1', bid_reference_no=notice, procurement_group='GO', method_code='DIR', signing_date='2020-01-01', signed_contract_price={'amount': '100', 'currency': 'USD'}, review_status='unreviewed-comparison-candidate')
    result.update(changes)
    return result


class AssemblerTests(unittest.TestCase):
    def setUp(self):
        self.case = dict(case_id='c', notice_id='case', project_id='P1', borrower_contract_reference='case', link_status='corroborated-multi-field-match', labels={'fraud': True})

    def assemble(self, rows, cases=None):
        with patch.object(socket, 'socket', side_effect=AssertionError('network prohibited')):
            return a.assemble({'cases': cases or [self.case]}, {'rows': rows}, 'sha')

    def test_no_leakage_method_selection_unknown_and_fit(self):
        other = dict(self.case, case_id='other', notice_id='other', link_status='unresolved')
        result = self.assemble([row(), row('other'), row('alias', bid_reference_no='case'), row('ok', method_code='OPEN', supplier_name='PRIVATE', html='PRIVATE')], [self.case, other])
        self.assertEqual([r['id'] for r in result['rows']], ['case', 'ok'])
        self.assertEqual(result['rows'][1]['labels'], dict.fromkeys(a.TARGETS))
        self.assertEqual(result['rows'][1]['method_code'], 'OPEN')
        self.assertNotIn('PRIVATE', str(result))
        self.assertFalse(result['eligibility']['fraud']['ready_for_fit'])
        self.assertFalse(result['ready_for_fit'])

    def test_tentative_duplicate_and_group_unknown(self):
        self.case['link_status'] = 'tentative-multi-field-match'
        self.assertIsNone(self.assemble([row()])['rows'][0]['labels']['fraud'])
        self.case['link_status'] = 'corroborated-multi-field-match'
        for rows in ([row(), row()], [row(), row('alias', bid_reference_no='case')], [row(validation_flags=['unresolved-grouping'])]):
            self.assertIsNone(self.assemble(rows)['rows'][0]['labels']['fraud'])

    def test_conflicts(self):
        for changes in ({'project_id': 'wrong'}, {'bid_reference_no': 'wrong'}):
            with self.assertRaisesRegex(ValueError, 'project/reference conflict'):
                self.assemble([row(**changes)])

    def test_guards_boundaries_and_determinism(self):
        rows = [row(), row('low', signed_contract_price={'amount': '25', 'currency': 'USD'}), row('high', signed_contract_price={'amount': '400', 'currency': 'USD'}, signing_date='2021-01-01')]
        bad = [row('currency', signed_contract_price={'amount': '100', 'currency': 'EUR'}), row('range', signed_contract_price={'amount': '401', 'currency': 'USD'}), row('date', signing_date='2021-01-02'), row('malformed', signed_contract_price={'amount': '1,000', 'currency': 'USD'}), row('invalid-date', signing_date='2020-02-30')]
        result = self.assemble(rows + bad)
        self.assertEqual({r['id'] for r in result['rows']}, {'case', 'low', 'high'})
        self.assertEqual(result, self.assemble(list(reversed(rows + bad))))

    def test_strict_measurements(self):
        for amount in ('NaN', 'Infinity', '-1', '0', ' 100', '1e2', True, None):
            with self.assertRaises(ValueError):
                a.measurements(row(signed_contract_price={'amount': amount, 'currency': 'USD'}))

    def test_review_regressions(self):
        rows = [row(), row('a'), row('b')]
        for group in ({'key': ['P1', 'a', '2020-01-01']}, {'row_indices': [1]}, {'notice_ids': ['a']}, {'unknown': True}):
            result = a.assemble({'cases': [self.case]}, {'rows': rows, 'duplicate_groups': [group]}, 'sha', 'case-sha')
            self.assertTrue(result['rows'][0]['labels']['fraud'])
            self.assertEqual(result['source_provenance']['case_manifest_sha256'], 'case-sha')
            self.assertTrue(all(r['labels']['fraud'] is None for r in result['rows'][1:]))
        for group in ({'row_indices': [0]}, {'ids': ['case']}, {'key': ['P1', 'case', '2020-01-01']}):
            result = a.assemble({'cases': [self.case]}, {'rows': rows, 'duplicate_groups': [group]}, 'sha')
            self.assertIsNone(result['rows'][0]['labels']['fraud'])
        for key in ('review_scope', 'finding_standard', 'finding_scope', 'limitations', 'link_basis', 'decision_paragraphs'):
            self.case[key] = ['evidence']
        result = self.assemble(rows)
        self.assertEqual(result['rows'][0]['decision_paragraphs'], ['evidence'])
        self.assertIsNone(result['source_provenance']['case_manifest_sha256'])
        self.case['expected_signing_date'] = '2020-02-01'
        with self.assertRaisesRegex(ValueError, 'signing date conflict'):
            self.assemble(rows)

    def test_incomplete_events_and_presence_not_readiness(self):
        rows = [row(signing_date=None), row('b', bid_reference_no='case', signing_date=None)]
        result = self.assemble(rows)
        self.assertTrue(result['rows'][0]['labels']['fraud'])
        self.assertNotIn('duplicate-contract-event', result['rows'][0]['grouping_flags'])
        self.assertFalse(result['ready_for_fit'])
        negative = dict(self.case, case_id='negative', notice_id='negative', borrower_contract_reference='negative', labels={'fraud': False})
        result = self.assemble([row(), row('negative')], [self.case, negative])
        self.assertTrue(result['eligibility']['fraud']['has_both_label_classes'])
        self.assertFalse(result['eligibility']['fraud']['ready_for_fit'])
        self.assertFalse(result['ready_for_fit'])

    def test_documentary_records(self):
        document = row('doc', record_type='documentary-contract', source_documents=[{
            'url': 'https://example.org/decision.pdf', 'citation': 'paragraph 12',
            'sha256_raw_response': 'document-sha'}], notice_date=None,
            conflicting_source_values={'signing_date': ['2019-01-01']})
        case = dict(self.case, record_id='doc', notice_id='missing-notice',
                    borrower_contract_reference='doc', expected_signing_date='2020-01-01',
                    labels={'corruption': True})

        def assemble(doc=document, linked=case):
            with patch.object(socket, 'socket', side_effect=AssertionError('network prohibited')):
                return a.assemble({'cases': [linked], 'documentary_records': [doc]},
                                  {'rows': [row('candidate')]}, 'pool-sha', 'manifest-sha')

        result = assemble()
        self.assertEqual([r['id'] for r in result['rows']], ['doc', 'candidate'])
        self.assertTrue(result['rows'][0]['labels']['corruption'])
        self.assertEqual(result['rows'][0]['record_type'], 'documentary-contract')
        self.assertNotIn('notice_id', result['rows'][0])
        self.assertEqual(result['rows'][1]['labels'], dict.fromkeys(a.TARGETS))
        self.assertEqual(result['source_provenance']['documentary_records'][0]['source_documents'], document['source_documents'])
        self.assertFalse(result['ready_for_fit'])
        for changes, error in (({'bid_reference_no': 'wrong'}, 'project/reference conflict'),
                               ({'project_id': 'wrong'}, 'project/reference conflict'),
                               ({'signing_date': '2020-02-01'}, 'signing date conflict')):
            with self.assertRaisesRegex(ValueError, error):
                assemble(dict(document, **changes))
        unknown = assemble(linked=dict(case, labels={}, decision_url='https://example.org/audit'))
        self.assertEqual(unknown['rows'][0]['labels'], dict.fromkeys(a.TARGETS))
        pending = assemble(linked=dict(case, link_status='tentative-multi-field-match'))
        self.assertEqual(pending['rows'], [])
        self.assertEqual(pending['pending_links'][0]['record_id'], 'doc')
        self.assertEqual(pending['pending_links'][0]['notice_id'], 'missing-notice')
        for invalid in (None, dict(document, id=''), dict(document, record_type='notice'),
                        dict(document, source_documents=[]),
                        dict(document, source_documents=[{'url': 'https://example.org/a'}])):
            with self.assertRaises(ValueError):
                assemble(invalid)

    def test_limit_stable_and_pending(self):
        rows = [row()] + [row(f'n{i:02}') for i in range(20)]
        result = self.assemble(rows)
        self.assertEqual(len(result['rows']), 13)
        self.assertEqual(result, self.assemble(rows[::-1]))
        self.case['notice_id'] = 'missing'
        result = self.assemble(rows)
        self.assertEqual(result['rows'], [])
        self.assertEqual(len(result['pending_links']), 1)


if __name__ == '__main__':
    unittest.main()
