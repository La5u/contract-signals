import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prozorro_expansion', ROOT / 'tools/import-prozorro.py')
ua = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ua)


class ExpansionTests(unittest.TestCase):
    def fixture(self, directory):
        pilot = json.loads((ROOT / 'data/prozorro.json').read_bytes())[0]
        tender = ua.load_gz(ROOT / f"data/prozorro/raw/records/{pilot['tenderID']}.json.gz")['data']
        body = json.dumps({'data': tender}).encode()
        url = f"{ua.API}/tenders/{tender['id']}"
        key = hashlib.sha256(url.encode()).hexdigest()[:32]
        digest = hashlib.sha256(body).hexdigest()
        (directory / f'{key}.gz').write_bytes(gzip.compress(body))
        meta = {'url': url, 'status': 200, 'sha256': digest, 'retrieved_at': 'fixture'}
        (directory / f'{key}.meta.json').write_text(json.dumps(meta))
        entry = dict(internalId=tender['id'], tenderID=tender['tenderID'],
                     buyerId=tender['procuringEntity']['identifier']['id'],
                     sourceSha256=digest, retrievedAt='fixture')
        config = dict(schemaVersion=1, cohortId='prozorro-test', selection={'method': 'fixture'},
                      window=dict(startInclusive=ua.START, endExclusive=ua.END), records=[entry])
        path = directory / 'config.json'
        path.write_text(json.dumps(config))
        return path, config, directory / f'{key}.gz'

    def test_offline_deterministic_and_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            config, _, _ = self.fixture(d)
            with patch.object(ua.urllib.request, 'urlopen', side_effect=AssertionError('network')):
                coverage = ua.expand_cached(config, d, d / 'out')
                before = (d / 'out/contracts.json').read_bytes()
                ua.expand_cached(config, d, d / 'out')
            self.assertEqual(before, (d / 'out/contracts.json').read_bytes())
            self.assertEqual(coverage['counts']['tenders'], 1)
            rows = json.loads(before)
            self.assertTrue(rows)
            self.assertTrue(all(r['cohortId'] == 'prozorro-test' and r['sourceSha256'] for r in rows))
            self.assertTrue(all('contractChanges' not in r for r in rows))

    def test_hash_mismatch_fails_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            config, _, body = self.fixture(d)
            body.write_bytes(gzip.compress(b'{}'))
            with self.assertRaisesRegex(ValueError, 'provenance mismatch'):
                ua.expand_cached(config, d, d / 'out')
            self.assertFalse((d / 'out').exists())

    def test_duplicate_and_buyer_mismatch_rejected(self):
        for duplicate in (True, False):
            with tempfile.TemporaryDirectory() as temp:
                d = Path(temp)
                path, config, _ = self.fixture(d)
                if duplicate:
                    config['records'] *= 2
                else:
                    config['records'][0]['buyerId'] = 'wrong'
                path.write_text(json.dumps(config))
                with self.assertRaises(ValueError):
                    ua.expand_cached(path, d, d / 'out')
                self.assertFalse((d / 'out').exists())

    def test_published_expansion_counts_and_provenance(self):
        d = ROOT / 'data/prozorro-expansion'
        config = json.loads((d / 'config.json').read_bytes())
        rows = json.loads((d / 'contracts.json').read_bytes())
        coverage = json.loads((d / 'coverage.json').read_bytes())
        self.assertEqual(coverage['configSha256'], hashlib.sha256((d / 'config.json').read_bytes()).hexdigest())
        self.assertEqual(len(rows), 106)
        self.assertEqual(len(config['records']), 100)
        self.assertEqual(len({r['buyerId'] for r in rows}), 96)
        sources = {e['tenderID']: e for e in config['records']}
        pilot = {r['id'] for r in json.loads((ROOT / 'data/prozorro.json').read_bytes())}
        self.assertFalse(pilot & {r['id'] for r in rows})
        for row in rows:
            self.assertEqual(row['sourceSha256'], sources[row['tenderID']]['sourceSha256'])
            self.assertEqual(row['sourceRetrievedAt'], sources[row['tenderID']]['retrievedAt'])
            self.assertNotIn(row['buyerId'], {b['code'] for b in ua.BUYERS})


if __name__ == '__main__':
    unittest.main()
