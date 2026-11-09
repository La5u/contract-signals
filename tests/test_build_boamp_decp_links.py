import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('boamp_links', ROOT / 'tools/build-boamp-decp-links.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def row(family, id, **extra):
    return dict(id=id, dataFamily=family, buyerSiret='21750001600019',
                supplierIds=[{'id': '12345678900012', 'identifierType': 'SIRET'}],
                date='2025-01-14', cpv='45000000',
                source=('https://www.boamp.fr/pages/avis/?q=idweb:25-1' if family == 'boamp'
                        else 'https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records'),
                **extra)


def raw(ref='2025ABC'):
    result = {'efac:SettledContract': {'cbc:ID': {'#text': 'CON-0001'},
                                     'efac:ContractReference': {'cbc:ID': ref}},
              'efac:LotResult': {'cbc:TenderResultCode': 'selec-w',
                                'efac:TenderLot': {'cbc:ID': 'LOT-0001'},
                                'efac:SettledContract': {'cbc:ID': 'CON-0001'}}}
    notice = {'ext:UBLExtensions': {'ext:UBLExtension': {'ext:ExtensionContent': {
        'efext:EformsExtension': {'efac:NoticeResult': result}}}}}
    return {'idweb': '25-1', 'donnees': json.dumps({'EFORMS': {'ContractAwardNotice': notice}})}


class LinksTest(unittest.TestCase):
    def setUp(self):
        self.b = row('boamp', 'boamp-25-1-lot-0001', noticeId='25-1', lotId='LOT-0001', contractId='CON-0001')
        self.d = row('decp', 'decp-1', contractId='2025ABC')

    def links(self, raw_rows=()):
        return m.build_links([self.b], [self.d], raw_rows)[0]

    def test_candidate_not_confirmed(self):
        link = self.links()[0]
        self.assertEqual(link['status'], 'candidate')
        self.assertEqual(link['basis'], ['buyer-holder-siret-same-date'])
        self.assertIn('unconfirmed-no-exact-reference', link['warnings'])

    def test_raw_exact_reference(self):
        self.d['date'] = None
        link = self.links([raw()])[0]
        self.assertEqual(link['status'], 'confirmed')
        self.assertEqual(link['basis'], ['buyer-published-contract-reference'])

    def test_published_reference_and_notice_lot(self):
        self.b['contractReference'] = '2025ABC'
        self.assertEqual(self.links()[0]['status'], 'confirmed')
        del self.b['contractReference']
        self.d.update(noticeId='25-1', lotId='LOT-0001', date=None)
        self.assertEqual(self.links()[0]['basis'], ['buyer-exact-notice-lot'])
        self.d['lotId'] = 'LOT-0002'
        self.assertEqual(self.links(), [])

    def test_never_substring_or_local_con(self):
        self.d['contractId'] = 'prefix2025ABCsuffix'
        self.assertEqual(self.links([raw()])[0]['status'], 'candidate')
        self.d['contractId'] = 'CON-0001'
        self.assertEqual(self.links([raw('CON-0001')])[0]['status'], 'candidate')
        self.b['date'] = None
        self.assertEqual(self.links([raw('CON-0001')]), [])

    def test_unique_raw_notice_lot_required(self):
        r = raw()
        self.assertEqual(m.raw_references([r, r]), {})
        d = json.loads(r['donnees'])
        result = d['EFORMS']['ContractAwardNotice']['ext:UBLExtensions']['ext:UBLExtension']['ext:ExtensionContent']['efext:EformsExtension']['efac:NoticeResult']
        for key in ['efac:LotResult', 'efac:SettledContract']:
            dup = copy.deepcopy(d)
            target = dup['EFORMS']['ContractAwardNotice']['ext:UBLExtensions']['ext:UBLExtension']['ext:ExtensionContent']['efext:EformsExtension']['efac:NoticeResult']
            target[key] = [result[key], result[key]]
            self.assertEqual(m.raw_references([dict(idweb='25-1', donnees=json.dumps(dup))]), {})
        self.b['lotId'] = 'LOT-0002'
        self.assertEqual(self.links([r])[0]['status'], 'candidate')

    def test_missing_or_invalid_date(self):
        for value in [None, '', '2025-02-30', '2025-01-14T00:00:00Z']:
            self.b['date'] = value
            self.assertEqual(self.links(), [])

    def test_siren_not_siret(self):
        for ids in [[{'id': '123456789', 'identifierType': 'SIREN'}],
                    [{'id': '12345678900012', 'identifierType': 'SIREN'}],
                    [{'id': '123456789', 'identifierType': 'SIRET'}]]:
            self.b['supplierIds'] = ids
            self.assertEqual(self.links(), [])
        self.b['supplierIds'] = self.d['supplierIds']
        self.b['buyerSiret'] = '217500016'
        self.assertEqual(self.links([raw()]), [])

    def test_mismatched_buyers_block_exact_and_candidate(self):
        self.d['buyerSiret'] = '21210231300013'
        self.d.update(noticeId='25-1', lotId='LOT-0001')
        self.assertEqual(self.links([raw()]), [])

    def test_ambiguity_and_cpv(self):
        d2 = dict(self.d, id='decp-2', cpv='45100000-1')
        b2 = dict(self.b, id='boamp-25-2-lot-0001')
        links, _ = m.build_links([self.b, b2], [self.d, d2], [])
        self.assertEqual(len(links), 4)
        for l in links:
            self.assertEqual(l['status'], 'candidate')
            self.assertIn('multiple-decp-matches', l['warnings'])
            self.assertIn('multiple-boamp-matches', l['warnings'])
        self.assertEqual(sum('different-cpv' in l['warnings'] for l in links), 2)
        self.d['cpv'] = '45000000-7'
        self.assertNotIn('different-cpv', self.links()[0]['warnings'])

    def test_official_urls_only(self):
        for url in ['javascript:alert(1)', 'https://www.boamp.fr.evil.test/',
                    'https://user@www.boamp.fr/', 'http://www.boamp.fr/', 'https://www.boamp.fr:444/']:
            self.assertFalse(m.official_url(url))
        self.b['source'] = 'https://example.org/'
        with self.assertRaises(ValueError):
            self.links()

    @unittest.skipUnless((ROOT / 'data/boamp-raw.json.gz').exists(), 'raw snapshot is private (not in git)')
    def test_current_artifact_deterministic_public_safe(self):
        expected = m.build()
        self.assertEqual(expected, m.build())
        self.assertEqual(expected, json.loads((ROOT / 'data/boamp-decp-links.json').read_text()))
        self.assertEqual(len(expected['sources']), 4)
        for link in expected['links']:
            self.assertEqual(set(link), {'boampId', 'decpId', 'status', 'basis', 'warnings', 'boampUrl', 'decpUrl'})

    def test_ui_validation_and_optional_loading(self):
        # Run the browser-independent validator, including malicious / malformed artifacts.
        js = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const context = vm.createContext({ URL });
require('./tools/engine.cjs').load(context);
const data = JSON.parse(fs.readFileSync('data/boamp-decp-links.json', 'utf8'));
assert.equal(context.validateBoampDecpLinks(data).length, data.links.length);
for (const mutate of [d => d.schemaVersion = 2, d => d.sources[0].sha256 = 'bad',
  d => d.links[0].decpUrl = 'javascript:alert(1)', d => d.links[0].decpUrl = 'https://data.economie.gouv.fr.evil.test/',
  d => d.links[0].status = 'confirmed', d => d.links.push(d.links[0]), d => d.counts.candidate++]) {
  const d = JSON.parse(JSON.stringify(data)); mutate(d);
  assert.throws(() => context.validateBoampDecpLinks(d));
}
'''
        subprocess.run(['node', '-e', js], cwd=ROOT, check=True)
        script = ''.join((ROOT / name).read_text() for name in ('views.js', 'script.js'))
        self.assertIn('Unconfirmed candidate only', script)
        self.assertIn('Missing or invalid optional evidence must not block', script)
        self.assertIn('!usingLocalFile', script)


if __name__ == '__main__':
    unittest.main()
