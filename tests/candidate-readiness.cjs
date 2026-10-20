'use strict';
// Actual retained extracts, no network, browser or national rebuild.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const importer = require('../import.js');
const ctx = vm.createContext({ URL, URLSearchParams });
require('../tools/engine.cjs').load(ctx);
const run = (expression, rows) => { ctx.input = rows; return vm.runInContext(expression, ctx); };
const ukraineText = fs.readFileSync('data/prozorro-expansion/contracts.json', 'utf8');
const ukraine = JSON.parse(ukraineText);
assert.equal(ukraine.length, 106);
const pilot = JSON.parse(fs.readFileSync('data/prozorro.json', 'utf8'));
for (const key of ['id', 'procedureId', 'contractInternalId', 'buyerId']) {
  const identities = new Set(pilot.map(row => row[key]).filter(Boolean));
  assert.ok(ukraine.every(row => !row[key] || !identities.has(row[key])));
}
// Demonstrate why registering the raw prozorro family is NOT a browse-only integration.
assert.equal(run('prepareContracts(input).filter(c => getVigilanceScore(c) != null).length', ukraine), 106);
function assertBrowse(text, count) {
  const parsed = importer.parse(text).records;
  assert.equal(parsed.length, count);
  const result = run(`(() => {
    const rows = prepareContracts(input);
    return { count: rows.length, scored: rows.filter(c => getVigilanceScore(c) != null).length,
      indicators: rows.reduce((n,c) => n + getIndicators(c).length, 0),
      exported: rows.map(exportRecord) };
  })()`, parsed);
  assert.equal(result.count, count);
  assert.equal(result.scored, 0);
  assert.equal(result.indicators, 0);
  assert.ok(result.exported.every(row => row.source && /^https:\/\//.test(row.source)));
  return result;
}
assertBrowse(ukraineText, 106);
if (process.argv.includes('--private-seap')) {
  const manifest = JSON.parse(fs.readFileSync('data/romania-seap-candidate-manifest.json', 'utf8'));
  const text = fs.readFileSync(path.join(os.homedir(), '.cache/contract-signals/romania-seap', manifest.candidate.relativePath), 'utf8');
  const raw = JSON.parse(text);
  assert.equal(raw.length, 149);
  assert.ok(raw.every(row => row.amount == null && row.currency == null && row.supplierIds.length === 0));
  assert.ok(raw.every(row => row.dataStatus === 'unverified' && row.descriptionGenerated === true));
  const browsed = assertBrowse(text, 149);
  assert.ok(browsed.exported.every(row => row.amount == null && row.currency == null));
  console.log('Private SEAP candidate: 149 records load browse-only, zero indicators/scores, no adopted values or winner IDs. Content/privacy clearance is NOT established.');
}
console.log('Ukraine candidate: no pilot identity overlap, 106 browse-only rows validated; raw family routing would score all 106 and must not be mistaken for browse-only.');
