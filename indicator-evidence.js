(function () {
'use strict';
/**
 * LOCAL ONLY: normalized, externally verified evidence; this module does not
 * fetch data, establish legal applicability, or modify any production score.
 * assess({ indicators: { cap?, execution?, legalGround?, unitPrice?, exclusivity? } }, options?)
 * Each indicator has applicability: 'applicable' | 'inapplicable'. Inapplicable
 * evidence must contain only that field. All other fields below are required;
 * unknown fields, coercible values, and unsupported assertions are rejected.
 * Every applicable indicator requires sourceRefs: a nonempty array of nonempty
 * strings identifying its evidence; missing references leave it not-assessed.
 *
 * cap: legalCapConfirmed:true, baseVerified:true, amendmentsVerified:true,
 *   baseAmount>0, cumulativeAmendments>=0, capRate>0 (fraction of base),
 *   baseBasis/amendmentsBasis: identical nonempty strings identifying currency,
 *   tax and legally relevant valuation basis. cumulativeAmendments includes all
 *   relevant amendments on that basis, not merely the last amendment. Near-cap
 *   points apply only from the near threshold through 100% inclusive; above-cap
 *   evidence receives no near-cap points and is reported as separate context.
 * execution: paymentsVerified:true, completionIndependentlyDocumented:true,
 *   actualPayments>=0, advances>=0, refunds>=0, payableAmount>0,
 *   physicalCompletion: fraction [0,1], samePaymentBasis:true,
 *   paymentsAsOf/completionAsOf: equal real ISO YYYY-MM-DD snapshot dates.
 *   Differing snapshot dates leave execution not-assessed.
 *   actualPayments is gross verified payments; net = payments-advances-refunds.
 * legalGround: mappingReviewed:true, classificationVerified:true,
 *   jurisdiction/mappingJurisdiction, classification/mappingClassification,
 *   legalGround/mappingLegalGround: matching nonempty strings;
 *   date, validFrom, validTo: real ISO YYYY-MM-DD dates (inclusive validity);
 *   compatible:boolean from the explicitly reviewed jurisdictional mapping.
 * unitPrice: unitPricesVerified:true, previousYear/currentYear: consecutive
 *   integer years [1,9999], previousUnitPrice/currentUnitPrice>0,
 *   inflationFactor>0 (current-year price index / prior-year price index),
 *   matched:{buyer,supplier,item,specification,quantity,unit,currency,taxTerms,
 *     deliveryTerms}: all true, explicitly verified equality, not fuzzy matches.
 * exclusivity: claim:'exclusivity'|'no-competition', claimDocumented:true,
 *   supplierIdentityVerified:true, comparableCompetitiveWinDocumented:true,
 *   sameMarket:true, sameServiceTerritory:true, relevantTime:true,
 *   comparableRightsContext:true, competitiveOfferCount: integer >=2.
 *
 * options: weights (five finite nonnegative numbers), capNearFraction (0,1],
 * fullyPaidFraction (0,1], maxCompletionFraction [0,1], realPriceJump>=0.
 * Defaults: [8,8,8,8,8], .95, .99, .80, .30. The uniform 8 points is an
 * UNCALIBRATED PLACEHOLDER (the lowest entry weight of the graduated checks)
 * pending a reviewed public-evidence sample. Default maximum sum is 40;
 * custom weights change the reported maximum. Points are review context only.
 */
const IDS = ['cap', 'execution', 'legalGround', 'unitPrice', 'exclusivity'];
const CAVEAT = 'Verified evidence provides review context, not a corruption, risk, or legal conclusion. Standalone sums are experimental; website scoring uses family maxima.';
const object = x => x !== null && typeof x === 'object' && !Array.isArray(x);
const num = x => typeof x === 'number' && Number.isFinite(x);
const positive = x => num(x) && x > 0;
const nonnegative = x => num(x) && x >= 0;
const fraction = x => nonnegative(x) && x <= 1;
const text = x => typeof x === 'string' && x.trim().length > 0;
const exact = (x, keys) => object(x) && Object.keys(x).length === keys.length && keys.every(k => Object.hasOwn(x, k));
const fields = (x, keys) => exact(x, ['applicability', 'sourceRefs', ...keys]);
function date(x) {
  if (typeof x !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(x) || x.startsWith('0000')) return false;
  const d = new Date(x);
  return Number.isFinite(d.getTime()) && d.toISOString().slice(0, 10) === x;
}
const dense = (x, check) => Array.isArray(x) && Array.from({ length: x.length }, (_, i) => Object.hasOwn(x, i) && check(x[i])).every(Boolean);
function near(a, b) { return a >= b || Math.abs(a - b) <= 8 * Number.EPSILON * Math.max(Math.abs(a), Math.abs(b)); }
function evaluate(id, e, c) {
  if (id === 'cap') {
    if (!fields(e, ['legalCapConfirmed','baseVerified','amendmentsVerified','baseAmount','cumulativeAmendments','capRate','baseBasis','amendmentsBasis']) || e.legalCapConfirmed !== true || e.baseVerified !== true || e.amendmentsVerified !== true || !positive(e.baseAmount) || !nonnegative(e.cumulativeAmendments) || !positive(e.capRate) || !text(e.baseBasis) || e.baseBasis !== e.amendmentsBasis) return null;
    const ratio = e.cumulativeAmendments / (e.baseAmount * e.capRate);
    if (!Number.isFinite(ratio) || !positive(e.baseAmount * e.capRate)) return null;
    const aboveCap = !near(1, ratio);
    return [!aboveCap && near(ratio, c.capNearFraction), aboveCap ? 'Above confirmed cap: separate contextual review, not automatic illegality.' : 'Cumulative amendments compared with confirmed applicable cap.', { capUtilization: ratio, aboveCap }];
  }
  if (id === 'execution') {
    if (!fields(e, ['paymentsVerified','completionIndependentlyDocumented','actualPayments','advances','refunds','payableAmount','physicalCompletion','samePaymentBasis','paymentsAsOf','completionAsOf']) || !date(e.paymentsAsOf) || !date(e.completionAsOf) || e.paymentsAsOf !== e.completionAsOf || e.paymentsVerified !== true || e.completionIndependentlyDocumented !== true || e.samePaymentBasis !== true || ![e.actualPayments,e.advances,e.refunds].every(nonnegative) || !positive(e.payableAmount) || !fraction(e.physicalCompletion)) return null;
    const net = e.actualPayments - e.advances - e.refunds;
    const paid = net / e.payableAmount;
    if (!nonnegative(net) || !num(paid)) return null;
    return [near(paid, c.fullyPaidFraction) && near(c.maxCompletionFraction, e.physicalCompletion), 'Verified net payments compared with independently documented physical completion; dates are not a progress proxy.', { netPayments: net, paidFraction: paid }];
  }
  if (id === 'legalGround') {
    if (!fields(e, ['mappingReviewed','classificationVerified','jurisdiction','mappingJurisdiction','classification','mappingClassification','legalGround','mappingLegalGround','date','validFrom','validTo','compatible']) || e.mappingReviewed !== true || e.classificationVerified !== true || typeof e.compatible !== 'boolean' || !['jurisdiction','classification','legalGround'].every(k => text(e[k]) && e[k] === e['mapping' + k[0].toUpperCase() + k.slice(1)]) || ![e.date,e.validFrom,e.validTo].every(date) || e.validFrom > e.validTo || e.date < e.validFrom || e.date > e.validTo) return null;
    return [!e.compatible, 'Explicit reviewed applicability mapping for this jurisdiction, classification, legal ground and period.', {}];
  }
  if (id === 'unitPrice') {
    const keys = ['buyer','supplier','item','specification','quantity','unit','currency','taxTerms','deliveryTerms'];
    if (!fields(e, ['unitPricesVerified','previousYear','currentYear','previousUnitPrice','currentUnitPrice','inflationFactor','matched']) || e.unitPricesVerified !== true || ![e.previousYear,e.currentYear].every(y => Number.isInteger(y) && y >= 1 && y <= 9999) || e.currentYear !== e.previousYear + 1 || ![e.previousUnitPrice,e.currentUnitPrice,e.inflationFactor].every(positive) || !exact(e.matched, keys) || !keys.every(k => e.matched[k] === true)) return null;
    let ratio = (e.currentUnitPrice / e.previousUnitPrice) / e.inflationFactor;
    if (!Number.isFinite(ratio) || ratio === 0) {
      ratio = Math.exp(Math.log(e.currentUnitPrice) - Math.log(e.previousUnitPrice) - Math.log(e.inflationFactor));
    }
    const jump = ratio - 1;
    if (!num(jump)) return null;
    return [near(jump, c.realPriceJump), 'Matched consecutive-year actual unit prices, adjusted for inflation.', { realUnitPriceJump: jump }];
  }
  if (!fields(e, ['claim','claimDocumented','supplierIdentityVerified','comparableCompetitiveWinDocumented','sameMarket','sameServiceTerritory','relevantTime','comparableRightsContext','competitiveOfferCount']) || !['exclusivity','no-competition'].includes(e.claim) || !['claimDocumented','supplierIdentityVerified','comparableCompetitiveWinDocumented','sameMarket','sameServiceTerritory','relevantTime','comparableRightsContext'].every(k => e[k] === true) || !Number.isInteger(e.competitiveOfferCount) || e.competitiveOfferCount < 2) return null;
  return [true, 'Context-only review of documented comparable competitive wins; this does not refute the claim.', {}];
}
function assess(input, options = {}) {
  const defaults = { weights: [8,8,8,8,8], capNearFraction: .95, fullyPaidFraction: .99, maxCompletionFraction: .8, realPriceJump: .3 };
  if (!object(options) || Object.keys(options).some(k => !Object.hasOwn(defaults,k))) throw new TypeError('Unsupported options');
  const c = { ...defaults, ...options };
  if (!Array.isArray(c.weights) || c.weights.length !== 5 || !dense(c.weights, nonnegative) || !num(c.weights.reduce((a,b) => a+b,0)) || !positive(c.capNearFraction) || c.capNearFraction > 1 || !positive(c.fullyPaidFraction) || c.fullyPaidFraction > 1 || !fraction(c.maxCompletionFraction) || !nonnegative(c.realPriceJump)) throw new TypeError('Invalid weights or thresholds');
  let validInput = false;
  try { validInput = exact(input, ['indicators']) && object(input.indicators) && Object.keys(input.indicators).every(k => IDS.includes(k)); } catch { /* Malformed input remains unknown. */ }
  const results = IDS.map((id, i) => {
    // Snapshot each indicator independently; uncloneable evidence stays unknown.
    let e = null;
    try { if (validInput && Object.hasOwn(input.indicators,id)) e = structuredClone(input.indicators[id]); } catch { /* Unsupported values or throwing accessors. */ }
    const base = { id, weight: c.weights[i], status: 'not-assessed', points: null, reason: 'Missing, unsupported, malformed or conflicting evidence.', evidence: e };
    if (!object(e)) return base;
    if (exact(e, ['applicability']) && e.applicability === 'inapplicable') return { ...base, status: 'not-applicable', reason: 'Explicitly inapplicable.' };
    if (e.applicability !== 'applicable' || !Array.isArray(e.sourceRefs) || e.sourceRefs.length === 0 || !dense(e.sourceRefs, text)) return base;
    const result = evaluate(id,e,c);
    if (!result) return base;
    return { ...base, status: result[0] ? 'signal' : 'no-signal', points: result[0] ? c.weights[i] : 0, reason: result[1], evidence: e, context: result[2] };
  });
  const assessed = results.filter(r => r.status === 'signal' || r.status === 'no-signal');
  return { caveat: CAVEAT, indicators: results, experimentalSum: assessed.length ? assessed.reduce((n,r) => n+r.points,0) : null, experimentalMaximum: c.weights.reduce((a,b) => a+b,0), assessedCount: assessed.length, notAssessedCount: results.filter(r => r.status === 'not-assessed').length, notApplicableCount: results.filter(r => r.status === 'not-applicable').length, assessedMaximum: assessed.reduce((n,r) => n+r.weight,0) };
}

const api = { assess };
if (typeof module !== 'undefined' && module.exports) module.exports = api;
if (typeof globalThis !== 'undefined') globalThis.IndicatorEvidence = api;
})();
