#!/usr/bin/env node
// Keep a bounded nationwide subset using the explorer's decoder and scoring engine.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function build(site, limit = 5000) {
  if (!Number.isSafeInteger(limit) || limit < 1) throw new Error('limit must be a positive integer');
  const read = file => JSON.parse(fs.readFileSync(path.join(site, file), 'utf8'));
  const meta = read('meta.json');
  const buyers = new Map(read('buyers.json').map(b => [b[0], b]));
  const ctx = vm.createContext({ URL });
  require('./engine.cjs').load(ctx);
  const decode = vm.runInContext('(meta, shard, buyer, rows) => prepareContracts(koreaRecords(meta, shard, buyer, rows))', ctx);
  const score = vm.runInContext('c => getVigilanceScore(c)', ctx);
  vm.runInContext('assessmentCache = new WeakMap()', ctx);
  const col = Object.fromEntries(meta.columns.map((k, i) => [k, i]));
  const collator = new Intl.Collator('en', { sensitivity: 'base', numeric: true });
  const compare = (a, b) => (b.score ?? -1) - (a.score ?? -1) || (b.amount ?? -1) - (a.amount ?? -1) || collator.compare(a.row[col.contractNo], b.row[col.contractNo]);
  const heap = [];
  function retain(entry) {
    if (heap.length < limit) {
      let i = heap.length;
      heap.push(entry);
      while (i > 0) {
        const parent = (i - 1) >> 1;
        if (compare(heap[parent], entry) >= 0) break;
        heap[i] = heap[parent]; i = parent;
      }
      heap[i] = entry;
    } else if (compare(entry, heap[0]) < 0) {
      let i = 0;
      while (i * 2 + 1 < heap.length) {
        let child = i * 2 + 1;
        if (child + 1 < heap.length && compare(heap[child + 1], heap[child]) > 0) child++;
        if (compare(entry, heap[child]) >= 0) break;
        heap[i] = heap[child]; i = child;
      }
      heap[i] = entry;
    }
  }
  let rows = 0;
  for (const file of fs.readdirSync(path.join(site, 's')).filter(f => /^\d+\.json$/.test(f)).sort()) {
    const shard = read(`s/${file}`);
    for (const [code, raw] of Object.entries(shard.buyers)) {
      const buyer = buyers.get(code);
      if (!buyer) throw new Error(`Unknown buyer ${code} in ${file}`);
      for (let start = 0; start < raw.length; start += 256) {
        const batch = raw.slice(start, start + 256);
        const records = decode(meta, shard, buyer, batch);
        records.forEach((c, i) => {
          rows++;
          const entry = { code, row: batch[i], score: score(c), amount: c.amount };
          if (heap.length === limit && compare(entry, heap[0]) >= 0) return;
          // Copy only retained rows and their referenced strings, never retain a shard.
          entry.row = [...entry.row];
          entry.demand = shard.demand[entry.row[col.demand]];
          entry.legal = shard.legal[entry.row[col.legalRef]];
          retain(entry);
        });
      }
    }
  }
  heap.sort(compare);
  const top = { v: meta.v, demand: [], legal: [], buyers: {}, count: heap.length, limit };
  const lists = { demand: new Map(), legal: new Map() };
  function index(key, value) {
    if (value == null) return null;
    if (!lists[key].has(value)) { lists[key].set(value, top[key].length); top[key].push(value); }
    return lists[key].get(value);
  }
  for (const entry of heap) {
    if (col.demand != null) entry.row[col.demand] = index('demand', entry.demand);
    if (col.legalRef != null) entry.row[col.legalRef] = index('legal', entry.legal);
    (top.buyers[entry.code] ??= []).push(entry.row);
  }
  const json = JSON.stringify(top);
  fs.writeFileSync(path.join(site, 'top.json'), json);
  console.log(`top.json: ${top.count.toLocaleString('en')} of ${rows.toLocaleString('en')} rows; score range ${heap.at(-1)?.score ?? 'unassessed'}–${heap[0]?.score ?? 'unassessed'}; ${Buffer.byteLength(json).toLocaleString('en')} bytes`);
  return top;
}

if (require.main === module) {
  const [site, flag, value, ...extra] = process.argv.slice(2);
  if (!site || (flag && flag !== '--limit') || (flag && value == null) || extra.length) {
    console.error('Usage: node tools/build-korea-top.cjs <site-dir> [--limit 5000]');
    process.exitCode = 1;
  } else {
    try { build(site, flag ? Number(value) : 5000); }
    catch (error) { console.error(error.message); process.exitCode = 1; }
  }
}
module.exports = { build };
