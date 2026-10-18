'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { scan, loadChunks } = require('../static-scan.js');

async function main() {
  const context = vm.createContext({});
  vm.runInContext(fs.readFileSync(require.resolve('../static-scan.js'), 'utf8'), context);
  assert.equal(typeof context.StaticScan.scan, 'function');
  assert.equal(typeof context.StaticScan.loadChunks, 'function');

  const data = [[{ id: 9, country: 'KR' }, { id: 2, country: 'FR' }], [],
    [{ id: 7, country: 'KR' }, { id: 1, country: 'FR' }, { id: 5, country: 'KR' }]];
  const progress = [], visited = [], loaded = [];
  let active = 0, maxActive = 0, yields = 0;
  const source = () => loadChunks([0, 1, 2], async (key, { index }) => {
    assert.equal(key, index);
    active++;
    maxActive = Math.max(active, maxActive);
    await Promise.resolve();
    loaded.push(key);
    active--;
    return data[key];
  });
  const result = await scan(source(), {
    predicate: async (row, location) => { visited.push(location); return row.country === 'KR'; },
    offset: 1, pageSize: 1, expectedChunks: 3, expectedRows: 5,
    onProgress: p => progress.push(p), yieldEvery: 2,
    yieldControl: async () => { yields++; }
  });
  assert.deepEqual(result.rows.map(r => r.id), [7]);
  assert.deepEqual({ ...result, rows: [] }, {
    rows: [], offset: 1, pageSize: 1, scannedRows: 5, matchedRows: 3,
    scannedChunks: 3, complete: true, exact: true
  });
  assert.deepEqual(loaded, [0, 1, 2]);
  assert.equal(maxActive, 1);
  assert.equal(yields, 2);
  assert.deepEqual(visited.map(p => [p.rowIndex, p.chunkIndex, p.indexInChunk]),
    [[0, 0, 0], [1, 0, 1], [2, 2, 0], [3, 2, 1], [4, 2, 2]]);
  assert.ok(progress.slice(0, -1).every(p => !p.complete && !p.exact && !('rows' in p)));
  assert.equal(progress.at(-1).exact, true);
  assert.equal(progress.at(-1).matchedRows, 3);
  // Every page rescans all rows: no early stop after filling a page, no sorting.
  const all = [];
  for (let offset = 0; offset < 7; offset += 2) {
    const page = await scan(source(), { offset, pageSize: 2 });
    assert.equal(page.scannedRows, 5);
    assert.equal(page.matchedRows, 5);
    all.push(...page.rows.map(r => r.id));
  }
  assert.deepEqual(all, [9, 2, 7, 1, 5]);
  for (const options of [{ pageSize: 0 }, { offset: 99 }, { predicate: () => false }]) {
    const emptyPage = await scan(source(), options);
    assert.deepEqual(emptyPage.rows, []);
    assert.equal(emptyPage.scannedRows, 5);
    assert.equal(emptyPage.exact, true);
  }
  assert.equal((await scan([], { expectedChunks: 0, expectedRows: 0 })).exact, true);

  async function fails(chunks, options, pattern, scannedRows) {
    await assert.rejects(scan(chunks, options), error => {
      assert.equal(error.name, 'StaticScanError');
      assert.match(error.message, pattern);
      assert.equal(error.progress.complete, false);
      assert.equal(error.progress.exact, false);
      if (scannedRows !== undefined) assert.equal(error.progress.scannedRows, scannedRows);
      return true;
    });
  }
  await fails([[1], null, [2]], {}, /must be an array/, 1);
  await fails([[1]], { expectedChunks: 2 }, /Fewer chunks/, 1);
  await fails([[1], [2]], { expectedChunks: 1 }, /More chunks/, 1);
  await fails([[1]], { expectedRows: 2 }, /Fewer rows/, 1);
  await fails([[1, 2]], { expectedRows: 1 }, /More rows/, 1);
  await fails([[1]], { predicate: () => 1 }, /boolean/, 0);
  const original = Object.freeze(new Error('predicate failed'));
  await assert.rejects(scan([[1]], { predicate() { throw original; } }), e => e.cause === original && !e.progress.exact);
  await fails([[1]], { onProgress() { throw Error('progress failed'); } }, /progress failed/, 0);
  await fails([[1]], { yieldEvery: 1, yieldControl() { throw Error('scheduler failed'); } }, /scheduler failed/, 1);
  let laterLoaded = false;
  await fails(loadChunks([0, 1, 2], async key => {
    if (key === 1) throw Error('HTTP 404');
    if (key === 2) laterLoaded = true;
    return [key];
  }), {}, /HTTP 404/, 1);
  assert.equal(laterLoaded, false);
  await fails(loadChunks(['missing'], async () => undefined), {}, /must be an array/, 0);
  async function* truncated() { yield [1]; throw Error('truncated JSON'); }
  await fails(truncated(), {}, /truncated JSON/, 1);
  await fails({}, {}, /iterable/, 0);

  for (const options of [{ offset: -1 }, { pageSize: Infinity }, { offset: 0.5 },
    { pageSize: Number.MAX_SAFE_INTEGER, offset: 1 }, { expectedChunks: -1 },
    { expectedRows: NaN }, { predicate: null }, { yieldEvery: 0 }, { onProgress: 42 }]) {
    await assert.rejects(scan([], options), TypeError);
  }

  const before = new AbortController();
  before.abort('before');
  let touched = false;
  await assert.rejects(scan(loadChunks([1], () => { touched = true; return []; }),
    { signal: before.signal }), e => e.name === 'AbortError' && e.progress.scannedRows === 0);
  assert.equal(touched, false);

  const during = new AbortController();
  let cleaned = false;
  async function* cancellable() {
    try { yield [1, 2, 3]; throw Error('must not request next chunk'); }
    finally { cleaned = true; }
  }
  await assert.rejects(scan(cancellable(), {
    signal: during.signal, yieldEvery: 1,
    onProgress(p) { if (p.scannedRows === 1) during.abort(); }
  }), e => e.name === 'AbortError' && e.progress.scannedRows === 1 && !e.progress.exact);
  await Promise.resolve();
  assert.equal(cleaned, true);

  // An uncooperative loader/predicate/iterator cannot hold cancellation hostage.
  for (const mode of ['loader', 'predicate', 'iterator']) {
    const controller = new AbortController();
    let started;
    const ready = new Promise(resolve => { started = resolve; });
    const never = () => { started(); return new Promise(() => {}); };
    const chunks = mode === 'loader' ? loadChunks([0], never, { signal: controller.signal })
      : mode === 'iterator' ? { [Symbol.asyncIterator]() { return { next: never }; } } : [[1]];
    const pending = scan(chunks, { signal: controller.signal,
      ...(mode === 'predicate' ? { predicate: never } : {}) });
    await ready;
    controller.abort();
    let timer;
    try {
      await Promise.race([
        assert.rejects(pending, e => e.name === 'AbortError' && !e.progress.exact),
        new Promise((_, reject) => { timer = setTimeout(() => reject(Error('Cancellation hung')), 500); })
      ]);
    } finally { clearTimeout(timer); }
  }

  // Many chunks: retain only a bounded page, still inspect every row.
  let count = 0;
  async function* many() {
    for (let i = 0; i < 10000; i++) yield [{ id: i }];
  }
  const bounded = await scan(many(), { offset: 9000, pageSize: 3,
    predicate(row) { count++; return row.id % 2 === 0; } });
  assert.equal(count, 10000);
  assert.equal(bounded.matchedRows, 5000);
  assert.equal(bounded.rows.length, 0);
  const small = await scan(many(), { offset: 2, pageSize: 3 });
  assert.deepEqual(small.rows.map(r => r.id), [2, 3, 4]);
  assert.equal(small.scannedChunks, 10000);
  console.log('Static scan tests passed');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
