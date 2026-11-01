"""Group measures per rival and the same-rival pairs (korea-labels-plan.md, amendment 2026-10-27), on synthetic data."""
import gzip
import importlib.util
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gm = load('korea_group_measures', 'tools/korea-group-measures.py')
gp = load('korea_group_pairs', 'tools/korea-group-pairs.py')
DAY = 740000
A, B, C, D = 1, 2, 3, 4  # A wins the target; B is its cover bidder, C a rival that only meets D


class PerRivalMeasures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = gm.connect(Path(self.tmp.name) / 'h.sqlite')
        openings = [(100, DAY, A, {A: 87.0, B: 88.0, C: 90.0})]  # target
        openings += [(101 + k, DAY - 50 + 10 * k, A, {A: 86.0 + k, B: 87.0 + k}) for k in range(4)]
        openings += [(110 + k, DAY + 20 + 10 * k, D, {D: 85.0, C: 89.0}) for k in range(3)]
        for notice, day, winner, bids in openings:
            self.db.execute('INSERT INTO openings VALUES (?, 1, ?, 7, ?, 1, ?)', (notice, day, len(bids), winner))
            for firm, rate in bids.items():
                self.db.execute('INSERT INTO bids VALUES (?, 1, ?, 7, ?, ?, NULL, ?, 0)',
                                (notice, day, firm, int(rate * 1000), int(firm == winner)))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_rivals_and_opening_level(self):
        rows, rivals = gm.measures(self.db, 7, [(100, 1, DAY, 1, A)], DAY - 400, DAY + 400)
        per = {r: (g1, g3, g5) for _, _, r, g1, g3, g5 in rivals}
        self.assertEqual(set(per), {B, C})
        # N = 7 other openings; A and B meet in all 4 of A's: 4 / (4 * 4 / 7 + 1)
        self.assertAlmostEqual(per[B][0], 4 / (16 / 7 + 1))
        self.assertEqual(per[C][0], 0.0)
        self.assertEqual(per[B][1], 1.0)  # B bid 4 times, never won, lost every one to A
        self.assertEqual(per[C][1], 0.0)  # C never won but never met A
        self.assertAlmostEqual(per[B][2], 0.0)  # B always bids 1 point above A
        self.assertEqual(per[C][2], gm.NO_PAIR)
        notice, order, g1, g2, g3, g4, g5 = rows[0]
        self.assertEqual((g1, g3, g5), (per[B][0], 1.0, per[B][2]))

    def test_rival_rows_flags(self):
        rivals = [('B', '', False), ('C', '예가초과', False)]
        hist = {'B': [2.0, 1.0, 0.0], 'E': [0.5, 0.0, gm.NO_PAIR]}
        picks = {'A': (1, 2), 'B': (1, 2), 'C': (3, 4)}
        contacts = {'A': {('tel', '0212345678')}, 'B': {('tel', '0212345678')}, 'C': {('adr', 'x')}}
        out = dict(gm.rival_rows(None, 'A', rivals, hist, picks, True, contacts, {'A', 'B', 'C'}, True, {'C'}, True))
        self.assertEqual(out['B'], [2.0, 1.0, 0.0, 0.0, 1.0, 1.0, 0.0])
        self.assertEqual(out['C'], [None, None, None, 1.0, 0.0, 0.0, 1.0])
        self.assertEqual(out['E'], [0.5, 0.0, gm.NO_PAIR, None, None, None, None])  # history only: no flags
        unknown = dict(gm.rival_rows(None, 'A', rivals, {}, picks, False, contacts, {'A'}, False, set(), False))
        self.assertEqual(unknown['B'][3:], [0.0, None, None, None])


class SameRivalPairs(unittest.TestCase):
    def write(self, folder, measures, rivals):
        m, r = folder / 'measures.tsv', folder / 'rivals.tsv.gz'
        head = ['notice', 'ord', *gm.COLUMNS]
        m.write_text('\t'.join(head) + '\n' + ''.join('\t'.join(row) + '\n' for row in measures))
        with gzip.open(r, 'wt') as f:
            f.write('notice\tord\trival\t' + '\t'.join(gm.RIVAL_COLUMNS) + '\n')
            f.writelines('\t'.join(row) + '\n' for row in rivals)
        return head, [row for row in measures], r

    def test_split_rivals_do_not_pair(self):
        # T1: rival X has the top G1 but no cover, Y the top cover but low G1; T2: one rival has both.
        # Any-rival P1 rates T1 like T2; same-rival P1 rates T1 lower.
        def row(notice, g1, g3):
            return [notice, '001', g1, '', g3] + [''] * 6  # G1, G2, G3, then G4-G10 unknown
        measures = [row('T1', '9', '1'), row('T2', '9', '1'), row('T3', '0', '0'), row('T4', '', '')]
        rivals = [['T1', '001', 'X', '9', '0', '1000', '1', '', '', ''],
                  ['T1', '001', 'Y', '0.1', '1', '1000', '0', '', '', ''],
                  ['T2', '001', 'Z', '9', '1', '1000', '', '', '', ''],
                  ['T4', '001', 'X', '', '', '', '0', '', '', '']]
        with tempfile.TemporaryDirectory() as tmp:
            head, rows, path = self.write(Path(tmp), measures, rivals)
            same = gp.same_rival(head, rows, path)
            loose = gp.any_rival(head, rows)
        self.assertEqual(loose['P1'][0], loose['P1'][1])
        self.assertLess(same['P1'][0], same['P1'][1])
        self.assertGreater(same['P3'][0], 0)  # X bid futile with the top G1
        self.assertTrue(math.isnan(same['P3'][1]))  # Z's futile flag unknown
        self.assertEqual((same['P1'][2], same['P3'][2]), (0.0, 0.0))  # G1 known, no rival
        self.assertTrue(math.isnan(same['P1'][3]))  # no history
        self.assertTrue(math.isnan(same['P4'][0]))  # no picks anywhere

    def test_flag_pairs(self):
        nan = float('nan')
        s = gp.rival_scores(0.9, 0.2, 0.8, 1.0, 1.0, 1.0, 0.0)
        self.assertEqual((s['P1'], s['P2'], s['P3'], s['P4'], s['P5'], s['P6']), (0.2, 0.8, 0.9, 0.8, 1.0, 0.0))
        s = gp.rival_scores(nan, 0.2, 0.8, 0.0, 0.0, nan, 1.0)
        self.assertTrue(all(math.isnan(s[p]) for p in ('P1', 'P2', 'P3', 'P5', 'P6')))
        self.assertEqual(s['P4'], 0.0)


if __name__ == '__main__':
    unittest.main()
