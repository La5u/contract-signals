// One indicator catalogue for every country: every check maps to a universal kind,
// and the kind filter works across jurisdictions.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const ctx = vm.createContext({URL});
require('../tools/engine.cjs').load(ctx);
const run = (fn,...args) => {ctx.args=args;return vm.runInContext(`${fn}(...args)`,ctx);};
const kinds = vm.runInContext('INDICATOR_KINDS', ctx);
assert.equal(Object.keys(kinds).length, 28);
const files = ['decp-history','tours-notices','decp-cities','contracts','colombia-secop2','paraguay-dncp','paraguay-dncp-3buyers','prozorro','ted-portugal','ted-romania','ted-czechia','uk-fts','chile-mp'];
const seen = new Set(), measured = new Set();
for (const f of files) {
  const rows = run('prepareContracts', JSON.parse(fs.readFileSync(`data/${f}.json`)));
  for (const r of rows) for (const c of run('getAssessment', r).checks) {
    const kind = run('indicatorKind', c.id);
    assert.ok(kind && kinds[kind], `${f}: check ${c.id} has no universal kind`);
    seen.add(kind);
    // Score 4.0: every check says where its points come from: its country's labels, other countries' labels, or
    // nowhere (context, no weight). A check file's own editorial weight never exceeds 30 and never reaches the index.
    assert.ok(['measured', 'borrowed', 'context'].includes(c.basis), `${f}: check ${c.id} has no points basis`);
    if (c.status === 'signal' && c.basis !== 'measured') assert.ok(c.checkWeight <= 30, `${f}: editorial ${c.id} weighs ${c.checkWeight}`);
    if (c.status === 'signal' && c.basis === 'context') assert.equal(c.weight, 0, `${f}: context ${c.id} scores ${c.weight}`);
    if (c.status === 'signal' && c.basis === 'borrowed') assert.equal(c.weight, vm.runInContext('BORROWED_KIND_POINTS', ctx)[kind].points);
    if (c.basis === 'measured') measured.add(`${f}:${c.id}`);
  }
  for (const i of rows.flatMap(r => run('getIndicators', r))) assert.equal(i.kindLabel, kinds[i.kind]);
}
// Measured points: Ukraine, Colombia and Romania (TED) on their own labels, including the checks measured at 0; nothing else.
assert.deepEqual([...measured].sort(), ['colombia-secop2:secop2-buyer-share', 'colombia-secop2:secop2-concentration', 'colombia-secop2:secop2-plurality-award',
  'colombia-secop2:secop2-repeated-plurality', 'colombia-secop2:secop2-term-extension',
  'prozorro:ua-better-bid-disqualified', 'prozorro:ua-buyer-share', 'prozorro:ua-contract-amendments', 'prozorro:ua-direct-award',
  'prozorro:ua-direct-contract', 'prozorro:ua-single-offer', 'prozorro:ua-term-extension',
  'ted-romania:ro-buyer-share', 'ted-romania:ro-supplier-dependence', 'ted-romania:ted-concentration', 'ted-romania:ted-direct-award',
  'ted-romania:ted-repeated-direct', 'ted-romania:ted-repeated-single-offer', 'ted-romania:ted-single-offer']);
// Borrowed points are the lowest any labelled country measured: single offer and direct award are 0 (Romania).
assert.equal(vm.runInContext('BORROWED_KIND_POINTS', ctx)['single-offer'].points, 0);
assert.equal(vm.runInContext('BORROWED_KIND_POINTS', ctx)['term-extension'].points, 1.2);
assert.equal(vm.runInContext('formatMultiplier(10)', ctx), '×2.0');
assert.equal(vm.runInContext('formatMultiplier(0)', ctx), '×1.0');
assert.equal(vm.runInContext('formatMultiplier(null)', ctx), 'Not assessed');
assert.equal(vm.runInContext('EDITORIAL_MAX', ctx), 30);
// The export names each signal's points and their basis.
const ua = run('prepareContracts', JSON.parse(fs.readFileSync('data/prozorro.json'))).find(r => run('getIndicators', r).some(i => i.id === 'ua-buyer-share'));
assert.match(run('exportRecord', ua).signalPoints, /Large share of the buyer’s yearly procurement: 2.2 \(measured\)/);
// Evidence-based checks appear only on records carrying indicatorEvidence, so their kinds are checked by id.
// Korean checks are precomputed into the hosted shards (tests/korea.cjs), so theirs are checked by id too.
for (const id of ['cap','execution','legalGround','unitPrice','exclusivity','kr-award-near-reserve','kr-restricted-competition','kr-supplier-dependence','kr-two-bids','kr-one-valid-bid','kr-exact-floor','kr-bid-gap','kr-floor-gap']) { const kind = run('indicatorKind', id); assert.ok(kind && kinds[kind], `evidence check ${id} has no universal kind`); seen.add(kind); }
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
// Priority, (multiplier - 1) x amount, also groups by currency; a record without weight comes after any with weight.
const pr = [{id:'p',amount:100,currency:'UAH',w:10},{id:'q',amount:1000,currency:'UAH',w:2.2},{id:'r',amount:1e9,currency:'UAH',w:0},{id:'s',amount:50,currency:'UAH',w:30}];
const fake = new Map(pr.map(x => [x.id, x.w]));
ctx.fake = fake;
vm.runInContext('globalThis.realScore = getVigilanceScore; getVigilanceScore = c => fake.get(c.id)', ctx);
// q: 0.165 x 1000 = 165; p: 1 x 100 = 100; s: 7 x 50 = 350; r: 0.
assert.deepEqual(run('selectContracts', pr, {sort:'priority'}).map(x => x.id), ['s','q','p','r']);
vm.runInContext('getVigilanceScore = realScore', ctx);
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
