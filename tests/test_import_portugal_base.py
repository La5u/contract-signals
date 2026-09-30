"""Tiny, offline synthetic BASE fixtures only; never read national archives."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('import_portugal_base', ROOT / 'tools/import-portugal-base.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
BUYER = '503933813'
OTHER = '508779472'
SUPPLIER_ID = '123456789'
COMPETITOR_ID = '987654321'


def plan_fixture():
    return {'dataset': 'https://dados.gov.pt/datasets/synthetic-base',
            'buyerNifs': [BUYER, OTHER],
            'window': {'startInclusive': '2024-09-01', 'endExclusive': '2026-09-01'},
            'resources': []}


def row_fixture(**changes):
    row = {'idcontrato': '00042', 'adjudicante': [f'{BUYER} - Public buyer'],
           'adjudicatarios': [f'{SUPPLIER_ID} - Name, é & Sons'],
           'concorrentes': [f'{COMPETITOR_ID} - Competitor private name'],
           'dataPublicacao': '01/09/2024', 'dataCelebracaoContrato': '31/08/2024',
           'dataDecisaoAdjudicacao': '29/02/2024', 'dataFechoContrato': '31/02/2025',
           'precoContratual': 0, 'prazoExecucao': 12,
           'cpv': ['45000000-7 - Construction'], 'descContrato': 'Published subject',
           'objectoContrato': 'Fallback subject', 'Observacoes': 'Unneeded private text'}
    row.update(changes)
    return row


def collect_rows(rows):
    plan = plan_fixture()
    provenance = [{'year': year, 'bytes': 1, 'sha256': 'a' * 64} for year in base.YEARS]
    candidate, coverage = base.collect([(2024, iter(rows)), (2025, iter([])), (2026, iter([]))], plan, provenance)
    base.validate_candidate(candidate, plan)
    base.validate_coverage(coverage, candidate, plan, provenance)
    return candidate, coverage


class StreamingTests(unittest.TestCase):
    def parse(self, blob, **kwargs):
        return list(base.iter_json_array(io.BytesIO(blob), **kwargs))

    def test_quote_escape_unicode_and_bom_in_tiny_chunks(self):
        rows = [{'text': 'é € 漢字 \\ " braces } ], [', 'nested': [{'x': None}]}, {'n': 0}]
        blob = b'\xef\xbb\xbf' + json.dumps(rows, ensure_ascii=False).encode()
        for chunk in (1, 2, 3, 7, 64):
            with self.subTest(chunk=chunk):
                self.assertEqual(self.parse(blob, chunk_bytes=chunk), rows)

    def test_empty_and_whitespace(self):
        self.assertEqual(self.parse(b' \r\n[ \t] \n', chunk_bytes=1), [])

    def test_no_silent_truncation_or_missing_delimiters(self):
        invalid = [b'', b'[', b'[{}', b'[{},', b'[{},]', b'[{} {}]', b'[{}]x',
                   b'[{}][]', b'{}', b'[1]', b'[null]', b'[{"x":}]', b'[{"x":[}]',
                   b'[{"x":"unterminated}]', b'[{"x":NaN}]', b'[{"x":Infinity}]',
                   b'[{"x":1,"x":2}]', b'[{"x":"\xff"}]', b'\xef\xbb']
        for blob in invalid:
            with self.subTest(blob=blob):
                with self.assertRaises(ValueError):
                    self.parse(blob, chunk_bytes=2)

    def test_record_and_depth_limits(self):
        self.assertEqual(self.parse(b'[{}]', record_max=2), [{}])
        with self.assertRaises(ValueError):
            self.parse(b'[{"text":"long"}]', record_max=10, chunk_bytes=2)
        with self.assertRaises(ValueError):
            self.parse(b'[{"nested":[[]]}]', max_depth=2)
        self.assertEqual(self.parse(b'[{"nested":[[]]}]', max_depth=3), [{'nested': [[]]}])
        with self.assertRaises(ValueError):
            self.parse(b'[]', chunk_bytes=base.CHUNK_BYTES + 1)

    def test_never_requests_large_reads(self):
        class Bounded(io.BytesIO):
            def read(self, size=-1):
                self_test.assertGreater(size, 0)
                self_test.assertLessEqual(size, base.CHUNK_BYTES)
                return super().read(size)
        self_test = self
        self.assertEqual(list(base.iter_json_array(Bounded(b'[{}]'))), [{}])


class NormalizationTests(unittest.TestCase):
    def test_exact_minimized_unverified_record(self):
        candidate, report = collect_rows([row_fixture()])
        row = candidate[0]
        self.assertEqual(row['id'], 'base-00042')
        self.assertEqual(row['contractId'], '00042')
        self.assertEqual(row['amount'], 0)
        self.assertIsNone(row['currency'])
        self.assertIsNone(row['durationMonths'])
        self.assertIsNone(row['offers'])
        self.assertIsNone(row['directAward'])
        self.assertEqual(row['baseDurationOriginal'], {'value': 12, 'unit': 'unknown'})
        self.assertEqual(row['baseSigningDate'], '2024-08-31')
        self.assertEqual(row['baseAwardDate'], '2024-02-29')
        self.assertIsNone(row['baseClosureDate'])
        self.assertEqual(row['supplierNamesPublished'], ['Name, é & Sons'])
        self.assertEqual(row['primarySource'], plan_fixture()['dataset'])
        self.assertEqual(row['sourceReference'], 'BASE contract 00042')
        self.assertEqual(row['assessmentMode'], 'browse')
        self.assertEqual(row['dataStatus'], 'unverified')
        self.assertNotIn('dataFamily', row)
        self.assertEqual(row['raw'], {'descContrato': 'Published subject'})
        text = json.dumps(candidate, ensure_ascii=False)
        for unwanted in (SUPPLIER_ID, COMPETITOR_ID, 'Competitor private name', 'concorrentes',
                         'supplierIds', 'Observacoes', 'Unneeded private text', 'Fallback subject'):
            self.assertNotIn(unwanted, text)
        report_text = json.dumps(report)
        for unwanted in ('Public buyer', 'Name,', SUPPLIER_ID, COMPETITOR_ID, 'Published subject'):
            self.assertNotIn(unwanted, report_text)

    def test_published_company_and_individual_names_are_both_retained(self):
        candidate, _ = collect_rows([row_fixture(adjudicatarios=[
            '123456789 - Fictional individual', '512345678 - Fictional company - Services'
        ])])
        self.assertEqual(candidate[0]['supplierNamesPublished'], ['Fictional individual', 'Fictional company - Services'])
        self.assertEqual(candidate[0]['supplier'], 'Fictional individual / Fictional company - Services')
        self.assertNotIn('123456789', json.dumps(candidate))
        self.assertNotIn('512345678', json.dumps(candidate))
        self.assertNotIn('supplierType', candidate[0])

    def test_explorer_schema_source_dates_and_text_notes(self):
        candidate, _ = collect_rows([row_fixture()])
        row = candidate[0]
        self.assertEqual(row['source'], plan_fixture()['dataset'])
        self.assertEqual(row['source'], row['primarySource'])
        self.assertEqual(row['sourceLabel'], 'Official BASE dataset · search by contract identifier')
        self.assertEqual(row['publicationDate'], '2024-09-01')
        self.assertEqual(row['date'], row['publicationDate'])
        self.assertEqual(row['dateNote'], 'Source dataPublicacao: publication date, not signing or award date.')
        self.assertIsInstance(row['notes'], str)
        self.assertEqual(row['notes'], ' '.join(base.NOTES))
        # Exercise the actual explorer validator, not a Python approximation of its schema.
        subprocess.run(['node', '-e', '''
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const ctx = vm.createContext({URL});
vm.runInContext(fs.readFileSync('script.js', 'utf8'), ctx);
ctx.rows = JSON.parse(fs.readFileSync(0, 'utf8'));
vm.runInContext('validateContracts(rows)', ctx);
const prepared = vm.runInContext('prepareContracts(rows)', ctx);
ctx.record = prepared[0];
assert.equal(vm.runInContext('getVigilanceScore(record)', ctx), null);
assert.equal(vm.runInContext('getIndicators(record).length', ctx), 0);
const exported = vm.runInContext('exportRecord(record)', ctx);
assert.equal(exported.supplier, ctx.record.supplier);
assert.equal(exported.supplierIds, null);
assert.equal(exported.currency, null);
assert.equal(exported.source, ctx.record.source);
for (const value of ['123456789', '987654321', 'Competitor private name']) assert.ok(!JSON.stringify(exported).includes(value));
for (const description of [null, '', '   ']) {
  ctx.rows[0].description = description;
  assert.throws(() => vm.runInContext('validateContracts(rows)', ctx), /missing description/);
}
'''], input=base.json_bytes(candidate), cwd=ROOT, check=True, capture_output=True)
        for key, value in [('source', 'BASE'), ('sourceLabel', 'wrong'), ('dateNote', 'wrong'),
                           ('notes', base.NOTES), ('date', row['baseSigningDate']),
                           ('description', None), ('description', '   ')]:
            with self.subTest(key=key, value=value):
                altered = copy.deepcopy(candidate)
                altered[0][key] = value
                with self.assertRaises(ValueError):
                    base.validate_candidate(altered, plan_fixture())
        for key in ('description', 'date', 'sourceLabel', 'dateNote'):
            with self.subTest(missing=key):
                altered = copy.deepcopy(candidate)
                del altered[0][key]
                with self.assertRaises(ValueError):
                    base.validate_candidate(altered, plan_fixture())

    def test_missing_or_identifier_subject_requires_private_review(self):
        for subject in (None, '', '   ', 42, f'Subject with {SUPPLIER_ID}'):
            with self.subTest(subject=subject):
                row = row_fixture(descContrato=subject, objectoContrato=None)
                with self.assertRaisesRegex(ValueError, '^subject$'):
                    base.normalize(row, plan_fixture(), [(BUYER, 'Public buyer')], [BUYER])
                candidate, report = collect_rows([row])
                self.assertEqual(candidate, [])
                self.assertEqual(report['normalizationErrors'], {'subject': 1})
                self.assertEqual(report['reviewQueue'], [{'contractId': '00042', 'reason': 'normalization-rejected'}])
                self.assertNotIn(SUPPLIER_ID, json.dumps(report))
        # Names in the permitted subject are retained, not silently blanked.
        candidate, _ = collect_rows([row_fixture(descContrato='Services by Published Person')])
        self.assertEqual(candidate[0]['description'], 'Services by Published Person')

    def test_buyer_exact_and_multibuyer(self):
        rows = [row_fixture(adjudicante=[f'  {BUYER}  –  First', f'{OTHER} - Second']),
                row_fixture(idcontrato='43', adjudicante=['1503933813 - Not same NIF']),
                row_fixture(idcontrato='44', adjudicante=['503933814 - Not selected'])]
        candidate, report = collect_rows(rows)
        self.assertEqual(len(candidate), 1)
        self.assertEqual(candidate[0]['buyerNamesPublished'], ['First', 'Second'])
        self.assertEqual(candidate[0]['buyerIds'], sorted([BUYER, OTHER]))
        self.assertNotIn('buyerId', candidate[0])
        self.assertEqual(report['counts']['unknownBuyerRows'], 1)
        self.assertEqual(report['counts']['nonMatchingBuyerRows'], 1)
        self.assertEqual(report['completeness'], 'unknown')
        self.assertEqual(report['perBuyer'][BUYER]['extractedRows'], 1)
        self.assertEqual(report['perBuyer'][OTHER]['extractedRows'], 1)

    def test_unselected_cobuyer_ids_are_not_published(self):
        candidate, _ = collect_rows([row_fixture(adjudicante=[f'{BUYER} - Selected', '500051070 - Other public buyer'])])
        self.assertEqual(candidate[0]['buyerIds'], [BUYER])
        self.assertNotIn('buyerId', candidate[0])
        self.assertNotIn('500051070', json.dumps(candidate))

    def test_missing_and_partly_malformed_buyers(self):
        candidate, report = collect_rows([row_fixture(adjudicante=None), row_fixture(adjudicante=[]),
            row_fixture(adjudicante=[f'{BUYER} - Public buyer', 'invalid personal party text'])])
        self.assertEqual(candidate, [])
        self.assertEqual(report['counts']['unknownBuyerRows'], 2)
        self.assertEqual(report['counts']['buyerParseErrorRows'], 3)
        self.assertEqual(report['normalizationErrors'], {'buyer-shape': 1})
        self.assertEqual(report['completeness'], 'unknown')
        self.assertNotIn('invalid personal', json.dumps(report))

    def test_strict_calendar_dates_and_window_no_substitution(self):
        dates = ['01/09/2024', '31/08/2026', '01/09/2026', '31/08/2024',
                 '29/02/2025', '31/04/2025', '1/09/2024', '2024-09-01', None, '01/09/2024 ']
        rows = [row_fixture(idcontrato=str(index), dataPublicacao=value,
                            dataCelebracaoContrato='01/10/2024') for index, value in enumerate(dates)]
        candidate, report = collect_rows(rows)
        self.assertEqual(len(candidate), 2)
        self.assertEqual(report['counts']['outsideWindowRows'], 2)
        self.assertEqual(report['counts']['invalidPublicationDateRows'], 6)
        self.assertEqual(base.parse_date('29/02/2024'), '2024-02-29')
        self.assertIsNone(base.parse_date('00/01/2025'))

    def test_supplier_multiple_names_retained_no_party_type_guess(self):
        names = ['Name, é & Sons', 'Person "Published"  ']
        candidate, _ = collect_rows([row_fixture(adjudicatarios=[f'{SUPPLIER_ID} - {names[0]}', f'234567890 – {names[1]}'])])
        self.assertEqual(candidate[0]['supplierNamesPublished'], names)
        self.assertEqual(candidate[0]['supplier'], ' / '.join(names))
        self.assertNotIn('supplierType', candidate[0])

    def test_malformed_supplier_requires_review_without_leaking_identifier(self):
        values = [['123456789'], ['123456789 - '], ['12 - Person'],
                  ['123456789 - 234567890'], ['123456789 - 234567890 - Person'],
                  ['raw private name'], '123456789 - Person', [{}]]
        for value in values:
            with self.subTest(value=value):
                candidate, report = collect_rows([row_fixture(adjudicatarios=value)])
                self.assertEqual(candidate, [])
                self.assertEqual(report['normalizationErrors'], {'supplier-shape': 1})
                self.assertEqual(report['reviewQueue'], [{'contractId': '00042', 'reason': 'normalization-rejected'}])
                self.assertNotIn(SUPPLIER_ID, json.dumps(report))

    def test_amount_exact_field_numeric_only_and_selected_only(self):
        for value in (0, 0.5, 100):
            candidate, _ = collect_rows([row_fixture(precoContratual=value, PrecoTotalEfetivo=9999)])
            self.assertEqual(candidate[0]['amount'], value)
        for value in ('12', True, -1, float('nan'), float('inf'), {}):
            candidate, report = collect_rows([row_fixture(precoContratual=value)])
            self.assertEqual(candidate, [])
            self.assertEqual(report['normalizationErrors'], {'amount': 1})
        candidate, report = collect_rows([row_fixture(adjudicante=['111111111 - Other'], precoContratual='not a number')])
        self.assertEqual(report['normalizationErrors'], {})
        self.assertEqual(candidate, [])
        candidate, _ = collect_rows([row_fixture(precoContratual=None, prazoExecucao='12')])
        self.assertIsNone(candidate[0]['amount'])
        self.assertNotIn('baseDurationOriginal', candidate[0])

    def test_subject_fallback_and_cpv_conservative(self):
        candidate, _ = collect_rows([row_fixture(descContrato='  ', cpv=['45000000-7 - Works', '45000000'])])
        self.assertEqual(candidate[0]['raw'], {'objectoContrato': 'Fallback subject'})
        self.assertEqual(candidate[0]['cpv'], '45000000')
        for codes in (['45000000', '44000000'], ['45000000', 'unknown'], ['garbage 45000000'], [], None):
            candidate, _ = collect_rows([row_fixture(cpv=codes)])
            self.assertIsNone(candidate[0]['cpv'])

    def test_duplicate_identical_minimized_records_and_all_conflicts_omitted(self):
        first = row_fixture()
        duplicate = row_fixture(Observacoes='Different excluded raw text', concorrentes=['Other private text'])
        conflict = row_fixture(idcontrato='43', precoContratual=1)
        other = row_fixture(idcontrato='43', precoContratual=2)
        rows = [first, duplicate, conflict, other, copy.deepcopy(conflict)]
        candidate, report = collect_rows(rows)
        self.assertEqual([row['contractId'] for row in candidate], ['00042'])
        counts = report['counts']
        self.assertEqual(counts['nationalRows'], 5)
        self.assertEqual(counts['normalizedRows'], 5)
        self.assertEqual(counts['duplicateIdenticalRows'], 1)
        self.assertEqual(counts['conflictingRows'], 3)
        self.assertEqual(counts['extractedRows'], 1)
        self.assertEqual(report['reviewQueue'], [{'contractId': '43', 'reason': 'conflicting-variants'}])
        # A later identical row cannot resurrect an already-conflicting ID.
        reversed_candidate, _ = collect_rows(list(reversed(rows)))
        self.assertEqual(reversed_candidate, candidate)

    def test_cross_year_dedup_and_unique_minimized_byte_budget(self):
        plan = plan_fixture()
        provenance = [{'year': year, 'bytes': 1, 'sha256': 'a' * 64} for year in base.YEARS]
        row = row_fixture()
        minimized = base.normalize(row, plan, [(BUYER, 'Public buyer')], [BUYER])
        with mock.patch.object(base, 'MAX_CANDIDATE_BYTES', len(base.json_bytes(minimized)) + 1):
            candidate, report = base.collect([(2024, iter([row])), (2025, iter([row])), (2026, iter([]))], plan, provenance)
        self.assertEqual(len(candidate), 1)
        self.assertEqual(report['counts']['duplicateIdenticalRows'], 1)
        self.assertEqual([item['scannedRows'] for item in report['archives']], [1, 1, 0])
        base.validate_coverage(report, candidate, plan, provenance)

    def test_rejected_variant_blocks_normalized_same_id(self):
        candidate, report = collect_rows([row_fixture(), row_fixture(adjudicatarios=['malformed'])])
        self.assertEqual(candidate, [])
        self.assertEqual(report['counts']['conflictingRows'], 1)
        self.assertEqual(report['counts']['rejectedNormalizationRows'], 1)
        self.assertEqual({item['reason'] for item in report['reviewQueue']},
                         {'conflicting-variants', 'normalization-rejected'})

    def test_cohort_and_minimized_byte_guards(self):
        with mock.patch.object(base, 'MAX_COHORT', 1):
            with self.assertRaises(ValueError):
                collect_rows([row_fixture(), row_fixture(idcontrato='43')])
        with mock.patch.object(base, 'MAX_CANDIDATE_BYTES', 100):
            with self.assertRaises(ValueError):
                collect_rows([row_fixture()])


class PrivateWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='base-test-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.archives = self.directory / 'archives'
        self.archives.mkdir(mode=0o700)
        self.candidate = self.directory / 'candidate'
        self.outputs = self.directory / 'public-output'
        self.plan_path = self.directory / 'plan.json'
        self.downloads_path = self.directory / 'downloads.json'
        self.make_inputs()

    def make_inputs(self, malformed=False, fingerprint_error=False, wrong_member=False, empty=False):
        plan, downloads = plan_fixture(), {'downloads': []}
        for year in base.YEARS:
            filename = f'contratos{year}.zip'
            resource = {'year': year, 'filename': filename, 'url': f'https://dados.gov.pt/s/synthetic/{filename}',
                        'resourceId': f'synthetic-{year}'}
            path = self.archives / filename
            rows = [row_fixture()] if year == 2024 and not empty else []
            blob = base.json_bytes(rows)
            if malformed and year == 2026:
                blob = b'[{}'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr(f'Contratos{year}.json' if not wrong_member else 'wrong.json', blob)
            archive_blob = path.read_bytes()
            resource['expectedBytes'] = len(archive_blob)
            plan['resources'].append(resource)
            downloads['downloads'].append({**resource, 'status': 'downloaded', 'bytes': len(archive_blob),
                                           'sha256': 'b' * 64 if fingerprint_error else hashlib.sha256(archive_blob).hexdigest()})
        self.plan_path.write_bytes(base.json_bytes(plan))
        self.downloads_path.write_bytes(base.json_bytes(downloads))

    def extract(self):
        return base.extract(self.candidate, self.archives, self.plan_path, self.downloads_path)

    def publish(self, reviewer='Synthetic reviewer', digest=None):
        if digest is None:
            digest = hashlib.sha256((self.candidate / 'candidate.json').read_bytes()).hexdigest()
        return base.publish_reviewed(self.candidate, reviewer, digest, self.plan_path,
                                     self.downloads_path, self.outputs)

    def test_extract_sequential_zip_hashes_private_atomic_no_publication(self):
        manifest = self.extract()
        self.assertEqual(sorted(path.name for path in self.candidate.iterdir()),
                         ['candidate.json', 'coverage.json', 'manifest.json'])
        self.assertEqual(self.candidate.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(path.stat().st_mode & 0o777 == 0o600 for path in self.candidate.iterdir()))
        candidate_blob = (self.candidate / 'candidate.json').read_bytes()
        self.assertEqual(manifest['candidateSha256'], hashlib.sha256(candidate_blob).hexdigest())
        self.assertEqual(manifest['status'], 'candidate')
        self.assertEqual(manifest['dataStatus'], 'unverified')
        report = json.loads((self.candidate / 'coverage.json').read_bytes())
        self.assertEqual(report['status'], 'candidate')
        self.assertEqual(report['dataStatus'], 'unverified')
        self.assertEqual([entry['year'] for entry in report['archives']], list(base.YEARS))
        self.assertEqual([entry['scannedRows'] for entry in report['archives']], [1, 0, 0])
        self.assertFalse(self.outputs.exists())
        with self.assertRaises(ValueError):
            self.extract()

    def test_empty_private_candidate_valid_but_no_public_cohort(self):
        self.make_inputs(empty=True)
        manifest = self.extract()
        self.assertEqual(json.loads((self.candidate / 'candidate.json').read_bytes()), [])
        report = json.loads((self.candidate / 'coverage.json').read_bytes())
        self.assertEqual(report['status'], 'candidate')
        self.assertEqual(report['counts']['extractedRows'], 0)
        with self.assertRaisesRegex(ValueError, 'No public cohort'):
            self.publish(digest=manifest['candidateSha256'])
        self.assertFalse(self.outputs.exists())
        self.assertTrue((self.candidate / 'coverage.json').exists())

    def test_late_malformed_archive_or_hash_failure_leaves_no_partial_output(self):
        for options in ({'malformed': True}, {'fingerprint_error': True}, {'wrong_member': True}):
            with self.subTest(options=options):
                self.make_inputs(**options)
                with self.assertRaises(ValueError):
                    self.extract()
                self.assertFalse(self.candidate.exists())
                self.assertFalse(self.outputs.exists())

    def test_publish_reviewed_does_not_open_archives(self):
        manifest = self.extract()
        for path in self.archives.iterdir():
            path.unlink()
        with mock.patch.object(base, 'archive_rows', side_effect=AssertionError('must not scan')), \
             mock.patch.object(base.zipfile, 'ZipFile', side_effect=AssertionError('must not open ZIP')):
            review = self.publish(digest=manifest['candidateSha256'])
        self.assertEqual(review['reviewer'], 'Synthetic reviewer')
        self.assertEqual(review['candidateSha256'], manifest['candidateSha256'])
        self.assertEqual((self.outputs / 'portugal-base.json').read_bytes(),
                         (self.candidate / 'candidate.json').read_bytes())
        coverage = json.loads((self.outputs / 'portugal-base-coverage.json').read_bytes())
        self.assertEqual(coverage['publicationReview'], review)
        self.assertEqual(coverage['status'], 'reviewed')
        self.assertEqual(coverage['dataStatus'], 'unverified')
        private_report = json.loads((self.candidate / 'coverage.json').read_bytes())
        self.assertEqual(private_report['status'], 'candidate')
        self.publish()  # Exact idempotent retry permitted.

    def test_reviewer_and_explicit_hash_required_and_fingerprints_checked(self):
        self.extract()
        for reviewer, digest in [('', 'a' * 64), ('reviewer', ''), ('reviewer', 'a' * 64)]:
            with self.assertRaises(ValueError):
                base.publish_reviewed(self.candidate, reviewer, digest, self.plan_path, self.downloads_path, self.outputs)
        self.assertFalse(self.outputs.exists())
        with (self.candidate / 'candidate.json').open('ab') as stream:
            stream.write(b' ')
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse(self.outputs.exists())

    def test_coverage_and_current_provenance_fingerprints_checked(self):
        self.extract()
        with (self.candidate / 'coverage.json').open('ab') as stream:
            stream.write(b' ')
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse(self.outputs.exists())
        # Restore exactly, then change a small provenance document only.
        path = self.candidate / 'coverage.json'
        path.write_bytes(path.read_bytes()[:-1])
        with self.downloads_path.open('ab') as stream:
            stream.write(b' ')
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse(self.outputs.exists())

    def test_existing_differing_output_not_overwritten_even_if_other_file_absent(self):
        self.extract()
        self.outputs.mkdir()
        original = b'preexisting unrelated output\n'
        (self.outputs / 'portugal-base-coverage.json').write_bytes(original)
        with self.assertRaises(ValueError):
            self.publish()
        self.assertEqual((self.outputs / 'portugal-base-coverage.json').read_bytes(), original)
        self.assertFalse((self.outputs / 'portugal-base.json').exists())

    def test_publication_rolls_back_on_second_install_failure(self):
        self.extract()
        real_link = os.link
        calls = 0
        def interrupted(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('synthetic interruption')
            real_link(source, destination)
        with mock.patch.object(base.os, 'link', side_effect=interrupted):
            with self.assertRaises(OSError):
                self.publish()
        self.assertEqual(list(self.outputs.iterdir()), [])

    def rewrite_and_refingerprint(self, filename, mutate):
        path = self.candidate / filename
        value = json.loads(path.read_bytes())
        mutate(value)
        path.write_bytes(base.json_bytes(value))
        manifest_path = self.candidate / 'manifest.json'
        manifest = json.loads(manifest_path.read_bytes())
        field = 'candidateSha256' if filename == 'candidate.json' else 'coverageSha256'
        manifest[field] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_bytes(base.json_bytes(manifest))

    def test_whitelist_blocks_personal_fields_even_with_matching_hash(self):
        self.extract()
        self.rewrite_and_refingerprint('candidate.json', lambda rows: rows[0].update(supplierIds=[SUPPLIER_ID]))
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse(self.outputs.exists())

    def test_whitelist_blocks_extra_raw_and_false_verified_claims(self):
        self.extract()
        original = (self.candidate / 'candidate.json').read_bytes()
        for mutate in (lambda rows: rows[0]['raw'].update(concorrentes=['private']),
                       lambda rows: rows[0].update(dataStatus='verified'),
                       lambda rows: rows[0].update(dataFamily='international')):
            (self.candidate / 'candidate.json').write_bytes(original)
            self.rewrite_and_refingerprint('candidate.json', mutate)
            with self.assertRaises(ValueError):
                self.publish()
            self.assertFalse(self.outputs.exists())

    def test_report_whitelist_and_reconciliation(self):
        self.extract()
        self.rewrite_and_refingerprint('coverage.json', lambda report: report.update(rawName='private'))
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse(self.outputs.exists())

    def test_private_repository_and_webroot_guards(self):
        for path in (ROOT / 'candidate', Path('/var/www/candidate'), Path('/srv/www/candidate')):
            with self.assertRaises(ValueError):
                base.private_path(path)
        self.extract()
        self.candidate.chmod(0o755)
        with self.assertRaises(ValueError):
            self.publish()

    def test_manifest_and_record_reconciliation_cannot_be_bypassed(self):
        self.extract()
        self.rewrite_and_refingerprint('coverage.json', lambda report: report['counts'].update(extractedRows=2))
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse(self.outputs.exists())

    def test_private_document_symlink_rejected(self):
        self.extract()
        original = self.candidate / 'candidate.json'
        target = self.directory / 'outside.json'
        original.rename(target)
        original.symlink_to(target)
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse(self.outputs.exists())

    def test_default_cli_only_reads_plan_no_network_or_archive(self):
        out = io.StringIO()
        with mock.patch.object(base, 'PLAN', self.plan_path), \
             mock.patch.object(base, 'extract', side_effect=AssertionError('must not extract')), \
             mock.patch.object(base, 'publish_reviewed', side_effect=AssertionError('must not publish')), \
             mock.patch.object(base.zipfile, 'ZipFile', side_effect=AssertionError('must not read ZIP')), \
             mock.patch('socket.socket', side_effect=AssertionError('must not network')), \
             contextlib.redirect_stdout(out):
            self.assertEqual(base.main([]), 0)
        self.assertIn('Plan only', out.getvalue())
        self.assertFalse(self.candidate.exists())
        self.assertFalse(self.outputs.exists())


if __name__ == '__main__':
    unittest.main()
