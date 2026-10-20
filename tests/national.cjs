// Ukraine (Prozorro) and Portugal/Romania (TED): cohorts, checks and exclusions.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const ctx = vm.createContext({URL});
require('../tools/engine.cjs').load(ctx);
const run = (fn,...args) => {ctx.args=args;return vm.runInContext(`${fn}(...args)`,ctx);};

function tally(rows) {
  const checks = {}; let flagged = 0, zero = 0, notAssessed = 0;
  for (const row of rows) {
    const a = run('getAssessment', row);
    assert.equal(a.checks.length, row.dataFamily === 'prozorro' ? 13 : 9);
    for (const c of a.checks) { checks[c.id] ??= {signal:0,clear:0,unknown:0,'not-applicable':0}; checks[c.id][c.status]++; }
    const s = run('getVigilanceScore', row);
    if (s == null) notAssessed++; else if (s > 0) flagged++; else zero++;
  }
  return { checks: JSON.parse(JSON.stringify(checks)), counts: [flagged, zero, notAssessed] };
}
const load = f => run('prepareContracts', JSON.parse(fs.readFileSync(f)));
const pick = (t, prefix) => Object.fromEntries(Object.entries(t.checks).filter(([k]) => k.startsWith(prefix)).map(([k, v]) => [k, [v.signal, v.clear, v.unknown, v['not-applicable']]]));

