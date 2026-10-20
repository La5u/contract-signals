const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const ctx = vm.createContext({ URL });
require('../tools/engine.cjs').load(ctx);
const ledger = JSON.parse(fs.readFileSync('data/public-link-evidence.json', 'utf8'));
const links = JSON.parse(fs.readFileSync('data/boamp-decp-links.json', 'utf8'));
const result = ctx.validatePublicLinkEvidence(ledger, links);
assert.equal(result.length, 9);
assert.equal(result.filter(p => p.conclusion.startsWith('disfavored')).length, 2);
assert.equal(result.filter(p => p.conclusion.startsWith('reference-pattern')).length, 5);
assert.equal(result.filter(p => p.conclusion.startsWith('lot-compatible')).length, 2);
assert.ok(result.every(p => !('fields' in p) && !('liveRequests' in p)));
for (const mutate of [d => d.schemaVersion++, d => d.confirmed = 1, d => d.resolved = 1,
  d => d.sourceHashes['data/contracts.json'] = 'bad', d => d.pairs[0].confirmed = true,
  d => d.pairs[0].resolution = 'corrected', d => d.pairs[0].boampUrl = 'javascript:alert(1)',
  d => d.pairs[0].decpId = 'decp-missing', d => d.pairs[0].conclusion = 'confirmed',
  d => d.pairs[0].notes = 'x'.repeat(2001), d => d.pairs.push(d.pairs[0]),
  d => d.pairs[1] = d.pairs[0], d => d.pairs[0].publishedReference = null]) {
  const changed = structuredClone(ledger); mutate(changed);
  assert.throws(() => ctx.validatePublicLinkEvidence(changed, links));
}
const confirmed = structuredClone(links);
confirmed.links[0].status = 'confirmed';
assert.throws(() => ctx.validatePublicLinkEvidence(ledger, confirmed));
for (const p of result) {
  const label = ctx.publicLinkEvidenceLabel(p);
  assert.match(label, /unconfirmed|candidate|not proof/);
  assert.doesNotMatch(label, /^Confirmed/);
}
const resolutions = JSON.parse(fs.readFileSync('data/public-link-resolutions.json', 'utf8'));
const reviewed = ctx.validatePublicLinkResolutions(resolutions, links);
assert.equal(reviewed.activePairs.length, 7);
assert.equal(reviewed.dismissedPairs.length, 2);
assert.equal(reviewed.counts.confirmedDecpLinks, 0);
assert.equal(reviewed.counts.verifiedTedNoticeVersions, 3);
for (const mutate of [d => d.schemaVersion++, d => d.sourceHashes['data/contracts.json'] = 'bad',
  d => d.dismissedPairs[0].replacementLinkConfirmed = true, d => d.dismissedPairs[0].disposition = 'confirmed',
  d => d.dismissedPairs[0].reason = '', d => d.activePairs.pop(),
  d => d.activePairs[0].activeWarnings.push('multiple-decp-matches'),
  d => d.tedNotices[0].decpCrosswalkConfirmed = true,
  d => d.tedNotices[0].url = 'javascript:alert(1)',
  d => d.tedNotices[0].httpStatus = '429', d => d.counts.confirmedDecpLinks = 1]) {
  const changed = structuredClone(resolutions); mutate(changed);
  assert.throws(() => ctx.validatePublicLinkResolutions(changed, links));
}
console.log('Public evidence UI: snapshot-bound annotations, seven active leads, two audited dismissals, notice-only TED verification; invalid/stale artifacts rejected.');
