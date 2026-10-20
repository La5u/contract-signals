// South Korea (KONEPS): shard rows become browse-only records; individual businesses keep their
// published name, flagged, and are left out of exports by name.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const ctx = vm.createContext({ URL });
require('../tools/engine.cjs').load(ctx);
const run = (fn, ...args) => { ctx.args = args; return vm.runInContext(`${fn}(...args)`, ctx); };
const columns = ['contractNo', 'date', 'dateIsFirstChange', 'name', 'demand', 'supplier', 'supplierBizrno', 'supplierKind',
  'originalAmount', 'latestAmount', 'versions', 'method', 'businessType', 'noticeNo', 'legalRef', 'joint', 'linkContract', 'linkChangeOrder', 'linkKind'];
const meta = { columns, methods: ['수의계약'], businessTypes: ['용역'], supplierKinds: ['corporation', 'individual', 'public-body', 'association', 'foreign', 'unknown'],
  linkKinds: ['조070003'], link: 'https://www.g2b.go.kr/link/FIUA027_01/single/?ctrtNo={}&ctrtChgOrd={}&prcmBsneSeCd={}&srchName=ctrtCrst&openUrl=Y' };
const shard = { v: 1, demand: ['서울특별시 강남구', '서울특별시 강남구 보건소'], legal: ['지방계약법 제25조제1항5호다목'], buyers: { '3220000': [
  ['A1', '2025-01-02', 0, '용역 A', 0, '(주)회사', '215-87-29444', 0, 1000, 1200, 2, 0, 0, '20250100001', 0, 0, 'A1_1', '02', 0],
  ['A2', '2024-10-01', 1, '용역 B', 1, '홍길동상회', null, 1, null, 500, 1, 0, 0, null, null, 1, 'A2_1', '01', 0]] } };
const rows = run('koreaRecords', meta, shard, ['3220000', '서울특별시 강남구', '지방자치단체', 2, 0]);
assert.equal(rows.length, 2);
const [corp, person] = rows;
assert.equal(corp.id, 'koneps-A1'); assert.equal(corp.dataFamily, 'koneps'); assert.equal(corp.currency, 'KRW'); assert.equal(corp.amount, 1200);
assert.deepEqual(JSON.parse(JSON.stringify(corp.supplierIds)), [{ id: '215-87-29444', identifierType: 'KR-BRN' }]);
assert.match(corp.amountBasis, /original contract was 1000 KRW \(2 versions\)/);
assert.equal(corp.notes, 'Legal ground cited: 지방계약법 제25조제1항5호다목.');   // demand = buyer: not repeated
assert.equal(corp.source, 'https://www.g2b.go.kr/link/FIUA027_01/single/?ctrtNo=A1_1&ctrtChgOrd=02&prcmBsneSeCd=%EC%A1%B0070003&srchName=ctrtCrst&openUrl=Y');
assert.deepEqual(JSON.parse(JSON.stringify(person.supplierIds)), []);
assert.deepEqual(JSON.parse(JSON.stringify(person.supplierIndividual)), [true]);
assert.match(person.dateNote, /first change in the period/);
assert.equal(person.notes, 'Requesting institution (수요기관): 서울특별시 강남구 보건소. Joint contract (공동계약).');
const prepared = run('prepareContracts', rows);
for (const c of prepared) {
  assert.equal(run('getVigilanceScore', c), null, 'Korean rows are not assessed yet');
  assert.match(run('computeAssessment', c).excludedReason, /Korean checks are not set yet/);
}
assert.equal(run('exportRecord', prepared[1]).supplier, 'individual (name in the explorer)');
assert.equal(run('exportRecord', prepared[0]).supplier, '(주)회사');
console.log('Korea: shard rows to records, browse-only, individual businesses flagged and left out of exports by name.');
