// South Korea (KONEPS): shard rows become records scored from their precomputed checks (tools/korea-site-checks.py);
// rows without checks stay browse-only. Individual businesses keep their published name, flagged, and are left out
// of exports by name.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const ctx = vm.createContext({ URL });
require('../tools/engine.cjs').load(ctx);
const run = (fn, ...args) => { ctx.args = args; return vm.runInContext(`${fn}(...args)`, ctx); };
const columns = ['contractNo', 'date', 'dateIsFirstChange', 'name', 'demand', 'supplier', 'supplierBizrno', 'supplierKind',
  'originalAmount', 'latestAmount', 'versions', 'method', 'businessType', 'noticeNo', 'legalRef', 'joint', 'linkContract', 'linkChangeOrder', 'linkKind', 'checks'];
const meta = { columns, methods: ['수의계약'], businessTypes: ['용역'], supplierKinds: ['corporation', 'individual', 'public-body', 'association', 'foreign', 'unknown'],
  linkKinds: ['조070003'], link: 'https://www.g2b.go.kr/link/FIUA027_01/single/?ctrtNo={}&ctrtChgOrd={}&prcmBsneSeCd={}&srchName=ctrtCrst&openUrl=Y' };
const shard = { v: 1, demand: ['서울특별시 강남구', '서울특별시 강남구 보건소'], legal: ['지방계약법 제25조제1항5호다목'], buyers: { '3220000': [
  ['A1', '2025-01-02', 0, '용역 A', 0, '(주)회사', '215-87-29444', 0, 1000, 1200, 2, 0, 0, '20250100001', 0, 0, 'A1_1', '02', 0, 'csuuuccsucccccsscsuucucsc'],
  ['A2', '2024-10-01', 1, '용역 B', 1, '홍길동상회', null, 1, null, 500, 1, 0, 0, null, null, 1, 'A2_1', '01', 0, null]] } };
const rows = run('koreaRecords', meta, shard, ['3220000', '서울특별시 강남구', '지방자치단체', 2, 0]);
assert.equal(rows.length, 2);
const [corp, person] = rows;
assert.equal(corp.id, 'koneps-A1'); assert.equal(corp.dataFamily, 'koneps'); assert.equal(corp.currency, 'KRW'); assert.equal(corp.amount, 1200);
assert.deepEqual(JSON.parse(JSON.stringify(corp.supplierIds)), [{ id: '215-87-29444', identifierType: 'KR-BRN' }]);
assert.match(corp.amountBasis, /original contract was ₩1,000 \(2 versions\)/);
assert.equal(corp.notes, 'Legal ground cited: 지방계약법 제25조제1항5호다목.');   // demand = buyer: not repeated
assert.equal(corp.source, 'https://www.g2b.go.kr/link/FIUA027_01/single/?ctrtNo=A1_1&ctrtChgOrd=02&prcmBsneSeCd=%EC%A1%B0070003&srchName=ctrtCrst&openUrl=Y');
assert.deepEqual(JSON.parse(JSON.stringify(person.supplierIds)), []);
assert.deepEqual(JSON.parse(JSON.stringify(person.supplierIndividual)), [true]);
assert.match(person.dateNote, /first change in the data/);
assert.equal(person.notes, 'Requesting institution (수요기관): 서울특별시 강남구 보건소. Joint contract (공동계약).');
const prepared = run('prepareContracts', rows);
// G3, N4, K5, K6, K7 and B2 signal, G4 and B4 unknown, B5 clear, B12 clear (win near the stated floor); BC2-C11 are
// missing (a file built before 2026-11-02), so unknown. Bid rigging: concentration N4 9.1, price B12 -11 -> 0 (floored);
// corruption: N4 10.1. The record's index is the higher one.
const checks = run('computeAssessment', prepared[0]).checks;
const by = Object.fromEntries(checks.map(r => [r.id, r]));
const bd = run('getScoreBreakdown', prepared[0]);
assert.equal(bd.score, 10.1); assert.equal(bd.mainIndex, 'corruption');
assert.deepEqual([bd.indices.rigging.score, bd.indices.corruption.score], [0, 10.1]);
assert.deepEqual(JSON.parse(JSON.stringify(by['kr-supplier-dependence'].weights)), { rigging: 9.1, corruption: 10.1 });
assert.deepEqual(['kr-supplier-dependence', 'kr-buyer-share', 'kr-floor-gap'].map(id => by[id].weight), [10.1, 6.8, -11]);
assert.deepEqual(['kr-two-bids', 'kr-concentration', 'kr-bid-gap', 'kr-floor-gap', 'kr-award-near-reserve'].map(id => by[id].status), ['unknown', 'unknown', 'clear', 'clear', 'not-applicable']);
assert.ok(!by['kr-restricted-competition'], 'checks without points under either index are not shown');
assert.equal(by['kr-award-near-reserve'].weight, null);
assert.deepEqual(['kr-two-bids', 'kr-supplier-dependence', 'kr-floor-gap'].map(id => by[id].family), ['competition', 'concentration', 'price']);
assert.ok(checks.filter(r => r.id.startsWith('kr-')).every(r => r.basis === 'measured'));
for (const id of Object.keys(by).filter(id => id.startsWith('kr-'))) assert.ok(run('indicatorKind', id), id);
// FLOOR-GAP has its own kind, so its chip and filter do not read "near reserve price" (review 2026-10-29).
assert.equal(run('indicatorKind', 'kr-floor-gap'), 'floor-gap');
assert.notEqual(run('indicatorKind', 'kr-floor-gap'), run('indicatorKind', 'kr-award-near-reserve'));
assert.match(run('checkPoints', prepared[0], by['kr-supplier-dependence']).note, /cautious bound/);
// The business type stands in for the sector; the bid count fills Offers once the shards carry it.
assert.deepEqual(JSON.parse(JSON.stringify(run('getSector', prepared[0]))), { code: 'kr-services', label: 'Services (용역)' });
assert.equal(prepared[0].offers, null, 'shards built before the bids column: no offer count');
const withBids = run('koreaRecords', { ...meta, columns: [...columns, 'bids'] }, { ...shard, buyers: { '3220000': [[...shard.buyers['3220000'][0], 3]] } },
  ['3220000', '서울특별시 강남구', '지방자치단체', 1, 0])[0];
