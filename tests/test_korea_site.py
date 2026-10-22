"""Korean site pipeline on a tiny database: tools/korea-site-checks.py scores each contract with its office's
complete history and leaves amendment-only records unknown; tools/build-korea-site.py publishes a valid period
and never destroys the previous build when a new one fails."""
import contextlib
import gzip
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from common import load  # noqa: E402

normalize = load('normalize_korea_opnstd', 'tools/normalize-korea-opnstd.py')
site_checks = load('korea_site_checks', 'tools/korea-site-checks.py')
build_site = load('build_korea_site', 'tools/build-korea-site.py')
bid_features = load('korea_bid_features', 'tools/korea-bid-features.py')
CHECKS = site_checks.ko.CHECKS


def version(no, ord_, signed, amount, buyer, supplier='1208100001', **extra):
    return {'unty_no': f'{no}-{ord_}', 'cntrct_no': no, 'ord': ord_, 'signed': signed, 'amount': amount,
            'buyer_code': buyer, 'buyer_name': f'office {buyer}', 'buyer_type': 'x', 'demand_code': buyer,
            'demand_name': 'demand', 'supplier_bizrno': supplier, 'supplier_name': 'supplier', 'supplier_kind': 'corporation',
            'method': '일반경쟁', 'business_type': '물품', 'name': f'contract {no}', 'week': '2020-W01', **extra}