// ---- Ukraine ----
{
  const rows = load('data/prozorro.json'), cov = JSON.parse(fs.readFileSync('data/prozorro-coverage.json'));
  assert.deepEqual(cov.cohort.buyers.map(b => [b.code, b.level]), [['00012925','national'],['20089290','regional'],['26510514','municipal']]);
  assert.equal(cov.counts.tendersInWindow, 526); assert.equal(cov.counts.tendersWithAnotherBuyer, 16);
  assert.equal(rows.length, 488);
  for (const r of rows) {
    assert.equal(r.dataFamily, 'prozorro'); assert.ok(r.tenderCreated >= '2024-09-01' && r.tenderCreated < '2026-09-01');
    assert.match(r.source, /^https:\/\/public-api\.prozorro\.gov\.ua\/api\/2\.5\/tenders\/[0-9a-f]{32}$/);
    const ids = run('getAssessment', r).checks.map(c => c.id);
    for (const foreign of ['single-bid','direct-award','secop2-plurality-award','dncp-single-tenderer']) assert.ok(!ids.includes(foreign));
    // Reporting is out of scope, never unknown, never a signal, except for the D2 direct-contract check (v3.7).
    if (r.procedure === 'reporting') for (const c of run('getAssessment', r).checks.filter(c => /single-offer|direct/.test(c.id) && c.id !== 'ua-direct-contract')) assert.equal(c.status, 'not-applicable');
    const d2 = run('getAssessment', r).checks.find(c => c.id === 'ua-direct-contract');
    assert.equal(d2.status, r.procedure !== 'reporting' ? 'not-applicable' : r.amount >= 200000 ? 'signal' : 'clear');
    if (r.procedureDirect === false) assert.ok(Number.isInteger(r.offers));
  }
  const t = tally(rows);
  assert.deepEqual(pick(t, 'ua-'), {
    'ua-contract-amendments': [1,487,0,0], 'ua-term-extension': [5,483,0,0], 'ua-single-offer': [38,26,0,424], 'ua-direct-award': [0,64,0,424], 'ua-repeated-single-offer': [10,28,0,450],
    'ua-repeated-direct': [0,0,0,488], 'ua-concentration': [0,483,5,0], 'ua-better-bid-disqualified': [9,55,0,424],
    'ua-buyer-share': [11,231,246,0], 'ua-direct-contract': [66,358,0,64] });
  assert.deepEqual(t.counts, [118,370,0]);
  // Disqualification before the award: counted per lot, only on competitive procedures, never on reporting.
  for (const r of rows) {
    if (r.procedureDirect !== false) assert.equal(r.disqualifiedBefore, null);
    const ids = run('getAssessment', r).checks.map(c => c.id);
    assert.equal(ids.length, 13); assert.ok(!ids.includes('short-bidding-period'));
  }
  const amendments = (fields) => run('getAssessment', { ...rows[0], contractChanges: undefined, contractChangeTypes: undefined, ...fields }).checks.find(c => c.id === 'ua-contract-amendments');
  assert.equal(amendments({contractChanges: 3, contractChangeTypes: ['priceReduction']}).status, 'signal');
  assert.equal(amendments({contractChanges: 3}).weight, 6); assert.equal(amendments({contractChanges: 4}).weight, 6);
  assert.equal(amendments({contractChanges: 5}).weight, 10);
  // v3.5: an amendment extending the term adds 6 points to three or more amendments, and scores 4 on its own below three.
  assert.equal(amendments({contractChanges: 3, contractChangeTypes: ['durationExtension']}).weight, 12);
  assert.equal(amendments({contractChanges: 5, contractChangeTypes: ['fiscalYearExtension']}).weight, 16);
  const term = (fields) => run('getAssessment', { ...rows[0], contractChanges: undefined, contractChangeTypes: undefined, ...fields }).checks.find(c => c.id === 'ua-term-extension');
  assert.equal(term({contractChanges: 1, contractChangeTypes: ['durationExtension']}).weight, 4);
  assert.equal(term({contractChanges: 1, contractChangeTypes: ['priceReduction']}).status, 'clear');
  assert.equal(term({}).status, 'unknown'); assert.equal(term({contractChanges: 0}).family, 'execution');
  assert.equal(run('indicatorKind', 'ua-term-extension'), 'term-extension');
  assert.equal(run('getVigilanceScore', {...rows.find(r => r.procedure === 'reporting'), contractChanges: 3, contractChangeTypes: ['durationExtension']}), 12);
  assert.equal(amendments({contractChanges: 2}).status, 'clear');
  assert.equal(amendments({}).status, 'unknown');
  assert.equal(amendments({}).reason, 'Contract record not retrieved: amendments not assessable.');
  assert.equal(amendments({}).applicability, 'yes');
  assert.equal(amendments({contractChanges: 3}).family, 'execution');
  assert.equal(run('indicatorKind', 'ua-contract-amendments'), 'contract-amendments');
  assert.equal(run('selectContracts', [{...rows[0], contractChanges: 3}, {...rows[1], contractChanges: 2}], {indicator: 'contract-amendments'}).length, 1);
  const dq = (n) => run('getAssessment', { ...rows.find(r => r.procedureDirect === false), disqualifiedBefore: n }).checks.find(c => c.id === 'ua-better-bid-disqualified');
  assert.equal(dq(0).status, 'clear'); assert.equal(dq(2).weight, 4); assert.equal(dq(null).status, 'unknown');
  // v3.5: a single offer scores 1 point in Ukraine only (12 elsewhere).
  const single = run('getAssessment', { ...rows.find(r => r.procedureDirect === false), offers: 1 }).checks.find(c => c.id === 'ua-single-offer');
  assert.equal(single.status, 'signal'); assert.equal(single.weight, 1);
  assert.equal(rows.filter(r=>r.linkedContract).length,3);
  for(const r of rows.filter(r=>r.linkedContract)) assert.ok(run('verificationLinks',r).some(l=>l.url===r.linkedContract.url));
  assert.ok(rows.every(r=>!run('getAssessment',r).checks.some(c=>c.id==='ua-bid-attrition')),'bid-attrition decisions are context, not a check');
  // v3.6: a contract of 5 % or more of its buyer's UAH total for a completely covered year signals (competition); 2.2 points since v3.8 (30 before: a size effect).
  const share = (fields) => run('getAssessment', { ...rows.find(r => r.uaBuyerShare?.complete), ...fields }).checks.find(c => c.id === 'ua-buyer-share');
  const big = rows.find(r => r.uaBuyerShare?.share >= 0.05 && r.uaBuyerShare.complete);
  assert.equal(share(big).status, 'signal'); assert.equal(share(big).weight, 2.2); assert.equal(share(big).family, 'competition');
  assert.equal(share({ uaBuyerShare: { ...big.uaBuyerShare, complete: false } }).status, 'unknown');
  assert.equal(share({ uaBuyerShare: { ...big.uaBuyerShare, share: null } }).status, 'unknown');
  assert.equal(share({ uaBuyerShare: { ...big.uaBuyerShare, share: 0.049 } }).status, 'clear');
  assert.ok(rows.filter(r => r.uaBuyerShare?.complete).every(r => r.uaBuyerShare.year === '2025'), 'only 2025 is complete in the bundled cohort');
  assert.equal(run('indicatorKind', 'ua-buyer-share'), 'buyer-share');
  // v3.7: D2, a direct-contract report of UAH 200,000 or more, scores 11 (competition); negotiated awards score 10, not 18.
  const reportingRow = rows.find(r => r.procedure === 'reporting');
  const d2 = (fields) => run('getAssessment', { ...reportingRow, ...fields }).checks.find(c => c.id === 'ua-direct-contract');
  assert.equal(d2({ amount: 200000, currency: 'UAH' }).weight, 11); assert.equal(d2({ amount: 200000, currency: 'UAH' }).family, 'competition');
  assert.equal(d2({ amount: 199999.99, currency: 'UAH' }).status, 'clear');
  assert.equal(d2({ amount: 500000, currency: 'EUR' }).status, 'unknown');
  assert.equal(run('indicatorKind', 'ua-direct-contract'), 'direct-award');
  const negotiated = run('getAssessment', { ...rows.find(r => r.procedureDirect === false), procedure: 'negotiation', procedureDirect: true }).checks.find(c => c.id === 'ua-direct-award');
  assert.equal(negotiated.status, 'signal'); assert.equal(negotiated.weight, 10);
  console.log('Ukraine Prozorro: 488 contracts, 118 flagged (66 by a direct contract of UAH 200,000 or more, 11 by buyer share, 9 by a better-ranked bidder disqualified), offers counted per lot.');
}

