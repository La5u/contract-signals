'use strict';
const assert = require('node:assert/strict');
const { assess } = require('../tools/experimental-indicators.cjs');
assert.equal(assess, require('../indicator-evidence.js').assess, 'CLI/API wrapper uses the shared engine');
const a = 'applicable';
const fixtures = {
  cap: { applicability:a, sourceRefs:['synthetic:cap-amendments-and-confirmed-limit'], legalCapConfirmed:true, baseVerified:true, amendmentsVerified:true, baseAmount:100, cumulativeAmendments:19, capRate:.2, baseBasis:'EUR net original base', amendmentsBasis:'EUR net original base' },
  execution: { applicability:a, sourceRefs:['synthetic:payments-ledger','synthetic:independent-completion-report'], paymentsAsOf:'2024-02-29', completionAsOf:'2024-02-29', paymentsVerified:true, completionIndependentlyDocumented:true, actualPayments:109, advances:5, refunds:5, payableAmount:100, physicalCompletion:.8, samePaymentBasis:true },
  legalGround: { applicability:a, sourceRefs:['synthetic:reviewed-legal-mapping'], mappingReviewed:true, classificationVerified:true, jurisdiction:'J', mappingJurisdiction:'J', classification:'C', mappingClassification:'C', legalGround:'G', mappingLegalGround:'G', date:'2024-02-29', validFrom:'2024-01-01', validTo:'2024-12-31', compatible:false },
  unitPrice: { applicability:a, sourceRefs:['synthetic:matched-unit-prices-and-inflation-index'], unitPricesVerified:true, previousYear:2023, currentYear:2024, previousUnitPrice:100, currentUnitPrice:143, inflationFactor:1.1, matched: { buyer:true,supplier:true,item:true,specification:true,quantity:true,unit:true,currency:true,taxTerms:true,deliveryTerms:true } },
  exclusivity: { applicability:a, sourceRefs:['synthetic:claim-and-comparable-competitive-win'], claim:'exclusivity', claimDocumented:true, supplierIdentityVerified:true, comparableCompetitiveWinDocumented:true, sameMarket:true, sameServiceTerritory:true, relevantTime:true, comparableRightsContext:true, competitiveOfferCount:2 }
};
function result(id, changes = {}, options) { return assess({ indicators: { [id]: { ...fixtures[id], ...changes } } }, options).indicators.find(x => x.id === id); }
function status(id, changes, expected, options) { assert.equal(result(id,changes,options).status, expected, `${id}: ${JSON.stringify(changes)}`); }
assert.equal(assess({indicators:fixtures}).experimentalSum,40);
assert.equal(assess({indicators:fixtures}).experimentalMaximum,40);
for (const input of [null, [], {}, {indicators:{}}, {indicators:{unknown:{}}}]) assert.equal(assess(input).experimentalSum,null);
for (const id of Object.keys(fixtures)) {
  status(id,{},'signal');
  for (const sourceRefs of [undefined, null, [], '', [''], ['   '], [123], ['synthetic:evidence', null]]) status(id,{sourceRefs},'not-assessed');
  status(id,{unsupported:true},'not-assessed');
  status(id,{applicability:true},'not-assessed');
  const r = assess({indicators:{[id]:{applicability:'inapplicable'}}}).indicators.find(x=>x.id===id);
  assert.equal(r.status,'not-applicable'); assert.equal(r.points,null);
  status(id,{applicability:'inapplicable'},'not-assessed');
  for (const key of Object.keys(fixtures[id])) {
    const e = {...fixtures[id]}; delete e[key];
    assert.equal(assess({indicators:{[id]:e}}).indicators.find(x=>x.id===id).status,'not-assessed');
  }
}
status('cap',{cumulativeAmendments:18.99},'no-signal');
status('cap',{cumulativeAmendments:20},'signal');
const aboveCap = result('cap',{cumulativeAmendments:21});
assert.match(aboveCap.reason,/not automatic illegality/);
assert.equal(aboveCap.status,'no-signal');
assert.equal(aboveCap.points,0);
assert.equal(aboveCap.context.aboveCap,true);
assert.equal(result('cap').context.aboveCap,false);
for (const changes of [{baseAmount:0},{capRate:0},{baseAmount:'100'},{cumulativeAmendments:-1},{legalCapConfirmed:false},{legalCapConfirmed:1},{amendmentsBasis:'USD gross'},{baseAmount:Infinity},{baseAmount:Number.MIN_VALUE,capRate:Number.MIN_VALUE}]) status('cap',changes,'not-assessed');
status('cap',{cumulativeAmendments:0},'no-signal');
status('cap',{cumulativeAmendments:18},'signal',{capNearFraction:.9});
// Snapshots must be real ISO dates for the same day, not just dated evidence.
for (const changes of [{paymentsAsOf:'2024-02-28'}, {completionAsOf:'2024-03-01'}, {paymentsAsOf:'2024-02-30',completionAsOf:'2024-02-30'}, {paymentsAsOf:'2023-02-29'}, {completionAsOf:'2024-2-29'}, {paymentsAsOf:'2024-02-29T00:00:00Z'}, {completionAsOf:20240229}]) status('execution',changes,'not-assessed');
status('execution',{actualPayments:108.99},'no-signal');
status('execution',{physicalCompletion:.8001},'no-signal');
status('execution',{actualPayments:110,physicalCompletion:0},'signal');
for (const changes of [{payableAmount:0},{physicalCompletion:1.1},{physicalCompletion:-1},{actualPayments:9},{advances:-1},{paymentsVerified:false},{completionIndependentlyDocumented:false},{samePaymentBasis:false},{physicalCompletion:'0.8'},{elapsedDays:300},{completionDate:'2020-01-01'}]) status('execution',changes,'not-assessed');
status('execution',{actualPayments:0,advances:0,refunds:0},'no-signal');
status('execution',{physicalCompletion:.9},'signal',{maxCompletionFraction:.9});
status('legalGround',{compatible:true},'no-signal');
for (const changes of [{mappingReviewed:false},{classificationVerified:false},{mappingJurisdiction:'Other'},{mappingClassification:'Other'},{mappingLegalGround:'Other'},{date:'2025-01-01'},{date:'2024-02-30'},{date:'2023-02-29'},{validFrom:'2024-12-31',validTo:'2024-01-01'},{compatible:'false'},{jurisdiction:''},{keywords:'direct purchase'}]) status('legalGround',changes,'not-assessed');
status('legalGround',{date:'2024-01-01'},'signal');
status('legalGround',{date:'2024-12-31'},'signal');
status('unitPrice',{currentUnitPrice:142.99},'no-signal');
status('unitPrice',{currentUnitPrice:130,inflationFactor:1},'signal');
status('unitPrice',{currentUnitPrice:130,inflationFactor:1.1},'no-signal');
for (const changes of [{previousUnitPrice:0},{currentUnitPrice:0},{inflationFactor:0},{previousYear:2022},{currentYear:2024.5},{previousYear:'2023'},{unitPricesVerified:false},{totalAmount:14300}]) status('unitPrice',changes,'not-assessed');
for (const key of Object.keys(fixtures.unitPrice.matched)) status('unitPrice',{matched:{...fixtures.unitPrice.matched,[key]:false}},'not-assessed');
for (const key of ['claimDocumented','supplierIdentityVerified','comparableCompetitiveWinDocumented','sameMarket','sameServiceTerritory','relevantTime','comparableRightsContext']) status('exclusivity',{[key]:false},'not-assessed');
for (const changes of [{claim:'sole-source'},{competitiveOfferCount:1},{competitiveOfferCount:'2'},{competitiveOfferCount:2.5}]) status('exclusivity',changes,'not-assessed');
status('exclusivity',{claim:'no-competition'},'signal');
assert.match(result('exclusivity').reason,/does not refute/);
assert.equal(assess({indicators:fixtures},{weights:[1,2,3,4,5]}).experimentalSum,15);
for (const options of [{weights:[1]},{weights:[20,10,5,3,'1']},{weights:[20,10,5,3,-1]},{capNearFraction:0},{fullyPaidFraction:2},{maxCompletionFraction:-1},{realPriceJump:'0.3'},{unknown:true}]) assert.throws(()=>assess({},options),TypeError);
const partial = assess({indicators:{cap:{...fixtures.cap,cumulativeAmendments:0},execution:{applicability:'inapplicable'}}});
assert.equal(partial.experimentalSum,0);
assert.equal(partial.experimentalMaximum,40);
assert.equal(partial.assessedCount,1);
assert.equal(partial.notAssessedCount,3);
assert.equal(partial.notApplicableCount,1);
assert.equal(partial.assessedMaximum,8);
const zero = assess({indicators:{}});
assert.equal(zero.experimentalSum,null);
assert.equal(zero.experimentalMaximum,40);
assert.equal(zero.assessedCount,0);
assert.equal(zero.notAssessedCount,5);
assert.equal(zero.notApplicableCount,0);
assert.equal(zero.assessedMaximum,0);
const full = assess({indicators:fixtures});
assert.equal(full.assessedCount,5);
assert.equal(full.notAssessedCount,0);
assert.equal(full.notApplicableCount,0);
assert.equal(full.assessedMaximum,40);
// Relative tolerance: rounding noise is accepted on both cap boundaries,
// but materially different small thresholds must not inherit an absolute floor.
status('cap',{cumulativeAmendments:20 * (1 + Number.EPSILON)},'signal');
assert.equal(result('cap',{cumulativeAmendments:20 * (1 + Number.EPSILON)}).context.aboveCap,false);
status('cap',{cumulativeAmendments:20 * (1 + 1e-13)},'no-signal');
assert.equal(result('cap',{cumulativeAmendments:20 * (1 + 1e-13)}).context.aboveCap,true);
status('cap',{cumulativeAmendments:19 * (1 - Number.EPSILON)},'signal');
status('cap',{cumulativeAmendments:19 * (1 - 1e-13)},'no-signal');
status('cap',{cumulativeAmendments:0},'no-signal',{capNearFraction:1e-15});
status('execution',{physicalCompletion:1e-15},'no-signal',{maxCompletionFraction:0});
status('unitPrice',{currentUnitPrice:100,inflationFactor:1},'no-signal',{realPriceJump:1e-15});
for (const sourceRefs of [new Array(1), ['reference', ,]]) status('cap',{sourceRefs},'not-assessed');
for (const weights of [new Array(5), [20,10,5,3, ,]]) assert.throws(()=>assess({}, {weights}),TypeError);
const snapshotInput = structuredClone({indicators:fixtures});
const snapshot = assess(snapshotInput);
snapshotInput.indicators.cap.sourceRefs.push('later');
snapshotInput.indicators.unitPrice.matched.buyer = false;
assert.deepEqual(snapshot.indicators[0].evidence.sourceRefs,fixtures.cap.sourceRefs);
assert.equal(snapshot.indicators[3].evidence.matched.buyer,true);
snapshot.indicators[3].evidence.matched.supplier = false;
assert.equal(snapshotInput.indicators.unitPrice.matched.supplier,true);
for (const bad of [()=>{}, new Proxy({},{}), {get applicability() { throw new Error('bad evidence'); }}]) {
  const out = assess({indicators:{cap:bad,execution:fixtures.execution}});
  assert.equal(out.indicators[0].status,'not-assessed');
  assert.equal(out.indicators[1].status,'signal');
}
const cyclic = {...fixtures.cap}; cyclic.extra = cyclic;
assert.equal(assess({indicators:{cap:cyclic}}).indicators[0].status,'not-assessed');
status('unitPrice',{previousUnitPrice:1e-200,currentUnitPrice:1e200,inflationFactor:1e200},'signal');
assert.ok(Number.isFinite(result('unitPrice',{previousUnitPrice:1e-200,currentUnitPrice:1e200,inflationFactor:1e200}).context.realUnitPriceJump));
status('unitPrice',{previousUnitPrice:1e200,currentUnitPrice:1e-200,inflationFactor:1e-200},'no-signal');
status('unitPrice',{previousUnitPrice:Number.MIN_VALUE,currentUnitPrice:Number.MAX_VALUE,inflationFactor:1},'not-assessed');
const demo = assess(JSON.parse(require('node:fs').readFileSync(require('node:path').join(__dirname,'fixtures/experimental-indicators-positive.json'),'utf8')));
assert.equal(demo.experimentalSum,40);
assert.equal(demo.assessedCount,5);
// CLI round trip with temporary synthetic data only; no repository datasets.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const dir = fs.mkdtempSync(path.join(os.tmpdir(),'experimental-indicators-'));
try {
  const file = path.join(dir,'synthetic.json');
  const cli = path.resolve(__dirname,'../tools/experimental-indicators.cjs');
  for (const input of [{indicators:fixtures},[{indicators:fixtures},{indicators:{}}]]) {
    fs.writeFileSync(file,JSON.stringify(input));
    const child = spawnSync(process.execPath,[cli,file],{encoding:'utf8'});
    assert.equal(child.status,0,child.stderr);
    const out = JSON.parse(child.stdout);
    assert.deepEqual(out,Array.isArray(input)?input.map(x=>assess(x)):assess(input));
  }
  fs.writeFileSync(file,'invalid json');
  assert.equal(spawnSync(process.execPath,[cli,file]).status,1);
} finally { fs.rmSync(dir,{recursive:true,force:true}); }
console.log('Experimental indicator synthetic tests passed.');