assert.equal(withBids.offers, 3);
const withLetters = (letters, i = 0) => run('prepareContracts', run('koreaRecords', meta, { ...shard, buyers: { '3220000': [[...shard.buyers['3220000'][0].slice(0, 19), letters]] } },
  ['3220000', '서울특별시 강남구', '지방자치단체', 1, 0]))[i];
const base = 'csuuuccsucccccsscsuucuc';
const rig = letters => run('getScoreBreakdown', withLetters(letters)).indices.rigging.score;
assert.equal(rig(base + 'ss' + 'suuu'), 27.6, 'two bids 11.8 + win well above the floor 6.7 + N4 9.1; K7 out of scope');
assert.equal(rig(base + 'su' + 'suuu'), 23.9, 'no stated floor: K7 3 scores the price');
assert.equal(rig(base + 'cu' + 'suuu'), 20.9, 'no floor, below 92.2 %: no price points');
assert.equal(run('getVigilanceScore', withLetters('c'.repeat(23) + 'cc')), 0, 'negative points alone: the index is floored at 0');
// B5 alone (7.3) offset by B12 (-11): index 0, yet a signal, labelled as offset rather than "no signal".
const offset = withLetters('c'.repeat(20) + 's' + 'cc' + 'cc');
assert.equal(run('getVigilanceScore', offset), 0);
assert.equal(run('getIndicators', offset).length, 1);
assert.equal(run('scoreLevel', 0, false, run('getScoreBreakdown', offset).assessment.signals).label, 'Signals offset by evidence against');
assert.equal(run('getVigilanceScore', withLetters(base)), null, 'a row from a build without the price slot is not assessed');
assert.equal(run('getVigilanceScore', prepared[1]), null, 'a row without computed checks is not assessed');
assert.match(run('computeAssessment', prepared[1]).excludedReason, /not computed for this record/);
assert.equal(run('exportRecord', prepared[1]).supplier, 'individual (name in the explorer)');
assert.equal(run('exportRecord', prepared[0]).supplier, '(주)회사');
console.log('Korea: shard rows to records, precomputed checks scored (rows without them browse-only), individual businesses flagged and left out of exports by name.');
