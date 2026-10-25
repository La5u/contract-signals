// Vigilance index framework shared by every country (docs/score-v3.md): cohorts, check kinds, points
// basis, the universal late-publication check, and getAssessment, which hands each record to its
// country's check set (checks-*.js). Engine files: no DOM; tools/engine.cjs lists their order.
'use strict';

const HISTORY_COHORT = 'decp-paris-ardeche-2024-2025';
const CITIES_COHORT = 'decp-six-cities-2024-2025';
const HISTORY_COHORTS = new Set([HISTORY_COHORT, CITIES_COHORT]);
function isAmbiguousCityContract(c) {
  return c.cohortId === CITIES_COHORT && Boolean(c.initialConflicts?.length || c.modificationConflicts?.length);
}
// How far a French DECP record's amount is corroborated (tools/decp_feeds.py).
const VERIFICATION_STATUSES = {
  'notice-checked': 'Checked against the award notice',
  'sources-agree': 'Sources agree',
  'sources-disagree': 'Sources disagree',
  'single-source': 'Single source',
};
const HISTORY_START = '2024-01-01';
const HISTORY_END = '2025-12-31';

const SCORE_VERSION = '3.8';

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

function validIsoDate(value) {
  const d = typeof value === 'string' ? value.slice(0, 10) : '';
  return /^\d{4}-\d{2}-\d{2}$/.test(d) && !Number.isNaN(Date.parse(`${d}T00:00:00Z`)) && new Date(`${d}T00:00:00Z`).toISOString().slice(0, 10) === d ? d : null;
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
  'contract-amendments': 'Three or more contract amendments',
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
  'buyer-share': 'Large share of the buyer’s yearly procurement',
  'award-near-reserve': 'Award close to the reserve price',
  'restricted-competition': 'Restricted or nominated competition',
  'supplier-dependence': 'Supplier holds a large share of the buyer’s yearly amount',
  'few-bidders': 'Only two or three bids',
  'bid-pattern': 'Unusual pattern of bid amounts',
};
// Short names for the table chips; the full name is in the tooltip, the filter and the record panel.
const KIND_SHORT = {
  'single-offer': 'Single offer', 'direct-award': 'No competition', 'repeated-single-offer': 'Repeated single offer',
  'repeated-direct': 'Repeated no competition', 'low-competition-rate': 'Low competition rate', 'concentration': 'Concentration',
  'disqualified-better-bid': 'Better bid disqualified', 'short-bidding-period': 'Short bidding period',
  'late-notice-change': 'Late notice change', 'long-duration': 'Long duration', 'amount-increase': 'Amount increase',
  'contract-amendments': 'Contract amendments',
  'term-extension': 'Term extended', 'late-publication': 'Late publication',
  'cap': 'Near applicable cap', 'execution': 'Payment / execution',
  'legalGround': 'Legal ground mismatch', 'unitPrice': 'Unit-price increase', 'exclusivity': 'Exclusivity context',
  'buyer-share': 'Buyer share', 'award-near-reserve': 'Near reserve price', 'restricted-competition': 'Restricted competition',
  'supplier-dependence': 'Supplier dependence', 'few-bidders': 'Two or three bids', 'bid-pattern': 'Bid pattern',
};
// Where a kind matches a red flag in a framework auditors already use (docs/indicators.md).
const KIND_REFERENCES = {
  'contract-amendments': 'StateWatch/Prozorro risk indicator ARI 1-1 (three or more contract amendments)',
  'single-offer': 'OCP Cardinal R018 “Single bid received”; single bidding in the Fazekas Corruption Risk Index',
  'direct-award': 'non-open procedure / no call for tender published in the Fazekas Corruption Risk Index',
  'short-bidding-period': 'OCP Cardinal R003 “Short submission period”; advertisement period in the Fazekas Corruption Risk Index',
  'disqualified-better-bid': 'related to OCP Cardinal R036 “Lowest bid disqualified” and R035, and to Ukraine’s State Audit Service risk indicators sas-3-2 and sas-3-5',
  'repeated-direct': 'related to Ukraine’s State Audit Service risk indicator sas-3-3 (one supplier across many purchase codes)',
  'concentration': 'related to Ukraine’s State Audit Service risk indicator sas-3-3 and OCP Cardinal R048 “Heterogeneous supplier”',
  'bid-pattern': 'the coefficient-of-variation and relative-distance screens for bid rigging (Imhof, Karagök and Rutz 2018)',
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
  'ua-contract-amendments': 'contract-amendments', 'ua-term-extension': 'term-extension', 'ua-buyer-share': 'buyer-share',
  'secop2-term-extension': 'term-extension', 'ua-better-bid-disqualified': 'disqualified-better-bid',
  'secop2-buyer-share': 'buyer-share', 'ua-direct-contract': 'direct-award',
  'kr-award-near-reserve': 'award-near-reserve', 'kr-supplier-dependence': 'supplier-dependence', 'kr-buyer-share': 'buyer-share',
  'kr-concentration': 'concentration', 'kr-restricted-competition': 'restricted-competition',
  'kr-few-bidders': 'few-bidders', 'kr-bid-gap': 'bid-pattern', 'kr-bid-dispersion': 'bid-pattern', 'kr-floor-gap': 'award-near-reserve',
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
function scoreLevel(score, incomplete = false, signals = 0) {
  if (score == null) return { id: 'unknown', label: 'Not assessed' };
  if (score === 0 && signals) return { id: 'offset', label: 'Signals offset by evidence against' };
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

// v3.7: editorial (unmeasured) points are capped at 30, then the strongest measured value (Ukrainian buyer
// share, LR 8). v3.8 found that value was contract size (now 2.2 points); the cap is kept pending an owner
// decision, although no measured check now scores above 11. Points from labelled cases are 10 x log2(LR).
const EDITORIAL_MAX = 30;
// Checks whose points come from labelled cases (court verdicts, competition-authority decisions); every other
// check carries editorial points. Shown next to the points in the record panel, the badges and exports.
const MEASURED_CHECKS = new Set(['ua-single-offer', 'ua-direct-award', 'ua-direct-contract', 'ua-better-bid-disqualified',
  'ua-contract-amendments', 'ua-term-extension', 'ua-buyer-share', 'secop2-buyer-share', 'secop2-repeated-plurality',
  'kr-award-near-reserve', 'kr-supplier-dependence', 'kr-buyer-share', 'kr-concentration', 'kr-restricted-competition',
  'kr-few-bidders', 'kr-bid-gap', 'kr-bid-dispersion', 'kr-floor-gap']);
const MEASURED_CHECKS_BY_COUNTRY = { ROU: new Set(['ted-repeated-direct', 'ted-concentration']) };
function pointsBasis(c, id) {
  return MEASURED_CHECKS.has(id) || (c.dataFamily === 'ted' && MEASURED_CHECKS_BY_COUNTRY[c.country]?.has(id)) ? 'measured' : 'editorial';
}
const BASIS_NOTE = { measured: 'measured on labelled cases', editorial: 'editorial, not measured' };
function graduated(value, start, end, low, high) {
  return Math.round((low + (high - low) * Math.min(1, Math.max(0, (value - start) / (end - start)))) * 10) / 10;
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
// Rows that may be one contract published twice count once in buyer-level baselines:
// the first of each cluster contributes, the others only receive the buyer's context.
function duplicateShadow(c) {
  return Array.isArray(c.possibleDuplicateOf) && c.possibleDuplicateOf.some(id => id < c.id);
}
function assignPublicationBaselines(contracts) {
  const buyers = new Map(), shadows = [];
  for (const c of contracts) {
    c.latePublicationBaseline = null;
    const delay = latePublicationDelay(c), buyer = c.buyerSiret || c.buyerId || c.buyer;
    if (delay == null || !buyer) continue;
    const key = `${c.dataFamily}|${buyer}`;
    if (duplicateShadow(c)) { shadows.push({ c, key }); continue; }
    if (!buyers.has(key)) buyers.set(key, []);
    buyers.get(key).push({ c, delay });
  }
  for (const rows of buyers.values()) {
    if (rows.length < latePublicationConfig(rows[0].c).minBuyerRecords) continue;
    const sorted = rows.map(r => r.delay).sort((x, y) => x - y), m = sorted.length - 1;
    const firstAt = new Map();
    sorted.forEach((d, i) => { if (!firstAt.has(d)) firstAt.set(d, i); });
    for (const { c, delay } of rows) {
      const p = firstAt.get(delay);   // any position holding this value gives the same remaining multiset
      const at = i => sorted[i < p ? i : i + 1];
      const median = m % 2 ? at((m - 1) / 2) : (at(m / 2 - 1) + at(m / 2)) / 2;
      c.latePublicationBaseline = { median, others: m };
    }
  }
  for (const { c, key } of shadows) {
    const rows = buyers.get(key);
    if (!rows || rows.length < latePublicationConfig(c).minBuyerRecords) continue;
    const sorted = rows.map(r => r.delay).sort((x, y) => x - y), n = sorted.length;
    c.latePublicationBaseline = { median: n % 2 ? sorted[(n - 1) / 2] : (sorted[n / 2 - 1] + sorted[n / 2]) / 2, others: n };
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
  const checks = [...base.checks, ...(browse ? [] : [latePublicationCheck(c, base.excludedReason)]), ...getAdditionalIndicatorChecks(c, base.excludedReason)]
    .map(r => ({ ...r, basis: pointsBasis(c, r.id) }));
  return { ...base, checks,
    applicable: checks.filter(r => r.applicability === 'yes').length,
    evaluated: checks.filter(r => r.status === 'signal' || r.status === 'clear').length,
    unknown: checks.filter(r => r.applicability === 'yes' && r.status === 'unknown').length,
    unknownApplicability: checks.filter(r => r.applicability === 'unknown').length,
    notApplicable: checks.filter(r => r.status === 'not-applicable').length,
    signals: checks.filter(r => r.status === 'signal').length };
}

function hasAdjudicatedCorruption(contract) {
  return contract.corruptionOutcome?.status === 'final-adjudication';
}
function hasReportedInvestigation(contract) {
  return Array.isArray(contract.investigationReports) && contract.investigationReports.length > 0;
}
// Supplier proceedings (data/supplier-proceedings.json, curated by hand): an authority's step that names a
// company, such as a competition inspection. They describe the company, never this contract, and are
// never scored. A supplier without an entry has not been checked; it is not known to be clear.
const PROCEEDING_STAGES = { inspection: 'Competition inspection', investigation: 'Investigation opened', decision: 'Authority decision', court: 'Court ruling' };
const PROCEEDING_CAVEATS = {
  inspection: 'An inspection is an investigative step, not a finding of wrongdoing.',
  investigation: 'An open investigation is not a finding of wrongdoing.',
  decision: 'A decision of the authority, not a court judgment; it may be under appeal.',
  court: 'A court ruling; check whether it is final.',
};
const PROCEEDING_SCOPE = 'It concerns the company; this contract is not known to be part of the case.';
function validateSupplierProceedings(data) {
  const isDate = v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0, 10) === v;
  const text = v => typeof v === 'string' && v.trim().length > 0;
  if (!data || !Array.isArray(data.suppliers)) throw new Error('Supplier proceedings: invalid file.');
  const index = new Map();
  for (const s of data.suppliers) {
    if (!s || !/^[A-Z]{3}$/.test(s.country || '') || !['identifierType', 'id', 'name', 'identityBasis'].every(k => text(s[k])) || !Array.isArray(s.proceedings) || !s.proceedings.length)
      throw new Error('Supplier proceedings: invalid supplier entry.');
    for (const x of s.proceedings) {
      if (!x || !PROCEEDING_STAGES[x.stage] || !['authority', 'wording', 'sourceLabel'].every(k => text(x[k])) || !safeSource(x.sourceUrl) || (x.copyUrl != null && !safeSource(x.copyUrl)) ||
          !isDate(x.eventDate) || !isDate(x.publishedAt) || !isDate(x.verifiedAt) || x.publishedAt < x.eventDate)
        throw new Error(`Supplier proceedings: invalid proceeding for ${s.name}.`);
    }
    const key = `${s.country}|${s.identifierType}:${s.id.trim()}`;
    if (index.has(key)) throw new Error(`Supplier proceedings: duplicate supplier ${key}.`);
    index.set(key, s);
  }
  return index;
}
// Every identified member of the winning supplier (consortia included), with its proceedings.
function getSupplierProceedings(c, index) {
  if (!index?.size || !c.country) return [];
  const out = [];
  for (const { id, identifierType } of c.supplierIds || []) {
    const entry = typeof id === 'string' ? index.get(`${c.country}|${identifierType}:${id.trim()}`) : null;
    for (const x of entry?.proceedings || []) out.push({ ...x, supplier: entry.name });
  }
  return out;
}
// Several holders on one award, recorded as a relationship between the firms, never a signal
// (docs/adjudicated-outcomes.md). A joint offer is claimed only with evidence: TED lists the members of
// one tendering party; DECP declares the grouping (operatorGrouping, from the source rows'
// typegroupementoperateurs, kept by tools/build-web-data.py). Otherwise the holders may also be the
// several holders of a multi-supplier framework. Firms are counted once per SIREN.
function jointOfferNote(c) {
  const firms = new Set((c.supplierIds || []).map(s => s.siren || s.id));
  if (firms.size < 2) return null;
  const n = firms.size, grouping = Array.isArray(c.operatorGrouping) ? c.operatorGrouping : [];
  if (c.dataFamily === 'ted') return `Joint offer by ${n} firms · a relationship between them, not a signal`;
  if (grouping.length && grouping.every(g => g === 'Conjoint' || g === 'Solidaire')) return `Joint offer by ${n} firms (declared grouping: ${grouping.join(' / ')}) · a relationship between them, not a signal`;
  if (grouping.length === 1 && grouping[0] === 'Pas de groupement') return `${n} firms hold this award, declared without a grouping (likely several framework holders) · a relationship between them, not a signal`;
  return `${n} firms hold this award (joint offer or several framework holders; the source does not say) · a relationship between them, not a signal`;
}
function supplierProceedingNote(x) {
  return `${x.wording} ${PROCEEDING_CAVEATS[x.stage]} ${PROCEEDING_SCOPE} Source: ${x.sourceLabel} (${x.publishedAt}); checked ${x.verifiedAt}.`;
}
function getIndicators(contract) {
  return getAssessment(contract).checks.filter(r => r.status === 'signal').map(r => ({ ...r, kind: indicatorKind(r.id), kindLabel: INDICATOR_KINDS[indicatorKind(r.id)] || r.label }));
}
function getScoreBreakdown(contract) {
  const assessment = getAssessment(contract);
  const families = { competition: 0, execution: 0, transparency: 0 };
  // Other families (South Korea: price, concentration) are added when a check names them.
  for (const r of assessment.checks) if (r.status === 'signal') families[r.family] = Math.max(families[r.family] || 0, r.weight);
  // A clear check with negative points (South Korea's FLOOR-GAP) offsets its family's largest signal; the index stays >= 0.
  for (const r of assessment.checks) if (r.status === 'clear' && r.weight < 0) families[r.family] = (families[r.family] || 0) + r.weight;
  const total = Object.values(families).reduce((sum, v) => sum + v, 0);
  const score = assessment.evaluated ? Math.round(Math.max(0, Math.min(100, total)) * 10) / 10 : null;
  return { ...families, families, score, assessment };
}
function getVigilanceScore(contract) { return getScoreBreakdown(contract).score; }

function getAmountEvolution(contract) {
  const unavailable = reason => ({ status: 'unavailable', reason });
  if (contract.dataFamily !== 'decp' || !Array.isArray(contract.history)) return unavailable('Published contract history not available for this record; increase check not applicable.');
  if (contract.identityAmbiguous) return unavailable('Duplicate identifier: calculation excluded.');
  if (!Array.isArray(contract.initialConflicts) || contract.initialConflicts.length) return unavailable('Diverging initial values: no increase calculation.');
  if (Array.isArray(contract.modificationConflicts) && contract.modificationConflicts.length) return unavailable('Diverging modification values for the same identifier: no increase calculation.');
  if (contract.verification?.amountRange || contract.verification?.placeholder) return unavailable('Sources disagree on the initial amount: no increase calculation, which could mix bases.');
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
