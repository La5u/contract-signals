const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx=vm.createContext({URL});vm.runInContext(fs.readFileSync('script.js','utf8'),ctx);
const run=(fn,...args)=>{ctx.args=args;return vm.runInContext(`${fn}(...args)`,ctx);};
let checks=0;const check=(v,message)=>{assert.ok(v,message);checks++;};
const base={id:'test',buyer:'Buyer',description:'Test',dataStatus:'verified',amount:null,offers:null,durationMonths:null,directAward:null};
const score=c=>run('getVigilanceScore',c);
const assessment=c=>run('getAssessment',c);
const rule=(c,id)=>assessment(c).checks.find(r=>r.id===id);
check(score(base)===null,'unknown is not zero');
check(assessment(base).evaluated===0);
check(score({...base,directAward:false})===0,'zero requires evaluated negative check');
for(const amount of [null,0,1,99999,100000,1e6,1e12]){
 check(score({...base,amount,directAward:true,offers:1})===18,'direct award independent of amount');
 check(rule({...base,amount,directAward:true,offers:1},'single-bid').status==='not-applicable');
 check(score({...base,amount,directAward:false,offers:1})===12);
 check(score({...base,amount})===null);
}
check(rule({...base,offers:1},'single-bid').applicability==='unknown');
check(rule({...base,offers:0,directAward:false},'single-bid').status==='unknown');
for(const c of [base,{...base,directAward:true},{...base,offers:1,directAward:false}])check(score(c)===score({...c,officialFinding:true}));
check(score({...base,findingScope:'aggregate',officialFinding:true,durationMonths:240,directAward:true})===null);
for(const dataFamily of ['decp','boamp','audit']){
 for(const conflict of [{initialConflicts:['amount']},{modificationConflicts:[{id:'1',fields:['amount']}]},{identityAmbiguous:true},{dataStatus:'unverified'}]){
  const c={...base,dataFamily,directAward:true,durationMonths:360,...conflict};check(score(c)===null);check(run('getIndicators',c).length===0);
 }
}
for(const [duration,weight] of [[119,null],[120,8],[121,8.1],[180,16],[240,24],[360,40],[600,40]])check(rule({...base,durationMonths:duration},'long-contract').weight===weight);
const evo=(a,b)=>({...base,dataFamily:'decp',priceType:'Définitif ferme',date:'2024-01-01',amount:a,initialConflicts:[],history:[{kind:'initial',date:'2024-01-01',amount:a},{kind:'modification',id:'1',date:'2025-01-01',amount:b}]});
check(rule(evo(100,120),'amount-increase').status==='clear');
check(rule(evo(100,121),'amount-increase').weight===8.4);
check(rule(evo(1000000,1210000),'amount-increase').weight===8.4);
check(rule(evo(100,200),'amount-increase').weight===40);
check(rule({...evo(100,200),priceType:'Définitif révisable'},'amount-increase').status==='not-applicable');
check(rule({...base,dataFamily:'decp',priceType:'Définitif ferme',history:[{kind:'initial'}],initialConflicts:[]},'amount-increase').status==='unknown');
check(run('getAmountEvolution',{...evo(100,200),history:[{kind:'initial',date:'2024-01-01',amount:100},{kind:'modification',date:'2025-01-01',amount:null}]}).status==='unavailable');
const context={known:10,total:10,single:6,rate:.6,coverage:1,sufficient:true,cpvGroup:'713'};
const supplier={known:10,total:10,wins:6,share:.6,coverage:1,sufficient:true,cpvGroup:'713',directCount:3,directKnownCount:3,supplierContracts:3};
for(const [rate,expected] of [[.59,null],[.6,12],[.61,12.7],[.8,26],[1,40]]){
 check(rule({...base,directAward:false,offers:1,competitionContext:{...context,rate}},'repeated-single-bid').weight===expected);
 check(rule({...base,supplierContext:{...supplier,share:rate}},'supplier-concentration').weight===expected);
}
check(rule({...base,directAward:false,offers:1,competitionContext:{...context,sufficient:false}},'repeated-single-bid').status==='unknown');
check(rule({...base,directAward:true,supplierContext:{...supplier,directCount:2,directKnownCount:2,supplierContracts:3}},'repeated-direct-award').status==='unknown');
check(rule({...base,directAward:true,supplierContext:{...supplier,directCount:2}},'repeated-direct-award').status==='clear');
for(const [count,weight] of [[3,18],[4,24],[7,42],[10,60],[100,60]])check(rule({...base,directAward:true,supplierContext:{...supplier,directCount:count}},'repeated-direct-award').weight===weight);
check(score({...base,directAward:true,offers:1,supplierContext:{...supplier,share:1,directCount:10},durationMonths:360})===100,'max families, cap 100');
check(score({...base,directAward:false,offers:1,competitionContext:{...context,rate:.8},supplierContext:{...supplier,share:.7}})===26,'correlated signals not added');
const notice={id:'n',version:'01',kind:'initial',source:'https://example.org/',publicationDate:'2025-02-01',deadline:'2025-02-15T00:00:00Z',procedureType:'open',accelerated:false,previousNoticeIds:[]};
const bidding=()=>({...base,consultation:{procedureId:'p',lotId:'lot',initialNoticeId:'n',searchComplete:true,exclusions:[],notices:[{...notice}]}});
let c=bidding();check(score(c)===10.7);c.consultation.notices[0].deadline='2025-02-16T00:00:00Z';check(score(c)===0);
c=bidding();c.consultation.notices[0].deadline='2025-02-04T00:00:00Z';check(score(c)===40);
for(const mutate of [c=>c.consultation.searchComplete=false,c=>c.consultation.notices[0].accelerated=null,c=>c.consultation.notices[0].deadline=null,c=>c.consultation.notices.push({...notice})]){c=bidding();mutate(c);check(score(c)===null);}
c=bidding();c.consultation.notices.push({...notice,id:'corr',version:'02',kind:'correction',publicationDate:'2025-02-10',deadline:'2025-03-01T00:00:00Z',previousNoticeIds:['n']});check(score(c)===0);
const datasets=['contracts','decp-history','decp-cities','consultations','tours-notices'];
const expected={contracts:[68,2665,277],'decp-history':[355,1835,404],'decp-cities':[172,974,124],consultations:[10,0,0],'tours-notices':[66,0,0]};
for(const file of datasets){
 const rows=run('prepareContracts',JSON.parse(fs.readFileSync(`data/${file}.json`)));
 const values=rows.map(score), exp=expected[file];
 check(values.filter(s=>s===null).length===exp[0]);check(values.filter(s=>s===0).length===exp[1]);check(values.filter(s=>s>0).length===exp[2]);
 for(const r of rows){
  const a=assessment(r),s=score(r);
  check(a.checks.length===8&&a.applicable+a.unknownApplicability+a.notApplicable===8);
  check(a.evaluated<=a.applicable);
  check(s===null ? a.evaluated===0 : a.evaluated>0&&s>=0&&s<=100);
  check(score({...r,officialFinding:!r.officialFinding})===s,'finding never changes score');
  if(!r.history)check(score({...r,amount:1e12})===s,'amount never changes standalone heuristics');
 }
 for(const order of ['score','score-asc']){
  const sorted=run('selectContracts',rows,{sort:order});const pos=sorted.findIndex(r=>score(r)===null);
  check(pos===-1||sorted.slice(pos).every(r=>score(r)===null),'unknown last both directions');
 }
 check(run('selectContracts',rows,{assessment:'unevaluated'}).length===exp[0]);
 check(run('selectContracts',rows,{assessment:'zero'}).length===exp[1]);
 check(run('selectContracts',rows,{flagged:true}).length===exp[2]);
 if(file==='contracts'){
  check(run('selectContracts',rows,{official:true}).length===8);
  check(run('selectContracts',rows,{indicator:'official-finding'}).length===8);
  check(run('selectContracts',rows,{sort:'official'}).slice(0,8).every(r=>r.officialFinding===true));
 }
}
// Single-vendor software maintenance: context label only, never read by scoring.
const softwareCounts={contracts:4,'decp-history':25,'decp-cities':1,consultations:0,'tours-notices':0};
for(const file of datasets){
 const rows=run('prepareContracts',JSON.parse(fs.readFileSync(`data/${file}.json`)));
 const labelled=run('selectContracts',rows,{legal:'fr-software'});
 check(labelled.length===softwareCounts[file]);
 for(const r of labelled){const l=run('softwareMaintenanceContext',r);check(r.directAward!==false&&['direct','R2122-3','one-offer'].includes(l.vendor)&&['cpv','text'].includes(l.software));}
}
const scoringSource=fs.readFileSync('script.js','utf8').split('function getAssessment(c)')[1].split('function prepareContracts')[0];
check(!/softwareMaintenanceContext|secop2PublicCounterparty/.test(scoringSource),'context labels are never read by scoring');
check(run('softwareMaintenanceContext',{dataFamily:'boamp',cpv:'72267000',description:'Maintenance du progiciel X',directAward:false,offers:1})===null,'competitive single offer is not a single-vendor context');
check(run('softwareMaintenanceContext',{dataFamily:'decp',cpv:'50324200-4',description:'Maintenance et garantie de la station totale avec mises à jour des logiciels',directAward:true,offers:1})===null,'equipment with bundled software is not labelled');
check(run('softwareMaintenanceContext',{dataFamily:'secop2',cpv:'72267000',description:'Maintenance du progiciel X',directAward:true})===null,'French label only on French families');
console.log(`${checks} active v3 assertions passed: coverage, null/zero, independence, thresholds, exclusions and full datasets.`);
