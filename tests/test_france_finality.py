import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('france_finality', Path(__file__).resolve().parents[1] / 'tools/france-finality.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
spec = importlib.util.spec_from_file_location('appeal_effects', Path(__file__).resolve().parents[1] / 'tools/extract-france-appeal-effects.py')
appeal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(appeal)


class FinalityTest(unittest.TestCase):
    def test_effects_and_unreviewed_pairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            rulings = base / 'rulings' / 'TA'
            rulings.mkdir(parents=True)
            later_dir = base / 'rulings' / 'CAA'
            later_dir.mkdir()
            links, effect_rows = [], []
            for n in range(1, 8):
                earlier = f'DTA_210000{n}_20220101'
                later = f'DCA_22AA0000{n}_20230101'
                (rulings / (earlier + '.xml')).write_text('<doc/>')
                (later_dir / (later + '.xml')).write_text(f'<doc>210000{n}</doc>')
                links.append({'ruling': earlier, 'class': 'A1'})
                if n != 4:
                    result = {'same_case': 'no' if n == 5 else 'yes',
                              'effect': {1: 'reversed', 2: 'confirmed', 3: 'not_examined',
                                         5: 'reversed', 6: 'partly_reversed', 7: 'reversed'}[n],
                              'earlier_final_after_this': 'yes'}
                    effect_rows.append({'earlier': earlier, 'later': later, 'result': result,
                                        'problems': ['bad quote'] if n == 7 else []})
            effects = base / 'effects'
            effects.mkdir()
            (effects / 'checked.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in effect_rows))
            lp = base / 'links.jsonl'
            lp.write_text(''.join(json.dumps(r) + '\n' for r in links))
            out = base / 'out'
            with contextlib.redirect_stdout(io.StringIO()):
                f.run(base, lp, out, effects)
            rows = {r['ruling']: r for r in map(json.loads, (out / 'finality.jsonl').read_text().splitlines())}
            statuses = [rows[x['ruling']]['status'] for x in links]
            self.assertEqual(statuses, ['overturned', 'upheld_by_later', 'upheld_by_later',
                                        'pending', 'final', 'pending', 'pending'])
            self.assertEqual(rows[links[0]['ruling']]['w'], 0)
            self.assertIn('DCA_22AA00004_20230101', (out / 'unread-appeals.txt').read_text())

    def test_pair_extractor_stub_and_quote_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            earlier, later = 'DTA_2100001_20220101', 'DCA_22AA00001_20230101'
            pair = earlier + '__' + later
            input_path = base / 'finality.jsonl'
            input_path.write_text(json.dumps({'ruling': earlier, 'class': 'A1',
                                              'later_rulings': [{'ruling': later}]}) + '\n')
            out = base / 'out'
            def stub_run(serial, model, effort, timeout, directory):
                work = directory / serial
                work.mkdir()
                (work / 'ruling.txt').write_text('=== EARLIER ===\nancien\n=== LATER ===\nPourvoi non admis')
                (work / 'status.json').write_text(json.dumps({'ok': True, 'model': model}))
                (work / 'result.json').write_text(json.dumps({'same_case': 'yes', 'effect': 'not_examined',
                    'earlier_final_after_this': 'yes', 'quote': 'Pourvoi non admis', 'confidence': 'high'}))
                return serial, 'ok', ''
            argv = ['extract', '--input', str(input_path), '--out', str(out), '--model', 'opencode/stub', '--only', earlier]
            with patch('sys.argv', argv), patch.object(appeal.kor, 'run_one', side_effect=stub_run) as runner, contextlib.redirect_stdout(io.StringIO()):
                appeal.main()
                appeal.main()
            self.assertEqual(runner.call_count, 1)
            row = json.loads((out / 'checked.jsonl').read_text())
            self.assertEqual((row['earlier'], row['later'], row['problems']), (earlier, later, []))
            result = out / pair / 'result.json'
            data = json.loads(result.read_text())
            data['quote'] = 'ancien'
            result.write_text(json.dumps(data))
            with contextlib.redirect_stdout(io.StringIO()):
                appeal.check(out)
            self.assertIn('quote missing or not in later ruling.txt', json.loads((out / 'checked.jsonl').read_text())['problems'])

    def test_long_excerpts_include_reference_and_operative_part(self):
        source = 'intro\n' + ('padding\n' * 15000) + 'Le jugement 2100001 est cité.\n' + ('other\n' * 15000) + 'DÉCIDE :\nArticle 1 : rejet.\n'
        excerpt = appeal.excerpt(source, 'DTA_2100001_20220101')
        self.assertLess(len(excerpt), 46000)
        self.assertIn('2100001 est cité', excerpt)
        self.assertIn('Article 1 : rejet', excerpt)

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
