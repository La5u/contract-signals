#!/usr/bin/env node
// Per-row explorer indicator statuses for the Ukraine audit label cohort, computed with the site's own engine
// (script.js in a VM, like tools/label-indicator-table.cjs) with all cohort rows prepared as ONE cohort.
// Research only: reads a JSON array of engine-ready rows, writes {id: {indicator: status}}.
// Usage: node tools/ukraine-cohort-indicators.cjs <rows.json> <out.json>
const fs = require('node:fs'), vm = require('node:vm'), path = require('node:path');
const [inFile, outFile] = process.argv.slice(2);
if (!inFile || !outFile) { console.error('usage: ukraine-cohort-indicators.cjs rows.json out.json'); process.exit(2); }
const ctx = vm.createContext({ URL });
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'script.js'), 'utf8'), ctx);
ctx.args = [JSON.parse(fs.readFileSync(inFile))];
const rows = vm.runInContext('prepareContracts(...args)', ctx);
const out = {};
for (const row of rows) {
  ctx.args = [row];
  const a = vm.runInContext('getAssessment(...args)', ctx);
  out[row.id] = Object.fromEntries(a.checks.map(c => [c.id, c.status]));
}
fs.writeFileSync(outFile, JSON.stringify(out));
console.log(`${rows.length} rows assessed`);
