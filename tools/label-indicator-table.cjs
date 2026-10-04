#!/usr/bin/env node
// Descriptive association table: for each label target, the share of rows where each explorer indicator is
// a "signal", among positives and among all other rows (negatives plus unknowns, positive-unlabelled view).
// Read-only: loads script.js in a VM like the tests do. No model fitting, no causal or corruption claim.
// Usage: node tools/label-indicator-table.cjs <labels.json> <explorer-data.json> [output.json]
const fs = require('node:fs'), vm = require('node:vm');
const [labelsFile, dataFile, outFile] = process.argv.slice(2);
if (!labelsFile || !dataFile) { console.error('usage: label-indicator-table.cjs labels.json data.json [out.json]'); process.exit(2); }
const ctx = vm.createContext({URL});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname, '..', 'script.js'), 'utf8'), ctx);
const run = (fn, ...args) => { ctx.args = args; return vm.runInContext(`${fn}(...args)`, ctx); };
const labels = JSON.parse(fs.readFileSync(labelsFile));
const rows = run('prepareContracts', JSON.parse(fs.readFileSync(dataFile)));
const byId = new Map(rows.map(r => [r.id, r]));
const status = new Map();   // explorer row id -> {indicator: status}
for (const l of labels.rows) {
  const row = byId.get(l.id);
  if (!row) continue;
  status.set(l.id, Object.fromEntries(run('getAssessment', row).checks.map(c => [c.id, c.status])));
}
const targets = Object.keys(labels.summary.targets || labels.summary.tender_level_counts);
const out = { labels: labelsFile, data: dataFile, note: 'Descriptive only. Signals are editorial indicators, labels are partial and selected; positive-vs-rest rates are not validation.', targets: {} };
for (const t of targets) {
  const pos = labels.rows.filter(r => r.labels[t] === true && status.has(r.id));
  const rest = labels.rows.filter(r => r.labels[t] !== true && status.has(r.id));
  const neg = labels.rows.filter(r => r.labels[t] === false && status.has(r.id));
  const ids = Object.keys(status.values().next().value || {});
  const rate = (set, id) => {
    const assessed = set.filter(r => ['signal', 'clear'].includes(status.get(r.id)[id]));
    const sig = assessed.filter(r => status.get(r.id)[id] === 'signal').length;
    return { signal: sig, assessed: assessed.length, rate: assessed.length ? +(sig / assessed.length).toFixed(4) : null };
  };
  out.targets[t] = { positives: pos.length, negatives_reviewed: neg.length, rest: rest.length,
    indicators: pos.length ? Object.fromEntries(ids.map(id => [id, { positives: rate(pos, id), rest: rate(rest, id) }])) : {},
    ...(pos.length ? {} : { note: 'No positives: no comparison possible.' }) };
}
const text = JSON.stringify(out, null, 1) + '\n';
if (outFile) fs.writeFileSync(outFile, text); else process.stdout.write(text);
