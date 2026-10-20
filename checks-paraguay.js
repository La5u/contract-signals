// Paraguay (DNCP) check set (docs/score-paraguay.md).
'use strict';

// ------------------------------------------------------------------
// DNCP (Paraguay) — jurisdiction-specific check set, method
// docs/score-paraguay.md. Same framework; French and Colombian
// thresholds are never applied to these rows.
// ------------------------------------------------------------------
const PY_COMPETITIVE_METHODS = new Set(['open', 'selective', 'limited']);
// Contratación por Vía de la Excepción: the declared exception to a
// competitive procedure. Other direct modalities add no points.
const PY_EXCEPTION_PATTERN = /\bCVE\b|v[ií]a de la excepci[oó]n/i;
const PY_REPETITION_ENTRY = 3;
const PY_REPETITION_MAX = 10;
const PY_CONCENTRATION_GROUP_MIN = 10;
const PY_CONCENTRATION_COVERAGE = 0.8;
const PY_CONCENTRATION_ENTRY_SHARE = 0.6;
// Ley 7021/22 Art. 67 (docs/score-paraguay.md): modifications, unilateral or agreed, may not exceed jointly or
// separately 20 % of the amount and term originally agreed. Score 3.3 anchors the amount-increase check to this
// ceiling: 'at' = within PY_CEILING_NEAR_SHARE of it up to the ceiling (plus rounding tolerance), 'beyond' = above it.
// Applies to all processes launched from 19 Feb 2024 (DNCP: Ley 7021 and decree 9823/2023 applied to every process
// from that date; https://www.ultimahora.com/todas-las-licitaciones-publicas-seran-procesadas-bajo-la-ley-7021-22-desde-el-lunes).
// An earlier or missing call date is unknown: the process may still be under Ley 2051/03.
const PY_LEGAL_CEILING = 20;
const PY_CEILING_NEAR_SHARE = 0.95;
const PY_CEILING_TOLERANCE = 0.05;
const PY_LAW_7021_FROM = '2024-02-19';

function dncpMethodState(c) {
  if (PY_COMPETITIVE_METHODS.has(c.procurementMethod)) return 'competitive';
  if (c.procurementMethod === 'direct') return 'direct';
  return 'unknown';
}

function dncpException(c) {
  return dncpMethodState(c) === 'direct' && typeof c.procedure === 'string' && PY_EXCEPTION_PATTERN.test(c.procedure);
}

// Tenderer count usable only when the published count and tenderer list agree;
// with several lots, a total above one says nothing about each lot.
function dncpTenderers(c) {
  const n = c.numberOfTenderers;
  if (!Number.isInteger(n) || n < 1) return { status: 'unknown', reason: 'Number of tenderers not published for this process.' };
  if (c.tenderersListed != null && c.tenderersListed !== n) return { status: 'unknown', reason: `Published count (${n}) and tenderer list (${c.tenderersListed}) disagree: not assessed.` };
  if (c.lotCount > 1 && n > 1) return { status: 'unknown', reason: `${n} tenderers across ${c.lotCount} lots: the OCDS data publishes no per-lot count, so a single tenderer on this lot cannot be excluded. The bid comparison table or evaluation report linked under “Verify it yourself” lists offers per lot.` };
  return { status: 'known', count: n };
}

function dncpSingleTenderer(c) {
  const t = dncpTenderers(c);
  return dncpMethodState(c) === 'competitive' && t.status === 'known' && t.count === 1;
}

function dncpSupplierIdentity(c) {
  if (c.supplierIds?.length !== 1) return null;
  const id = c.supplierIds[0].id;
  return typeof id === 'string' && id.trim() ? id.trim() : null;
}

// Sum of published amount amendments relative to the original contract value.
// Amendments without an amount (term, scope) are not monetary and are skipped.
function dncpAmountIncrease(c) {
  if (!(c.amount > 0)) return { status: 'unknown', reason: 'Original declared amount missing or zero.' };
  if (!Array.isArray(c.amendments)) return { status: 'unknown', reason: 'Amendments were not captured for this row.' };
  const monetary = c.amendments.filter(a => a.amount != null);
  if (monetary.some(a => a.currency !== 'PYG' || typeof a.amount !== 'number')) return { status: 'unknown', reason: 'An amendment amount is not a PYG number: not assessed.' };
  const delta = monetary.reduce((sum, a) => sum + a.amount, 0);
  return { status: 'known', count: monetary.length, delta, percentage: delta / c.amount * 100 };
}

function dncpCeilingBand(percentage) {
  // Round away binary-float artefacts (0.57 / 3 = 18.999999999999996 %) before comparing bands.
  const p = Math.round(percentage * 1e6) / 1e6;
  if (p > PY_LEGAL_CEILING + PY_CEILING_TOLERANCE) return 'beyond';
  return p >= PY_LEGAL_CEILING * PY_CEILING_NEAR_SHARE ? 'at' : 'below';
}

