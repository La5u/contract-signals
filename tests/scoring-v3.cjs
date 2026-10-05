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
// French direct award: below the legal threshold in force it is the lawful default (not applicable), missing amount is unknown.
for(const amount of [null,0,1,99999,100000,1e6,1e12]){
 check(rule({...base,amount,directAward:true,offers:1},'single-bid').status==='not-applicable');
 check(score({...base,amount,directAward:false,offers:1})===12);
 check(score({...base,amount})===null);
}
const dated={...base,date:'2024-06-01',cpv:'30000000-1',offers:1};
const direct=(c)=>rule({...dated,directAward:true,...c},'direct-award');
check(direct({amount:39999.99}).status==='not-applicable'&&/40,000/.test(direct({amount:39999.99}).reason),'below 40k supplies: not applicable, threshold cited');
check(direct({amount:40000}).status==='signal'&&direct({amount:40000}).weight===18,'at 40k: signal');
check(direct({amount:1e6}).status==='signal');
check(direct({amount:null}).status==='unknown'&&direct({amount:null}).applicability==='unknown','missing amount: unknown, never scored');
check(direct({amount:0}).status==='unknown');
check(score({...dated,directAward:true,amount:null})===null,'missing amount direct award alone is not assessed');
check(direct({amount:24000,date:'2019-06-01'}).status==='not-applicable'&&direct({amount:26000,date:'2019-06-01'}).status==='signal','25k threshold before 2020');
check(direct({amount:30000,date:'2019-12-31'}).status==='signal'&&direct({amount:30000,date:'2020-01-15'}).status==='unknown','1 Jan 2020 change: transition window is unknown');
check(direct({amount:30000,date:'2020-09-01'}).status==='not-applicable','40k from 2020 once the window has passed');
const works={cpv:'45233120-6'};
check(direct({...works,amount:99999}).status==='not-applicable'&&direct({...works,amount:100000}).status==='signal','works exemption: 100k');
check(direct({...works,amount:60000,date:'2022-03-01'}).status==='not-applicable'&&direct({...works,amount:60000,date:'2025-03-01'}).status==='not-applicable','works exemption in force 2022 and 2025');
check(direct({...works,amount:80000,date:'2026-03-01'}).status==='not-applicable','works 100k permanent from 2026');
check(direct({...works,amount:80000,date:'2020-10-01'}).status==='signal'&&direct({...works,amount:60000,date:'2020-10-01'}).status==='unknown','works 70k from 24 Jul 2020 (40k to 70k uncertain during the transition)');
check(direct({...works,amount:80000,date:'2020-12-20'}).status==='unknown','70k to 100k right after the ASAP law: uncertain');
check(direct({...works,amount:50000,date:'2020-12-20'}).status==='unknown','overlapping changes: the 180-day window also includes the 40k works regime');
check(direct({...works,amount:39999,date:'2020-12-20'}).status==='not-applicable','below all three possible works thresholds');
check(direct({...works,amount:100000,date:'2020-12-20'}).status==='signal','at or above all possible works thresholds');
check(direct({...works,amount:50000,date:'2021-01-19'}).status==='unknown','earlier works transition still inside 180 days');
check(direct({...works,amount:50000,date:'2021-01-20'}).status==='not-applicable','earlier works transition ends at exactly 180 days');
for(const date of ['2024-99-99','2024-02-30','2023-02-29','2024-00-01','2024-01-00','2024-06-01junk']) {
 check(direct({amount:50000,date}).status==='unknown',`invalid calendar date ${date}: no direct-award points`);
}
check(direct({amount:50000,date:'2024-02-29'}).status==='signal','valid leap day remains assessable');
check(direct({amount:80000}).status==='signal'&&direct({amount:80000,cpv:undefined}).status==='unknown','CPV missing between supplies and works thresholds: unknown');
check(direct({amount:30000,cpv:undefined}).status==='not-applicable'&&direct({amount:150000,cpv:undefined}).status==='signal');
check(direct({amount:50000,date:'2026-02-01'}).status==='signal'&&direct({amount:50000,date:'2026-04-10'}).status==='unknown'&&direct({amount:50000,date:'2026-10-01'}).status==='not-applicable','60k supplies/services from 1 Apr 2026');
check(direct({amount:90000,date:'2024-06-01',date:undefined}).status==='unknown');
check(rule({...dated,directAward:true,amount:10000,supplierContext:{known:10,total:10,wins:3,share:.3,coverage:1,sufficient:true,cpvGroup:'300',directCount:3,directKnownCount:3,supplierContracts:3}},'repeated-direct-award').status==='signal','repeated direct awards still count small awards');
check(direct({amount:30000,directAward:false}).status==='clear'&&direct({amount:30000,directAward:null}).status==='unknown');
// Late publication relative to the buyer (leave-one-out median over at least 10 dated rows of the cohort).
const siret=b=>String(b.charCodeAt(0)).padStart(14,'0');
const late=(id,buyer,delay,more={})=>({...base,id,buyer,buyerSiret:siret(buyer),dataFamily:'decp',cohortId:'t',date:'2024-01-01',publicationDate:new Date(Date.parse('2024-01-01')+delay*864e5).toISOString().slice(0,10),...more});
const lateRule=c=>rule(c,'late-publication');
const solo=late('solo','S',300);
check(lateRule(solo).status==='signal'&&lateRule(solo).weight===graduatedLate(300),'no baseline: whole delay counts');
check(/No usual delay is established/.test(lateRule(solo).reason));
function graduatedLate(d,from=120){return Math.round((8+8*Math.min(1,Math.max(0,(d-from)/(730-from))))*10)/10;}
const batch=[...Array.from({length:12},(_,i)=>late('b'+i,'B',200)),late('bout','B',900)];
const prepared=run('prepareContracts',batch);
const byId=id=>prepared.find(r=>r.id===id);
check(lateRule(byId('b0')).status==='clear'&&/within this buyer.s usual delay \(median 200 days over 12 other records\)/.test(lateRule(byId('b0')).reason),'delay equal to buyer habit: clear');
check(lateRule(byId('bout')).status==='signal'&&lateRule(byId('bout')).weight===graduatedLate(700,240),'excess over the buyer median is what counts (900-200), from 240 days in the DECP');
// DECP (score 3.3): with an established usual delay, the excess counts from 240 days; other families keep 120.
const mid=run('prepareContracts',[...Array.from({length:12},(_,i)=>late('m'+i,'M',200)),late('mout','M',430)]).find(r=>r.id==='mout');
check(lateRule(mid).status==='clear','DECP: 230 days later than usual stays clear');
const midBoamp=run('prepareContracts',[...Array.from({length:12},(_,i)=>late('n'+i,'N',200,{dataFamily:'boamp'})),late('nout','N',430,{dataFamily:'boamp'})]).find(r=>r.id==='nout');
check(lateRule(midBoamp).status==='signal'&&lateRule(midBoamp).weight===graduatedLate(230),'BOAMP keeps the 120-day excess');
check(byId('b0').latePublicationBaseline.median===200&&byId('b0').latePublicationBaseline.others===12,'leave-one-out: the row is not in its own baseline');
check(byId('bout').latePublicationBaseline.median===200,'outlier excluded from its own median');
const few=run('prepareContracts',Array.from({length:9},(_,i)=>late('f'+i,'F',300)));
check(few.every(r=>r.latePublicationBaseline===null&&lateRule(r).status==='signal'),'fewer than 10 dated rows: no baseline');
const ten=run('prepareContracts',Array.from({length:10},(_,i)=>late('t'+i,'T',300)));
check(ten.every(r=>r.latePublicationBaseline?.others===9&&lateRule(r).status==='clear'),'exactly 10 dated rows establish a baseline');
// Compare every leave-one-out baseline with an independently sorted median; cover
// both parities, duplicates, and removal below/at/above the middle.
for(const delays of [Array.from({length:10},(_,i)=>i*100),Array.from({length:11},(_,i)=>i*100),[0,0,100,100,200,300,300,400,500,900]]) {
 const rows=delays.map((d,i)=>late('median'+i,'V',d));
 run('assignPublicationBaselines',rows);
 rows.forEach((r,i)=>{
  const peers=delays.filter((_,j)=>j!==i).sort((a,b)=>a-b),middle=Math.floor(peers.length/2);
  const expectedMedian=peers.length%2?peers[middle]:(peers[middle-1]+peers[middle])/2;
  check(r.latePublicationBaseline.median===expectedMedian,`exact leave-one-out median for ${delays.length} rows, removal ${i}`);
 });
}
// The parity bug could hide a signal at the DECP excess boundary.
const boundary=run('prepareContracts',[...Array.from({length:9},(_,i)=>late('edge'+i,'E',i*100)),late('edge-out','E',641)]).find(r=>r.id==='edge-out');
check(boundary.latePublicationBaseline.median===400&&lateRule(boundary).status==='signal','241-day excess uses the true odd median');
const mixed=run('prepareContracts',[...batch,late('x','X',200,{buyer:'B'})]);
check(mixed.find(r=>r.id==='x').latePublicationBaseline===null,'different buyer identifier is a different buyer');
const excl=run('prepareContracts',[...batch,...Array.from({length:20},(_,i)=>late('e'+i,'B',5,{dataStatus:'unverified'}))]);
check(excl.find(r=>r.id==='b0').latePublicationBaseline.median===200,'unverified rows never feed a baseline');
check(lateRule(late('neg','B',-3)).status==='unknown'&&lateRule(late('ok','B',120)).status==='clear'&&lateRule(late('k','B',121)).weight===8,'negative unknown; 120 days clear; just above 120 scores 8 without baseline');
check(lateRule({...solo,dataFamily:'secop2'}).status==='not-applicable'||lateRule({...solo,dataFamily:'secop2'}).status==='unknown');
check(run('selectContracts',prepared,{indicator:'late-publication'}).length===run('selectContracts',prepared,{indicator:'late-publication'}).length);
// Filters never change baselines: they are fixed at preparation.
const before=byId('b0').latePublicationBaseline.median;run('selectContracts',prepared,{search:'zzz'});check(byId('b0').latePublicationBaseline.median===before);
// Tie-breaking: equal scores order by number of families with a signal, then strongest single signal, then id.
const tie=(id,more)=>({...base,id,dataFamily:'decp',date:'2024-01-01',cpv:'30000000-1',...more});
const oneFamily=tie('a-one',{directAward:true,amount:50000});                                   // competition 18
const twoFamilies=tie('z-two',{durationMonths:180,publicationDate:'2024-05-01',cohortId:'t'}); // execution 10 + transparency 8
check(score(oneFamily)===18&&score(twoFamilies)===18);
check(run('selectContracts',[oneFamily,twoFamilies],{sort:'score'}).map(r=>r.id).join()==='z-two,a-one','more families first at equal score');
check(run('selectContracts',[oneFamily,twoFamilies],{sort:'score-asc'}).map(r=>r.id).join()==='z-two,a-one','same tie order when ascending');
const weaker=tie('a-weak',{directAward:false,offers:1,durationMonths:300});                    // competition 12 + execution 14 = 26
const stronger=tie('z-strong',{directAward:true,amount:50000,publicationDate:'2024-05-01'});    // competition 18 + transparency 8 = 26
check(score(weaker)===26&&score(stronger)===26);
check(run('selectContracts',[weaker,stronger],{sort:'score'}).map(r=>r.id).join()==='z-strong,a-weak','same families: strongest single signal first');
const twin=tie('a-twin',{directAward:true,amount:50000,publicationDate:'2024-05-01'});
check(run('selectContracts',[stronger,twin],{sort:'score'}).map(r=>r.id).join()==='a-twin,z-strong','then id');
const unknownRow=tie('0-unknown',{});
for(const sort of ['score','score-asc'])check(run('selectContracts',[unknownRow,oneFamily,twoFamilies],{sort}).at(-1).id==='0-unknown','unknown scores stay last');
const datasets=['contracts','decp-history','decp-cities','consultations','tours-notices'];
// v3.2: buyer-relative late publication and French direct-award threshold eligibility reduce flags (v3.1: 9/2466/535, 355/1747/492, 172/835/263).
// v3.1 adds the transparency family (late publication): counts differ from v3.0 (68/2665/277, 355/1835/404, 172/974/124).
const expected={contracts:[12,2566,432],'decp-history':[355,1966,273],'decp-cities':[172,987,111],consultations:[10,0,0],'tours-notices':[60,6,0]};
for(const file of datasets){
 const rows=run('prepareContracts',JSON.parse(fs.readFileSync(`data/${file}.json`)));
 const values=rows.map(score), exp=expected[file];
 check(values.filter(s=>s===null).length===exp[0]);check(values.filter(s=>s===0).length===exp[1]);check(values.filter(s=>s>0).length===exp[2]);
 for(const r of rows){
  const a=assessment(r),s=score(r);
  const expectedChecks=file==='tours-notices'?10:9;
  check(a.checks.length===expectedChecks&&a.applicable+a.unknownApplicability+a.notApplicable===expectedChecks);
  check(a.evaluated<=a.applicable);
  check(s===null ? a.evaluated===0 : a.evaluated>0&&s>=0&&s<=100);
  check(score({...r,officialFinding:!r.officialFinding})===s,'finding never changes score');
  if(!r.history&&r.directAward!==true)check(score({...r,amount:1e12})===s,'amount never changes standalone heuristics (French direct awards use it only for legal-threshold eligibility)');
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
