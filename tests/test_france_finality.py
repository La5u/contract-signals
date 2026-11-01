import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('france_finality', Path(__file__).resolve().parents[1] / 'tools/france-finality.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


class FinalityTest(unittest.TestCase):
    def test_corpus_and_readings(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            links = []

            def xml(rid, text=''):
                level = {'DTA': 'TA', 'DCA': 'CAA', 'DCE': 'CE'}[rid[:3]]
                path = base / 'rulings' / level / (rid + '.xml')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('<Document><Texte>' + text + '</Texte></Document>')

            def link(rid, cls='A1'):
                links.append({'ruling': rid, 'class': cls})
                xml(rid)

            link('DTA_2100001_20220101')
            link('DTA_2100002_20220101')
            link('DTA_2100003_20220101')
            link('DCA_21AA00004_20220101')
            link('DCE_400005_20220101')
            link('DTA_2100006_20251201')
            xml('DCA_22AA00001_20230101', 'jugement numero 2100001')
            xml('DCA_22AA00002_20230101', 'jugement numero 2100002')
            xml('DCA_22AA00003_20230101', 'jugement numero 2100003')
            xml('DCE_400004_20230101', 'arrêt numero 21AA00004')
            link('DTA_2100007_20220101')
            link('DTA_2100008_20220101')
            xml('DCA_22AA00009_20230101', 'jugement numero 2100008')
            xml('DTA_2100009_20260101', 'malformed & source')
            xml('DCA_22AA00008_20240101', 'jugement numero 2100001')
            readings = [
                {'id': 'DCA_22AA00009_20230101', 'result': {'outcome_class': 'A2'}},
                {'id': 'DCA_22AA00001_20230101', 'result': {'outcome_class': 'A2'}},
                {'id': 'DCA_22AA00002_20230101', 'result': {'outcome_class': 'C'}},
                {'id': 'DCE_400004_20230101', 'result': {'outcome_class': 'X'}},
                {'id': 'DCA_22AA00008_20240101', 'model': 'terra', 'result': {'outcome_class': 'X',
                 'relevant_reason': "La cour statue sur le montant de l'indemnisation après un précédent arrêt ayant tranché l'irrégularité."}},
            ]
            path = base / 'extract-terra' / 'checked.jsonl'
            path.parent.mkdir()
            path.write_text(''.join(json.dumps(r) + '\n' for r in readings))
            lp = base / 'links.jsonl'
            lp.write_text(''.join(json.dumps(r) + '\n' for r in links + links[:1]))
            out = base / 'out'
            with contextlib.redirect_stdout(io.StringIO()):
                f.run(base, lp, out)
            rows = {r['ruling']: r for r in map(json.loads, (out / 'finality.jsonl').read_text().splitlines())}
            self.assertEqual(len(rows), 8)
            self.assertEqual(rows['DTA_2100007_20220101']['status'], 'final')
            self.assertEqual(rows['DTA_2100008_20220101']['status'], 'upheld_by_later')
            self.assertEqual(rows['DTA_2100001_20220101']['status'], 'pending')
            self.assertEqual(rows['DTA_2100002_20220101']['status'], 'overturned')
            self.assertEqual(rows['DTA_2100003_20220101']['w'], .91)
            self.assertEqual(rows['DCA_21AA00004_20220101']['w'], .85)
            self.assertEqual(rows['DCE_400005_20220101']['status'], 'final')
            self.assertEqual(rows['DTA_2100006_20251201']['status'], 'pending')
            self.assertIn('DTA_2100009_20260101', (out / 'malformed-xml.txt').read_text())
            self.assertIn('DCA_22AA00003_20230101', (out / 'unread-appeals.txt').read_text())
            self.assertIn('DTA_2100001_20220101', (out / 'damages-only.tsv').read_text())
            self.assertEqual(f.identity('ORCA_23NC00842_20230424')['level'], 'CAA')
            self.assertEqual(f.six_months(f.dt.date(2024, 8, 31)), f.dt.date(2025, 2, 28))


if __name__ == '__main__':
    unittest.main()