// DNCP assessment: six Paraguayan checks plus two kept out of scope.
// Eight local checks (a ninth, universal transparency check is added by getAssessment).
function getAssessmentDncp(c) {
  const excludedReason = c.dataStatus === 'unverified' ? 'Unverified record: calculations excluded.' : null;
  const checks = [];
  function add(id, label, family, applicability, evaluable, triggered, weight, reason) {
    if (excludedReason) { applicability = 'unknown'; evaluable = false; reason = excludedReason; }
    const status = applicability === 'no' ? 'not-applicable' : applicability !== 'yes' || !evaluable ? 'unknown' : triggered ? 'signal' : 'clear';
    const severity = indicatorSeverity(weight || 0);
    checks.push({ id, label, family, applicability, status, weight: status === 'signal' ? weight : null,
      reason, explanation: reason, severity: severity.id, severityLabel: severity.label });
  }
  const method = dncpMethodState(c);
  const tenderers = dncpTenderers(c);
  const single = dncpSingleTenderer(c);
  const exception = dncpException(c);
  const supplierId = dncpSupplierIdentity(c);
  add('dncp-single-tenderer', 'Single tenderer in a competitive procedure', 'competition',
    method === 'competitive' ? 'yes' : method === 'direct' ? 'no' : 'unknown', tenderers.status === 'known', single, 12,
    method === 'direct' ? 'Direct modality: one tenderer is expected, not a signal.' :
    method === 'unknown' ? 'Procurement method not published or outside the known OCDS list: applicability not established.' :
    tenderers.status !== 'known' ? tenderers.reason :
    `${tenderers.count} tenderer(s) published for this ${c.procedure || 'competitive'} process (OCDS numberOfTenderers, matching the tenderer list). One tenderer: 12 points, all amounts. Admissibility of offers is not assessed; a small market may explain it.`);
  add('dncp-exception-award', 'Award by exception to competitive procedure (CVE)', 'competition',
    method === 'direct' ? 'yes' : method === 'competitive' ? 'no' : 'unknown', typeof c.procedure === 'string' && Boolean(c.procedure.trim()), exception, 18,
    method === 'competitive' ? 'Competitive procurement method published: exception rule out of scope.' :
    method === 'unknown' ? 'Procurement method not published: applicability not established.' :
    exception ? `Declared modality “${c.procedure}”: contracting by way of exception (Contratación por Vía de la Excepción). 18 points, all amounts. The published rationale is ${c.procurementMethodRationale ? `“${c.procurementMethodRationale}”` : 'absent'}; a lawful exception may apply and is not assessed here.` :
    `Direct modality “${c.procedure}” without a declared exception: ordinary direct contracting adds no points. Not a conclusion of regularity.`);
  const repeatedSingle = c.dncpRepeatedSingle;
  add('dncp-repeated-single-tenderer', 'Repeated single-tenderer awards to the same supplier', 'competition',
    single ? 'yes' : method === 'direct' || (tenderers.status === 'known' && tenderers.count > 1) ? 'no' : 'unknown',
    Boolean(repeatedSingle), Boolean(repeatedSingle && repeatedSingle.count >= PY_REPETITION_ENTRY),
    graduated(repeatedSingle?.count || 0, PY_REPETITION_ENTRY, PY_REPETITION_MAX, 12, EDITORIAL_MAX),
    !single && (method === 'direct' || (tenderers.status === 'known' && tenderers.count > 1)) ? 'This award is not a single-tenderer competitive award: outside the repetition scope.' :
    !single ? 'Single-tenderer status unknown: repetition not assessable.' :
    repeatedSingle ? `Same buyer and supplier ${supplierId}: ${repeatedSingle.count} distinct process(es) in this cohort won as the only tenderer. From 12 points at ${PY_REPETITION_ENTRY}, linear to 30 at ${PY_REPETITION_MAX}. Computed over the whole cohort before filters.` :
    'Supplier identifier missing: repetition not assessable.');
  const repeatedException = c.dncpRepeatedException;
  add('dncp-repeated-exception', 'Repeated exception awards to the same supplier', 'competition',
    exception ? 'yes' : method === 'unknown' ? 'unknown' : 'no', Boolean(repeatedException),
    Boolean(repeatedException && repeatedException.count >= PY_REPETITION_ENTRY),
    graduated(repeatedException?.count || 0, PY_REPETITION_ENTRY, PY_REPETITION_MAX, 18, EDITORIAL_MAX),
    !exception ? (method === 'unknown' ? 'Procurement method not published: applicability not established.' : 'This award is not declared by exception: outside the repetition scope.') :
    repeatedException ? `Same buyer and supplier ${supplierId}: ${repeatedException.count} distinct process(es) awarded by exception in this cohort. From 18 points at ${PY_REPETITION_ENTRY}, linear to 30 at ${PY_REPETITION_MAX}. Lawful grounds may apply to each.` :
    'Supplier identifier missing: repetition not assessable.');
  const concentration = c.dncpConcentration;
  add('dncp-concentration', 'Concentrated awards within a procurement category', 'competition',
    supplierId ? 'yes' : 'unknown', Boolean(concentration?.sufficient), Boolean(concentration && concentration.share >= PY_CONCENTRATION_ENTRY_SHARE),
    graduated(concentration?.share || 0, PY_CONCENTRATION_ENTRY_SHARE, 1, 12, EDITORIAL_MAX),
    concentration ? `Same buyer and category (${concentration.category || 'unspecified'}): ${concentration.wins}/${concentration.known} contracts to this supplier, out of ${concentration.total} in the group (${Math.round(concentration.coverage * 100)} % coverage). Minimum ${PY_CONCENTRATION_GROUP_MIN} identified contracts and ${Math.round(PY_CONCENTRATION_COVERAGE * 100)} % coverage; from 12 points at ${Math.round(PY_CONCENTRATION_ENTRY_SHARE * 100)} % to 30 at 100 %. ${concentration.sufficient ? '' : 'Insufficient sample or coverage: not assessed.'} Specialisation may explain a share.` :
    'Supplier identity unknown: applicability not established.');
  const increase = dncpAmountIncrease(c);
  const callDate = validIsoDate(c.callPublishedDate);
  const lawApplies = callDate ? callDate >= PY_LAW_7021_FROM : null;
  const band = increase.status === 'known' && increase.count ? dncpCeilingBand(increase.percentage) : null;
  const ceilingPoints = band === 'beyond' ? graduated(increase.percentage, PY_LEGAL_CEILING, 5 * PY_LEGAL_CEILING, 16, EDITORIAL_MAX) : 8;
  add('dncp-amount-increase', `Declared amount increase near or beyond the ${PY_LEGAL_CEILING} % legal ceiling`, 'execution',
    lawApplies === false ? 'no' : lawApplies === null ? 'unknown' : 'yes', increase.status === 'known' && lawApplies === true, band === 'at' || band === 'beyond',
    ceilingPoints,
    lawApplies === false ? `Process launched on ${callDate}, before Ley 7021/22 applied to every process (${PY_LAW_7021_FROM}): the Art. 67 ceiling is not applied. Out of scope.` :
    increase.status !== 'known' ? increase.reason :
    lawApplies === null ? 'Call publication date missing or invalid: whether Ley 7021/22 Art. 67 applies to this process cannot be determined. Not assessed.' :
    !increase.count ? 'No published amount amendment in the downloaded record. The absence of a published amendment does not prove the absence of a real change.' :
    band === 'beyond' ? `${increase.count} published amount amendment(s): +${increase.percentage.toFixed(2)} % of the original declared amount, above the ${PY_LEGAL_CEILING} % ceiling of Ley 7021/22 Art. 67 on modifications. 16 points just above the ceiling, linear to 30 at +100 %. DNCP rules allow a separate 20 % for unilateral public-interest changes (Art. 65 b), so a larger total is not by itself unlawful; a new procedure may also have been required. Declared, not paid.` :
    band === 'at' ? `${increase.count} published amount amendment(s): +${increase.percentage.toFixed(2)} % of the original declared amount, near or at the ${PY_LEGAL_CEILING} % ceiling of Ley 7021/22 Art. 67 on modifications (band from ${PY_LEGAL_CEILING * PY_CEILING_NEAR_SHARE} %). 8 points. Reaching the ceiling is lawful and leaves no further agreed increase; the term, also capped at 20 %, is not published.` :
    `${increase.count} published amount amendment(s): +${increase.percentage.toFixed(2)} % of the original declared amount, below ${PY_LEGAL_CEILING * PY_CEILING_NEAR_SHARE} % (the near-ceiling band of Ley 7021/22 Art. 67). Not a conclusion of regularity.`);
  add('short-bidding-period', 'Short bidding period', 'competition', 'no', false, false, null,
    `No validated Paraguayan minimum period per modality in this method: out of scope. Published tender period: ${c.tenderPeriodDays == null ? 'not published' : `${c.tenderPeriodDays} day(s)`}, shown as context only.`);
  add('long-contract', 'Long declared duration', 'execution', 'no', false, false, null,
    'No contract end date or duration is published in these records: duration out of scope.');
  const applicable = checks.filter(r => r.applicability === 'yes').length;
  const evaluated = checks.filter(r => r.status === 'signal' || r.status === 'clear').length;
  return { checks, applicable, evaluated, unknown: checks.filter(r => r.applicability === 'yes' && r.status === 'unknown').length,
    unknownApplicability: checks.filter(r => r.applicability === 'unknown').length,
    notApplicable: checks.filter(r => r.status === 'not-applicable').length,
    signals: checks.filter(r => r.status === 'signal').length, excludedReason };
}
