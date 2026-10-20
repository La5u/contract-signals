// Offline revision diagnostics only; no ground-truth validation or label fitting.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const { datasetPaths } = require('./datasets.cjs');
const root = path.resolve(__dirname, '..');
const hash = content => crypto.createHash('sha256').update(content).digest('hex');

// A checkout directory (its engine files, tools/engine.cjs) or one engine file, such as a revision's
// script.js from before the split (git show REV:script.js).
function engine(file) {
  const full = path.resolve(root, file);
  const code = fs.statSync(full).isDirectory() ? require('./engine.cjs').source(full) : fs.readFileSync(full, 'utf8');
  const context = vm.createContext({ URL });
  vm.runInContext(code, context, { filename: file });
  return { code, hash: hash(code), call(fn, ...args) {
    context.args = args;
    return vm.runInContext(`${fn}(...args)`, context);
  } };
}

function snapshot(runtime, data) {
  const rows = runtime.call('prepareContracts', data);
  const entries = new Map();
  const counts = { rows: rows.length, positive: 0, zero: 0, null: 0 };
  for (const row of rows) {
    if (entries.has(row.id)) throw new Error(`Duplicate prepared id: ${row.id}`);
    const score = runtime.call('getVigilanceScore', row);
    if (score !== null && (!Number.isFinite(score) || score < 0)) throw new Error(`Invalid score: ${row.id}`);
    counts[score === null ? 'null' : score > 0 ? 'positive' : 'zero']++;
    const indicators = Array.from(runtime.call('getIndicators', row), indicator => indicator.id).sort();
    entries.set(row.id, { score, indicators });
  }
  const ranked = Array.from(runtime.call('selectContracts', rows, { sort: 'score' }))
    .filter(row => entries.get(row.id).score > 0).map(row => row.id);
  return { entries, counts, ranked, ranks: new Map(ranked.map((id, index) => [id, index + 1])) };
}

function compareDataset(before, after, data) {
  // Independent inputs prevent either engine's preparation from affecting the other.
  const old = snapshot(before, JSON.parse(data));
  const next = snapshot(after, JSON.parse(data));
  const changedRows = [];
  let changedScoreRows = 0, changedIndicatorRows = 0, changedRankRows = 0;
  const ids = [...new Set([...old.entries.keys(), ...next.entries.keys()])].sort();
  for (const id of ids) {
    const b = old.entries.get(id), a = next.entries.get(id);
    const added = (a?.indicators || []).filter(value => !b?.indicators.includes(value));
    const removed = (b?.indicators || []).filter(value => !a?.indicators.includes(value));
    const oldRank = old.ranks.get(id) ?? null, newRank = next.ranks.get(id) ?? null;
    const scoreChanged = !b || !a || b.score !== a.score;
    const indicatorsChanged = added.length > 0 || removed.length > 0;
    if (scoreChanged) changedScoreRows++;
    if (indicatorsChanged) changedIndicatorRows++;
    if (oldRank !== newRank) changedRankRows++;
    if (scoreChanged || indicatorsChanged || oldRank !== newRank) changedRows.push({
      id, beforePresent: Boolean(b), afterPresent: Boolean(a),
      beforeScore: b?.score ?? null, afterScore: a?.score ?? null,
      oldRank, newRank, indicatorsAdded: added, indicatorsRemoved: removed,
    });
  }
  const beforeTop = old.ranked.slice(0, 20), afterTop = next.ranked.slice(0, 20);
  const rankedRow = id => ({ id, beforeScore: old.entries.get(id)?.score ?? null,
    afterScore: next.entries.get(id)?.score ?? null, oldRank: old.ranks.get(id) ?? null, newRank: next.ranks.get(id) ?? null });
  return { inputSha256: hash(data), before: old.counts, after: next.counts,
    changedScoreRows, changedIndicatorRows, changedRankRows, changedRows,
    top20: {
      before: beforeTop.map(id => ({ id, score: old.entries.get(id).score, rank: old.ranks.get(id) })),
      after: afterTop.map(id => ({ id, score: next.entries.get(id).score, rank: next.ranks.get(id) })),
      entered: afterTop.filter(id => !beforeTop.includes(id)).map(rankedRow),
      left: beforeTop.filter(id => !afterTop.includes(id)).map(rankedRow),
      reordered: afterTop.filter(id => beforeTop.includes(id) && old.ranks.get(id) !== next.ranks.get(id)).map(rankedRow),
    } };
}

function compareRevisions(before, after = engine(root)) {
  const report = {
    sourceCodeHashes: { before: before.hash, after: after.hash },
    method: 'Same bundled inputs, independent preparation. Positive-score ranks and top 20 use each engine selectContracts(rows, {sort: "score"}); zero/null excluded. Offline revision diagnostics, not ground-truth validation.',
    datasets: {},
  };
  for (const file of datasetPaths()) {
    report.datasets[file] = compareDataset(before, after, fs.readFileSync(path.join(root, file), 'utf8'));
  }
  return report;
}

module.exports = { engine, datasetPaths, snapshot, compareDataset, compareRevisions };
if (require.main === module) {
  const [beforeFile, outputFile, ...extra] = process.argv.slice(2);
  if (!beforeFile || extra.length) {
    console.error('Usage: node tools/compare-score-revisions.cjs BEFORE_CHECKOUT_DIR_OR_SCRIPT [OUTPUT_JSON]');
    process.exitCode = 1;
  } else {
    const report = compareRevisions(engine(path.resolve(beforeFile)));
    const json = JSON.stringify(report, null, 2) + '\n';
    if (outputFile) fs.writeFileSync(path.resolve(outputFile), json);
    else process.stdout.write(json);
  }
}
