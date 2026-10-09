// One indicator catalogue for every country: every check maps to a universal kind,
// and the kind filter works across jurisdictions.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const ctx = vm.createContext({URL});
vm.runInContext(fs.readFileSync('script.js','utf8'), ctx);
const run = (fn,...args) => {ctx.args=args;return vm.runInContext(`${fn}(...args)`,ctx);};
const kinds = vm.runInContext('INDICATOR_KINDS', ctx);
assert.equal(Object.keys(kinds).length, 19);
const files = ['decp-history','tours-notices','decp-cities','contracts','colombia-secop2','paraguay-dncp','paraguay-dncp-3buyers','prozorro','ted-portugal','ted-romania','ted-czechia','uk-fts','chile-mp'];
const seen = new Set();
for (const f of files) {
  const rows = run('prepareContracts', JSON.parse(fs.readFileSync(`data/${f}.json`)));
  for (const r of rows) for (const c of run('getAssessment', r).checks) {
    const kind = run('indicatorKind', c.id);
    assert.ok(kind && kinds[kind], `${f}: check ${c.id} has no universal kind`);
    seen.add(kind);
  }
  for (const i of rows.flatMap(r => run('getIndicators', r))) assert.equal(i.kindLabel, kinds[i.kind]);
}
// Evidence-based checks appear only on records carrying indicatorEvidence, so their kinds are checked by id.
for (const id of ['cap','execution','legalGround','unitPrice','exclusivity']) { const kind = run('indicatorKind', id); assert.ok(kind && kinds[kind], `evidence check ${id} has no universal kind`); seen.add(kind); }
for (const kind of Object.keys(kinds)) assert.ok(seen.has(kind), `kind ${kind} never used`);
for (const kind of Object.keys(vm.runInContext('KIND_REFERENCES', ctx))) assert.ok(kinds[kind], `reference for unknown kind ${kind}`);
// The kind filter spans jurisdictions; an old check id in a saved link still works.
const co = run('prepareContracts', JSON.parse(fs.readFileSync('data/colombia-secop2.json')));
assert.equal(run('selectContracts', co, {indicator:'direct-award'}).length, 176);
assert.equal(run('selectContracts', co, {indicator:'secop2-plurality-award'}).length, 176);
const uk = run('prepareContracts', JSON.parse(fs.readFileSync('data/uk-fts.json')));
assert.equal(run('selectContracts', uk, {indicator:'direct-award'}).length, 23);
// Amounts are never compared across currencies: the amount sort groups by currency.
const mixed = [{id:'a',amount:5,currency:'GBP'},{id:'b',amount:900,currency:'CLP'},{id:'c',amount:7,currency:'GBP'},{id:'d',amount:3,currency:'CLP'}].map(x => ({...x, dataFamily:'fts', dataStatus:'verified', buyer:'x', description:'x'}));
const sorted = run('selectContracts', mixed, {sort:'amount'}).map(x => x.id);
assert.deepEqual(sorted, ['b','d','c','a']);
// Profiles: one buyer or supplier within its own dataset; amounts are never summed.
const decp = run('prepareContracts', JSON.parse(fs.readFileSync('data/decp-history.json')));
const ardeche = decp.find(c => /Ardèche/.test(c.buyer));
const bp = run('buildProfile', decp, 'buyer', run('profileKey', ardeche, 'buyer'));
assert.equal(bp.contracts, decp.filter(c => c.buyerSiret === ardeche.buyerSiret).length);
assert.ok(bp.flagged <= bp.assessed && bp.assessed <= bp.contracts);
assert.ok(!('total' in bp) && Object.values(bp.currencies).every(v => 'largest' in v && !('sum' in v)));
const person = co.find(c => c.supplierIds[0]?.id.startsWith('masked-'));
const sp = run('buildProfile', co, 'supplier', run('profileKey', person, 'supplier'));
assert.ok(sp.contracts >= 1 && sp.ids.has(person.id));
assert.equal(run('profileKey', {...person, datasetKey:'colombia'}, 'supplier').split('|')[0], 'colombia');
console.log(`Indicator catalogue: ${seen.size} universal kinds cover every check of ${files.length} datasets; the kind filter crosses jurisdictions; amounts sort within their currency.`);
