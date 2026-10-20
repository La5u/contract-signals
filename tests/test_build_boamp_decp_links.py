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

    def test_current_artifact_deterministic_public_safe(self):
        expected = m.build()
        self.assertEqual(expected, m.build())
        self.assertEqual(expected, json.loads((ROOT / 'data/boamp-decp-links.json').read_text()))
        self.assertEqual(len(expected['sources']), 4)
        for link in expected['links']:
            self.assertEqual(set(link), {'boampId', 'decpId', 'status', 'basis', 'warnings', 'boampUrl', 'decpUrl'})

    @unittest.skipUnless(Path('/tmp/procurement-browser/node_modules/playwright').exists(), 'optional Playwright not installed')
    def test_browser_candidate_and_missing_artifact(self):
        js = r'''
const { chromium } = require('/tmp/procurement-browser/node_modules/playwright');
const fs = require('fs'), path = require('path'), http = require('http'), assert = require('assert');
const server = http.createServer((req, res) => {
  const file = path.join(process.cwd(), new URL(req.url, 'http://x').pathname.replace(/\/$/, '/index.html'));
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end(); }
  res.setHeader('Content-Type', ({'.json':'application/json','.js':'text/javascript','.html':'text/html','.css':'text/css'})[path.extname(file)] || 'application/octet-stream');
  fs.createReadStream(file).pipe(res);
});
(async () => {
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const browser = await chromium.launch({ executablePath: fs.existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined, headless: true, args: ['--no-sandbox'] });
  try {
    const page = await browser.newPage(); const errors = []; page.on('pageerror', e => errors.push(e.message));
    const base = `http://127.0.0.1:${server.address().port}`;
    await page.goto(base + '/#dataset=boamp&open=boamp-25-34782-lot-0003');
    await page.getByText('Cross-source evidence · BOAMP ↔ DECP', {exact:true}).waitFor();
    const links = page.getByRole('link', {name:'Unconfirmed candidate only — DECP official source'});
    // Wait for reviewed dispositions before counting active links.
    await page.getByRole('link', {name:'Correction history'}).waitFor();
    assert.equal(await links.count(), 1);
    for (const url of await links.evaluateAll(a => a.map(v => v.href))) assert.ok(url.startsWith('https://data.economie.gouv.fr/'));
    await page.getByRole('link', {name:'Public evidence ledger (JSON)'}).waitFor();
    await page.getByRole('link', {name:'Correction history'}).waitFor();
    assert.equal(await links.count(), 1, 'Dismissed CUISSON/LAVERIE pairing is not active');
    const text = await page.locator('#detail-verify').textContent();
    assert.ok(!text.includes('Ambiguous:')); assert.ok(text.includes('differing CPVs'));
    assert.ok(text.includes('Dismissed investigation leads'));
    assert.ok(text.includes('Reject this investigation lead for technical LOT-0003'));
    assert.ok(text.includes('Lot-compatible candidate; no identifier bridge.'));
    assert.ok(text.includes('Published notice reference: 2024-88480'));
    assert.ok(!text.includes('Confirmed exact identifiers'));
    await page.goto(base + '/#dataset=boamp&open=boamp-25-21317-lot-0001');
    await page.getByRole('link', {name:'TED — same notice/version 01 verified'}).waitFor();
    assert.ok((await page.locator('#detail-verify').textContent()).includes('DECP contract linkage remains unconfirmed'));
    await page.goto(base + '/#dataset=decp&open=decp-21440109300015-2025F00012');
    await page.getByRole('link', {name:'Correction history'}).waitFor();
    await page.getByRole('link', {name:'Dismissed pairing — audit source'}).waitFor();
    assert.equal(await page.getByRole('link', {name:'Unconfirmed candidate only — BOAMP official source'}).count(), 0);
    await page.getByRole('link', {name:'Public evidence ledger (JSON)'}).waitFor();
    await page.route('**/data/public-link-resolutions.json', route => route.fulfill({status:404, body:'missing'}));
    await page.goto(base + '/?missing-resolutions#dataset=boamp&open=boamp-25-34782-lot-0003');
    await page.getByRole('link', {name:'Public evidence ledger (JSON)'}).waitFor();
    assert.equal(await page.getByRole('link', {name:'Unconfirmed candidate only — DECP official source'}).count(), 2);
    assert.equal(await page.getByText('Dismissed investigation leads', {exact:true}).count(), 0);
    await page.unroute('**/data/public-link-resolutions.json');
    await page.route('**/data/public-link-evidence.json', route => route.fulfill({status:404, body:'missing'}));
    await page.goto(base + '/?missing-ledger#dataset=boamp&open=boamp-25-34782-lot-0003');
    await page.getByText('Cross-source evidence · BOAMP ↔ DECP', {exact:true}).waitFor();
    await page.getByRole('link', {name:'Correction history'}).waitFor();
    assert.equal(await page.getByRole('link', {name:'Unconfirmed candidate only — DECP official source'}).count(), 1);
    assert.equal(await page.getByRole('link', {name:'Public evidence ledger (JSON)'}).count(), 0);
    await page.route('**/data/boamp-decp-links.json', route => route.fulfill({status:404, body:'missing'}));
    await page.goto(base + '/?missing-artifact#dataset=boamp&open=boamp-25-34782-lot-0003');
    await page.locator('#detail-panel').waitFor();
    assert.equal(await page.getByText('Cross-source evidence · BOAMP ↔ DECP', {exact:true}).count(), 0);
    assert.deepEqual(errors, []);
  } finally { await browser.close(); server.close(); }
})().catch(e => { console.error(e); server.close(); process.exitCode = 1; });
'''
        subprocess.run(['node', '-e', js], cwd=ROOT, check=True, timeout=90)

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
