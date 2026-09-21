const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ctx = vm.createContext({ URL });
vm.runInContext(fs.readFileSync('script.js','utf8'),ctx);
const run=(fn,...args)=>{ctx.args=args;return vm.runInContext(`${fn}(...args)`,ctx);};
let checks=0;
const check=(value)=>{assert.ok(value);checks++;};
const data=JSON.parse(fs.readFileSync('data/decp-cities.json'));
const raw=JSON.parse(fs.readFileSync('data/decp-cities-raw.json'));
const coverage=JSON.parse(fs.readFileSync('data/decp-cities-coverage.json'));
const identities=JSON.parse(fs.readFileSync('data/supplier-identities.json'));
const rows=run('prepareContracts',data);
check(raw.records.length===1865);check(rows.length===1270);
check(new Set(raw.records.map(r=>r.acheteur_id+':'+r.id)).size===rows.length);
check(new Set(rows.map(r=>r.buyerSiret)).size===6);
check(rows.filter(r=>run('isAmbiguousCityContract',r)).length===172);
check(rows.filter(r=>r.modificationConflicts.length).length===7);
check(rows.reduce((n,r)=>n+r.history.filter(e=>e.kind==='modification').length,0)===365);
check(rows.filter(r=>r.supplierProfiles.length).length===148);
check(identities.identities.length===100);
for(const r of rows){
 const variants=raw.records.filter(s=>s.acheteur_id===r.buyerSiret&&s.id===r.contractId);
 check(variants.length>0);
 const where=new URL(r.source).searchParams.get('where');
 check(where.includes(`acheteur_id='${r.buyerSiret}'`)&&where.includes(`id='${r.contractId.replaceAll("'","''")}'`));
 if(run('isAmbiguousCityContract',r)){
  check(run('getIndicators',r).length===0);check(r.competitionContext===null&&r.supplierContext===null);
  check(run('getAmountEvolution',r).status==='unavailable');
 }
 check(run('getVigilanceScore',r)===run('getVigilanceScore',{...r,supplierProfiles:[]}));
 for(const p of r.supplierProfiles){
  check(p.diffusionStatus==='O'&&p.status==='available');
  check(r.supplierIds.some(s=>(s.identifierType==='SIRET'&&s.id.slice(0,9)===p.siren)||(s.identifierType==='SIREN'&&s.id===p.siren)));
  check(identities.identities.some(i=>i.siren===p.siren&&i.name===p.name&&i.source===p.source));
 }
}
for(const b of coverage.scope.buyers){
 const pages=raw.queries.filter(q=>q.buyerSiret===b.siret);
 check(pages.reduce((n,p)=>n+p.count,0)===raw.totals[b.siret]);
 check(pages.every((p,i)=>p.offset===i*100&&p.total===raw.totals[b.siret]));
}
for(const [indicator,count] of [['single-bid',52],['long-contract',4],['direct-award',66],['repeated-single-bid',11],['amount-increase',2],['supplier-concentration',0],['repeated-direct-award',3]])check(run('selectContracts',rows,{indicator}).length===count);
for(const mode of ['buyer','supplier','sector','project']){
 const arranged=run('arrangeGroups',rows,mode);check(arranged.rows.length===1270);check(new Set(arranged.rows.map(r=>r.id)).size===1270);
}
for(const sort of ['score','score-asc','amount','amount-asc','date','date-asc','sector','sector-desc','buyer','supplier','offers','increase'])check(run('selectContracts',rows,{sort}).length===1270);
const enriched=rows.find(r=>r.supplierProfiles.length);
check(run('selectContracts',rows,{search:enriched.supplierProfiles[0].name}).some(r=>r.id===enriched.id));
for(const mutate of [p=>p.siren='000000000',p=>p.diffusionStatus='P',p=>p.source='javascript:alert(1)',p=>p.status='unavailable']){
 const invalid=JSON.parse(JSON.stringify(enriched));mutate(invalid.supplierProfiles[0]);assert.throws(()=>run('validateContracts',[invalid]));checks++;
}
const base={id:'synthetic-test',buyer:'Buyer',buyerSiret:'21350238800019',contractId:'test',description:'Test',dataStatus:'synthetic',dataFamily:'decp',cohortId:'decp-six-cities-2024-2025',date:'2024-01-01',amount:1,offers:1,cpv:'71300000-1',directAward:false,initialConflicts:[],modificationConflicts:[],supplierIds:[{id:'12345678900011',identifierType:'SIRET'}]};
let samples=Array.from({length:10},(_,i)=>({...base,id:'sample-'+i,contractId:'contract-'+i}));
let prepared=run('prepareContracts',samples);check(prepared[0].competitionContext.sufficient);check(prepared[0].supplierContext.sufficient);
check(run('getIndicators',prepared[0]).some(i=>i.id==='repeated-single-bid'));
check(!run('prepareContracts',samples.slice(0,9))[0].competitionContext.sufficient);
let coverageSamples=[...samples,...Array.from({length:2},(_,i)=>({...base,id:'unknown-'+i,contractId:'unknown-'+i,offers:null}))];
check(run('prepareContracts',coverageSamples)[0].competitionContext.sufficient);
coverageSamples.push({...base,id:'unknown-2',contractId:'unknown-2',offers:null});
check(!run('prepareContracts',coverageSamples)[0].competitionContext.sufficient);
let duplicate=run('prepareContracts',[...samples,{...samples[0],id:'duplicate-other-row'}]);
check(duplicate[0].competitionContext===null&&duplicate[10].competitionContext===null);
check(!duplicate[1].competitionContext.sufficient);
let mixed=run('prepareContracts',[...samples,...samples.map((c,i)=>({...c,id:'other-'+i,contractId:'other-'+i,cohortId:'decp-paris-ardeche-2024-2025'}))]);
check(mixed[0].competitionContext.total===10&&mixed[10].competitionContext.total===10);
console.log(`${checks} city-cohort assertions passed: completeness, exclusions, identities, scores, filters, sorts and grouping.`);
