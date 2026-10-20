'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const http = require('node:http');
const path = require('node:path');
const source = fs.readFileSync('script.js', 'utf8');
const columns = ['contractNo','name','date','latestAmount','supplier','supplierKind','method'];
const meta = {columns, supplierKinds:['corporation'], methods:['Open'], businessTypes:[],linkKinds:[],link:''};
const buyers = [['A','Alpha','',305,0],['B','Beta','',305,0],['C','Gamma','',305,1]];
const makeRows = prefix => Array.from({length:305},(_,i)=>[prefix+i, i % 2 ? 'Road' : 'School','2025-01-01',i+1,'Published company',0,0]);
const shards = [{buyers:{A:makeRows('A'),B:makeRows('B')},demand:[],legal:[]},{buyers:{C:makeRows('C')},demand:[],legal:[]}];
async function unitTests() {
 const ctx=vm.createContext({URL,structuredClone,setTimeout}); require('../tools/engine.cjs').load(ctx);
 ctx.args={meta,buyers,fetchShard:async n=>shards[n],limit:25,offset:25,signal:new AbortController().signal};
 ctx.args.predicate=c=>vm.runInContext('selectContracts([record], {search:"school", minimum:100, assessment:"unevaluated"}).length > 0',Object.assign(ctx,{record:c}));
 const r=await vm.runInContext('scanKoreaPage(args)',ctx);
 assert.equal(r.rows.length,25); assert.equal(r.rows[0].id,'koneps-A150'); assert.equal(r.hasMore,true); assert.equal(r.complete,false);
 for(const opts of [{flagged:true},{minScore:1},{assessment:'zero'},{indicator:'official-finding'},{legal:'direct'},{official:true}]) {
  ctx.opts=opts; assert.equal(vm.runInContext('selectContracts([record],opts).length',ctx),0);
 }
 // Cap and paging must agree, even for the ordinary UI's 250-row setting.
 ctx.args={meta,buyers,fetchShard:async n=>shards[n],limit:250,predicate:()=>true};
 const first=await vm.runInContext('scanKoreaPage(args)',ctx); assert.equal(first.rows.length,200);
 const ids=[];
 for(let offset=0;offset<915;offset+=200) {
  ctx.args.offset=offset;
  const page=await vm.runInContext('scanKoreaPage(args)',ctx); ids.push(...page.rows.map(c=>c.id));
  if(!page.hasMore) { assert.equal(page.complete,true); assert.equal(page.matches,915); }
 }
 assert.equal(ids.length,915); assert.equal(new Set(ids).size,915);
 // A buyer too big for one file spans its own shards, oldest first; every part is scanned once, in order.
 const partShards=[shards[0],{buyers:{D:makeRows('D').slice(0,200)},demand:[],legal:[]},{buyers:{D:makeRows('D').slice(200)},demand:[],legal:[]}];
 ctx.args={meta,buyers:[['D','Delta','',305,2,[1,2]],buyers[0]],fetchShard:async n=>partShards[n],limit:200,offset:410,predicate:()=>true};
 const split=await vm.runInContext('scanKoreaPage(args)',ctx);
 assert.equal(split.matches,610); assert.equal(split.complete,true); assert.equal(split.rows[0].id,'koneps-D105'); assert.equal(split.rows.at(-1).id,'koneps-D304');
 // Cancellation while a fetch ignores AbortSignal must not accept stale data.
 let release; const abort=new AbortController();
 ctx.args={meta,buyers,fetchShard:()=>new Promise(r=>release=r),signal:abort.signal,predicate:()=>true};
 const pending=vm.runInContext('scanKoreaPage(args)',ctx); abort.abort(); release(shards[0]);
 await assert.rejects(pending,{name:'AbortError'});
 let active=0,maxActive=0,maxRetained=0;
 ctx.args={meta,buyers,limit:10,offset:900,predicate:()=>true,
 fetchShard:async n=>{active++;maxActive=Math.max(active,maxActive);await new Promise(r=>setTimeout(r,2));active--;return shards[n];},
 progress:p=>maxRetained=Math.max(maxRetained,p.retained)};
 await vm.runInContext('scanKoreaPage(args)',ctx); assert.equal(maxActive,1);assert.ok(maxRetained<=10);
 // Cancellation after a CPU batch yields must stop before another batch/fetch.
 const midAbort=new AbortController();let yields=0,requests=0;
 ctx.args={meta,buyers,limit:200,offset:10000,predicate:()=>false,signal:midAbort.signal,
 fetchShard:async n=>{requests++;return shards[n];},yieldTask:async()=>{yields++;midAbort.abort();}};
 await assert.rejects(vm.runInContext('scanKoreaPage(args)',ctx),{name:'AbortError'});
 assert.equal(yields,1);assert.equal(requests,1);
 ctx.args={meta,buyers,predicate:()=>true,fetchShard:async()=>({buyers:{},demand:[],legal:[]})};
 await assert.rejects(vm.runInContext('scanKoreaPage(args)',ctx),/Incomplete shard/);
 console.log('Korea scanner unit tests passed');
}
async function browserTests() {
 const {chromium}=require(process.env.PLAYWRIGHT_PATH || '/tmp/procurement-browser/node_modules/playwright');
 const server=http.createServer((req,res)=>{
  const file=path.join(process.cwd(),new URL(req.url,'http://x').pathname.replace(/\/$/,'/index.html'));
  if(!file.startsWith(process.cwd())||!fs.existsSync(file)||fs.statSync(file).isDirectory()){res.writeHead(404);return res.end();}
  res.setHeader('content-type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':file.endsWith('.json')?'application/json':'text/html');fs.createReadStream(file).pipe(res);
 });
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH || (fs.existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined),headless:true,args:['--no-sandbox']});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 try {
  const page=await browser.newPage({viewport:{width:1280,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let active=0,maxActive=0;
  await page.route('**/korea-site/**',async route=>{
   const name=new URL(route.request().url()).pathname.split('/').pop();
   if(name==='meta.json')return route.fulfill({json:meta});
   if(name==='buyers.json')return route.fulfill({json:buyers});
   active++; maxActive=Math.max(active,maxActive);
   await new Promise(r=>setTimeout(r,100));active--;
   try {await route.fulfill({json:shards[Number(name.slice(0,4))]});} catch {} // aborted requests
  });
  const base=`http://127.0.0.1:${server.address().port}`;
  await page.goto(base+'/#dataset=korea');
  await page.waitForFunction(()=>document.querySelector('#korea-scan-status').textContent.includes('matches retained'));
  assert.equal(await page.locator('.main-table tbody tr').count(),50);
  await page.locator('#korea-scan-next').click();
  await page.waitForFunction(()=>document.querySelector('#korea-scan-status').textContent.includes('page 2:'));
  assert.equal(await page.locator('.main-table tbody tr').count(),50);
  const downloadPromise=page.waitForEvent('download');await page.locator('#export-json').click();
  const download=await downloadPromise;
  assert.match(download.suggestedFilename(),/scan-page-2/);
  const exported=JSON.parse(fs.readFileSync(await download.path(),'utf8'));
  assert.equal(exported.count,50);assert.match(exported.dataset,/page 2 ONLY/);
  // Existing predicates: Korea is unevaluated, not a zero or a signal.
  await page.locator('#advanced-filters').evaluate(el=>el.open=true);
  await page.selectOption('#assessment','zero');
  assert.equal(await page.locator('#export-csv').isDisabled(),true);
  await page.locator('#korea-scan-start').click();
  await page.waitForFunction(()=>document.querySelector('#korea-scan-status').textContent.includes('scan complete'));
  assert.match(await page.locator('#korea-scan-status').textContent(),/0 total matches/);
  await page.selectOption('#assessment','unevaluated');
  await page.locator('#korea-scan-start').click();
  await page.locator('#search').fill('does not exist');
  await page.waitForTimeout(250);
  assert.equal(await page.locator('#export-csv').isDisabled(),true);
  assert.match(await page.locator('#korea-scan-status').textContent(),/Filters changed/);
  await page.locator('#korea-scan-start').click();await page.locator('#korea-scan-cancel').click();
  await page.waitForTimeout(250);assert.match(await page.locator('#korea-scan-status').textContent(),/cancelled/);
  // Buyer mode and country/source selector remain usable; in-flight nationwide response cannot overwrite it.
  await page.locator('#korea-results button').first().click();
  await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('305'));
  assert.equal(await page.locator('#korea-scan').isHidden(),true);
  // Global scope uses every published registry collection, not candidate imports.
  const ordinary = await page.evaluate(({meta,shard,buyer}) => koreaRecords(meta,shard,buyer), {meta,shard:shards[0],buyer:buyers[0]});
  const files = await page.evaluate(() => Object.values(globalThis.DATASET_FILES || {}).flat());
  for (const file of new Set(files)) await page.route('**/' + file, route => route.fulfill({json:ordinary.slice(0,3).map(c => ({...c, id: file + ':' + c.id}))}));
  await page.goto(base+'/#dataset=global');
  await page.waitForFunction(()=>/matches retained|Scan failed/.test(document.querySelector('#korea-scan-status').textContent));
  assert.match(await page.locator('#korea-scan-status').textContent(), /matches retained/);
  assert.equal(await page.locator('#country').inputValue(),'All published collections');
  assert.equal(await page.locator('#korea-picker').isHidden(),true);
  assert.equal(await page.locator('#korea-scan').isVisible(),true);
  assert.ok(await page.locator('.collection-context').count()>0);
  assert.ok(await page.locator('#indicator option').count()>10);
  const globalDownloadPromise=page.waitForEvent('download');await page.locator('#export-json').click();
  const globalDownload=await globalDownloadPromise;
  const globalExport=JSON.parse(fs.readFileSync(await globalDownload.path(),'utf8'));
  assert.ok(globalExport.records.every(c=>c.collectionId && c.originalId));
  assert.ok(globalExport.records.some(c=>c.collectionId==='korea'));
  assert.ok(globalExport.records.some(c=>c.collectionId==='decp'));
  assert.ok(!globalExport.records.some(c=>/candidate|expansion|base|seap/.test(c.collectionId)));
  assert.deepEqual(errors,[]); assert.ok(maxActive<=2); // aborted requests can overlap network teardown
  console.log('Korea browser integration tests passed');
 } finally {await browser.close();await new Promise(r=>server.close(r));}
}
(async()=>{await unitTests();if(!process.argv.includes('--unit'))await browserTests();})().catch(e=>{console.error(e);process.exitCode=1;});
