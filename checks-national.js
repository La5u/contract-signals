// Ukraine (Prozorro), TED eForms (Portugal, Romania, Czechia), Chile and the UK: one check set with
// per-family labels and scope (docs/score-ukraine.md, docs/score-ted.md); South Korea's checks come precomputed.
'use strict';

// South Korea (KONEPS). Each contract's checks are computed when the static files are built
// (tools/korea-site-checks.py) by the calibration's own code (tools/korea-label-checks.py), one letter per check
// in KR_CHECK_ORDER (letters for checks appended later are ignored): s signal, c clear, u unknown. Points: 10 x log2 of the LR at the 25th percentile, KFTC
// bid-rigging decisions against the same contracting offices' other contracts (decision rule of 2026-10-20,
// research/calibration/korea-collusion-results.md); G3 and N4 controlled for contract size, rigged prices taken as
// inflated x1.3 (research/calibration/korea-buyer-share-size-results.md). The B checks read the tender's bid opening
// (개찰결과, tools/korea-bid-features.py); unknown when it was not found. Checks without points are not shown.
// Families (2026-10-24, owner: stopgap until a joint model sets how much each check adds when others fire):
// competition (bids and restricted competition: B2, B4, B5, K5), price (B12 or K7) and concentration (G3, G4, N4).
// Only the heaviest signal of a family counts, so B5 does not add to B2 (B5 is mostly the few-bidders effect).
// Price slot (owner 2026-10-25, korea-collusion-results.md "One range per indicator, counter-ranges and two ranges"):
// one price check per tender. Where the bid opening states a lower award limit, FLOOR-GAP (B12) scores the price and
// PRICE-RATIO (K7) is out of scope, since both measure a high price. B12 clear (a win within 0.97 points of the floor)
// carries negative points, the one-per-case value -10.9 rather than -27.7 until a joint model (owner's choice); they
// offset the other families' points, and the index is floored at 0. K6 (>= 95 %) gave way to K7's chosen range.
const KONEPS_NOT_ASSESSED = 'Korean checks were not computed for this record: it is shown for browsing and is not assessed.';
const KR_CHECK_ORDER = ['G2', 'G3', 'G4', 'G5', 'G6', 'N1', 'N2', 'N4', 'N5', 'U2', 'K1', 'K2', 'K3', 'K4', 'K5', 'K6',
  'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'K7', 'B12'];
const KR_NO_OPENING = 'The tender’s bid opening (개찰결과) was not found: not assessable.';
const KR_CHECKS = [
  ['B2', 'competition', 'kr-few-bidders', 'Only two or three bids', 14.8,
    'Two or three bids were opened in this tender (개찰결과). Among tenders the Fair Trade Commission found rigged it was 3 times as frequent as among the same contracting offices’ other contracts, also at equal contract value. Specialised or small markets often draw few bidders lawfully.',
    'One bid, or four or more bids, were opened.', KR_NO_OPENING],
  ['B12', 'price', 'kr-floor-gap', 'Winning bid well above the lower award limit', 17.8,
    'The winning bid is at least 0.97 percentage points (of the reserve price) above the tender’s lower award limit (낙찰하한율), where Korean bids usually cluster. Among tenders the Fair Trade Commission found rigged it was 3.7 times as frequent as among the same contracting offices’ other contracts. A bidder may also simply price higher.',
    'The winning bid is within 0.97 percentage points of the tender’s lower award limit (낙찰하한율), where competitive bids cluster. Rigged tenders were rarely this close to the floor, so this lowers the index by 10.9 points.',
    'The bid opening (개찰결과) states no lower award limit, or was not found: not assessable.', -10.9],
  ['K7', 'price', 'kr-award-near-reserve', 'Award at 92.2 % or more of the reserve price', 15.5,
    'The contract amount is between 92.2 % and 100 % of the reserve price (예정가격). Among tenders the Fair Trade Commission found rigged it was 3.1 times as frequent as among the same contracting offices’ other contracts, also at equal contract value. Lawful awards also come close to the reserve price.',
    'The contract amount is below 92.2 % of the reserve price, or above it.', 'No reserve price or amount published, or the tender states a lower award limit (the gap to it then scores the price): not assessable.'],
  ['B5', 'competition', 'kr-bid-gap', 'Large gap between the two lowest bids', 12.1,
    'The gap between the two lowest valid bids is large against the spread of the other valid bids (above the 90th percentile for this business type and year), the pattern cover bids placed above an agreed winner leave. Among rigged tenders 2.8 times as frequent as among the offices’ other contracts. It also arises by chance.',
    'The gap between the two lowest valid bids is within the usual range.', 'Fewer than three valid bids, or the bid opening (개찰결과) was not found: not assessable.'],
  ['N4', 'concentration', 'kr-supplier-dependence', 'Supplier holds 25 % or more of the buyer’s yearly amount', 9.2,
    'This supplier’s contracts make up at least 25 % of the contracting office’s contract amount for the signing year. Among rigged tenders 2 times as frequent as among the office’s other contracts, at equal contract value. A sole specialist supplier is often lawful.',
    'This supplier holds less than 25 % of the office’s yearly contract amount.', 'Supplier number or the office’s yearly total unknown: not assessable.'],
  ['G3', 'concentration', 'kr-buyer-share', 'Large share of the buyer’s yearly procurement', 8.4,
    'This contract alone is at least 5 % of the contracting office’s contract amount for its signing year. Among rigged tenders 1.9 times as frequent as among the office’s other contracts, at equal contract value. Large purchases are often lawful.',
    'Below 5 % of the office’s yearly contract amount.', 'The office’s yearly total is unknown: not assessable.'],
  ['G4', 'concentration', 'kr-concentration', 'Concentrated awards within a business type', 7.7,
    'This supplier won at least 60 % of the contracting office’s contracts of this business type in the signing year (10 or more contracts). Among rigged tenders 1.9 times as frequent as among the office’s other contracts.',
    'The supplier holds less than 60 % of the office’s contracts of this type that year.', 'Fewer than 10 contracts of this type at the office that year, or no supplier number: not assessable.'],
  ['B4', 'competition', 'kr-bid-dispersion', 'Bid amounts unusually close together', 4.5,
    'The valid bids are unusually close to one another (coefficient of variation below the 10th percentile for this business type and year). Among rigged tenders 1.7 times as frequent as among the offices’ other contracts. Korean bids cluster near the lower award limit by design, so this is a weak signal.',
    'The valid bids are spread as usual.', 'Fewer than three valid bids, or the bid opening (개찰결과) was not found: not assessable.'],
  ['K5', 'competition', 'kr-restricted-competition', 'Restricted or nominated competition', 3.7,
    'Awarded by restricted (제한경쟁) or nominated (지명경쟁) competition, which limits who may bid. Among rigged tenders 1.4 times as frequent as among the office’s other contracts. Restrictions are often lawful (region, licence, performance record).',
    'Open competition or another method.', 'Contract method not published: not assessable.'],
];
function getAssessmentKoneps(c) {
  const letters = typeof c.koreaChecks === 'string' && c.koreaChecks.length >= KR_CHECK_ORDER.length ? c.koreaChecks : null;
  if (!letters) return { checks: [], applicable: 0, evaluated: 0, unknown: 0, unknownApplicability: 0, notApplicable: 0, signals: 0, excludedReason: KONEPS_NOT_ASSESSED };
  const letter = code => letters[KR_CHECK_ORDER.indexOf(code)];
  const floorStated = letter('B12') === 's' || letter('B12') === 'c';
  const checks = KR_CHECKS.map(([code, family, id, label, weight, signal, clear, unknown, clearWeight]) => {
    if (code === 'K7' && floorStated) {
      const reason = 'This tender states a lower award limit, so the gap to it scores the price instead (one price check per tender).';
      return { id, label, family, applicability: 'no', status: 'not-applicable', weight: null, reason, explanation: reason, severity: indicatorSeverity(0).id, severityLabel: indicatorSeverity(0).label };
    }
    const l = letter(code);
    const status = l === 's' ? 'signal' : l === 'c' ? 'clear' : 'unknown';
    const points = status === 'signal' ? weight : status === 'clear' && clearWeight ? clearWeight : null;
    const reason = status === 'signal' ? `${signal} ${weight} points.` : status === 'clear' ? clear : unknown;
    const severity = indicatorSeverity(status === 'signal' ? weight : 0);
    return { id, label, family, applicability: 'yes', status, weight: points,
      reason, explanation: reason, severity: severity.id, severityLabel: severity.label };
  });
  return { checks, excludedReason: null };
}

// Ukraine (Prozorro) and Portugal/Romania (TED eForms): one engine, per-family
// labels and scope. Methods: docs/score-ukraine.md, docs/score-ted.md. Checks were
// fixed before these cohorts were downloaded; French thresholds are not applied.
// Ukrainian points from labelled cases (docs/score-ukraine.md, research/calibration/ukraine-results-2026-10-14.md).
const UA_POINTS = { amendments3: 6, amendments5: 10, termExtension: 4, termExtensionBonus: 6, betterBidDisqualified: 4, buyerShare: 2.2, directContract: 11 };
// D2 (v3.7): a direct-contract report of at least UAH 200,000, the open-tender threshold for goods and services
// (research/calibration/ukraine-candidate-indicators.md, census on the linked conviction cohort: LR 2.18).
const UA_DIRECT_CONTRACT_MIN = 200000;
// R1 (v3.6): a contract of at least 5 % of the buyer's UAH contract total for the tender's creation year
// (research/calibration/ukraine-candidate-indicators.md, part 4). v3.8: 2.2 points (30 in v3.6-3.7): at the same
// contract value, allowing convicted prices 30 % overpricing, the LR is 1.21 (25th percentile 1.16), so the
// unadjusted LR 6.5 measured size, which prosecutions favour (research/calibration/ukraine-buyer-share-size-results.json). Assessed only for buyer-years the cohort
// covers completely; the bundled cohort runs 2024-09-01 → 2026-09-01, so only 2025 is complete.
const UA_BUYER_SHARE = 0.05;
const UA_COMPLETE_YEARS = { 'prozorro-3buyers-2024-2026': new Set(['2025']) };
// Random samples of tenders, not every tender of a buyer: repetition, concentration and buyer share are not assessable.
const UA_SAMPLE_COHORTS = new Set(['prozorro-abovethreshold-2026-06-08']);
const UA_SAMPLE_REASON = 'Random sample of tenders, not every tender of this buyer: not assessable.';
const UA_TERM_EXTENSION_TYPES = ['durationExtension', 'fiscalYearExtension'];
const NATIONAL_FAMILIES = {
  // Ukraine v3.5: points from court verdicts and bid-rigging decisions (docs/score-ukraine.md). Other
  // countries keep their own points: a check's weight is set per jurisdiction, never shared by default.
  prozorro: { prefix: 'ua', doc: 'docs/score-ukraine.md', category: c => c.category, notScored: new Set(['reporting']), singleOfferPoints: 1, directAwardPoints: 10,
    directLabel: 'Negotiated procedure without competition', directReason: 'negotiation or negotiation.quick',
    outOfScope: { directKind: 'Offer and direct-award checks are excluded for direct-contract reports (reporting), which are recorded without a procedure. Concentration remains assessable where cohort data permits.',
      increase: 'Linked contract samples expose change metadata, not comparable dated amounts: increase out of scope.' } },
  // Romania v3.7: Competition Council bid-rigging decisions measured repeated awards without competition
  // (LR 0.38) and concentration (LR 1.09, fails the holdout); a token point each. Czechia and Portugal unchanged.
  ted: { prefix: 'ted', doc: 'docs/score-ted.md', notScored: new Set(), category: c => /^\d{8}/.test(c.cpv || '') ? c.cpv.slice(0, 2) : null,
    countryPoints: { ROU: { repeatedDirect: 1, concentration: 1, source: 'Romanian Competition Council bid-rigging decisions' } },
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
  const singlePoints = spec.singleOfferPoints ?? 12;
  add(`${p}-single-offer`, 'Single offer in a competitive procedure', 'competition', competitive ? 'yes' : direct ? 'no' : unknownKind, nationalOffersKnown(c), c.offers === 1, singlePoints,
    direct ? 'Procedure without competition: one offer is expected, not a signal.' : !competitive ? spec.outOfScope.directKind :
    !nationalOffersKnown(c) ? (c.offersNote || 'Number of offers for this lot not published.') :
    singlePoints === 12 ? `${c.offers} offer(s) published for this lot (${c.procedure}). One offer: 12 points, all amounts. Admissibility is not assessed.` :
    `${c.offers} offer(s) published for this lot (${c.procedure}). One offer: ${singlePoints} point(s), all amounts, lowered from 12 because among Ukrainian tenders in criminal verdicts it was less frequent than among the same buyers' other tenders. Admissibility is not assessed.`);
  const directPoints = spec.directAwardPoints ?? 18, countryPoints = spec.countryPoints?.[c.country];
  add(`${p}-direct-award`, `Award without competition (${spec.directLabel})`, 'competition', spec.directOutOfScope ? 'no' : c.procedureDirect == null ? unknownKind : 'yes', c.procedureDirect != null, direct, directPoints,
    spec.directOutOfScope ? spec.directOutOfScope : c.procedureDirect == null ? spec.outOfScope.directKind : direct ? `${c.procedure} (${spec.directReason}): award without a competitive call. ${directPoints === 18 ? '18 points, all amounts.' : `${directPoints} points, all amounts, lowered from 18: among Ukrainian tenders in criminal verdicts negotiated procedures were about twice as frequent as among the same buyers' other tenders.`} A lawful ground may apply (urgency, exclusivity, failed call); not assessed here.` : `Competitive procedure (${c.procedure}): no direct-award signal.`);
  if (c.dataFamily === 'prozorro') {
    const reporting = c.procedure === 'reporting', uah = c.currency === 'UAH' && Number.isFinite(c.amount);
    add('ua-direct-contract', 'Direct contract of UAH 200,000 or more', 'competition', reporting ? 'yes' : 'no', uah, uah && c.amount >= UA_DIRECT_CONTRACT_MIN, UA_POINTS.directContract,
      !reporting ? 'Not a direct-contract report (reporting): outside this check’s scope.' :
      !uah ? 'Amount not in UAH: not compared with the UAH threshold (no currency conversion).' :
      c.amount >= UA_DIRECT_CONTRACT_MIN ? `Direct contract of ${Math.round(c.amount).toLocaleString('en')} UAH, at or above UAH 200,000, the open-tender threshold for goods and services. ${UA_POINTS.directContract} points: among Ukrainian tenders in criminal verdicts direct contracts this large were about twice as frequent as among the same buyers' other completed purchases. Thresholds differ for works (UAH 1.5 million) and some exemptions apply; neither is assessed here.` :
      'Direct contract below UAH 200,000.');
  }
  const rs = c.nationalRepeatedSingle;
  add(`${p}-repeated-single-offer`, 'Repeated single-offer awards to the same supplier', 'competition', nationalSingle(c) ? 'yes' : competitive && nationalOffersKnown(c) || direct ? 'no' : unknownKind, Boolean(rs), rs?.count >= 3,
    graduated(rs?.count || 0, 3, 10, 12, EDITORIAL_MAX), !nationalSingle(c) ? 'Not a single-offer competitive award: outside the repetition scope.' : UA_SAMPLE_COHORTS.has(c.cohortId) ? UA_SAMPLE_REASON : rs ? `Same buyer and supplier ${supplier}: ${rs.count} distinct procedure(s) in this cohort won with a single offer. From 12 points at 3, linear to 30 at 10.` : 'Supplier identifier not usable (not a national registration number): repetition not assessable.');
  const rd = c.nationalRepeatedDirect;
  add(`${p}-repeated-direct`, 'Repeated awards without competition to the same supplier', 'competition', spec.directOutOfScope ? 'no' : direct ? 'yes' : c.procedureDirect == null ? unknownKind : 'no', Boolean(rd), rd?.count >= 3,
    countryPoints ? countryPoints.repeatedDirect : graduated(rd?.count || 0, 3, 10, 18, EDITORIAL_MAX), spec.directOutOfScope ? spec.directOutOfScope : !direct ? 'Not an award without competition: outside the repetition scope.' : UA_SAMPLE_COHORTS.has(c.cohortId) ? UA_SAMPLE_REASON : rd ? `Same buyer and supplier ${supplier}: ${rd.count} distinct procedure(s) without competition in this cohort. ${countryPoints ? `${countryPoints.repeatedDirect} point from 3, lowered from 18–60: in ${countryPoints.source} repeated awards without competition were rarer than among the same buyers' other contracts.` : 'From 18 points at 3, linear to 30 at 10.'} Lawful grounds may apply to each.` : 'Supplier identifier not usable: repetition not assessable.');
  const k = c.nationalConcentration;
  add(`${p}-concentration`, 'Concentrated awards within a category', 'competition', supplier ? 'yes' : 'unknown', Boolean(k?.sufficient), k?.share >= 0.6,
    countryPoints ? countryPoints.concentration : graduated(k?.share || 0, 0.6, 1, 12, EDITORIAL_MAX), supplier && UA_SAMPLE_COHORTS.has(c.cohortId) ? UA_SAMPLE_REASON : k ? `Same buyer and category ${k.category}: ${k.wins}/${k.known} procedures won by this supplier, out of ${k.total} (${Math.round(k.coverage * 100)} % with an identified winner; lots of one procedure count once). Minimum 10 and 80 %; ${countryPoints ? `${countryPoints.concentration} point from 60 %, lowered from 12–40: in ${countryPoints.source} concentration was barely more frequent than among the same buyers' other contracts.` : 'from 12 points at 60 % to 30 at 100 %.'} ${k.sufficient ? '' : 'Insufficient sample or coverage: not assessed.'}` : 'Supplier identity or category unknown: applicability not established.');
  add('amount-increase', 'Relative increase in declared amount', 'execution', 'no', false, false, null, spec.outOfScope.increase);
  if (c.dataFamily === 'prozorro') {
    // Prozorro creates awards in ranking order: an unsuccessful award before the
    // winning one means a better-ranked bid was set aside (docs/score-ukraine.md).
    const amendments = c.contractChanges, types = c.contractChangeTypes || [];
    const extended = Number.isInteger(amendments) && types.some(t => UA_TERM_EXTENSION_TYPES.includes(t));
    const amendmentPoints = (amendments >= 5 ? UA_POINTS.amendments5 : UA_POINTS.amendments3) + (extended ? UA_POINTS.termExtensionBonus : 0);
    add('ua-contract-amendments', 'Three or more contract amendments', 'execution', 'yes', Number.isInteger(amendments), amendments >= 3, amendmentPoints,
      !Number.isInteger(amendments) ? 'Contract record not retrieved: amendments not assessable.' :
      `${amendments} active contract amendment(s). Rationale types: ${types.join(', ') || 'none published'}. Amendments are often lawful (Law on Public Procurement art. 41 permits listed changes). The threshold of three follows StateWatch/Prozorro risk indicator ARI 1-1. ${UA_POINTS.amendments3} points at 3–4 amendments, ${UA_POINTS.amendments5} at 5 or more, plus ${UA_POINTS.termExtensionBonus} when an amendment extends the contract term.`);
    // A separate check so it can be filtered; with three or more amendments it counts through the bonus above (family maximum).
    add('ua-term-extension', 'Contract term extended by amendment', 'execution', 'yes', Number.isInteger(amendments), extended, UA_POINTS.termExtension,
      !Number.isInteger(amendments) ? 'Contract record not retrieved: term extension not assessable.' :
      extended ? `An active amendment extends the contract term (rationale types: ${types.filter(t => UA_TERM_EXTENSION_TYPES.includes(t)).join(', ')}). ${UA_POINTS.termExtension} points with fewer than three amendments; with three or more it adds ${UA_POINTS.termExtensionBonus} points to the amendments check instead. Extensions are often lawful (Law on Public Procurement art. 41 permits some); this check does not assess their grounds.` :
      'No active amendment extends the contract term.');
    const bs = c.uaBuyerShare;
    add('ua-buyer-share', 'Large share of the buyer’s yearly procurement', 'competition', 'yes', Boolean(bs?.complete && bs.share != null), bs?.share >= UA_BUYER_SHARE, UA_POINTS.buyerShare,
      !bs ? 'Buyer share not computed.' : UA_SAMPLE_COHORTS.has(c.cohortId) ? UA_SAMPLE_REASON :
      !bs.complete ? `This cohort does not cover the buyer’s whole year ${bs.year || '(unknown)'}: share not assessable.` :
      bs.share == null ? 'Amount not in UAH: not compared with the buyer’s UAH total (no currency conversion).' :
      `${(bs.share * 100).toFixed(1)} % of this buyer’s UAH contract total for ${bs.year} (${Math.round(bs.total).toLocaleString('en')} UAH, contracts of tenders created that year). ` +
      (bs.share >= UA_BUYER_SHARE ? `${UA_POINTS.buyerShare} points at 5 % or more, all procedures: among Ukrainian tenders in criminal verdicts a contract this large relative to its buyer was about 6.5 times as frequent as among the same buyers’ other tenders, but at the same contract value only about 1.2 times: most of the difference is size, which prosecutions favour. Large purchases are often lawful; this check does not assess need or price.` : 'Below the 5 % threshold.'));
    const dq = c.disqualifiedBefore;
    add('ua-better-bid-disqualified', 'Better-ranked bidder disqualified before the award', 'competition', competitive ? 'yes' : direct ? 'no' : unknownKind, Number.isInteger(dq), dq > 0, UA_POINTS.betterBidDisqualified,
      !competitive ? (direct ? 'Procedure without competition: no ranking of bids.' : spec.outOfScope.directKind) :
      !Number.isInteger(dq) ? 'Award history without dates: disqualifications not assessable.' :
      dq > 0 ? `${dq} better-ranked bidder(s) on this lot had their award declared unsuccessful before this award. ${UA_POINTS.betterBidDisqualified} points, all amounts. Disqualification is often lawful (missing documents, non-compliant offer); read the award decisions linked on the Prozorro page.` :
      'No better-ranked bid set aside before this award on this lot.');
  } else add('short-bidding-period', 'Short bidding period', 'competition', 'no', false, false, null, 'No validated minimum period for this jurisdiction in this method: out of scope.');
  add('long-contract', 'Long declared duration', 'execution', 'no', false, false, null, 'No duration threshold validated for this jurisdiction: out of scope.');
  const applicable = checks.filter(r => r.applicability === 'yes').length;
  const evaluated = checks.filter(r => r.status === 'signal' || r.status === 'clear').length;
  return { checks, applicable, evaluated, unknown: checks.filter(r => r.applicability === 'yes' && r.status === 'unknown').length,
    unknownApplicability: checks.filter(r => r.applicability === 'unknown').length, notApplicable: checks.filter(r => r.status === 'not-applicable').length,
    signals: checks.filter(r => r.status === 'signal').length, excludedReason };
}