// ---- Portugal and Romania (TED) ----
for (const [file, country, expected, counts] of [
  ['data/ted-portugal.json', 'PRT', { 'ted-single-offer': [63,319,43,63], 'ted-direct-award': [63,412,13,0], 'ted-repeated-single-offer': [20,42,44,382],
    'ted-repeated-direct': [35,25,16,412], 'ted-concentration': [0,234,254,0], 'late-publication': [11,477,0,0] }, [136,352,0]],
  ['data/ted-romania.json', 'ROU', { 'ted-single-offer': [125,186,6,4], 'ted-direct-award': [4,317,0,0], 'ted-repeated-single-offer': [42,70,19,190],
    'ted-repeated-direct': [0,0,4,317], 'ted-concentration': [0,43,278,0], 'late-publication': [12,309,0,0] }, [138,183,0]],
  ['data/ted-czechia.json', 'CZE', { 'ted-single-offer': [89,254,267,20], 'ted-direct-award': [20,344,266,0], 'ted-repeated-single-offer': [12,74,270,274],
    'ted-repeated-direct': [7,13,266,344], 'ted-concentration': [14,393,223,0], 'late-publication': [15,613,2,0] }, [135,495,0]],
]) {
  const rows = load(file), cov = JSON.parse(fs.readFileSync(file.replace('.json', '-coverage.json')));
  assert.equal(cov.cohort.country, country);
  assert.match(cov.license, /2011\/833\/EU/);
  for (const r of rows) {
    assert.equal(r.country, country); assert.ok(cov.cohort.buyers.some(b => b.id === r.buyerId));
    assert.match(r.source, /^https:\/\/ted\.europa\.eu\/en\/notice\/-\/detail\/\d+-\d{4}$/);
    assert.ok(r.publicationDate >= '2024-09-01' && r.publicationDate < '2026-09-01');
    for (const s of r.supplierIds) if (['NIF','CUI','ICO'].includes(s.identifierType)) assert.match(s.id, /^\d+$/);
  }
  const t = tally(rows);
  assert.deepEqual({...pick(t, 'ted-'), ...pick(t, 'late-')}, expected);
  assert.deepEqual(t.counts, counts);
  console.log(`TED ${country}: ${rows.length} lots, ${counts[0]} flagged.`);
}

