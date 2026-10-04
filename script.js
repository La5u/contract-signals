'use strict';

const HISTORY_COHORT = 'decp-paris-ardeche-2024-2025';
const CITIES_COHORT = 'decp-six-cities-2024-2025';
const HISTORY_COHORTS = new Set([HISTORY_COHORT, CITIES_COHORT]);
function isAmbiguousCityContract(c) {
  return c.cohortId === CITIES_COHORT && Boolean(c.initialConflicts?.length || c.modificationConflicts?.length);
}
const HISTORY_START = '2024-01-01';
const HISTORY_END = '2025-12-31';

const SCORE_VERSION = '3.3';

// Conservative calendar-day upper bound: publication time is not supplied by BOAMP.
function getBiddingPeriod(contract) {
  const unavailable = reason => ({ status: 'unavailable', reason });
  const c = contract.consultation;
  if (!c) return unavailable('Initial notice and timetable not imported.');
  if (!c.searchComplete) return unavailable('Completeness of versions not demonstrated; no bidding-period calculation.');
  if (!c.procedureId || !c.lotId) return unavailable('Missing procedure or lot identifier.');
  if (c.exclusions?.length) return unavailable('Timeline excluded: ' + c.exclusions.join(' '));
  const notices = c.notices;    if (!Array.isArray(notices) || notices.filter(n => n.kind === 'initial').length !== 1) return unavailable('Ambiguous initial notice.');
  const initial = notices.find(n => n.kind === 'initial');
  if (initial.id !== c.initialNoticeId) return unavailable('Incompatible initial reference.');
  const ordered = [...notices].sort((a, b) => (a.publicationDate || '').localeCompare(b.publicationDate || ''));
  const seen = new Set();
  for (const n of ordered) {
    if (!['initial', 'correction'].includes(n.kind) || seen.has(n.id) || !safeSource(n.source) || !n.version ||
        !/^\d{4}-\d{2}-\d{2}$/.test(n.publicationDate || '') || !Number.isFinite(Date.parse(n.publicationDate)) ||
        new Date(n.publicationDate).toISOString().slice(0, 10) !== n.publicationDate) return unavailable('Ambiguous version, source or publication.');
    if (n.kind === 'correction' && (!(n.previousNoticeIds || []).some(id => seen.has(id)) || n.publicationDate <= initial.publicationDate)) return unavailable('Unlinked correction or ambiguous order.');
    if (n.procedureType !== 'open' || n.accelerated !== false) return unavailable('Procedure other than explicitly open non-accelerated, or unknown acceleration.');
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$/.test(n.deadline || '') || !Number.isFinite(Date.parse(n.deadline))) return unavailable('Unknown deadline or time zone; the previous deadline must not be silently carried over.');
    const deadlineDay = n.deadline.slice(0, 10);
    if (new Date(deadlineDay).toISOString().slice(0, 10) !== deadlineDay) return unavailable('Invalid deadline.');
    if (Date.parse(n.deadline) <= Date.parse(n.publicationDate)) return unavailable('Deadline earlier than publication.');
    seen.add(n.id);
  }
  if (ordered[0] !== initial || new Set(ordered.map(n => n.publicationDate)).size !== ordered.length) return unavailable('Ambiguous version order.');
  // A shortened deadline or correction after the previous deadline needs manual review.
  for (let i = 1; i < ordered.length; i++) {
    if (Date.parse(ordered[i].deadline) < Date.parse(ordered[i - 1].deadline) || Date.parse(ordered[i].publicationDate) > Date.parse(ordered[i - 1].deadline)) return unavailable('Shortened or reopened bidding period: manual review required.');
  }
  const latest = ordered[ordered.length - 1];
  const days = (Date.parse(latest.deadline) - Date.parse(initial.publicationDate + 'T00:00:00Z')) / 86400000;
  return { status: 'available', days, initialPublication: initial.publicationDate, deadline: latest.deadline, short: days < 15 };
}
const CPV_SECTORS = {
  '03': 'Agriculture and fisheries', '09': 'Energy and fuels', '14': 'Mining and minerals',
  '15': 'Food and beverages', '16': 'Agricultural machinery', '18': 'Clothing and equipment',
  '19': 'Leather and textiles', '22': 'Printed matter and publishing', '24': 'Chemical products',
  '30': 'Computer and office equipment', '31': 'Electrical equipment', '32': 'Telecommunications — equipment',
  '33': 'Medical equipment and pharmacy', '34': 'Vehicles and transport — equipment', '35': 'Security and defence — equipment',
  '37': 'Music, sport and leisure — equipment', '38': 'Measurement, laboratory and optics', '39': 'Furniture and miscellaneous equipment',
  '41': 'Collected and purified water', '42': 'Industrial machinery', '43': 'Construction and mining machinery',
  '44': 'Construction materials', '45': 'Construction work', '48': 'Software',
  '50': 'Repair and maintenance', '51': 'Installation', '55': 'Hotel and restaurant services',
  '60': 'Transport', '63': 'Transport — ancillary services', '64': 'Post and telecommunications',
  '65': 'Utility distribution services', '66': 'Finance and insurance', '70': 'Real estate',
  '71': 'Architecture, engineering and inspection', '72': 'IT services', '73': 'Research and development',
  '75': 'Administration, defence and social security', '76': 'Oil and gas services',
  '77': 'Agricultural and forestry services', '79': 'Consulting, communication and business services',
  '80': 'Education and training', '85': 'Health and social services', '90': 'Waste, sanitation and environment',
  '92': 'Culture, leisure and sport', '98': 'Other services'
};

function getSector(contract) {
  const code = /^\d{8}(?:-\d)?$/.test(contract.cpv || '') ? contract.cpv.slice(0, 2) : null;
  return code && CPV_SECTORS[code] ? { code, label: CPV_SECTORS[code] } : { code: 'unknown', label: 'Sector not specified' };
}

function getSupplierIdentity(contract) {
  const ids = [...new Set((contract.supplierIds || []).map(s => {
    if (s.identifierType === 'SIRET' && /^\d{14}$/.test(s.id)) return s.id.slice(0, 9);
    if (s.identifierType === 'SIREN' && /^\d{9}$/.test(s.id)) return s.id;
    return null;
  }).filter(Boolean))];
  return (contract.supplierIds || []).length === 1 && ids.length === 1 ? ids[0] : null;
}

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
function validIsoDate(value) {
  const d = typeof value === 'string' ? value.slice(0, 10) : '';
  return /^\d{4}-\d{2}-\d{2}$/.test(d) && !Number.isNaN(Date.parse(`${d}T00:00:00Z`)) && new Date(`${d}T00:00:00Z`).toISOString().slice(0, 10) === d ? d : null;
}

