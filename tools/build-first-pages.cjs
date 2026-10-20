#!/usr/bin/env node
// First page of each dataset in the default view (index, descending; 50 rows), prepared and
// scored exactly as the explorer does, so it can be shown while the full dataset downloads.
// Rows keep their cohort context (baselines, concentration, buyer share), so their checks and
// index equal the full-dataset ones; the explorer locks filters, export and the record panel
// until the full dataset replaces them.
//
//   node tools/build-first-pages.cjs          # rewrite data/web/first/
//   node tools/build-first-pages.cjs --check  # exit 1 if a page is missing or stale
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.resolve(__dirname, '..');
const PAGE_SIZE = 50;
// The controls' initial values (index.html); render() passes the same options.
const DEFAULT_VIEW = { search: '', minimum: 0, minScore: 0, flagged: false, official: false, adjudicated: false, investigation: false, indicator: '', legal: '', noticeContext: '', assessment: '', sector: '', project: '', verification: '', sort: 'score' };

const files = require('./datasets.cjs').browserFiles();
const explorer = vm.createContext({ URL, console });
require('./engine.cjs').load(explorer);

function firstPage(key) {
  const data = files[key].flatMap(file => JSON.parse(fs.readFileSync(path.join(ROOT, file), 'utf8')));
  const prepared = explorer.prepareContracts(data);
  const rows = explorer.selectContracts(prepared, DEFAULT_VIEW).slice(0, PAGE_SIZE);
  return JSON.stringify({ dataset: key, total: prepared.length, pageSize: PAGE_SIZE, rows }) + '\n';
}

const check = process.argv.includes('--check');
const stale = [];
for (const key of Object.keys(files)) {
  const target = path.join(ROOT, 'data', 'web', 'first', `${key}.json`);
  const text = firstPage(key);
  if (check) {
    if (!fs.existsSync(target) || fs.readFileSync(target, 'utf8') !== text) stale.push(key);
    continue;
  }
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, text);
  console.log(`${path.relative(ROOT, target)}: ${text.length.toLocaleString('en')} bytes`);
}
if (stale.length) {
  console.error(`Stale first pages (run node tools/build-first-pages.cjs): ${stale.join(', ')}`);
  process.exit(1);
}