// A lot listed again in a later award notice of the same procedure (same contract reference and
// conclusion date) is kept once, from its first publication: Cluj-Napoca's 575056-2026 relists the
// four lots of 13780-2026 with 0.01 RON placeholders and must not add rows or late-publication signals.
{
  const ro = load('data/ted-romania.json'), cov = JSON.parse(fs.readFileSync('data/ted-romania-coverage.json'));
  assert.equal(cov.counts.relistedLotsExcluded, 35);
  assert.ok(!ro.some(r => r.noticeId === '575056-2026'));
  assert.deepEqual(ro.filter(r => r.noticeId === '13780-2026').map(r => r.amount), [2130296.39, 1965109.3, 5574428.85, 5887692.2]);
  assert.deepEqual(ro.filter(r => r.noticeId === '513566-2026').map(r => r.lotId), ['LOT-0003']);
  assert.ok(!ro.some(r => r.amount != null && r.amount > 0 && r.amount < 1));
  console.log('TED republished lots kept once, from the first notice.');
}
// v3.7: Romanian repeated awards without competition and concentration score a token point; other TED countries keep 18 and 12 at entry, capped at 30 (editorial maximum).
{
  const withId = f => load(f).find(r => run('nationalSupplierIdentity', r));
  const ro = withId('data/ted-romania.json'), cz = withId('data/ted-czechia.json');
  const weight = (row, id, fields) => run('getAssessment', { ...row, ...fields }).checks.find(c => c.id === id).weight;
  const repeated = { procedureDirect: true, nationalRepeatedDirect: { count: 10 } };
  const concentrated = { nationalConcentration: { category: '45', wins: 10, known: 10, total: 10, coverage: 1, share: 1, sufficient: true } };
  assert.equal(weight(ro, 'ted-repeated-direct', repeated), 1); assert.equal(weight(cz, 'ted-repeated-direct', repeated), 30);
  assert.equal(weight(ro, 'ted-concentration', concentrated), 1); assert.equal(weight(cz, 'ted-concentration', concentrated), 30);
  assert.equal(weight(ro, 'ted-direct-award', { procedureDirect: true }), 18);
}

// ---- United Kingdom (Find a Tender) ----
{
  const rows = load('data/uk-fts.json'), cov = JSON.parse(fs.readFileSync('data/uk-fts-coverage.json'));
  assert.deepEqual(cov.cohort.buyers.map(b => [b.id, b.level]), [['GB-FTS-131','national'],['GB-FTS-39','regional'],['GB-FTS-289','municipal']]);
  assert.match(cov.license, /Open Government Licence v3\.0/);
  assert.equal(cov.retrieval.indexedAwardReleases, 33457); assert.equal(cov.retrieval.noticesDownloaded, 516);
  assert.equal(rows.length, 1081);
  for (const r of rows) {
    assert.equal(r.dataFamily, 'fts'); assert.ok(cov.cohort.buyers.some(b => b.id === r.buyerId));
    assert.match(r.source, /^https:\/\/www\.find-tender\.service\.gov\.uk\/api\/1\.0\/ocdsReleasePackages\/\d{6}-\d{4}$/);
    assert.ok(!/@|contactPoint|email/i.test(JSON.stringify(r)), 'no contact data imported');
    if (r.procedureDirect !== false) assert.equal(r.offers, null);
  }
  const t = tally(rows);
  assert.deepEqual(pick(t, 'uk-'), { 'uk-single-offer': [20,1031,7,23], 'uk-direct-award': [23,1053,5,0], 'uk-repeated-single-offer': [4,16,7,1054],
    'uk-repeated-direct': [0,23,5,1053], 'uk-concentration': [0,359,722,0] });
  assert.deepEqual(t.counts, [43,1036,2]);
  // Identity: platform party id only; a Companies House number would not change the key.
  const r0 = rows.find(r => r.supplierIds.length);
  assert.equal(run('nationalSupplierIdentity', r0), `GB-FTS:${r0.supplierIds[0].id}`);
  assert.equal(run('nationalSupplierIdentity', {...r0, supplierIds: [...r0.supplierIds, {id:'01234567', identifierType:'GB-COH'}]}), `GB-FTS:${r0.supplierIds[0].id}`);
  console.log('United Kingdom Find a Tender: 1,081 awards, 43 flagged, no contact data, identity by platform id.');
}

