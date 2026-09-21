const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ctx = vm.createContext({ URL, console });
vm.runInContext(fs.readFileSync('tools/legacy/scoring-v2.1.js','utf8'), ctx);
const run = (fn, ...args) => { ctx.args = args; return vm.runInContext(`${fn}(...args)`,ctx); };
let checks=0;
function check(value) { assert.ok(value); checks++; }
const base = {id:'test',buyer:'Test',description:'Test',dataStatus:'verified', amount:null,offers:null,directAward:null,durationMonths:null};
const notice = {id:'a',version:'01',kind:'initial',publicationDate:'2025-02-01',deadline:'2025-02-15T00:00:00Z',procedureType:'open',accelerated:false,source:'https://www.boamp.fr/',previousNoticeIds:[]};
const make = () => ({...base,consultation:{procedureId:'uuid',lotId:'LOT-0001',initialNoticeId:'a',searchComplete:true,exclusions:[],notices:[{...notice}]}});
check(run('getVigilanceScore',make())===12);
let c=make(); c.consultation.notices[0].deadline='2025-02-16T00:00:00Z'; check(run('getVigilanceScore',c)===0);
for (const change of [c=>c.consultation.searchComplete=false,c=>c.consultation.procedureId=null,c=>c.consultation.notices[0].accelerated=null,c=>c.consultation.notices[0].accelerated=true,c=>c.consultation.notices[0].deadline=null,c=>c.consultation.notices[0].deadline='2025-02-30T00:00:00Z',c=>c.consultation.notices[0].kind='award',c=>c.consultation.notices.push({...notice}),c=>c.consultation.notices[0].procedureType='MAPA']) { c=make();change(c);check(run('getBiddingPeriod',c).status==='unavailable');check(run('getVigilanceScore',c)===0); }
c=make(); c.consultation.notices.push({...notice,id:'b',version:'02',kind:'correction',publicationDate:'2025-02-10',deadline:'2025-03-01T00:00:00Z',previousNoticeIds:['a']});check(run('getBiddingPeriod',c).status==='available');check(run('getVigilanceScore',c)===0);
c.consultation.notices[1].previousNoticeIds=['wrong'];check(run('getBiddingPeriod',c).status==='unavailable');
c=make(); c.offers=1;c.amount=100000;check(run('getVigilanceScore',c)===12); // max, not 12+11
check(run('getVigilanceScore',{...base,amount:100000000})===0);
for(const [amount,score] of [[99999,0],[100000,30],[500000,35],[1000000,40],[10000000,50]])check(run('getVigilanceScore',{...base,amount,directAward:true})===score);
const evolution = (initial, revised) => ({...base,dataFamily:'decp',date:'2024-01-01',amount:initial,priceType:'Définitif ferme',initialConflicts:[],history:[{kind:'initial',date:'2024-01-01',amount:initial},{kind:'modification',date:'2025-01-01',amount:revised}]});
for(const [initial,revised,expected] of [[250000,300000,false],[100000,150000,false],[100000,150000.01,true],[300000,360000,false],[300000,360000.01,true]])check(run('getIndicators',evolution(initial,revised)).some(i=>i.id==='amount-increase')===expected);
c=evolution(100000,200000); c.initialConflicts=['amount'];check(run('getAmountEvolution',c).status==='unavailable');
c=evolution(100000,200000); c.history.push({kind:'modification',date:'2025-01-01',amount:300000});check(run('getAmountEvolution',c).status==='unavailable');
c=make(); c.consultation.notices.push({...notice,id:'b',version:'02',kind:'correction',publicationDate:'2025-02-10',deadline:'2025-02-14T00:00:00Z',previousNoticeIds:['a']});check(run('getBiddingPeriod',c).status==='unavailable');
const nullSort=[{...base,id:'unknown'},{...base,id:'known',amount:1,date:'2024-01-01',offers:1,supplier:'A'}];
for(const sort of ['amount','amount-asc','date','date-asc','offers','supplier'])check(run('selectContracts',nullSort,{sort})[1].id==='unknown');
const datasets = ['contracts','decp-history','consultations'].map(f=>run('prepareContracts',JSON.parse(fs.readFileSync(`data/${f}.json`))));
check(datasets[0].length===3010);check(datasets[1].length===2594);check(datasets[2].length===10);
check(run('selectContracts',datasets[0],{official:true}).length===8);
for(const [id,count] of [['amount-increase',13],['repeated-single-bid',9],['supplier-concentration',8]])check(run('selectContracts',datasets[1],{indicator:id}).length===count);
check(datasets[2].every(c=>run('getBiddingPeriod',c).status==='unavailable'));
check(run('selectContracts',datasets[2],{search:'25-22678'}).length===1);
check(run('selectContracts',datasets[2],{sector:'45'}).length>0);
for(const sort of ['amount','amount-asc','date','date-asc','offers','supplier','sector','sector-desc','score','score-asc','increase','buyer'])check(run('selectContracts',datasets[0],{sort}).length===3010);
for(const mode of ['sector','buyer','supplier','project']) {const arranged=run('arrangeGroups',datasets[1],mode);check(arranged.rows.length===2594);check(new Set(arranged.rows.map(c=>c.id)).size===2594);}
assert.throws(()=>run('validateContracts',[base,base]));checks++;
const raw=JSON.parse(fs.readFileSync('data/consultations-raw.json')).records;
for(const row of datasets[2])for(const n of [...row.consultation.notices,...row.consultation.matchedAwards]) {const source=raw.find(r=>r.idweb===n.id);check(!!source);check(n.source.includes(n.id));if(n.kind!=='initial')check(n.previousNoticeIds.some(id=>(source.annonce_lie||[]).includes(id)));}
for (const [text,article] of [['R-2122-1','R2122-1'],['R. 2122-3- 3°','R2122-3'],['R2122-30','R2122-30'],['r 2122 – 1','R2122-1']]) {
 const c={...base,description:text,source:'https://example.org/contract'};
 check(run('getLegalContext',c)[0].article===article);
 check(run('getVigilanceScore',c)===run('getVigilanceScore',base));
}
for(const c of [{...base,description:'45212200 2122-1 exclusivité'},{...base,notes:'R2122-1'},{...base,description:'R2122-1',dataFamily:'audit'}])check(run('getLegalContext',{...c,source:'https://example.org'}).length===0);
check(run('getLegalContext',{...base,description:'R2122-1'}).length===0);
check(run('selectContracts',datasets[1],{legal:'cited'}).length===5);
check(run('selectContracts',datasets[1],{legal:'R2122-1'}).length===1);
check(run('selectContracts',datasets[1],{legal:'R2122-3'}).length===4);
check(run('selectContracts',[{...base,directAward:true,amount:1}],{legal:'direct'}).length===1);
check(run('selectContracts',[{...base,directAward:null}],{legal:'direct'}).length===0);
console.log(`${checks} historical v2.1 assertions passed; frozen baseline reproducible (not the active v3 rules).`);