// France: maintenance, support or licences of an existing software product
// placed with one vendor. Context only, never points (docs/score-v3.md).
// Proprietary status and exclusive rights are not verified.
const FR_SOFTWARE_CPV = /^(48|7221|7225|7226)/;
const FR_SOFTWARE_TEXT = /progiciel|licences? logicielles?|maint\w*\s+(?:\S+\s+){0,3}(?:du|des|de la|de l’|de l')\s*logiciels?/i;
const FR_MAINTENANCE_TEXT = /\bmaint(?:enances?)?\b|\bsupport\b|\bassistance\b|mises? à jour|\bTMA\b|\bMCO\b|\blicences?\b|\babonnement|\bsouscription|droit de suivi/i;
function softwareMaintenanceContext(c) {
  if (c.dataFamily !== 'boamp' && c.dataFamily !== 'decp') return null;
  const cpv = String(c.cpv || '').replace(/\D/g, '');
  const text = typeof c.description === 'string' ? c.description : '';
  const software = FR_SOFTWARE_CPV.test(cpv) ? 'cpv' : FR_SOFTWARE_TEXT.test(text) ? 'text' : null;
  if (!software || !(/^72267/.test(cpv) || FR_MAINTENANCE_TEXT.test(text))) return null;
  const vendor = c.directAward === true ? 'direct'
    : getLegalContext(c).some(item => item.article === 'R2122-3') ? 'R2122-3'
    : c.directAward == null && c.offers === 1 ? 'one-offer' : null;
  return vendor ? { software, vendor } : null;
}

// Routine-context labels shown next to the signals; never read by scoring.
function contextLabels(c) {
  const labels = [];
  if (softwareMaintenanceContext(c)) labels.push({ id: 'fr-software', short: 'single-vendor software maintenance', long: 'Maintenance, support or licences of an existing software product placed with one vendor (docs/score-v3.md).' });
  if (c.secop2PublicCounterparty?.labelled) labels.push({ id: 'co-public', short: 'public-to-public agreement', long: 'Agreement declared between public bodies (docs/score-colombia.md).' });
  return labels;
}

// One indicator catalogue for every country (docs/indicators.md). Each jurisdiction keeps
// its own check ids, eligibility and thresholds; every check maps to one universal kind,
// which is what the table, the filter and exports show.
const INDICATOR_KINDS = {
  'single-offer': 'Single offer in a competitive procedure',
  'direct-award': 'Award without competition',
  'repeated-single-offer': 'Repeated single-offer wins by the same supplier',
  'repeated-direct': 'Repeated awards without competition to the same supplier',
  'low-competition-rate': 'Buyer with repeated low competition',
  'concentration': 'Concentrated awards',
  'disqualified-better-bid': 'Better-ranked bidder disqualified',
  'short-bidding-period': 'Short bidding period',
  'late-notice-change': 'Late notice change without deadline extension',
  'long-duration': 'Long declared duration',
  'amount-increase': 'Amount increase after award',
  'term-extension': 'Term extended after award',
  'late-publication': 'Published long after the contract',
  'cap': 'Monetary modifications near applicable cap',
  'execution': 'Full payment with incomplete documented execution',
  'legalGround': 'Legal ground and purchase mismatch',
  'unitPrice': 'Year-over-year comparable unit-price increase',
  'exclusivity': 'Exclusivity claim and comparable competitive wins',
};
// Short names for the table chips; the full name is in the tooltip, the filter and the record panel.
const KIND_SHORT = {
  'single-offer': 'Single offer', 'direct-award': 'No competition', 'repeated-single-offer': 'Repeated single offer',
  'repeated-direct': 'Repeated no competition', 'low-competition-rate': 'Low competition rate', 'concentration': 'Concentration',
  'disqualified-better-bid': 'Better bid disqualified', 'short-bidding-period': 'Short bidding period',
  'late-notice-change': 'Late notice change', 'long-duration': 'Long duration', 'amount-increase': 'Amount increase',
  'term-extension': 'Term extended', 'late-publication': 'Late publication',
  'cap': 'Near applicable cap', 'execution': 'Payment / execution',
  'legalGround': 'Legal ground mismatch', 'unitPrice': 'Unit-price increase', 'exclusivity': 'Exclusivity context',
};
// Where a kind matches a red flag in a framework auditors already use (docs/indicators.md).
const KIND_REFERENCES = {
  'single-offer': 'OCP Cardinal R018 “Single bid received”; single bidding in the Fazekas Corruption Risk Index',
  'direct-award': 'non-open procedure / no call for tender published in the Fazekas Corruption Risk Index',
  'short-bidding-period': 'OCP Cardinal R003 “Short submission period”; advertisement period in the Fazekas Corruption Risk Index',
  'disqualified-better-bid': 'related to OCP Cardinal R036 “Lowest bid disqualified” and R035, and to Ukraine’s State Audit Service risk indicators sas-3-2 and sas-3-5',
  'repeated-direct': 'related to Ukraine’s State Audit Service risk indicator sas-3-3 (one supplier across many purchase codes)',
  'concentration': 'related to Ukraine’s State Audit Service risk indicator sas-3-3 and OCP Cardinal R048 “Heterogeneous supplier”',
};
const KIND_OF_CHECK = {
  cap: 'cap', execution: 'execution', legalGround: 'legalGround', unitPrice: 'unitPrice', exclusivity: 'exclusivity',
  'single-bid': 'single-offer', 'dncp-single-tenderer': 'single-offer',
  'direct-award': 'direct-award', 'secop2-plurality-award': 'direct-award', 'dncp-exception-award': 'direct-award',
  'repeated-direct-award': 'repeated-direct', 'secop2-repeated-plurality': 'repeated-direct', 'dncp-repeated-exception': 'repeated-direct',
  'dncp-repeated-single-tenderer': 'repeated-single-offer', 'repeated-single-bid': 'low-competition-rate',
  'supplier-concentration': 'concentration', 'secop2-concentration': 'concentration', 'dncp-concentration': 'concentration',
  'long-contract': 'long-duration', 'secop2-long-duration': 'long-duration',
  'amount-increase': 'amount-increase', 'dncp-amount-increase': 'amount-increase',
  'secop2-term-extension': 'term-extension', 'ua-better-bid-disqualified': 'disqualified-better-bid',
  'short-bidding-period': 'short-bidding-period', 'late-publication': 'late-publication', 'notice-late-change': 'late-notice-change',
};
function indicatorKind(id) {
  if (INDICATOR_KINDS[id] && !KIND_OF_CHECK[id]) return id;
  if (KIND_OF_CHECK[id]) return KIND_OF_CHECK[id];
  const national = /^(?:ua|ted|uk|cl)-(single-offer|direct-award|repeated-single-offer|repeated-direct|concentration)$/.exec(id || '');
  return national ? national[1] : null;
}

// Natural persons' national ID numbers are pseudonymised at import (tools/personal_ids.py).
function isMaskedId(id) { return typeof id === 'string' && id.startsWith('masked-'); }
function displayIdentifier(s) {
  const type = s.identifierType || 'Identifier';
  return isMaskedId(s.id) ? `${type} (a person's ID number, not republished here; pseudonym ${s.id.slice(7, 15)})` : `${type} ${s.id}`;
}

function indicatorSeverity(weight) {
  if (weight >= 40) return { id: 'extreme', label: 'Very high' };
  if (weight >= 25) return { id: 'high', label: 'High' };
  if (weight >= 12) return { id: 'moderate', label: 'Moderate' };
  return { id: 'low', label: 'Low' };
}
function hasIncompleteData(contract) {
  const a = getAssessment(contract);
  return Boolean(a.excludedReason) || a.unknown > 0 || a.unknownApplicability > 0;
}
function scoreLevel(score, incomplete = false) {
  if (score == null) return { id: 'unknown', label: 'Not assessed' };
  if (score === 0) return incomplete ? { id: 'unknown', label: 'Partial data' } : { id: 'none', label: 'No signal triggered' };
  if (score < 20) return { id: 'low', label: 'Low vigilance' };
  if (score < 40) return { id: 'moderate', label: 'Moderate vigilance' };
  if (score < 70) return { id: 'high', label: 'High vigilance' };
  return { id: 'extreme', label: 'Very high vigilance' };
}

// Explicit published citations only; never used by scoring or identity matching.
function getLegalContext(contract) {
  if (contract.dataFamily === 'audit' || !safeSource(contract.source)) return [];
  const citations = [];
  for (const field of ['description', 'procedure']) {
    const text = contract[field];
    if (typeof text !== 'string') continue;
    const pattern = /\bR[.\s–—-]*2122\s*[-–—]\s*(\d+)(?:\s*[-–—]?\s*\d+\s*°)?/gi;
    for (const match of text.matchAll(pattern)) {
      const article = `R2122-${match[1]}`;
      if (citations.some(c => c.article === article && c.field === field)) continue;
      citations.push({ article, citation: match[0], field, excerpt: text, source: contract.source,
        label: article === 'R2122-1' ? 'Imperative urgency — article cited' : article === 'R2122-3' ? 'Artistic, technical or exclusive-rights reasons — article cited' : 'Other cited R2122 basis' });
    }
  }
  return citations;
}

function graduated(value, start, end, low, high) {
  return Math.round((low + (high - low) * Math.min(1, Math.max(0, (value - start) / (end - start)))) * 10) / 10;
}

// French legal threshold below which a contract may be awarded without publicity or competition
// (Code de la commande publique, art. R2122-8): below it a direct award is the legal default, not a
// signal. Amounts are HT. The regime applies by the date the consultation is launched, which the
// data never gives, so the contract date is used and amounts that fall between the old and the new
// threshold during TRANSITION_DAYS after a change stay unknown. Sources (checked 2026-10-04):
//  - 25 000 EUR from 1 Oct 2015 (décret n° 2015-1163), 40 000 EUR from 1 Jan 2020 (décret n° 2019-1344)
//    https://www.marche-public.fr/Marches-publics/Definitions/Entrees/Seuil-dispense-publicite.htm
//  - works 70 000 EUR from 24 Jul 2020 (décret n° 2020-893, https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000042138128);
//    works 100 000 EUR by loi ASAP n° 2020-1525 art. 142 (published 8 Dec 2020), to 31 Dec 2022, extended to 31 Dec 2024
//    (décret n° 2022-1683) and to 31 Dec 2025 (décret n° 2024-1217)
//    https://www.marche-public.fr/contrats-publics/Decret-2024-1217-seuil-travaux-ECOM2434725D.htm
//  - décret n° 2025-1386 of 29 Dec 2025: works 100 000 EUR made permanent from 1 Jan 2026, supplies and services 60 000 EUR from 1 Apr 2026
//    https://blog.landot-avocats.net/2025/12/30/rehaussement-des-seuils-de-dispense-de-publicite-et-de-mise-en-concurrence-decryptage-du-decret-n-2025-1386-du-29-decembre-2025-modifiant-certains-seuils-relatifs-aux-marches-publics/
const FR_DIRECT_THRESHOLDS = {
  general: [['2015-10-01', 25000], ['2020-01-01', 40000], ['2026-04-01', 60000]],
  works: [['2015-10-01', 25000], ['2020-01-01', 40000], ['2020-07-24', 70000], ['2020-12-08', 100000]]
};
const FR_THRESHOLD_TRANSITION_DAYS = 180;
function frenchThresholdBand(series, date) {
  let i = -1;
  series.forEach(([from], k) => { if (date >= from) i = k; });
  if (i < 0) return null;
  const current = series[i][1];
  const recent = i > 0 && Date.parse(date) < Date.parse(series[i][0]) + FR_THRESHOLD_TRANSITION_DAYS * 864e5;
  return { current, previous: recent ? series[i - 1][1] : current };   // below previous: certain; from current: certain
}
function frenchDirectAwardEligibility(c) {
  const euros = n => `€${n.toLocaleString('en-GB')}`;
  if (!(c.amount > 0) || (c.currency && c.currency !== 'EUR')) return { status: 'unknown', reason: 'Declared amount missing: cannot tell whether the contract was below the legal threshold for an award without publicity or competition. Not assessed.' };
  if (!/^\d{4}-\d{2}-\d{2}$/.test(c.date || '')) return { status: 'unknown', reason: 'Contract date missing: the legal threshold in force cannot be determined. Not assessed.' };
  const works = typeof c.cpv === 'string' && /^\d/.test(c.cpv) ? c.cpv.startsWith('45') : null;
  const bands = [works !== false && frenchThresholdBand(FR_DIRECT_THRESHOLDS.works, c.date), works !== true && frenchThresholdBand(FR_DIRECT_THRESHOLDS.general, c.date)].filter(b => b !== false);
  if (bands.some(b => !b)) return { status: 'unknown', reason: `Contract date ${c.date} precedes the legal regimes encoded (October 2015). Not assessed.` };
  const sure = bands.map(b => c.amount < b.previous ? 'below' : c.amount >= b.current ? 'above' : 'unknown');
  const kind = works === true ? 'works' : works === false ? 'supplies and services' : 'works or supplies/services (CPV missing)';
  const limits = bands.map(b => euros(b.current)).join(' / ');
  if (sure.every(x => x === 'below')) return { status: 'below', reason: `Declared amount ${euros(c.amount)} HT is below the legal threshold of ${limits} HT in force on ${c.date} for ${kind} (art. R2122-8, décrets 2019-1344, 2022-1683, 2024-1217, 2025-1386): an award without publicity or competition is the legal default, not a signal.` };
  if (sure.every(x => x === 'above')) return { status: 'above', reason: `Declared amount ${euros(c.amount)} HT reaches the legal threshold of ${limits} HT in force on ${c.date} for ${kind}.` };
  return { status: 'unknown', reason: `Declared amount ${euros(c.amount)} HT: the threshold for ${kind} on ${c.date} is uncertain (${works === null ? 'CPV missing, works and supplies have different thresholds' : `within ${FR_THRESHOLD_TRANSITION_DAYS} days of a legal change, the consultation may have been launched under the previous threshold`}). Not assessed.` };
}

// Eight heuristic checks, with explicit applicability and evaluation states.
// Official findings and financial amounts are separate evidence/context, not points.
// Transparency family, the same for every country (docs/indicators.md): the award or
// contract data published more than 120 days after the contract date. 120 days exceeds
// every deadline of the regimes covered (EU award notices 30 days, or quarterly grouping
// plus 30 days for framework and DPS call-offs; UK 30 days; French essential data 2 months).
const LATE_PUBLICATION_DAYS = 120;
const LATE_PUBLICATION_MAX_DAYS = 730;
// Buyer-relative since score 3.2: a delay beyond LATE_PUBLICATION_DAYS only counts when it also
// exceeds the buyer's usual delay (median of its other dated records, same cohort) by more than
// that many days. Per-jurisdiction overrides go here, keyed by country code or dataFamily, e.g.
// { decp: { days: 150 } }; `excessDays` applies only where a buyer's usual delay is established.
const LATE_PUBLICATION_DEFAULTS = { days: LATE_PUBLICATION_DAYS, excessDays: LATE_PUBLICATION_DAYS, maxDays: LATE_PUBLICATION_MAX_DAYS, minBuyerRecords: 10 };
// DECP (score 3.3): the excess over the buyer's usual delay counts from 240 days. On the national
// DECP (210,018 competitive contracts, 8,702 buyers), single-bid odds first rise reliably from
// 241 days later than usual (OR 1.14, 95 % CI 1.01-1.29; 1.71 beyond 730 days), not from 120:
// research/thresholds/france-national.md.
const LATE_PUBLICATION_OVERRIDES = { decp: { excessDays: 240 } };
function latePublicationConfig(c) { return { ...LATE_PUBLICATION_DEFAULTS, ...(LATE_PUBLICATION_OVERRIDES[c.country] || LATE_PUBLICATION_OVERRIDES[c.dataFamily] || {}) }; }
const PUBLICATION_DATE_MEANING = { decp: 'essential data published on the buyer profile', boamp: 'BOAMP award notice', ted: 'TED award notice' };
const NO_RELIABLE_CONTRACT_DATE = { fts: 'Find a Tender award notices can carry the date of an original contract signed years earlier (modification notices under PCR 2015 Regulation 72) or of admission to a dynamic purchasing system: the delay would not measure late publication. Out of scope.' };
// Publication delay in days for a row the late-publication check can measure, else null.
// Excluded, aggregate and documentary rows never feed a buyer baseline.
function latePublicationDelay(c) {
  if (!PUBLICATION_DATE_MEANING[c.dataFamily] || c.assessmentMode === 'browse' || c.findingScope === 'aggregate' || (c.consultation && !c.contractId) || (c.noticeEvidence && !c.date) ||
      c.initialConflicts?.length || c.modificationConflicts?.length || c.identityAmbiguous || c.dataStatus === 'unverified' || !c.date || !c.publicationDate) return null;
  const days = Math.round((Date.parse(c.publicationDate) - Date.parse(c.date)) / 864e5);
  return Number.isFinite(days) && days >= 0 ? days : null;
}
// Leave-one-out median delay per buyer, over the whole cohort before any filter.
function assignPublicationBaselines(contracts) {
  const buyers = new Map();
  for (const c of contracts) {
    c.latePublicationBaseline = null;
    const delay = latePublicationDelay(c), buyer = c.buyerSiret || c.buyerId || c.buyer;
    if (delay == null || !buyer) continue;
    const key = `${c.dataFamily}|${buyer}`;
    if (!buyers.has(key)) buyers.set(key, []);
    buyers.get(key).push({ c, delay });
  }
  for (const rows of buyers.values()) {
    if (rows.length < latePublicationConfig(rows[0].c).minBuyerRecords) continue;
    const sorted = rows.map(r => r.delay).sort((x, y) => x - y), m = sorted.length - 1;
    for (const { c, delay } of rows) {
      const p = sorted.indexOf(delay);   // any position holding this value gives the same remaining multiset
      const at = i => sorted[i < p ? i : i + 1];
      const median = m % 2 ? (at((m - 1) / 2) + at((m + 1) / 2)) / 2 : at(m / 2);
      c.latePublicationBaseline = { median, others: m };
    }
  }
}
function latePublicationCheck(c, excludedReason) {
  const meaning = PUBLICATION_DATE_MEANING[c.dataFamily];
  const cfg = latePublicationConfig(c);
  const base = { id: 'late-publication', label: 'Published late, beyond the legal deadlines and this buyer’s usual delay', family: 'transparency' };
  const make = (applicability, status, weight, reason) => {
    const severity = indicatorSeverity(weight || 0);
    return { ...base, applicability, status, weight: status === 'signal' ? weight : null, reason, explanation: reason, severity: severity.id, severityLabel: severity.label };
  };
  if (excludedReason) return make('unknown', 'unknown', null, excludedReason);
  if (!meaning) return make('no', 'not-applicable', null, NO_RELIABLE_CONTRACT_DATE[c.dataFamily] || 'This source publishes no publication date to compare with the contract date: out of scope.');
  if (c.findingScope === 'aggregate' || (c.consultation && !c.contractId) || c.noticeEvidence && !c.date) return make('no', 'not-applicable', null, 'Not an individual awarded contract with a contract date.');
  if (!c.date || !c.publicationDate) return make('yes', 'unknown', null, 'Contract date or publication date missing: delay not assessable.');
  const days = Math.round((Date.parse(c.publicationDate) - Date.parse(c.date)) / 864e5);
  if (!Number.isFinite(days)) return make('yes', 'unknown', null, 'Unreadable date: delay not assessable.');
  if (days < 0) return make('yes', 'unknown', null, `Publication date (${c.publicationDate}) before the contract date (${c.date}): inconsistent dates, not assessed.`);
  const dates = `between the contract date (${c.date}) and the ${meaning} (${c.publicationDate})`;
  if (days <= cfg.days) return make('yes', 'clear', null, `${days} day(s) ${dates}: within ${cfg.days} days. Not a conclusion of regularity.`);
  const usual = c.latePublicationBaseline;
  const baseline = usual ? usual.median : 0;
  const excess = days - baseline;
  // Without an established usual delay the whole delay counts against the legal threshold.
  const excessDays = usual ? cfg.excessDays : cfg.days;
  if (excess <= excessDays) return make('yes', 'clear', null, `${days} days ${dates}, beyond the legal deadlines but within this buyer’s usual delay (median ${baseline} days over ${usual.others} other records): a buyer-level publication practice, not specific to this contract. Not a conclusion of regularity.`);
  const weight = graduated(excess, excessDays, cfg.maxDays, 8, 16);
  const practice = usual ? `Its buyer’s usual delay is ${baseline} days (median of ${usual.others} other records), so it is ${excess} days later than usual.` : `No usual delay is established for this buyer (fewer than ${cfg.minBuyerRecords} dated records in this dataset), so the whole delay counts.`;
  return make('yes', 'signal', weight, `${days} days ${dates}, beyond the legal deadlines. ${practice} Signal above ${cfg.days} days of delay and ${excessDays} days later than usual: 8 points, linear to 16 at ${cfg.maxDays} days later than usual, in the transparency family. Late publication hides a contract from scrutiny while it runs; it can also be a clerical delay.`);
}

// The explorer turns this on once records are prepared: they no longer change, so each
// record's checks are computed once instead of on every filter, sort and redraw.
let assessmentCache = null;
function getAssessment(c) {
  if (!assessmentCache) return computeAssessment(c);
  let cached = assessmentCache.get(c);
  if (!cached) { cached = computeAssessment(c); assessmentCache.set(c, cached); }
  return cached;
}
// Listed only for the checks a record carries evidence for: no bundled dataset maps any yet,
// and five permanent "not assessed" lines on every row would say nothing.
function getAdditionalIndicatorChecks(c, excludedReason) {
  const evidence = c.indicatorEvidence && typeof c.indicatorEvidence === 'object' ? c.indicatorEvidence : {};
  const ids = ['cap', 'execution', 'legalGround', 'unitPrice', 'exclusivity'].filter(id => Object.hasOwn(evidence, id));
  if (!ids.length) return [];
  excludedReason = excludedReason || (c.assessmentMode === 'browse' ? 'Browse-only import: scoring eligibility not established.' :
    c.initialConflicts?.length || c.modificationConflicts?.length ? 'Conflicting versions: calculations excluded.' :
    c.identityAmbiguous ? 'Duplicate contract identifier: calculations excluded.' :
    c.dataStatus === 'unverified' ? 'Unverified record: calculations excluded.' : null);
  const blocked = excludedReason || (c.findingScope === 'aggregate' ? 'Aggregate dossier: not a comparable individual award.' :
    c.consultation && !c.contractId || c.noticeEvidence && !c.date ? 'Documentary notice, not a normalized attributed contract.' : null);
  let results = [];
  if (!blocked && globalThis.IndicatorEvidence?.assess) {
    try { results = globalThis.IndicatorEvidence.assess({ indicators: c.indicatorEvidence || {} }).indicators; }
    catch { /* Unsupported evidence remains unknown. */ }
  }
  return ids.map(id => {
    const r = results.find(r => r.id === id);
    const applicability = blocked ? excludedReason ? 'unknown' : 'no' : !r || r.status === 'not-assessed' ? 'unknown' : r.status === 'not-applicable' ? 'no' : 'yes';
    const status = applicability === 'no' ? 'not-applicable' : applicability === 'unknown' ? 'unknown' : r.status === 'signal' ? 'signal' : 'clear';
    const weight = status === 'signal' ? r.points : null;
    const severity = indicatorSeverity(weight || 0);
    const reason = blocked || r?.reason || 'Missing verified evidence or evidence engine: not assessed.';
    return { id, label: INDICATOR_KINDS[id], family: ['cap', 'execution', 'unitPrice'].includes(id) ? 'execution' : 'competition',
      applicability, status, weight, reason, explanation: reason, severity: severity.id, severityLabel: severity.label };
  });
}
function computeAssessment(c) {
  const browse = c.assessmentMode === 'browse';
  const base = browse ? { checks: [], excludedReason: 'Browse-only import: no jurisdiction or scoring eligibility has been established.' } : getAssessmentLocal(c);
  const checks = [...base.checks, ...(browse ? [] : [latePublicationCheck(c, base.excludedReason)]), ...getAdditionalIndicatorChecks(c, base.excludedReason)];
  return { ...base, checks,
    applicable: checks.filter(r => r.applicability === 'yes').length,
    evaluated: checks.filter(r => r.status === 'signal' || r.status === 'clear').length,
    unknown: checks.filter(r => r.applicability === 'yes' && r.status === 'unknown').length,
    unknownApplicability: checks.filter(r => r.applicability === 'unknown').length,
    notApplicable: checks.filter(r => r.status === 'not-applicable').length,
    signals: checks.filter(r => r.status === 'signal').length };
}

function getAssessmentLocal(c) {
  if (c.dataFamily === 'secop2') return getAssessmentSecop2(c);
  if (c.dataFamily === 'dncp') return getAssessmentDncp(c);
  if (NATIONAL_FAMILIES[c.dataFamily]) return getAssessmentNational(c);
  const excludedReason = c.initialConflicts?.length || c.modificationConflicts?.length ? 'Conflicting versions: calculations excluded.' :
    c.identityAmbiguous ? 'Duplicate contract identifier: calculations excluded.' :
    c.dataStatus === 'unverified' ? 'Unverified record: calculations excluded.' : null;
  const aggregate = c.findingScope === 'aggregate';
  const documentOnly = Boolean(c.consultation && !c.contractId);
  const checks = [];
  function add(id, label, family, applicability, evaluable, triggered, weight, reason) {
    if (aggregate) { applicability = 'no'; evaluable = false; reason = 'Aggregate dossier: not a comparable individual award.'; }
    if (documentOnly && !['short-bidding-period', 'notice-late-change'].includes(id)) { applicability = 'no'; evaluable = false; reason = 'Documentary notice, not a normalized attributed contract.'; }
    if (excludedReason) { applicability = 'unknown'; evaluable = false; reason = excludedReason; }
    const status = applicability === 'no' ? 'not-applicable' : applicability !== 'yes' || !evaluable ? 'unknown' : triggered ? 'signal' : 'clear';
    const severity = indicatorSeverity(weight || 0);
    checks.push({ id, label, family, applicability, status, weight: status === 'signal' ? weight : null,
      reason, explanation: reason, severity: severity.id, severityLabel: severity.label });
  }
  const competitive = c.directAward === false;
  const knownOffers = Number.isInteger(c.offers) && c.offers > 0;
  add('single-bid', 'Single offer in a competitive procedure', 'competition', c.directAward === true ? 'no' : competitive ? 'yes' : 'unknown', knownOffers, c.offers === 1, 12,
    !competitive ? 'An offer expected in a direct award adds nothing; competitive procedure not established if unknown.' : !knownOffers ? 'Positive number of offers unknown or unusable.' : `${c.offers} offer(s) declared, without presuming admissibility. One offer: 12 points, regardless of amount.`);
  const directEligibility = c.directAward === true ? frenchDirectAwardEligibility(c) : null;
  add('direct-award', 'Award without competition', 'competition',
    directEligibility?.status === 'below' ? 'no' : directEligibility?.status === 'unknown' ? 'unknown' : 'yes',
    typeof c.directAward === 'boolean' && directEligibility?.status !== 'unknown', c.directAward === true, 18,
    c.directAward == null ? 'Competitive character unknown.' : c.directAward === false ? 'Explicitly competitive procedure: no direct-award signal.' :
    directEligibility.status === 'above' ? `${directEligibility.reason} Award explicitly declared without competition: 18 points. May be legal (R2122 exceptions); no bonus for an R2122 citation.` : directEligibility.reason);
  add('long-contract', 'Declared duration ≥ 10 years', 'execution', 'yes', c.durationMonths != null, c.durationMonths >= 120,
    graduated(c.durationMonths || 0, 120, 360, 8, 16), c.durationMonths == null ? 'Declared duration unknown.' : `${c.durationMonths} months declared. From 120 months: 8 points, linear progression up to 16 at 360 months; renewals are not invented. Not a sectoral comparison nor an illegality threshold.`);
  const bidding = getBiddingPeriod(c);
  const initial = c.consultation?.notices?.find(n => n.kind === 'initial');
  const biddingApplicability = c.directAward === true || (initial?.procedureType && initial.procedureType !== 'open') || initial?.accelerated === true ? 'no' :
    bidding.status === 'available' || (initial?.procedureType === 'open' && initial.accelerated === false) ? 'yes' : 'unknown';
  add('short-bidding-period', 'Short bidding period', 'competition', biddingApplicability, bidding.status === 'available', bidding.short === true,
    graduated(15 - (bidding.days ?? 15), 0, 12, 8, 40), biddingApplicability === 'no' ? 'Rule reserved for explicitly open non-accelerated procedures; this record’s known type is out of scope.' : bidding.status === 'available' ? `${bidding.days.toFixed(2)} days, upper bound. Signal if < 15 days; 8 points near 15, 40 at 3 days or fewer. Editorial threshold, not a legal one.` : bidding.reason);
  const evolution = getAmountEvolution(c);
  const priceExcluded = c.priceType != null && c.priceType !== 'Définitif ferme';
  add('amount-increase', 'Relative increase in declared amount', 'execution', priceExcluded ? 'no' : c.priceType === 'Définitif ferme' ? 'yes' : 'unknown', evolution.status === 'available', evolution.percentage > 20,
    graduated(evolution.percentage || 0, 20, 100, 8, 40), evolution.status === 'available' ? `Declared increase of ${evolution.percentage.toFixed(2)} %. Signal strictly > 20 %, from 8 points near the threshold to 40 at +100 %. No euro threshold or bonus. Additional services possible: not a final expense nor a proven cost overrun.` : evolution.reason);
  const context = c.competitionContext;
  const oneOfferApplicability = c.directAward === true || (knownOffers && c.offers !== 1) ? 'no' : competitive && c.offers === 1 ? 'yes' : 'unknown';
  add('repeated-single-bid', 'Repeated low competition', 'competition', oneOfferApplicability, Boolean(context?.sufficient), context?.rate >= 0.6,
    graduated(context?.rate || 0, 0.6, 1, 12, 40), oneOfferApplicability === 'no' ? 'This contract is not a single-offer competitive award: outside the repeated-single-offer scope.' : context ? `${context.single}/${context.known} single offers, ${context.total} eligible contracts, CPV ${context.cpvGroup}, 2024–2025. Minimum 10 observations and 80 % coverage; from 12 points at 60 % to 40 points at 100 %. ${context.sufficient ? '' : 'Insufficient sample/coverage: not assessed.'}` : 'No eligible competitive context: no zero rate assumed.');
  const supplier = c.supplierContext;
  add('supplier-concentration', 'Concentrated awards', 'competition', (c.supplierIds || []).length > 1 ? 'no' : 'yes', Boolean(supplier?.sufficient), supplier?.share >= 0.6,
    graduated(supplier?.share || 0, 0.6, 1, 12, 40), supplier ? `Same SIREN: ${supplier.wins}/${supplier.known} contracts to the known holder, out of ${supplier.total} eligible; CPV ${supplier.cpvGroup}, 2024–2025. Minimum 10 and 80 % coverage. From 12 points at 60 % to 40 at 100 %. Specialisation and framework agreements may explain this share. ${supplier.sufficient ? '' : 'Insufficient sample/coverage.'}` : 'Single holder or insufficient/unknown cohort context; no name-based matching.');
  if (c.cohortId === 'tours-full-notices-2025') {
    const change = c.noticeChange;
    add('notice-late-change', 'Late notice change without deadline extension', 'competition', change?.status === 'not-applicable' ? 'no' : 'yes',
      ['signal', 'clear'].includes(change?.status), change?.status === 'signal', 5,
      change?.reason || 'Linked correction evidence not imported.');
  }
  const directEnough = supplier?.directCount >= 3;
  const directKnown = supplier && supplier.directKnownCount === supplier.supplierContracts;
  add('repeated-direct-award', 'Repeated direct awards', 'competition', c.directAward === false ? 'no' : c.directAward === true ? 'yes' : 'unknown', Boolean(supplier && (directEnough || directKnown)), directEnough,
    graduated(supplier?.directCount || 0, 3, 10, 18, 60), c.directAward === false ? 'This contract is explicitly competitive: direct repetition out of scope.' : c.directAward == null ? 'Competitive character of this contract unknown: direct repetition not assessable.' : supplier ? `${supplier.directCount} direct awards identified, all amounts, same buyer/CPV/SIREN, 2024–2025. From 18 points at 3 contracts to 60 at 10. Unknown procedures do not become competitive. Legal exceptions possible.` : 'No history for an identified holder: repetition unknown.');
  const applicable = checks.filter(r => r.applicability === 'yes').length;
  const evaluated = checks.filter(r => r.status === 'signal' || r.status === 'clear').length;
  return { checks, applicable, evaluated, unknown: checks.filter(r => r.applicability === 'yes' && r.status === 'unknown').length,
    unknownApplicability: checks.filter(r => r.applicability === 'unknown').length,
    notApplicable: checks.filter(r => r.status === 'not-applicable').length,
    signals: checks.filter(r => r.status === 'signal').length, excludedReason };
}
// SECOP II assessment: five jurisdiction-specific checks plus the three
// French checks that stay out of scope here (no offers table, no
// publication–deadline chronology, no published amount additions).
// Eight local checks (a ninth, universal transparency check is added by getAssessment).
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
    graduated(repetition?.count || 0, CO_REPETITION_ENTRY, CO_REPETITION_MAX, 18, 60),
    !justified ? 'This contract is not among the awards declared without supplier plurality or under manifest urgency: outside the repetition scope.' :
    repetition ? `Same buyer and supplier document: ${repetition.count} award(s) of this cohort declared without supplier plurality. From 18 points at ${CO_REPETITION_ENTRY} contracts, linear to 60 at ${CO_REPETITION_MAX}. Published declarations only; a lawful ground may still apply.` : 'No identified holder for a repetition computation.');
  const concentration = c.secop2Concentration;
  add('secop2-concentration', 'Concentrated awards within a contract type', 'competition',
    (c.supplierIds || []).length > 1 ? 'no' : supplierIdentity ? 'yes' : 'unknown',
    Boolean(concentration?.sufficient), Boolean(concentration && concentration.share >= CO_CONCENTRATION_ENTRY_SHARE),
    graduated(concentration?.share || 0, CO_CONCENTRATION_ENTRY_SHARE, 1, 12, 40),
    concentration ? `Same buyer and contract type (${concentration.contractType || 'unspecified'}): ${concentration.wins}/${concentration.known} contracts to this holder, out of ${concentration.total} in the group (${Math.round(concentration.coverage * 100)} % coverage). Minimum ${CO_CONCENTRATION_GROUP_MIN} identified contracts and ${Math.round(CO_CONCENTRATION_COVERAGE * 100)} % coverage; from 12 points at ${Math.round(CO_CONCENTRATION_ENTRY_SHARE * 100)} % to 40 at 100 %. ${concentration.sufficient ? '' : 'Insufficient sample or coverage: not assessed.'} Specialisation may explain a share; computed over the whole cohort, before filters.` :
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
    graduated(extensionRatio || 0, CO_EXTENSION_ENTRY, CO_EXTENSION_MAX, 8, 40),
    c.daysAdded == null ? 'Days added (dias_adicionados) not published for this row: applicability not established.' :
    extensionRatio == null ? `${c.daysAdded} day(s) added, but the declared duration “${durationText || '—'}” is not comparable to days: not assessed.` :
    extensionRatio > CO_EXTENSION_ENTRY ? `${c.daysAdded} day(s) added to a declared term of ${durationMonths} months (+${Math.round(extensionRatio * 100)} %). Strictly above +${CO_EXTENSION_ENTRY * 100} %: 8 points, linear to 40 at +${CO_EXTENSION_MAX * 100} %. Editorial threshold; an extension can be lawful and necessary (weather, design changes, budget calendars). Amount additions are not published in this extract.` :
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
    graduated(repeatedSingle?.count || 0, PY_REPETITION_ENTRY, PY_REPETITION_MAX, 12, 40),
    !single && (method === 'direct' || (tenderers.status === 'known' && tenderers.count > 1)) ? 'This award is not a single-tenderer competitive award: outside the repetition scope.' :
    !single ? 'Single-tenderer status unknown: repetition not assessable.' :
    repeatedSingle ? `Same buyer and supplier ${supplierId}: ${repeatedSingle.count} distinct process(es) in this cohort won as the only tenderer. From 12 points at ${PY_REPETITION_ENTRY}, linear to 40 at ${PY_REPETITION_MAX}. Computed over the whole cohort before filters.` :
    'Supplier identifier missing: repetition not assessable.');
  const repeatedException = c.dncpRepeatedException;
  add('dncp-repeated-exception', 'Repeated exception awards to the same supplier', 'competition',
    exception ? 'yes' : method === 'unknown' ? 'unknown' : 'no', Boolean(repeatedException),
    Boolean(repeatedException && repeatedException.count >= PY_REPETITION_ENTRY),
    graduated(repeatedException?.count || 0, PY_REPETITION_ENTRY, PY_REPETITION_MAX, 18, 60),
    !exception ? (method === 'unknown' ? 'Procurement method not published: applicability not established.' : 'This award is not declared by exception: outside the repetition scope.') :
    repeatedException ? `Same buyer and supplier ${supplierId}: ${repeatedException.count} distinct process(es) awarded by exception in this cohort. From 18 points at ${PY_REPETITION_ENTRY}, linear to 60 at ${PY_REPETITION_MAX}. Lawful grounds may apply to each.` :
    'Supplier identifier missing: repetition not assessable.');
  const concentration = c.dncpConcentration;
  add('dncp-concentration', 'Concentrated awards within a procurement category', 'competition',
    supplierId ? 'yes' : 'unknown', Boolean(concentration?.sufficient), Boolean(concentration && concentration.share >= PY_CONCENTRATION_ENTRY_SHARE),
    graduated(concentration?.share || 0, PY_CONCENTRATION_ENTRY_SHARE, 1, 12, 40),
    concentration ? `Same buyer and category (${concentration.category || 'unspecified'}): ${concentration.wins}/${concentration.known} contracts to this supplier, out of ${concentration.total} in the group (${Math.round(concentration.coverage * 100)} % coverage). Minimum ${PY_CONCENTRATION_GROUP_MIN} identified contracts and ${Math.round(PY_CONCENTRATION_COVERAGE * 100)} % coverage; from 12 points at ${Math.round(PY_CONCENTRATION_ENTRY_SHARE * 100)} % to 40 at 100 %. ${concentration.sufficient ? '' : 'Insufficient sample or coverage: not assessed.'} Specialisation may explain a share.` :
    'Supplier identity unknown: applicability not established.');
  const increase = dncpAmountIncrease(c);
  const callDate = validIsoDate(c.callPublishedDate);
  const lawApplies = callDate ? callDate >= PY_LAW_7021_FROM : null;
  const band = increase.status === 'known' && increase.count ? dncpCeilingBand(increase.percentage) : null;
  const ceilingPoints = band === 'beyond' ? graduated(increase.percentage, PY_LEGAL_CEILING, 5 * PY_LEGAL_CEILING, 16, 40) : 8;
  add('dncp-amount-increase', `Declared amount increase at or beyond the ${PY_LEGAL_CEILING} % legal ceiling`, 'execution',
    lawApplies === false ? 'no' : lawApplies === null ? 'unknown' : 'yes', increase.status === 'known' && lawApplies === true, band === 'at' || band === 'beyond',
    ceilingPoints,
    lawApplies === false ? `Process launched on ${callDate}, before Ley 7021/22 applied to every process (${PY_LAW_7021_FROM}): the Art. 67 ceiling is not applied. Out of scope.` :
    increase.status !== 'known' ? increase.reason :
    lawApplies === null ? 'Call publication date missing or invalid: whether Ley 7021/22 Art. 67 applies to this process cannot be determined. Not assessed.' :
    !increase.count ? 'No published amount amendment in the downloaded record. The absence of a published amendment does not prove the absence of a real change.' :
    band === 'beyond' ? `${increase.count} published amount amendment(s): +${increase.percentage.toFixed(2)} % of the original declared amount, above the ${PY_LEGAL_CEILING} % ceiling of Ley 7021/22 Art. 67 on modifications. 16 points just above the ceiling, linear to 40 at +100 %. DNCP rules allow a separate 20 % for unilateral public-interest changes (Art. 65 b), so a larger total is not by itself unlawful; a new procedure may also have been required. Declared, not paid.` :
    band === 'at' ? `${increase.count} published amount amendment(s): +${increase.percentage.toFixed(2)} % of the original declared amount, at the ${PY_LEGAL_CEILING} % ceiling of Ley 7021/22 Art. 67 on modifications (from ${PY_LEGAL_CEILING * PY_CEILING_NEAR_SHARE} %). 8 points. Reaching the ceiling is lawful and leaves no further agreed increase; the term, also capped at 20 %, is not published.` :
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
// Ukraine (Prozorro) and Portugal/Romania (TED eForms): one engine, per-family
// labels and scope. Methods: docs/score-ukraine.md, docs/score-ted.md. Checks were
// fixed before these cohorts were downloaded; French thresholds are not applied.
const NATIONAL_FAMILIES = {
  prozorro: { prefix: 'ua', doc: 'docs/score-ukraine.md', category: c => c.category, notScored: new Set(['reporting']),
    directLabel: 'Negotiated procedure without competition', directReason: 'negotiation or negotiation.quick',
    outOfScope: { directKind: 'Offer and direct-award checks are excluded for direct-contract reports (reporting), which are recorded without a procedure. Concentration remains assessable where cohort data permits.',
      increase: 'Linked contract samples expose change metadata, not comparable dated amounts: increase out of scope.' } },
  ted: { prefix: 'ted', doc: 'docs/score-ted.md', notScored: new Set(), category: c => /^\d{8}/.test(c.cpv || '') ? c.cpv.slice(0, 2) : null,
    directLabel: 'Negotiated without prior publication', directReason: 'eForms procedure code neg-wo-call',
    outOfScope: { directKind: 'Procedure code outside the known competitive/direct list: not assessed.',
      increase: 'Contract modification notices are separate TED notices, not imported: increase out of scope.' } },
  fts: { prefix: 'uk', doc: 'docs/score-uk.md', notScored: new Set(), category: c => /^\d{8}/.test(c.cpv || '') ? c.cpv.slice(0, 2) : null,
    directLabel: 'Award without prior publication', directReason: 'OCDS procurementMethod limited',
    outOfScope: { directKind: 'Procurement method not published in this notice: not assessed.',
      increase: 'Contract change notices are separate Find a Tender notices, not imported: increase out of scope.' } },
  chile: { prefix: 'cl', doc: 'docs/score-chile.md', notScored: new Set(), category: c => c.category || null,
    directLabel: 'Direct deal (trato directo)', directReason: 'trato directo',
    directOutOfScope: 'This source lists licitaciones only: direct deals (trato directo) are published as purchase orders, not imported. Out of scope, not clear.',
    outOfScope: { directKind: 'Procedure name not published: not assessed.',
      increase: 'Contract modifications are not in this OCDS source: increase out of scope.' } },
};
function nationalSupplierIdentity(c) {
  // Find a Tender rows carry the platform party id, plus a Companies House number when published.
  const ids = c.dataFamily === 'fts' ? (c.supplierIds || []).filter(x => x.identifierType === 'GB-FTS') : c.supplierIds || [];
  if (ids.length !== 1) return null;
  const { id, identifierType } = ids[0];
  return ['EDRPOU', 'RNOKPP', 'NIF', 'CUI', 'ICO', 'GB-FTS', 'CL-RUT'].includes(identifierType) && typeof id === 'string' && id.trim() ? `${identifierType}:${id.trim()}` : null;
}
function nationalOffersKnown(c) { return Number.isInteger(c.offers) && c.offers > 0; }
function nationalSingle(c) { return c.procedureDirect === false && c.offers === 1; }
function getAssessmentNational(c) {
  const spec = NATIONAL_FAMILIES[c.dataFamily];
  const excludedReason = c.dataStatus === 'unverified' ? 'Unverified record: calculations excluded.' : null;
  const checks = [];
  function add(id, label, family, applicability, evaluable, triggered, weight, reason) {
    if (excludedReason) { applicability = 'unknown'; evaluable = false; reason = excludedReason; }
    const status = applicability === 'no' ? 'not-applicable' : applicability !== 'yes' || !evaluable ? 'unknown' : triggered ? 'signal' : 'clear';
    const severity = indicatorSeverity(weight || 0);
    checks.push({ id, label, family, applicability, status, weight: status === 'signal' ? weight : null, reason, explanation: reason, severity: severity.id, severityLabel: severity.label });
  }
  const p = spec.prefix, competitive = c.procedureDirect === false, direct = c.procedureDirect === true, supplier = nationalSupplierIdentity(c);
  // A known type the method deliberately does not score is out of scope, not unknown.
  const unknownKind = spec.notScored.has(c.procedure) ? 'no' : 'unknown';
  add(`${p}-single-offer`, 'Single offer in a competitive procedure', 'competition', competitive ? 'yes' : direct ? 'no' : unknownKind, nationalOffersKnown(c), c.offers === 1, 12,
    direct ? 'Procedure without competition: one offer is expected, not a signal.' : !competitive ? spec.outOfScope.directKind :
    !nationalOffersKnown(c) ? (c.offersNote || 'Number of offers for this lot not published.') : `${c.offers} offer(s) published for this lot (${c.procedure}). One offer: 12 points, all amounts. Admissibility is not assessed.`);
  add(`${p}-direct-award`, `Award without competition (${spec.directLabel})`, 'competition', spec.directOutOfScope ? 'no' : c.procedureDirect == null ? unknownKind : 'yes', c.procedureDirect != null, direct, 18,
    spec.directOutOfScope ? spec.directOutOfScope : c.procedureDirect == null ? spec.outOfScope.directKind : direct ? `${c.procedure} (${spec.directReason}): award without a competitive call. 18 points, all amounts. A lawful ground may apply (urgency, exclusivity, failed call); not assessed here.` : `Competitive procedure (${c.procedure}): no direct-award signal.`);
  const rs = c.nationalRepeatedSingle;
  add(`${p}-repeated-single-offer`, 'Repeated single-offer awards to the same supplier', 'competition', nationalSingle(c) ? 'yes' : competitive && nationalOffersKnown(c) || direct ? 'no' : unknownKind, Boolean(rs), rs?.count >= 3,
    graduated(rs?.count || 0, 3, 10, 12, 40), !nationalSingle(c) ? 'Not a single-offer competitive award: outside the repetition scope.' : rs ? `Same buyer and supplier ${supplier}: ${rs.count} distinct procedure(s) in this cohort won with a single offer. From 12 points at 3, linear to 40 at 10.` : 'Supplier identifier not usable (not a national registration number): repetition not assessable.');
  const rd = c.nationalRepeatedDirect;
  add(`${p}-repeated-direct`, 'Repeated awards without competition to the same supplier', 'competition', spec.directOutOfScope ? 'no' : direct ? 'yes' : c.procedureDirect == null ? unknownKind : 'no', Boolean(rd), rd?.count >= 3,
    graduated(rd?.count || 0, 3, 10, 18, 60), spec.directOutOfScope ? spec.directOutOfScope : !direct ? 'Not an award without competition: outside the repetition scope.' : rd ? `Same buyer and supplier ${supplier}: ${rd.count} distinct procedure(s) without competition in this cohort. From 18 points at 3, linear to 60 at 10. Lawful grounds may apply to each.` : 'Supplier identifier not usable: repetition not assessable.');
  const k = c.nationalConcentration;
  add(`${p}-concentration`, 'Concentrated awards within a category', 'competition', supplier ? 'yes' : 'unknown', Boolean(k?.sufficient), k?.share >= 0.6,
    graduated(k?.share || 0, 0.6, 1, 12, 40), k ? `Same buyer and category ${k.category}: ${k.wins}/${k.known} procedures won by this supplier, out of ${k.total} (${Math.round(k.coverage * 100)} % with an identified winner; lots of one procedure count once). Minimum 10 and 80 %; from 12 points at 60 % to 40 at 100 %. ${k.sufficient ? '' : 'Insufficient sample or coverage: not assessed.'}` : 'Supplier identity or category unknown: applicability not established.');
  add('amount-increase', 'Relative increase in declared amount', 'execution', 'no', false, false, null, spec.outOfScope.increase);
  if (c.dataFamily === 'prozorro') {
    // Prozorro creates awards in ranking order: an unsuccessful award before the
    // winning one means a better-ranked bid was set aside (docs/score-ukraine.md).
    const dq = c.disqualifiedBefore;
    add('ua-better-bid-disqualified', 'Better-ranked bidder disqualified before the award', 'competition', competitive ? 'yes' : direct ? 'no' : unknownKind, Number.isInteger(dq), dq > 0, 12,
      !competitive ? (direct ? 'Procedure without competition: no ranking of bids.' : spec.outOfScope.directKind) :
      !Number.isInteger(dq) ? 'Award history without dates: disqualifications not assessable.' :
      dq > 0 ? `${dq} better-ranked bidder(s) on this lot had their award declared unsuccessful before this award. 12 points, all amounts. Disqualification is often lawful (missing documents, non-compliant offer); read the award decisions linked on the Prozorro page.` :
      'No better-ranked bid set aside before this award on this lot.');
  } else add('short-bidding-period', 'Short bidding period', 'competition', 'no', false, false, null, 'No validated minimum period for this jurisdiction in this method: out of scope.');
  add('long-contract', 'Long declared duration', 'execution', 'no', false, false, null, 'No duration threshold validated for this jurisdiction: out of scope.');
  const applicable = checks.filter(r => r.applicability === 'yes').length;
  const evaluated = checks.filter(r => r.status === 'signal' || r.status === 'clear').length;
  return { checks, applicable, evaluated, unknown: checks.filter(r => r.applicability === 'yes' && r.status === 'unknown').length,
    unknownApplicability: checks.filter(r => r.applicability === 'unknown').length, notApplicable: checks.filter(r => r.status === 'not-applicable').length,
    signals: checks.filter(r => r.status === 'signal').length, excludedReason };
}
function hasAdjudicatedCorruption(contract) {
  return contract.corruptionOutcome?.status === 'final-adjudication';
}
function hasReportedInvestigation(contract) {
  return Array.isArray(contract.investigationReports) && contract.investigationReports.length > 0;
}
function getIndicators(contract) {
  return getAssessment(contract).checks.filter(r => r.status === 'signal').map(r => ({ ...r, kind: indicatorKind(r.id), kindLabel: INDICATOR_KINDS[indicatorKind(r.id)] || r.label }));
}
function getScoreBreakdown(contract) {
  const assessment = getAssessment(contract);
  const families = { competition: 0, execution: 0, transparency: 0 };
  for (const r of assessment.checks) if (r.status === 'signal') families[r.family] = Math.max(families[r.family], r.weight);
  const score = assessment.evaluated ? Math.round(Math.min(100, families.competition + families.execution + families.transparency) * 10) / 10 : null;
  return { ...families, score, assessment };
}
function getVigilanceScore(contract) { return getScoreBreakdown(contract).score; }

function getAmountEvolution(contract) {
  const unavailable = reason => ({ status: 'unavailable', reason });
  if (contract.dataFamily !== 'decp' || !Array.isArray(contract.history)) return unavailable('Published contract history not available for this record; increase check not applicable.');
  if (contract.identityAmbiguous) return unavailable('Duplicate identifier: calculation excluded.');
  if (!Array.isArray(contract.initialConflicts) || contract.initialConflicts.length) return unavailable('Diverging initial values: no increase calculation.');
  if (Array.isArray(contract.modificationConflicts) && contract.modificationConflicts.length) return unavailable('Diverging modification values for the same identifier: no increase calculation.');
  const initial = contract.history.find(event => event.kind === 'initial');
  const changes = contract.history.filter(event => event.kind === 'modification');
  if (!changes.length) return unavailable('No modification published in this extract; this does not prove the absence of an amendment.');
  if (!initial?.date || !(initial.amount > 0)) return unavailable('Initial amount or date unusable.');
  if (initial.amount !== contract.amount || initial.date !== contract.date) return unavailable('The initial state of the history does not match the contract fields.');
  if (changes.some(event => !event.date || event.date < initial.date)) return unavailable('Incomplete or inconsistent modification chronology.');
  const ordered = [...changes].sort((a, b) => b.date.localeCompare(a.date));
  const latest = ordered[0];
  if (ordered.some(event => event.date === latest.date && event.amount !== latest.amount)) return unavailable('Several different amounts on the same date.');
  if (latest.amount == null) return unavailable('The last published modification does not state an amount.');
  if (contract.priceType !== 'Définitif ferme') return unavailable('Price not declared exclusively fixed and firm (Définitif ferme): revision or update cannot be isolated, no automatic signal.');
  if (changes.some(event => event.supplierId && !contract.supplierIds?.some(supplier => supplier.id === event.supplierId))) return unavailable('Change of holder: scope requiring manual review.');
  if (latest.amount < initial.amount) return unavailable('Modified amount lower than the initial one: possible decrease or mis-entered increment. No increments are summed.');
  // Compare euro cents to avoid binary-float artefacts in the relative change; no absolute-euro scoring threshold.
  const initialCents = Math.round(initial.amount * 100);
  const revisedCents = Math.round(latest.amount * 100);
  if (!Number.isSafeInteger(initialCents) || !Number.isSafeInteger(revisedCents) || initialCents <= 0) return unavailable('Amounts beyond usable monetary precision.');
  const deltaCents = revisedCents - initialCents;
  return { status: 'available', initialAmount: initialCents / 100, revisedAmount: revisedCents / 100, delta: deltaCents / 100, percentage: deltaCents / initialCents * 100, date: latest.date };
}

// Retrospective context on the COMPLETE loaded cohort, never on filtered/page rows.
function prepareContracts(data) {
  const contracts = validateContracts(data).map(c => ({ ...c, competitionContext: null, supplierContext: null, identityAmbiguous: false, secop2Concentration: null, secop2Repetition: null, secop2PublicCounterparty: null, dncpConcentration: null, dncpRepeatedSingle: null, dncpRepeatedException: null, nationalConcentration: null, nationalRepeatedSingle: null, nationalRepeatedDirect: null }));
  const groups = new Map();
  const supplierGroups = new Map();
  const identityCounts = new Map();
  for (const c of contracts) {
    if (c.dataFamily !== 'decp' || !c.buyerSiret || !c.contractId) continue;
    const identity = `${c.buyerSiret}:${c.contractId}`;
    identityCounts.set(identity, (identityCounts.get(identity) || 0) + 1);
  }
  for (const c of contracts) c.identityAmbiguous = c.dataFamily === 'decp' && Boolean(c.buyerSiret && c.contractId && identityCounts.get(`${c.buyerSiret}:${c.contractId}`) > 1);
  assignPublicationBaselines(contracts);
  for (const c of contracts) {
    if (c.dataFamily !== 'decp' || !HISTORY_COHORTS.has(c.cohortId) || c.modificationConflicts?.length ||
        !c.buyerSiret || !c.contractId || identityCounts.get(`${c.buyerSiret}:${c.contractId}`) !== 1 ||
        !/^\d{8}-\d$/.test(c.cpv || '') || c.cpv.startsWith('000') || !c.date ||
        c.date < HISTORY_START || c.date > HISTORY_END || c.directAward !== false ||
        !Array.isArray(c.initialConflicts) || c.initialConflicts.length) continue;
    const key = `${c.cohortId}:${c.buyerSiret}:${c.cpv.slice(0, 3)}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(c);
  }
  for (const group of groups.values()) {
    const known = group.filter(c => Number.isInteger(c.offers) && c.offers > 0);
    const single = known.filter(c => c.offers === 1).length;
    const coverage = known.length / group.length;
    const rate = known.length ? single / known.length : null;
    const context = { total: group.length, known: known.length, single, coverage, rate,
      cpvGroup: group[0].cpv.slice(0, 3), start: HISTORY_START, end: HISTORY_END,
      sufficient: known.length >= 10 && coverage >= 0.8 };
    group.forEach(c => { c.competitionContext = context; });
  }
  for (const c of contracts) {
    if (c.dataFamily !== 'decp' || !HISTORY_COHORTS.has(c.cohortId) || c.modificationConflicts?.length || !c.buyerSiret || !c.contractId ||
        identityCounts.get(`${c.buyerSiret}:${c.contractId}`) !== 1 || !c.date || c.date < HISTORY_START || c.date > HISTORY_END ||
        !/^\d{8}-\d$/.test(c.cpv || '') || c.cpv.startsWith('000') ||
        !Array.isArray(c.initialConflicts) || c.initialConflicts.length) continue;
    const key = `${c.cohortId}:${c.buyerSiret}:${c.cpv.slice(0, 3)}`;
    if (!supplierGroups.has(key)) supplierGroups.set(key, []);
    supplierGroups.get(key).push(c);
  }
  for (const group of supplierGroups.values()) {
    const known = group.filter(c => getSupplierIdentity(c) !== null);
    const bySupplier = new Map();
    known.forEach(c => { const id = getSupplierIdentity(c); if (!bySupplier.has(id)) bySupplier.set(id, []); bySupplier.get(id).push(c); });
    group.forEach(c => {
      const id = getSupplierIdentity(c);
      if (id === null) return;
      const supplierRows = bySupplier.get(id);
      const context = { cpvGroup: c.cpv.slice(0, 3), total: group.length, known: known.length,
        wins: supplierRows.length, share: supplierRows.length / known.length, coverage: known.length / group.length,
        sufficient: known.length >= 10 && known.length / group.length >= 0.8,
        directCount: supplierRows.filter(row => row.directAward === true).length,
        directKnownCount: supplierRows.filter(row => typeof row.directAward === 'boolean').length,
        supplierContracts: supplierRows.length };
      c.supplierContext = context;
    });
  }
  // SECOP II: buyer/contract-type concentration over the whole cohort, and
  // repetition of awards declared without supplier plurality, per buyer+supplier document.
  const coConcentrationGroups = new Map();
  const coRepetitionGroups = new Map();
  for (const c of contracts) {
    if (c.dataFamily !== 'secop2') continue;
    const buyerKey = c.buyerNit || c.buyer;
    const typeKey = `${buyerKey}|${c.contractType || ''}`;
    if (!coConcentrationGroups.has(typeKey)) coConcentrationGroups.set(typeKey, []);
    coConcentrationGroups.get(typeKey).push(c);
    const supplierId = secop2SupplierIdentity(c);
    if (secop2AvoidanceJustified(c) && supplierId != null) {
      const pairKey = `${buyerKey}|${supplierId}`;
      if (!coRepetitionGroups.has(pairKey)) coRepetitionGroups.set(pairKey, []);
      coRepetitionGroups.get(pairKey).push(c);
    }
  }
  for (const group of coConcentrationGroups.values()) {
    const known = group.filter(c => secop2SupplierIdentity(c) != null);
    const winsBySupplier = new Map();
    for (const c of known) {
      const id = secop2SupplierIdentity(c);
      winsBySupplier.set(id, (winsBySupplier.get(id) || 0) + 1);
    }
    for (const c of group) {
      const id = secop2SupplierIdentity(c);
      if (id == null) continue;
      const coverage = known.length / group.length;
      c.secop2Concentration = { contractType: group[0].contractType || '', total: group.length, known: known.length,
        wins: winsBySupplier.get(id) || 0, share: known.length ? (winsBySupplier.get(id) || 0) / known.length : null,
        coverage, sufficient: known.length >= CO_CONCENTRATION_GROUP_MIN && coverage >= CO_CONCENTRATION_COVERAGE };
    }
  }
  for (const group of coRepetitionGroups.values()) {
    for (const c of group) c.secop2Repetition = { count: group.length };
  }
  // SECOP II public-to-public context (no points): a declared interadministrative
  // agreement, or a comodato / public-credit contract whose counterparty document
  // is the counterparty of such an agreement elsewhere in the cohort.
  const coPublicAgreements = new Map();
  for (const c of contracts) {
    if (c.dataFamily !== 'secop2' || !CO_INTERADMIN_JUSTIFICATIONS.has(c.procedureJustification)) continue;
    const supplierId = secop2SupplierIdentity(c);
    const withheld = supplierId == null ? 'no-document' : CO_PERSON_DOCUMENTS.has(c.supplierIds[0].identifierType) ? 'person-document'
      : CO_COMMUNITY_NAME.test(c.supplier || '') ? 'community-body' : null;
    c.secop2PublicCounterparty = withheld ? { labelled: false, withheld } : { labelled: true, basis: 'declared-interadministrative' };
    if (!withheld && !coPublicAgreements.has(supplierId)) coPublicAgreements.set(supplierId, c.contractId);
  }
  for (const c of contracts) {
    if (c.dataFamily !== 'secop2' || c.secop2PublicCounterparty) continue;
    if (!CO_LOAN_OF_USE_OR_CREDIT.has(c.contractType) && !CO_LOAN_OF_USE_OR_CREDIT.has(c.procedureJustification)) continue;
    const agreement = coPublicAgreements.get(secop2SupplierIdentity(c));
    if (agreement) c.secop2PublicCounterparty = { labelled: true, basis: 'counterparty-of-agreement', agreementContractId: agreement };
  }
  // DNCP: buyer/category concentration and repetition per buyer+supplier,
  // counted in distinct processes (OCIDs) so multi-contract processes do not inflate.
  const pyConcentrationGroups = new Map();
  const pyRepetition = { single: new Map(), exception: new Map() };
  for (const c of contracts) {
    if (c.dataFamily !== 'dncp') continue;
    const key = `${c.buyerId || c.buyer}|${c.category || ''}`;
    if (!pyConcentrationGroups.has(key)) pyConcentrationGroups.set(key, []);
    pyConcentrationGroups.get(key).push(c);
    const supplierId = dncpSupplierIdentity(c);
    if (supplierId == null) continue;
    for (const [kind, member] of [['single', dncpSingleTenderer(c)], ['exception', dncpException(c)]]) {
      if (!member) continue;
      const pair = `${c.buyerId || c.buyer}|${supplierId}`;
      if (!pyRepetition[kind].has(pair)) pyRepetition[kind].set(pair, new Set());
      pyRepetition[kind].get(pair).add(c.ocid || c.id);
    }
  }
  for (const group of pyConcentrationGroups.values()) {
    const known = group.filter(c => dncpSupplierIdentity(c) != null);
    const wins = new Map();
    for (const c of known) wins.set(dncpSupplierIdentity(c), (wins.get(dncpSupplierIdentity(c)) || 0) + 1);
    const coverage = known.length / group.length;
    for (const c of known) {
      c.dncpConcentration = { category: group[0].category || '', total: group.length, known: known.length,
        wins: wins.get(dncpSupplierIdentity(c)), share: wins.get(dncpSupplierIdentity(c)) / known.length, coverage,
        sufficient: known.length >= PY_CONCENTRATION_GROUP_MIN && coverage >= PY_CONCENTRATION_COVERAGE };
    }
  }
  // Ukraine and TED: repetition in distinct procedures and buyer/category concentration.
  const natGroups = new Map(), natRep = { single: new Map(), direct: new Map() };
  for (const c of contracts) {
    const spec = NATIONAL_FAMILIES[c.dataFamily];
    if (!spec) continue;
    const buyer = `${c.dataFamily}|${c.buyerId || c.buyer}`, category = spec.category(c), supplier = nationalSupplierIdentity(c);
    if (category) { const key = `${buyer}|${category}`; if (!natGroups.has(key)) natGroups.set(key, []); natGroups.get(key).push(c); }
    if (!supplier) continue;
    for (const [kind, member] of [['single', nationalSingle(c)], ['direct', c.procedureDirect === true]]) {
      if (!member) continue;
      const pair = `${buyer}|${supplier}`;
      if (!natRep[kind].has(pair)) natRep[kind].set(pair, new Set());
      natRep[kind].get(pair).add(c.procedureId || c.noticeId || c.id);
    }
  }
  // Counted in distinct procedures: one multi-lot notice won by one supplier is one win, not one per lot.
  const procedureOf = c => c.procedureId || c.noticeId || c.id;
  for (const group of natGroups.values()) {
    const all = new Set(group.map(procedureOf)), known = new Set(), wins = new Map();
    for (const c of group) {
      const id = nationalSupplierIdentity(c);
      if (id == null) continue;
      known.add(procedureOf(c));
      if (!wins.has(id)) wins.set(id, new Set());
      wins.get(id).add(procedureOf(c));
    }
    const coverage = known.size / all.size;
    for (const c of group) {
      const id = nationalSupplierIdentity(c);
      if (id == null) continue;
      c.nationalConcentration = { category: NATIONAL_FAMILIES[c.dataFamily].category(c), total: all.size, known: known.size,
        wins: wins.get(id).size, share: wins.get(id).size / known.size, coverage, sufficient: known.size >= 10 && coverage >= 0.8 };
    }
  }
  for (const c of contracts) {
    if (!NATIONAL_FAMILIES[c.dataFamily] || !nationalSupplierIdentity(c)) continue;
    const pair = `${c.dataFamily}|${c.buyerId || c.buyer}|${nationalSupplierIdentity(c)}`;
    if (nationalSingle(c)) c.nationalRepeatedSingle = { count: natRep.single.get(pair).size };
    if (c.procedureDirect === true) c.nationalRepeatedDirect = { count: natRep.direct.get(pair).size };
  }
  for (const c of contracts) {
    if (c.dataFamily !== 'dncp' || dncpSupplierIdentity(c) == null) continue;
    const pair = `${c.buyerId || c.buyer}|${dncpSupplierIdentity(c)}`;
    if (dncpSingleTenderer(c)) c.dncpRepeatedSingle = { count: pyRepetition.single.get(pair).size };
    if (dncpException(c)) c.dncpRepeatedException = { count: pyRepetition.exception.get(pair).size };
  }
  return contracts;
}

function groupInfo(contract, mode) {
  if (mode === 'sector') { const sector = getSector(contract); return { key: `sector:${sector.code}`, label: `${sector.code === 'unknown' ? '' : sector.code + ' · '}${sector.label}` }; }
  if (mode === 'buyer') return { key: `buyer:${contract.buyerSiret || normalize(contract.buyer)}`, label: contract.buyer + (contract.buyerSiret ? ` · ${contract.buyerSiret}` : ' · matched by name, to be verified') };
  if (mode === 'supplier') {
    const identity = getSupplierIdentity(contract);
    return identity ? { key: `supplier:${identity}`, label: `SIREN ${identity} · ${supplierNames(contract)[0] || contract.supplier || 'Holder'}` } : { key: `supplier-unknown:${contract.id}`, label: `${contract.supplier || 'Unknown holder'} · consortium or unmatched identity` };
  }
  if (mode === 'project') return contract.project ? { key: `project:${contract.project.id}`, label: contract.project.title } : { key: 'project:unknown', label: 'No documented project — these contracts are not one project' };
  return { key: '', label: '' };
}

function arrangeGroups(contracts, mode) {
  if (!mode) return { rows: contracts, groups: new Map() };
  const groups = new Map();
  for (const c of contracts) {
    const info = groupInfo(c, mode);
    if (!groups.has(info.key)) groups.set(info.key, { ...info, contracts: [] });
    groups.get(info.key).contracts.push(c);
  }
  const ordered = [...groups.values()];
  if (mode === 'project') ordered.sort((a, b) => Number(a.key === 'project:unknown') - Number(b.key === 'project:unknown'));
  return { rows: ordered.flatMap(group => group.contracts), groups };
}

function normalize(value) {
  return String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('fr');
}

function safeSource(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}

function validateNoticeEvidence(c) {
  const e = c.noticeEvidence;
  if (!e || typeof e !== 'object' || e.noticeId !== c.noticeId || e.lotId !== c.lotId || e.procedureId !== c.contractFolderId ||
      e.source !== c.source || !safeSource(e.source) || !['initial', 'correction', 'award'].includes(e.kind))      throw new Error(`${c.id} : incompatible notice evidence scope.`);
  for (const key of ['noticeUuid', 'version', 'lotReference', 'procedureId', 'procedureReference', 'procedureType', 'procedureDescription', 'legalBasis', 'dispatchDate', 'dispatchTime', 'publicationDate', 'sourcePath']) {
    if (e[key] != null && typeof e[key] !== 'string') throw new Error(`${c.id} : invalid documentary field ${key}.`);
  }    for (const key of ['accelerated', 'relaunch', 'deadlineConflict', 'inPublicationWindow']) if (e[key] != null && typeof e[key] !== 'boolean') throw new Error(`${c.id} : invalid documentary state.`);    for (const key of ['justifications', 'awardCriteria', 'documents', 'references', 'buyers', 'ted', 'sameProcedureNotices', 'linkedNoticeLots']) if (!Array.isArray(e[key])) throw new Error(`${c.id} : invalid documentary list ${key}.`);
  if (!e.deadline || ['date', 'time', 'iso'].some(k => e.deadline[k] != null && typeof e.deadline[k] !== 'string')) throw new Error(`${c.id} : invalid documentary deadline.`);
  const texts = (item, keys) => item && keys.every(k => item[k] == null || typeof item[k] === 'string');
  for (const j of e.justifications) if (!texts(j, ['code', 'category', 'text', 'path']) || j.scope !== 'procedure' || j.source !== e.source) throw new Error(`${c.id} : justification without valid scope/source.`);
  for (const a of e.awardCriteria) {
    if (!texts(a, ['type', 'name', 'description', 'formula', 'path']) || a.lotId !== e.lotId || a.source !== e.source || !Array.isArray(a.parameters)) throw new Error(`${c.id} : criterion attached to the wrong lot/source.`);
    for (const p of a.parameters) if (!texts(p, ['code', 'codeList', 'rawValue']) || (p.value != null && (!Number.isFinite(p.value) || p.value < 0))) throw new Error(`${c.id} : invalid weighting.`);
  }
  for (const d of e.documents) if (!d || !safeSource(d.url) || typeof d.downloaded !== 'boolean') throw new Error(`${c.id} : invalid document.`);
  for (const r of e.references) if (!texts(r, ['id', 'kind', 'path']) || !Array.isArray(r.matchedNoticeIds) || r.matchedNoticeIds.some(id => typeof id !== 'string') || (r.tedSource != null && !safeSource(r.tedSource))) throw new Error(`${c.id} : invalid notice reference.`);
  for (const b of e.buyers) if (!texts(b, ['id', 'name', 'siret'])) throw new Error(`${c.id} : invalid documentary buyer.`);
  for (const t of e.ted) if (!texts(t, ['version', 'publicationNumber', 'publicationDate', 'deadlineDate', 'deadlineTime', 'retrievedAt']) || t.noticeUuid !== e.noticeUuid || (t.lotId != null && t.lotId !== e.lotId) || typeof t.versionMatches !== 'boolean' || t.versionMatches !== (t.version === e.version) || !safeSource(t.source) || !/^data\/tours-notices\/raw\/ted-\d+-\d{4}\.xml$/.test(t.localFile || '')) throw new Error(`${c.id} : invalid TED matching.`);
  for (const n of e.linkedNoticeLots) if (!texts(n, ['noticeId', 'lotId', 'version', 'kind', 'publicationDate', 'deadline', 'relation', 'basis']) || n.lotId !== e.lotId || !safeSource(n.source)) throw new Error(`${c.id} : invalid documentary lot link.`);
  for (const n of e.sameProcedureNotices) if (!n || typeof n.id !== 'string' || !safeSource(n.source)) throw new Error(`${c.id} : invalid procedure link.`);
}

function validateContracts(data) {
  if (!Array.isArray(data)) throw new Error('The file must contain a JSON array.');
  const ids = new Set();
  const projectDefinitions = new Map();
  for (const c of data) {
    if (!c || typeof c !== 'object' || typeof c.id !== 'string' || !c.id || ids.has(c.id)) {
      throw new Error('Each record must have a unique text identifier.');
    }
    ids.add(c.id);
    for (const key of ['buyer', 'description']) {
      if (typeof c[key] !== 'string' || !c[key].trim()) throw new Error(`${c.id} : missing ${key}.`);
    }
    for (const key of ['supplier', 'procedure', 'source', 'sourceLabel', 'sourceReference', 'notes', 'amountBasis', 'dateNote', 'reportUrl', 'responseLink', 'buyerSiret', 'contractId', 'lotId', 'noticeId', 'contractFolderId', 'cpv', 'publicationDate', 'priceType', 'priceForm', 'cohortId', 'identifierNote', 'nature', 'frameworkId', 'supplierNameSource']) {
      if (c[key] != null && typeof c[key] !== 'string') throw new Error(`${c.id} : ${key} must be text.`);
    }
    for (const key of ['amount', 'offers', 'durationMonths']) {
      if (c[key] != null && (typeof c[key] !== 'number' || !Number.isFinite(c[key]) || c[key] < 0)) {
        throw new Error(`${c.id} : ${key} must be a positive or zero number, or null.`);
      }
    }
    if (c.offers != null && !Number.isInteger(c.offers)) throw new Error(`${c.id} : invalid number of offers.`);
    for (const key of ['directAward', 'officialFinding']) {
      if (c[key] != null && typeof c[key] !== 'boolean') throw new Error(`${c.id} : ${key} must be boolean or null.`);
    }
    if (c.date != null && (typeof c.date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(c.date) || !Number.isFinite(Date.parse(c.date)) || new Date(c.date).toISOString().slice(0, 10) !== c.date)) {
      throw new Error(`${c.id} : invalid date (YYYY-MM-DD or null).`);
    }
    if (!['verified', 'unverified', 'synthetic'].includes(c.dataStatus)) throw new Error(`${c.id} : dataStatus required (verified, unverified, synthetic).`);
    for (const key of ['source', 'reportUrl', 'responseLink', 'supplierNameSource']) {
      if (c[key] != null && !safeSource(c[key])) throw new Error(`${c.id} : invalid ${key} HTTP(S) link.`);
    }
    if (c.project != null) {
      if (!c.project || typeof c.project !== 'object' || Array.isArray(c.project) ||
          typeof c.project.id !== 'string' || !/^[a-z0-9-]+$/.test(c.project.id) || typeof c.project.title !== 'string' || !c.project.title.trim() ||
          typeof c.project.basis !== 'string' || !c.project.basis.trim() || typeof c.project.source !== 'string' || !safeSource(c.project.source)) {
        throw new Error(`${c.id} : projet invalide.`);
      }
      if (c.project.evidence != null && (!Array.isArray(c.project.evidence) || c.project.evidence.some(e => !e ||
          typeof e !== 'object' || typeof e.label !== 'string' || !e.label.trim() || typeof e.description !== 'string' || !e.description.trim() || typeof e.type !== 'string' || !e.type.trim() ||
          typeof e.date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(e.date) || !Number.isFinite(Date.parse(e.date)) ||
          new Date(e.date).toISOString().slice(0, 10) !== e.date || typeof e.source !== 'string' || !safeSource(e.source)))) throw new Error(`${c.id} : invalid project evidence.`);
      const definition = JSON.stringify([c.project.title, c.project.basis, c.project.source, c.project.evidence || []]);
      if (projectDefinitions.has(c.project.id) && projectDefinitions.get(c.project.id) !== definition) throw new Error(`${c.id} : conflicting metadata for the same project.`);
      projectDefinitions.set(c.project.id, definition);
    }
    if (c.noticeEvidence != null) validateNoticeEvidence(c);
    if (c.consultation != null) {
      const timeline = c.consultation;
      if (!timeline || typeof timeline !== 'object' || typeof timeline.searchComplete !== 'boolean' ||
          !Array.isArray(timeline.notices) || !Array.isArray(timeline.exclusions) || timeline.exclusions.some(r => typeof r !== 'string')) throw new Error(`${c.id} : invalid timeline.`);
      for (const key of ['procedureId', 'procedureReference', 'lotId', 'initialNoticeId']) if (timeline[key] != null && typeof timeline[key] !== 'string') throw new Error(`${c.id} : invalid consultation identifier.`);
      if (timeline.matchedAwards != null && !Array.isArray(timeline.matchedAwards)) throw new Error(`${c.id} : invalid linked results.`);
      if (timeline.lots != null && (!Array.isArray(timeline.lots) || timeline.lots.some(l => !l || typeof l !== 'object' || (l.cpv != null && !Array.isArray(l.cpv))))) throw new Error(`${c.id} : invalid lots.`);
      for (const n of [...timeline.notices, ...(timeline.matchedAwards || [])]) {
        for (const key of ['version', 'publicationState', 'publicationDate', 'deadline', 'procedureType', 'correctionText']) if (n?.[key] != null && typeof n[key] !== 'string') throw new Error(`${c.id} : invalid notice field ${key}.`);
        if (!n || typeof n.id !== 'string' || !['initial', 'correction', 'award'].includes(n.kind) || !safeSource(n.source) ||
            (n.accelerated != null && typeof n.accelerated !== 'boolean') ||
            (n.previousNoticeIds != null && (!Array.isArray(n.previousNoticeIds) || n.previousNoticeIds.some(id => typeof id !== 'string')))) throw new Error(`${c.id} : invalid timeline notice.`);
      }
    }
    if (c.findingScope != null && !['contract', 'aggregate'].includes(c.findingScope)) throw new Error(`${c.id} : invalid finding scope.`);
    if (c.amountQualifier != null && !['at-least', 'more-than', 'approximate'].includes(c.amountQualifier)) throw new Error(`${c.id} : invalid amount qualifier.`);
    if (c.assessmentMode != null && !['browse', 'french'].includes(c.assessmentMode)) throw new Error(`${c.id} : invalid import assessment mode.`);
    if (c.dataFamily != null && !['decp', 'boamp', 'audit', 'secop2', 'dncp', 'prozorro', 'ted', 'fts', 'chile'].includes(c.dataFamily)) throw new Error(`${c.id} : invalid data family.`);
    if (c.buyerSiret != null && !/^\d{14}$/.test(c.buyerSiret)) throw new Error(`${c.id} : invalid buyer SIRET.`);
    if (c.supplierIds != null && (!Array.isArray(c.supplierIds) || c.supplierIds.some(s => !s || typeof s.id !== 'string' || (s.identifierType != null && typeof s.identifierType !== 'string')))) throw new Error(`${c.id} : invalid supplier identifiers.`);
    if (c.supplierProfiles != null) {
      if (!Array.isArray(c.supplierProfiles)) throw new Error(`${c.id} : invalid supplier profiles.`);
      const identities = new Set((c.supplierIds || []).map(s => s.identifierType === 'SIRET' && /^\d{14}$/.test(s.id) ? s.id.slice(0, 9) : s.identifierType === 'SIREN' && /^\d{9}$/.test(s.id) ? s.id : null).filter(Boolean));
      const seenProfiles = new Set();
      for (const p of c.supplierProfiles) {
        if (!p || !identities.has(p.siren) || seenProfiles.has(p.siren) || p.diffusionStatus !== 'O' || p.status !== 'available' ||
            typeof p.name !== 'string' || !p.name.trim() || (p.administrativeState != null && !['A', 'C'].includes(p.administrativeState)) ||
            typeof p.retrievedAt !== 'string' || !Number.isFinite(Date.parse(p.retrievedAt)) ||
            p.source !== `https://recherche-entreprises.api.gouv.fr/search?q=${p.siren}&per_page=25`) throw new Error(`${c.id} : unmatched supplier identity or invalid diffusion/provenance.`);
        seenProfiles.add(p.siren);
      }
    }
    if (c.modificationConflicts != null && (!Array.isArray(c.modificationConflicts) || c.modificationConflicts.some(m => !m || typeof m.id !== 'string' || !Array.isArray(m.fields) || m.fields.some(f => typeof f !== 'string')))) throw new Error(`${c.id} : invalid modification conflicts.`);
    if (c.initialConflicts != null && (!Array.isArray(c.initialConflicts) || c.initialConflicts.some(key => typeof key !== 'string'))) throw new Error(`${c.id} : invalid version conflicts.`);
    if (c.history != null) {
      if (!Array.isArray(c.history) || c.history.filter(e => e?.kind === 'initial').length !== 1) throw new Error(`${c.id} : a history requires exactly one initial entry.`);
      for (const event of c.history) {
        if (!event || !['initial', 'modification'].includes(event.kind)) throw new Error(`${c.id} : invalid history event.`);
        for (const key of ['id', 'supplierId']) if (event[key] != null && typeof event[key] !== 'string') throw new Error(`${c.id} : invalid history identifier.`);
        for (const key of ['amount', 'durationMonths']) if (event[key] != null && (typeof event[key] !== 'number' || !Number.isFinite(event[key]) || event[key] < 0)) throw new Error(`${c.id} : invalid historical amount or duration.`);
        for (const key of ['date', 'publicationDate']) if (event[key] != null && (typeof event[key] !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(event[key]) || !Number.isFinite(Date.parse(event[key])) || new Date(event[key]).toISOString().slice(0, 10) !== event[key])) throw new Error(`${c.id} : invalid historical date.`);
      }
    }
    if (c.initialAlternatives != null && (!Array.isArray(c.initialAlternatives) || c.initialAlternatives.some(a => !a || typeof a !== 'object' || (a.amount != null && (typeof a.amount !== 'number' || !Number.isFinite(a.amount) || a.amount < 0))))) throw new Error(`${c.id} : invalid initial variants.`);
    if (c.officialFinding === true && (c.dataStatus !== 'verified' || !safeSource(c.source) || !c.sourceReference)) {
      throw new Error(`${c.id} : an official finding requires a verified source and a reference passage.`);
    }
    if (c.investigationReports != null) {
      if (!Array.isArray(c.investigationReports) || c.findingScope === 'aggregate' || c.dataStatus !== 'verified' ||
          c.investigationReports.some(report => {
            const fields = ['publisher', 'reportedFact', 'linkageBasis', 'currentStatus'];
            return !report || typeof report !== 'object' || Array.isArray(report) ||
              report.status !== 'reported-at-date-current-unknown' || report.scope !== 'contract' ||
              fields.some(key => typeof report[key] !== 'string' || !report[key].trim()) ||
              !safeSource(report.sourceUrl) ||
              [report.reportedAt, report.eventDate].some(date => typeof date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isFinite(Date.parse(date)) || new Date(date).toISOString().slice(0, 10) !== date) ||
              report.reportedAt < report.eventDate;
          })) throw new Error(`${c.id} : reported investigation requires dated contract-specific news and unknown current status.`);
    }
    if (c.corruptionOutcome != null) {
      const o = c.corruptionOutcome;
      const required = ['authority', 'decisionId', 'decisionDate', 'judgmentUrl', 'finalityUrl', 'verifiedAsOf', 'sourcePassage', 'offence', 'contractId', 'linkageBasis'];
      if (!o || typeof o !== 'object' || Array.isArray(o) || o.status !== 'final-adjudication' || o.scope !== 'contract' ||
          c.dataStatus !== 'verified' || c.findingScope === 'aggregate' || !c.contractId || o.contractId !== c.contractId ||
          required.some(key => typeof o[key] !== 'string' || !o[key].trim()) ||
          !safeSource(o.judgmentUrl) || !safeSource(o.finalityUrl) ||
          [o.decisionDate, o.verifiedAsOf].some(date => !/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isFinite(Date.parse(date)) || new Date(date).toISOString().slice(0, 10) !== date) ||
          o.verifiedAsOf < o.decisionDate) throw new Error(`${c.id} : final corruption outcome requires a contract-specific judgment, source passage and verified finality.`);
    }
  }
  return data;
}

