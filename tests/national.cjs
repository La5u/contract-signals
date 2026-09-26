// Ukraine (Prozorro) and Portugal/Romania (TED): cohorts, checks and exclusions.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const ctx = vm.createContext({URL});
vm.runInContext(fs.readFileSync('script.js','utf8'),ctx);
const run = (fn,...args) => {ctx.args=args;return vm.runInContext(`${fn}(...args)`,ctx);};

function tally(rows) {
  const checks = {}; let flagged = 0, zero = 0, notAssessed = 0;
  for (const row of rows) {
    const a = run('getAssessment', row);
    assert.equal(a.checks.length, 8);
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
    // Reporting is out of scope, never unknown, never a signal.
    if (r.procedure === 'reporting') for (const c of run('getAssessment', r).checks.filter(c => /single-offer|direct/.test(c.id))) assert.equal(c.status, 'not-applicable');
    if (r.procedureDirect === false) assert.ok(Number.isInteger(r.offers));
  }
  const t = tally(rows);
  assert.deepEqual(pick(t, 'ua-'), {
    'ua-single-offer': [38,26,0,424], 'ua-direct-award': [0,64,0,424], 'ua-repeated-single-offer': [10,28,0,450],
    'ua-repeated-direct': [0,0,0,488], 'ua-concentration': [0,483,5,0], 'ua-better-bid-disqualified': [9,55,0,424] });
  assert.deepEqual(t.counts, [47,441,0]);
  // Disqualification before the award: counted per lot, only on competitive procedures, never on reporting.
  for (const r of rows) {
    if (r.procedureDirect !== false) assert.equal(r.disqualifiedBefore, null);
    const ids = run('getAssessment', r).checks.map(c => c.id);
    assert.equal(ids.length, 8); assert.ok(!ids.includes('short-bidding-period'));
  }
  const dq = (n) => run('getAssessment', { ...rows.find(r => r.procedureDirect === false), disqualifiedBefore: n }).checks.find(c => c.id === 'ua-better-bid-disqualified');
  assert.equal(dq(0).status, 'clear'); assert.equal(dq(2).weight, 12); assert.equal(dq(null).status, 'unknown');
  console.log('Ukraine Prozorro: 488 contracts, 47 flagged (9 by a better-ranked bidder disqualified), reporting out of scope, offers counted per lot.');
}

// ---- Portugal and Romania (TED) ----
for (const [file, country, expected, counts] of [
  ['data/ted-portugal.json', 'PRT', { 'ted-single-offer': [64,322,43,64], 'ted-direct-award': [64,416,13,0], 'ted-repeated-single-offer': [20,43,44,386],
    'ted-repeated-direct': [36,25,16,416], 'ted-concentration': [0,237,256,0] }, [128,359,6]],
  ['data/ted-romania.json', 'ROU', { 'ted-single-offer': [132,209,11,4], 'ted-direct-award': [4,352,0,0], 'ted-repeated-single-offer': [42,77,24,213],
    'ted-repeated-direct': [0,0,4,352], 'ted-concentration': [0,70,286,0] }, [136,220,0]],
]) {
  const rows = load(file), cov = JSON.parse(fs.readFileSync(file.replace('.json', '-coverage.json')));
  assert.equal(cov.cohort.country, country);
  assert.match(cov.license, /2011\/833\/EU/);
  for (const r of rows) {
    assert.equal(r.country, country); assert.ok(cov.cohort.buyers.some(b => b.id === r.buyerId));
    assert.match(r.source, /^https:\/\/ted\.europa\.eu\/en\/notice\/-\/detail\/\d+-\d{4}$/);
    assert.ok(r.publicationDate >= '2024-09-01' && r.publicationDate < '2026-09-01');
    for (const s of r.supplierIds) if (['NIF','CUI'].includes(s.identifierType)) assert.match(s.id, /^\d+$/);
  }
  const t = tally(rows);
  assert.deepEqual(pick(t, 'ted-'), expected);
  assert.deepEqual(t.counts, counts);
  console.log(`TED ${country}: ${rows.length} lots, ${counts[0]} flagged.`);
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
    assert.equal(r.supplierIds.length, 1); assert.equal(r.supplierIds[0].identifierType, 'CL-RUT'); assert.match(r.supplierIds[0].id, /^\d+[\dkK]?$/);
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
