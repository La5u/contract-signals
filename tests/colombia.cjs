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
}
// Per-buyer volumes match the coverage file exactly
const per=cov.counts.perBuyer;
check(per['Nacional'].rows===2618&&per['Departamental'].rows===3696&&per['Municipal-local (Bogotá)'].rows===1246);
check(run('selectContracts',rows,{search:'GOBERNACION DE CALDAS'}).length===3696);
check(run('selectContracts',rows,{search:'ALCALDIA LOCAL DE USAQUEN'}).length===1246);
check(run('selectContracts',rows,{search:'MINISTERIO DE EDUCACION NACION'}).length===2618);
// Join verification: intra-row process–contract–supplier completeness
const jv=cov.joinVerification;
check(jv.rows===7560&&jv.rowsWithContractId===7560&&jv.rowsWithProcessId===7560&&jv.rowsWithSupplierIdentifier===7560&&jv.duplicateExtractIds===0);
// No French heuristic fires; every row stays "Not assessed" (null), never 0
for(const c of rows){check(run('getVigilanceScore',c)===null);check(run('getIndicators',c).length===0);}
check(run('selectContracts',rows,{assessment:'unevaluated'}).length===7560);
check(run('selectContracts',rows,{assessment:'zero'}).length===0);
check(run('selectContracts',rows,{flagged:true}).length===0);
// Sorting, grouping and the out-of-scope increase rule
for(const sort of ['date','date-asc','amount','amount-asc','buyer','supplier','score'])check(run('selectContracts',rows,{sort}).length===7560);
check(run('selectContracts',rows,{sort:'amount'})[0].amount>=run('selectContracts',rows,{sort:'amount'})[7559].amount);
check(run('selectContracts',rows,{sort:'amount-asc'})[0].amount!==null);
for(const group of ['buyer','supplier','sector','project'])check(run('arrangeGroups',rows,group).rows.length===7560);
const evo=run('getAmountEvolution',rows[0]);
check(evo.status==='unavailable');
check(!/DECP/i.test(evo.reason));
// No euro conversion anywhere in the extract
check(!fs.readFileSync('data/colombia-secop2.json','utf8').includes('"currency":"EUR"'));
console.log(`${checks} Colombia SECOP II pilot assertions passed: cohort integrity, join verification, per-buyer counts, no premature heuristics, sorting and grouping.`);