// Normalised searchable text, built once per record (records do not change after preparation).
const searchTextCache = new WeakMap();
function searchText(c) {
  let text = searchTextCache.get(c);
  if (text === undefined) {
    const projectText = c.project ? [c.project.title, c.project.basis] : [];
    const evidence = c.noticeEvidence;
    const noticeText = evidence ? [evidence.noticeUuid, evidence.lotReference, evidence.procedureId, evidence.procedureReference, evidence.procedureDescription, ...evidence.awardCriteria.map(a => [a.name, a.description, a.formula].join(' ')), ...evidence.justifications.map(j => j.text), ...evidence.references.map(r => r.id)] : [];
    text = normalize([c.id, c.buyer, c.buyerSiret, c.supplier, c.description, c.procedure, c.cpv, c.contractId, c.awardId, c.buyerId, c.lotId, c.noticeId, ...(c.supplierProfiles || []).map(p => p.name), c.consultation?.procedureReference, ...(c.consultation?.notices || []).map(n => n.id), ...(c.consultation?.lots || []).map(l => `${l.id || ''} ${l.description || ''}`), ...projectText, ...noticeText, ...(c.supplierIds || []).map(s => `${s.id} ${s.siren || ''}`)].join(' '));
    searchTextCache.set(c, text);
  }
  return text;
}

