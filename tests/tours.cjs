const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx=vm.createContext({URL});vm.runInContext(fs.readFileSync('script.js','utf8'),ctx);
const run=(fn,...args)=>{ctx.args=args;return vm.runInContext(`${fn}(...args)`,ctx);};
let checks=0;const check=v=>{assert.ok(v);checks++;};
const rows=run('prepareContracts',JSON.parse(fs.readFileSync('data/tours-notices.json')));
const cov=JSON.parse(fs.readFileSync('data/tours-notices-coverage.json'));
const raw=JSON.parse(fs.readFileSync('data/tours-notices/raw/api-records.json'));
check(rows.length===66);check(cov.counts.buyerQualifiedNotices===25);check(cov.counts.correctionNotices===2);
check(new Set(rows.map(r=>r.id)).size===66);
for(const c of rows){
 const e=c.noticeEvidence;
 check(e.buyers.some(b=>b.siret==='21370261600011'));
 check(e.noticeId===c.noticeId&&e.lotId===c.lotId);
 check(c.amount===null&&c.offers===null&&c.directAward===null&&c.date===null);
 check(run('getBiddingPeriod',c).status==='unavailable');check(run('getVigilanceScore',c)===null);
 check(raw.some(r=>r.idweb===c.noticeId));
 for(const t of e.ted){check(fs.existsSync(t.localFile));check(t.noticeUuid===e.noticeUuid&&t.versionMatches);}
 for(const a of e.awardCriteria){check(a.lotId===c.lotId);check(a.source===c.source);check(a.path.includes('cac:AwardingTerms'));check(!a.path.includes('SelectionCriteria'));}
}
for(const [filter,count] of [['criteria',25],['explanation',13],['correction',6],['ted',66]])check(run('selectContracts',rows,{noticeContext:filter}).length===count);
check(run('selectContracts',rows,{search:'R2122-8'}).length===3);
check(run('selectContracts',rows,{search:'R2122-8',legal:'direct'}).length===0);
check(run('selectContracts',rows,{minimum:1}).length===0);
check(run('selectContracts',rows,{flagged:true}).length===0);
for(const sort of ['publication','publication-asc','date','date-asc','sector','sector-desc'])check(run('selectContracts',rows,{sort}).length===66);
check(run('selectContracts',rows,{sort:'publication-asc'})[0].publicationDate==='2024-06-16');
check(run('selectContracts',rows,{sort:'publication'})[0].publicationDate==='2026-04-19');
for(const group of ['buyer','supplier','sector','project'])check(run('arrangeGroups',rows,group).rows.length===66);
const corrected=rows.find(r=>r.noticeId==='25-127301');
check(corrected.noticeEvidence.references[0].matchedNoticeIds[0]==='25-119055');
for(const mutate of [c=>c.noticeEvidence.awardCriteria[0].lotId='LOT-WRONG',c=>c.noticeEvidence.ted[0].noticeUuid='wrong',c=>c.noticeEvidence.documents[0].url='javascript:alert(1)',c=>c.noticeEvidence.ted[0].localFile='../../secret',c=>c.noticeEvidence.ted[0].version='999']){
 const c=JSON.parse(JSON.stringify(corrected));mutate(c);assert.throws(()=>run('validateContracts',[c]));checks++;
}
const hostile=JSON.parse(JSON.stringify(corrected));hostile.noticeEvidence.procedureDescription='<img src=x onerror=alert(1)>';check(run('validateContracts',[hostile]).length===1); // permitted text, rendered with textContent
console.log(`${checks} full-notice assertions passed.`);
