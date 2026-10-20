// Every user-visible scoring output, for checking that a code change alters nothing.
//   node tools/snapshot-outputs.cjs DIR          write one JSON file per bundled dataset into DIR
//   node tools/snapshot-outputs.cjs --check DIR  compare with DIR; list the first differing rows, exit 1
// Per row: the score breakdown, assessment, signals and export record, computed by the browser engine
// (indicator-evidence.js, then the engine files, in one context as index.html loads them). Keep DIR outside the
// repository (e.g. ~/.cache/contract-signals/snapshots/<commit>).
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), crypto = require('node:crypto');
const { datasetPaths } = require('./datasets.cjs');
const root = path.resolve(__dirname, '..');
const { load } = require('./engine.cjs');

function engine() {
  const context = vm.createContext({ URL });
  context.globalThis = context;
  vm.runInContext(fs.readFileSync(path.join(root, 'indicator-evidence.js'), 'utf8'), context, { filename: 'indicator-evidence.js' });
  load(context);
  return (fn, ...args) => { context.args = args; return vm.runInContext(`${fn}(...args)`, context); };
}

function snapshot(run, file) {
  const rows = run('prepareContracts', JSON.parse(fs.readFileSync(path.join(root, file), 'utf8')));
  return rows.map(c => ({
    id: c.id,
    breakdown: run('getScoreBreakdown', c),
    indicators: run('getIndicators', c),
    export: run('exportRecord', c),
  }));
}

const name = file => file.replace(/^data\//, '').replace(/\//g, '__');
const args = process.argv.slice(2), check = args[0] === '--check', dir = check ? args[1] : args[0];
if (!dir) { console.error('usage: snapshot-outputs.cjs [--check] DIR'); process.exit(2); }
const run = engine();
const files = datasetPaths();
let failed = false;
if (!check) fs.mkdirSync(dir, { recursive: true });
for (const file of files) {
  const text = JSON.stringify(snapshot(run, file), null, 1);
  const target = path.join(dir, name(file));
  const digest = crypto.createHash('sha256').update(text).digest('hex').slice(0, 12);
  if (!check) { fs.writeFileSync(target, text); console.log(`${file}: ${digest}`); continue; }
  if (!fs.existsSync(target)) { console.log(`${file}: missing from ${dir}`); failed = true; continue; }
  const before = fs.readFileSync(target, 'utf8');
  if (before === text) { console.log(`${file}: unchanged`); continue; }
  failed = true;
  const a = JSON.parse(before), b = JSON.parse(text);
  const changed = b.filter((row, i) => JSON.stringify(row) !== JSON.stringify(a[i])).map(row => row.id);
  console.log(`${file}: CHANGED (${a.length} -> ${b.length} rows, ${changed.length} differ: ${changed.slice(0, 5).join(', ')})`);
}
const seen = new Set(files.map(name));
if (check) for (const f of fs.readdirSync(dir)) if (!seen.has(f)) { console.log(`${f}: no longer produced`); failed = true; }
process.exit(failed ? 1 : 0);
