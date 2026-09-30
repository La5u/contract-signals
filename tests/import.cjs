'use strict';
const assert = require('node:assert/strict');
const api = require('../import.js');

function throws(fn, pattern) { assert.throws(fn, pattern); }

const csv = '\uFEFFid,buyer,description,amount,offers,currency,direct award\r\n1,"Buyer, Inc.","line one\nline ""two""",0,0,EUR,false\r\n';
const parsed = api.parse(csv);
assert.equal(parsed.format, 'csv');
assert.equal(parsed.records[0].buyer, 'Buyer, Inc.');
assert.equal(parsed.records[0].description, 'line one\nline "two"');
assert.equal(parsed.records[0].amount, 0);
assert.equal(parsed.records[0].offers, 0);
assert.equal(parsed.records[0].directAward, false);
assert.equal(parsed.records[0].assessmentMode, 'browse');
assert.equal(parsed.records[0].dataStatus, 'unverified');
assert(parsed.warnings.some(w => /unverified/.test(w)));

throws(() => api.parse('id;acheteur;description;amount;currency\n2;Mairie;Travaux;12,5;EUR'), /row 2 \(2\).*amount/i);
const semi = api.parse('id;acheteur;description;amount;currency\n2;Mairie;Travaux;12;EUR');
assert.equal(semi.records[0].buyer, 'Mairie');
assert.equal(semi.records[0].amount, 12);
assert.equal(semi.records[0].currency, 'EUR');
const mapped = api.parse('key;owner;notes\nx;Council;Test', { mapping: { id: 'key', buyer: 'owner', description: 'notes' } });
assert.equal(mapped.records[0].id, 'x');
throws(() => api.parse('id,buyer,description\n1,b,c', { mapping: { buyer: 'missing' } }), /mapping/i);
throws(() => api.parse('id,buyer\n1,b'), /requires a description/i);
throws(() => api.parse('id,buyer,description\n1,b,"bad'), /unterminated/i);
throws(() => api.parse(''), /empty/i);
throws(() => api.parse('id,buyer,description\n' + 'x'.repeat(25 * 1024 * 1024)), /25 MiB/i);

const malicious = '<img src=x onerror=alert(1)>\t=HYPERLINK("bad")';
throws(() => api.parse(JSON.stringify([{ id: 'bad-json-row', buyer: 'b', description: malicious, amount: 'not-a-number' }])), /bad-json-row.*amount/i);
throws(() => api.parse('id,buyer,description,directAward\nx,b,d,perhaps'), /row 2 \(x\).*directAward/i);
throws(() => api.parse('id,buyer,description,amount\nx,b,d,broken'), /row 2 \(x\).*amount/i);
const literal = api.parse(JSON.stringify([{ id: 'x', buyer: 'b', description: malicious, dataFamily: 'decp', cohortId: 'native' }])).records[0];
assert.equal(literal.description, malicious);
assert.equal(literal.dataFamily, 'decp');
const french = api.parse(JSON.stringify([{ id: 'x', buyer: 'b', description: 'd', dataFamily: 'decp', cohortId: 'native' }]), { method: 'french' }).records[0];
assert.equal(french.assessmentMode, 'french');
assert(!('dataFamily' in french)); assert(!('cohortId' in french));

throws(() => api.parse(JSON.stringify(Array.from({ length: 20001 }, (_, i) => ({ id: String(i), buyer: 'b', description: 'd' })))), /20,000/i);
const envelope = api.parse(JSON.stringify({ records: [{ id: 'e', buyer: 'b', description: 'd' }] }));
assert.equal(envelope.format, 'json'); assert.equal(envelope.records.length, 1);

