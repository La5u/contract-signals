const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const ctx = vm.createContext({URL});
vm.runInContext(fs.readFileSync('script.js','utf8'),ctx);
const run = (fn,...args) => {ctx.args=args;return vm.runInContext(`${fn}(...args)`,ctx);};

function tally(rows) {
  const checks = {}; let flagged = 0, zero = 0, notAssessed = 0;
  for (const row of rows) {
    const a = run('getAssessment', row);
    assert.equal(a.checks.length, 9);
    for (const c of a.checks) { checks[c.id] ??= {signal:0,clear:0,unknown:0,'not-applicable':0}; checks[c.id][c.status]++; }
    const s = run('getVigilanceScore', row);
    if (s == null) notAssessed++; else if (s > 0) flagged++; else zero++;
  }
  return { checks, flagged, zero, notAssessed };
}

function commonRowChecks(rows, cov, start, end) {
  const buyers = cov.cohort.buyers ? cov.cohort.buyers.map(b => b.buyerId) : [cov.cohort.buyerId];
  assert.equal(new Set(rows.map(r=>r.id)).size,rows.length);
  for (const row of rows) {
    assert.equal(row.dataFamily,'dncp'); assert.equal(row.currency,'PYG');
    assert.ok(buyers.includes(row.buyerId));
    assert.ok(row.callPublishedDate>=start&&row.callPublishedDate<end);
    assert.ok(row.ocid&&row.contractId&&row.awardId&&row.supplierIds.length===1);
    assert.equal(row.source,`https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/${row.ocid}`);
    // French and Colombian checks are never applied to DNCP rows.
    const ids = run('getAssessment',row).checks.map(c=>c.id);
    for (const foreign of ['single-bid','direct-award','secop2-plurality-award','amount-increase']) assert.ok(!ids.includes(foreign));
    // Every link offered for verification is published in the data, human-readable page first.
    const links = run('verificationLinks',row);
    assert.equal(links.at(-1).url,row.source);
    if (row.awardUrl) { assert.equal(links[0].url,row.awardUrl); assert.match(row.awardUrl,/^https:\/\/www\.contrataciones\.gov\.py\/licitaciones\//); }
    for (const l of links) assert.match(l.url,/^https:\/\/www\.contrataciones\.gov\.py\//);
  }
}

// ---- First pilot: Fernando de la Mora (unchanged raw snapshot) ----
{
  const raw = JSON.parse(fs.readFileSync('data/paraguay-dncp.json'));
  const cov = JSON.parse(fs.readFileSync('data/paraguay-dncp-coverage.json'));
  const rows = run('prepareContracts',raw);
  assert.equal(cov.cohort.buyerId,'DNCP-SICP-CODE-66');
  assert.equal(cov.cohort.window.startInclusive,'2024-09-01');
  assert.equal(cov.cohort.window.endExclusive,'2025-09-01');
  assert.equal(cov.counts.searchProcesses,88);
  assert.equal(cov.counts.publishedContractsInFullRecords,86);
  assert.equal(cov.counts.retainedContracts,84);
  assert.equal(cov.counts.excludedEntriesThatAreAmendmentRecords,2);
  assert.equal(cov.counts.retainedWithoutSignatureDate,84);
  assert.equal(cov.counts.retainedWithSignedDocumentUrl,80);
  assert.equal(cov.counts.retainedWithPortalAwardPage,84);
  assert.equal(rows.length,84);
  commonRowChecks(rows,cov,'2024-09-01','2025-09-01');
  for (const row of rows) assert.equal(row.signatureDate,null);
  const t = tally(rows);
  assert.deepEqual(JSON.parse(JSON.stringify(t.checks)), {
    'dncp-single-tenderer':          {signal:34,clear:46,unknown:3,'not-applicable':1},
    'dncp-exception-award':          {signal:1,clear:0,unknown:0,'not-applicable':83},
    'dncp-repeated-single-tenderer': {signal:21,clear:13,unknown:3,'not-applicable':47},
    'dncp-repeated-exception':       {signal:0,clear:1,unknown:0,'not-applicable':83},
    'dncp-concentration':            {signal:0,clear:77,unknown:7,'not-applicable':0},
    'dncp-amount-increase':          {signal:2,clear:82,unknown:0,'not-applicable':0},
    'short-bidding-period':          {signal:0,clear:0,unknown:0,'not-applicable':84},
    'long-contract':                 {signal:0,clear:0,unknown:0,'not-applicable':84},
    'late-publication':              {signal:0,clear:0,unknown:0,'not-applicable':84},
  });
  assert.deepEqual([t.flagged,t.zero,t.notAssessed],[36,48,0]);
  // The two published amount amendments are +20.0 % and +19.99 %: evaluated, not above the threshold.
  const amended = rows.filter(r=>r.amendments.some(a=>a.amount!=null));
  assert.equal(amended.length,2);
  for (const r of amended) assert.ok(Math.abs(run('dncpAmountIncrease',r).percentage-20)<0.05);
  // Multi-lot processes with several tenderers stay unknown, never clear.
  const multiLot = rows.find(r=>r.lotCount>1&&r.numberOfTenderers>1);
  assert.equal(run('getAssessment',multiLot).checks.find(c=>c.id==='dncp-single-tenderer').status,'unknown');
  // Repetition counts distinct processes, not contract rows.
  for (const r of rows.filter(r=>r.dncpRepeatedSingle)) {
    const same = rows.filter(o=>o.buyerId===r.buyerId&&o.supplierIds[0].id===r.supplierIds[0].id&&run('dncpSingleTenderer',o));
    assert.equal(r.dncpRepeatedSingle.count,new Set(same.map(o=>o.ocid)).size);
  }
  console.log(`Paraguay pilot: 84 rows, ${t.flagged} flagged, ${t.zero} zero, ${t.notAssessed} not assessed under Paraguayan checks only.`);
}

// ---- Three-buyer cohort: checks fixed before download ----
{
  const raw = JSON.parse(fs.readFileSync('data/paraguay-dncp-3buyers.json'));
  const cov = JSON.parse(fs.readFileSync('data/paraguay-dncp-3buyers-coverage.json'));
  const rows = run('prepareContracts',raw);
  assert.deepEqual(cov.cohort.buyers.map(b=>[b.buyerId,b.level]),
    [['DNCP-SICP-CODE-20','national'],['DNCP-SICP-CODE-81','departmental'],['DNCP-SICP-CODE-108','municipal']]);
  assert.equal(cov.cohort.window.startInclusive,'2024-09-01');
  assert.equal(cov.cohort.window.endExclusive,'2026-09-01');
  assert.deepEqual(cov.counts.searchProcessesByBuyer.map(q=>q.searchProcesses),[149,95,97]);
  assert.equal(cov.counts.searchProcesses,339);           // 2 processes found under two buyers, counted once
  assert.equal(cov.counts.processesWithoutSingleCohortBuyer,1);
  assert.equal(cov.counts.publishedContractsInFullRecords,326);
  assert.equal(cov.counts.retainedContracts,293);
  assert.equal(cov.counts.excludedBudgetOnlyEntries,21);
  assert.equal(cov.counts.excludedEntriesThatAreAmendmentRecords,12);
  assert.equal(cov.counts.excludedContractEntries,21+12);
  assert.equal(rows.length,293);
  commonRowChecks(rows,cov,'2024-09-01','2026-09-01');
  const byBuyer = {}; for (const r of rows) byBuyer[r.buyerId]=(byBuyer[r.buyerId]||0)+1;
  assert.deepEqual(byBuyer,{'DNCP-SICP-CODE-20':168,'DNCP-SICP-CODE-81':88,'DNCP-SICP-CODE-108':37});
  const t = tally(rows);
  assert.deepEqual(JSON.parse(JSON.stringify(t.checks)), {
    'dncp-single-tenderer':          {signal:51,clear:132,unknown:108,'not-applicable':2},
    'dncp-exception-award':          {signal:2,clear:0,unknown:0,'not-applicable':291},
    'dncp-repeated-single-tenderer': {signal:3,clear:48,unknown:108,'not-applicable':134},
    'dncp-repeated-exception':       {signal:0,clear:2,unknown:0,'not-applicable':291},
    'dncp-concentration':            {signal:0,clear:282,unknown:11,'not-applicable':0},
    'dncp-amount-increase':          {signal:8,clear:285,unknown:0,'not-applicable':0},
    'short-bidding-period':          {signal:0,clear:0,unknown:0,'not-applicable':293},
    'long-contract':                 {signal:0,clear:0,unknown:0,'not-applicable':293},
    'late-publication':              {signal:0,clear:0,unknown:0,'not-applicable':293},
  });
  assert.deepEqual([t.flagged,t.zero,t.notAssessed],[58,235,0]);
  // 12 published amount amendments, none strictly above +20 %.
  const pct = rows.filter(r=>r.amendments.length).map(r=>run('dncpAmountIncrease',r).percentage);
  assert.equal(pct.length,12); assert.ok(pct.every(p=>p<=20.0001));
  console.log(`Paraguay three buyers: 293 rows, ${t.flagged} flagged, ${t.zero} zero, ${t.notAssessed} not assessed.`);
}

// Ley 7021/22 Art. 67 ceiling (score 3.3): the amount-increase check is anchored to the 20 % legal ceiling.
{
  const all = [...run('prepareContracts',JSON.parse(fs.readFileSync('data/paraguay-dncp.json'))), ...run('prepareContracts',JSON.parse(fs.readFileSync('data/paraguay-dncp-3buyers.json')))];
  const check = r => run('getAssessment',r).checks.find(c=>c.id==='dncp-amount-increase');
  const atCeiling = all.filter(r=>check(r).status==='signal');
  assert.equal(atCeiling.length, 10); // pilot 2 + three buyers 8 (6 x 20.00 %, 2 x 19.99 %): at the ceiling, none beyond
  for (const r of atCeiling) assert.equal(check(r).weight,8);
  // Bands on a synthetic row: below the near band, at it, at the ceiling, within rounding, beyond it, far beyond.
  const base = {dataFamily:'dncp',dataStatus:'verified',amount:1000,callPublishedDate:'2025-03-01',procedure:'x',procurementMethod:'open'};
  const at = pctv => check({...base,amendments:[{amount:pctv*10,currency:'PYG'}]});
  assert.equal(at(18.9).status,'clear');
  assert.equal(at(19).status,'signal'); assert.equal(at(19).weight,8);
  assert.equal(at(20).weight,8); assert.equal(at(20.04).weight,8);
  assert.equal(at(20.1).status,'signal'); assert.equal(at(20.1).weight,16.0);
  assert.equal(at(60).weight,28); assert.equal(at(100).weight,40); assert.equal(at(250).weight,40);
  assert.ok(at(30).weight > at(20).weight);
  // No amendment: clear, not a signal; unreadable amount: unknown.
  assert.equal(check({...base,amendments:[]}).status,'clear');
  assert.equal(check({...base,amount:0,amendments:[]}).status,'unknown');
  // Transition: a process launched before Ley 7021/22 applied to everything (19 Feb 2024) is out of scope; a missing call date is unknown.
  assert.equal(check({...base,callPublishedDate:'2024-02-18',amendments:[{amount:500,currency:'PYG'}]}).status,'not-applicable');
  assert.equal(check({...base,callPublishedDate:'2024-02-19',amendments:[{amount:500,currency:'PYG'}]}).status,'signal');
  assert.equal(check({...base,callPublishedDate:null,amendments:[{amount:500,currency:'PYG'}]}).status,'unknown');
  // Float artefacts at the band edges (found in review): 0.57/3 and 400.8+0.1+0.1 of 2000.
  assert.equal(check({...base,amount:3,amendments:[{amount:0.57,currency:'PYG'}]}).weight,8);
  assert.equal(check({...base,amount:2000,amendments:[400.8,0.1,0.1].map(amount=>({amount,currency:'PYG'}))}).weight,8);
  // A missing or impossible call date leaves applicability unknown, never a signal.
  assert.equal(check({...base,callPublishedDate:null,amendments:[]}).applicability,'unknown');
  assert.equal(check({...base,callPublishedDate:'2024-99-99',amendments:[{amount:200,currency:'PYG'}]}).status,'unknown');
  assert.equal(run('dncpCeilingBand',20.05),'at'); assert.equal(run('dncpCeilingBand',20.06),'beyond'); assert.equal(run('dncpCeilingBand',18.99),'below');
  console.log('Paraguay 20 % ceiling: 10 contracts at the ceiling (8 points), bands and transition covered.');
}

// Multi-lot awards stay unknown for single tenderer, but always point at the per-lot evidence.
{
  const rows = run('prepareContracts',JSON.parse(fs.readFileSync('data/paraguay-dncp-3buyers.json')));
  const multi = rows.filter(r=>r.lotCount>1&&r.numberOfTenderers>1);
  assert.equal(multi.length,92);
  for (const r of multi) assert.ok(run('verificationLinks',r).some(l=>/Bid comparison table|Evaluation report/.test(l.label)), r.id);
  console.log('Paraguay multi-lot awards: 92 unknown, each linked to its bid comparison table or evaluation report.');
}

// DNCP complaints: procedural context outside the index, no personal names.
{
  const rows = [...run('prepareContracts',JSON.parse(fs.readFileSync('data/paraguay-dncp.json'))), ...run('prepareContracts',JSON.parse(fs.readFileSync('data/paraguay-dncp-3buyers.json')))];
  const withComplaint = rows.filter(r=>r.complaints.length);
  assert.equal(withComplaint.length, 19);
  assert.equal(run('selectContracts',rows,{legal:'py-complaint'}).length, 19);
  for (const r of withComplaint) {
    assert.equal(run('getVigilanceScore',{...r,complaints:[]}), run('getVigilanceScore',r));
    for (const k of r.complaints) { assert.ok(['protest','investigation','other'].includes(k.kind)); assert.ok(!('intervenients' in k)); }
  }
  assert.ok(!JSON.stringify(rows.map(r=>r.complaints)).includes('"name"'));
  console.log('DNCP complaints: 19 contracts with a recorded complaint, context only, no names.');
}

// Indicators sort: most signals first, unassessed rows always last in both directions.
{
  const rows = run('prepareContracts',JSON.parse(fs.readFileSync('data/paraguay-dncp-3buyers.json')));
  const desc = run('selectContracts',rows,{sort:'indicators'}), asc = run('selectContracts',rows,{sort:'indicators-asc'});
  const n = r => run('getIndicators',r).length;
  for (let i = 1; i < desc.length; i++) assert.ok(n(desc[i-1]) >= n(desc[i]));
  for (let i = 1; i < asc.length; i++) assert.ok(n(asc[i-1]) <= n(asc[i]));
  const mixed = [...rows.slice(0,3), {...rows[0], id:'unassessed', dataStatus:'unverified'}];
  assert.equal(run('selectContracts',run('prepareContracts',mixed),{sort:'indicators-asc'}).at(-1).id,'unassessed');
  console.log('Indicators sort: ordered by signal count, not-assessed rows last.');
}
