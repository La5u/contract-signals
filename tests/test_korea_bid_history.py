"""B10/B11 rules and missing-input handling on synthetic, unlabelled bid histories."""
import contextlib
import csv
import datetime as dt
import gzip
import importlib.util
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # parsing workers look functions up by module name
    spec.loader.exec_module(module)
    return module


history = load('korea_history', 'tools/korea-bid-history.py')
labels = load('korea_labels', 'tools/korea-label-checks.py')
CENTER = dt.date(2020, 7, 1)


def stamp(offset):
    return (CENTER + dt.timedelta(days=offset)).isoformat()


class HistoryRules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.db = history.connect(self.folder / 'history.sqlite')
        self.codes = history.Codes(self.db)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def n(self, notice):
        return self.codes.identity('notice', notice)

    def opening(self, notice, offset, rates, winner=None, demand='buyer', ord_='000'):
        for bizno, quote in rates.items():
            self.db.execute(history.UPSERT, (self.n(notice), int(ord_), history.day(stamp(offset)), self.codes.demand(demand),
                                            self.codes.identity('bizno', bizno), *history.rate(quote), int(bizno == winner), 0))
        self.db.execute('INSERT OR IGNORE INTO dirty VALUES (?, ?)', (self.n(notice), int(ord_)))
        self.db.commit()
        history.refresh_openings(self.db)

    def check(self, notice='target', ord_='000'):
        o = self.db.execute('SELECT * FROM openings WHERE notice = ? AND ord = ?', (self.n(notice), int(ord_))).fetchone()
        return (history.rotation(self.db, o, history.day(stamp(-365)), history.day(stamp(365))),
                history.repeated_quotes(self.db, o, history.day(stamp(-365)), history.day(stamp(365))))

    def test_rotation_three_other_openings_same_demand_inclusive_window(self):
        self.opening('target', 0, {'W': '90', 'F': '91'}, winner='W')
        self.opening('past', -365, {'W': '92', 'F': '90'}, winner='F')
        self.opening('middle', 10, {'W': '90', 'F': '93', 'X': '89'}, winner='X')
        self.opening('future', 365, {'W': '93', 'F': '94'})
        self.assertEqual(self.check()[0], 1)
        # The current win is excluded, and two qualifying other openings are insufficient.
        self.db.execute(f"UPDATE bids SET opening_date = ? WHERE notice = {self.n('future')}", (history.day(stamp(366)),))
        self.assertEqual(self.check()[0], 0)
        self.db.execute(f"UPDATE bids SET opening_date = ?, demand_code = {self.codes.demand('other')} WHERE notice = {self.n('future')}", (history.day(stamp(365)),))
        self.assertEqual(self.check()[0], 0)

    def test_rotation_does_not_combine_peers_or_count_a_win_without_w(self):
        self.opening('target', 0, {'W': '90', 'F': '91', 'G': '92'}, winner='W')
        for i in range(3):
            self.opening(f'common{i}', i + 1, {'W': '90', 'F': '91'}, winner='W')
        self.opening('alone', 4, {'F': '90', 'G': '91'}, winner='F')
        self.opening('gwin', 5, {'W': '91', 'G': '90'}, winner='G')
        self.assertEqual(self.check()[0], 0)
        self.db.execute(f"UPDATE openings SET winner = NULL, winners = 0 WHERE notice = {self.n('target')}")
        self.assertIsNone(self.check()[0])
        self.db.execute(f"UPDATE openings SET winner = {self.codes.identity('bizno', 'W')}, winners = 1, demand_code = NULL WHERE notice = {self.n('target')}")
        self.assertIsNone(self.check()[0])

    def test_quotes_round_difference_not_each_rate_and_allow_large_comparisons(self):
        self.opening('target', 0, {'a': '90.0004', 'b': '91.0009'})
        # Absolute differences: the relative price order may reverse. Same notice,
        # different order is another opening. Historical buyer and bid count may differ.
        self.opening('target', -365, {'a': '91.1005', 'b': '90.1'}, demand='other', ord_='001')
        big = {f'firm{i}': str(100 + i) for i in range(21)}
        big.update({'a': '93.0005', 'b': '92'})
        self.opening('big', 365, big, demand='another')
        self.assertEqual(self.check()[1], 1)
        self.db.execute(f"UPDATE bids SET opening_date = ? WHERE notice = {self.n('big')}", (history.day(stamp(366)),))
        self.assertEqual(self.check()[1], 0)
        self.assertEqual(self.check('big')[1], 0)  # >20 target bids

    def test_zero_gaps_distinct_pairs_and_missing_quotes(self):
        self.opening('target', 0, {'a': '90', 'b': '90.0004'})
        for i in range(2):
            self.opening(f'zero{i}', i + 1, {'a': '91', 'b': '91'})
        self.assertEqual(self.check()[1], 0)
        self.db.execute(f"UPDATE bids SET rate = 91000 WHERE notice = {self.n('target')} AND bizno = {self.codes.identity('bizno', 'b')}")
        self.opening('different', 3, {'x': '90', 'y': '91'})
        self.assertEqual(self.check()[1], 0)
        self.opening('one', 4, {'a': '90', 'b': '91'})
        self.opening('missing', 5, {'a': '90', 'b': None})
        self.assertIsNone(self.check()[1])
        self.opening('two', 6, {'a': '92', 'b': '93'})
        self.assertEqual(self.check()[1], 1)
        self.db.execute(f"UPDATE bids SET rate = NULL WHERE notice = {self.n('target')} AND bizno = {self.codes.identity('bizno', 'b')}")
        self.assertIsNone(self.check()[1])

    def test_window_gate_and_incremental_invalidation(self):
        self.opening('target', 0, {'W': '90', 'F': '91'}, winner='W')
        for i, offset in enumerate((-300, 10, 300)):
            self.opening(f'other{i}', offset, {'W': '90', 'F': '91'}, winner='F')
        history.refresh_checks(self.db, history.day(stamp(-1)), history.day(stamp(1)), set())
        self.assertEqual(self.db.execute(f"SELECT b10, b11 FROM checks WHERE notice = {self.n('target')}").fetchone(), (None, None))
        # New coverage is enough to refresh an unchanged target opening.
        history.refresh_checks(self.db, history.day(stamp(-1)), history.day(stamp(1)), {history.day(stamp(0))})
        self.assertEqual(self.db.execute(f"SELECT b10, b11 FROM checks WHERE notice = {self.n('target')}").fetchone(), (1, 1))
        history.refresh_checks(self.db, history.day(stamp(-1)), history.day(stamp(1)), set())
        self.assertEqual(self.db.execute(f"SELECT b10, b11 FROM checks WHERE notice = {self.n('target')}").fetchone(), (None, None))
        history.refresh_checks(self.db, history.day(stamp(-1)), history.day(stamp(1)), {history.day(stamp(0))})
        self.opening('other0', -300, {'W': '90', 'F': '95'}, winner='F')
        self.opening('other1', 10, {'W': '90', 'F': '95'}, winner='F')
        history.refresh_checks(self.db, history.day(stamp(-1)), history.day(stamp(1)), {history.day(stamp(0))})
        self.assertEqual(self.db.execute(f"SELECT b10, b11 FROM checks WHERE notice = {self.n('target')}").fetchone(), (1, 0))

    def test_compact_types_and_lexical_demand_precedence(self):
        self.opening('20190701001', 0, {'0000000010': '90.0004'}, demand='z')
        self.opening('20190701001', 1, {'1234567890': '91.0009'}, demand='a')
        self.assertEqual(self.db.execute('SELECT DISTINCT demand_code FROM bids').fetchall(),
                         [(self.codes.demand('z'),)])
        self.assertEqual(self.db.execute('SELECT DISTINCT opening_date FROM bids').fetchall(),
                         [(history.day(stamp(1)),)])
        types = self.db.execute('''SELECT typeof(notice), typeof(ord), typeof(opening_date), typeof(demand_code),
            typeof(bizno), typeof(rate), typeof(rate_tail), typeof(won) FROM bids LIMIT 1''').fetchone()
        self.assertEqual(types, ('integer',) * 8)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM identities').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT MIN(bizno) FROM bids').fetchone()[0], 10)
        a, at = history.rate('90.0004')
        b, bt = history.rate('91.0009')
        self.assertEqual(history.quote_gap(a, b, at, bt), 1001)

    def test_non_numeric_order_is_skipped(self):
        row = {'bidNtceNo': '20100331065', 'bidNtceOrd': '0-2', 'opengDate': '2010-04-16', 'dmndInsttCd': 'd',
               'bidprcCorpBizrno': '1234567890', 'bidprcRt': '90', 'sucsfYn': 'N'}
        self.assertIsNone(history.record(row, False, self.codes))
        self.assertIsNotNone(history.record(dict(row, bidNtceOrd='002'), False, self.codes))

    def test_prune_is_inclusive_and_preserves_results(self):
        for name, offset in [('old', -366), ('left', -365), ('target', 0), ('right', 365), ('future', 366)]:
            self.opening(name, offset, {'1': '90', '2': '91'}, winner='1')
        history.refresh_checks(self.db, history.day(stamp(-366)), history.day(stamp(367)), set())
        history.prune(self.db, history.day(stamp(-365)), history.day(stamp(365)))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM checks').fetchone()[0], 5)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM openings').fetchone()[0], 3)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM bids').fetchone()[0], 6)
        self.assertEqual(self.db.execute('SELECT MIN(opening_date), MAX(opening_date) FROM bids').fetchone(),
                         (history.day(stamp(-365)), history.day(stamp(365))))

    def test_hard_database_ceiling(self):
        path = self.folder / 'limited.sqlite'
        with contextlib.closing(history.connect(path, max_bytes=1_000_000)) as db:
            limit = db.execute('PRAGMA max_page_count').fetchone()[0] * db.execute('PRAGMA page_size').fetchone()[0]
            with self.assertRaisesRegex(sqlite3.OperationalError, 'full'):
                with db:
                    db.execute("INSERT INTO meta VALUES ('oversize', zeroblob(1100000))")
            self.assertLessEqual(path.stat().st_size, limit)


