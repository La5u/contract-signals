"""Offline document queue: deterministic scopes, real app scoring, privacy, freeze."""
import copy
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('document_review', ROOT / 'tools/prepare-document-review.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


# The six-row plan was frozen on this city snapshot. The cohort was later re-keyed
# (rows sharing a DECP id split into distinct contracts), which removed the
# 'initial-conflict' stratum from live data, so selection is re-derived from the
# frozen-time file, pinned by commit and SHA-256.
FROZEN_CITIES = ('581fe2c98e64e66ed5fd3964f599115f8e42767f', 'data/decp-cities.json',
                 'd5126b0742d27858d68acc4b63c7a967db9653fd7cfbd96e1bfef6c98cfd1184')


def frozen_available():
    """The frozen-time city file lives in git history; shallow CI checkouts do not have it."""
    commit, relative, _ = FROZEN_CITIES
    return subprocess.run(['git', 'cat-file', '-e', f'{commit}:{relative}'], cwd=ROOT, capture_output=True).returncode == 0


def frozen_root(tmp):
    root = Path(tmp)
    for relative in ['script.js', *m.DATASETS.values()]:
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_bytes((ROOT / relative).read_bytes())
    commit, relative, sha = FROZEN_CITIES
    blob = subprocess.run(['git', 'show', f'{commit}:{relative}'], cwd=ROOT, capture_output=True, check=True).stdout
    if m.digest(blob) != sha:
        raise AssertionError('Frozen city snapshot hash mismatch')
    (root / relative).write_bytes(blob)
    return root


@unittest.skipUnless(frozen_available(), 'frozen-time city snapshot not in this checkout (shallow clone)')
class DocumentReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = frozen_root(cls.tmp.name)
        cls.plan = m.build_plan(cls.root)
        cls.datasets = {key: json.loads((cls.root / path).read_bytes()) for key, path in m.DATASETS.items()}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_deterministic_actual_scope_and_hash(self):
        self.assertEqual(self.plan, m.build_plan(self.root))
        m.verify_hash(self.plan)
        self.assertEqual(len(self.plan['rows']), 6)
        self.assertEqual(self.plan['emptyStrata'], [])
        self.assertEqual([r['stratum'] for r in self.plan['rows']], [s[0] for s in m.STRATA])
        identities = [(r['dataset'], r['rowId']) for r in self.plan['rows']]
        self.assertEqual(len(set(identities)), 6)
        for row, (_, scope) in zip(self.plan['rows'], m.STRATA):
            self.assertIn(row['dataset'], scope)
            original = next(r for r in self.datasets[row['dataset']] if r['id'] == row['rowId'])
            self.assertEqual(row['matchingIds'], {k: original[k] for k in m.ID_FIELDS if original.get(k) is not None})
            self.assertEqual(row['published'], {k: original.get(k) for k in m.VALUE_FIELDS})
            snapshot = row['sourceSnapshot']
            self.assertEqual(snapshot['sha256'], m.digest((self.root / snapshot['path']).read_bytes()))
        changed = copy.deepcopy(self.plan)
        changed['rows'][0]['published']['amount'] += 1
        with self.assertRaises(ValueError):
            m.verify_hash(changed)
        self.assertEqual(self.plan['scoring']['scriptSha256'], m.digest((self.root / 'script.js').read_bytes()))

    def test_independent_node_app_preparation_and_lexicographic_selection(self):
        # Independently load complete files in Node, using fresh preparation per
        # dataset exactly as loadDataset does. Do not prepare only six selected rows.
        code = r"""
const fs=require('node:fs'),vm=require('node:vm');
const ctx=vm.createContext({URL});vm.runInContext(fs.readFileSync('script.js','utf8'),ctx);
const paths=JSON.parse(process.argv[1]),out={};
for(const [key,path] of Object.entries(paths)) {
 ctx.rows=JSON.parse(fs.readFileSync(path,'utf8'));
 out[key]=vm.runInContext('prepareContracts(rows).map(c=>({id:c.id,score:getVigilanceScore(c),excluded:!!getAssessment(c).excludedReason,evaluated:getAssessment(c).evaluated}))',ctx);
}
console.log(JSON.stringify(out));
"""
        actual = json.loads(subprocess.run(['node', '-e', code, json.dumps(m.DATASETS)],
                                           cwd=self.root, text=True, capture_output=True, check=True).stdout)
        used = set()
        for row, (stratum, scope) in zip(self.plan['rows'], m.STRATA):
            candidates = []
            for dataset in scope:
                index = {r['id']: r for r in actual[dataset]}
                for original in self.datasets[dataset]:
                    score = index[original['id']]
                    minimal = {'score': score['score'], 'assessment': {'excluded': score['excluded']}}
                    if (dataset, original['id']) not in used and m.eligible(stratum, original, minimal):
                        candidates.append((dataset, original['id']))
            self.assertEqual((row['dataset'], row['rowId']), min(candidates))
            used.add((row['dataset'], row['rowId']))
            scored = next(r for r in actual[row['dataset']] if r['id'] == row['rowId'])
            self.assertEqual(row['score'], scored['score'])
            self.assertEqual(row['assessment']['evaluated'], scored['evaluated'])
            self.assertEqual(row['assessment']['excluded'], scored['excluded'])

    def test_zero_missing_conflict_and_document_semantics(self):
        rows = {r['stratum']: r for r in self.plan['rows']}
        self.assertGreater(rows['scored-flagged-positive']['published']['amount'], 0)
        self.assertGreater(rows['scored-flagged-positive']['score'], 0)
        self.assertGreater(rows['scored-zero-positive']['published']['amount'], 0)
        self.assertEqual(rows['scored-zero-positive']['score'], 0)
        self.assertEqual(rows['declared-zero']['published']['amount'], 0)
        self.assertTrue(rows['declared-zero']['officialUrls'])
        self.assertIsNone(rows['missing-amount']['published']['amount'])
        conflict = rows['initial-conflict']
        self.assertTrue(conflict['initialConflicts'])
        self.assertTrue(conflict['assessment']['excluded'])
        self.assertIsNone(conflict['score'])
        self.assertTrue(rows['published-contractSigned']['officialUrls']['signedDocumentUrls'])
        unknown = {'score': None, 'assessment': {'excluded': False}}
        self.assertFalse(m.eligible('scored-zero-positive', {'amount': 1}, unknown))
        self.assertFalse(m.eligible('missing-amount', {'amount': 0, 'dataFamily': 'boamp'}, unknown))
        self.assertTrue(m.eligible('missing-amount', {'dataFamily': 'fts'}, unknown))
        self.assertFalse(m.eligible('declared-zero', {'amount': False}, unknown))

    def test_privacy_allowlists_and_no_severity_hunting(self):
        datasets = {key: [] for key in m.DATASETS}
        scores = {key: {} for key in m.DATASETS}
        for rid, score in [('z', 99), ('a', 1)]:
            datasets['boamp'].append({'id': rid, 'amount': 1, 'supplier': 'SECRET PERSON',
                                      'supplierIds': [{'id': 'SECRET ID'}],
                                      'description': 'SECRET DESCRIPTION',
                                      'sourceReference': 'SECRET REFERENCE',
                                      'source': 'https://evil.example/SECRET',
                                      'history': [{'supplierId': 'SECRET HISTORY'}],
                                      'sourceRowVariants': [{'secret': 'RAW SECRET'}]})
            scores['boamp'][rid] = {'score': score, 'assessment': {'excluded': False}}
        rows, empty = m.select_rows(datasets, scores, {key: {} for key in datasets})
        self.assertEqual([r['rowId'] for r in rows], ['a'])
        self.assertEqual(len(empty), 5)
        self.assertNotIn('SECRET', json.dumps(rows))
        self.assertEqual(rows[0]['officialUrls'], {})
        for row in self.plan['rows']:
            self.assertNotIn('supplier', row)
            self.assertNotIn('supplierIds', row['matchingIds'])
            self.assertTrue(set(row['matchingIds']) <= set(m.ID_FIELDS))
            for check in row['assessment']['checks']:
                self.assertTrue(set(check) <= {'id', 'status', 'applicability'})
            source = next(r for r in self.datasets[row['dataset']] if r['id'] == row['rowId'])
            for key in ('supplier', 'description', 'sourceReference'):
                if source.get(key):
                    self.assertNotIn(source[key], json.dumps(row, ensure_ascii=False))

    def test_immutable_private_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'private' / 'plan.json'
            self.assertTrue(m.freeze(self.plan, path))
            before = path.read_bytes(), path.stat().st_mtime_ns
            self.assertFalse(m.freeze(self.plan, path))
            self.assertEqual(before, (path.read_bytes(), path.stat().st_mtime_ns))
            self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o400)
            different = copy.deepcopy(self.plan)
            different['protocolVersion'] = 'new-version'
            different.pop('planSha256')
            different['planSha256'] = m.digest(m.canonical(different))
            with self.assertRaisesRegex(ValueError, 'Refusing to overwrite'):
                m.freeze(different, path)
            self.assertEqual(path.read_bytes(), before[0])
            path.chmod(0o600)
            corrupted = copy.deepcopy(self.plan)
            corrupted['rows'] = []
            path.write_text(json.dumps(corrupted))
            with self.assertRaisesRegex(ValueError, 'invalid plan hash'):
                m.freeze(self.plan, path)


if __name__ == '__main__':
    unittest.main()
