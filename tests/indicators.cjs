// One indicator catalogue for every country: every check maps to a universal kind,
// and the kind filter works across jurisdictions.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const ctx = vm.createContext({URL});
vm.runInContext(fs.readFileSync('script.js','utf8'), ctx);
const run = (fn,...args) => {ctx.args=args;return vm.runInContext(`${fn}(...args)`,ctx);};
const kinds = vm.runInContext('INDICATOR_KINDS', ctx);
const files = ['decp-history','decp-cities','contracts','colombia-secop2','paraguay-dncp','paraguay-dncp-3buyers','prozorro','ted-portugal','ted-romania','ted-czechia','uk-fts','chile-mp'];
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
for (const kind of Object.keys(kinds)) assert.ok(seen.has(kind), `kind ${kind} never used`);
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
console.log(`Indicator catalogue: ${seen.size} universal kinds cover every check of ${files.length} datasets; the kind filter crosses jurisdictions; amounts sort within their currency.`);
