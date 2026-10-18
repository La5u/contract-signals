// Bounded DOM-adapter test: no network, browser, or procurement data imports.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('index.html', 'utf8');
const script = fs.readFileSync('script.js', 'utf8');
const ctx = vm.createContext({ URL, URLSearchParams });
vm.runInContext(script, ctx);
const catalogue = [...html.matchAll(/<option value="([^"]+)" data-country="([^"]+)">([^<]+)<\/option>/g)]
  .map(([, value, country, textContent]) => ({ value, dataset: { country }, textContent }));
assert.equal(catalogue.length, 16);
assert.equal(new Set(catalogue.map(option => option.value)).size, 16);
assert.match(html, /id="country"/);
assert.match(html, /Source \/ cohort/);

class Select {
  constructor(options = []) {
    this.options = options;
    this.value = options[0]?.value || '';
    this.listeners = {};
    this.ownerDocument = { createElement: () => ({}) };
  }
  get value() { return this.options.some(option => option.value === this.selected) ? this.selected : ''; }
  set value(value) { this.selected = this.options.some(option => option.value === value) ? value : ''; }
  append(option) { this.options.push(option); }
  replaceChildren(...options) { this.options = options; this.value = options[0]?.value || ''; }
  addEventListener(type, handler) { this.listeners[type] = handler; }
  change(value) { this.value = value; this.listeners.change(); }
}
function mount(initial = 'decp') {
  const country = new Select();
  const dataset = new Select(catalogue.map(option => ({ ...option })));
  dataset.value = initial;
  const loads = [];
  const selection = ctx.setupDatasetSelection(country, dataset, () => loads.push(dataset.value));
  return { country, dataset, loads, selection };
}
const { country, dataset, loads, selection } = mount();
assert.equal(country.options.length, 11, 'one entry per country plus the explicit published-collections scope');
assert.equal(country.value, 'France');
assert.deepEqual(dataset.options.map(option => option.value), ['decp', 'tours', 'consultations', 'boamp']);
dataset.change('tours');
country.change('Paraguay');
assert.equal(dataset.value, 'paraguay', 'first explicit cohort, not an aggregate');
dataset.change('paraguay3');
country.change('France');
assert.equal(dataset.value, 'tours', 'remember the chosen source within this visit');
country.change('Paraguay');
assert.equal(dataset.value, 'paraguay3');
assert.deepEqual(loads, ['tours', 'paraguay', 'paraguay3', 'tours', 'paraguay3'], 'one load per user change');

// Initial deep links and later cross-country hash changes can reach every original ID.
for (const option of catalogue) {
  const initial = mount(option.value);
  assert.equal(initial.dataset.value, option.value);
  assert.equal(initial.country.value, option.dataset.country);
  assert.equal(selection.selectDataset(option.value), true);
  assert.equal(dataset.value, option.value);
  assert.equal(country.value, option.dataset.country);
  assert.ok(dataset.options.every(item => item.dataset.country === country.value));
  const view = ctx.hashToViewState('#dataset=' + option.value + '&q=buyer&open=record-123');
  assert.equal(view.dataset, option.value);
  assert.equal(view.search, 'buyer');
  assert.equal(view['open-record'], 'record-123');
}
assert.equal(loads.length, 5, 'URL sync must not trigger a second load');
assert.equal(selection.selectDataset('nonexistent'), false);
assert.equal(dataset.value, catalogue.at(-1).value);
for (const alias of ['cities', 'all']) {
  selection.selectDataset(ctx.hashToViewState('#dataset=' + alias).dataset);
  assert.equal(dataset.value, 'decp');
  assert.equal(country.value, 'France');
}
assert.match(script, /datasetSelection\.selectDataset\(wanted\)/, 'hashchange uses the full catalogue');
assert.match(script, /const version = \+\+loadVersion/, 'stale loads remain guarded');
console.log('dataset selection: country navigation, cohort memory, all deep-link IDs and aliases OK');
