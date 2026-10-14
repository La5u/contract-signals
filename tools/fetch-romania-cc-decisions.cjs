// Research only (owner-approved 2026-10-14): Romanian Competition Council decisions for bid-rigging labels.
// The site answers scripts with a JavaScript browser check, so a real Firefox (Playwright) is used; no stealth,
// no captcha solving. Output stays outside the repository, in ~/.cache/contract-signals/romania-cc/.
// Competition Council cartel decisions: list all index pages, then download each PDF once.
// One real Firefox, serial, 5 s between requests, resumable (skips files already saved).
const fs = require('fs'), path = require('path');
const { firefox } = require('/tmp/procurement-browser/node_modules/playwright');
const OUT = path.join(process.env.HOME, '.cache/contract-signals/romania-cc');
const BASE = 'https://www.consiliulconcurentei.ro/documente-oficiale/concurenta/decizii/serviciul-carteluri/';
const EXTRA = ['https://www.consiliulconcurentei.ro/wp-content/uploads/2026/06/blacklist_08.06.2026.pdf', 'https://www.consiliulconcurentei.ro/wp-content/uploads/2024/11/Decizie-134-din-2024.pdf', 'https://www.consiliulconcurentei.ro/wp-content/uploads/2025/07/Decizie-271-din-2024.pdf'];
const sleep = ms => new Promise(r => setTimeout(r, ms));
const settle = async page => {
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(2000);
    const html = await page.content().catch(() => '');
    if (html && !/Verifying your browser/.test(html) && /<body/i.test(html)) break;
  }
  await page.waitForLoadState('load').catch(() => {});
};
(async () => {
  fs.mkdirSync(path.join(OUT, 'pdf'), { recursive: true });
  const browser = await firefox.launch({ headless: true });
  const page = await browser.newPage();
  const index = fs.existsSync(path.join(OUT, 'index.json')) ? JSON.parse(fs.readFileSync(path.join(OUT, 'index.json'))) : {};
  for (let p = 1; p <= 11; p++) {
    const url = p === 1 ? BASE : `${BASE}page/${p}/`;
    if (index[url]) continue;
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 }); await settle(page);
    index[url] = await page.$$eval('a', as => as.filter(a => /\.pdf/i.test(a.href)).map(a => [a.textContent.replace(/\s+/g, ' ').trim(), a.href]));
    fs.writeFileSync(path.join(OUT, 'index.json'), JSON.stringify(index, null, 1));
    console.log('page', p, index[url].length, 'pdf links'); await sleep(5000);
  }
  const titles = {};
  for (const links of Object.values(index)) for (const [t, h] of links) if (t.length > (titles[h] || '').length) titles[h] = t;
  for (const h of EXTRA) titles[h] = titles[h] || 'blacklist';
  fs.writeFileSync(path.join(OUT, 'titles.json'), JSON.stringify(titles, null, 1));
  // Downloads need the browser check's cookie: pass it once on a normal page.
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 90000 }); await settle(page); await sleep(3000);
  let n = 0;
  for (const h of Object.keys(titles)) {
    const file = path.join(OUT, 'pdf', decodeURIComponent(h.split('/').pop()));
    if (fs.existsSync(file)) continue;
    const r = await page.request.get(h, { timeout: 120000 });
    const body = await r.body();
    if (r.status() !== 200 || body.slice(0, 4).toString() !== '%PDF') { console.log('not a pdf', r.status(), h); await sleep(5000); continue; }
    fs.writeFileSync(file, body); n++;
    console.log('saved', n, path.basename(file), body.length); await sleep(5000);
  }
  console.log('done', Object.keys(titles).length, 'documents');
  await browser.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