const packageDoc = { records: [{ compiledRelease: {
  ocid: 'oc-1', parties: [{ id: 'buyer', name: 'Public Buyer', roles: ['buyer'] }, { id: 'sup', name: 'Supplier', identifier: { scheme: 'VAT', id: '123' }, roles: ['supplier'] }],
  tender: { title: 'Tender', procurementMethod: 'direct', items: [{ classification: { scheme: 'CPV', id: '45000000-7' } }] },
  awards: [
    { id: 'a1', date: '2024-01-02T00:00:00Z', value: { amount: 0, currency: 'EUR' }, suppliers: [{ id: 'sup' }] },
    { id: 'a2', date: '2024-02-03', value: { amount: 9, currency: 'XXX' }, suppliers: [{ id: 'sup' }] }
  ]
} }] };
const awards = api.parse(JSON.stringify(packageDoc), { method: 'french' });
assert.equal(awards.format, 'ocds'); assert.equal(awards.records.length, 2);
assert.deepEqual(awards.records.map(r => r.id), ['oc-1/a1', 'oc-1/a2']);
assert.equal(awards.records[0].buyer, 'Public Buyer');
assert.equal(awards.records[0].supplier, 'Supplier');
assert.equal(awards.records[0].date, '2024-01-02');
assert.equal(awards.records[0].cpv, '45000000-7');
assert.equal(awards.records[0].directAward, null); // Method alone is not evidence.
assert.equal(awards.records[0].offers, null);
assert.equal(awards.records[1].currency, null);
assert(awards.warnings.some(w => /published awards.*not necessarily signed contracts/i.test(w)));
assert.equal(awards.records[0].assessmentMode, 'french');
throws(() => api.parse(JSON.stringify({ releases: [{ ocid: 'same', awards: [] }, { ocid: 'same', awards: [] }] })), /multiple OCDS releases/i);
throws(() => api.parse(JSON.stringify({ records: [{ id: 'entry-1', url: 'https://example.test/release' }] })), /entry-1.*missing.*URL/i);
const release = { ocid: 'array-1', buyer: { name: 'B' }, awards: [{ id: 'a', suppliers: [{ id: 'unknown', name: 'Fallback supplier' }] }] };
throws(() => api.parse(JSON.stringify({ ...release, awards: [{ id: 'bad', date: '2024-01-02not-a-date' }] })), /invalid date/);
throws(() => api.parse(JSON.stringify({ ...release, awards: [{ id: 'bad', date: '2024-02-30' }] })), /invalid calendar date/);
const explicitBuyer = api.parse(JSON.stringify({ ...release, buyer: { name: 'Explicit buyer' }, parties: [{ id: 'wrong', name: 'Other buyer', roles: ['buyer'] }] }));
assert.equal(explicitBuyer.records[0].buyer, 'Explicit buyer');
throws(() => api.parse(JSON.stringify({ ...release, buyer: null, parties: [{ name: 'A', roles: ['buyer'] }, { name: 'B', roles: ['buyer'] }] })), /multiple buyers/);
const multiSector = api.parse(JSON.stringify({ ...release, tender: { items: [{ classification: { scheme: 'CPV', id: '45000000-7' } }, { classification: { scheme: 'CPV', id: '72000000-5' } }] } }));
assert.equal(multiSector.records[0].cpv, null);
assert(multiSector.warnings.some(w => /multiple CPV/.test(w)));
const arrayRelease = api.parse(JSON.stringify([release]));
assert.equal(arrayRelease.format, 'ocds');
assert.equal(arrayRelease.records[0].supplier, 'Fallback supplier');
assert.deepEqual(arrayRelease.records[0].supplierIds, [{ id: 'unknown' }]);
const preferred = api.parse(JSON.stringify({ records: [{ compiledRelease: release, releases: [{ ocid: 'array-1', awards: [{ id: 'old' }] }] }], releases: [{ ocid: 'array-1', awards: [{ id: 'also-old' }] }] }));
assert.deepEqual(preferred.records.map(r => r.awardId), ['a']);
const canonical = api.parse('id,buyer,description,buyerSiret,directAward,dataStatus,source\nx,b,d,12345678901234,false,verified,https://example.test');
assert.equal(canonical.records[0].buyerSiret, '12345678901234');
assert.equal(canonical.records[0].directAward, false);
assert.equal(canonical.records[0].dataStatus, 'verified');
assert.equal(canonical.records[0].source, 'https://example.test');
throws(() => api.parse('id,buyer,id,description\nx,b,y,d'), /duplicate header/i);
throws(() => api.parse(`${Array.from({length: 1001}, (_, i) => `c${i}`).join(',')}\n${Array(1001).fill('x').join(',')}`), /1,000-column/i);
assert.deepEqual(api.columns('"id;label";buyer;description\nx;b;d'), ['id;label', 'buyer', 'description']);

assert.deepEqual(api.columns('id;buyer;description\n1;b;d'), ['id', 'buyer', 'description']);
(async () => {
  const fp = await api.fingerprint('a', 'browse', {});
  assert.match(fp, /^[0-9a-f]{64}$/);
  assert.notEqual(fp, await api.fingerprint('b', 'browse', {}));
  assert.notEqual(fp, await api.fingerprint('a', 'french', {}));
  assert.notEqual(fp, await api.fingerprint('a', 'browse', { id: 'key' }));
  console.log('import: ok');
})().catch(err => { console.error(err); process.exitCode = 1; });
