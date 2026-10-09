#!/usr/bin/env node
// Research only. Usage: node tools/analyze-ukraine-verdict-cohort.cjs [cohort.json[.gz]]
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), zlib = require('node:zlib');
const root = path.join(__dirname, '..');
const file = process.argv[2] || path.join(root, 'research/labels/ukraine-verdict-cohort.json.gz');
const bytes = fs.readFileSync(file);
const cohort = JSON.parse(file.endsWith('.gz') ? zlib.gunzipSync(bytes) : bytes.toString('utf8'));
const ctx = vm.createContext({ URL });
vm.runInContext(fs.readFileSync(path.join(root, 'script.js'), 'utf8'), ctx);
const call = (fn, ...args) => { ctx.args = args; return vm.runInContext(`${fn}(...args)`, ctx); };
const rows = call('prepareContracts', Array.isArray(cohort) ? cohort : cohort.rows);
const groups = ['corruption', 'fraud', 'combined', 'comparison'];
const table = new Map();
let flagged = 0;
const empty = () => ({ signal: 0, clear: 0, unknown: 0, 'not-applicable': 0 });
for (const row of rows) {
  // Assess every row, but never let unconfirmed/recent/pending verdicts enter the positive denominator.
  const checks = call('getAssessment', row).checks;
  const positive = ['corruption', 'fraud'].includes(row.label) && ['confirmed', 'presumed'].includes(row.finality);
  const strata = positive ? [row.label, 'combined'] : row.label === 'comparison' ? ['comparison'] : [];
  if (!strata.length) flagged++;
  for (const check of checks) {
    if (!table.has(check.id)) table.set(check.id, Object.fromEntries(groups.map(g => [g, empty()])));
    for (const group of strata) {
      const status = ['signal', 'clear', 'not-applicable'].includes(check.status) ? check.status : 'unknown';
      table.get(check.id)[group][status]++;
    }
  }
}
function wilson(hits, n) {
  if (!n) return null;
  const z = 1.959963984540054, p = hits / n, d = 1 + z * z / n;
  const center = (p + z * z / (2 * n)) / d;
  const half = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d;
  return [center - half, center + half];
}
const pct = x => (100 * x).toFixed(1) + '%';
function rate(counts) {
  const n = counts.signal + counts.clear, ci = wilson(counts.signal, n);
  return `${counts.signal}/${n} ${ci ? pct(counts.signal / n) + ' [' + ci.map(pct).join(', ') + ']' : 'NA'}; unknown=${counts.unknown}; not-applicable=${counts['not-applicable']}`;
}
function likelihood(positive, comparison) {
  const n1 = positive.signal + positive.clear, n0 = comparison.signal + comparison.clear;
  if (!n1 || !n0) return 'NA (no evaluable rows in one group)';
  // Haldane-Anscombe 0.5 added to all four cells. LR+ is a rate ratio, not an odds ratio.
  const a = positive.signal + 0.5, b = positive.clear + 0.5;
  const c = comparison.signal + 0.5, d = comparison.clear + 0.5;
  const lr = (a / (a + b)) / (c / (c + d));
  const se = Math.sqrt(1 / a - 1 / (a + b) + 1 / c - 1 / (c + d));
  return `${lr.toFixed(3)} [${Math.exp(Math.log(lr) - 1.96 * se).toFixed(3)}, ${Math.exp(Math.log(lr) + 1.96 * se).toFixed(3)}]`;
}
console.log(`${rows.length} rows assessed; ${flagged} flagged rows excluded from positive rates.`);
console.log('Hit rates: Wilson 95% intervals; LR+: 0.5-smoothed log rate-ratio 95% intervals. Unknown/not-applicable excluded from denominators.');
console.log('One tender row per observation; intervals assume independent rows and do not adjust for matched buyers/groups. Comparisons are unlabelled, not verified negatives.');
for (const [id, counts] of [...table.entries()].sort(([a], [b]) => a.localeCompare(b))) {
  console.log('\n' + id);
  for (const group of groups) console.log(`  ${group}: ${rate(counts[group])}`);
  for (const group of groups.slice(0, 3)) console.log(`  LR+ ${group}/comparison: ${likelihood(counts[group], counts.comparison)}`);
}
