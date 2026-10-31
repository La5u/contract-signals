'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const http = require('node:http');
const { build } = require('../tools/build-korea-top.cjs');
const ctx = vm.createContext({ URL });
require('../tools/engine.cjs').load(ctx);
const run = (fn, ...args) => { ctx.args = args; return vm.runInContext(`${fn}(...args)`, ctx); };
const meta = { v: 1, contracts: 8, columns: ['contractNo','name','date','latestAmount','supplier','supplierKind','method','demand','legalRef','checks'],
  methods: ['일반경쟁'], supplierKinds: ['corporation'], businessTypes: [], linkKinds: [], link: '' };
const buyers = [['A','Alpha','',4,0], ['B','Beta','',4,1]];
const row = (id, amount, checks, demand = 0, legal = 0) => [id, 'School '+id, '2025-01-01', amount, 'Company', 0, 0, demand, legal, checks];
const shards = [
  { v: 1, demand: ['Request A'], legal: ['Law A'], buyers: { A: [row('A1',100,null),row('A2',50,'s'.repeat(25)),row('A3',50,'s'.repeat(25)),row('A4',-1,null)] } },
  { v: 1, demand: ['Request B'], legal: ['Law B'], buyers: { B: [row('B1',500,null),row('B2',100,'s'.repeat(25)),row('B3',40,'s'.repeat(25)),row('B4',0,'c'.repeat(25))] } }
];
let top;
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'korea-top-'));
try {
  fs.mkdirSync(path.join(dir,'s'));
  fs.writeFileSync(path.join(dir,'meta.json'),JSON.stringify(meta));
  fs.writeFileSync(path.join(dir,'buyers.json'),JSON.stringify(buyers));
  shards.forEach((shard,i) => fs.writeFileSync(path.join(dir,'s',`${String(i).padStart(4,'0')}.json`),JSON.stringify(shard)));
  top = build(dir,3);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(dir,'top.json'),'utf8')),top);
  assert.equal(top.limit,3); assert.equal(top.count,3);
  assert.deepEqual(Object.values(top.buyers).flat().map(r=>r[0]),['B2','A2','A3']);
  const decoded = buyers.flatMap(b => run('koreaRecords',meta,top,b));
  for (const c of decoded) {
    assert.match(c.notes,c.buyerId === 'A' ? /Request A.*Law A/ : /Request B.*Law B/);
    const original = run('koreaRecords',meta,shards[c.buyerId === 'A' ? 0 : 1],buyers[c.buyerId === 'A' ? 0 : 1]).find(r=>r.id===c.id);
    assert.deepEqual(JSON.parse(JSON.stringify(c)),JSON.parse(JSON.stringify(original)));
    assert.equal(run('getVigilanceScore',c),run('getVigilanceScore',original));
  }
  assert.equal(run('koreaRecords',meta,shards[0],buyers[0])[3].amount,null);
  assert.equal(build(dir).count,8);
  assert.throws(()=>build(dir,0),/positive integer/);
} finally { fs.rmSync(dir,{recursive:true,force:true}); }
console.log('Korea top builder: ranking, ties, dictionaries, defaults and negative amounts passed');

async function browserTests() {
  const { chromium } = require(process.env.PLAYWRIGHT_PATH || '/tmp/procurement-browser/node_modules/playwright');
  const server = http.createServer((req,res) => {
    const file = path.join(process.cwd(),new URL(req.url,'http://x').pathname.replace(/\/$/,'/index.html'));
    if (!file.startsWith(process.cwd()) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end(); }
    res.setHeader('content-type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':file.endsWith('.json')?'application/json':'text/html');
    fs.createReadStream(file).pipe(res);
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const browser = await chromium.launch({executablePath:process.env.CHROMIUM_PATH || (fs.existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined),headless:true,
    args:['--no-sandbox','--enable-gpu','--use-angle=gl-egl','--ignore-gpu-blocklist']});
  try {
    const page = await browser.newPage();
    const errors = []; page.on('pageerror',e=>errors.push(e.message));
    let missing = false, release, delay = false;
    await page.route('**/korea-site/**',async route => {
      const name = new URL(route.request().url()).pathname.split('/').pop();
      if (name === 'meta.json') return route.fulfill({json:meta});
      if (name === 'buyers.json') return route.fulfill({json:buyers});
      if (name === 'top.json') {
        if (delay) await new Promise(resolve=>release=resolve);
        return missing ? route.fulfill({status:404,body:''}) : route.fulfill({json:top});
      }
      return route.fulfill({json:shards[Number(name.slice(0,4))]});
    });
    const base = `http://127.0.0.1:${server.address().port}`;
    await page.goto(base+'/#dataset=korea');
    await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('3 / 3 results'));
    assert.equal(await page.locator('#korea-all').textContent(),'Most flagged · nationwide');
    assert.match(await page.locator('#dataset-note').textContent(),/3 highest-scored of all 8 contracts/);
    assert.equal(await page.locator('#korea-scan').count(),0);
    const renderer = await page.evaluate(()=>{
      const gl = document.createElement('canvas').getContext('webgl');
      const ext = gl?.getExtension('WEBGL_debug_renderer_info');
      return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : null;
    });
    assert.ok(renderer && !/SwiftShader/i.test(renderer),`WebGL renderer: ${renderer}`);
    console.log(`Headless WebGL renderer: ${renderer}`);
    await page.locator('.row-toggle').first().click();
    await page.locator('#detail-panel').waitFor();
    await page.locator('#detail-close').click();
    await page.fill('#search','A2');
    await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('1 / 3 results'));
    const downloadPromise = page.waitForEvent('download');
    await page.locator('#export-json').click();
    const download = await downloadPromise;
    const exported = JSON.parse(fs.readFileSync(await download.path(),'utf8'));
    assert.equal(exported.count,1); assert.equal(exported.records[0].id,'koneps-A2');
    missing = true;
    await page.reload();
    await page.waitForFunction(()=>document.querySelector('#status').textContent === 'Choose a contracting institution.');
    assert.equal(await page.locator('#korea-picker').isVisible(),true);
    await page.locator('#korea-results button').first().click();
    await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('4 / 4 results'));
    // A delayed subset response cannot replace a buyer chosen while it loads.
    missing = false; delay = true;
    const request = page.waitForRequest('**/top.json');
    await page.locator('#korea-all').click();
    await request;
    await page.locator('#korea-results button').first().click();
    await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('4 / 4 results'));
    release();
    await page.waitForTimeout(100);
    assert.match(await page.locator('#status').textContent(),/^4 \/ 4 results/);
    await page.goto(base+'/#dataset=global');
    await page.waitForFunction(()=>/ results/.test(document.querySelector('#status').textContent));
    assert.equal(await page.locator('#dataset').inputValue(),'decp');
    assert.deepEqual(errors,[]);
    console.log('Korea top view: filters, record panel, export, missing file, stale response and old global links passed');
  } finally { await browser.close(); await new Promise(resolve=>server.close(resolve)); }
}
if (!process.argv.includes('--unit')) browserTests().catch(error=>{console.error(error);process.exitCode=1;});