function selectContracts(contracts, { search = '', minimum = 0, minScore = 0, flagged = false, official = false, adjudicated = false, investigation = false, indicator = '', legal = '', noticeContext = '', assessment = '', sector = '', project = '', sort = 'score' } = {}) {
  const terms = normalize(search).trim().split(/\s+/).filter(Boolean);
  // Per-render caches only: no stale scores when data or cohort context changes.
  const scores = new Map();
  const increases = new Map();
  const scoreFor = c => { if (!scores.has(c)) scores.set(c, getVigilanceScore(c)); return scores.get(c); };
  const increaseFor = c => {
    if (!increases.has(c)) { const change = getAmountEvolution(c); increases.set(c, change.status === 'available' ? change.percentage : null); }
    return increases.get(c);
  };
  const collator = new Intl.Collator('en', { sensitivity: 'base', numeric: true });
  // Equal scores: more families with a signal first, then the strongest single signal.
  const strengths = new Map();
  const strengthFor = c => {
    if (!strengths.has(c)) {
      const signals = getAssessment(c).checks.filter(r => r.status === 'signal');
      strengths.set(c, [new Set(signals.map(r => r.family)).size, signals.reduce((m, r) => Math.max(m, r.weight), 0)]);
    }
    return strengths.get(c);
  };
  const filtered = contracts.filter(c => {
    const evidence = c.noticeEvidence;
    const noticeMatch = !noticeContext || Boolean(evidence && (noticeContext === 'criteria' ? evidence.awardCriteria.length : noticeContext === 'explanation' ? evidence.procedureDescription || evidence.justifications.some(j => j.text) : noticeContext === 'correction' ? evidence.kind === 'correction' : noticeContext === 'ted' ? evidence.ted.length : false));
    const citations = legal && !['py-complaint', 'co-public', 'fr-software', 'direct'].includes(legal) ? getLegalContext(c) : [];
    const legalMatch = !legal || (legal === 'py-complaint' ? Boolean(c.complaints?.length) : legal === 'co-public' ? Boolean(c.secop2PublicCounterparty?.labelled) : legal === 'fr-software' ? Boolean(softwareMaintenanceContext(c)) : legal === 'direct' ? c.directAward === true : legal === 'cited' ? citations.length > 0 : citations.some(item => item.article === legal));
    const evaluated = getAssessment(c);
    const assessmentMatch = !assessment || (assessment === 'unevaluated' ? scoreFor(c) == null : assessment === 'zero' ? scoreFor(c) === 0 : assessment === 'partial' ? evaluated.unknown > 0 || evaluated.unknownApplicability > 0 : false);
    const sectorMatch = !sector || getSector(c).code === sector;
    const projectMatch = !project || (project === '@documented' ? Boolean(c.project) : c.project?.id === project);
    return (!terms.length || terms.every(term => searchText(c).includes(term))) && assessmentMatch && noticeMatch && legalMatch && sectorMatch && projectMatch &&
      (minimum <= 0 || (c.amount != null && c.amount >= minimum)) && (minScore <= 0 || (scoreFor(c) != null && scoreFor(c) >= minScore)) &&
      (!flagged || getIndicators(c).length > 0) && (!official || c.officialFinding === true) && (!adjudicated || hasAdjudicatedCorruption(c)) && (!investigation || hasReportedInvestigation(c)) &&
      (!indicator || (indicator === 'official-finding' ? c.officialFinding === true : getIndicators(c).some(i => i.kind === indicatorKind(indicator))));
  });
  const direction = ['score-asc', 'amount-asc', 'date-asc', 'publication-asc', 'indicators-asc', 'offers'].includes(sort) ? 1 : ['sector', 'sector-desc', 'buyer', 'buyer-desc', 'supplier', 'supplier-desc'].includes(sort) ? (sort.endsWith('-desc') ? -1 : 1) : -1;
  const field = sort === 'recent-signal' ? 'recent-signal' : sort.startsWith('score') ? 'score' : sort.startsWith('amount') ? 'amount' : sort.startsWith('date') ? 'date' : sort.startsWith('indicators') ? 'indicators' : sort.startsWith('publication') ? 'publication' : sort.startsWith('sector') ? 'sector' : sort.startsWith('buyer') ? 'buyer' : sort.startsWith('supplier') ? 'supplier' : sort.startsWith('offers') ? 'offers' : sort;
  const raw = c => field === 'recent-signal' ? (scoreFor(c) > 0 && c.date ? Date.parse(c.date) : null) : field === 'score' ? scoreFor(c) : field === 'amount' ? c.amount : field === 'date' ? (c.date ? Date.parse(c.date) : null) :
    field === 'publication' ? (c.publicationDate ? Date.parse(c.publicationDate) : null) : field === 'sector' ? getSector(c).label : field === 'buyer' ? c.buyer : field === 'supplier' ? c.supplier :
    field === 'indicators' ? (scoreFor(c) == null ? null : getIndicators(c).length) :
    field === 'official' ? (c.officialFinding === true ? 1 : null) : field === 'offers' ? c.offers : field === 'increase' ? increaseFor(c) : null;
  return filtered.sort((a, b) => {
    const av = raw(a), bv = raw(b);
    const nullOrder = av == null ? (bv == null ? 0 : 1) : bv == null ? -1 : 0;
    if (nullOrder) return nullOrder;
    // Amounts are never compared across currencies: group by currency, then amount.
    if (field === 'amount' && (a.currency || 'EUR') !== (b.currency || 'EUR')) return collator.compare(a.currency || 'EUR', b.currency || 'EUR');
    if (field === 'sector' && av === 'Sector not specified' && bv !== av) return 1;
    if (field === 'sector' && bv === 'Sector not specified' && av !== bv) return -1;
    const comparison = typeof av === 'string' ? collator.compare(av, bv) : av === bv ? 0 : av > bv ? 1 : -1;
    return comparison * direction || ((scoreFor(b) ?? -1) - (scoreFor(a) ?? -1)) || (strengthFor(b)[0] - strengthFor(a)[0]) || (strengthFor(b)[1] - strengthFor(a)[1]) || collator.compare(a.id, b.id);
  });
}

// Export only the visible page, never silently imply that the cohort is complete.
// This is a research lead with source links, not a corruption verdict or payment audit.
function pageSummaryForCopy(rows, { dataset, page, totalPages, totalResults }) {
  const lines = [`Contract signals · ${dataset}`, `Page ${page} / ${totalPages} · ${rows.length} of ${totalResults} filtered records`,
    'Published declarations and heuristic signals only. A flag is not proof of wrongdoing; zero or no label is not clearance. Dates, amounts and source coverage vary by dataset.', ''];
  for (const [index, c] of rows.entries()) {
    const score = getVigilanceScore(c);
    const signals = getIndicators(c);
    const source = safeSource(c.processUrl) || safeSource(c.source);
    const names = supplierNames(c);
    lines.push(`[${index + 1}] ${c.id}`, `Buyer: ${c.buyer}`, `Supplier: ${c.supplier || 'not specified'}${names.length ? ` (current register name: ${names.join('; ')})` : ''}`,
      `Subject: ${c.description}`, `Date (source field; see record for meaning): ${c.date || 'unknown'}`,
      `Declared amount: ${c.amount == null ? 'unknown' : `${c.amount} ${recordCurrency(c) || '(currency unknown)'}`} (not an audited payment)`,
      `Index: ${score == null ? 'Not assessed' : `${score}/100`} · Heuristic signals: ${signals.length ? signals.map(i => i.kindLabel).join('; ') : score == null ? 'not assessed' : 'none among assessed checks'}`,
      `Audit finding: ${c.officialFinding === true ? 'documented, separate from index' : 'not linked in this extract'} · Reported investigation: ${hasReportedInvestigation(c) ? 'reported at the time; current status unknown' : 'not linked in this extract'}`,
      `Record source: ${source || 'not available'}`);
    for (const link of verificationLinks(c)) if (link.url !== source && link.url !== safeSource(c.reportUrl)) lines.push(`Verify: ${link.label} · ${link.url}`);
    if (c.officialFinding && safeSource(c.reportUrl)) lines.push(`Audit report: ${safeSource(c.reportUrl)}`);
    for (const report of c.investigationReports || []) lines.push(`Dated news report: ${report.reportedAt} · ${report.sourceUrl}`);
    lines.push('');
  }
  return lines.join('\n').trimEnd();
}

// Shareable view state lives in the URL fragment (#…), which browsers never send to the server.
// [fragment key, control id, default value]
const VIEW_FIELDS = [['q', 'search', ''], ['sort', 'sort', 'score'], ['min', 'minimum', ''], ['sector', 'sector', ''], ['group', 'group-by', ''],
  ['project', 'project', ''], ['assessment', 'assessment', ''], ['index', 'min-score', '0'], ['indicator', 'indicator', ''],
  ['notice', 'notice-context', ''], ['legal', 'legal', ''], ['open', 'open-record', '']];
const VIEW_FLAGS = ['flagged', 'official', 'adjudicated', 'investigation'];
const PAGE_SIZES = [25, 50, 100, 250];

function viewStateToHash(state) {
  const params = new URLSearchParams();
  if (state.dataset) params.set('dataset', state.dataset);
  for (const [key, id, fallback] of VIEW_FIELDS) if (state[id] != null && state[id] !== '' && state[id] !== fallback) params.set(key, state[id]);
  for (const id of VIEW_FLAGS) if (state[id]) params.set(id, '1');
  if (state.page > 1) params.set('page', String(state.page));
  if (state.pageSize && state.pageSize !== 50) params.set('size', String(state.pageSize));
  const text = params.toString();
  return text ? '#' + text : '';
}