class KoreaSite(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.db = self.dir / 'opnstd.sqlite'

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir)

    def make_db(self, versions):
        db = sqlite3.connect(self.db)
        columns = [c for c, _, _ in normalize.COLUMNS] + [c for c, _ in normalize.DERIVED]
        db.execute(f'CREATE TABLE versions ({", ".join(columns)})')
        for v in versions:
            db.execute(f'INSERT INTO versions ({", ".join(v)}) VALUES ({", ".join("?" * len(v))})', list(v.values()))
        normalize.build_contracts(db)
        db.commit()
        db.close()

    def checks(self, versions, bids=None):
        self.make_db(versions)
        out = self.dir / 'site-checks.tsv'
        features = self.dir / 'bid-features.sqlite'
        with contextlib.redirect_stdout(io.StringIO()):
            if bids:
                folder = self.dir / 'bids/goods'
                folder.mkdir(parents=True)
                with gzip.open(folder / '2025-04-15.jsonl.gz', 'wt', encoding='utf-8') as f:
                    f.writelines(json.dumps(r, ensure_ascii=False) + '\n' for r in bids)
                bid_features.main(['--bids', str(self.dir / 'bids'), '--out', str(features), '--workers', '1'])
            site_checks.main(['--db', str(self.db), '--out', str(out), '--workers', '1', '--bids', str(features)])
        lines = out.read_text().splitlines()
        self.assertEqual(lines[0], '# ' + '\t'.join(['contract'] + CHECKS))
        return {no: dict(zip(CHECKS, letters)) for no, letters in (l.split('\t') for l in lines[1:])}

    def build(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()):
            build_site.main(['--db', str(self.db), '--out', str(self.dir / 'site'),
                             '--checks', str(self.dir / 'site-checks.tsv'), *argv])

    def test_contract_that_changed_office_is_scored_with_its_first_office(self):
        # 100 of the office's 10,000 in 2020: a 1 % share, although its latest version names another office.
        got = self.checks([version('A1', 0, '2020-03-01', 9900, 'A'), version('A2', 0, '2020-04-01', 100, 'A'),
                           version('A2', 1, '2020-06-01', 100, 'B')])
        self.assertEqual(got['A2']['G3 buyer share >= 5 %'], 'c')
        self.assertEqual(got['A1']['G3 buyer share >= 5 %'], 's')
        self.assertEqual(set(got), {'A1', 'A2'})

    def test_amendment_only_contract_is_unknown_and_out_of_totals(self):
        # Z has no original: its amendment (99 against a reserve of 100) is no award, and its 10,000 is not in 2020's total.
        got = self.checks([version('W', 0, '2020-03-01', 100, 'A', reserve_price=200),
                           version('Z', 1, '2020-05-01', 99, 'A', reserve_price=100),
                           version('Z', 2, '2020-07-01', 10000, 'A')])
        self.assertEqual(set(got['Z'].values()), {'u'})
        self.assertEqual(got['W']['G3 buyer share >= 5 %'], 's')
        self.assertEqual(got['W']['N4 supplier dependence >= 25 %'], 's')
        self.assertEqual(got['W']['K6 award >= 95 % of reserve'], 'c')

    def test_bid_checks_from_the_contracts_opening(self):
        def bid(notice, ord_, firm, amount, reason='정상', won='N', minute='10:00', rate='90.0'):
            return {'bidNtceNo': notice, 'bidNtceOrd': ord_, 'bsnsDivNm': '물품', 'sucsfLwstlmtRt': '89.95',
                    'bidprcCorpBizrno': firm, 'bidprcAmt': str(amount), 'bidprcRt': rate, 'bidprcDate': '2025-04-14',
                    'bidprcTm': minute, 'sucsfYn': won, 'dqlfctnRsn': reason}
        bids = [bid('N1', '000', 'a', 900),  # a failed first round: one bid
                bid('N1', '001', 'a', 1000, won='Y', minute='10:01'), bid('N1', '001', 'b', 1001, minute='10:01'),
                bid('N1', '001', 'c', 950, reason='서류미제출'), bid('N1', '001', 'd', 960, reason='시공실적미만'),
                bid('N1', '001', 'e', 980, reason='낙찰하한선 미달'), bid('N1', '001', 'f', 1100)]
        got = self.checks([version('X', 0, '2025-04-20', 1000, 'A', notice_no='N1', notice_ord='001'),
                           version('Y', 0, '2025-04-20', 1000, 'A', notice_no='N9')], bids)
        x = {k.split(' ')[0]: v for k, v in got['X'].items()}
        self.assertEqual([x[k] for k in ('B1', 'B2', 'B3', 'B6', 'B7')], ['c', 'c', 's', 's', 's'])
        self.assertIn(x['B4'], 'cs')
        self.assertEqual({v for k, v in got['Y'].items() if k.startswith('B')}, {'u'})

    def test_bid_features(self):
        rows = [{'bidprcAmt': a, 'dqlfctnRsn': '정상', 'sucsfYn': 'Y' if a == 100 else 'N', 'bidprcRt': '88',
                 'sucsfLwstlmtRt': '87.745', 'bidprcDate': '2025-01-01', 'bidprcTm': t} for a, t in ((100, '1'), (110, '2'), (120, '3'))]
        f = bid_features.features(rows)
        self.assertEqual((f['bids'], f['valid'], f['winner'], f['dq_lower'], f['same_minute']), (3, 3, True, 0, False))
        self.assertAlmostEqual(f['rd'], 10 / 7.0710678, places=5)
        self.assertAlmostEqual(f['cv'], 8.1649658 / 110, places=6)

    def test_period_ends_at_the_latest_change(self):
        self.checks([version('C', 0, '2020-01-01', 100, 'A'), version('C', 1, '2025-03-01', 120, 'A')])
        self.build('--start', '2024-09-01')
        meta = json.loads((self.dir / 'site/meta.json').read_text())
        self.assertEqual(meta['period'], ['2024-09-01', '2025-03-01'])
        self.assertEqual(meta['contracts'], 1)

    def test_failed_build_keeps_the_previous_one(self):
        self.checks([version('C', 0, '2025-01-01', 100, 'A')])
        (self.dir / 'site').mkdir()
        (self.dir / 'site/meta.json').write_text('previous')
        with self.assertRaises(SystemExit):
            self.build('--start', '2030-01-01')
        self.assertEqual((self.dir / 'site/meta.json').read_text(), 'previous')
        self.assertFalse((self.dir / 'site.new').exists())
        self.build('--start', '2024-09-01')
        self.assertEqual(json.loads((self.dir / 'site/meta.json').read_text())['contracts'], 1)
        self.assertFalse((self.dir / 'site.new').exists())


if __name__ == '__main__':
    unittest.main()
