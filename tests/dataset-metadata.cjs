'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const api = require('../dataset-metadata.js');
const map = require('../data/dataset-metadata.json');
const script = fs.readFileSync(require.resolve('../script.js'), 'utf8');
// A dataset may load several files (the merged France DECP dataset): path is a string or a list.
const registry = [...script.matchAll(/^\s+(\w+): \{ path: (?:'[^']+'|\[[^\]]+\]), coverage: '([^']+)'/gm)];
assert.equal(registry.length, 13);
assert.deepEqual(Object.keys(map).sort(), registry.map(m => m[1]).sort());
for (const [, key, path] of registry) {
  assert.equal(map[key].coveragePath, path);
  assert.equal(map[key].source_updated, null);
  assert.ok(api.validate(map[key]).coverage);
  assert.deepEqual(api.validate(map[key]).snapshot, map[key].snapshot);
  assert.equal(api.formatEntries(key, map).fields[2].value, 'Unknown');
}
for (const key of ['missing', 'local']) {
  assert.ok(api.formatEntries(key, map).fields.every(f => f.value === 'Unknown'));
}
assert.ok(api.formatEntries('all', map).notes[0].includes('No single'));
for (const date of ['2025-02-29', '2026-04-31', '2026-00-01', '2026-01-00', '2026-01-01T24:00:00Z', '2026-01-01T00:60:00Z', '2026-01-01T00:00:00', 'today']) {
  assert.equal(api.validDate(date), false, date);
  assert.equal(api.validate({ source_updated: date }).source_updated, null);
}
assert.ok(api.validDate('2024-02-29'));
assert.ok(api.validDate('2026-09-26T18:18:42.329232+00:00'));
assert.equal(api.validate({ snapshot: { start: '2026-01-02', end: '2026-01-01' } }).snapshot, null);
assert.equal(api.validate({ coverage: { start: '2026-01-02', end: '2026-01-01', endExclusive: true, basis: 'publication' } }).coverage, null);
assert.deepEqual(api.validate({ snapshot: map.uk.snapshot }).snapshot, map.uk.snapshot);
assert.match(api.formatEntries('uk', map).fields[0].value, /UTC/);
assert.match(api.formatEntries('uk', map).fields[1].value, /2026-09-01.*end exclusive.*award release date/);
assert.match(api.formatEntries('chile', map).fields[1].value, /listing months/);
for (const key of ['decp', 'boamp']) {
  assert.equal(map[key].snapshot, null);
  assert.equal(api.formatEntries(key, map).fields[0].value, 'Unknown');
  assert.ok(map[key].notes.some(n => n.includes('2026-09-13') && n.includes('2026-09-25') && n.includes('not collection')));
}
assert.ok(map.tours.notes.some(n => n.includes('BOAMP collected') && n.includes('last recorded download, not a completion')));
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(require.resolve('../dataset-metadata.js'), 'utf8'), context);
assert.equal(typeof context.DatasetMetadata.formatEntries, 'function');
console.log('Dataset metadata tests passed');
