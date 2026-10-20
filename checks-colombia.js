// Colombia (SECOP II) check set (docs/score-colombia.md).
'use strict';

// ------------------------------------------------------------------
// SECOP II (Colombia pilot) — jurisdiction-specific check set.
// Framework v3.0 (families, maxima, null semantics) with Colombian
// eligibility and thresholds; method: docs/score-colombia.md.
// French thresholds are never applied to these rows.
// ------------------------------------------------------------------
const CO_COMPETITIVE_MODALITIES = new Set([
  'Licitación pública', 'Licitación pública Obra Publica',
  'Selección Abreviada de Menor Cuantía', 'Selección abreviada subasta inversa',
  'Concurso de méritos abierto', 'Seleccion Abreviada Menor Cuantia Sin Manifestacion Interes',
]);
const CO_DIRECT_MODALITIES = new Set([
  'Contratación directa', 'Contratación Directa (con ofertas)',
  'Contratación régimen especial', 'Contratación régimen especial (con ofertas)',
  'Mínima cuantía',
]);
// Published modality justifications that themselves declare competition
// avoidance (no plurality of suppliers / manifest urgency). Ordinary
// grounds — professional services, interadministrative agreements,
// minimum-amount rules, regime statutes — never enter this set.
const CO_AVOIDANCE_JUSTIFICATIONS = new Set([
  'No existe pluralidad de oferentes en el mercado',
  'Urgencia manifiesta',
]);
// Public-to-public context, outside the index (docs/score-colombia.md).
// SECOP II publishes no field for the counterparty's legal nature, so the
// positive evidence is always the buyer's declared justification; names are
// only used to withhold the label, never to grant it.
const CO_INTERADMIN_JUSTIFICATIONS = new Set([
  'Contratos o convenios Interadministrativos (con valor)',
  'Contratos o convenios Interadministrativos (valor cero)',
]);
const CO_PERSON_DOCUMENTS = new Set(['Cédula de Ciudadanía', 'Cédula de Extranjería']);
// Juntas de acción comunal are community bodies (Ley 2166 de 2021), not public entities.
const CO_COMMUNITY_NAME = /acci[oó]n\s+comunal|desarrollo\s+comunal|^\s*jac|^\s*junta\b/i;
const CO_LOAN_OF_USE_OR_CREDIT = new Set(['Comodato', 'Prestamo de uso', 'Operaciones de Crédito Público']);
const CO_DURATION_ENTRY_MONTHS = 36;
const CO_DURATION_MAX_MONTHS = 120;
const CO_EXTENSION_ENTRY = 1;
const CO_EXTENSION_MAX = 3;
const CO_REPETITION_ENTRY = 3;
const CO_REPETITION_MAX = 10;
const CO_CONCENTRATION_GROUP_MIN = 10;
const CO_CONCENTRATION_COVERAGE = 0.8;
const CO_CONCENTRATION_ENTRY_SHARE = 0.6;
// Points from labelled cases (v3.7, research/calibration/romania-colombia-results-2026-10-14.md): repeated
// awards without competition were rarer among convicted contracts (0 % vs 6 %); a token point is kept.
const CO_REPETITION_POINTS = 1;
// Buyer share (v3.7): a contract of at least 5 % of its buyer's contract total for its signing year; among
// contracts in Colombian corruption convictions LR 2.4, but at the same contract value, allowing convicted prices
// 30 % overpricing, only LR 1.64 (25th percentile 1.39): 4.7 points since v3.8
// (research/calibration/colombia-buyer-share-size-results.json, fine value bands;
// 14 in v3.7, which measured contract size, favoured by prosecutions). Only 2025 is a complete
// signing year in the bundled cohort. The tested total merges SECOP I and II: SECOP I contracts signed in
// 2025 are not in this extract, so their declared total is added (datos.gov.co f789-7hwg, sum of
// cuantia_contrato, anno_firma_contrato 2025, queried 2026-10-15; x6v4-i8gf and Usaquén: none).
const CO_BUYER_SHARE = 0.05;
const CO_BUYER_SHARE_POINTS = 4.7;
const CO_COMPLETE_YEARS = { 'secop2-three-buyers-2024-2026': new Set(['2025']) };
const CO_SECOP1_TOTALS = { '899999001|2025': 77864151275, '890801052|2025': 37103760417 };

