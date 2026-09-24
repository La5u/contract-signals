const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const ctx=vm.createContext({URL}); vm.runInContext(fs.readFileSync('script.js','utf8'),ctx);
const run=(fn,...args)=>{ctx.args=args;return vm.runInContext(`${fn}(...args)`,ctx);};
const base={id:'example',buyer:'Buyer',description:'Contract',dataFamily:'dncp',dataStatus:'verified',contractId:'ABC-1',source:'https://example.org/record',amount:100};
const outcome={status:'final-adjudication',scope:'contract',contractId:'ABC-1',authority:'Competent court',decisionId:'Decision 1',decisionDate:'2025-02-01',judgmentUrl:'https://example.org/decision',finalityUrl:'https://example.org/finality',verifiedAsOf:'2025-04-01',sourcePassage:'Contract ABC-1 is expressly identified.',offence:'Bribery',linkageBasis:'Contract ID quoted by court'};
const labelled={...base,corruptionOutcome:outcome};
assert.equal(run('validateContracts',[labelled]).length,1);
assert.equal(run('hasAdjudicatedCorruption',labelled),true);
assert.equal(run('getVigilanceScore',labelled),run('getVigilanceScore',base));
assert.equal(run('selectContracts',[base,labelled].map((c,i)=>({...c,id:`row-${i}`})),{adjudicated:true}).length,1);
for(const change of [{contractId:'OTHER'}, {scope:'aggregate'}, {status:'pending'}, {finalityUrl:'javascript:alert(1)'},{verifiedAsOf:'2024-01-01'},{sourcePassage:''}]){
  assert.throws(()=>run('validateContracts',[{...labelled,corruptionOutcome:{...outcome,...change}}]),/final corruption outcome/);
}
assert.throws(()=>run('validateContracts',[{...labelled,findingScope:'aggregate'}]),/final corruption outcome/);
const report={status:'reported-at-date-current-unknown',scope:'contract',reportedAt:'2024-09-11',eventDate:'2024-09-10',publisher:'News',sourceUrl:'https://example.org/news',reportedFact:'Search reported',linkageBasis:'Exact contract named',currentStatus:'Unknown'};
const newsRow={...base,investigationReports:[report]};
assert.equal(run('validateContracts',[newsRow]).length,1);
assert.equal(run('getVigilanceScore',newsRow),run('getVigilanceScore',base));
for(const change of [{status:'ongoing'},{scope:'aggregate'},{sourceUrl:'javascript:alert(1)'},{linkageBasis:''},{eventDate:'2024-09-12'}])
 assert.throws(()=>run('validateContracts',[{...newsRow,investigationReports:[{...report,...change}]}]),/reported investigation/);
assert.throws(()=>run('validateContracts',[{...newsRow,findingScope:'aggregate'}]),/reported investigation/);
for(const file of ['contracts','decp-history','decp-cities','consultations','tours-notices','colombia-secop2','paraguay-dncp']){
 const rows=run('prepareContracts',JSON.parse(fs.readFileSync(`data/${file}.json`)));
 assert.equal(run('selectContracts',rows,{adjudicated:true}).length,0,`${file}: audit reports or signals must never turn into convictions`);
 const reported=run('selectContracts',rows,{investigation:true});
 assert.equal(reported.length,file==='contracts'?1:0,`${file}: news must identify this exact contract dossier`);
 if(file==='contracts'){
   assert.equal(reported[0].id,'crc-station-nuage');
   assert.equal(reported[0].investigationReports[0].status,'reported-at-date-current-unknown');
   assert.equal(run('getVigilanceScore',reported[0]),run('getVigilanceScore',{...reported[0],investigationReports:[]}));
 }
}
console.log('Outcome and dated news-lead validation: one historical investigation report, zero adjudicated labels, no points.');
