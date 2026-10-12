import copy
import gzip
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('public_evidence', ROOT / 'tools/build-public-link-evidence.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


class OfflineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.annotations = json.loads((ROOT / e.ANNOTATIONS).read_text())
        cls.ledger = e.build()

    def test_deterministic_repository_only(self):
        original = Path.read_bytes
        def guarded(path):
            self.assertTrue(path.resolve().is_relative_to(ROOT))
            return original(path)
        with patch.object(Path, 'read_bytes', guarded), patch.object(e.subprocess, 'Popen', side_effect=AssertionError('network forbidden')):
            self.assertEqual(e.render(e.build()), (ROOT / 'data/public-link-evidence.json').read_text())
            self.assertEqual(e.build(), self.ledger)

    def test_inventory_and_no_resolution(self):
        ledger = self.ledger
        self.assertEqual(len(ledger['pairs']), 9)
        self.assertEqual(len({p['boampId'] for p in ledger['pairs']}), 7)
        self.assertEqual(ledger['confirmed'], 0)
        self.assertEqual(ledger['resolved'], 0)
        self.assertEqual(len(ledger['liveRequests']), 14)
        conclusions = [p['conclusion'] for p in ledger['pairs']]
        self.assertEqual(conclusions.count('reference-pattern-supported-unconfirmed'), 5)
        self.assertEqual(conclusions.count('lot-compatible-unconfirmed'), 2)
        for p in ledger['pairs']:
            self.assertFalse(p['confirmed'])
            self.assertIsNone(p['resolution'])
            self.assertTrue(p['fields'])
            self.assertEqual(len(p['decodedStringSha256']), 64)

    def test_hash_pointer_reference_and_id_fail_closed(self):
        for change in ['source', 'pointer', 'reference', 'id', 'scalar', 'url']:
            a = copy.deepcopy(self.annotations)
            if change == 'source':
                a['sourceHashes']['data/contracts.json'] = '0' * 64
            elif change == 'pointer':
                a['pairs'][0]['normalizedDecpPointer'] = 'data/decp-history.json#/583'
            elif change == 'reference':
                a['pairs'][0]['publishedReference'] = 'invented'
            elif change == 'id':
                a['pairs'][0]['decpContractId'] = 'invented'
            elif change == 'url':
                a['pairs'][0]['boampUrl'] = 'https://evil.invalid/'
            else:
                a['pairs'][0]['fields'][0]['scalarSha256'] = '0' * 64
            with self.subTest(change=change), self.assertRaises(ValueError):
                e.build(annotations=a)

    def test_nonminimal_pointers_rejected(self):
        a = copy.deepcopy(self.annotations)
        a['pairs'][0]['fields'][0].update(scope='decp', pointer='/supplier')
        with self.assertRaises(ValueError):
            e.build(annotations=a)
        self.assertFalse(e.allowed_decoded(e.N + '/efac:LotTender/0/efac:TenderingParty/cbc:ID'))

    def test_synthetic_privacy_canaries(self):
        a = copy.deepcopy(self.annotations)
        canary = 'PRIVATE_PERSON_CANARY_email@example.invalid_SIGNATURE'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in a['sourceHashes']:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())
            for name in ['data/contracts.json', 'data/decp-history.json', 'data/decp-cities.json']:
                data = json.loads((root / name).read_bytes())
                for p in a['pairs']:
                    key = 'normalizedBoampPointer' if name.endswith('contracts.json') else 'normalizedDecpPointer'
                    f, ptr = p[key].split('#')
                    if f == name:
                        record = e.pointer(data, ptr)
                        record['supplier'] = canary
                        record['contact'] = {'name': canary, 'signature': canary}
                (root / name).write_text(e.render(data))
            name = 'data/boamp-raw.json.gz'
            raw = json.loads(gzip.decompress((root / name).read_bytes()))
            touched = set()
            for p in a['pairs']:
                _, ptr = p['rawNoticePointer'].split('#')
                if ptr in touched:
                    continue
                touched.add(ptr)
                record = e.pointer(raw, ptr)
                record['titulaire'] = canary
                decoded = json.loads(record['donnees'])
                decoded['contact'] = canary
                # A reviewed lot-note excerpt must not expand to added private prose.
                for pair in a['pairs']:
                    if pair['rawNoticePointer'].split('#')[1] != ptr:
                        continue
                    for field in pair['fields']:
                        if 'excerpt' not in field:
                            continue
                        path = field['pointer']
                        parent, key = path.rsplit('/', 1)
                        value = e.pointer(decoded, parent)
                        if canary not in value[key]:
                            value[key] += '\\n' + canary
                        field['scalarSha256'] = e.sha(e.canonical(value[key]))
                record['donnees'] = json.dumps(decoded, ensure_ascii=False)
            (root / name).write_bytes(gzip.compress(e.canonical(raw)))
            for name in a['sourceHashes']:
                a['sourceHashes'][name] = e.sha((root / name).read_bytes())
            output = e.render(e.build(root, a))
            self.assertNotIn(canary, output)
            self.assertNotIn("Porte d'Ivry", output)
            self.assertNotIn('titulaire', output)


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.requests = json.loads((ROOT / e.ANNOTATIONS).read_text())['liveRequests']

    def test_historical_recorded_scalars_are_minimal_and_hash_bound(self):
        self.assertEqual(sum(len(r['recordedFields']) for r in self.requests), 104)
        for change in ['private-pointer', 'hash', 'nested', 'duplicate']:
            requests = copy.deepcopy(self.requests)
            field = requests[0]['recordedFields'][0]
            if change == 'private-pointer':
                field['pointer'] = '/results/0/titulaire'
            elif change == 'hash':
                field['scalarSha256'] = '0' * 64
            elif change == 'nested':
                field['value'] = {'contact': 'PRIVATE_CANARY'}
            else:
                requests[0]['recordedFields'].append(copy.deepcopy(field))
            with self.subTest(change=change), self.assertRaises(ValueError):
                e.validate_requests(requests)

    def test_exact_allowlist(self):
        for url in ['https://evil.invalid/', 'https://data.economie.gouv.fr/other',
                    self.requests[0]['url'] + '#hidden', self.requests[0]['url'].replace('https:', 'http:'),
                    self.requests[0]['url'].replace('data.economie.gouv.fr', 'data.economie.gouv.fr@evil.invalid')]:
            requests = copy.deepcopy(self.requests)
            requests[0]['url'] = url
            with self.assertRaises(ValueError):
                e.validate_requests(requests)
        with self.assertRaises(ValueError):
            e.validate_requests(self.requests + [self.requests[0]])
        requests = copy.deepcopy(self.requests)
        requests[-1]['requestBody']['limit'] = 11
        with self.assertRaises(ValueError):
            e.validate_requests(requests)

    def test_exclusive_external_private_directory_and_ceiling(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'new'
            with patch.object(e, 'acquire', return_value={'failure': None}) as acquire:
                e.fetch(self.requests, directory)
                self.assertEqual(acquire.call_count, 14)
                self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
                self.assertEqual((directory / 'manifest.json').stat().st_mode & 0o777, 0o600)
                with self.assertRaises(FileExistsError):
                    e.fetch(self.requests, directory)
                link = Path(tmp) / 'symlink'
                link.symlink_to(directory, target_is_directory=True)
                with self.assertRaises(FileExistsError):
                    e.fetch(self.requests, link)
        with self.assertRaises(ValueError):
            e.fetch(self.requests, ROOT / 'new-raw-forbidden')
        with self.assertRaises(ValueError):
            e.fetch(self.requests, Path('relative'))

    def mocked_acquire(self, program, expected_failure):
        popen = subprocess.Popen
        commands = []
        def mock(command, **kwargs):
            commands.append(command)
            return popen([sys.executable, '-c', program], **kwargs)
        with tempfile.TemporaryDirectory() as tmp, patch.object(e.subprocess, 'Popen', mock):
            dest = Path(tmp) / 'body'
            result = e.acquire(self.requests[0], dest)
            self.assertEqual(result['failure'], expected_failure)
            self.assertLessEqual(dest.stat().st_size, e.LIMIT)
            self.assertEqual(dest.stat().st_mode & 0o777, 0o600)
            self.assertEqual(e.sha(dest.read_bytes()), result['bodySha256'])
        command = commands[0]
        self.assertNotIn('--location', command)
        self.assertEqual(command[command.index('--max-time') + 1], '15')
        self.assertEqual(command[command.index('--retry') + 1], '0')
        self.assertEqual(command[1], '--disable')
        return result

    def test_live_minimization_canaries(self):
        canary = 'PERSON_COMPANY_CONTACT_SIGNATURE_CANARY'
        ministry = {'results': [{'id': '2025F00013', 'montant': 415000,
                                'titulaire': canary, 'contact': canary, 'objet': canary}]}
        output = e.minimize_response(self.requests[4], e.canonical(ministry))
        self.assertNotIn(canary, e.render(output))
        self.assertEqual(output[0]['pointer'], '/results/0')
        nantes = [{'reference_interne_du_contrat': '2024_8846', 'entreprise': canary}]
        self.assertNotIn(canary, e.render(e.minimize_response(self.requests[10], e.canonical(nantes))))
        ted = {'notices': [{'notice-title': canary}], 'totalNoticeCount': 1, 'timedOut': False}
        self.assertNotIn(canary, e.render(e.minimize_response(self.requests[11], e.canonical(ted))))
        with self.assertRaises(ValueError):
            e.minimize_response(self.requests[11], e.canonical({'totalNoticeCount': {'contact': canary}}))

    def test_mock_success(self):
        result = self.mocked_acquire("import os;os.write(1,b'{}');os.write(2,b'200')", None)
        self.assertEqual(result['httpStatus'], '200')

    def test_mock_redirect_not_followed(self):
        self.mocked_acquire("import os;os.write(2,b'302')", 'redirect-not-followed')

    def test_mock_bound(self):
        self.mocked_acquire("import os;os.write(1,b'x'*(2*1024*1024+1));os.write(2,b'200')", 'body-limit')

    def test_mock_curl_timeout(self):
        self.mocked_acquire("import os;os.write(2,b'000');raise SystemExit(28)", 'timeout')

    def test_mock_enclosing_timeout(self):
        # Advance monotonic time only inside acquire; no real 15-second wait.
        with patch.object(e.time, 'monotonic', side_effect=[0, 16, 17]):
            self.mocked_acquire("import time;time.sleep(60)", 'timeout')

    def test_failures_recorded_no_raw_published(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(e, 'acquire', side_effect=OSError('secret-contact-canary')):
            results = e.fetch(self.requests, Path(tmp) / 'new')
            self.assertEqual(len(results), 14)
            self.assertTrue(all(r['failure'] == 'acquisition-failed' for r in results))
            self.assertNotIn('secret-contact-canary', e.render(results))


if __name__ == '__main__':
    unittest.main()