function secop2ModalityState(procedure) {
  if (typeof procedure !== 'string' || !procedure.trim()) return 'unknown';
  if (CO_COMPETITIVE_MODALITIES.has(procedure)) return 'competitive';
  if (CO_DIRECT_MODALITIES.has(procedure)) return 'direct';
  return 'unknown';
}

function secop2AvoidanceJustified(contract) {
  return CO_AVOIDANCE_JUSTIFICATIONS.has(contract.procedureJustification);
}

function secop2SupplierIdentity(contract) {
  if (contract.supplierIds?.length !== 1) return null;
  const { id, identifierType } = contract.supplierIds[0];
  if (typeof id !== 'string' || !id.trim() || /^(no definid[oa]|sin definir|n\/a|null|none)$/i.test(id.trim())) return null;
  return `${identifierType || 'Documento'}:${id.trim()}`;
}

// Read-only parse of the published free text duraci_n_del_contrato
// ("6 Mes(es)", "345 Dia(s)", "12 Semana(s)", "5 Año(s)"); the extract
// text itself is never rewritten. Hours and anything else stay null.
function secop2DurationMonths(text) {
  if (typeof text !== 'string' || !text.trim()) return null;
  let match = text.match(/^(\d+)\s*Mes/i);
  if (match) return Number(match[1]);
  match = text.match(/^(\d+)\s*Dia/i);
  if (match) return Math.round(Number(match[1]) / 30.4375 * 10) / 10;
  match = text.match(/^(\d+)\s*Semana/i);
  if (match) return Math.round(Number(match[1]) / 4.348 * 10) / 10;
  match = text.match(/^(\d+)\s*Año/i) || text.match(/^(\d+)\s*Ano/i);
  if (match) return Number(match[1]) * 12;
  return null;
}

