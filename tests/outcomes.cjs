const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const ctx=vm.createContext({URL}); require('../tools/engine.cjs').load(ctx);
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

// Supplier proceedings: company-level steps (an inspection, a decision) shown with exact wording, never on
// the contract's own investigation flag and never scored. Consortium members are matched one by one.
{
  const step={stage:'inspection',authority:'Competition Council',eventDate:'2024-05-14',publishedAt:'2024-05-15',verifiedAt:'2026-10-15',
    sourceUrl:'https://example.org/press',sourceLabel:'Council press release',wording:'The Council inspected this company in a suspected bid-rigging case.'};
  const file={suppliers:[{country:'ROU',identifierType:'CUI',id:'123',name:'Member B',identityBasis:'Same name and CUI.',proceedings:[step]}]};
  const index=run('validateSupplierProceedings',file);
  const row={id:'r',country:'ROU',supplierIds:[{id:'999',identifierType:'CUI'},{id:'123',identifierType:'CUI'}]};
  const found=run('getSupplierProceedings',row,index);
  assert.equal(found.length,1); assert.equal(found[0].supplier,'Member B');
  const note=run('supplierProceedingNote',found[0]);
  assert.match(note,/^The Council inspected this company/); assert.match(note,/not a finding of wrongdoing/); assert.match(note,/this contract is not known to be part of the case/);
  assert.equal(run('getSupplierProceedings',{...row,country:'PRT'},index).length,0,'identifiers are national: the country must match');
  assert.equal(run('hasReportedInvestigation',row),false);
  for(const change of [{stage:'suspected'},{sourceUrl:'javascript:alert(1)'},{wording:' '},{publishedAt:'2024-05-01'},{eventDate:'2024-5-14'}])
    assert.throws(()=>run('validateSupplierProceedings',{suppliers:[{...file.suppliers[0],proceedings:[{...step,...change}]}]}),/Supplier proceedings/);
  assert.throws(()=>run('validateSupplierProceedings',{suppliers:[file.suppliers[0],file.suppliers[0]]}),/duplicate/);
  assert.throws(()=>run('validateSupplierProceedings',{suppliers:[{...file.suppliers[0],identityBasis:''}]}),/Supplier proceedings/);
  // The published file: the four firms of the 2024 Cisco tender inspection (Ministry of Finance TED rows) and the two
  // firms fined in Decision 225/2024 (Cluj County and Cluj-Napoca rows, not part of that case).
  const published=run('validateSupplierProceedings',JSON.parse(fs.readFileSync('data/supplier-proceedings.json')));
  const ro=run('prepareContracts',JSON.parse(fs.readFileSync('data/ted-romania.json')));
  assert.deepEqual(ro.filter(c=>run('getSupplierProceedings',c,published).length).map(c=>c.id).sort(),
    ['ted-335119-2025-lot-0000','ted-365345-2025-lot-0000','ted-477464-2025-lot-0000','ted-49562-2025-lot-0000','ted-576922-2024-lot-0004','ted-613767-2024-lot-0022',
     'ted-639516-2025-lot-0000','ted-686957-2024-lot-0000','ted-735680-2024-lot-0000']);
  assert.ok(ro.every(c=>!run('hasReportedInvestigation',c)));
  console.log('Supplier proceedings: company-level, exact wording with caveats, consortium members matched, never on the contract flag.');
}

// Joint offers: several declared holders are recorded as a relationship between the firms, never a signal.
{
  // A joint offer is claimed only with evidence: TED tendering-party members or a declared DECP grouping.
  assert.equal(run('jointOfferNote',{dataFamily:'ted',supplierIds:[{id:'1'},{id:'2'}]}),'Joint offer by 2 firms · a relationship between them, not a signal');
  assert.equal(run('jointOfferNote',{dataFamily:'decp',operatorGrouping:['Conjoint'],supplierIds:[{id:'1'},{id:'2'}]}),'Joint offer by 2 firms (declared grouping: Conjoint) · a relationship between them, not a signal');
  assert.match(run('jointOfferNote',{dataFamily:'decp',operatorGrouping:['Pas de groupement'],supplierIds:[{id:'1'},{id:'2'}]}),/^2 firms hold this award, declared without a grouping/);
  assert.match(run('jointOfferNote',{dataFamily:'boamp',supplierIds:[{id:'1'},{id:'2'}]}),/^2 firms hold this award \(joint offer or several framework holders; the source does not say\)/);
  // Two establishments (SIRET) of one company (SIREN) are one firm.
  assert.equal(run('jointOfferNote',{dataFamily:'ted',supplierIds:[{id:'55204499201624',siren:'552044992'},{id:'55204499201947',siren:'552044992'}]}),null);
  assert.match(run('jointOfferNote',{dataFamily:'ted',supplierIds:[{id:'a',siren:'1'},{id:'b',siren:'1'},{id:'c',siren:'2'}]}),/^Joint offer by 2 firms/);
  assert.equal(run('jointOfferNote',{supplierIds:[{id:'1'}]}),null);
  assert.equal(run('jointOfferNote',{}),null);
  const ro=run('prepareContracts',JSON.parse(fs.readFileSync('data/ted-romania.json')));
  const joint=ro.filter(c=>c.supplierIds?.length>1);
  assert.ok(joint.length>0);
  for(const c of joint) assert.ok(!run('getIndicators',c).some(i=>i.id==='supplier-concentration'),`${c.id}: a joint offer is not a concentrated award`);
  console.log(`Joint offers: ${joint.length} Romanian TED rows noted as a relationship, never as concentration.`);
}
