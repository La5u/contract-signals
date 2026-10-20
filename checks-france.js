// France (DECP, BOAMP, notices): bidding period, software-maintenance context, legal direct-award
// thresholds and the French check set (docs/score-v3.md).
'use strict';

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
  // Include every regime intersecting the possible consultation window, not just the
  // immediately preceding one (works changed twice within 180 days in 2020).
  let previous = current;
  for (let k = i; k > 0 && Date.parse(date) < Date.parse(series[k][0]) + FR_THRESHOLD_TRANSITION_DAYS * 864e5; k--) {
    previous = Math.min(previous, series[k - 1][1]);
  }
  return { current, previous };   // below every possible threshold: certain; from current: certain
}
function frenchDirectAwardEligibility(c) {
  const euros = n => `€${n.toLocaleString('en-GB')}`;
  if (c.amount == null && c.verification?.placeholder) return { status: 'unknown', reason: 'The published amount is a placeholder (10 EUR or less) and no source gives a real amount: cannot tell whether the contract was below the legal threshold. Not assessed.' };
  const range = c.verification?.amountRange;
  if (c.amount != null && Array.isArray(range)) {
    // Sources disagree on the amount: only a conclusion that holds at both ends is used.
    const [low, high] = range.map(amount => frenchDirectAwardEligibility({ ...c, amount, verification: null }).status);
    if (low !== high) return { status: 'unknown', reason: `Sources disagree on the amount (${euros(range[0])} to ${euros(range[1])} HT), on either side of the legal threshold: not assessed.` };
  }
  if (c.amount == null) return { status: 'unknown', reason: 'Declared amount missing: cannot tell whether the contract was below the legal threshold for an award without publicity or competition. Not assessed.' };
  if (!(c.amount > 0)) return { status: 'unknown', reason: 'Declared amount is nonpositive: cannot tell whether the contract was below the legal threshold for an award without publicity or competition. Not assessed.' };
  if (recordCurrency(c) !== 'EUR') return { status: 'unknown', reason: 'Declared currency is unknown or not EUR: the French euro threshold cannot be applied. Not assessed.' };
  if (!/^\d{4}-\d{2}-\d{2}$/.test(c.date || '') || !validIsoDate(c.date)) return { status: 'unknown', reason: 'Contract date missing or invalid: the legal threshold in force cannot be determined. Not assessed.' };
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

function getAssessmentLocal(c) {
  if (c.dataFamily === 'koneps') return getAssessmentKoneps(c);
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
    !competitive ? 'An offer expected in a direct award adds nothing; competitive procedure not established if unknown.' : c.offersConflict ? (c.offersConflict.feed ? `Offers unknown: the buyer declared ${c.offersConflict.decp ?? '—'} in the Ministry dataset and ${c.offersConflict.feed.join(' / ')} in its own feed; neither is chosen.` : `Offers unknown: the buyer declared ${c.offersConflict.decp ?? '—'} in DECP and ${c.offersConflict.notice ?? '—'} in notice ${c.offersConflict.noticeId}; neither is chosen.`) : !knownOffers ? 'Positive number of offers unknown or unusable.' : `${c.offers} offer(s) declared, without presuming admissibility. One offer: 12 points, regardless of amount.`);
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
    graduated(15 - (bidding.days ?? 15), 0, 12, 8, EDITORIAL_MAX), biddingApplicability === 'no' ? 'Rule reserved for explicitly open non-accelerated procedures; this record’s known type is out of scope.' : bidding.status === 'available' ? `${bidding.days.toFixed(2)} days, upper bound. Signal if < 15 days; 8 points near 15, 30 at 3 days or fewer. Editorial threshold, not a legal one.` : bidding.reason);
  const evolution = getAmountEvolution(c);
  const priceExcluded = c.priceType != null && c.priceType !== 'Définitif ferme';
  add('amount-increase', 'Relative increase in declared amount', 'execution', priceExcluded ? 'no' : c.priceType === 'Définitif ferme' ? 'yes' : 'unknown', evolution.status === 'available', evolution.percentage > 20,
    graduated(evolution.percentage || 0, 20, 100, 8, EDITORIAL_MAX), evolution.status === 'available' ? `Declared increase of ${evolution.percentage.toFixed(2)} %. Signal strictly > 20 %, from 8 points near the threshold to 30 at +100 %. No euro threshold or bonus. Additional services possible: not a final expense nor a proven cost overrun.` : evolution.reason);
  const context = c.competitionContext;
  const oneOfferApplicability = c.directAward === true || (knownOffers && c.offers !== 1) ? 'no' : competitive && c.offers === 1 ? 'yes' : 'unknown';
  add('repeated-single-bid', 'Repeated low competition', 'competition', oneOfferApplicability, Boolean(context?.sufficient), context?.rate >= 0.6,
    graduated(context?.rate || 0, 0.6, 1, 12, EDITORIAL_MAX), oneOfferApplicability === 'no' ? 'This contract is not a single-offer competitive award: outside the repeated-single-offer scope.' : context ? `${context.single}/${context.known} single offers, ${context.total} eligible contracts, CPV ${context.cpvGroup}, 2024–2025. Minimum 10 observations and 80 % coverage; from 12 points at 60 % to 30 points at 100 %. ${context.sufficient ? '' : 'Insufficient sample/coverage: not assessed.'}` : 'No eligible competitive context: no zero rate assumed.');
  const supplier = c.supplierContext;
  add('supplier-concentration', 'Concentrated awards', 'competition', (c.supplierIds || []).length > 1 ? 'no' : 'yes', Boolean(supplier?.sufficient), supplier?.share >= 0.6,
    graduated(supplier?.share || 0, 0.6, 1, 12, EDITORIAL_MAX), supplier ? `Same SIREN: ${supplier.wins}/${supplier.known} contracts to the known holder, out of ${supplier.total} eligible; CPV ${supplier.cpvGroup}, 2024–2025. Minimum 10 and 80 % coverage. From 12 points at 60 % to 30 at 100 %. Specialisation and framework agreements may explain this share. ${supplier.sufficient ? '' : 'Insufficient sample/coverage.'}` : 'Single holder or insufficient/unknown cohort context; no name-based matching.');
  if (c.cohortId === 'tours-full-notices-2025') {
    const change = c.noticeChange;
    add('notice-late-change', 'Late notice change without deadline extension', 'competition', change?.status === 'not-applicable' ? 'no' : 'yes',
      ['signal', 'clear'].includes(change?.status), change?.status === 'signal', 5,
      change?.reason || 'Linked correction evidence not imported.');
  }
  const directEnough = supplier?.directCount >= 3;
  const directKnown = supplier && supplier.directKnownCount === supplier.supplierContracts;
  add('repeated-direct-award', 'Repeated direct awards', 'competition', c.directAward === false ? 'no' : c.directAward === true ? 'yes' : 'unknown', Boolean(supplier && (directEnough || directKnown)), directEnough,
    graduated(supplier?.directCount || 0, 3, 10, 18, EDITORIAL_MAX), c.directAward === false ? 'This contract is explicitly competitive: direct repetition out of scope.' : c.directAward == null ? 'Competitive character of this contract unknown: direct repetition not assessable.' : supplier ? `${supplier.directCount} direct awards identified, all amounts, same buyer/CPV/SIREN, 2024–2025. From 18 points at 3 contracts to 30 at 10. Unknown procedures do not become competitive. Legal exceptions possible.` : 'No history for an identified holder: repetition unknown.');
  const applicable = checks.filter(r => r.applicability === 'yes').length;
  const evaluated = checks.filter(r => r.status === 'signal' || r.status === 'clear').length;
  return { checks, applicable, evaluated, unknown: checks.filter(r => r.applicability === 'yes' && r.status === 'unknown').length,
    unknownApplicability: checks.filter(r => r.applicability === 'unknown').length,
    notApplicable: checks.filter(r => r.status === 'not-applicable').length,
    signals: checks.filter(r => r.status === 'signal').length, excludedReason };
}