// SECOP II assessment: six jurisdiction-specific checks plus the three
// French checks that stay out of scope here (no offers table, no
// publication–deadline chronology, no published amount additions).
// Nine local checks (a tenth, universal transparency check is added by getAssessment).
function getAssessmentSecop2(c) {
  const excludedReason = c.initialConflicts?.length || c.modificationConflicts?.length ? 'Conflicting versions: calculations excluded.' :
    c.identityAmbiguous ? 'Duplicate contract identifier: calculations excluded.' :
    c.dataStatus === 'unverified' ? 'Unverified record: calculations excluded.' : null;
  const checks = [];
  function add(id, label, family, applicability, evaluable, triggered, weight, reason) {
    if (excludedReason) { applicability = 'unknown'; evaluable = false; reason = excludedReason; }
    const status = applicability === 'no' ? 'not-applicable' : applicability !== 'yes' || !evaluable ? 'unknown' : triggered ? 'signal' : 'clear';
    const severity = indicatorSeverity(weight || 0);
    checks.push({ id, label, family, applicability, status, weight: status === 'signal' ? weight : null,
      reason, explanation: reason, severity: severity.id, severityLabel: severity.label });
  }
  const modality = secop2ModalityState(c.procedure);
  const justified = secop2AvoidanceJustified(c);
  add('secop2-plurality-award', 'Award declared without supplier plurality or under manifest urgency', 'competition',
    modality === 'competitive' ? 'no' : modality === 'direct' ? 'yes' : 'unknown',
    typeof c.procedureJustification === 'string' && Boolean(c.procedureJustification.trim()),
    justified, 18,
    modality === 'competitive' ? 'Explicitly competitive modality (licitación, selección abreviada, subasta, concurso): this award-without-plurality rule is out of scope.' :
    modality === 'unknown' ? 'Declared modality missing or outside the known SECOP II list: applicability not established.' :
    typeof c.procedureJustification !== 'string' || !c.procedureJustification.trim() ? 'Published justification of the modality missing: not assessable.' :
    justified ? `Non-competitive modality (${c.procedure}) with the published justification “${c.procedureJustification}”: the file itself declares an absent plurality of suppliers or manifest urgency. 18 points, all amounts. Ordinary grounds (professional services, interadministrative agreements, minimum-amount rules, regime statutes) add nothing; legality is not assessed here.` :
    `Non-competitive modality (${c.procedure}) with the published justification “${c.procedureJustification}”: an ordinary declared ground in this cohort, not a plurality/urgency claim. Threshold not crossed — not a conclusion of regularity.`);
  const repetition = c.secop2Repetition;
  const supplierIdentity = secop2SupplierIdentity(c);
  add('secop2-repeated-plurality', 'Repeated awards declared without supplier plurality', 'competition',
    justified ? 'yes' : 'no', Boolean(repetition),
    Boolean(repetition && repetition.count >= CO_REPETITION_ENTRY),
    CO_REPETITION_POINTS,
    !justified ? 'This contract is not among the awards declared without supplier plurality or under manifest urgency: outside the repetition scope.' :
    repetition ? `Same buyer and supplier document: ${repetition.count} award(s) of this cohort declared without supplier plurality. ${CO_REPETITION_POINTS} point from ${CO_REPETITION_ENTRY} contracts, lowered from 18–60 because among contracts in Colombian corruption convictions repeated awards without competition were rarer than among the same buyers' other contracts. Published declarations only; a lawful ground may still apply.` : 'No identified holder for a repetition computation.');
  const bs = c.coBuyerShare;
  add('secop2-buyer-share', 'Large share of the buyer’s yearly procurement', 'competition', 'yes', Boolean(bs?.complete && bs.share != null), bs?.share >= CO_BUYER_SHARE, CO_BUYER_SHARE_POINTS,
    !bs ? 'Buyer share not computed.' :
    !bs.complete ? `This cohort does not cover the buyer’s whole signing year ${bs.year || '(unknown)'}: share not assessable.` :
    bs.share == null ? 'Amount not in COP: not compared with the buyer’s COP total (no currency conversion).' :
    `${(bs.share * 100).toFixed(1)} % of this buyer’s COP contract total for ${bs.year} (${Math.round(bs.total).toLocaleString('en')} COP, contracts signed that year${bs.secop1 ? `, including ${Math.round(bs.secop1).toLocaleString('en')} COP declared in SECOP I` : ''}). ` +
    (bs.share >= CO_BUYER_SHARE ? `${CO_BUYER_SHARE_POINTS} points at 5 % or more, all modalities: among contracts in Colombian corruption convictions a contract this large relative to its buyer was about 2.4 times as frequent as among the same buyers’ other contracts, but at the same contract value only about 1.6 times: most of the difference is size, which prosecutions favour. Large purchases are often lawful; this check does not assess need or price.` : 'Below the 5 % threshold.'));
  const concentration = c.secop2Concentration;
  add('secop2-concentration', 'Concentrated awards within a contract type', 'competition',
    (c.supplierIds || []).length > 1 ? 'no' : supplierIdentity ? 'yes' : 'unknown',
    Boolean(concentration?.sufficient), Boolean(concentration && concentration.share >= CO_CONCENTRATION_ENTRY_SHARE),
    graduated(concentration?.share || 0, CO_CONCENTRATION_ENTRY_SHARE, 1, 12, EDITORIAL_MAX),
    concentration ? `Same buyer and contract type (${concentration.contractType || 'unspecified'}): ${concentration.wins}/${concentration.known} contracts to this holder, out of ${concentration.total} in the group (${Math.round(concentration.coverage * 100)} % coverage). Minimum ${CO_CONCENTRATION_GROUP_MIN} identified contracts and ${Math.round(CO_CONCENTRATION_COVERAGE * 100)} % coverage; from 12 points at ${Math.round(CO_CONCENTRATION_ENTRY_SHARE * 100)} % to 30 at 100 %. ${concentration.sufficient ? '' : 'Insufficient sample or coverage: not assessed.'} Specialisation may explain a share; computed over the whole cohort, before filters.` :
    supplierIdentity ? 'No eligible buyer/contract-type group for this holder: not assessed.' :
    (c.supplierIds || []).length > 1 ? 'Several declared holders: concentration of a single holder out of scope.' : 'Holder identity unknown: applicability not established.');
  const durationText = c.durationOriginal;
  const durationMonths = secop2DurationMonths(durationText);
  add('secop2-long-duration', `Long declared duration (≥ ${CO_DURATION_ENTRY_MONTHS} months)`, 'execution',
    typeof durationText === 'string' && durationText.trim() ? 'yes' : 'unknown',
    durationMonths != null, durationMonths != null && durationMonths >= CO_DURATION_ENTRY_MONTHS,
    graduated(durationMonths || 0, CO_DURATION_ENTRY_MONTHS, CO_DURATION_MAX_MONTHS, 8, 16),
    durationMonths == null ? (typeof durationText === 'string' && durationText.trim() ? `Declared duration “${durationText}” not comparable to months: not assessed.` : 'Declared duration field missing: applicability not established.') :
    durationMonths >= CO_DURATION_ENTRY_MONTHS ? `${durationMonths} months declared (parsed read-only from “${durationText}”). From ${CO_DURATION_ENTRY_MONTHS} months: 8 points, linear to 16 at ${CO_DURATION_MAX_MONTHS} months. Editorial threshold for this cohort, not a Colombian legal threshold; renewals are not invented.` :
    `${durationMonths} months declared (parsed read-only from “${durationText}”): below the ${CO_DURATION_ENTRY_MONTHS}-month entry threshold. Not a conclusion of regularity.`);
  add('single-bid', 'Single offer in a competitive procedure', 'competition', 'no', false, false, null,
    'No offers/proposals table in this SECOP II extract: the number of offers was never imported; out of scope.');
  add('short-bidding-period', 'Short bidding period', 'competition', 'no', false, false, null,
    'No publication–deadline chronology in this extract: bidding period out of scope.');
  // Term extension: published dias_adicionados against the original declared
  // term. The published end date is not always updated after an extension, so
  // it is not used. Amount additions are not published: out of scope.
  const extensionRatio = c.daysAdded != null && durationMonths > 0 ? c.daysAdded / (durationMonths * 30.4375) : null;
  add('secop2-term-extension', `Declared term more than doubled by extensions (> ${CO_EXTENSION_ENTRY * 100} %)`, 'execution',
    c.daysAdded != null && typeof durationText === 'string' && durationText.trim() ? 'yes' : 'unknown',
    extensionRatio != null, extensionRatio != null && extensionRatio > CO_EXTENSION_ENTRY,
    graduated(extensionRatio || 0, CO_EXTENSION_ENTRY, CO_EXTENSION_MAX, 8, EDITORIAL_MAX),
    c.daysAdded == null ? 'Days added (dias_adicionados) not published for this row: applicability not established.' :
    extensionRatio == null ? `${c.daysAdded} day(s) added, but the declared duration “${durationText || '—'}” is not comparable to days: not assessed.` :
    extensionRatio > CO_EXTENSION_ENTRY ? `${c.daysAdded} day(s) added to a declared term of ${durationMonths} months (+${Math.round(extensionRatio * 100)} %). Strictly above +${CO_EXTENSION_ENTRY * 100} %: 8 points, linear to 30 at +${CO_EXTENSION_MAX * 100} %. Editorial threshold; an extension can be lawful and necessary (weather, design changes, budget calendars). Amount additions are not published in this extract.` :
    `${c.daysAdded} day(s) added to a declared term of ${durationMonths} months (+${Math.round(extensionRatio * 100)} %): not above +${CO_EXTENSION_ENTRY * 100} %. Not a conclusion of regularity.`);
  add('repeated-single-bid', 'Repeated low competition', 'competition', 'no', false, false, null,
    'Depends on offer counts, absent from this extract: repetition of low competition out of scope.');
  const applicable = checks.filter(r => r.applicability === 'yes').length;
  const evaluated = checks.filter(r => r.status === 'signal' || r.status === 'clear').length;
  return { checks, applicable, evaluated, unknown: checks.filter(r => r.applicability === 'yes' && r.status === 'unknown').length,
    unknownApplicability: checks.filter(r => r.applicability === 'unknown').length,
    notApplicable: checks.filter(r => r.status === 'not-applicable').length,
    signals: checks.filter(r => r.status === 'signal').length, excludedReason };
}
