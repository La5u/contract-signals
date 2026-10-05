const assert = require('node:assert/strict');
const { engine, datasetPaths, compareDataset, compareRevisions } = require('../tools/compare-score-revisions.cjs');
const current = engine('script.js');
const report = compareRevisions(current, current);
assert.equal(datasetPaths(current.code).length, 14);
assert.deepEqual(Object.keys(report.datasets), datasetPaths(current.code));
assert.equal(report.sourceCodeHashes.before, report.sourceCodeHashes.after);
for (const [file, result] of Object.entries(report.datasets)) {
  assert.deepEqual(result.before, result.after, file);
  assert.equal(result.changedScoreRows, 0, file);
  assert.equal(result.changedIndicatorRows, 0, file);
  assert.equal(result.changedRankRows, 0, file);
  assert.deepEqual(result.changedRows, [], file);
  assert.deepEqual(result.top20.before, result.top20.after, file);
  for (const key of ['entered', 'left', 'reordered']) assert.deepEqual(result.top20[key], [], file);
  assert.equal(result.before.rows, result.before.positive + result.before.zero + result.before.null, file);
  assert.equal(result.top20.before.length, Math.min(20, result.before.positive), file);
  result.top20.before.forEach((row, index) => {
    assert.ok(row.score > 0, file);
    assert.equal(row.rank, index + 1, file);
  });
}
// Exercise changed-score/signal and top-20 displacement branches with independent
// deterministic stub engines, rather than validating only the identity case.
const fixture=JSON.stringify(Array.from({length:21},(_,i)=>({id:`row-${String(i+1).padStart(2,'0')}`,score:21-i})));
const stub=changed=>({call(fn,...args){
 if(fn==='prepareContracts')return args[0].map(row=>({...row,score:changed&&row.id==='row-21'?30:row.score}));
 if(fn==='getVigilanceScore')return args[0].score;
 if(fn==='getIndicators')return changed&&args[0].id==='row-21'?[{id:'added-signal'}]:[];
 if(fn==='selectContracts')return [...args[0]].sort((a,b)=>b.score-a.score||a.id.localeCompare(b.id));
 throw new Error(`Unexpected function ${fn}`);
}});
const changed=compareDataset(stub(false),stub(true),fixture);
assert.equal(changed.changedScoreRows,1);
assert.equal(changed.changedIndicatorRows,1);
assert.equal(changed.changedRankRows,21);
assert.equal(changed.top20.entered[0].id,'row-21');
assert.equal(changed.top20.left[0].id,'row-20');
assert.equal(changed.top20.reordered.length,19);
assert.deepEqual(changed.changedRows.find(row=>row.id==='row-21').indicatorsAdded,['added-signal']);
const reversed=compareDataset(stub(true),stub(false),fixture);
assert.deepEqual(reversed.changedRows.find(row=>row.id==='row-21').indicatorsRemoved,['added-signal']);
assert.equal(reversed.top20.entered[0].id,'row-20');
assert.equal(reversed.top20.left[0].id,'row-21');
console.log(`score revisions: unchanged across ${Object.keys(report.datasets).length} datasets; changed scores, signals and top-20 displacement verified`);
