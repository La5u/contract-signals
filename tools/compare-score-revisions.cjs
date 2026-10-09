// Offline revision diagnostics only; no ground-truth validation or label fitting.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const hash = content => crypto.createHash('sha256').update(content).digest('hex');

function engine(file) {
  const code = fs.readFileSync(path.resolve(root, file), 'utf8');
  const context = vm.createContext({ URL });
  vm.runInContext(code, context, { filename: file });
  return { code, hash: hash(code), call(fn, ...args) {
    context.args = args;
    return vm.runInContext(`${fn}(...args)`, context);
  } };
}

// Read only primary paths from the UI dataset config, not coverage/raw paths.
function datasetPaths(code) {
  const start = code.indexOf('const datasets = {');
  const end = code.indexOf('\n  };', start);
  if (start < 0 || end < 0) throw new Error('Dataset config not found');
  // A dataset's path is one file or a list of files (the merged France DECP dataset): every file is compared.
  const paths = [...code.slice(start, end).matchAll(/\bpath:\s*(\[[^\]]*\]|['"]data\/[^'"]+\.json['"])/g)]
    .flatMap(match => [...match[1].matchAll(/['"](data\/[^'"]+\.json)['"]/g)].map(m => m[1]));
  if (!paths.length || new Set(paths).size !== paths.length) throw new Error('Invalid dataset paths');
  return paths;
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

function compareRevisions(before, after = engine('script.js')) {
  const report = {
    sourceCodeHashes: { before: before.hash, after: after.hash },
    method: 'Same bundled inputs, independent preparation. Positive-score ranks and top 20 use each engine selectContracts(rows, {sort: "score"}); zero/null excluded. Offline revision diagnostics, not ground-truth validation.',
    datasets: {},
  };
  for (const file of datasetPaths(after.code)) {
    report.datasets[file] = compareDataset(before, after, fs.readFileSync(path.join(root, file), 'utf8'));
  }
  return report;
}

module.exports = { engine, datasetPaths, snapshot, compareDataset, compareRevisions };
if (require.main === module) {
  const [beforeFile, outputFile, ...extra] = process.argv.slice(2);
  if (!beforeFile || extra.length) {
    console.error('Usage: node tools/compare-score-revisions.cjs BEFORE_SCRIPT [OUTPUT_JSON]');
    process.exitCode = 1;
  } else {
    const report = compareRevisions(engine(path.resolve(beforeFile)));
    const json = JSON.stringify(report, null, 2) + '\n';
    if (outputFile) fs.writeFileSync(path.resolve(outputFile), json);
    else process.stdout.write(json);
  }
}
