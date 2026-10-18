'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('script.js', 'utf8');
const ctx = vm.createContext({ URL, URLSearchParams, structuredClone, setTimeout });
vm.runInContext(source, ctx);
const meta = { columns: ['contractNo','name','date','latestAmount','supplier','supplierKind','method'], supplierKinds:['corporation'], methods:['Open'], businessTypes:[],linkKinds:[],link:'' };
const buyers = [['A','Alpha','',7,0]];
const shard = {buyers:{A:Array.from({length:7},(_,i)=>['K'+i,'School','2025-01-01',i+1,'Company',0,0])},demand:[],legal:[]};
ctx.meta=meta;ctx.buyers=buyers;ctx.shard=shard;
const ordinary = JSON.parse(vm.runInContext('JSON.stringify(koreaRecords(meta, shard, buyers[0]))',ctx));
// Country, inclusive date bounds and independently targeted fields compose with indicators.
ctx.records = [...ordinary, {...ordinary[0], id:'unknown-date', date:null}];
assert.equal(vm.runInContext('selectContracts(records, {country:"KOR",dateFrom:"2025-01-01",dateTo:"2025-01-01",buyer:"alpha",supplier:"company",procedure:"open"}).length',ctx),7);
assert.equal(vm.runInContext('selectContracts(records, {country:"FRA"}).length',ctx),0);
assert.equal(vm.runInContext('selectContracts(records, {dateFrom:"2025-01-02"}).length',ctx),0);
assert.equal(vm.runInContext('selectContracts(records, {supplier:"not-published"}).length',ctx),0);
assert.equal(vm.runInContext('recordCountry({dataFamily:"decp"})',ctx),'FRA');
assert.equal(vm.runInContext('hashToViewState("#dataset=global&from=2025-01-01&country=KOR")["date-from"]',ctx),'2025-01-01');
(async()=>{
 const collections=[{key:'one',label:'First source'},{key:'two',label:'Second source'}];
 let active=0,max=0;
 const args={collections,loadCollection:async()=>{active++;max=Math.max(max,active);await new Promise(r=>setTimeout(r,1));active--;return ordinary;},
 korea:async()=>({meta,buyers,fetchShard:async()=>shard}),limit:5,predicate:()=>true};
 const ids=[];
 for(let offset=0;offset<21;offset+=5){
  ctx.args={...args,offset};
  const result=await vm.runInContext('scanPublishedPage(args)',ctx);
  assert.ok(result.rows.length<=5);ids.push(...result.rows.map(c=>c.id));
  assert.equal(result.hasMore,offset+5<21);
  assert.equal(result.complete,offset+5>=21);
  for(const c of result.rows){assert.ok(c.originalId);assert.ok(c.collectionLabel);ctx.record=c;assert.equal(vm.runInContext('getVigilanceScore(record)',ctx),null);}
 }
 assert.equal(ids.length,21);assert.equal(new Set(ids).size,21);assert.equal(max,1);
 assert.equal(ids[0],'one::koneps-K0');assert.equal(ids[7],'two::koneps-K0');assert.equal(ids[14],'korea::koneps-K0');
 // Filters are applied before retention, including unevaluated vs zero.
 ctx.args={...args,predicate:c=>c.amount>=5,offset:0,limit:200};
 let result=await vm.runInContext('scanPublishedPage(args)',ctx);assert.equal(result.rows.length,9);
 ctx.args={...args,predicate:c=>{ctx.record=c;return vm.runInContext('selectContracts([record], {assessment:"zero"}).length > 0',ctx);}};
 result=await vm.runInContext('scanPublishedPage(args)',ctx);assert.equal(result.matches,0);assert.equal(result.complete,true);
 const abort=new AbortController();let release;
 ctx.args={...args,signal:abort.signal,loadCollection:()=>new Promise(r=>release=r)};
 const pending=vm.runInContext('scanPublishedPage(args)',ctx);abort.abort();release(ordinary);
 await assert.rejects(pending,{name:'AbortError'});
 ctx.record={...ordinary[0],collectionId:'one',collectionLabel:'First source',originalId:ordinary[0].id};
 assert.equal(vm.runInContext('exportRecord(record).collectionId',ctx),'one');
 assert.equal(vm.runInContext('hashToViewState("#dataset=all").dataset',ctx),'decp');
 assert.equal(vm.runInContext('hashToViewState("#dataset=global").dataset',ctx),'global');
 console.log('Published collections union: bounded paging, source context, unknowns, filters, cancellation and aliases passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
