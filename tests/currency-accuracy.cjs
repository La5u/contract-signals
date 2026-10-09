const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const source = fs.readFileSync('script.js', 'utf8');
const ctx = vm.createContext({ URL, URLSearchParams });
vm.runInContext(source, ctx);
const run = (fn, ...args) => { ctx.args = args; return vm.runInContext(`${fn}(...args)`, ctx); };
const legacy = { id: 'legacy', buyer: 'Buyer', supplier: 'Supplier', amount: 200, date: '2025-06-01', cpv: '72000000', dataStatus: 'verified' };
const local = { ...legacy, assessmentMode: 'fr-v3', datasetKey: 'local' };
// Preserve the helper's deliberate legacy EUR default, but never infer EUR for imports.
assert.equal(run('recordCurrency', legacy), 'EUR');
for (const assessmentMode of ['fr-v3', 'browse']) {
  assert.equal(run('recordCurrency', { ...local, assessmentMode }), null);
  assert.equal(run('recordCurrency', { ...local, assessmentMode, currency: 'USD' }), 'USD');
}
const rows = [
  { ...local, id: 'unknown-high', amount: 9000 },
  { ...local, id: 'eur-low', currency: 'EUR', amount: 10 },
  { ...local, id: 'usd-high', currency: 'USD', amount: 800 },
  { ...local, id: 'unknown-low', amount: 5 },
  { ...local, id: 'eur-high', currency: 'EUR', amount: 100 },
  { ...local, id: 'usd-low', currency: 'USD', amount: 20 },
  { ...local, id: 'missing', currency: 'EUR', amount: null }
];
for (const sort of ['amount', 'amount-asc']) {
  const sorted = run('selectContracts', rows, { sort });
  assert.equal(sorted.at(-1).id, 'missing');
  const groups = [];
  for (const c of sorted.slice(0, -1)) {
    const currency = run('recordCurrency', c);
    if (groups.at(-1)?.currency !== currency) groups.push({ currency, amounts: [] });
    groups.at(-1).amounts.push(c.amount);
  }
  assert.equal(groups.length, 3, 'unknown must not be interleaved with EUR');
  assert.deepEqual(groups.map(g => g.currency).sort(), [null, 'EUR', 'USD'].sort());
  for (const g of groups) assert.deepEqual(g.amounts, [...g.amounts].sort((a, b) => sort === 'amount' ? b - a : a - b));
}
const profile = run('buildProfile', rows, 'buyer', run('profileKey', local, 'buyer'));
assert.deepEqual(JSON.parse(JSON.stringify(profile.currencies)), {
  '(currency unknown)': { contracts: 2, largest: 9000 }, EUR: { contracts: 2, largest: 100 }, USD: { contracts: 2, largest: 800 }
});
const legacyProfile = run('buildProfile', [legacy], 'buyer', run('profileKey', legacy, 'buyer'));
assert.equal(legacyProfile.currencies.EUR.largest, 200);
assert.equal(run('frenchDirectAwardEligibility', legacy).status, 'below');
assert.equal(run('frenchDirectAwardEligibility', { ...local, currency: 'EUR' }).status, 'below');
for (const currency of [undefined, null, '', 'USD', 'COP']) {
  const result = run('frenchDirectAwardEligibility', { ...local, currency });
  assert.equal(result.status, 'unknown');
  assert.match(result.reason, /currency.*unknown or not EUR/);
  assert.doesNotMatch(result.reason, /amount missing/);
}
for (const amount of [0, -1]) {
  const result = run('frenchDirectAwardEligibility', { ...local, currency: 'EUR', amount });
  assert.equal(result.status, 'unknown');
  assert.match(result.reason, /nonpositive/);
  assert.doesNotMatch(result.reason, /missing/);
}
assert.match(run('frenchDirectAwardEligibility', { ...local, amount: null }).reason, /amount missing/);

// Execute the production formatter and DECP detail-rendering block with tiny text-only
// DOM stubs. Browser tests remain unchanged; this exercises the actual call sites.
const formatter = source.slice(source.indexOf('  const uiLocale ='), source.indexOf('  const dateFormat ='));
const detailStart = source.indexOf("    } else if (c.dataFamily === 'decp') {", source.indexOf('function startExplorer'));
const detail = source.slice(detailStart + "    } else if (c.dataFamily === 'decp') {".length, source.indexOf('\n    }\n    if (c.noticeChange', detailStart));
vm.runInContext(formatter + `
  function node(tag, text) { return { tag, text, children: [], append(...children) { this.children.push(...children); } }; }
  element = node;
  const pairs = () => {}, line = () => {};
  function renderCurrencyDetail(input) {
    const c = input, record = node('section');
    ${detail}
    return record;
  }
`, ctx);
const texts = n => [n.text, ...n.children.flatMap(texts)].filter(x => x != null);
for (const c of [legacy, local, { ...local, currency: 'USD' }, { ...local, currency: 'EUR' }]) {
  const rendered = texts(run('renderCurrencyDetail', { ...c, dataFamily: 'decp', initialConflicts: ['amount'],
    initialAlternatives: [{ amount: 1234 }, { amount: null }],
    history: [{ kind: 'initial', amount: 1234 }, { kind: 'modification', amount: 0 }, { kind: 'modification', amount: null }] }));
  ctx.c = c;
  const expected = vm.runInContext('moneyFor(c).format(1234)', ctx);
  assert.ok(rendered.includes(`Variant 1: ${expected}`));
  assert.ok(rendered.includes(expected));
  assert.ok(rendered.includes('Variant 2: amount unknown'));
  assert.ok(rendered.includes('—'));
  assert.ok(rendered.includes(vm.runInContext('moneyFor(c).format(0)', ctx)));
  if (c === local) { assert.match(expected, /currency unknown/); assert.doesNotMatch(rendered.join(' '), /€/); }
  if (c.currency === 'USD') { assert.match(expected, /\$/); assert.doesNotMatch(rendered.join(' '), /€/); }
}
console.log('Currency accuracy: sorting, profiles, French eligibility and detail amounts preserve known/unknown currencies.');
