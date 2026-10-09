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
check(raw.records.length===1865);check(rows.length===2289);
check(coverage.procedureMapping.competitive.includes('Dialogue compétitif'));
check(!coverage.procedureMapping.observed.includes('Dialogue compétitif')); // mapping fix has no effect on this snapshot
check(new Set(raw.records.map(r=>r.acheteur_id+':'+r.id)).size===new Set(rows.filter(r=>!r.verification.addedFromFeed).map(r=>r.buyerSiret+':'+r.contractId)).size);
// Evidenced splits: 3 groups -> 13 rows; members share exactly one buyer+identifier and link to each other.
const split=rows.filter(r=>r.procedureGroup);check(split.length===992);check(new Set(split.map(r=>r.procedureGroup.id)).size===237);
check(split.filter(r=>r.procedureGroup.kind==='lots').length===10);check(rows.every(r=>!r.initialConflicts.length&&!r.modificationConflicts.length));
for(const r of split){const same=rows.filter(x=>x.buyerSiret===r.buyerSiret&&x.contractId===r.contractId).map(x=>x.id).sort();
 check(JSON.stringify(same)===JSON.stringify([...r.procedureGroup.members].sort()));check(!r.identityAmbiguous&&!run('isAmbiguousCityContract',r));
 check(r.procedureGroup.kind!=='lots'||(r.lotId&&r.noticeId&&r.sourceRowVariants.length===1));
 for(const d of r.possibleDuplicateOf||[]){const o=rows.find(x=>x.id===d);check(o&&o.possibleDuplicateOf.includes(r.id));}}
check(rows.filter(r=>r.possibleDuplicateOf).length===25);check(rows.filter(r=>run('duplicateShadow',r)).length===15);
// Route evidence settled the other clusters: distinct references (cleared) or one confirmed member (folded, two amounts kept).
check(rows.filter(r=>r.verification.duplicateCleared).length===50&&rows.filter(r=>r.verification.foldedRows).length===10);
const joint=rows.filter(r=>r.contractId==='2024VDAO017006');check(joint.length===1&&joint[0].supplierIds.length===1&&joint[0].unconfirmedHolders.length===1&&!joint[0].procedureGroup);
// Every source row is represented exactly once.
check(rows.reduce((n,r)=>n+r.sourceRowVariants.length,0)+(coverage.counts.duplicateRowsDeduplicated||0)===raw.records.length);
// Feed reconciliation: every record has a status; statuses and additions are as published by tools/decp_feeds.py.
const status={};for(const r of rows)status[r.verification.status]=(status[r.verification.status]||0)+1;
check(JSON.stringify(status)===JSON.stringify({'sources-agree':1782,'notice-checked':10,'single-source':400,'sources-disagree':97}));
check(rows.filter(r=>r.verification.majority).length===62&&rows.filter(r=>r.feedSource?.startsWith('portal_')).length===78);
check(rows.filter(r=>r.verification.addedFromFeed).length===435&&coverage.counts.contractsAddedFromFeeds===435);
for(const r of rows){const pos=(r.amountSources||[]).map(s=>s.amount).filter(a=>a!=null&&a>10);check(r.amount==null||r.amount===0||pos.includes(r.amount));check(!(r.amount>0&&r.amount<=10));}
check(!rows.some(r=>r.id==='decp-21210231300013-2023VDAO1642'));
const disputed=rows.filter(r=>r.offersConflict);check(disputed.length===12);check(disputed.filter(r=>r.offersConflict.feed).length===5);
check(disputed.every(r=>r.offers===null&&!(r.offersConflict.feed||[r.offersConflict.notice]).includes(r.offersConflict.decp)));
check(run('getAssessment',rows.find(r=>r.contractId==='2024VDAO1642')).checks.find(c=>c.id==='single-bid').status==='unknown');
check(rows.filter(r=>r.project?.id==='dijon-maison-des-associations').length===26);
check(new Set(rows.map(r=>r.buyerSiret)).size===6);
check(rows.filter(r=>run('isAmbiguousCityContract',r)).length===0);
check(rows.filter(r=>r.modificationConflicts.length).length===0);
check(rows.reduce((n,r)=>n+r.history.filter(e=>e.kind==='modification').length,0)===490);
check(rows.filter(r=>r.supplierProfiles.length).length===2209);
check(identities.identities.length===2710);
const feeds=JSON.parse(require('node:zlib').gunzipSync(fs.readFileSync('data/decp-feeds-raw.json.gz')));
const portals=JSON.parse(require('node:zlib').gunzipSync(fs.readFileSync('data/city-portals-raw.json.gz')));
const feedUids=new Set([...feeds.records,...portals.records].map(f=>f.uid));
for(const r of rows){
 if(r.verification.addedFromFeed){check(feedUids.has(r.feedUid)&&!raw.records.some(s=>s.acheteur_id===r.buyerSiret&&s.id===r.contractId&&s.datenotification===r.date&&r.supplierIds.some(h=>h.id===s.titulaire_id_1)));check(r.source===feeds.source.dataset_page||portals.sources.some(p=>p.dataset_page===r.source));}
 else{
 const variants=raw.records.filter(s=>s.acheteur_id===r.buyerSiret&&s.id===r.contractId);
 check(variants.length>0);
 const where=new URL(r.source).searchParams.get('where');
 check(where.includes(`acheteur_id='${r.buyerSiret}'`)&&where.includes(`id='${r.contractId.replaceAll("'","''")}'`));}
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
for(const [indicator,count] of [['single-bid',98],['long-contract',6],['direct-award',57],['late-publication',66],['repeated-single-bid',11],['amount-increase',3],['supplier-concentration',0],['repeated-direct-award',6]])check(run('selectContracts',rows,{indicator}).length===count);
for(const mode of ['buyer','supplier','sector','project']){
 const arranged=run('arrangeGroups',rows,mode);check(arranged.rows.length===2289);check(new Set(arranged.rows.map(r=>r.id)).size===2289);
}
for(const sort of ['score','score-asc','amount','amount-asc','date','date-asc','sector','sector-desc','buyer','supplier','offers','increase'])check(run('selectContracts',rows,{sort}).length===2289);
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
// A procedure group must list the record itself; disputed offers must stay null; an extra row reusing the identifier stays ambiguous.
{const lot=JSON.parse(JSON.stringify(split[0]));
 for(const mutate of [g=>g.members=g.members.filter(id=>id!==lot.id),g=>g.kind='guess',g=>g.members=[lot.id]]){const bad=JSON.parse(JSON.stringify(lot));mutate(bad.procedureGroup);assert.throws(()=>run('validateContracts',[bad]));}
 const withOffers=JSON.parse(JSON.stringify(disputed[0]));withOffers.offers=2;assert.throws(()=>run('validateContracts',[withOffers]));
 const siblings=split.filter(r=>r.procedureGroup.id===lot.procedureGroup.id).map(r=>JSON.parse(JSON.stringify(r)));
 const intruder={...JSON.parse(JSON.stringify(siblings[0])),id:'intruder',procedureGroup:null,offersConflict:null};
 const prepared=run('prepareContracts',[...siblings,intruder]);check(prepared.every(r=>r.identityAmbiguous));
 check(run('prepareContracts',siblings).every(r=>!r.identityAmbiguous));}
console.log(`${checks} city-cohort assertions passed: completeness, exclusions, identities, scores, filters, sorts and grouping.`);