class Coverage(unittest.TestCase):
    def api(self, lo, hi):
        return [(None, kind, stamp(i)) for i in range(lo, hi + 1) for kind in history.BUSINESS]

    def hub(self):
        lo = CENTER - dt.timedelta(days=425)
        lo -= dt.timedelta(days=lo.weekday())
        return [(None, 'hub', (lo + dt.timedelta(days=i)).isoformat()) for i in range(0, 798, 7)]

    def test_api_requires_all_four_types_and_every_day_including_weekends(self):
        files = self.api(-365, 365)
        self.assertEqual(history.complete_days(files), {history.day(stamp(0))})
        self.assertEqual(history.complete_days(files[1:]), set())
        self.assertEqual(history.complete_days([r for r in files if r[2] != stamp(17)]), set())

    def test_hub_notice_lookback_and_mixed_sources(self):
        files = self.hub()
        self.assertIn(history.day(stamp(0)), history.complete_days(files))
        missing = files[len(files) // 2]
        files.remove(missing)
        self.assertNotIn(history.day(stamp(0)), history.complete_days(files))
        # A missing notice week affects opening coverage through its Sunday + 60.
        monday = dt.date.fromisoformat(missing[2])
        offset = (monday - CENTER).days
        files += self.api(offset, offset + 66)
        self.assertIn(history.day(stamp(0)), history.complete_days(files))
        files.pop()
        self.assertNotIn(history.day(stamp(0)), history.complete_days(files))
        first = dt.date.fromisoformat(self.hub()[0][2])
        earliest_center = first + dt.timedelta(days=60 + 365)
        self.assertIn(earliest_center.toordinal(), history.complete_days(self.hub()))
        self.assertNotIn((earliest_center - dt.timedelta(days=1)).toordinal(), history.complete_days(self.hub()))


class Integration(unittest.TestCase):
    def test_history_reader_accepts_numeric_keys_and_legacy_text_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            features = folder / 'bid-features.sqlite'
            with contextlib.closing(sqlite3.connect(features)) as db:
                db.execute('CREATE TABLE refs (type, year)')
            current, legacy = folder / 'current.sqlite', folder / 'legacy.sqlite'
            with contextlib.closing(history.connect(current)) as db:
                db.execute("INSERT INTO meta VALUES ('checks_ready', '1')")
                db.execute('INSERT INTO checks VALUES (20190701001, 1, 1, 0)')
                db.commit()
            with contextlib.closing(sqlite3.connect(legacy)) as db:
                db.execute('CREATE TABLE meta (key, value)')
                db.execute('CREATE TABLE checks (notice, ord, b10, b11)')
                db.execute("INSERT INTO meta VALUES ('checks_ready', '1')")
                db.execute("INSERT INTO checks VALUES ('20190701001', '001', 1, 0)")
                db.commit()
            for path in (current, legacy):
                reader = labels.Bids(features, path)
                try:
                    self.assertEqual(dict(reader.history({'notice': '20190701001', 'ord': '001'})), {'b10': 1, 'b11': 0})
                    self.assertIsNone(reader.history({'notice': 'missing', 'ord': '001'}))
                finally:
                    reader.con.close()
                    reader.history_con.close()

    def test_streaming_dedup_resume_and_same_opening_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            hub, api = folder / 'hub', folder / 'api'
            hub.mkdir()
            (api / 'goods').mkdir(parents=True)
            names = ['입찰공고번호', '입찰공고차수', '개찰일자', '수요기관코드', '업체사업자등록번호', '투찰율', '낙찰자선정여부']
            with gzip.open(hub / '2020-06-29.csv.gz', 'wt', encoding='utf-8', newline='') as f:
                writer = csv.writer(f, delimiter='\t')
                writer.writerow(names)
                writer.writerows([['n', '1', '20200701', 'd', 'a', '1,002.564', 'Y'],
                                  ['n', '001', '20200701', 'd', 'a', '1,002.564', 'Y'],
                                  ['n', '001', '20200702', 'd', 'b', '', 'N'],
                                  ['bad', '001', '', 'd', 'c', '90', 'N'],
                                  ['bad', '001', '20200701', 'd', '', '90', 'N']])
            with gzip.open(api / 'goods/2020-07-01.jsonl.gz', 'wt') as f:
                f.write(json.dumps({'bidNtceNo': 'n', 'bidNtceOrd': '001', 'opengDate': '2020-07-01',
                                    'bidprcCorpBizrno': 'a', 'bidprcRt': '90', 'sucsfYn': 'Y'}) + '\n')
            out = folder / 'bid-history.sqlite'
            argv = ['--datahub', str(hub), '--bids', str(api), '--out', str(out)]
            with contextlib.redirect_stdout(io.StringIO()):
                history.main(argv)
                history.main(argv)
            db = sqlite3.connect(out)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM bids').fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT ord, rate, (SELECT code FROM demands WHERE id = demand_code), won FROM bids WHERE bizno = (SELECT id FROM identities WHERE kind = 'bizno' AND value = 'a')").fetchone(),
                             (1, 90000, 'd', 1))
            self.assertEqual(db.execute('SELECT b10, b11 FROM checks').fetchone(), (None, None))
            self.assertEqual(db.execute('SELECT DISTINCT opening_date FROM bids').fetchall(), [(history.day('2020-07-01'),)])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sources').fetchone()[0], 2)
            # B10/B11 attach to the same notice order chosen by B1-B9.
            features = folder / 'bid-features.sqlite'
            con = sqlite3.connect(features)
            con.execute('CREATE TABLE openings (notice, ord, day, winner)')
            con.executemany('INSERT INTO openings VALUES (?, ?, ?, ?)', [('n', '000', '2020-06-30', 0),
                                                                        ('n', '001', '2020-07-01', 1)])
            con.execute('CREATE TABLE refs (type, year)')
            con.commit()
            con.close()
            db.execute("UPDATE checks SET b10 = 1, b11 = 0")
            db.commit()
            bids = labels.Bids(features)
            self.assertEqual(dict(bids.history(bids.opening('n', '001'))), {'b10': 1, 'b11': 0})
            self.assertIsNone(bids.history(bids.opening('n', '000')))
            db.execute("UPDATE meta SET value = '0' WHERE key = 'checks_ready'")
            db.commit()
            self.assertIsNone(bids.history(bids.opening('n', '001')))
            self.assertTrue(all(v['status'] == 'unknown' for v in labels.bid_checks(None, {}).values()))
            bids.con.close()
            bids.history_con.close()
            db.close()
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(SystemExit, 'scope changed'):
                    history.main(argv + ['--limit', '1'])
                (hub / '2020-06-29.csv.gz').unlink()
                with self.assertRaisesRegex(SystemExit, 'source changed or disappeared'):
                    history.main(argv)

    def test_new_weeks_enable_coverage_and_new_bids_invalidate_nearby_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            hub, api = folder / 'hub', folder / 'api'
            hub.mkdir()
            (api / 'goods').mkdir(parents=True)
            weeks = Coverage().hub()
            missing = weeks[len(weeks) // 2][2]
            names = ['입찰공고번호', '입찰공고차수', '개찰일자', '수요기관코드', '업체사업자등록번호', '투찰율', '낙찰자선정여부']
            for _, _, monday in weeks:
                if monday == missing:
                    continue
                with gzip.open(hub / f'{monday}.csv.gz', 'wt', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f, delimiter='\t')
                    writer.writerow(names)
                    if monday == '2020-06-29':
                        for i in range(4):
                            for bizno in ('W', 'F'):
                                writer.writerow([f'n{i}', '000', stamp(i).replace('-', ''), 'buyer', bizno,
                                                 '90' if bizno == 'W' else '91',
                                                 'Y' if bizno == ('W' if i == 0 else 'F') else 'N'])
            # In-progress exports never contribute coverage.
            (hub / f'{missing}.csv.part').touch()
            out = folder / 'history.sqlite'
            argv = ['--datahub', str(hub), '--bids', str(api), '--out', str(out)]

            def run():
                with contextlib.redirect_stdout(io.StringIO()):
                    history.main(argv)
                with contextlib.closing(sqlite3.connect(out)) as db:
                    return db.execute("SELECT b10, b11 FROM checks WHERE notice = (SELECT id FROM identities WHERE kind = 'notice' AND value = 'n0')").fetchone()

            self.assertEqual(run(), (None, None))
            with gzip.open(hub / f'{missing}.csv.gz', 'wt') as f:
                f.write('\t'.join(names) + '\n')
            self.assertEqual(run(), (1, 1))
            for i in (1, 2):
                with gzip.open(api / f'goods/{stamp(i)}.jsonl.gz', 'wt') as f:
                    f.write(json.dumps({'bidNtceNo': f'n{i}', 'bidNtceOrd': '000', 'opengDate': stamp(i),
                                        'bidprcCorpBizrno': 'F', 'bidprcRt': '95', 'sucsfYn': 'Y'}) + '\n')
            self.assertEqual(run(), (1, 0))

    def test_bid_check_statuses_for_history_values_and_missing_history(self):
        opening = dict(type='goods', year=2020, bids=2, winner_rate=None, lower_rate=None,
                       cv=None, rd=None, dq_lower=None, same_minute=False)
        found = labels.bid_checks(opening, {}, {'b10': 1, 'b11': 0})
        self.assertEqual(found['B10 rotation']['status'], 'signal')
        self.assertEqual(found['B11 repeated quote pair']['status'], 'clear')
        for data in (None, {'b10': None, 'b11': None}):
            found = labels.bid_checks(opening, {}, data)
            self.assertEqual(found['B10 rotation']['status'], 'unknown')
            self.assertEqual(found['B11 repeated quote pair']['status'], 'unknown')


class Rolling(unittest.TestCase):
    names = ['입찰공고번호', '입찰공고차수', '개찰일자', '수요기관코드', '업체사업자등록번호', '투찰율', '낙찰자선정여부']

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.hub = self.folder / 'hub'
        self.hub.mkdir()
        self.out = self.folder / 'bid-history.sqlite'
        self.argv = ['--datahub', str(self.hub), '--bids', str(self.folder / 'api'), '--out', str(self.out)]

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, monday, rows=()):
        path = self.hub / f'{monday}.csv.gz'
        with gzip.open(path, 'wt', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(self.names)
            writer.writerows(rows)
        return path

    def run_history(self):
        with contextlib.redirect_stdout(io.StringIO()):
            history.main(self.argv)

    def full_fixture(self):
        rows = {}
        for notice, opened, winner in [('1', '2018-02-01', '10'), ('2', '2018-07-01', '20'),
                                       ('3', '2019-07-01', '10'), ('4', '2019-07-02', '20'),
                                       ('5', '2020-06-30', '20'), ('6', '2021-12-01', '10')]:
            d = dt.date.fromisoformat(opened) - dt.timedelta(days=7)
            monday = (d - dt.timedelta(days=d.weekday())).isoformat()
            for bizno in ('10', '20'):
                rows.setdefault(monday, []).append([notice, '000', opened, 'buyer', bizno,
                                                   '90' if bizno == '10' else '91', 'Y' if bizno == winner else 'N'])
        # This file straddles the first window's upper edge and must be reread.
        rows['2019-03-25'] = [['7', '000', '2019-03-28', 'buyer', '30', '90', 'Y'],
                              ['8', '000', '2019-04-02', 'buyer', '30', '90', 'Y']]
        d = dt.date(2018, 1, 1)
        while d <= dt.date(2022, 1, 3):
            self.write(d.isoformat(), rows.get(d.isoformat(), ()))
            d += dt.timedelta(days=7)

    def test_parallel_parsing_matches_in_process_parsing(self):
        self.full_fixture()
        tables = []
        for workers in ('0', '3'):
            out = self.folder / f'workers-{workers}.sqlite'
            with contextlib.redirect_stdout(io.StringIO()):
                history.main(self.argv[:-1] + [str(out), '--workers', workers])
            with contextlib.closing(sqlite3.connect(out)) as db:
                tables.append([db.execute(f'SELECT * FROM {t} ORDER BY 1, 2').fetchall()
                               for t in ('bids', 'openings', 'checks', 'loads')])
        self.assertTrue(tables[0][2])
        self.assertEqual(tables[0], tables[1])

    def test_rolling_matches_unpruned_history_and_skips_unchanged_blocks(self):
        self.full_fixture()
        with mock.patch.object(history, 'import_file', wraps=history.import_file) as imported:
            self.run_history()
        calls = [str(c.args[2]) for c in imported.call_args_list]
        self.assertEqual(calls.count(str(self.hub / '2019-03-25.csv.gz')), 3)
        with contextlib.closing(sqlite3.connect(self.out)) as db:
            actual = db.execute('SELECT * FROM checks ORDER BY notice, ord').fetchall()
            self.assertEqual(db.execute('SELECT b10, b11 FROM checks WHERE notice = 3').fetchone(), (1, 1))
            self.assertTrue(db.execute("SELECT 1 FROM blocks WHERE status = 'done'").fetchone())
            self.assertTrue(db.execute("SELECT 1 FROM blocks WHERE status = 'pending'").fetchone())
            # Last window has pruned 2018/2019, yet their check results survive.
            self.assertIsNone(db.execute('SELECT 1 FROM bids WHERE notice = 3').fetchone())
            self.assertEqual(len(actual), 8)
        # Compare every result with the same definitions over a non-pruned database.
        with contextlib.closing(history.connect(self.folder / 'oracle.sqlite')) as db:
            codes = history.Codes(db)
            files = [(p, 'hub', p.name[:10]) for p in sorted(self.hub.glob('*.gz'))]
            for path, kind, stamp_ in files:
                history.import_file(db, codes, path, kind, stamp_, path.stat(), history.day('2018-01-01'), history.day('2022-12-31'))
            history.refresh_openings(db)
            history.refresh_checks(db, history.day('2018-01-01'), history.day('2023-01-01'), history.complete_days(files))
            self.assertEqual(db.execute('SELECT * FROM checks ORDER BY notice, ord').fetchall(), actual)
        with mock.patch.object(history, 'import_file', wraps=history.import_file) as imported:
            self.run_history()
            imported.assert_not_called()
        # Even a completed block must be revisited when newly arrived API rows
        # change a comparison, after its original scratch history has been pruned.
        goods = self.folder / 'api/goods'
        goods.mkdir(parents=True)
        for notice, date in [('4', '2019-07-02'), ('5', '2020-06-30')]:
            with gzip.open(goods / f'{date}.jsonl.gz', 'wt') as f:
                f.write(json.dumps({'bidNtceNo': notice, 'bidNtceOrd': '000', 'opengDate': date,
                                    'bidprcCorpBizrno': '20', 'bidprcRt': '95', 'sucsfYn': 'Y'}) + '\n')
        self.run_history()
        with contextlib.closing(sqlite3.connect(self.out)) as db:
            self.assertEqual(db.execute('SELECT b10, b11 FROM checks WHERE notice = 3').fetchone(), (1, 0))
            self.assertEqual(db.execute('SELECT status FROM blocks WHERE start = ?',
                                       (history.day('2019-07-01'),)).fetchone()[0], 'done')

    def test_interrupted_block_is_recomputed_before_marked_done(self):
        self.full_fixture()
        original = history.refresh_checks
        def interrupt(db, start, end, *args):
            result = original(db, start, end, *args)
            if start == history.day('2019-07-01'):
                raise RuntimeError('interrupted after result commit')
            return result
        with mock.patch.object(history, 'refresh_checks', side_effect=interrupt):
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                self.run_history()
        with contextlib.closing(sqlite3.connect(self.out)) as db:
            self.assertEqual(db.execute("SELECT value FROM meta WHERE key = 'checks_ready'").fetchone()[0], '0')
            self.assertIsNone(db.execute('SELECT 1 FROM blocks WHERE start = ?', (history.day('2019-07-01'),)).fetchone())
            self.assertTrue(db.execute('SELECT 1 FROM checks WHERE notice = 3').fetchone())
        self.run_history()
        with contextlib.closing(sqlite3.connect(self.out)) as db:
            self.assertEqual(db.execute("SELECT value FROM meta WHERE key = 'checks_ready'").fetchone()[0], '1')
            self.assertEqual(db.execute('SELECT status FROM blocks WHERE start = ?',
                                       (history.day('2019-07-01'),)).fetchone()[0], 'done')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM checks').fetchone()[0], 8)

    def test_interrupted_source_batch_is_reread_without_claiming_coverage(self):
        row = ['20200701001', '001', '2020-07-01', 'd', '1234567890', '90', 'Y']
        self.write('2020-06-29', [row] * (history.BATCH + 2))
        original = history.encode
        seen = 0
        def interrupt(*args):
            nonlocal seen
            seen += 1
            if seen == history.BATCH + 1:
                raise RuntimeError('interrupted after first bid batch')
            return original(*args)
        with mock.patch.object(history, 'encode', side_effect=interrupt):
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                self.run_history()
        with contextlib.closing(sqlite3.connect(self.out)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM bids').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM loads').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM blocks').fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT value FROM meta WHERE key = 'checks_ready'").fetchone()[0], '0')
        self.run_history()
        with contextlib.closing(sqlite3.connect(self.out)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM bids').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM loads').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT b10, b11 FROM checks').fetchone(), (None, None))
            self.assertEqual(db.execute("SELECT DISTINCT status FROM blocks").fetchall(), [('pending',)])

    def test_candidates_use_notice_week_delay_and_api_opening_day(self):
        lo, hi = history.day('2020-07-01'), history.day('2020-09-30')
        files = [(Path('near'), 'hub', '2020-03-02'), (Path('old'), 'hub', '2020-02-24'),
                 (Path('day'), 'goods', '2020-07-01'), (Path('early'), 'goods', '2020-06-30'),
                 (Path('late'), 'hub', '2020-10-05')]
        self.assertEqual([p.name for p, _, _ in history.candidates(files, lo, hi)], ['near', 'day'])


if __name__ == '__main__':
    unittest.main()
