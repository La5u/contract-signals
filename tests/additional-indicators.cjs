'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const a = 'applicable';
const fixtures = {
  cap: { applicability:a, sourceRefs:['synthetic:cap-amendments-and-confirmed-limit'], legalCapConfirmed:true, baseVerified:true, amendmentsVerified:true, baseAmount:100, cumulativeAmendments:19, capRate:.2, baseBasis:'EUR net original base', amendmentsBasis:'EUR net original base' },
  execution: { applicability:a, sourceRefs:['synthetic:payments-ledger','synthetic:independent-completion-report'], paymentsAsOf:'2024-02-29', completionAsOf:'2024-02-29', paymentsVerified:true, completionIndependentlyDocumented:true, actualPayments:109, advances:5, refunds:5, payableAmount:100, physicalCompletion:.8, samePaymentBasis:true },
  legalGround: { applicability:a, sourceRefs:['synthetic:reviewed-legal-mapping'], mappingReviewed:true, classificationVerified:true, jurisdiction:'J', mappingJurisdiction:'J', classification:'C', mappingClassification:'C', legalGround:'G', mappingLegalGround:'G', date:'2024-02-29', validFrom:'2024-01-01', validTo:'2024-12-31', compatible:false },
  unitPrice: { applicability:a, sourceRefs:['synthetic:matched-unit-prices-and-inflation-index'], unitPricesVerified:true, previousYear:2023, currentYear:2024, previousUnitPrice:100, currentUnitPrice:143, inflationFactor:1.1, matched: { buyer:true,supplier:true,item:true,specification:true,quantity:true,unit:true,currency:true,taxTerms:true,deliveryTerms:true } },
  exclusivity: { applicability:a, sourceRefs:['synthetic:claim-and-comparable-competitive-win'], claim:'exclusivity', claimDocumented:true, supplierIdentityVerified:true, comparableCompetitiveWinDocumented:true, sameMarket:true, sameServiceTerritory:true, relevantTime:true, comparableRightsContext:true, competitiveOfferCount:2 }
};

function harness(engine = true) {
  const ctx = vm.createContext({ URL, structuredClone });
  if (engine) vm.runInContext(fs.readFileSync('indicator-evidence.js', 'utf8'), ctx);
  vm.runInContext(fs.readFileSync('script.js', 'utf8'), ctx);
  return (fn, ...args) => { ctx.args = args; return vm.runInContext(`${fn}(...args)`, ctx); };
}
const run = harness();
const c = { id:'synthetic', dataFamily:'decp', dataStatus:'verified', buyer:'Synthetic', description:'Synthetic', supplierIds:[], indicatorEvidence:fixtures };
const additional = run('getAdditionalIndicatorChecks', c);
assert.deepEqual(Array.from(additional, r => r.weight), [8,8,8,8,8]);
assert.equal(run('getScoreBreakdown',c).execution,8);
assert.equal(run('getScoreBreakdown',c).competition,8);
assert.equal(run('getVigilanceScore',c),16);
for (const id of Object.keys(fixtures)) {
  assert.equal(run('selectContracts',[c],{indicator:id}).length,1);
  assert.equal(run('indicatorKind',id),id);
  assert.ok(run('exportRecord',c).signals.includes(additional.find(r => r.id === id).label));
}
const empty = run('getAdditionalIndicatorChecks',{...c,indicatorEvidence:undefined});
assert.equal(empty.length,0);
assert.equal(run('getAdditionalIndicatorChecks',{...c,indicatorEvidence:{}}).length,0);
const onlyCap = run('getAdditionalIndicatorChecks',{...c,indicatorEvidence:{cap:fixtures.cap}});
assert.deepEqual(Array.from(onlyCap, r => r.id),['cap']);
assert.ok(harness(false)('getAdditionalIndicatorChecks',c).every(r => r.status === 'unknown'));
for (const extra of [{dataStatus:'unverified'},{identityAmbiguous:true},{initialConflicts:['x']},{modificationConflicts:['x']},{assessmentMode:'browse'}]) {
  const record = {...c,...extra};
  const a = run('computeAssessment',record);
  assert.equal(a.signals,0);
  assert.equal(run('getVigilanceScore',record),null);
  assert.ok(a.checks.filter(r => Object.hasOwn(fixtures,r.id)).every(r => r.status === 'unknown'));
}
for (const extra of [{findingScope:'aggregate'},{consultation:true},{noticeEvidence:true}]) {
  assert.ok(run('getAdditionalIndicatorChecks',{...c,...extra}).every(r => r.status === 'not-applicable'));
}
const malformed = {...c,indicatorEvidence:{cap:{...fixtures.cap,baseVerified:false}}};
assert.ok(run('getAdditionalIndicatorChecks',malformed).every(r => r.weight === null));
const a2 = run('computeAssessment',c);
assert.equal(a2.evaluated,a2.checks.filter(r => ['signal','clear'].includes(r.status)).length);
assert.equal(a2.unknownApplicability,a2.checks.filter(r => r.applicability === 'unknown').length);
console.log('additional indicators: OK');