// ---- Chile (Mercado Público) ----
{
  const rows = load('data/chile-mp.json'), cov = JSON.parse(fs.readFileSync('data/chile-mp-coverage.json'));
  assert.deepEqual(cov.cohort.buyers.map(b => [b.id, b.level]), [['CL-MP-2015','national'],['CL-MP-2592','regional'],['CL-MP-3414','municipal']]);
  assert.match(cov.license, /CC0 1\.0/); assert.deepEqual(cov.retrieval.emptyMonths, ['2026-08']);
  assert.equal(cov.counts.tendersListed, 844); assert.equal(cov.counts.excluded['award record unavailable (API error)'], 47);
  assert.equal(rows.length, 522);
  for (const r of rows) {
    assert.equal(r.dataFamily, 'chile'); assert.equal(r.currency, 'CLP'); assert.ok(cov.cohort.buyers.some(b => b.id === r.buyerId));
    assert.equal(r.supplierIds.length, 1); assert.equal(r.supplierIds[0].identifierType, 'CL-RUT'); assert.match(r.supplierIds[0].id, /^(\d+[\dkK]?|masked-[0-9a-f]{16})$/);
    assert.ok(!/@|contactPoint|email/i.test(JSON.stringify(r)), 'no contact data imported');
    const direct = run('getAssessment', r).checks.find(c => c.id === 'cl-direct-award');
    assert.equal(direct.status, 'not-applicable'); assert.match(direct.reason, /trato directo/);
  }
  const t = tally(rows);
  assert.deepEqual(pick(t, 'cl-'), { 'cl-single-offer': [71,448,3,0], 'cl-direct-award': [0,0,0,522], 'cl-repeated-single-offer': [14,57,3,448],
    'cl-repeated-direct': [0,0,0,522], 'cl-concentration': [0,296,226,0] });
  assert.deepEqual(t.counts, [71,449,2]);
  console.log('Chile Mercado Público: 522 awards, 71 flagged, direct deals out of scope, identity by RUT.');
}

// Concentration counts distinct procedures: a supplier winning many lots of one notice wins once.
{
  const rows = load('data/ted-romania.json');
  const r = rows.find(x => x.nationalConcentration && x.supplierIds[0]?.id === '1770555' && x.cpv.startsWith('37'));
  assert.equal(r.nationalConcentration.wins, 1);
  console.log('Concentration counts procedures, not lots.');
}

// "Declared without competition" covers the source's own declaration in every family:
// DECP/BOAMP directAward, TED and Find a Tender procedureDirect.
{
  const pt = run('prepareContracts', JSON.parse(fs.readFileSync('data/ted-portugal.json')));
  const direct = run('selectContracts', pt, { legal: 'direct' });
  assert.equal(direct.length, pt.filter(c => c.procedureDirect === true).length);
  assert.ok(direct.length > 0);
  assert.ok(direct.every(c => c.procedureDirect === true));
  console.log(`Declared-without-competition filter: ${direct.length} Portuguese TED direct awards.`);
}
