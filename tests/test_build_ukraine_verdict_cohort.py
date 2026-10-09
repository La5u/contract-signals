import contextlib
import gzip
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_ukraine_verdict_cohort', ROOT / 'tools/build-ukraine-verdict-cohort.py')
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)
# Share the small importer fixture used by the existing cohort tests.
spec = importlib.util.spec_from_file_location('label_cohort_tests', ROOT / 'tests/test_build_ukraine_label_cohort.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


def verdict(tid='UA-t1', label='procurement fraud (no official established)', finality='unknown', day='2026-07-09', rid='1'):
    return {'tender_id_normalised': tid, 'proposed_label': label, 'verdict_date': day, 'reyestr_id': rid,
            'outcome': 'conviction', 'verification': {'finality': finality}}


class FinalityTests(unittest.TestCase):
    def test_final_pending_presumed_and_recent(self):
        today = date(2026, 10, 9)
        classify = lambda *vs: bc.classify_finality(vs, today)
        self.assertEqual(classify(verdict(finality='final 2026-09-30', day='2026-10-01')), 'confirmed')
        self.assertEqual(classify(verdict(finality='appealed: result unavailable')), 'pending-appeal')
        self.assertEqual(classify(verdict(finality='appealed: pending according to case index')), 'pending-appeal')
        self.assertEqual(classify(verdict(finality='appeal filed')), 'pending-appeal')
        self.assertEqual(classify(verdict()), 'presumed')
        self.assertEqual(classify(verdict(day='2026-07-10')), 'too-recent')
        self.assertEqual(classify(verdict(day='invalid')), 'too-recent')
        self.assertEqual(classify(verdict(finality='appealed: convictions preserved on 2026-05-07')), 'confirmed')
        self.assertEqual(classify(verdict(finality='appealed: decision issued')), 'pending-appeal')
        self.assertEqual(classify(verdict(finality='appealed: pending'), verdict(finality='final 2026-08-01')), 'confirmed')

    def test_calendar_month_boundary(self):
        self.assertEqual(bc.three_months_before(date(2026, 5, 31)), date(2026, 2, 28))
        self.assertEqual(bc.three_months_before(date(2024, 5, 31)), date(2024, 2, 29))

    def test_dedup_strongest_label_and_all_ids(self):
        vs = [verdict(rid='2'), verdict(label='corruption (official involved)', rid='3'),
              verdict(label='exclude: acquittal', rid='1'), verdict(rid='2')]
        picks = bc.positive_tenders(vs, date(2026, 10, 9))
        self.assertEqual(len(picks), 1)
        self.assertEqual(picks[0]['label'], 'corruption')
        self.assertEqual(picks[0]['verdict_ids'], ['1', '2', '3'])
        self.assertTrue(picks[0]['positive'])
        self.assertEqual(picks, bc.positive_tenders(list(reversed(vs)), date(2026, 10, 9)))
        self.assertFalse(bc.positive_tenders([verdict(day='2026-10-01')], date(2026, 10, 9))[0]['positive'])


class ComparisonTests(unittest.TestCase):
    def test_deterministic_buyer_year_exclusions(self):
        meta = {'buyerId': 'B', 'created': '2025-03-01', 'procedureId': 'positive', 'tenderID': 'UA-2025-03-01-000001-a'}
        pool = {'B': ['UA-2025-05-01-000002-a', 'UA-2025-12-31-000003-b', 'UA-2025-01-01-000004-a', 'UA-2025-02-01-000005-a',
                      'UA-2024-03-01-000006-a', 'UA-2025-03-01-000001-a'],
                'C': ['UA-2025-06-01-000007-a']}
        order = bc.comparison_order(meta, pool, {'UA-2025-01-01-000004-a'}, {'UA-2025-02-01-000005-a'})
        self.assertEqual(set(order), {'UA-2025-05-01-000002-a', 'UA-2025-12-31-000003-b'})
        self.assertEqual(order, bc.comparison_order(meta, {'B': list(reversed(pool['B']))}, {'UA-2025-01-01-000004-a'}, {'UA-2025-02-01-000005-a'}))
        self.assertEqual(order, bc.comparison_order(meta, {'B': pool['B'] * 2}, {'UA-2025-01-01-000004-a'}, {'UA-2025-02-01-000005-a'}))

    def test_one_minimized_masked_row_per_tender(self):
        t = fixtures.tender(supplier_id='1234567890')
        t['contracts'].append({**t['contracts'][0], 'id': 'd' * 32})
        info = bc.positive_tenders([verdict()], date(2026, 10, 9))[0]
        row, _ = bc.representative_row(t, info)
        self.assertEqual(row['label'], 'fraud')
        self.assertEqual(row['cohortId'], bc.COHORT_ID)
        text = json.dumps(row)
        for secret in ('1234567890', 'PRIVATE PERSON', 'SECRET TITLE', 'a@b.c'):
            self.assertNotIn(secret, text)
        t['contracts'].reverse()
        self.assertEqual(row, bc.representative_row(t, info)[0])


class OfflineTests(unittest.TestCase):
    def test_plan_hard_budget_no_network_or_writes(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / 'cache'
            f = bc.bc.Fetcher(cache, network=False, budget=3, prior=1,
                              opener=lambda u: self.fail('network called'))
            positives = bc.positive_tenders([verdict()], date(2026, 10, 9))
            with contextlib.redirect_stdout(io.StringIO()) as output:
                plan = bc.plan(f, positives, 3, 30)
            self.assertEqual(len(plan.requests), 2)
            self.assertGreater(plan.omitted, 0)
            self.assertIn('Planned request count', output.getvalue())
            self.assertFalse(cache.exists())
            self.assertEqual(f.requests, 1)

    def test_cache_build(self):
        with tempfile.TemporaryDirectory() as d:
            cache, source, out = Path(d) / 'cache', Path(d) / 'input.json', Path(d) / 'cohort.json.gz'
            source.write_text(json.dumps({'verdicts': [verdict(), verdict(tid='UA-recent', day='2026-10-01')]}))
            t = fixtures.tender()
            # Populate cache using an in-memory fake opener, never a socket.
            replies = {bc.imp.DETAILS.format(tender_id='UA-t1'): {'id': 't1'}, bc.bc.tender_url('t1'): {'data': t}}
            f = bc.bc.Fetcher(cache, network=True, budget=150, prior=0, min_interval=0,
                              opener=lambda u: (200, json.dumps(replies[u]).encode(), {}))
            for url in replies:
                f.fetch(url)
            with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')):
                bc.main(['--input', str(source), '--output', str(out), '--cache', str(cache), '--from-cache',
                         '--run-date', '2026-10-09', '--k', '0'])
            data = json.loads(gzip.decompress(out.read_bytes()))
            self.assertEqual(len(data['rows']), 1)
            self.assertEqual(len(data['tenders']), 2)
            self.assertFalse(next(t for t in data['tenders'] if t['tenderID'] == 'UA-recent')['positive'])

    def test_analysis_fixture_unknowns_and_rates(self):
        rows = []
        for tid, label, bids, finality in [('corruption', 'corruption', 1, 'confirmed'),
                                           ('fraud', 'fraud', 2, 'presumed'),
                                           ('comparison', 'comparison', 2, None),
                                           ('unknown', 'fraud', 0, 'presumed'),
                                           ('flagged', 'corruption', 1, 'pending-appeal')]:
            tender = fixtures.tender(tid, bids=bids)
            if tid == 'unknown':
                tender['bids'] = []
            row, _ = bc.representative_row(tender, {'label': label, 'finality': finality, 'group': 'UA-corruption', 'verdict_ids': []})
            rows.append(row)
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / 'cohort.json.gz'
            bc.imp.save_gz(file, {'rows': rows})
            result = subprocess.run(['node', str(ROOT / 'tools/analyze-ukraine-verdict-cohort.cjs'), str(file)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('5 rows assessed; 1 flagged rows excluded', result.stdout)
        single = result.stdout.split('\nua-single-offer\n')[1].split('\n\n')[0]
        self.assertIn('corruption: 1/1 100.0% [20.7%, 100.0%]', single)
        self.assertIn('fraud: 0/1 0.0% [0.0%, 79.3%]; unknown=1', single)
        self.assertIn('combined: 1/2 50.0% [9.5%, 90.5%]; unknown=1', single)
        self.assertIn('comparison: 0/1', single)
        self.assertIn('LR+ combined/comparison: 2.000', single)
        self.assertLess(single.index('combined:'), single.index('comparison:'))

    def test_cached_search_matches_buyer_year_and_excludes_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            cache, source, out = Path(d) / 'cache', Path(d) / 'input.json', Path(d) / 'cohort.json.gz'
            pos, comp, old, excl = '2025-03-01-000001-a', '2025-06-01-000002-a', '2024-03-01-000003-a', '2025-07-01-000004-a'
            source.write_text(json.dumps({'verdicts': [verdict(tid='UA-' + pos), verdict(tid='UA-' + excl, label='exclude: acquittal')]}))
            positive, comparison = fixtures.tender(pos), fixtures.tender(comp)
            listing = {'total': 4, 'data': [{'tenderID': 'UA-' + t} for t in (pos, comp, old, excl)]}
            replies = {bc.imp.DETAILS.format(tender_id='UA-' + pos): {'id': pos},
                       bc.bc.tender_url(pos): {'data': positive},
                       bc.search_url('11111111', 1, '2025'): listing,
                       bc.imp.DETAILS.format(tender_id='UA-' + comp): {'id': comp},
                       bc.bc.tender_url(comp): {'data': comparison}}
            f = bc.bc.Fetcher(cache, network=True, budget=150, prior=0, min_interval=0,
                              opener=lambda u: (200, json.dumps(replies[u]).encode(), {}))
            for url in replies:
                f.fetch(url)
            with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')):
                bc.main(['--input', str(source), '--output', str(out), '--cache', str(cache), '--from-cache',
                         '--run-date', '2026-10-09', '--k', '3'])
            data = json.loads(gzip.decompress(out.read_bytes()))
            self.assertEqual([r['label'] for r in data['rows']], ['fraud', 'comparison'])
            self.assertEqual(data['rows'][1]['group'], 'UA-' + pos)
            self.assertEqual(data['rows'][1]['verdict_ids'], [])
            self.assertTrue(data['summary']['scan_complete'])
            self.assertEqual(data['summary']['notes'][0]['comparisons'], 1)

    def test_reused_fetcher_cap(self):
        with tempfile.TemporaryDirectory() as d:
            calls = []
            def opener(url):
                calls.append(url)
                return 200, b'{"id":"t1"}', {}
            f = bc.bc.Fetcher(d, budget=1, network=True, prior=0, min_interval=0, opener=opener)
            with self.assertRaises(bc.bc.BudgetExceeded):
                bc.resolve(f, 'UA-t1')
            self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