function hashToViewState(hash) {
  const params = new URLSearchParams(String(hash || '').replace(/^#/, ''));
  const state = { dataset: params.get('dataset') || '' };
  for (const [key, id, fallback] of VIEW_FIELDS) state[id] = params.get(key) ?? fallback;
  for (const id of VIEW_FLAGS) state[id] = params.get(id) === '1';
  const page = Number(params.get('page'));
  state.page = Number.isInteger(page) && page > 0 ? page : 1;
  const size = Number(params.get('size'));
  state.pageSize = PAGE_SIZES.includes(size) ? size : 50;
  return state;
}

function supplierNames(contract) {
  // The register repeats the acronym when it equals the name: “MGDIS (MGDIS)”.
  return (contract.supplierProfiles || []).map(p => String(p.name || '').replace(/^(.+) \(\1\)$/, '$1'));
}

// Buyer and supplier profiles (never cross datasets; amounts never summed).
function profileScope(c) { return c.datasetKey || c.cohortId || c.dataFamily || 'data'; }
function profileKey(c, role) {
  if (role === 'buyer') {
    const id = c.buyerSiret || c.buyerNit || c.buyerId || c.buyer;
    return id ? `${profileScope(c)}|${id}` : null;
  }
  const id = c.dataFamily === 'secop2' ? secop2SupplierIdentity(c) : c.dataFamily === 'dncp' ? dncpSupplierIdentity(c)
    : NATIONAL_FAMILIES[c.dataFamily] ? nationalSupplierIdentity(c) : getSupplierIdentity(c);
  return id ? `${profileScope(c)}|${id}` : null;
}
function buildProfile(contracts, role, key) {
  const rows = contracts.filter(c => profileKey(c, role) === key);
  if (!rows.length) return null;
  const scope = contracts.filter(c => profileScope(c) === profileScope(rows[0]));
  const rate = set => {
    const out = {};
    for (const c of set) for (const check of getAssessment(c).checks) {
      const kind = indicatorKind(check.id);
      if (!kind || (check.status !== 'signal' && check.status !== 'clear')) continue;
      out[kind] ??= { signals: 0, evaluated: 0 };
      out[kind].evaluated++;
      if (check.status === 'signal') out[kind].signals++;
    }
    return out;
  };
  const other = role === 'buyer' ? 'supplier' : 'buyer';
  const counterparts = new Map();
  for (const c of rows) {
    const name = (other === 'supplier' ? (supplierNames(c)[0] || c.supplier) : c.buyer) || 'not published';
    const entry = counterparts.get(name) || { name, contracts: 0, flagged: 0 };
    entry.contracts++;
    if (getVigilanceScore(c) > 0) entry.flagged++;
    counterparts.set(name, entry);
  }
  const currencies = {};
  for (const c of rows) if (c.amount != null) {
    const cur = c.currency || 'EUR';
    currencies[cur] ??= { contracts: 0, largest: 0 };
    currencies[cur].contracts++;
    currencies[cur].largest = Math.max(currencies[cur].largest, c.amount);
  }
  const dates = rows.map(c => c.date).filter(Boolean).sort();
  const scores = rows.map(getVigilanceScore);
  return { role, key, name: role === 'buyer' ? rows[0].buyer : (supplierNames(rows[0])[0] || rows[0].supplier), country: rows[0].datasetCountry || null,
    ids: new Set(rows.map(c => c.id)), contracts: rows.length, assessed: scores.filter(x => x != null).length, flagged: scores.filter(x => x > 0).length,
    firstDate: dates[0] || null, lastDate: dates[dates.length - 1] || null, kinds: rate(rows), baseline: rate(scope), scopeSize: scope.length,
    counterparts: [...counterparts.values()].sort((a, b) => b.contracts - a.contracts || b.flagged - a.flagged || a.name.localeCompare(b.name)).slice(0, 10), currencies };
}

// Export the whole filtered view as flat records. Unknown stays empty, never zero.
const EXPORT_CAVEAT = 'Published declarations and heuristic signals only. A flag is not proof of wrongdoing; zero or no label is not clearance. Declared amounts are not audited payments; never sum amounts across datasets or currencies. Current supplier names are a register snapshot, not historical names.';
const EXPORT_COLUMNS = ['id', 'date', 'buyer', 'buyerId', 'supplier', 'supplierCurrentName', 'supplierIds', 'description', 'cpv', 'sector', 'procedure',
  'amount', 'currency', 'offers', 'durationMonths', 'index', 'indexStatus', 'signals', 'context', 'officialFinding', 'investigationReported', 'dataStatus', 'source', 'verifyUrls'];

function exportRecord(c) {
  const score = getVigilanceScore(c);
  return {
    id: c.id, date: c.date ?? null, buyer: c.buyer, buyerId: c.buyerSiret || c.buyerNit || c.buyerId || null, supplier: c.supplier ?? null,
    supplierCurrentName: supplierNames(c).join('; ') || null,
    supplierIds: (c.supplierIds || []).map(s => `${s.identifierType || 'identifier'} ${s.id}`).join('; ') || null,
    description: c.description, cpv: c.cpv ?? null, sector: getSector(c).label, procedure: c.procedure ?? null,
    amount: c.amount ?? null, currency: c.amount == null ? null : recordCurrency(c), offers: c.offers ?? null, durationMonths: c.durationMonths ?? null,
    index: score, indexStatus: score == null ? 'not assessed' : 'assessed', signals: getIndicators(c).map(i => i.kindLabel).join('; ') || null,
    context: contextLabels(c).map(l => l.short).join('; ') || null,
    officialFinding: c.officialFinding === true, investigationReported: hasReportedInvestigation(c), dataStatus: c.dataStatus,
    source: safeSource(c.processUrl) || safeSource(c.source) || null,
    verifyUrls: verificationLinks(c).map(l => l.url).join(' ') || null
  };
}

function recordCurrency(c) {
  return c.currency || (c.assessmentMode ? null : 'EUR');
}

function csvCell(value) {
  if (value == null) return '';
  let text = String(value);
  // Spreadsheet formula guard: published text is data, never a formula.
  if (typeof value === 'string' && /^[\s\u0000-\u001f]*[=+\-@]|^[\t\r\n]/.test(text)) text = "'" + text;
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function rowsToCsv(rows) {
  const lines = [EXPORT_COLUMNS.join(',')];
  for (const c of rows) { const record = exportRecord(c); lines.push(EXPORT_COLUMNS.map(key => csvCell(record[key])).join(',')); }
  return lines.join('\r\n') + '\r\n';
}

function rowsToJson(rows, { dataset, view, exportedAt }) {
  return JSON.stringify({ tool: 'Contract signals', scoreVersion: SCORE_VERSION, dataset, view, exportedAt, caveat: EXPORT_CAVEAT,
    count: rows.length, records: rows.map(exportRecord) }, null, 2) + '\n';
}

// Everything from JSON is inserted as text, never as HTML.
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function sourceLink(url, label) {
  const link = element('a', label); link.href = safeSource(url); link.target = '_blank'; link.rel = 'noopener noreferrer'; return link;
}

// Every link a reader can follow to check a row at its source, human-readable
// official pages first, then documents, then the machine-readable record.
// Only URLs published in the data are listed; none is constructed.
function verificationLinks(c) {
  const links = [];
  const add = (url, label) => { const safe = safeSource(url); if (safe && !links.some(l => l.url === safe)) links.push({ label, url: safe }); };
  if (c.dataFamily === 'dncp') {
    add(c.awardUrl, 'Award page on contrataciones.gov.py (tenderers, award resolution, evaluation report)');
    add(c.callUrl, 'Call for tenders page on contrataciones.gov.py');
    const kinds = { bidComparison: 'Bid comparison table (Cuadro Comparativo de Ofertas): offers per lot', evaluationReport: 'Evaluation report (Informe de Evaluación)', awardResolution: 'Award resolution (Resolución de Adjudicación)' };
    for (const kind of ['bidComparison', 'evaluationReport', 'awardResolution']) {
      (c.awardDocuments || []).filter(d => d.kind === kind).forEach(d => add(d.url, `${kinds[kind]} · ${d.title || 'PDF'}${d.date ? ` · ${d.date}` : ''}`));
    }
    (c.signedDocumentUrls || []).forEach((url, n) => add(url, `Contract document ${n + 1} typed contractSigned (PDF; contents not reviewed here)`));
    for (const complaint of c.complaints || []) for (const d of complaint.documents) add(d.url, `DNCP resolution on complaint ${complaint.id} · ${d.title || 'PDF'}${d.date ? ` · ${d.date}` : ''}`);
  }
  if (c.dataFamily === 'secop2') add(c.processUrl, 'Process page on SECOP II');
  if (c.dataFamily === 'chile') add(c.portalUrl, 'Tender page on Mercado Público (bids, evaluation and award documents; address built from the tender code)');
  if (c.dataFamily === 'fts') add(c.portalUrl, 'Notice page on Find a Tender (full award notice; address built from the notice ID)');
  if (c.dataFamily === 'prozorro') {
    add(c.portalUrl, 'Tender page on prozorro.gov.ua (bids, awards, contract documents; address built from the tender ID)');
    add(c.linkedContract?.url, 'Linked official contract record · separately dated snapshot');
  }
  add(c.source, c.sourceLabel || 'Original source record');
  if (c.dataFamily === 'ted') add(c.xmlUrl, 'Official eForms XML of the notice (machine-readable)');
  add(c.reportUrl, 'Original official report');
  add(c.responseLink, 'Official response of the audited organization');
  add(c.supplierNameSource, 'Supplier name — Annuaire des entreprises');
  for (const r of c.investigationReports || []) add(r.sourceUrl, `Contemporary report · ${r.publisher}`);
  return links;
}

// Identifiers to paste into the official portal's own search, if a link breaks.
function verificationIdentifiers(c) {
  return [['OCID', c.ocid], ['Contract', c.contractId], ['Award', c.awardId], ['Process', c.processId], ['Buyer', c.buyerId || c.buyerSiret || c.buyerNit],
    ...(c.supplierIds || []).filter(s => !isMaskedId(s.id)).map(s => [s.identifierType || 'Supplier', s.id])].filter(([, v]) => typeof v === 'string' && v.trim());
}

function renderNoticeEvidence(cell, c) {
  // The notice's own declarations, compactly; procedure-wide texts may concern other lots.
  const e = c.noticeEvidence;
  const p = (text, ...nodes) => { const el = element('p', text); el.append(...nodes); cell.append(el); };
  cell.append(element('h4', 'Notice'));
  p(`${e.kind} · version ${e.version || '—'} · lot ${e.lotId || '—'}${e.lotReference ? ` (${e.lotReference})` : ''} · deadline ${e.deadline.iso || [e.deadline.date, e.deadline.time].filter(Boolean).join(' ') || '—'}${e.accelerated ? ' · accelerated' : ''}${e.relaunch ? ' · relaunch' : ''}`);
  if (e.buyers.length > 1) p(`Joint purchase: ${e.buyers.map(b => b.name || b.siret || '—').join(' / ')}`);
  if (e.legalBasis) p(`Legal basis: ${e.legalBasis}`);
  if (e.procedureDescription || e.justifications.some(j => j.text)) p('Procedure-wide text (may cover other lots):');
  if (e.procedureDescription) cell.append(element('blockquote', e.procedureDescription));
  for (const j of e.justifications) if (j.text) cell.append(element('blockquote', `${j.code ? `${j.code}: ` : ''}${j.text}`));
  if (e.awardCriteria.length) {
    const list = element('ul');
    for (const a of e.awardCriteria) list.append(element('li', `${a.type || '—'} · ${a.name || a.description || a.formula || '—'}${a.parameters.length ? ` · ${a.parameters.map(x => `${x.rawValue ?? '—'}${x.code ? ` (${x.code})` : ''}`).join(', ')}` : ''}`));
    cell.append(element('h4', 'Award criteria (this lot)'), list);
  }
  if (e.deadlineConflict) p('Deadlines differ between sources.');
  const links = element('p', null, 'link-row');
  for (const t of e.ted) { links.append(sourceLink(t.source, `TED ${t.publicationNumber}${t.versionMatches ? '' : ' (other version)'}`), ' '); const local = element('a', 'XML'); local.href = t.localFile; local.setAttribute('download', ''); links.append(local, ' · '); }
  for (const n of e.linkedNoticeLots) links.append(sourceLink(n.source, `${n.relation} ${n.noticeId}`), ' · ');
  for (const r of e.references) if (r.tedSource) links.append(sourceLink(r.tedSource, `Cited TED ${r.id}`), ' · ');
  for (const n of e.sameProcedureNotices) links.append(sourceLink(n.source, `Same procedure ${n.id}`), ' · ');
  for (const d of e.documents) links.append(sourceLink(d.url, 'Buyer document'), ' · ');
  if (links.childNodes.length) { if (links.lastChild.textContent === ' · ') links.lastChild.remove(); cell.append(links); }
}

// Names of individuals and foreign holders without a tax number (Portugal BASE) are stored scrambled so they cannot be read or
// collected in bulk from the data file; one name at a time can be shown in the record panel.
// Same method as tools/import-portugal-base.py (scramble_name). A deterrent, not secrecy.
const PROTECTED_NAME_SALT = 'contract-signals:base:name:v1';
const PROTECTED_NAME_ITERATIONS = 400000;
async function revealProtectedName(recordId, index, data) {
  if (!globalThis.crypto?.subtle) throw new Error('This browser cannot unscramble names here.');
  const encoder = new TextEncoder();
  const bytes = Uint8Array.from(atob(data), ch => ch.charCodeAt(0));
  const material = await crypto.subtle.importKey('raw', encoder.encode(recordId), 'PBKDF2', false, ['deriveBits']);
  const key = new Uint8Array(await crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt: encoder.encode(`${PROTECTED_NAME_SALT}:${index}`), iterations: PROTECTED_NAME_ITERATIONS }, material, 256));
  const out = new Uint8Array(bytes.length);
  for (let block = 0; block * 32 < bytes.length; block++) {
    const stream = new Uint8Array(await crypto.subtle.digest('SHA-256', Uint8Array.from([...key, block])));
    for (let i = 0; i < 32 && block * 32 + i < bytes.length; i++) out[block * 32 + i] = bytes[block * 32 + i] ^ stream[i];
  }
  return new TextDecoder('utf-8', { fatal: true }).decode(out);
}

// First sentence of a check's reason: the record's own fact, without the method text.
function briefReason(text) {
  // Translate the whole sentence first (the dictionaries hold full reasons), then shorten.
  const full = String(text || '').trim();
  const s = typeof i18nTranslate === 'function' ? i18nTranslate(full) : full;
  const m = /^(.+?(?<!\b(?:Art|art|No|no|Nº|n|cf))[.!?])\s+(?=[\p{Lu}\d“"(«])/u.exec(s);
  return m ? m[1] : s;
}

function startExplorer() {
  const body = document.querySelector('#contracts');
  const status = document.querySelector('#status');
  const fileHelp = document.querySelector('#file-help');
  const controls = Object.fromEntries(['search', 'minimum', 'flagged', 'official', 'adjudicated', 'investigation', 'indicator', 'legal', 'notice-context', 'assessment', 'sort', 'sector', 'project', 'group-by', 'min-score', 'review'].map(id => [id, document.getElementById(id)]));
  const datasetSelect = document.querySelector('#dataset');
  const datasets = {
    tours: { path: 'data/tours-notices.json', coverage: 'data/tours-notices-coverage.json', sources: { publisher: 'DILA — BOAMP; Publications Office of the EU — TED', links: [['BOAMP search', 'https://www.boamp.fr/'], ['BOAMP API used', 'https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records'], ['TED search', 'https://ted.europa.eu/']], licence: 'BOAMP: Licence Ouverte 2.0 (DILA legal notice and data.gouv.fr); TED legal notice applies. See docs/data-sources.md for scope.', raw: 'data/tours-notices/raw/', reproduce: 'python tools/import-tours-notices.py --offline', collected: 'BOAMP notices matched by the buyer’s exact SIRET, TED XML matched by UUID and version.' }, note: 'Tours · full 2025 notices and out-of-period linked references: 25 buyer-verified notices, 66 version/lot rows, including labelled joint purchases. 25 rows with award criteria; procedure texts and 2 corrections kept. TED XML matched by UUID and version, not by name. These are documents, not 66 contracts or expenses: no bidding-period score without a reliable chain.' },
    cities: { path: 'data/decp-cities.json', coverage: 'data/decp-cities-coverage.json', sources: { publisher: 'Ministère de l’Économie et des Finances — DECP (données essentielles de la commande publique)', links: [['Dataset page · data.economie.gouv.fr', 'https://data.economie.gouv.fr/explore/dataset/decp-2022-marches-valides/'], ['API used (records endpoint)', 'https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records'], ['DECP schema v2.0.4', 'https://github.com/139bercy/decp-arr2022/blob/main/schemes/schema_decp_v2.0.4.json']], licence: 'Licence Ouverte v2.0 (Etalab)', raw: 'data/decp-cities-raw.json', reproduce: 'python tools/import-decp-cities.py --offline', collected: 'Every DECP row for six pre-selected municipal buyer SIRETs, notified 2024–2025, paged through the source total.' }, note: 'Six pre-selected municipalities: Rennes, Nantes, Bordeaux, Grenoble, Dijon and Tours (not the metro areas). Notifications 2024–2025: 1,865 published rows, 1,270 buyer/identifier groups, of which 172 ambiguous ones excluded from calculations. 355 groups with published modifications. Non-representative cohort, not all spending. Current public register names on 1,116 rows (every typed SIREN looked up; restricted-diffusion companies are not named): current names and status, not verified at the contract date. Separate datasets, no cross-source sums.' },
    consultations: { path: 'data/consultations.json', coverage: 'data/consultations-coverage.json', sources: { publisher: 'DILA — BOAMP', links: [['BOAMP search', 'https://www.boamp.fr/'], ['BOAMP API used', 'https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records']], licence: 'Licence Ouverte 2.0 (DILA legal notice and official data.gouv.fr records); incorporated third-party material may have separate rights.', raw: 'data/consultations-raw.json', reproduce: 'python tools/import-consultations.py --offline', collected: 'The first 10 initial BOAMP calls published on 3 February 2025, by identifier order.' }, note: '10 initial BOAMP notices from 3 February 2025, first identifiers among 200, selected before any calculation. One correction and three award notices linked explicitly. Notice-level rows, not attributed contracts or expenses. Chains not certified complete: no bidding-period score in this extract. No independent TED download.' },
    decp: { path: 'data/decp-history.json', coverage: 'data/decp-coverage.json', sources: { publisher: 'Ministère de l’Économie et des Finances — DECP (données essentielles de la commande publique)', links: [['Dataset page · data.economie.gouv.fr', 'https://data.economie.gouv.fr/explore/dataset/decp-2022-marches-valides/'], ['API used (records endpoint)', 'https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records'], ['DECP schema v2.0.4', 'https://github.com/139bercy/decp-arr2022/blob/main/schemes/schema_decp_v2.0.4.json']], licence: 'Licence Ouverte v2.0 (Etalab)', raw: 'data/decp-history-raw.json.gz', reproduce: 'python tools/import-decp-paris-ardeche.py --offline', collected: 'Every DECP row for the Ville de Paris and Département de l’Ardèche SIRETs, notified 2024–2025. Three rows of the Paris 13 November dossier carry hand-curated fields, kept in data/decp-history-curated.json.' }, note: 'Exploratory 24-month history: 2,594 DECP contracts from Paris and Ardèche, notified in 2024–2025. Every row returned by the source for these two SIRETs was examined; this does not guarantee that all actual purchases were published. Paris was chosen for volume, Ardèche for the availability of modifications: this choice is not representative. Modifications may be later than 2025. Suppliers identified by SIRET; current public register names shown on 2,586 rows (not the names at the contract date; restricted-diffusion companies are not named). The eight official findings are in the other dataset.' },
    boamp: { path: 'data/contracts.json', coverage: 'data/coverage.json', sources: { publisher: 'DILA — BOAMP; Chambres régionales des comptes (audit dossiers)', links: [['BOAMP search', 'https://www.boamp.fr/'], ['BOAMP API used', 'https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records'], ['CRC reports · ccomptes.fr', 'https://www.ccomptes.fr/fr/publications']], licence: 'BOAMP: Licence Ouverte 2.0 (DILA legal notice and data.gouv.fr); CRC reports quoted with links.', raw: 'data/boamp-raw.json.gz', reproduce: 'python tools/import-boamp-sample.py --offline', collected: 'All 8,386 BOAMP award notices published February–April 2025; 3,000 unambiguous lots kept by SHA-256 order of their identifier. The two Mauges lots and eight CRC audit dossiers are documented by hand.' }, note: '3,010 records: 3,000 BOAMP lots sampled from February–April 2025 publications, two Mauges lots and eight documented CRC dossiers. Some findings concern sets of orders, not an individual award. A finding does not extend to a municipality’s other purchases. This sample does not allow an exhaustive competition history to be computed.' },
    colombia: { path: 'data/colombia-secop2.json', coverage: 'data/colombia-secop2-coverage.json', sources: { publisher: 'Colombia Compra Eficiente — SECOP II, via datos.gov.co', links: [['Dataset page · datos.gov.co (jbjy-vk9h)', 'https://www.datos.gov.co/Gastos-Gubernamentales/SECOP-II-Contratos-Electr-nicos/jbjy-vk9h'], ['API used', 'https://www.datos.gov.co/resource/jbjy-vk9h.json'], ['SECOP II public search', 'https://community.secop.gov.co/Public/Tendering/ContractNoticeManagement/Index']], licence: 'CC BY-SA 4.0', raw: 'data/colombia-secop2/raw/', reproduce: 'python tools/import-colombia-secop2.py --offline', collected: 'Every SECOP II contract of three buyers announced before download, signed 2024-09-01 → 2026-09-01.' }, note: 'SECOP II pilot · Colombia · three buyers announced before download · signatures 2024-09 → 2026-09: 7,560 contracts (Ministerio de Educación Nacional 2,618, national; Gobernación de Caldas 3,696, departmental; Alcaldía Local de Usaquén 1,246, municipal-local). Fields kept verbatim in Spanish; amounts in COP, never converted. Jurisdiction-specific indicators (docs/score-colombia.md): declared absence of supplier plurality or manifest urgency, repetition of such awards, concentration within buyer and contract type, declared duration ≥ 36 months. The bare direct-family modality (≈82 % of the cohort) and ordinary justifications add no points; amounts sort only. Licence CC BY-SA 4.0 (Colombia Compra Eficiente); not exhaustive of each buyer’s procurement; no offers table was imported, so no offer-count indicator exists.' },
    paraguay: { path: 'data/paraguay-dncp.json', coverage: 'data/paraguay-dncp-coverage.json', sources: { publisher: 'Dirección Nacional de Contrataciones Públicas (DNCP), Paraguay', links: [['Public procurement portal · contrataciones.gov.py', 'https://www.contrataciones.gov.py/'], ['Open data and API documentation', 'https://www.contrataciones.gov.py/datos/api/v3/doc/'], ['Legal notice and licence (the OCDS packages cite /datos/legal, which now returns 404)', 'https://www.contrataciones.gov.py/datos/aviso-legal']], licence: 'CC BY 4.0', raw: 'data/paraguay-dncp/raw/', reproduce: 'python tools/import-paraguay-dncp.py --cohort fernando --offline', collected: 'Every process of the buyer whose call was published 2024-09-01 → 2025-09-01, then each full OCDS record by OCID.' }, note: 'Paraguay · DNCP OCDS pilot · Municipalidad de Fernando de la Mora only. Calls published 2024-09-01 → 2025-09-01: 88 process records, 84 linked contract entries retained; 2 contract entries excluded, 4 other processes without eligible contracts. PYG, no conversion. Source contract.period.startDate is not a signature date; no published dateSigned on retained rows. Raw OCDS records retained, 80 entries link a document typed contractSigned, contents not independently reviewed. Paraguayan checks only (docs/score-paraguay.md), fixed after reading this pilot’s field distributions: single tenderer in a competitive procedure, award by exception (CVE), their repetition per supplier, concentration by category, amount increase > 20 %. The 2 excluded entries are the separate records of 2 amount amendments (+20.0 %, +19.99 %), kept on their parent contracts. No French/Colombian rules applied. Not a national sample or payment audit.' },
    paraguay3: { path: 'data/paraguay-dncp-3buyers.json', coverage: 'data/paraguay-dncp-3buyers-coverage.json', sources: { publisher: 'Dirección Nacional de Contrataciones Públicas (DNCP), Paraguay', links: [['Public procurement portal · contrataciones.gov.py', 'https://www.contrataciones.gov.py/'], ['Open data and API documentation', 'https://www.contrataciones.gov.py/datos/api/v3/doc/'], ['Legal notice and licence (the OCDS packages cite /datos/legal, which now returns 404)', 'https://www.contrataciones.gov.py/datos/aviso-legal']], licence: 'CC BY 4.0', raw: 'data/paraguay-dncp-3buyers/raw/ (records gzipped, exact response bytes)', reproduce: 'python tools/import-paraguay-dncp.py --cohort 3buyers --offline', collected: 'Every process of three buyers announced before download (one per government level) whose call was published 2024-09-01 → 2026-09-01, then each full OCDS record by OCID.' }, note: 'Paraguay · DNCP OCDS · three buyers announced before download, one per level: Ministerio de Obras Públicas y Comunicaciones (national, 168 contracts), Gobierno Departamental de Central (departmental, 88), Municipalidad de Asunción (municipal, 37). Calls published 2024-09-01 → 2026-09-01: 339 processes, 293 linked contract entries retained; excluded: 12 amendment entries (kept on their parent contract), 21 budget-only entries, 1 multi-buyer process. PYG, no conversion. Paraguayan checks only (docs/score-paraguay.md), fixed before this cohort was downloaded: single tenderer in a competitive procedure, award by exception (CVE), their repetition per supplier, concentration by category, amount increase > 20 %. 92 multi-lot awards cannot be checked for a single tenderer (no per-lot count published). Not a national sample or payment audit.' },
    ukraine: { path: 'data/prozorro.json', coverage: 'data/prozorro-coverage.json', sources: { publisher: 'Prozorro (State enterprise Prozorro, Ministry of Economy of Ukraine)', links: [['Prozorro public portal', 'https://prozorro.gov.ua/'], ['Open-data reuse terms', 'https://prozorro.gov.ua/openprocurement'], ['Public API documentation', 'https://prozorro-api-docs.readthedocs.io/'], ['Public API used (official records)', 'https://public-api.prozorro.gov.ua/api/2.5/tenders']], licence: 'Prozorro open-data reuse terms: redistribution, including commercial reuse, permitted with source attribution; no named licence for API records', raw: 'data/prozorro/raw/ (official records gzipped, exact response bytes)', reproduce: 'python tools/import-prozorro.py --offline', collected: 'Search-discovered tenders for three preselected buyers, created 2024-09-01 → 2026-09-01, checked against the official API buyer field. Search completeness is not established; see docs/ukraine-audit.md.' }, note: 'Ukraine · Prozorro · 526 tenders and 488 signed contracts (2024–2026), three buyers. Amounts remain in UAH, EUR or USD. Reporting records skip offer/direct-award checks; concentration is still assessed. Wartime rules allow exceptions and withheld publications. Open-data reuse requires source attribution.' },
    chile: { path: 'data/chile-mp.json', coverage: 'data/chile-mp-coverage.json', sources: { publisher: 'Dirección de Compras y Contratación Pública (ChileCompra) — Mercado Público', links: [['Mercado Público · buscador de licitaciones', 'https://www.mercadopublico.cl/Home/BusquedaLicitacion'], ['OCDS API used (tender and award releases)', 'https://api.mercadopublico.cl/APISOCDS/OCDS/listaOCDSAgnoMes/2025/03/0/10'], ['CC0 1.0 public-domain dedication', 'https://creativecommons.org/publicdomain/zero/1.0/']], licence: 'CC0 1.0 (declared in every release package)', raw: 'data/chile-mp/raw/ (monthly listings, prefix map, tender and award releases gzipped, exact response bytes)', reproduce: 'python tools/import-chilecompra.py --offline', collected: 'Every licitación of three purchasing units announced before download (one per level), listed 2024-09 → 2026-08, chosen from a map of all 4,582 purchasing-unit prefixes.' }, note: 'Chile · Mercado Público · three purchasing units announced before download: Ministerio de Obras Públicas (Dirección General de Aguas unit, national), Gobierno Regional del Maule (regional), I. Municipalidad de Puente Alto (municipal). Licitaciones listed 2024-09 → 2026-08: 844 tenders, 522 single-supplier awards. Licitaciones only: direct deals (trato directo) are purchase orders, not in this source. Amounts in CLP, never converted. Chilean checks (docs/score-chile.md): single tenderer, its repetition per supplier (RUT), concentration by UNSPSC segment. Tenderers counted per tender, not per line item. CC0 1.0.' },
    uk: { path: 'data/uk-fts.json', coverage: 'data/uk-fts-coverage.json', sources: { publisher: 'Find a Tender service (Cabinet Office, United Kingdom)', links: [['Find a Tender · search notices', 'https://www.find-tender.service.gov.uk/Search'], ['OCDS API used (release packages)', 'https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages'], ['Open Government Licence v3.0', 'https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/']], licence: 'Open Government Licence v3.0', raw: 'data/uk-fts/raw/ (compact award index and full notices, gzipped exact response bytes)', reproduce: 'python tools/import-find-a-tender.py --offline', collected: 'Every award notice of three buyer accounts announced before download (one per level), released 2024-09-01 → 2026-09-01, chosen from a compact index of all 33,457 award releases in the window.' }, note: 'United Kingdom · Find a Tender · three buyer accounts announced before download: Foreign, Commonwealth and Development Office (national), Lincolnshire County Council (regional), Milton Keynes Council (municipal). Award releases 2024-09-01 → 2026-09-01: 516 notices, 1,081 single-supplier awards. Above-threshold and Procurement Act notices only. Amounts as published (mostly GBP), never converted. UK checks (docs/score-uk.md): single offer per lot, awards without prior publication, their repetition per supplier, concentration by category. Supplier identity is the Find a Tender party id, which can split one company across ids: repetition can only be undercounted. Open Government Licence v3.0.' },
    portugal: { path: 'data/ted-portugal.json', coverage: 'data/ted-portugal-coverage.json', sources: { publisher: 'Publications Office of the European Union — TED', links: [['TED search · ted.europa.eu', 'https://ted.europa.eu/'], ['TED Search API documentation', 'https://docs.ted.europa.eu/api/latest/search.html'], ['TED legal notice (reuse authorised)', 'https://ted.europa.eu/en/legal-notice']], licence: 'Free reuse, commercial or not (Commission Decision 2011/833/EU)', raw: 'data/ted-portugal/raw/ (official eForms XML gzipped)', reproduce: 'python tools/import-ted-cohorts.py --cohort portugal --offline', collected: 'Every TED award notice (can-standard) of three buyers announced before download, published 2024-09-01 → 2026-09-01, matched by identifier and its spelling variants.' }, note: 'Portugal · TED award notices (above EU thresholds only) · Infraestruturas de Portugal (national), Comunidade Intermunicipal do Cávado (regional), Município de Lisboa (municipal). Published 2024-09-01 → 2026-09-01: 442 notices, 493 awarded lots; 137 multi-winner framework results excluded (no single holder). The Cávado notices link no winning tender, so the regional level contributes almost nothing. EUR. EU eForms checks (docs/score-ted.md). Not a picture of Portuguese procurement: national below-threshold purchases are not in TED.' },
    czechia: { path: 'data/ted-czechia.json', coverage: 'data/ted-czechia-coverage.json', sources: { publisher: 'Publications Office of the European Union — TED', links: [['TED search · ted.europa.eu', 'https://ted.europa.eu/'], ['TED Search API documentation', 'https://docs.ted.europa.eu/api/latest/search.html'], ['TED legal notice (reuse authorised)', 'https://ted.europa.eu/en/legal-notice']], licence: 'Free reuse, commercial or not (Commission Decision 2011/833/EU)', raw: 'data/ted-czechia/raw/ (official eForms XML gzipped)', reproduce: 'python tools/import-ted-cohorts.py --cohort czechia --offline', collected: 'Every TED award notice (can-standard) of three buyers announced before download, published 2024-09-01 → 2026-09-01, matched by IČO and its spelling variants.' }, note: 'Czechia · TED award notices (above EU thresholds only) · Ministry of Finance (national), Moravian-Silesian Region (regional), City of Ostrava with its districts, which share its IČO (municipal). Published 2024-09-01 → 2026-09-01: 661 notices, 674 awarded lots; 122 results with several or no winning references excluded. CZK and EUR as published. EU eForms checks (docs/score-ted.md). Not a picture of Czech procurement: below-threshold purchases are published nationally, not in TED.' },
    romania: { path: 'data/ted-romania.json', coverage: 'data/ted-romania-coverage.json', sources: { publisher: 'Publications Office of the European Union — TED', links: [['TED search · ted.europa.eu', 'https://ted.europa.eu/'], ['TED Search API documentation', 'https://docs.ted.europa.eu/api/latest/search.html'], ['TED legal notice (reuse authorised)', 'https://ted.europa.eu/en/legal-notice']], licence: 'Free reuse, commercial or not (Commission Decision 2011/833/EU)', raw: 'data/ted-romania/raw/ (official eForms XML gzipped)', reproduce: 'python tools/import-ted-cohorts.py --cohort romania --offline', collected: 'Every TED award notice (can-standard) of three buyers announced before download, published 2024-09-01 → 2026-09-01, matched by identifier and its spelling variants.' }, note: 'Romania · TED award notices (above EU thresholds only) · Ministerul Finanțelor (national), Județul Cluj (regional), Municipiul Cluj-Napoca (municipal). Published 2024-09-01 → 2026-09-01: 299 notices, 356 awarded lots; 289 multi-winner framework results excluded. RON and EUR as published, never converted. EU eForms checks (docs/score-ted.md). Not a picture of Romanian procurement: SEAP/SICAP below-threshold purchases are not in TED.' },
    all: { combined: true, path: null, coverage: null, note: 'All countries · every dataset listed together. Each dataset is prepared on its own (repetition and concentration never cross cohorts), then its rows are shown side by side with their country. Amounts stay in their own currency: never converted or summed, and the amount sort groups by currency. Dates have each source\u2019s meaning (signature, award or publication). Checks share one catalogue (docs/indicators.md) but eligibility and thresholds follow each jurisdiction\u2019s law and data. Open a row for its sources.' },
  };
  let datasetMetadata = {};
  function renderDatasetDates(key) {
    const dates = document.querySelector('#dataset-dates');
    const notes = document.querySelector('#dataset-date-notes');
    const metadata = globalThis.DatasetMetadata.formatEntries(key, datasetMetadata);
    dates.replaceChildren(); notes.replaceChildren();
    for (const field of metadata.fields) {
      dates.append(element('dt', field.label), element('dd', field.value));
    }
    for (const note of metadata.notes) notes.append(element('li', note));
    notes.hidden = metadata.notes.length === 0;
  }
  // Dataset-level provenance, so anyone can repeat the collection or check a row at its source.
  function renderSources(selected) {
    const panel = document.querySelector('#dataset-sources');
    const body = document.querySelector('#sources-body');
    body.replaceChildren();
    panel.hidden = !selected.sources;
    if (!selected.sources) return;
    const s = selected.sources;
    body.append(element('p', `Publisher: ${s.publisher}. Licence: ${s.licence}.`), element('p', `What was collected: ${s.collected}`));
    const list = element('ul');
    for (const [label, url] of s.links) { const item = element('li'); item.append(sourceLink(url, label)); list.append(item); }
    const coverage = element('li'); const coverageLink = element('a', 'Exact queries, retrieval times, counts and exclusions (coverage JSON)'); coverageLink.href = selected.coverage; coverage.append(coverageLink); list.append(coverage);
    body.append(list);
    body.append(element('p', s.raw ? `Raw source responses are kept unmodified in ${s.raw} in the project repository. To rebuild this dataset from them: ${s.reproduce}` : 'Raw source responses for this older cohort are not kept in the repository; use the queries in the coverage file to fetch them again.'));
    body.append(element('p', 'To check one contract: open its row and follow “Verify it yourself”. Official pages come first; if a link has moved, search the portal for the identifiers listed there.'));
  }
  const provenance = { verified: 'Documented · public source', unverified: 'To verify · research lead', synthetic: 'Fictional · pedagogical comparison' };
  const uiLocale = typeof i18nLocale === 'function' ? i18nLocale() : 'en-IE';
  const money = new Intl.NumberFormat(uiLocale, { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 });
  const moneyCop = new Intl.NumberFormat(uiLocale, { style: 'currency', currency: 'COP', maximumFractionDigits: 0 });
  const moneyPyg = new Intl.NumberFormat(uiLocale, { style: 'currency', currency: 'PYG', maximumFractionDigits: 0 });
  const otherMoney = new Map();
  // Local files may declare any ISO currency; amounts are never converted.
  const moneyFor = c => {
    if (!recordCurrency(c)) return { format: amount => `${new Intl.NumberFormat('en-IE').format(amount)} (currency unknown)` };
    if (!c.assessmentMode && c.dataFamily === 'secop2') return moneyCop;
    if (!c.assessmentMode && c.dataFamily === 'dncp') return moneyPyg;
    if (!/^[A-Z]{3}$/.test(c.currency || '') || c.currency === 'EUR') return money;
    if (!otherMoney.has(c.currency)) otherMoney.set(c.currency, new Intl.NumberFormat(uiLocale, { style: 'currency', currency: c.currency, maximumFractionDigits: 2 }));
    return otherMoney.get(c.currency);
  };
  const dateFormat = new Intl.DateTimeFormat(uiLocale === 'en-IE' ? 'en-GB' : uiLocale, { timeZone: 'UTC', day: 'numeric', month: 'short', year: 'numeric' });
  let contracts = [];
  // Notes repeated on many rows describe the dataset, not a record: shown once under “Scope and limits”.
  let sharedNotes = new Set();
  const fieldNotes = document.querySelector('#field-notes');
  let loaded = false;
  let loadVersion = 0;
  let page = 0;
  let pageSize = 50;
  let pageRowsForCopy = [];
  let totalResultsForCopy = 0;
  let rowsForExport = [];
  let usingLocalFile = false;
  let localFileName = '';
  let localFileIdentity = '';
  const defaultDataset = datasetSelect.options[0].value;
  const initialView = hashToViewState(location.hash);
  if (datasets[initialView.dataset]) datasetSelect.value = initialView.dataset;
  let pendingView = location.hash ? initialView : null;
  // Options sit under their country's group, so the full name joins both.
  const datasetLabel = () => { const option = datasetSelect.selectedOptions[0]; return `${option.parentElement.label} · ${option.textContent.trim()}`; };
  let currentDatasetLabel = datasetLabel();
  const pageSizeSelect = document.querySelector('#page-size');
  const copyPage = document.querySelector('#copy-page');
  const copyStatus = document.querySelector('#copy-status');
  const exportCsv = document.querySelector('#export-csv');
  const exportJson = document.querySelector('#export-json');
  const pagination = document.querySelector('#pagination');
  const previous = document.querySelector('#previous');
  const next = document.querySelector('#next');
  const viewport = document.querySelector('.table-wrap');
  const projectPanel = document.querySelector('#project-panel');
  const detailPanel = document.querySelector('#detail-panel');
  const detailBody = document.querySelector('#detail-body');
  const filterPanel = document.querySelector('#advanced-filters');
  let projectCatalog = new Map();
  // The record shown in the side panel; kept in the link as open=<id>.
  let openId = '';
  let pendingOpen = '';
  let visibleRows = [];
  let signalCounts = new Map();
  const indicatorLabels = new Map([...controls.indicator.options].map(option => [option.value, option.textContent]));
  for (const [id, label] of Object.entries(INDICATOR_KINDS)) if (!indicatorLabels.has(id)) indicatorLabels.set(id, label);

  // Filters: a collapsible sidebar on wide screens (choice remembered in this browser), folded on narrow ones.
  const FILTERS_STORE = 'contract-signals-filters';
  const wideScreen = matchMedia('(min-width: 1001px)');
  const sidebarWanted = () => { try { return localStorage.getItem(FILTERS_STORE) === 'open'; } catch { return false; } };
  const filterToggleLabel = filterPanel.querySelector('.filter-toggle-label');
  const syncFilterLabel = () => { filterToggleLabel.textContent = filterPanel.open ? 'Hide advanced filters' : 'Advanced filters'; };
  filterPanel.open = wideScreen.matches && sidebarWanted();
  syncFilterLabel();
  wideScreen.addEventListener('change', () => { filterPanel.open = wideScreen.matches && sidebarWanted(); syncFilterLabel(); });
  filterPanel.addEventListener('toggle', () => {
    syncFilterLabel();
    if (wideScreen.matches) try { localStorage.setItem(FILTERS_STORE, filterPanel.open ? 'open' : 'closed'); } catch { /* Storage blocked: the choice lasts for this visit. */ }
  });

  // Colour theme: automatic (system), light or dark, remembered in this browser only.
  const THEME_STORE = 'contract-signals-theme';
  const themeButton = document.querySelector('#theme-toggle');
  const themeNames = { auto: 'Auto', light: 'Light', dark: 'Dark' };
  let theme = ['light', 'dark'].includes(document.documentElement.dataset.theme) ? document.documentElement.dataset.theme : 'auto';
  function applyTheme() {
    if (theme === 'auto') delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = theme;
    document.querySelector('#theme-label').textContent = themeNames[theme];
    themeButton.setAttribute('aria-label', `Colour theme: ${themeNames[theme].toLowerCase()}. Change theme.`);
    themeButton.title = `Colour theme: ${themeNames[theme].toLowerCase()} · click to change`;
  }
  applyTheme();
  themeButton.addEventListener('click', () => {
    theme = theme === 'auto' ? 'light' : theme === 'light' ? 'dark' : 'auto';
    applyTheme();
    try { if (theme === 'auto') localStorage.removeItem(THEME_STORE); else localStorage.setItem(THEME_STORE, theme); } catch { /* Storage blocked: the choice lasts for this visit. */ }
  });

  // Review marks and notes: a reviewer's own working notes, stored only in this browser.
  // They never change the index and are not part of the shareable link.
  const REVIEW_STORE = 'contract-signals-review-v1';
  const REVIEW_STATUSES = { 'follow-up': 'Follow up', referred: 'Referred', reviewed: 'Reviewed' };
  let reviews = {};
  let reviewStorageWorks = true;
  try { const saved = JSON.parse(localStorage.getItem(REVIEW_STORE) || '{}'); if (saved && typeof saved === 'object' && !Array.isArray(saved)) reviews = saved; } catch { reviewStorageWorks = false; }
  function saveReviews() {
    try { localStorage.setItem(REVIEW_STORE, JSON.stringify(reviews)); reviewStorageWorks = true; } catch { reviewStorageWorks = false; }
  }
  const reviewScope = () => usingLocalFile ? `local:${localFileIdentity}` : datasetSelect.value;
  const reviewKey = c => `${reviewScope()}|${c.id}`;
  const reviewOf = c => reviews[reviewKey(c)] || null;
  function setReview(c, patch) {
    const key = reviewKey(c);
    const entry = { ...(reviews[key] || {}), ...patch, updatedAt: new Date().toISOString() };
    if (!entry.status && !entry.note?.trim()) delete reviews[key]; else reviews[key] = entry;
    saveReviews();
  }
  function reviewMatch(c) {
    const wanted = controls.review.value;
    if (!wanted) return true;
    const mark = reviewOf(c)?.status || '';
    return wanted === '@none' ? !mark : wanted === '@any' ? Boolean(mark) : mark === wanted;
  }
  function reviewCounts() {
    const prefix = reviewScope() + '|';
    const counts = { total: 0 };
    for (const [key, entry] of Object.entries(reviews)) if (key.startsWith(prefix) && entry.status) { counts.total++; counts[entry.status] = (counts[entry.status] || 0) + 1; }
    return counts;
  }
  function renderReviewSummary() {
    const counts = reviewCounts();
    document.querySelector('#review-summary').textContent = !reviewStorageWorks ? 'This browser blocks storage: marks last until the page is closed.' :
      counts.total ? `In this dataset: ${Object.entries(REVIEW_STATUSES).map(([id, label]) => `${counts[id] || 0} ${label.toLowerCase()}`).join(' · ')}.` : 'None in this dataset yet.';
  }

  function fillSelect(select, options) {
    const previousValue = select.value;
    select.replaceChildren(...options.map(([value, label]) => { const option = element('option', label); option.value = value; return option; }));
    select.value = options.some(([value]) => value === previousValue) ? previousValue : '';
  }
  function applyView(view) {
    for (const [, id, fallback] of VIEW_FIELDS) {
      if (id === 'open-record') { pendingOpen = view[id]; continue; }
      controls[id].value = view[id];
      if (controls[id].tagName === 'SELECT' && controls[id].selectedIndex === -1) controls[id].value = fallback;
    }
    for (const id of VIEW_FLAGS) controls[id].checked = view[id];
    pageSize = view.pageSize;
    pageSizeSelect.value = String(pageSize);
    page = view.page - 1;
  }
  function currentView() {
    const view = { dataset: usingLocalFile || datasetSelect.value === defaultDataset ? '' : datasetSelect.value, page: page + 1, pageSize };
    for (const [, id] of VIEW_FIELDS) view[id] = id === 'open-record' ? openId : controls[id].value;
    for (const id of VIEW_FLAGS) view[id] = controls[id].checked;
    return view;
  }
  // replaceState keeps the link current without adding a history entry per keystroke.
  function writeView() {
    const hash = viewStateToHash(currentView());
    if (hash === location.hash) return;
    try { history.replaceState(null, '', hash || location.pathname + location.search); } catch { /* Some file:// contexts refuse history updates. */ }
  }
  const FILTER_VALUES = ['minimum', 'sector', 'group-by', 'project', 'assessment', 'min-score', 'indicator', 'notice-context', 'legal', 'review'];
  function clearFilters() {
    for (const id of FILTER_VALUES) controls[id].value = '';
    controls['min-score'].value = '0';
    for (const id of VIEW_FLAGS) controls[id].checked = false;
  }
  function refresh() { page = 0; render(); viewport.scrollTop = 0; }
  function showProject(id) {
    controls.search.value = '';
    clearFilters();
    controls.project.value = id;
    controls['group-by'].value = id ? 'project' : '';
    refresh();
  }
  let activeProfile = null;
  const profilePanel = document.querySelector('#profile-panel');
  function openProfile(c, role) {
    const key = profileKey(c, role);
    activeProfile = key ? buildProfile(contracts, role, key) : null;
    page = 0;
    render();
    profilePanel.scrollIntoView({ block: 'start' });
  }
  function renderProfilePanel() {
    profilePanel.replaceChildren();
    profilePanel.hidden = !activeProfile;
    if (!activeProfile) return;
    const p = activeProfile;
    const pct = (a, b) => b ? `${Math.round(a / b * 100)} %` : '—';
    profilePanel.append(element('h2', `${p.role === 'buyer' ? 'Buyer' : 'Supplier'} profile · ${p.name || '—'}`),
      element('p', `${p.contracts} contract(s)${p.country ? ` · ${p.country}` : ''}${p.firstDate ? ` · ${p.firstDate} → ${p.lastDate}` : ''} · ${p.assessed} assessed · ${p.flagged} with a signal (${pct(p.flagged, p.assessed)}). The table below now shows only these contracts. Compared with the ${p.scopeSize} records of the same dataset; amounts are never summed.`));
    const table = element('table', null, 'profile-table');
    const head = element('tr');
    head.append(element('th', 'Indicator'), element('th', `This ${p.role}`), element('th', 'Whole dataset'));
    table.append(head);
    for (const kind of Object.keys(INDICATOR_KINDS)) {
      const mine = p.kinds[kind], all = p.baseline[kind];
      if (!mine && !all) continue;
      const tr = element('tr');
      tr.append(element('td', INDICATOR_KINDS[kind]), element('td', mine ? `${mine.signals} / ${mine.evaluated} evaluated (${pct(mine.signals, mine.evaluated)})` : 'not evaluated'),
        element('td', all ? `${pct(all.signals, all.evaluated)} of ${all.evaluated} evaluated` : '—'));
      table.append(tr);
    }
    profilePanel.append(table);
    profilePanel.append(element('h3', p.role === 'buyer' ? 'Main suppliers' : 'Main buyers'));
    const list = element('ol');
    for (const cp of p.counterparts) list.append(element('li', `${cp.name} · ${cp.contracts} contract(s), ${cp.flagged} with a signal`));
    profilePanel.append(list);
    const money = Object.entries(p.currencies).map(([cur, v]) => `${v.contracts} with an amount in ${cur} (largest ${v.largest.toLocaleString('en-IE')} ${cur})`).join('; ');
    if (money) profilePanel.append(element('p', `Declared amounts: ${money}. Not summed: declared amounts are not payments, and ceilings and amendments would double count.`));
    profilePanel.append(element('p', 'A profile describes published declarations and heuristic signals only; a high rate is a reason to read the sources, not a finding.'));
    const close = element('button', 'Close profile and show all contracts');
    close.type = 'button';
    close.addEventListener('click', () => { activeProfile = null; page = 0; render(); });
    profilePanel.append(close);
  }
  function renderProjectPanel() {
    projectPanel.replaceChildren();
    const project = projectCatalog.get(controls.project.value);
    projectPanel.hidden = !project;
    if (!project) return;
    projectPanel.append(element('h2', project.title), element('p', project.basis));
    projectPanel.append(sourceLink(project.source, 'Public reference notice of the dossier'));
    const list = element('ol', null, 'evidence-list');
    (project.evidence || []).forEach(evidence => {
      const item = element('li');
      item.append(sourceLink(evidence.source, `${evidence.date} — ${evidence.label}`), element('span', ` · ${evidence.type}. ${evidence.description}`));
      list.append(item);
    });
    projectPanel.append(list, element('p', 'These documentary elements earn no additional points and do not constitute an official finding. No project amount or score is summed.'));
    const clear = element('button', 'Back to all records', 'clear-group');
    clear.type = 'button';
    clear.addEventListener('click', () => showProject(''));
    projectPanel.append(clear);
  }

  // Indicator list: only the checks this dataset runs, most frequent first, each with its count.
  function computeOverview() {
    const officialCount = contracts.filter(c => c.officialFinding === true).length;
    signalCounts = new Map();
    const present = new Set();
    // Counted per shared indicator kind, the value the filter matches (one row per kind).
    for (const c of contracts) {
      const kinds = new Set();
      for (const r of getAssessment(c).checks) {
        const kind = indicatorKind(r.id);
        if (!kind) continue;
        present.add(kind);
        if (r.status === 'signal') kinds.add(kind);
      }
      for (const kind of kinds) signalCounts.set(kind, (signalCounts.get(kind) || 0) + 1);
    }
    if (officialCount) { present.add('official-finding'); signalCounts.set('official-finding', officialCount); }
    const options = [...indicatorLabels].filter(([id]) => id && present.has(id)).sort((a, b) => (signalCounts.get(b[0]) || 0) - (signalCounts.get(a[0]) || 0));
    const tr = typeof i18nTranslate === 'function' ? i18nTranslate : text => text;
    fillSelect(controls.indicator, [['', 'All indicators'], ...options.map(([id, label]) => [id, `${tr(label)} · ${signalCounts.get(id) || 0}`])]);
  }
  // Full-width rows must span only the visible columns: on phones six columns are hidden,
  // and a colspan of 9 would create phantom columns that squeeze the subject.
  function visibleColumnCount() {
    return [...document.querySelectorAll('.main-table > thead th')].filter(th => getComputedStyle(th).display !== 'none').length || 9;
  }
  matchMedia('(max-width: 760px)').addEventListener('change', () => { if (loaded) render(); });
  const formatDate = c => c.date ? dateFormat.format(new Date(c.date)) : c.noticeEvidence ? c.publicationDate || '—' : '—';
  const formatAmount = c => c.amount == null ? '—' : ({ 'at-least': '≥ ', 'more-than': '> ', approximate: '≈ ' }[c.amountQualifier] || '') + moneyFor(c).format(c.amount);
  function scoreChip(c) {
    const breakdown = getScoreBreakdown(c);
    const level = scoreLevel(breakdown.score, hasIncompleteData(c));
    const chip = element('span', breakdown.score == null ? 'Not assessed' : `${breakdown.score} / 100`, `score-chip level-${level.id}`);
    chip.title = `${level.label} — editorial index, not a probability nor legal gravity.`;
    return chip;
  }
  function render() {
    syncSortHeaders();
    if (!loaded) return;
    const minimum = Math.max(0, Number(controls.minimum.value) || 0);
    const pool = activeProfile ? contracts.filter(c => activeProfile.ids.has(c.id)) : contracts;
    const filtered = selectContracts(controls.review.value ? pool.filter(reviewMatch) : pool, { search: controls.search.value, minimum, minScore: Number(controls['min-score'].value) || 0, flagged: controls.flagged.checked, official: controls.official.checked, adjudicated: controls.adjudicated.checked, investigation: controls.investigation.checked, indicator: controls.indicator.value, legal: controls.legal.value, noticeContext: controls['notice-context'].value, assessment: controls.assessment.value, sector: controls.sector.value, project: controls.project.value, sort: controls.sort.value });
    const arrangement = arrangeGroups(filtered, controls['group-by'].value);
    const visible = arrangement.rows;
    visibleRows = visible;
    renderProjectPanel();
    renderProfilePanel();
    const pageCount = Math.max(1, Math.ceil(visible.length / pageSize));
    page = Math.min(page, pageCount - 1);
    const pageRows = visible.slice(page * pageSize, (page + 1) * pageSize);
    pageRowsForCopy = pageRows;
    totalResultsForCopy = visible.length;
    rowsForExport = visible;
    const fragment = document.createDocumentFragment();
    pageRows.forEach((c, index) => {
      const indicators = getIndicators(c);
      if (controls['group-by'].value) {
        const info = groupInfo(c, controls['group-by'].value);
        const preceding = visible[page * pageSize + index - 1];
        if (index === 0 || groupInfo(preceding, controls['group-by'].value).key !== info.key) {
          const group = arrangement.groups.get(info.key);
          const header = element('tr', null, 'group-row');
          const headerCell = element('td', `${group.label} · ${group.contracts.length} filtered result(s)${index === 0 && preceding && groupInfo(preceding, controls['group-by'].value).key === info.key ? ' · continued' : ''}`);
          headerCell.colSpan = visibleColumnCount();
          if (controls['group-by'].value === 'project' && c.project) {
            const link = element('button', 'Open the dossier and its sources', 'group-link');
            link.type = 'button';
            link.addEventListener('click', () => showProject(c.project.id));
            headerCell.append(element('span', ' · '), link);
          }
          header.append(headerCell);
          fragment.append(header);
        }
      }
      const row = element('tr', null, 'contract-row');
      row.dataset.id = c.id;
      const names = supplierNames(c);
      const supplierCell = element('td', names.length ? names.join(' / ') : c.supplier || '—');
      if (names.length && c.supplier) supplierCell.append(element('small', c.supplier, 'provenance'));
      const dateCell = element('td', formatDate(c));
      if (c.noticeEvidence) dateCell.append(element('small', 'BOAMP publication', 'provenance'));
      if (c.dataFamily === 'dncp') dateCell.append(element('small', 'Contract-period start · not signature', 'provenance'));
      if (c.datasetCountry) dateCell.append(element('small', c.datasetCountry, 'provenance country'));
      row.append(dateCell, element('td', c.buyer), supplierCell);
      const objectCell = element('td');
      const button = element('button', c.description, 'row-toggle');
      button.type = 'button';
      button.setAttribute('aria-expanded', String(openId === c.id));
      button.setAttribute('aria-controls', 'detail-panel');
      button.title = `${c.description} — open details, evidence and sources`;
      objectCell.append(button, element('small', c.buyer, 'mobile-buyer'));
      const mark = reviewOf(c)?.status;
      if (mark) objectCell.append(element('span', REVIEW_STATUSES[mark], `review-tag review-${mark}`));
      if (c.dataStatus !== 'verified') objectCell.append(element('small', provenance[c.dataStatus], 'provenance'));
      if (c.project) {
        const projectLink = element('button', `Project: ${c.project.title}`, 'group-link');
        projectLink.type = 'button';
        projectLink.addEventListener('click', event => { event.stopPropagation(); showProject(c.project.id); });
        objectCell.append(element('br'), projectLink);
      }
      if (c.noticeEvidence) objectCell.append(element('small', `Notice ${c.noticeId} · ${c.lotId || 'unknown lot'} · local ref. ${c.noticeEvidence.lotReference || '—'}`, 'provenance'));
      const legalContext = getLegalContext(c);
      if (legalContext.length) objectCell.append(element('small', `Context · ${[...new Set(legalContext.map(item => item.article))].join(', ')} cited · no points added`, 'provenance'));
      if (c.initialConflicts?.length || c.identityAmbiguous) objectCell.append(element('small', 'Ambiguous identifier / versions · calculations excluded', 'provenance'));
      if (c.modificationConflicts?.length) objectCell.append(element('small', 'Conflicting modification versions', 'provenance'));
      if (c.officialFinding === true) objectCell.append(element('small', 'Official audit finding · not a conviction', 'provenance tone-official'));
      if (hasReportedInvestigation(c)) objectCell.append(element('small', 'Investigation reported at the time · current status unknown', 'provenance'));
      if (hasAdjudicatedCorruption(c)) objectCell.append(element('small', 'Final judgment linked to this contract', 'provenance'));
      const sector = getSector(c);
      const sectorCell = element('td', sector.label);
      sectorCell.append(element('small', c.cpv || 'unknown CPV', 'provenance'));
      row.append(objectCell, sectorCell, element('td', formatAmount(c), 'numeric'), element('td', c.offers ?? '—', 'numeric'));
      const badges = element('td');
      // Every signal is shown, heaviest first. Within a family only the
      // heaviest counts; the others are marked as not added to the index.
      const counted = new Set();
      const ordered = [...indicators].sort((a, b) => b.weight - a.weight);
      for (const indicator of ordered) {
        const counts = !counted.has(indicator.family);
        counted.add(indicator.family);
        const familyName = indicator.family === 'competition' ? 'competition' : indicator.family === 'transparency' ? 'transparency' : 'execution/duration';
        const badge = element('span', KIND_SHORT[indicator.kind] || indicator.kindLabel, `badge severity-${indicator.severity}${counts ? '' : ' not-counted'}`);
        badge.title = `${indicator.label} (this jurisdiction's check). Raw weight ${indicator.weight}. ${counts ? `Counts for the ${familyName} family.` : `Not added: a heavier ${familyName} signal already counts.`} ${indicator.explanation}`;
        badges.append(badge);
      }
      for (const label of contextLabels(c)) {
        const badge = element('span', `Context: ${label.short}`, 'badge context');
        badge.title = `${label.long} Context outside the index: no points added or removed.`;
        badges.append(badge);
      }
      if (ordered.length) objectCell.append(element('small', `Signals: ${ordered.map(i => i.kindLabel).join(' · ')}`, 'mobile-signals'));
      for (const label of contextLabels(c)) objectCell.append(element('small', `Context: ${label.short} · no points`, 'mobile-signals context'));
      const breakdown = getScoreBreakdown(c);
      const assessment = breakdown.assessment;
      const scoreValue = breakdown.score;
      if (!indicators.length) badges.append(element('span', '—', 'muted'));
      const score = element('td', null, 'numeric');
      const coverageLabel = assessment.excludedReason ? 'Calculations excluded' : assessment.applicable ? `${assessment.signals} signal(s) · ${assessment.evaluated}/${assessment.applicable} known-applicable checks evaluated` : 'No check with established applicability';
      score.append(scoreChip(c));
      score.title = `${coverageLabel}. ${assessment.unknownApplicability} unknown applicability(ies). Open the row for details.`;
      score.setAttribute('aria-label', `${scoreValue == null ? 'Index not assessed.' : `Heuristic index: ${scoreValue} out of 100.`} ${coverageLabel}. ${assessment.unknownApplicability} unknown applicabilities.`);
      row.append(badges, score);
      button.addEventListener('click', event => { event.stopPropagation(); toggleDetail(c.id); });
      row.addEventListener('click', () => { if (!window.getSelection()?.toString()) toggleDetail(c.id); });
      fragment.append(row);
    });
    if (!visible.length) {
      const row = element('tr', null, 'empty-row');
      const cell = element('td', 'No result. Try lowering the minimum amount or changing the filters. ');
      cell.colSpan = visibleColumnCount();
      const reset = element('button', 'Reset filters and search', 'link-button');
      reset.type = 'button';
      reset.addEventListener('click', () => { controls.search.value = ''; clearFilters(); refresh(); });
      cell.append(reset);
      row.append(cell);
      fragment.append(row);
    }
    body.replaceChildren(fragment);
    const active = FILTER_VALUES.filter(id => controls[id].value && controls[id].value !== '0').length + VIEW_FLAGS.filter(id => controls[id].checked).length;
    document.querySelector('#advanced-count').textContent = active ? `· ${active} active` : '';
    document.querySelector('#clear-filters').disabled = !active;
    const signals = visible.filter(c => getIndicators(c).length).length;
    const unknown = visible.filter(c => getVigilanceScore(c) == null).length;
    status.textContent = `${visible.length} / ${contracts.length} results · ${signals} with a heuristic signal · ${unknown} not assessed`;
    pagination.hidden = false;
    copyPage.disabled = !pageRows.length;
    exportCsv.disabled = exportJson.disabled = !visible.length;
    previous.disabled = page === 0;
    next.disabled = page >= pageCount - 1;
    document.querySelector('#page-status').textContent = `Page ${page + 1} / ${pageCount} · ${pageSize} rows per page`;
    renderReviewSummary();
    markOpenRow();
    updateDetailPosition();
    writeView();
  }

  // Side panel with everything known about one record, organised for review.
  function detailSection(id, title) {
    const section = element('section', null, 'detail-section');
    section.id = `detail-${id}`;
    section.append(element('h3', title, 'section-title'));
    return section;
  }
  function renderDetail(c) {
    // Only what is specific to this record. Dataset-wide notes live in “Scope and limits”;
    // method text lives in “How to read · Method”.
    const indicators = getIndicators(c);
    const breakdown = getScoreBreakdown(c);
    const assessment = breakdown.assessment;
    const ids = c.supplierIds || [];

    const head = element('header', null, 'detail-head');
    const title = element('h2', c.description);
    title.id = 'detail-title';
    head.append(title);
    const facts = element('dl', null, 'detail-facts');
    const fact = (label, ...values) => {
      if (!values.length || values[0] == null || values[0] === '') return;
      const box = element('div'); box.append(element('dt', label));
      const dd = element('dd'); dd.append(...values); box.append(dd); facts.append(box);
    };
    const profileButton = role => {
      if (!profileKey(c, role)) return [];
      const button = element('button', 'Profile', 'link-button profile-link');
      button.type = 'button';
      button.title = role === 'buyer' ? 'All contracts of this buyer in the dataset' : 'All contracts of this supplier in the dataset';
      button.addEventListener('click', () => { closeDetail({ restoreFocus: false }); openProfile(c, role); });
      return [' · ', button];
    };
    fact('Buyer', c.buyer || '—', ...profileButton('buyer'));
    // Supplier: published or register name, its identifiers, and the register status if enriched.
    const names = supplierNames(c);
    const supplierName = names.length ? names.join(' / ') : c.supplier || 'not specified';
    const supplier = element('span');
    const protectedNames = Array.isArray(c.supplierProtectedNames) && Array.isArray(c.supplierNamesPublished) ? c.supplierProtectedNames : null;
    if (protectedNames?.some(Boolean)) {
      // Each protected name is shown only on request, one record at a time.
      c.supplierNamesPublished.forEach((published, index) => {
        if (index) supplier.append(' / ');
        const item = protectedNames[index];
        if (!item || typeof item.data !== 'string') { supplier.append(String(published)); return; }
        const label = element('span', String(published));
        const button = element('button', 'Show name', 'link-button profile-link');
        button.type = 'button';
        button.title = 'Published by the source register. Shown one record at a time; not in lists, search or exports.';
        button.addEventListener('click', async () => {
          button.disabled = true;
          button.textContent = 'Working…';
          try {
            label.setAttribute('data-no-i18n', '');
            label.textContent = `${await revealProtectedName(c.id, index, item.data)} (${item.code})`;
            button.remove();
          } catch (error) { button.textContent = 'Name unavailable'; button.title = error.message; }
        });
        supplier.append(label, ' ', button);
      });
    } else supplier.append(supplierName);
    const supplierIdText = ids.map(s => { const shown = displayIdentifier(s); return s.siren && !shown.includes(s.siren) ? `${shown} · SIREN ${s.siren}` : shown; }).join(' / ');
    if (supplierIdText && (names.length || !supplierIdText.includes(supplierName))) supplier.append(element('small', ` ${supplierIdText}`, 'muted'));
    for (const p of c.supplierProfiles || []) {
      const state = p.administrativeState === 'A' ? 'active' : p.administrativeState === 'C' ? 'ceased' : 'status unknown';
      const status = element('small', ' · ', 'muted');
      status.append(element('span', state), ' ', element('span', 'in the register on'), ` ${(p.retrievedAt || '').slice(0, 10)} `);
      supplier.append(status, sourceLink(p.source, 'Annuaire'));
    }
    if (!c.noticeEvidence || c.supplier) fact('Supplier', supplier, ...profileButton('supplier'));
    fact(c.dataFamily === 'dncp' ? 'Period start' : c.noticeEvidence ? 'Published' : 'Date', formatDate(c));
    if (!c.noticeEvidence || c.amount != null) fact('Amount', formatAmount(c));
    const offers = c.offers ?? (c.dataFamily === 'dncp' ? c.numberOfTenderers : null);
    if (!c.noticeEvidence || offers != null) fact('Offers', offers == null ? '—' : String(offers));
    const procedureKind = NATIONAL_FAMILIES[c.dataFamily] ? (c.procedureDirect === true ? 'without competition' : c.procedureDirect === false ? 'competitive' : 'not classified') : null;
    fact('Procedure', [c.procedure || '—', c.procedureCode].filter(Boolean).join(' · '), ...(procedureKind ? [' · ', element('span', procedureKind)] : []));
    if (c.durationMonths != null || c.durationOriginal) fact('Duration', ...(c.durationMonths != null ? [`${c.durationMonths} `, element('span', 'months')] : [c.durationOriginal]));
    fact('Index', scoreChip(c));
    head.append(facts);
    if (c.dataStatus && c.dataStatus !== 'verified') head.append(element('p', provenance[c.dataStatus] || c.dataStatus, 'detail-status'));

    // Reviewer's own mark and note.
    const review = element('div', null, 'review-box');
    const current = reviewOf(c) || {};
    const statusSelect = element('select');
    statusSelect.id = 'detail-review-status';
    statusSelect.setAttribute('aria-label', 'Your review');
    for (const [value, label] of [['', 'Not marked'], ...Object.entries(REVIEW_STATUSES)]) { const option = element('option', label); option.value = value; statusSelect.append(option); }
    statusSelect.value = current.status || '';
    const note = element('textarea');
    note.id = 'detail-review-note';
    note.rows = 1;
    note.maxLength = 10000;
    note.setAttribute('aria-label', 'Note');
    note.placeholder = typeof i18nTranslate === 'function' ? i18nTranslate('Note (stays in this browser)') : 'Note (stays in this browser)';
    note.value = current.note || '';
    const saved = element('span', '', 'field-help');
    saved.setAttribute('role', 'status');
    const savedText = () => reviewStorageWorks ? 'Saved' : 'Not saved: storage blocked';
    statusSelect.addEventListener('change', () => { setReview(c, { status: statusSelect.value || null }); saved.textContent = savedText(); render(); });
    let noteTimer = null;
    note.addEventListener('input', () => {
      clearTimeout(noteTimer);
      noteTimer = setTimeout(() => { setReview(c, { note: note.value }); saved.textContent = savedText(); }, 400);
    });
    review.append(statusSelect, note, saved);
    head.append(review);

    const sections = [];
    const line = (parent, text, ...nodes) => { const p = element('p', text); p.append(...nodes); parent.append(p); return p; };
    const aside = (parent, text) => { const p = element('p', text, 'muted'); parent.append(p); return p; };
    // “Label value · Label value”: labels are interface text, values stay as published.
    const pairs = (parent, items, className) => {
      const shown = items.filter(([, v]) => v != null && v !== '');
      if (!shown.length) return null;
      const p = element('p', null, className);
      shown.forEach(([label, value], i) => p.append(i ? ' · ' : '', element('span', label), ` ${value}`));
      parent.append(p);
      return p;
    };

    // 1. Signals: the triggered checks with this record's own facts.
    const why = detailSection('signals', 'Signals');
    if (assessment.excludedReason) line(why, assessment.excludedReason);
    if (indicators.length) {
      const triggered = element('ul', null, 'triggered-indicators');
      const counted = new Set();
      for (const signal of [...indicators].sort((a, b) => b.weight - a.weight)) {
        const counts = !counted.has(signal.family);
        counted.add(signal.family);
        const item = element('li', null, `severity-line severity-${signal.severity}`);
        const name = element('strong', signal.kindLabel);
        if (KIND_REFERENCES[signal.kind]) name.title = `Also known as ${KIND_REFERENCES[signal.kind]}`;
        item.append(name, element('span', ` · ${signal.weight} pts`, 'muted'), ...(counts ? [] : [element('span', ' · not added (same family)', 'muted')]), element('p', briefReason(signal.explanation)));
        triggered.append(item);
      }
      why.append(triggered);
    } else if (!assessment.excludedReason) line(why, breakdown.score == null ? 'Not assessed: no check could be evaluated.' : 'No threshold crossed in the evaluated checks.');
    if (breakdown.score != null) {
      const parts = [['competition', breakdown.competition], ['execution', breakdown.execution], ['transparency', breakdown.transparency]].filter(([, v]) => v > 0);
      const summary = element('p', null, 'muted');
      if (parts.length) {
        summary.append(element('span', 'Index'), ` ${breakdown.score} = `);
        parts.forEach(([k, v], i) => summary.append(i ? ' + ' : '', element('span', k), ` ${v}`));
        summary.append('. ');
      }
      summary.append(element('span', `${assessment.evaluated} of ${assessment.applicable} applicable checks evaluated.`));
      if (assessment.unknownApplicability) summary.append(' ', element('span', `${assessment.unknownApplicability} with unknown applicability.`));
      why.append(summary);
    }
    sections.push(why);

    // 2. Details published for this record (dataset-wide notes are left out).
    const record = detailSection('record', 'Details');
    const own = key => c[key] && !sharedNotes.has(c[key]) ? c[key] : null;
    pairs(record, [['Contract', c.contractId], ['Lot', c.lotId], ['CPV', c.cpv], ['Notice', c.noticeId], ['Published', c.publicationDate],
      ['Buyer SIRET', c.buyerSiret], ['Framework', c.frameworkId], ['Reference', c.contractId ? null : c.id]], 'muted');
    for (const key of ['dateNote', 'amountBasis', 'notes', 'identifierNote']) if (own(key)) line(record, own(key));
    if (c.findingScope === 'aggregate') line(record, 'Finding scope: a set of orders examined by the CRC, not one award.');
    pairs(record, [['Modalities', [c.executionModalities, c.techniques].filter(x => x && x !== 'Sans objet').join(' · ')], ['Project', c.project ? `${c.project.title}. ${c.project.basis}` : null]]);
    if (c.dataFamily === 'dncp') {
      pairs(record, [['OCID', c.ocid], ['Status', c.contractStatus || '—'], ['Call', c.callPublishedDate || '—'], ['Signed', c.signatureDate || '—']]);
      pairs(record, [['Lots', c.lotCount > 1 ? c.lotCount : null], ['Tender period (days)', c.tenderPeriodDays ?? '—'], ['Category', c.category || '—']]);
      if (c.amendments?.length) {
        const list = element('ul');
        for (const a of c.amendments) list.append(element('li', `${a.date || '—'} · ${a.description || '—'}${a.amount == null ? '' : ` · ${moneyPyg.format(a.amount)}`}`));
        record.append(element('h4', `Amendments (${c.amendments.length})`), list);
      }
    } else if (c.dataFamily === 'chile') {
      pairs(record, [['Tender', c.tenderCode]]);
      line(record, 'Offers are counted on the whole tender, not per item.');
    } else if (c.dataFamily === 'secop2') {
      pairs(record, [['Status', c.contractStatus || '—'], ['Type', c.contractType || '—'], ['Declared justification', c.procedureJustification]]);
      if (c.amountPaid != null || c.amountInvoiced != null) pairs(record, [['Paid', c.amountPaid == null ? '—' : moneyCop.format(c.amountPaid)], ['Invoiced', c.amountInvoiced == null ? '—' : moneyCop.format(c.amountInvoiced)]]);
    } else if (c.dataFamily === 'decp') {
      pairs(record, [['Price', [c.priceForm, c.priceType].filter(Boolean).join(' · ')]]);
      if (c.initialConflicts?.length) {
        line(record, `Conflicting initial versions (${c.initialConflicts.join(', ')}): no chronology inferred.`);
        const list = element('ul');
        (c.initialAlternatives || []).forEach((a, n) => list.append(element('li', `Variant ${n + 1}: ${a.amount == null ? 'amount unknown' : money.format(a.amount)}${c.cohortId === CITIES_COHORT ? ` · notified ${a.date || '—'} · ${a.procedure || '—'} · offers ${a.offers ?? '—'}` : ''}`)));
        record.append(list);
      }
      if (c.modificationConflicts?.length) line(record, `Conflicting modifications: ${c.modificationConflicts.map(m => `${m.id} (${m.fields.join(', ')})`).join('; ')}.`);
      if (c.history?.length > 1) {
        const table = element('table', null, 'history-table');
        const thead = element('thead'); const heading = element('tr');
        for (const label of ['Event', 'Notified', 'Published', 'Amount']) { const th = element('th', label); th.scope = 'col'; heading.append(th); }
        thead.append(heading);
        const rows = element('tbody');
        for (const event of c.history) {
          const tr = element('tr');
          tr.append(element('td', event.kind === 'initial' ? 'Initial' : `Change ${event.id || '—'}`), element('td', event.date || '—'), element('td', event.publicationDate || '—'), element('td', event.amount == null ? '—' : money.format(event.amount)));
          rows.append(tr);
        }
        table.append(thead, rows);
        const wrap = element('div', null, 'history-wrap'); wrap.append(table); record.append(wrap);
      }
    }
    if (c.noticeChange?.previousSource) { const p = element('p'); p.append(element('span', 'Correction: deadline'), ` ${c.noticeChange.oldDeadline} → ${c.noticeChange.newDeadline} (${c.noticeChange.extensionDays > 0 ? '+' : ''}${c.noticeChange.extensionDays} d) `, sourceLink(c.noticeChange.previousSource, 'Previous notice')); record.append(p); }
    if (c.linkedContract) {
      const linked = c.linkedContract;
      line(record, `Contract record (${linked.retrievedAt?.slice(0, 10) || 'date unknown'}): ${linked.contractStatus || 'status unknown'} · ${linked.publishedChangeCount == null ? 'changes not published' : `${linked.publishedChangeCount} change(s)`}${(linked.changes || []).map(x => ` · ${x.dateSigned || x.date || '—'} ${(x.rationaleTypes || []).join(', ')}`).join('')}. `, sourceLink(linked.url, 'Record'));
    }
    if (c.bidAttrition?.decisions?.length) {
      const list = element('ul');
      for (const d of c.bidAttrition.decisions) list.append(element('li', `${d.status}${d.qualified === false ? ' · unqualified' : ''}: ${[d.title, d.description].filter(Boolean).join(' — ') || '—'}`));
      record.append(element('h4', 'Bid decisions'), list);
    }
    if (c.noticeEvidence) renderNoticeEvidence(record, c);
    if (c.consultation) {
      const t = c.consultation;
      const list = element('ul');
      for (const n of [...t.notices, ...(t.matchedAwards || [])]) {
        const item = element('li');
        item.append(sourceLink(n.source, `${n.id} · ${n.kind}`), ` · ${n.publicationDate || '—'} · deadline ${n.deadline || '—'}${n.accelerated ? ' · accelerated' : ''}`);
        if (n.correctionText) item.append(element('p', n.correctionText));
        list.append(item);
      }
      const period = getBiddingPeriod(c);
      record.append(element('h4', 'Notices'), list);
      line(record, period.status === 'available' ? `Bidding period: ${period.days.toFixed(1)} days (upper bound).` : `Bidding period not assessable: ${period.reason}`);
      for (const reason of t.exclusions || []) line(record, reason);
    }
    if (record.children.length > 1) sections.push(record);

    // 3. Context that adds no points, one line each.
    const outside = detailSection('context', 'Context · no points');
    const software = softwareMaintenanceContext(c);
    if (software) line(outside, 'Single-vendor software maintenance: often routine; exclusivity not verified.');
    const publicContext = c.secop2PublicCounterparty;
    if (publicContext?.labelled) line(outside, publicContext.basis === 'declared-interadministrative' ? 'Public-to-public agreement (declared interadministrative; not verified).' : `Public-to-public agreement: counterparty of interadministrative contract ${publicContext.agreementContractId}.`);
    const legalContext = getLegalContext(c);
    for (const item of legalContext) {
      line(outside, `${item.article} cited: `, sourceLink(item.source, 'source'));
      outside.append(element('blockquote', item.excerpt));
    }
    if (c.directAward === true && !legalContext.length && c.dataFamily === 'decp') line(outside, 'No R2122 article cited in the published text.');
    if (c.officialFinding === true) line(outside, `Official audit finding${c.sourceReference ? `: ${c.sourceReference}` : ''}.`);
    for (const report of c.investigationReports || []) line(outside, `Reported investigation (${report.publisher}, ${report.reportedAt}): ${report.reportedFact} Status: ${report.currentStatus} `, sourceLink(report.sourceUrl, 'Report'));
    if (hasAdjudicatedCorruption(c)) {
      const o = c.corruptionOutcome;
      line(outside, `Judgment ${o.decisionId} (${o.authority}, ${o.decisionDate}): ${o.offence}. Finality checked ${o.verifiedAsOf}. `, sourceLink(o.judgmentUrl, 'Judgment'), ' · ', sourceLink(o.finalityUrl, 'Finality'));
    }
    if (c.dataFamily === 'dncp') {
      for (const x of c.sanctionsInForceAtAward || []) line(outside, `Supplier ${x.type} in force at award (${x.start} → ${x.end || 'no end'}, ${x.status || 'status —'}).`);
      for (const k of c.complaints || []) line(outside, `DNCP ${k.kind === 'protest' ? 'protest' : k.kind === 'investigation' ? 'investigation' : 'proceeding'} ${k.id}: ${k.eventCount} step(s), ${k.firstEventDate || '—'} → ${k.lastEventDate || '—'}${k.closureRecorded ? ', closed' : ''}.`);
    }
    if (c.complaintCount) line(outside, `${c.complaintCount} complaint(s) filed on this tender.`);
    if (outside.children.length > 1) sections.push(outside);

    // 4. Every check, folded: one line each.
    const all = element('details', null, 'detail-section detail-checks');
    all.id = 'detail-checks';
    all.append(element('summary', `All ${assessment.checks.length} checks`));
    const checks = element('ul', null, 'assessment-checks');
    const states = { signal: 'Signal', clear: 'Clear', unknown: 'Not assessable', 'not-applicable': 'Out of scope' };
    for (const r of assessment.checks) {
      const item = element('li', null, `check-${r.status}`);
      item.append(element('strong', r.label), ' — ', element('span', states[r.status]));
      if (r.status === 'signal' && r.weight != null) item.append(' · ', element('span', `${r.weight} pts`));
      item.append('. ', element('span', briefReason(r.reason), 'muted'));
      checks.append(item);
    }
    all.append(checks);
    sections.push(all);

    // 5. Where to check it.
    const verify = detailSection('verify', 'Sources');
    verify.classList.add('verify');
    const links = verificationLinks(c);
    if (links.length) {
      const list = element('ul', null, 'verify-links');
      for (const l of links) { const item = element('li'); item.append(sourceLink(l.url, l.label)); list.append(item); }
      verify.append(list);
    } else line(verify, c.dataStatus === 'synthetic' ? 'None: fictional example.' : 'No source link published.');
    const searchIds = verificationIdentifiers(c);
    if (searchIds.length) { const p = element('p', null, 'muted'); p.append(element('span', 'Search the portal for'), ` ${searchIds.map(([k, v]) => `${k} ${v}`).join(' · ')}`); verify.append(p); }
    sections.push(verify);

    const printed = element('p', `${currentDatasetLabel}. Printed ${new Date().toISOString().slice(0, 10)} from ${location.href}. Index v${SCORE_VERSION}: an editorial review aid, not a finding. Review notes are the reviewer’s own.`, 'print-only');
    detailBody.replaceChildren(head, ...sections, printed);
  }
  function markOpenRow() {
    for (const row of body.querySelectorAll('.contract-row')) {
      const open = row.dataset.id === openId;
      row.classList.toggle('is-open', open);
      row.querySelector('.row-toggle').setAttribute('aria-expanded', String(open));
    }
  }
  function updateDetailPosition() {
    if (!openId) return;
    const index = visibleRows.findIndex(c => c.id === openId);
    document.querySelector('#detail-position').textContent = index === -1 ? 'Not in the current results' : `Record ${index + 1} of ${visibleRows.length}`;
    document.querySelector('#detail-previous').disabled = index <= 0;
    document.querySelector('#detail-next').disabled = index === -1 ? !visibleRows.length : index >= visibleRows.length - 1;
  }
  function openDetail(id, { focus = true } = {}) {
    const c = contracts.find(x => x.id === id);
    if (!c) { closeDetail({ restoreFocus: false }); return; }
    openId = id;
    renderDetail(c);
    detailPanel.hidden = false;
    document.body.classList.add('detail-open');
    detailBody.scrollTop = 0;
    markOpenRow();
    updateDetailPosition();
    if (loaded) writeView();
    if (focus) detailPanel.focus({ preventScroll: true });
  }
  function closeDetail({ restoreFocus = true } = {}) {
    if (!openId) return;
    const id = openId;
    openId = '';
    detailPanel.hidden = true;
    detailBody.replaceChildren();
    document.body.classList.remove('detail-open');
    markOpenRow();
    if (loaded) writeView();
    if (restoreFocus) [...body.querySelectorAll('.contract-row')].find(row => row.dataset.id === id)?.querySelector('.row-toggle').focus();
  }
  function toggleDetail(id) { if (openId === id) closeDetail(); else openDetail(id); }
  function stepDetail(delta) {
    if (!openId || !visibleRows.length) return;
    const index = visibleRows.findIndex(c => c.id === openId);
    const target = index === -1 ? 0 : index + delta;
    if (target < 0 || target >= visibleRows.length) return;
    const targetPage = Math.floor(target / pageSize);
    if (targetPage !== page) { page = targetPage; render(); }
    openDetail(visibleRows[target].id, { focus: false });
    [...body.querySelectorAll('.contract-row')].find(row => row.dataset.id === openId)?.scrollIntoView({ block: 'nearest' });
  }
  document.querySelector('#detail-close').addEventListener('click', () => closeDetail());
  document.querySelector('#detail-previous').addEventListener('click', () => stepDetail(-1));
  document.querySelector('#detail-next').addEventListener('click', () => stepDetail(1));
  document.querySelector('#detail-print').addEventListener('click', () => {
    document.body.classList.add('print-detail');
    window.print();
  });
  window.addEventListener('afterprint', () => document.body.classList.remove('print-detail'));
  // Help and method dialog.
  const helpDialog = document.querySelector('#help-dialog');
  document.querySelector('#help-button').addEventListener('click', () => helpDialog.showModal());
  helpDialog.addEventListener('click', event => { if (event.target === helpDialog) helpDialog.close(); });
  document.querySelector('#help-close').addEventListener('click', () => helpDialog.close());

  // Keyboard: / focuses search, j/k step through records, Escape closes the panel.
  document.addEventListener('keydown', event => {
    if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey || helpDialog.open) return;
    const typing = event.target.closest?.('input, select, textarea, [contenteditable="true"]');
    if (event.key === 'Escape' && openId && (!typing || detailPanel.contains(event.target))) { closeDetail(); return; }
    if (typing) return;
    if (event.key === '/') { event.preventDefault(); controls.search.focus(); }
    else if (openId && event.key === 'j') { event.preventDefault(); stepDetail(1); }
    else if (openId && event.key === 'k') { event.preventDefault(); stepDetail(-1); }
  });

  function accept(data, prepared = null) {
    contracts = prepared || prepareContracts(data);
    assessmentCache = new WeakMap();
    const sectors = [...new Map(contracts.map(c => { const s = getSector(c); return [s.code, s]; })).values()].sort((a, b) => a.code === 'unknown' ? 1 : b.code === 'unknown' ? -1 : a.label.localeCompare(b.label, 'en'));
    fillSelect(controls.sector, [['', 'All sectors'], ...sectors.map(s => [s.code, `${s.code === 'unknown' ? '' : s.code + ' · '}${s.label}`])]);
    projectCatalog = new Map(contracts.filter(c => c.project).map(c => [c.project.id, c.project]));
    fillSelect(controls.project, [['', 'All records'], ...(projectCatalog.size ? [['@documented', 'Documented projects only']] : []), ...[...projectCatalog.values()].map(p => [p.id, p.title])]);
    controls.project.disabled = projectCatalog.size === 0;
    computeOverview();
    const noteCounts = new Map();
    for (const c of contracts) for (const key of ['dateNote', 'amountBasis', 'notes', 'identifierNote', 'offersNote']) {
      if (typeof c[key] === 'string' && c[key]) noteCounts.set(c[key], (noteCounts.get(c[key]) || 0) + 1);
    }
    const threshold = Math.max(5, contracts.length * 0.2);
    sharedNotes = new Set([...noteCounts].filter(([, n]) => n >= threshold).map(([text]) => text));
    fieldNotes.replaceChildren(...[...sharedNotes].map(text => element('li', text)));
    fieldNotes.hidden = !sharedNotes.size;
    loaded = true;
    page = 0;
    pendingOpen = '';
    if (pendingView) { applyView(pendingView); pendingView = null; }
    const missing = key => contracts.filter(c => c[key] == null).length;
    const conflictCount = contracts.filter(c => c.initialConflicts?.length).length;
    const withMods = contracts.filter(c => c.history?.some(event => event.kind === 'modification')).length;
    const enrichedCount = contracts.filter(c => c.supplierProfiles?.length).length;
    document.querySelector('#completeness').textContent = `In the loaded file: ${missing('amount')} amounts, ${missing('offers')} offer counts and ${contracts.filter(c => c.durationMonths == null && !c.durationOriginal).length} durations not provided out of ${contracts.length} records. ${conflictCount} groups with diverging initial values; ${withMods} histories containing a published modification. ${enrichedCount ? `${enrichedCount} records with an enriched current public name (not historical). ` : ''}Official findings are not subject to an exhaustive automatic search.`;
    render();
    if (pendingOpen) openDetail(pendingOpen, { focus: false });
    pendingOpen = '';
  }
  function fail(error) {
    loaded = false;
    contracts = [];
    closeDetail({ restoreFocus: false });
    body.replaceChildren();
    pagination.hidden = true;
    projectPanel.hidden = true;
    projectPanel.replaceChildren();
    document.querySelector('#completeness').textContent = '';
    fieldNotes.replaceChildren(); fieldNotes.hidden = true;
    status.textContent = `Unable to load the data: ${error.message}`;
    exportCsv.disabled = exportJson.disabled = true;
    fileHelp.hidden = false;
  }
  Object.values(controls).forEach(control => control.addEventListener('input', refresh));
  // Column headers sort too: first click descending (newest, largest, most), second ascending.
  // They drive the Sort control, so the link, page reset and export stay in step.
  const SORT_PAIRS = { date: ['date', 'date-asc'], amount: ['amount', 'amount-asc'], indicators: ['indicators', 'indicators-asc'], score: ['score', 'score-asc'], buyer: ['buyer', 'buyer-desc'], supplier: ['supplier', 'supplier-desc'], sector: ['sector', 'sector-desc'], offers: ['offers-desc', 'offers'] };
  const sortHeaders = [...document.querySelectorAll('th[data-sort-key]')];
  function syncSortHeaders() {
    for (const th of sortHeaders) {
      const [desc, asc] = SORT_PAIRS[th.dataset.sortKey];
      const alphabetical = ['buyer', 'supplier', 'sector'].includes(th.dataset.sortKey);
      const state = controls.sort.value === desc ? (alphabetical ? 'ascending' : 'descending') : controls.sort.value === asc ? (alphabetical ? 'descending' : 'ascending') : 'none';
      th.setAttribute('aria-sort', state);
      th.querySelector('button').dataset.direction = state;
      th.querySelector('button').title = state === 'descending' ? 'Sorted descending · click for ascending' : state === 'ascending' ? 'Sorted ascending · click for descending' : 'Sort by this column';
    }
  }
  for (const th of sortHeaders) th.querySelector('button').addEventListener('click', event => {
    event.stopPropagation();
    const [desc, asc] = SORT_PAIRS[th.dataset.sortKey];
    controls.sort.value = controls.sort.value === desc ? asc : desc;
    controls.sort.dispatchEvent(new Event('input'));
  });
  controls.sort.addEventListener('input', syncSortHeaders);
  syncSortHeaders();
  document.querySelector('#clear-filters').addEventListener('click', () => { activeProfile = null; clearFilters(); refresh(); });
  pageSizeSelect.addEventListener('change', () => {
    const nextSize = Number(pageSizeSelect.value);
    if (!PAGE_SIZES.includes(nextSize)) return;
    page = Math.floor(page * pageSize / nextSize);
    pageSize = nextSize;
    render(); viewport.scrollTop = 0;
  });
  async function copyText(text) {
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard API unavailable');
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // file:// and older browsers may not expose the async Clipboard API.
      const field = document.createElement('textarea');
      field.value = text; field.style.position = 'fixed'; field.style.opacity = '0';
      document.body.append(field); field.select();
      let copied = false;
      try { copied = document.execCommand('copy'); } catch (_) { /* Browser blocked clipboard access. */ }
      field.remove();
      return copied;
    }
  }
  copyPage.addEventListener('click', async () => {
    if (!loaded || !pageRowsForCopy.length) return;
    const copiedCount = pageRowsForCopy.length;
    const text = pageSummaryForCopy(pageRowsForCopy, { dataset: currentDatasetLabel,
      page: page + 1, totalPages: Math.max(1, Math.ceil(totalResultsForCopy / pageSize)), totalResults: totalResultsForCopy });
    copyStatus.textContent = await copyText(text) ? `${copiedCount} sourced page summaries copied. Public-record context is explained in the personal-data inventory.` : 'Unable to copy. Serve over localhost or select the rows manually.';
    const original = 'Copy page summary';
    copyPage.textContent = copyStatus.textContent.startsWith('Unable') ? 'Copy failed' : 'Copied!';
    setTimeout(() => { copyPage.textContent = original; }, 2500);
  });
  // Files are built in this browser from the loaded data; nothing is uploaded.
  function download(filename, type, text) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const link = element('a');
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const exportName = extension => `contract-signals-${usingLocalFile ? 'local-file' : datasetSelect.value}-${new Date().toISOString().slice(0, 10)}.${extension}`;
  exportCsv.addEventListener('click', () => {
    if (!loaded || !rowsForExport.length) return;
    download(exportName('csv'), 'text/csv;charset=utf-8', '﻿' + rowsToCsv(rowsForExport));
    copyStatus.textContent = `${rowsForExport.length} filtered records exported as CSV.`;
  });
  exportJson.addEventListener('click', () => {
    if (!loaded || !rowsForExport.length) return;
    download(exportName('json'), 'application/json', rowsToJson(rowsForExport, { dataset: currentDatasetLabel, view: viewStateToHash(currentView()), exportedAt: new Date().toISOString() }));
    copyStatus.textContent = `${rowsForExport.length} filtered records exported as JSON.`;
  });
  // Review notes travel as a JSON file the reviewer chooses to share; nothing is uploaded.
  const reviewStatus = document.querySelector('#review-status');
  document.querySelector('#export-review').addEventListener('click', () => {
    const items = Object.entries(reviews).map(([key, r]) => { const cut = key.indexOf('|'); return { dataset: key.slice(0, cut), id: key.slice(cut + 1), status: r.status || null, note: r.note || null, updatedAt: r.updatedAt || null }; });
    download(`contract-signals-review-notes-${new Date().toISOString().slice(0, 10)}.json`, 'application/json', JSON.stringify({ tool: 'Contract signals', kind: 'review-notes', exportedAt: new Date().toISOString(),
      caveat: 'Working notes of a reviewer. They are not findings and never change the index. Notes are newly created information, not source publications. Do not include protected casework; exported notes are plaintext.', count: items.length, items }, null, 2) + '\n');
    reviewStatus.textContent = `${items.length} review note(s) exported.`;
  });
  document.querySelector('#import-review').addEventListener('change', async event => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      if (file.size > 5 * 1024 * 1024) throw new Error('Notes file exceeds 5 MiB.');
      const data = JSON.parse(await file.text());
      if (data?.kind !== 'review-notes' || !Array.isArray(data.items)) throw new Error('not a Contract signals review-notes file');
      if (data.items.length > 20000) throw new Error('Too many review notes (maximum 20,000).');
      for (const item of data.items) {
        if (typeof item?.dataset !== 'string' || typeof item.id !== 'string' || !item.dataset || !item.id || item.dataset.includes('|')) throw new Error('Each note needs an unambiguous dataset and record identifier.');
        if (item.status != null && !Object.prototype.hasOwnProperty.call(REVIEW_STATUSES, item.status)) throw new Error('Invalid review status.');
        if (item.note != null && (typeof item.note !== 'string' || item.note.length > 10000)) throw new Error('Notes must be text of at most 10,000 characters.');
        if (item.updatedAt != null && (typeof item.updatedAt !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(item.updatedAt) || !Number.isFinite(Date.parse(item.updatedAt)))) throw new Error('Invalid review timestamp (UTC ISO format required).');
      }
      let merged = 0;
      for (const item of data.items) {
        const key = `${item.dataset}|${item.id}`;
        const existing = reviews[key];
        if (existing?.updatedAt && item.updatedAt && existing.updatedAt >= item.updatedAt) continue;
        reviews[key] = { status: item.status || null, note: (item.note || '').slice(0, 10000), updatedAt: typeof item.updatedAt === 'string' ? item.updatedAt : new Date().toISOString() };
        merged++;
      }
      saveReviews();
      reviewStatus.textContent = `${merged} review note(s) imported; newer local notes were kept.`;
      if (loaded) render();
      if (openId) openDetail(openId, { focus: false });
    } catch (error) { reviewStatus.textContent = `Unable to import: ${error.message}.`; }
    event.target.value = '';
  });
  previous.addEventListener('click', () => { if (page > 0) { page--; render(); viewport.scrollTop = 0; } });
  next.addEventListener('click', () => { page++; render(); viewport.scrollTop = 0; });
  const importStatus = document.querySelector('#import-status');
  const importPreview = document.querySelector('#import-preview');
  const importMethod = document.querySelector('#import-method');
  const previewImport = document.querySelector('#preview-import');
  const confirmImport = document.querySelector('#confirm-import');
  const columnControls = document.querySelector('#import-columns');
  let stagedFile = null;
  let stagedPreview = null;
  let importVersion = 0;
  function invalidateImport() {
    importVersion++;
    stagedPreview = null;
    confirmImport.disabled = true;
    importPreview.replaceChildren();
  }
  importMethod.addEventListener('change', invalidateImport);
  document.querySelector('#open-import').addEventListener('click', () => {
    filterPanel.open = true;
    document.querySelector('.local-file').open = true;
    importMethod.focus();
  });
  document.querySelector('#file').addEventListener('change', async event => {
    invalidateImport();
    stagedFile = null;
    previewImport.disabled = true;
    columnControls.replaceChildren();
    document.querySelector('#import-mapping').hidden = true;
    const file = event.target.files[0];
    if (!file) return;
    const version = importVersion;
    try {
      if (file.size > 25 * 1024 * 1024) throw new Error('File exceeds the 25 MiB import limit.');
      const text = await file.text();
      if (version !== importVersion) return;
      stagedFile = { name: file.name, text };
      if (!/^[\[{]/.test(text.replace(/^\uFEFF/, '').trim())) {
        const headers = ContractImport.columns(text, file.name);
        document.querySelector('#import-mapping').hidden = false;
        for (const key of ['id', 'buyer', 'description', 'supplier', 'supplierId', 'buyerSiret', 'amount', 'currency', 'date', 'offers', 'durationMonths', 'directAward', 'dataStatus', 'cpv', 'procedure', 'source']) {
          const label = element('label', key);
          const select = element('select');
          select.dataset.field = key;
          select.append(new Option('Auto-detect', ''), ...headers.map(h => new Option(h, h)));
          select.addEventListener('change', invalidateImport);
          label.append(select);
          columnControls.append(label);
        }
      }
      previewImport.disabled = false;
      importStatus.textContent = 'File read locally. Choose a method, map CSV columns if needed, then preview. The current dataset is unchanged.';
    } catch (error) { if (version === importVersion) importStatus.textContent = `Unable to read: ${error.message}`; }
  });
  previewImport.addEventListener('click', () => {
    invalidateImport();
    if (!stagedFile) return;
    try {
      const mapping = Object.fromEntries([...columnControls.querySelectorAll('select')].filter(s => s.value).map(s => [s.dataset.field, s.value]));
      const method = importMethod.value;
      const result = ContractImport.parse(stagedFile.text, { filename: stagedFile.name, method, mapping });
      validateContracts(result.records);
      stagedPreview = { ...result, method, mapping };
      importPreview.append(element('p', `${result.records.length} records · ${result.format.toUpperCase()} · ${method === 'browse' ? 'browse only, no scoring' : 'French v3 editorial checks; not legal conclusions'}.`));
      const missing = key => result.records.filter(c => c[key] == null || c[key] === '').length;
      importPreview.append(element('p', `Missing from this file: ${missing('amount')} amounts, ${missing('currency')} currencies, ${missing('date')} dates, ${missing('offers')} offer counts and ${missing('source')} source links. ${result.records.filter(c => c.dataStatus === 'unverified').length} records are unverified and excluded from scoring.`));
      for (const warning of result.warnings) importPreview.append(element('p', warning));
      for (const c of result.records.slice(0, 3)) importPreview.append(element('p', `${c.id} · ${c.buyer} · ${c.description}`));
      confirmImport.disabled = false;
      importStatus.textContent = 'Preview validated. No records loaded yet. Missing data stays unknown; cohort completeness is not verified.';
    } catch (error) { importStatus.textContent = `Unable to preview: ${error.message}`; }
  });
  confirmImport.addEventListener('click', async () => {
    if (!stagedPreview || !stagedFile) return;
    const version = importVersion;
    const preview = stagedPreview, file = stagedFile;
    confirmImport.disabled = true;
    try {
      const identity = await ContractImport.fingerprint(file.text, preview.method, preview.mapping);
      if (version !== importVersion) return;
      ++loadVersion;
      closeDetail({ restoreFocus: false });
      usingLocalFile = true;
      localFileName = file.name;
      localFileIdentity = identity;
      currentDatasetLabel = `Local file: ${file.name} (${preview.method === 'browse' ? 'browse only' : 'French v3'}; scope not verified)`;
      for (const id of FILTER_VALUES) controls[id].value = id === 'min-score' ? '0' : '';
      for (const id of VIEW_FLAGS) controls[id].checked = false;
      controls.search.value = '';
      controls.sort.value = preview.method === 'browse' ? 'date' : 'score';
      pendingView = null;
      accept(preview.records);
      document.querySelector('#dataset-note').textContent = `Local file: ${file.name}. ${preview.method === 'browse' ? 'No scoring method selected.' : 'French thresholds explicitly selected; imported status is not independent verification.'} The file is not certified complete. Repetition and concentration need a validated cohort and are not enabled by this generic import.`;
      document.querySelector('#coverage-link').hidden = true;
      document.querySelector('#dataset-sources').hidden = true;
      renderDatasetDates('local');
      importStatus.textContent = `${preview.records.length} records loaded locally. Review marks are scoped to this file’s SHA-256 fingerprint and import settings.`;
    } catch (error) { importStatus.textContent = `Unable to load: ${error.message}`; }
    if (version === importVersion) confirmImport.disabled = false;
  });
  async function loadDataset() {
    const selected = datasets[datasetSelect.value];
    invalidateImport();
    const version = ++loadVersion;
    activeProfile = null;
    loaded = false;
    closeDetail({ restoreFocus: false });
    usingLocalFile = false;
    currentDatasetLabel = datasetLabel();
    copyStatus.textContent = '';
    copyPage.textContent = 'Copy page summary';
    contracts = [];
    body.replaceChildren();
    pagination.hidden = true;
    document.querySelector('#completeness').textContent = '';
    fieldNotes.replaceChildren(); fieldNotes.hidden = true;
    document.querySelector('#dataset-note').textContent = selected.note;
    document.querySelector('#coverage-link').href = selected.coverage;
    renderSources(selected);
    renderDatasetDates(datasetSelect.value);
    document.querySelector('#coverage-link').hidden = false;
    document.querySelector('#file-path').textContent = selected.path;
    document.querySelector('#file').value = '';
    fileHelp.hidden = location.protocol !== 'file:';
    controls.search.value = '';
    clearFilters();
    projectPanel.hidden = true;
    projectPanel.replaceChildren();
    viewport.scrollTop = 0;
    status.textContent = 'Loading data…';
    if (selected.combined) {
      document.querySelector('#coverage-link').hidden = true;
      document.querySelector('#file-path').textContent = 'every data/*.json file above';
      try {
        const keys = Object.keys(datasets).filter(key => !datasets[key].combined);
        const parts = await Promise.all(keys.map(async key => {
          const response = await fetch(datasets[key].path);
          if (!response.ok) throw new Error(`${datasets[key].path}: HTTP ${response.status}`);
          const option = [...datasetSelect.options].find(o => o.value === key);
          const country = option?.parentElement?.label || '';
          return prepareContracts(await response.json()).map(c => ({ ...c, datasetKey: key, datasetCountry: country }));
        }));
        if (version === loadVersion) accept(null, parts.flat());
      } catch (error) { if (version === loadVersion) fail(error); }
      return;
    }
    try {
      const response = await fetch(selected.path);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (version === loadVersion) accept(data);
    } catch (error) { if (version === loadVersion) fail(error); }
  }
  datasetSelect.addEventListener('change', loadDataset);
  // A pasted link or back/forward: reload only when the dataset differs.
  window.addEventListener('hashchange', () => {
    const view = hashToViewState(location.hash);
    const wanted = datasets[view.dataset] ? view.dataset : usingLocalFile ? null : defaultDataset;
    if (wanted && (wanted !== datasetSelect.value || usingLocalFile)) {
      datasetSelect.value = wanted;
      pendingView = view;
      loadDataset();
    } else if (loaded) {
      applyView(view);
      render();
      if (pendingOpen && pendingOpen !== openId) openDetail(pendingOpen, { focus: false });
      else if (!pendingOpen && openId) closeDetail({ restoreFocus: false });
      pendingOpen = '';
    }
  });
  fetch('data/dataset-metadata.json').then(response => {
    if (!response.ok) throw new Error('Dataset date metadata unavailable');
    return response.json();
  }).then(metadata => {
    datasetMetadata = metadata;
    renderDatasetDates(usingLocalFile ? 'local' : datasetSelect.value);
  }).catch(() => { /* Dates remain unknown; record loading is independent. */ });
  loadDataset();
}

if (typeof document !== 'undefined') startExplorer();
