import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sweep_ukraine_verdicts', ROOT / 'tools/sweep-ukraine-verdicts.py')
sw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sw)


class TenderIds(unittest.TestCase):
    def ids(self, text):
        return set(sw.tender_ids(text))

    def test_plain_id(self):
        self.assertEqual(self.ids('з ідентифікатором UA-2022-11-18-008338-a, орієнтовна'), {'UA-2022-11-18-008338-a'})

    def test_cyrillic_lookalikes_and_spaces(self):
        self.assertEqual(self.ids('UА-2018-06-07-002943-а'), {'UA-2018-06-07-002943-a'})
        self.assertEqual(self.ids('UA - 2020 - 01 - 02 - 123456 - b'), {'UA-2020-01-02-123456-b'})

    def test_lowercase_url_and_soft_sign(self):
        self.assertEqual(self.ids('prozorro.gov.ua/tender/ua-2018-05-16-000079-b.'), {'UA-2018-05-16-000079-b'})
        self.assertEqual(self.ids('UA-2016-12-15-002302-ь'), {'UA-2016-12-15-002302-b'})

    def test_bare_id_merged_into_suffixed(self):
        self.assertEqual(self.ids('UA-2019-12-05-000169 та UA-2019-12-05-000169-b'), {'UA-2019-12-05-000169-b'})

    def test_suffix_must_be_one_letter(self):
        self.assertEqual(self.ids('UA-2019-11-29-000765-Оплата'), {'UA-2019-11-29-000765'})
        self.assertEqual(self.ids('UA-2021-02-16-001638-b-c1'), {'UA-2021-02-16-001638-b'})

    def test_missing_first_hyphen(self):
        self.assertEqual(self.ids('закупівлі UA2021-02-01-000081-c на'), {'UA-2021-02-01-000081-c'})
        self.assertEqual(self.ids('рахунок 2601UA2021-02-01-0000812'), set())

    def test_plans_and_bad_dates_ignored(self):
        self.assertEqual(self.ids('UA-P-2020-01-01-000001-a'), set())
        self.assertEqual(self.ids('UA-2020-13-01-000001-a'), set())

    def test_context_kept(self):
        hit = sw.tender_ids('закупівля UA-2022-11-18-008338-a шин')['UA-2022-11-18-008338-a']
        self.assertIn('шин', hit['context'])
        self.assertEqual(hit['as_printed'], 'UA-2022-11-18-008338-a')


class Rtf(unittest.TestCase):
    def test_cp1251_escapes_and_skipped_tables(self):
        body = (rb"{\rtf1\ansi\ansicpg1251{\fonttbl{\f0 Times New Roman CYR;}}{\colortbl ;\red0;}"
                rb"\pard \'c2\'c8\'d0\'ce\'ca\par UA-2022-11-18-008338-a\par " + b"\\" + b"u1028?}")
        self.assertEqual(sw.plain(body).split('\n'), ['ВИРОК', 'UA-2022-11-18-008338-a', 'Є'])

    def test_html_fallback(self):
        self.assertEqual(sw.plain('<p>Вирок&nbsp;UA</p>'.encode()).strip(), 'Вирок UA')


class Outcome(unittest.TestCase):
    def test_pleas_before_operative_part_ignored(self):
        text = 'Захисник просив виправдати. Особа вважається невинуватою. УХВАЛИВ: ОСОБА_1 визнати винуватим і призначити йому покарання'
        self.assertEqual(sw.outcome(text), 'conviction')

    def test_acquittal_and_mixed(self):
        self.assertEqual(sw.outcome('У Х В А Л И В: ОСОБА_1 визнати невинуватим та виправдати'), 'acquittal')
        self.assertEqual(sw.outcome('УХВАЛИВ: ОСОБА_1 визнати винуватим. ОСОБА_2 визнати невинуватим і виправданим'), 'mixed')

    def test_no_operative_heading(self):
        self.assertEqual(sw.outcome('ОСОБА_1 визнати винуватим'), 'unclear')


class Labels(unittest.TestCase):
    def test_label_rule(self):
        row = {'outcome': 'conviction (plea agreement)', 'tender_role': 'scheme', 'official_involved': 'yes'}
        self.assertEqual(sw.proposed_label(row), 'corruption (official involved)')
        self.assertEqual(sw.proposed_label({**row, 'official_involved': 'unclear'}), 'procurement fraud (no official established)')
        self.assertTrue(sw.proposed_label({**row, 'tender_role': 'context'}).startswith('exclude'))
        self.assertTrue(sw.proposed_label({**row, 'outcome': 'other'}).startswith('exclude'))

    def test_finality_state(self):
        v = {'verdict_date': '2024-01-01', 'later_higher_court_decisions': [{'adjudication_date': '2024-05-01'}]}
        self.assertTrue(sw.finality_state(v, '2024-02-01').startswith('final 2024-02-01'))
        self.assertTrue(sw.finality_state(v, 'no date shown').startswith('appeal'))
        self.assertEqual(sw.finality_state({**v, 'later_higher_court_decisions': []}, 'no date shown'), '')


class Appeals(unittest.TestCase):
    def test_only_higher_instances(self):
        rows = [{'doc_id': '1', 'cause_num': 'c', 'court': 'first', 'instance': '3', 'judgment_code': '1', 'adjudication_date': '2024-01-01'},
                {'doc_id': '2', 'cause_num': 'c', 'court': 'appeal', 'instance': '2', 'judgment_code': '5', 'adjudication_date': '2024-05-01'}]
        self.assertEqual([d['doc_id'] for d in sw.appeals(rows)['c']], ['2'])


if __name__ == '__main__':
    unittest.main()
