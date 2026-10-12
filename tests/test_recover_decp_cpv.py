"""Offline CPV candidate tests; no network calls or production writes."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import gzip

SPEC = importlib.util.spec_from_file_location(
    'recover_decp_cpv', Path(__file__).resolve().parents[1] / 'tools/recover-decp-cpv.py')
cpv = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cpv)


class ResolveTests(unittest.TestCase):
    def test_exact_retained_mapping(self):
        self.assertEqual(cpv.resolve('03121210', {'03121210': {'03121210-0': []}}),
                         ('03121210-0', 'safe-exact-prefix'))

    def test_no_checksum_or_nearest_prefix(self):
        self.assertEqual(cpv.resolve('03121211', {'03121210': {'03121210-0': []}}),
                         (None, 'no-full-code-evidence'))

    def test_ambiguous_retained_is_unresolved(self):
        evidence = {'03121210': {'03121210-0': [], '03121210-1': []}}
        self.assertEqual(cpv.resolve('03121210', evidence)[1], 'ambiguous-full-codes')
        self.assertEqual(cpv.resolve('03121210', evidence, ['03121210-0'])[1],
                         'ambiguous-full-codes')

    def test_official_conflict_is_not_overridden(self):
        self.assertEqual(cpv.resolve('03121210', {'03121210': {'03121210-1': []}},
                                     ['03121210-0']), (None, 'ambiguous-full-codes'))

    def test_nonexistent_despite_retained_evidence(self):
        self.assertEqual(cpv.resolve('99999999', {'99999999': {'99999999-9': []}},
                                     ['03121210-0']), (None, 'nonexistent-in-vocabulary'))

    def test_ambiguous_official(self):
        self.assertEqual(cpv.resolve('03121210', {}, ['03121210-0', '03121210-1'])[1],
                         'ambiguous-full-codes')

    def test_placeholder(self):
        self.assertEqual(cpv.resolve('00000000', {'00000000': {'00000000-0': []}})[1],
                         'placeholder-prefix')


class VocabularyTests(unittest.TestCase):
    def test_main_vocabulary_only_and_duplicate_dedup(self):
        xml = b'<CPV_CODE><CPV CODE="03121210-0"/><CPV CODE="03121210-0"/></CPV_CODE>'
        self.assertEqual(cpv.parse_vocabulary(xml), ['03121210-0'])

    def test_invalid_or_supplementary_or_entities_rejected(self):
        for xml in (b'<CPV_CODE><CPV CODE="03121210"/></CPV_CODE>',
                    b'<CPV_CODE/>', b'<SUPPLEMENTARY><CPV CODE="03121210-0"/></SUPPLEMENTARY>',
                    b'<!DOCTYPE CPV_CODE><CPV_CODE><CPV CODE="03121210-0"/></CPV_CODE>'):
            with self.subTest(xml=xml), self.assertRaises(ValueError):
                cpv.parse_vocabulary(xml)

    def test_private_cache_guard(self):
        with self.assertRaises(ValueError):
            cpv.private_cache(cpv.ROOT / 'data/vocabulary')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'linked'
            p.symlink_to(Path(tmp), target_is_directory=True)
            with self.assertRaises(ValueError):
                cpv.private_cache(p / 'cache')


class ArtifactTests(unittest.TestCase):
    def fixture(self, root):
        for rel in cpv.RETAINED:
            rows = [{'codecpv': '03121210-0', 'description': 'PRIVATE-RAW'}]
            if 'feeds' in rel:
                rows = [{'codeCPV': '03121210'}, {'codeCPV': '03200000-8 extra'}]
            blob = json.dumps({'records': rows}).encode()
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(gzip.compress(blob, mtime=0) if rel.endswith('.gz') else blob)
        rows = [{'cpv': '03121210', 'supplier': 'PRIVATE-SUPPLIER', 'id': 'PRIVATE-ID'},
                {'cpv': '03200000'}, {'cpv': '99999999'}, {'cpv': '03121210-0'},
                {'cpv': '03121210-1'}, {'cpv': '03121210 extra'}, {'cpv': None},
                {'cpv': 3121210}]
        for rel in cpv.DATASETS:
            (root / rel).write_text(json.dumps(rows))
        archive = root / 'official.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('cpv_2008.xml', '<CPV_CODE><CPV CODE="03121210-0"/>'
                       '<CPV CODE="03200000-3"/></CPV_CODE>')
            z.writestr('code_cpv_suppl_2008.xml', '<CPV CODE="99999999-9"/>')
        return archive

    def test_deterministic_provenance_and_public_allowlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self.fixture(root)
            report = cpv.build(root, archive)
            self.assertEqual(report, cpv.build(root, archive))
            self.assertEqual(report['counts'], {'safe-exact-prefix': 4,
                                                'nonexistent-in-vocabulary': 2})
            self.assertEqual(report['existingCodeValidation'],
                             {'full-in-vocabulary': 2, 'full-not-in-vocabulary': 2,
                              'malformed': 2, 'missing-or-nonstring': 4})
            serialized = json.dumps(report)
            self.assertNotIn('PRIVATE', serialized)
            self.assertNotIn(str(root), serialized)
            c = report['candidates'][0]
            self.assertEqual(c['rowSha256'], cpv.row_hash(json.loads(
                (root / cpv.DATASETS[0]).read_text())[0]))
            self.assertEqual(c['candidateCpv'], '03121210-0')
            self.assertEqual(report['prefixMappings'][0]['observedFullCodes']['03121210-0'][0],
                             {'source': cpv.RETAINED[0], 'rowIndex': 0})
            self.assertIn('```json', cpv.render(report))

    def test_offline_absence_is_unknown_and_inputs_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            report = cpv.build(root)
            self.assertFalse(report['officialVocabularyUsed'])
            self.assertEqual(report['counts'], {'safe-exact-prefix': 2,
                                                'no-full-code-evidence': 4})
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_canonical_row_hash_ignores_key_order_not_values(self):
        self.assertEqual(cpv.row_hash({'a': 1, 'cpv': '03121210'}),
                         cpv.row_hash({'cpv': '03121210', 'a': 1}))
        self.assertNotEqual(cpv.row_hash({'cpv': '03121210'}),
                            cpv.row_hash({'cpv': '03121210-0'}))


if __name__ == '__main__':
    unittest.main()
