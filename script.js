'use strict';

const HISTORY_COHORT = 'decp-paris-ardeche-2024-2025';
const CITIES_COHORT = 'decp-six-cities-2024-2025';
const HISTORY_COHORTS = new Set([HISTORY_COHORT, CITIES_COHORT]);
function isAmbiguousCityContract(c) {
  return c.cohortId === CITIES_COHORT && Boolean(c.initialConflicts?.length || c.modificationConflicts?.length);
}
const HISTORY_START = '2024-01-01';
const HISTORY_END = '2025-12-31';

const SCORE_VERSION = '3.0';

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

// Eight heuristic checks, with explicit applicability and evaluation states.
// Official findings and financial amounts are separate evidence/context, not points.
function getAssessment(c) {
  const excludedReason = c.initialConflicts?.length || c.modificationConflicts?.length ? 'Conflicting versions: calculations excluded.' :
    c.identityAmbiguous ? 'Duplicate contract identifier: calculations excluded.' :
    c.dataStatus === 'unverified' ? 'Unverified record: calculations excluded.' : null;
  const aggregate = c.findingScope === 'aggregate';
  const documentOnly = Boolean(c.consultation && !c.contractId);
  const checks = [];
  function add(id, label, family, applicability, evaluable, triggered, weight, reason) {
    if (aggregate) { applicability = 'no'; evaluable = false; reason = 'Aggregate dossier: not a comparable individual award.'; }
    if (documentOnly && id !== 'short-bidding-period') { applicability = 'no'; evaluable = false; reason = 'Documentary notice, not a normalized attributed contract.'; }
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
  add('direct-award', 'Award without competition', 'competition', 'yes', typeof c.directAward === 'boolean', c.directAward === true, 18,
    c.directAward == null ? 'Competitive character unknown.' : c.directAward === false ? 'Explicitly competitive procedure: no direct-award signal.' : 'Award explicitly declared without competition: 18 points, all amounts. May be legal; no bonus for an R2122 citation.');
  add('long-contract', 'Declared duration ≥ 10 years', 'execution', 'yes', c.durationMonths != null, c.durationMonths >= 120,
    graduated(c.durationMonths || 0, 120, 360, 8, 40), c.durationMonths == null ? 'Declared duration unknown.' : `${c.durationMonths} months declared. From 120 months: 8 points, linear progression up to 40 at 360 months; renewals are not invented. Not a sectoral comparison nor an illegality threshold.`);
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
function getIndicators(contract) { return getAssessment(contract).checks.filter(r => r.status === 'signal'); }
function getScoreBreakdown(contract) {
  const assessment = getAssessment(contract);
  const families = { competition: 0, execution: 0 };
  for (const r of assessment.checks) if (r.status === 'signal') families[r.family] = Math.max(families[r.family], r.weight);
  const score = assessment.evaluated ? Math.round(Math.min(100, families.competition + families.execution) * 10) / 10 : null;
  return { ...families, score, assessment };
}
function getVigilanceScore(contract) { return getScoreBreakdown(contract).score; }

function getAmountEvolution(contract) {
  const unavailable = reason => ({ status: 'unavailable', reason });
  if (contract.dataFamily !== 'decp' || !Array.isArray(contract.history)) return unavailable('DECP history not available.');
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
  const contracts = validateContracts(data).map(c => ({ ...c, competitionContext: null, supplierContext: null, identityAmbiguous: false }));
  const groups = new Map();
  const supplierGroups = new Map();
  const identityCounts = new Map();
  for (const c of contracts) {
    if (c.dataFamily !== 'decp' || !c.buyerSiret || !c.contractId) continue;
    const identity = `${c.buyerSiret}:${c.contractId}`;
    identityCounts.set(identity, (identityCounts.get(identity) || 0) + 1);
  }
  for (const c of contracts) c.identityAmbiguous = c.dataFamily === 'decp' && Boolean(c.buyerSiret && c.contractId && identityCounts.get(`${c.buyerSiret}:${c.contractId}`) > 1);
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
  return contracts;
}

function groupInfo(contract, mode) {
  if (mode === 'sector') { const sector = getSector(contract); return { key: `sector:${sector.code}`, label: `${sector.code === 'unknown' ? '' : sector.code + ' · '}${sector.label}` }; }
  if (mode === 'buyer') return { key: `buyer:${contract.buyerSiret || normalize(contract.buyer)}`, label: contract.buyer + (contract.buyerSiret ? ` · ${contract.buyerSiret}` : ' · matched by name, to be verified') };
  if (mode === 'supplier') {
    const identity = getSupplierIdentity(contract);
    return identity ? { key: `supplier:${identity}`, label: `SIREN ${identity} · ${contract.supplier || 'Holder'}` } : { key: `supplier-unknown:${contract.id}`, label: `${contract.supplier || 'Unknown holder'} · consortium or unmatched identity` };
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
    if (c.dataFamily != null && !['decp', 'boamp', 'audit'].includes(c.dataFamily)) throw new Error(`${c.id} : invalid data family.`);
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
  }
  return data;
}

function selectContracts(contracts, { search = '', minimum = 0, minScore = 0, flagged = false, official = false, indicator = '', legal = '', noticeContext = '', assessment = '', sector = '', project = '', sort = 'score' } = {}) {
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
  return contracts.filter(c => {
    const projectText = c.project ? [c.project.title, c.project.basis] : [];
    const evidence = c.noticeEvidence;
    const noticeText = evidence ? [evidence.noticeUuid, evidence.lotReference, evidence.procedureId, evidence.procedureReference, evidence.procedureDescription, ...evidence.awardCriteria.map(a => [a.name, a.description, a.formula].join(' ')), ...evidence.justifications.map(j => j.text), ...evidence.references.map(r => r.id)] : [];
    const noticeMatch = !noticeContext || Boolean(evidence && (noticeContext === 'criteria' ? evidence.awardCriteria.length : noticeContext === 'explanation' ? evidence.procedureDescription || evidence.justifications.some(j => j.text) : noticeContext === 'correction' ? evidence.kind === 'correction' : noticeContext === 'ted' ? evidence.ted.length : false));
    const text = normalize([c.id, c.buyer, c.buyerSiret, c.supplier, c.description, c.procedure, c.cpv, c.contractId, c.lotId, c.noticeId, ...(c.supplierProfiles || []).map(p => p.name), c.consultation?.procedureReference, ...(c.consultation?.notices || []).map(n => n.id), ...(c.consultation?.lots || []).map(l => `${l.id || ''} ${l.description || ''}`), ...projectText, ...noticeText, ...(c.supplierIds || []).map(s => `${s.id} ${s.siren || ''}`)].join(' '));
    const citations = getLegalContext(c);
    const legalMatch = !legal || (legal === 'direct' ? c.directAward === true : legal === 'cited' ? citations.length > 0 : citations.some(item => item.article === legal));
    const evaluated = getAssessment(c);
    const assessmentMatch = !assessment || (assessment === 'unevaluated' ? scoreFor(c) == null : assessment === 'zero' ? scoreFor(c) === 0 : assessment === 'partial' ? evaluated.unknown > 0 || evaluated.unknownApplicability > 0 : false);
    const sectorMatch = !sector || getSector(c).code === sector;
    const projectMatch = !project || (project === '@documented' ? Boolean(c.project) : c.project?.id === project);
    return terms.every(term => text.includes(term)) && assessmentMatch && noticeMatch && legalMatch && sectorMatch && projectMatch &&
      (minimum <= 0 || (c.amount != null && c.amount >= minimum)) && (minScore <= 0 || (scoreFor(c) != null && scoreFor(c) >= minScore)) &&
      (!flagged || getIndicators(c).length > 0) && (!official || c.officialFinding === true) &&
      (!indicator || (indicator === 'official-finding' ? c.officialFinding === true : getIndicators(c).some(i => i.id === indicator)));
  }).sort((a, b) => {
    const direction = ['score-asc', 'amount-asc', 'date-asc', 'publication-asc'].includes(sort) ? 1 : ['sector', 'buyer', 'supplier', 'offers'].includes(sort) ? 1 : -1;
    const field = sort.startsWith('score') ? 'score' : sort.startsWith('amount') ? 'amount' : sort.startsWith('date') ? 'date' : sort.startsWith('publication') ? 'publication' : sort === 'sector-desc' ? 'sector' : sort;
    const raw = c => field === 'score' ? scoreFor(c) : field === 'amount' ? c.amount : field === 'date' ? (c.date ? Date.parse(c.date) : null) :
      field === 'publication' ? (c.publicationDate ? Date.parse(c.publicationDate) : null) : field === 'sector' ? getSector(c).label : field === 'buyer' ? c.buyer : field === 'supplier' ? c.supplier :
      field === 'official' ? (c.officialFinding === true ? 1 : null) : field === 'offers' ? c.offers : field === 'increase' ? increaseFor(c) : null;
    const av = raw(a), bv = raw(b);
    const nullOrder = av == null ? (bv == null ? 0 : 1) : bv == null ? -1 : 0;
    if (nullOrder) return nullOrder;
    if (field === 'sector' && av === 'Sector not specified' && bv !== av) return 1;
    if (field === 'sector' && bv === 'Sector not specified' && av !== bv) return -1;
    const comparison = typeof av === 'string' ? collator.compare(av, bv) : av === bv ? 0 : av > bv ? 1 : -1;
    return comparison * direction || ((scoreFor(b) ?? -1) - (scoreFor(a) ?? -1)) || collator.compare(a.id, b.id);
  });
}

// Everything from JSON is inserted as text, never as HTML.
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function renderNoticeEvidence(cell, c) {
  const e = c.noticeEvidence;
  function sourceLink(url, label) {
    const link = element('a', label); link.href = safeSource(url); link.target = '_blank'; link.rel = 'noopener noreferrer'; return link;
  }
  cell.append(element('h3', 'Full notice · declared explanations and criteria'),
    element('p', `Version ${e.version || '—'} · notice UUID ${e.noticeUuid || '—'} · lot ${e.lotId || '—'} · local lot reference ${e.lotReference || '—'} · ${e.kind}. A version/lot is a document, not a single attributed contract.`),
    element('p', `Resolved buyers: ${e.buyers.map(b => `${b.name || '—'} (${b.siret || '—'})`).join(' / ')}. ${e.buyers.length > 1 ? 'Joint purchase: do not attribute all services or expenses to Tours.' : ''}`),
    element('p', `Published legal framework: ${e.legalBasis || '—'} (directive/general framework, not a justification for an R2122 derogation).`));
  cell.append(element('h3', 'Text declared by the buyer — whole-procedure scope'), element('p', 'These texts may concern lots other than the one displayed. Their presence proves neither their applicability to this lot nor their legal validity. No additional points.'));
  if (e.procedureDescription) cell.append(element('blockquote', e.procedureDescription), sourceLink(e.source, 'Exact source · TenderingProcess/Description'));
  else cell.append(element('p', 'Procedure description absent from the reproduced field: justification unknown in this extract, not absence of justification.'));
  for (const j of e.justifications) {
    cell.append(element('p', `Structured declaration · list ${j.category || '—'} · code ${j.code || '—'} · whole-procedure scope.`));
    if (j.text) cell.append(element('blockquote', j.text));
    cell.append(element('small', j.path, 'provenance'));
  }
  cell.append(element('p', `Explicitly declared acceleration: ${e.accelerated == null ? 'unknown' : e.accelerated ? 'yes' : 'no'} · Declared relaunch: ${e.relaunch == null ? 'unknown' : e.relaunch ? 'yes' : 'no'}. A false acceleration value is not a justification of exclusivity.`));
  cell.append(element('h3', `Award criteria for lot ${e.lotId || 'unknown'}`));
  if (!e.awardCriteria.length) cell.append(element('p', 'Criteria not provided in the reproduced fields. They may appear in the consultation rules. Candidate-selection criteria are not substituted for award criteria.'));
  for (const a of e.awardCriteria) {
    const box = element('div', null, 'notice-criterion');
    box.append(element('p', `${a.type || 'Type not specified'} · ${a.name || a.description || a.formula || 'Unknown label'}`));
    if (a.description && a.name) box.append(element('p', a.description));
    if (a.formula) box.append(element('p', `Published method: ${a.formula}`));
    if (!a.parameters.length) box.append(element('p', 'Numeric weighting unknown in this field.'));
    for (const p of a.parameters) box.append(element('p', `Published value: ${p.rawValue ?? '—'} · parameter code ${p.code || '—'} · list ${p.codeList || '—'}. Codes and values kept, without arbitrary conversion into percentages or sums.`));
    box.append(element('small', a.path, 'provenance')); cell.append(box);
  }
  cell.append(element('p', 'Criteria and weights are context: a low price weight is not automatically suspect and earns no points.'));
  cell.append(element('h3', 'Publications, deadlines and TED matching'), element('p', `BOAMP publication: ${e.publicationDate || '—'} · Declared dispatch: ${e.dispatchDate || '—'} ${e.dispatchTime || ''}. The dispatch date and the award date are not used as the initial publication.`),
    element('p', `BOAMP bid deadline for the lot: ${e.deadline.date || '—'} ${e.deadline.time || ''}. Times and time zones kept as published.`));
  for (const t of e.ted) {
    const line = element('p', `TED ${t.publicationNumber} · publication ${t.publicationDate || '—'} · version ${t.version || '—'} · ${t.versionMatches ? 'UUID and version match' : 'different version: no substitution'} · deadline ${t.deadlineDate || '—'} ${t.deadlineTime || ''}. `);
    line.append(sourceLink(t.source, 'Official XML'), element('span', ' · '));
    const local = element('a', 'Downloaded local XML'); local.href = t.localFile; local.setAttribute('download', ''); line.append(local); cell.append(line);
  }
  if (e.deadlineConflict) cell.append(element('p', 'Diverging deadlines between sources: calculation excluded.'));
  if (e.linkedNoticeLots.length) {
    cell.append(element('h3', 'Partial chronology of the same lot — explicit references'), element('p', 'These links are documented, but their presence does not guarantee that all earlier versions or publications were recovered.'));
    for (const n of e.linkedNoticeLots) cell.append(element('p', `${n.relation} · ${n.noticeId} · ${n.lotId} · version ${n.version || '—'} · ${n.kind} · publication ${n.publicationDate || '—'} · bid deadline ${n.deadline || '—'}. ${n.basis}`), sourceLink(n.source, 'Explicitly linked notice'));
  }
  cell.append(element('h3', 'Explicit references and documents'));
  for (const r of e.references) {
    cell.append(element('p', `${r.kind} · ${r.id} · ${r.ambiguous ? 'ambiguous reference' : r.matchedNoticeIds.length ? 'BOAMP notice resolved: '+r.matchedNoticeIds.join(', ') : 'reference kept, not resolved to a BOAMP notice'}. ${r.path}`));
    if (r.tedSource) cell.append(sourceLink(r.tedSource, 'Earlier TED notice explicitly cited and downloaded'));
  }
  for (const n of e.sameProcedureNotices) cell.append(element('p', 'Same procedure UUID, without automatic attribution to the lot: '), sourceLink(n.source, n.id));
  for (const d of e.documents) cell.append(element('p', 'Buyer-profile document cited, not downloaded: '), sourceLink(d.url, 'Open the document / profile'));
  cell.append(element('p', 'No merging with DECP. No amounts, ceilings or notice versions summed. The bidding period remains non-assessable until the complete chain and the relevant initial publication are established.'));
}

function startExplorer() {
  const body = document.querySelector('#contracts');
  const status = document.querySelector('#status');
  const fileHelp = document.querySelector('#file-help');
  const controls = Object.fromEntries(['search', 'minimum', 'flagged', 'official', 'indicator', 'legal', 'notice-context', 'assessment', 'sort', 'sector', 'project', 'group-by', 'min-score'].map(id => [id, document.getElementById(id)]));
  const datasetSelect = document.querySelector('#dataset');
  const datasets = {
    tours: { path: 'data/tours-notices.json', coverage: 'data/tours-notices-coverage.json', note: 'Tours · full 2025 notices and out-of-period linked references: 25 buyer-verified notices, 66 version/lot rows, including labelled joint purchases. 25 rows with award criteria; procedure texts and 2 corrections kept. TED XML matched by UUID and version, not by name. These are documents, not 66 contracts or expenses: no bidding-period score without a reliable chain.' },
    cities: { path: 'data/decp-cities.json', coverage: 'data/decp-cities-coverage.json', note: 'Six pre-selected municipalities: Rennes, Nantes, Bordeaux, Grenoble, Dijon and Tours (not the metro areas). Notifications 2024–2025: 1,865 published rows, 1,270 buyer/identifier groups, of which 172 ambiguous ones excluded from calculations. 355 groups with published modifications. Non-representative cohort, not all spending. 100 SIRENs enriched out of 703 identified: current names and status, not verified at the contract date. Separate datasets, no cross-source sums.' },
    consultations: { path: 'data/consultations.json', coverage: 'data/consultations-coverage.json', note: '10 initial BOAMP notices from 3 February 2025, first identifiers among 200, selected before any calculation. One correction and three award notices linked explicitly. Notice-level rows, not attributed contracts or expenses. Chains not certified complete: no bidding-period score in this extract. No independent TED download.' },
    decp: { path: 'data/decp-history.json', coverage: 'data/decp-coverage.json', note: 'Exploratory 24-month history: 2,594 DECP contracts from Paris and Ardèche, notified in 2024–2025. Every row returned by the source for these two SIRETs was examined; this does not guarantee that all actual purchases were published. Paris was chosen for volume, Ardèche for the availability of modifications: this choice is not representative. Modifications may be later than 2025. Suppliers identified by SIRET; three names in the Paris dossier are confirmed by the Annuaire des entreprises. The eight official findings are in the other dataset.' },
    boamp: { path: 'data/contracts.json', coverage: 'data/coverage.json', note: '3,010 records: 3,000 BOAMP lots sampled from February–April 2025 publications, two Mauges lots and eight documented CRC dossiers. Some findings concern sets of orders, not an individual award. A finding does not extend to a municipality’s other purchases. This sample does not allow an exhaustive competition history to be computed.' }
  };
  const provenance = { verified: 'Documented · public source', unverified: 'To verify · research lead', synthetic: 'Fictional · pedagogical comparison' };
  const money = new Intl.NumberFormat('en-IE', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 });
  const dateFormat = new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', day: 'numeric', month: 'short', year: 'numeric' });
  let contracts = [];
  let loaded = false;
  let loadVersion = 0;
  let page = 0;
  const pageSize = 50;
  const pagination = document.querySelector('#pagination');
  const previous = document.querySelector('#previous');
  const next = document.querySelector('#next');
  const expanded = new Set();
  const viewport = document.querySelector('.table-wrap');
  const projectPanel = document.querySelector('#project-panel');
  let projectCatalog = new Map();

  function fillSelect(select, options) {
    const previousValue = select.value;
    select.replaceChildren(...options.map(([value, label]) => { const option = element('option', label); option.value = value; return option; }));
    select.value = options.some(([value]) => value === previousValue) ? previousValue : '';
  }
  function showProject(id) {
    controls.search.value = '';
    controls.minimum.value = '';
    controls['min-score'].value = '0';
    controls.assessment.value = '';
    controls['notice-context'].value = '';
    controls.indicator.value = '';
    controls.legal.value = '';
    controls.sector.value = '';
    controls.flagged.checked = false;
    controls.official.checked = false;
    controls.project.value = id;
    controls['group-by'].value = id ? 'project' : '';
    page = 0;
    render();
    viewport.scrollTop = 0;
  }
  function renderProjectPanel() {
    projectPanel.replaceChildren();
    const project = projectCatalog.get(controls.project.value);
    projectPanel.hidden = !project;
    if (!project) return;
    projectPanel.append(element('h2', project.title), element('p', project.basis));
    const reference = element('a', 'Public reference notice of the dossier');
    reference.href = safeSource(project.source);
    reference.target = '_blank';
    reference.rel = 'noopener noreferrer';
    projectPanel.append(reference);
    const list = element('ol', null, 'evidence-list');
    (project.evidence || []).forEach(evidence => {
      const item = element('li');
      const link = element('a', `${evidence.date} — ${evidence.label}`);
      link.href = safeSource(evidence.source);
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      item.append(link, element('span', ` · ${evidence.type}. ${evidence.description}`));
      list.append(item);
    });
    projectPanel.append(list, element('p', 'These documentary elements earn no additional points and do not constitute an official finding. No project amount or score is summed.'));
    const clear = element('button', 'Back to all records', 'clear-group');
    clear.type = 'button';
    clear.addEventListener('click', () => showProject(''));
    projectPanel.append(clear);
  }

  function render() {
    if (!loaded) return;
    const minimum = Math.max(0, Number(controls.minimum.value) || 0);
    const filtered = selectContracts(contracts, { search: controls.search.value, minimum, minScore: Number(controls['min-score'].value) || 0, flagged: controls.flagged.checked, official: controls.official.checked, indicator: controls.indicator.value, legal: controls.legal.value, noticeContext: controls['notice-context'].value, assessment: controls.assessment.value, sector: controls.sector.value, project: controls.project.value, sort: controls.sort.value });
    const arrangement = arrangeGroups(filtered, controls['group-by'].value);
    const visible = arrangement.rows;
    renderProjectPanel();
    const pageCount = Math.max(1, Math.ceil(visible.length / pageSize));
    page = Math.min(page, pageCount - 1);
    const pageRows = visible.slice(page * pageSize, (page + 1) * pageSize);
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
          headerCell.colSpan = 9;
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
      const supplierCell = element('td', c.supplier || '—');
      for (const p of c.supplierProfiles || []) supplierCell.append(element('small', `${p.name} · current name (${p.retrievedAt.slice(0, 10)}), not historical`, 'provenance'));
      const dateCell = element('td', c.date ? dateFormat.format(new Date(c.date)) : c.noticeEvidence ? c.publicationDate || '—' : '—');
      if (c.noticeEvidence) dateCell.append(element('small', 'BOAMP publication', 'provenance'));
      row.append(dateCell, element('td', c.buyer), supplierCell);
      const objectCell = element('td');
      const button = element('button', c.description, 'row-toggle');
      button.type = 'button';
      button.setAttribute('aria-expanded', String(expanded.has(c.id)));
      button.setAttribute('aria-controls', `detail-${index}`);
      objectCell.append(button, element('small', provenance[c.dataStatus], 'provenance'));
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
      if ([c.amount, c.offers, c.durationMonths, c.directAward].some(value => value == null)) {
        objectCell.append(element('small', 'Partial data · see details', 'provenance'));
      }
      if (c.findingScope) objectCell.append(element('small', c.findingScope === 'aggregate' ? 'Finding on a set of orders' : 'Finding attached to the described contract', 'provenance'));
      const amountPrefix = { 'at-least': '≥ ', 'more-than': '> ', approximate: '≈ ' }[c.amountQualifier] || '';
      const sector = getSector(c);
      const sectorCell = element('td', sector.label);
      sectorCell.append(element('small', c.cpv || 'unknown CPV', 'provenance'));
      row.append(objectCell, sectorCell, element('td', c.amount == null ? '—' : amountPrefix + money.format(c.amount), 'numeric'), element('td', c.offers ?? '—', 'numeric'));
      const badges = element('td');
      if (indicators.length) indicators.forEach(i => {
        const badge = element('span', `${i.label} · ${i.weight} pts · ${i.severityLabel.toLocaleLowerCase('en')}`, `badge severity-${i.severity}${i.id === 'official-finding' ? ' official' : ''}`);
        badge.title = `Vigilance level ${i.severityLabel.toLocaleLowerCase('en')}; raw weight, not summed with the other signals of the same family. ${i.explanation}`;
        badges.append(badge);
      });
      const breakdown = getScoreBreakdown(c);
      const assessment = breakdown.assessment;
      const scoreValue = breakdown.score;
      if (!indicators.length) badges.append(element('span', scoreValue == null ? 'Checks not assessed' : 'No signal among the evaluated checks', 'muted'));
      if (c.officialFinding === true) badges.append(element('span', 'Official finding · outside the index', 'badge official'));
      const level = scoreLevel(scoreValue, hasIncompleteData(c));
      const score = element('td', null, 'numeric');
      const chip = element('span', scoreValue == null ? 'Not assessed' : `${scoreValue} / 100`, `score-chip level-${level.id}`);
      chip.title = `${level.label} — editorial index, not a probability nor legal gravity.`;
      const coverageLabel = assessment.excludedReason ? 'Calculations excluded' : assessment.applicable ? `${assessment.signals} signal(s) · ${assessment.evaluated}/${assessment.applicable} known-applicable checks evaluated` : 'No check with established applicability';
      score.append(chip, element('small', coverageLabel, 'provenance'));
      if (assessment.unknownApplicability) score.append(element('small', `${assessment.unknownApplicability} additional unknown applicability(ies)`, 'provenance'));
      score.setAttribute('aria-label', `${scoreValue == null ? 'Index not assessed.' : `Heuristic index: ${scoreValue} out of 100.`} ${coverageLabel}. ${assessment.unknownApplicability} unknown applicabilities.`);
      row.append(badges, score);
      const detail = element('tr', null, 'detail-row');
      detail.id = `detail-${index}`;
      detail.hidden = !expanded.has(c.id);
      const cell = element('td');
      cell.colSpan = 9;
      cell.append(element('p', `${provenance[c.dataStatus]} · Reference: ${c.id}`), element('p', `Procedure: ${c.procedure || 'not specified'} · Duration: ${c.durationMonths == null ? 'not specified' : `${c.durationMonths} months`}`));
      if (c.findingScope) cell.append(element('p', c.findingScope === 'aggregate' ? 'Scope: a set of orders or services examined by the CRC, not an individual award. This finding is not extended to the buyer’s or supplier’s other contracts.' : 'Scope: the contract described in this record. This finding is not extended to the buyer’s or supplier’s other contracts.'));
      if (c.dateNote) cell.append(element('p', `Date: ${c.dateNote}`));
      if (c.amountBasis) cell.append(element('p', `Amount scope: ${c.amountBasis}`));
      if (c.notes) cell.append(element('p', c.notes));
      cell.append(element('p', `Identifiers — Buyer SIRET: ${c.buyerSiret || '—'} · Contract: ${c.contractId || '—'} · Lot: ${c.lotId || '—'} · CPV: ${c.cpv || '—'}`));
      if (c.noticeId || c.publicationDate) cell.append(element('p', `Notice: ${c.noticeId || '—'} · Publication: ${c.publicationDate || '—'}`));
      if (c.supplierIds?.length) cell.append(element('p', `Holders: ${c.supplierIds.map(s => `${s.identifierType || 'Identifier'} ${s.id}${s.siren ? ` · SIREN ${s.siren}` : ''}`).join(' / ')}`));
      if (c.directAward === true || legalContext.length) {
        cell.append(element('h3', 'Declared legal basis — context, not an indicator'), element('p', 'A citation proves neither that the legal conditions are met nor an irregularity. A single offer received does not demonstrate exclusivity. No points added; no inference about other contracts.'));
        if (!legalContext.length) cell.append(element('p', 'Article R2122 not found in the imported object or procedure. Justification unknown in this extract, not absence of justification.'));
        if (c.initialConflicts?.length) cell.append(element('p', 'Diverging initial versions: context of the displayed text only, not validation of the basis. The variants remain to be examined in the source.'));
        for (const context of legalContext) {
          cell.append(element('p', `${context.article} · ${context.label} · exact citation: “${context.citation}”`), element('blockquote', context.excerpt));
          const link = element('a', `Source of the published text (${context.field === 'description' ? 'object' : 'procedure'})`);
          link.href = safeSource(context.source); link.target = '_blank'; link.rel = 'noopener noreferrer';
          cell.append(link);
        }
      }
      if (c.identifierNote) cell.append(element('p', c.identifierNote));
      if (c.supplierProfiles?.length) {
        cell.append(element('h3', 'Current public identity — not historical'), element('p', 'SIREN matching derived from an explicitly typed French identifier. Name and status of the legal unit observed at retrieval time, not those of each establishment nor those at the contract date. No points for the name or status; no link between companies inferred.'));
        for (const p of c.supplierProfiles) {
          const state = p.administrativeState === 'A' ? 'active' : p.administrativeState === 'C' ? 'cessation declared' : 'unknown';
          const paragraph = element('p', `${p.name} · SIREN ${p.siren} · current legal-unit status: ${state} · snapshot ${p.retrievedAt}. `);
          const link = element('a', 'Annuaire des entreprises — exact source');
          link.href = safeSource(p.source); link.target = '_blank'; link.rel = 'noopener noreferrer';
          paragraph.append(link); cell.append(paragraph);
        }
      } else if (c.cohortId === CITIES_COHORT) cell.append(element('p', 'Current identity not enriched in this extract: outside the 100-SIREN sample, ambiguous identity or information unavailable. The historical name remains unknown.'));
      if (c.executionModalities || c.techniques) cell.append(element('p', `Published modalities: ${c.executionModalities || '—'} · Techniques: ${c.techniques || '—'}. Declared amounts, not observed spending; do not sum framework-agreement ceilings.`));
      if (c.frameworkId) cell.append(element('p', `Parent framework agreement cited in the source: ${c.frameworkId}. A subsequent contract is not a distinct project by mere deduction.`));
      if (c.project) cell.append(element('p', `Documented project: ${c.project.title}. ${c.project.basis}`));
      cell.append(element('h3', `Heuristic index v${SCORE_VERSION} and coverage`));
      if (assessment.excludedReason) cell.append(element('p', assessment.excludedReason));
      cell.append(element('p', scoreValue == null ? 'Not assessed: no applicable check could be evaluated. This is not a zero score.' : `Competition: ${breakdown.competition} (maximum); execution/duration: ${breakdown.execution} (maximum). Total: ${scoreValue}/100. No compensation for unknown information.`),
        element('p', `${assessment.evaluated}/${assessment.applicable} checks with established applicability evaluated; ${assessment.unknownApplicability} unknown applicabilities reported separately; ${assessment.notApplicable} checks out of scope. The 8 checks are detailed below.`),
        element('p', 'Separate financial stake: the declared amount increases no weight. An increase uses only the comparable percentage, not a payments total. No points for an official finding, a project or an R2122 citation.'));
      const checks = element('ul', null, 'assessment-checks');
      const states = { signal: 'Signal', clear: 'Evaluated · threshold not crossed', unknown: 'Not assessable', 'not-applicable': 'Out of scope' };
      for (const r of assessment.checks) checks.append(element('li', `${r.label} — ${states[r.status]}${r.applicability === 'unknown' ? ' (unknown applicability)' : ''}${r.weight != null ? ` · ${r.weight} raw points` : ''}. ${r.reason}`));
      cell.append(checks);
      if (c.officialFinding === true) cell.append(element('h3', 'Documented official finding — separate from the index'), element('p', `This finding keeps its scope, source and response; it earns no heuristic points and is not a presumed conviction. Passage: ${c.sourceReference || '—'}.`));
      if (c.noticeEvidence) renderNoticeEvidence(cell, c);
      if (c.consultation) {
        const timeline = c.consultation;
        cell.append(element('h3', 'Consultation: publications and versions'), element('p', `Internal reference: ${timeline.procedureReference || '—'} · Procedure UUID: ${timeline.procedureId || '—'} · Lot analysed: ${timeline.lotId || '—'}. A row represents a notice, not an award.`));
        const list = element('ol');
        for (const n of [...timeline.notices, ...(timeline.matchedAwards || [])]) {
          const item = element('li');
          const link = element('a', `${n.id} · ${n.kind} · state ${n.publicationState || '—'} · version ${n.version || '—'} · publication ${n.publicationDate || '—'}`);
          link.href = safeSource(n.source); link.target = '_blank'; link.rel = 'noopener noreferrer';
          item.append(link, element('span', ` · Published deadline: ${n.deadline || '—'} · Procedure: ${n.procedureType || '—'} · Accelerated: ${n.accelerated == null ? 'unknown' : n.accelerated ? 'yes' : 'no'} · Earlier references: ${(n.previousNoticeIds || []).join(', ') || '—'}`));
          if (n.correctionText) item.append(element('p', n.correctionText));
          list.append(item);
        }
        for (const lot of timeline.lots || []) cell.append(element('p', `Published lot: ${lot.id || 'unknown identifier'} · ${lot.description || '—'} · CPV ${(lot.cpv || []).join(', ') || '—'} · raw deadline ${lot.deadline || '—'}. No per-lot score without a verified calendar.`));
        const period = getBiddingPeriod(c);
        cell.append(list, element('p', period.status === 'available' ? `Bidding period: ${period.days.toFixed(2)} days (upper bound), last deadline ${period.deadline}.` : `Bidding period not assessable: ${period.reason}`));
        (timeline.exclusions || []).forEach(reason => cell.append(element('p', reason)));
        cell.append(element('p', 'An award notice linked to this notice does not prove a match for every lot; no amount, holder or finding is transferred.'));
      }
      if (c.dataFamily === 'decp') {
        cell.append(element('h3', 'Published contract history'));
        cell.append(element('p', `Price form: ${c.priceForm || '—'} · Type: ${c.priceType || '—'}. Declared amounts, not observed payments.`));
        if (c.initialConflicts?.length) {
          cell.append(element('p', `Contradictory initial versions (${c.initialConflicts.join(', ')}). No chronology is inferred from these differences.`));
          const alternatives = element('ul');
          (c.initialAlternatives || []).forEach((a, n) => {
            const item = element('li', `Initial variant ${n + 1}: ${a.amount == null ? 'unknown amount' : money.format(a.amount)} — this is not a dated amendment.`);
            if (c.cohortId === CITIES_COHORT) item.append(element('p', `Notification: ${a.date || '—'} · Publication: ${a.publicationDate || '—'} · CPV: ${a.cpv || '—'} · Offers: ${a.offers ?? '—'} · Procedure: ${a.procedure || '—'} · Holders: ${Array.isArray(a.supplierIds) ? a.supplierIds.map(s => s.id).join(' / ') || '—' : '—'}`), element('p', a.description || 'Unknown object in this variant.'));
            alternatives.append(item);
          });
          cell.append(alternatives);
        }
        if (c.modificationConflicts?.length) cell.append(element('p', `Conflicting modifications: ${c.modificationConflicts.map(m => `${m.id} (${m.fields.join(', ')})`).join(' ; ')}. No evolution calculation.`));
        if (c.history?.length) {
          const historyTable = element('table', null, 'history-table');
          historyTable.append(element('caption', 'Available published versions — absence of a published amendment ≠ absence of a real modification.'));
          const head = element('thead');
          const heading = element('tr');
          ['Event', 'Notification', 'Publication', 'Declared amount'].forEach(label => { const th = element('th', label); th.scope = 'col'; heading.append(th); });
          head.append(heading);
          const entries = element('tbody');
          c.history.forEach(event => {
            const entry = element('tr');
            entry.append(element('td', event.kind === 'initial' ? 'Initial award' : `Modification ${event.id || '—'}`), element('td', event.date || '—'), element('td', event.publicationDate || '—'), element('td', event.amount == null ? '—' : money.format(event.amount)));
            entries.append(entry);
          });
          historyTable.append(head, entries);
          cell.append(historyTable);
        }
        const evolution = getAmountEvolution(c);
        cell.append(element('p', evolution.status === 'available' ? `Analysable declared evolution: +${money.format(evolution.delta)} (+${evolution.percentage.toLocaleString('en-IE', { maximumFractionDigits: 1 })} %), from ${money.format(evolution.initialAmount)} to ${money.format(evolution.revisedAmount)}, on ${evolution.date}. Quantities or scope may have changed; consult the source.` : `Increase calculation unavailable: ${evolution.reason}`));
        const supplierContext = c.supplierContext;
        if (supplierContext) cell.append(element('p', `Single identified holder: SIREN ${getSupplierIdentity(c)}. Same buyer/CPV ${supplierContext.cpvGroup}, 2024–2025: ${supplierContext.wins}/${supplierContext.known} contracts to the known holder, out of ${supplierContext.total} eligible contracts (${Math.round(supplierContext.coverage * 100)} % coverage); ${supplierContext.directCount} awards without competition identified to this holder, all amounts; ${supplierContext.directKnownCount}/${supplierContext.supplierContracts} known competitive statuses. ${supplierContext.sufficient ? 'Sufficient sample to examine concentration.' : 'Concentration not computable: insufficient sample or coverage.'} The statistics do not change with your filters.`));
        const context = c.competitionContext;
        cell.append(element('p', context ? `Retrospective context ${context.start}–${context.end}, same buyer and CPV ${context.cpvGroup}: ${context.single} single-offer contracts / ${context.known} with a known count, out of ${context.total} eligible competitive contracts (${Math.round(context.coverage * 100)} % coverage). ${context.sufficient ? 'Coverage thresholds met.' : 'Insufficient sample or coverage: no repetition indicator.'} Computed over the whole cohort, unchanged by your filters.` : 'Repeated competition not computable: procedure not explicitly competitive, version conflict, missing identifier or contract outside the cohort.'));
      }
      if (indicators.length) {
        const list = element('ul');
        indicators.forEach(i => list.append(element('li', `${i.label} — ${i.severityLabel}, raw weight ${i.weight}, family ${i.family}. ${i.explanation}`)));
        cell.append(list);
      } else cell.append(element('p', scoreValue == null ? 'No heuristic conclusion: not assessed. The documents and findings remain consultable.' : 'No threshold crossed among the evaluated checks only. Unknowns do not prove an absence of risk.'));
      if (c.sourceReference) cell.append(element('p', `Source passage: ${c.sourceReference}`));
      if (safeSource(c.source)) {
        const link = element('a', c.sourceLabel || 'Consulter la source originale');
        link.href = safeSource(c.source);
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        cell.append(link);
      } else cell.append(element('p', c.dataStatus === 'synthetic' ? 'Source: none, entirely fictional example.' : 'Original source not provided: this lead remains to be verified.'));
      for (const [key, label] of [['reportUrl', 'Original official report'], ['responseLink', 'Official response of the audited organization'], ['supplierNameSource', 'Supplier name — Annuaire des entreprises']]) {
        if (!safeSource(c[key])) continue;
        const paragraph = element('p');
        const link = element('a', label);
        link.href = safeSource(c[key]);
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        paragraph.append(link);
        cell.append(paragraph);
      }
      detail.append(cell);
      function toggle() {
        if (expanded.has(c.id)) expanded.delete(c.id); else expanded.add(c.id);
        detail.hidden = !expanded.has(c.id);
        button.setAttribute('aria-expanded', String(!detail.hidden));
      }
      button.addEventListener('click', event => { event.stopPropagation(); toggle(); });
      row.addEventListener('click', () => { if (!window.getSelection()?.toString()) toggle(); });
      fragment.append(row, detail);
    });
    if (!visible.length) {
      const row = element('tr');
      const cell = element('td', 'No result. Try lowering the minimum amount or changing the filters.');
      cell.colSpan = 9;
      row.append(cell);
      fragment.append(row);
    }
    body.replaceChildren(fragment);    status.textContent = `${visible.length} / ${contracts.length} results · ${visible.filter(c => getIndicators(c).length).length} with a heuristic signal · ${visible.filter(c => getVigilanceScore(c) == null).length} not assessed · ${visible.filter(c => c.officialFinding === true).length} separate findings · Rows ${visible.length ? page * pageSize + 1 : 0}–${page * pageSize + pageRows.length} · Vigilance index: a sorting tool only.`;
    pagination.hidden = visible.length <= pageSize;
    previous.disabled = page === 0;
    next.disabled = page >= pageCount - 1;
    document.querySelector('#page-status').textContent = `Page ${page + 1} / ${pageCount} · ${pageSize} rows per page`;
  }
  function accept(data) {
    contracts = prepareContracts(data);
    const sectors = [...new Map(contracts.map(c => { const s = getSector(c); return [s.code, s]; })).values()].sort((a, b) => a.code === 'unknown' ? 1 : b.code === 'unknown' ? -1 : a.label.localeCompare(b.label, 'en'));
    fillSelect(controls.sector, [['', 'All sectors'], ...sectors.map(s => [s.code, `${s.code === 'unknown' ? '' : s.code + ' · '}${s.label}`])]);
    projectCatalog = new Map(contracts.filter(c => c.project).map(c => [c.project.id, c.project]));
    fillSelect(controls.project, [['', 'All records'], ...(projectCatalog.size ? [['@documented', 'Documented projects only']] : []), ...[...projectCatalog.values()].map(p => [p.id, p.title])]);
    controls.project.disabled = projectCatalog.size === 0;
    loaded = true;
    page = 0;
    const missing = key => contracts.filter(c => c[key] == null).length;
    const conflictCount = contracts.filter(c => c.initialConflicts?.length).length;
    const withMods = contracts.filter(c => c.history?.some(event => event.kind === 'modification')).length;
    const enrichedCount = contracts.filter(c => c.supplierProfiles?.length).length;
    document.querySelector('#completeness').textContent = `In the loaded file: ${missing('amount')} amounts, ${missing('offers')} offer counts and ${missing('durationMonths')} durations not provided out of ${contracts.length} records. ${conflictCount} groups with diverging initial values; ${withMods} histories containing a published modification. ${enrichedCount ? `${enrichedCount} records with an enriched current public name (not historical). ` : ''}Official findings are not subject to an exhaustive automatic search.`;
    expanded.clear();
    render();
  }
  function fail(error) {
    loaded = false;
    contracts = [];
    body.replaceChildren();
    pagination.hidden = true;
    projectPanel.hidden = true;
    projectPanel.replaceChildren();
    document.querySelector('#completeness').textContent = '';
    status.textContent = `Unable to load the data: ${error.message}`;
    fileHelp.hidden = false;
  }
  Object.values(controls).forEach(control => control.addEventListener('input', () => { page = 0; render(); viewport.scrollTop = 0; }));
  previous.addEventListener('click', () => { if (page > 0) { page--; render(); viewport.scrollTop = 0; } });
  next.addEventListener('click', () => { page++; render(); viewport.scrollTop = 0; });
  document.querySelector('#file').addEventListener('change', async event => {
    const file = event.target.files[0];
    if (!file) return;
    const version = ++loadVersion;
    try {
      const data = JSON.parse(await file.text());
      if (version === loadVersion) {
        accept(data);
        document.querySelector('#dataset-note').textContent = `Local file loaded: ${file.name}. The statistics describe this file; they do not prove its completeness. Use the dataset selector to reload a provided dataset.`;
        document.querySelector('#coverage-link').hidden = true;
      }
    }
    catch (error) { if (version === loadVersion) fail(error); }
  });
  async function loadDataset() {
    const selected = datasets[datasetSelect.value];
    const version = ++loadVersion;
    loaded = false;
    contracts = [];
    body.replaceChildren();
    pagination.hidden = true;
    document.querySelector('#completeness').textContent = '';
    document.querySelector('#dataset-note').textContent = selected.note;
    document.querySelector('#coverage-link').href = selected.coverage;
    document.querySelector('#coverage-link').hidden = false;
    document.querySelector('#file-path').textContent = selected.path;
    document.querySelector('#file').value = '';
    fileHelp.hidden = location.protocol !== 'file:';
    controls.search.value = '';
    controls.minimum.value = '';
    controls.assessment.value = '';
    controls['notice-context'].value = '';
    controls.indicator.value = '';
    controls.legal.value = '';
    controls.sector.value = '';
    controls.project.value = '';
    controls['group-by'].value = '';
    controls['min-score'].value = '0';
    projectPanel.hidden = true;
    projectPanel.replaceChildren();
    viewport.scrollTop = 0;
    controls.flagged.checked = false;
    controls.official.checked = false;
    status.textContent = 'Loading data…';
    try {
      const response = await fetch(selected.path);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (version === loadVersion) accept(data);
    } catch (error) { if (version === loadVersion) fail(error); }
  }
  datasetSelect.addEventListener('change', loadDataset);
  loadDataset();
}

if (typeof document !== 'undefined') startExplorer();
