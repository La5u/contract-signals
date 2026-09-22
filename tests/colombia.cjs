const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx=vm.createContext({URL});vm.runInContext(fs.readFileSync('script.js','utf8'),ctx);
const run=(fn,...args)=>{ctx.args=args;return vm.runInContext(`${fn}(...args)`,ctx);};
let checks=0;const check=v=>{assert.ok(v,`colombia check failed: ${v}`);checks++;};
const rows=run('prepareContracts',JSON.parse(fs.readFileSync('data/colombia-secop2.json')));
const cov=JSON.parse(fs.readFileSync('data/colombia-secop2-coverage.json'));
check(rows.length===7560);
check(new Set(rows.map(r=>r.id)).size===7560);
// Cohort integrity: announced buyers, window, currency, language
check(cov.cohort.announcedBeforeDownload===true);
check(cov.cohort.window.startInclusive==='2024-09-01'&&cov.cohort.window.endExclusive==='2026-09-01');
for(const c of rows){
  check(c.dataFamily==='secop2'&&c.currency==='COP');
  check(c.date>='2024-09-01'&&c.date<'2026-09-01');
  check(typeof c.description==='string'&&c.description.trim().length>0);
  check(Array.isArray(c.supplierIds)&&c.supplierIds.length===1&&c.supplierIds[0].id);
  check(c.contractId&&c.processId&&c.processUrl);
  check(typeof c.procedure==='string'&&c.procedure.length>0);
  check(typeof c.procedureJustification==='string'&&c.procedureJustification.length>0);
  check(c.liquidation==='Si'||c.liquidation==='No');
}
check(cov.counts.liquidation.Si===1542&&cov.counts.liquidation.No===6018);
// Per-buyer volumes match the coverage file exactly
const per=cov.counts.perBuyer;
check(per['Nacional'].rows===2618&&per['Departamental'].rows===3696&&per['Municipal-local (Bogotá)'].rows===1246);
check(run('selectContracts',rows,{search:'GOBERNACION DE CALDAS'}).length===3696);
check(run('selectContracts',rows,{search:'ALCALDIA LOCAL DE USAQUEN'}).length===1246);
check(run('selectContracts',rows,{search:'MINISTERIO DE EDUCACION NACION'}).length===2618);
// Join verification: intra-row process–contract–supplier completeness
const jv=cov.joinVerification;
check(jv.rows===7560&&jv.rowsWithContractId===7560&&jv.rowsWithProcessId===7560&&jv.rowsWithSupplierIdentifier===7560&&jv.duplicateExtractIds===0);
// Duration parser: read-only on the published free text
check(run('secop2DurationMonths','6 Mes(es)')===6);
check(run('secop2DurationMonths','345 Dia(s)')===11.3);
check(run('secop2DurationMonths','12 Semana(s)')===2.8);
check(run('secop2DurationMonths','5 Año(s)')===60);
check(run('secop2DurationMonths','10 Año(s)')===120);
check(run('secop2DurationMonths','0 Mes(es)')===0);
check(run('secop2DurationMonths','7 Hora(s)')===null);
check(run('secop2DurationMonths',null)===null);
// Exactly the eight-check Colombian set; French-only checks always out of scope
const EXPECTED_IDS=['amount-increase','repeated-single-bid','secop2-concentration','secop2-long-duration','secop2-plurality-award','secop2-repeated-plurality','short-bidding-period','single-bid'].sort();
const NA_FRENCH=['single-bid','short-bidding-period','amount-increase','repeated-single-bid'];
let flagged=0,nulls=0,zeros=0,positives=0,partials=0;
const fires=Object.create(null);
const scores=new Map();
for(const c of rows){
  const a=run('getAssessment',c);
  check(a.checks.length===8);
  check(JSON.stringify(a.checks.map(r=>r.id).sort())===JSON.stringify(EXPECTED_IDS));
  for(const r of a.checks){
    if(NA_FRENCH.includes(r.id)) check(r.status==='not-applicable');
    if(r.status==='signal'){fires[r.id]=(fires[r.id]||0)+1;check(r.weight>0);}
    if(r.status!=='signal') check(r.weight==null);
  }
  const s=run('getVigilanceScore',c);
  scores.set(s,(scores.get(s)||0)+1);
  const ind=run('getIndicators',c);
  check(ind.every(i=>i.id.startsWith('secop2-')));
  check((s===0&&ind.length===0)||(s>0&&ind.length>0)||(s==null&&ind.length===0));
  if(s==null)nulls++;else if(s===0)zeros++;else positives++;
  if(ind.length)flagged++;
  if(a.unknown>0||a.unknownApplicability>0)partials++;
}
// Exact cohort results of the documented Colombian method (docs/score-colombia.md)
check(fires['secop2-plurality-award']===176);
check(fires['secop2-repeated-plurality']===15);
check(!('secop2-concentration' in fires));
check(fires['secop2-long-duration']===39);
check(positives===215&&zeros===7345&&nulls===0&&flagged===215&&partials===56);
check(scores.get(18)===170&&scores.get(36)===6&&scores.get(40)===4&&scores.get(17.1)===18);
check(run('selectContracts',rows,{assessment:'unevaluated'}).length===0);
check(run('selectContracts',rows,{assessment:'zero'}).length===7345);
check(run('selectContracts',rows,{assessment:'partial'}).length===56);
check(run('selectContracts',rows,{flagged:true}).length===215);
check(run('selectContracts',rows,{indicator:'secop2-plurality-award'}).length===176);
check(run('selectContracts',rows,{indicator:'secop2-repeated-plurality'}).length===15);
check(run('selectContracts',rows,{indicator:'secop2-concentration'}).length===0);
check(run('selectContracts',rows,{indicator:'secop2-long-duration'}).length===39);
// The bare direct-family modality is never a signal by itself
const directOnly=rows.filter(c=>c.procedure==='Contratación directa'&&c.procedureJustification==='Servicios profesionales y apoyo a la gestión');
check(directOnly.length>5000);
check(directOnly.every(c=>run('getIndicators',c).every(i=>i.id==='secop2-long-duration')));
// Amounts never influence the score: same row scored with amount kept as-is (no path reads amount for secop2)
const amountRow=rows.find(c=>c.amount>1e11);
check(amountRow&&run('getVigilanceScore',amountRow)===run('getVigilanceScore',{...amountRow,amount:1}));
// Sorting, grouping and the out-of-scope increase rule
for(const sort of ['date','date-asc','amount','amount-asc','buyer','supplier','score'])check(run('selectContracts',rows,{sort}).length===7560);
check(run('selectContracts',rows,{sort:'amount'})[0].amount>=run('selectContracts',rows,{sort:'amount'})[7559].amount);
check(run('selectContracts',rows,{sort:'amount-asc'})[0].amount!==null);
check(run('selectContracts',rows,{sort:'score'})[0].amount!==null);
for(const group of ['buyer','supplier','sector','project'])check(run('arrangeGroups',rows,group).rows.length===7560);
const evo=run('getAmountEvolution',rows[0]);
check(evo.status==='unavailable');
check(!/DECP/i.test(evo.reason));
// No euro conversion anywhere in the extract
check(!fs.readFileSync('data/colombia-secop2.json','utf8').includes('"currency":"EUR"'));
console.log(`${checks} Colombia SECOP II assertions passed: cohort integrity, join verification, per-buyer counts, liquidation, jurisdiction-specific indicators (176/15/0/39 fires, 215 flagged, 7,345 zero, 0 not assessed), parser units, filters, sorting and grouping.`);
