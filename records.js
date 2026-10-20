// Records: preparation of a loaded cohort (cohort-wide context), validation, grouping, search and
// selection. Engine file: no DOM.
'use strict';

// Retrospective context on the COMPLETE loaded cohort, never on filtered/page rows.
function prepareContracts(data) {
  const contracts = validateContracts(data).map(c => ({ ...c, competitionContext: null, supplierContext: null, identityAmbiguous: false, secop2Concentration: null, secop2Repetition: null, secop2PublicCounterparty: null, dncpConcentration: null, dncpRepeatedSingle: null, dncpRepeatedException: null, nationalConcentration: null, nationalRepeatedSingle: null, nationalRepeatedDirect: null }));
  const groups = new Map();
  const supplierGroups = new Map();
  const identityCounts = new Map();
  for (const c of contracts) {
    if (c.dataFamily !== 'decp' || !c.buyerSiret || !c.contractId) continue;
    const identity = `${c.buyerSiret}:${c.contractId}`;
    if (!identityCounts.has(identity)) identityCounts.set(identity, []);
    identityCounts.get(identity).push(c.id);
  }
  // An evidenced split shares the identifier on purpose: unambiguous only if the rows sharing it are exactly its members.
  const exactGroup = (c, ids) => Boolean(c.procedureGroup) && ids.length === c.procedureGroup.members.length && ids.every(id => c.procedureGroup.members.includes(id));
  for (const c of contracts) {
    const ids = c.dataFamily === 'decp' && c.buyerSiret && c.contractId ? identityCounts.get(`${c.buyerSiret}:${c.contractId}`) : null;
    c.identityAmbiguous = Boolean(ids && ids.length > 1 && !exactGroup(c, ids));
  }
  assignPublicationBaselines(contracts);
  const competitionShadows = [], supplierShadows = [];
  for (const c of contracts) {
    if (c.dataFamily !== 'decp' || !HISTORY_COHORTS.has(c.cohortId) || c.modificationConflicts?.length ||
        !c.buyerSiret || !c.contractId || c.identityAmbiguous ||
        !/^\d{8}-\d$/.test(c.cpv || '') || c.cpv.startsWith('000') || !c.date ||
        c.date < HISTORY_START || c.date > HISTORY_END || c.directAward !== false ||
        !Array.isArray(c.initialConflicts) || c.initialConflicts.length) continue;
    const key = `${c.cohortId}:${c.buyerSiret}:${c.cpv.slice(0, 3)}`;
    if (duplicateShadow(c)) { competitionShadows.push([c, key]); continue; }
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
  for (const [c, key] of competitionShadows) c.competitionContext = groups.get(key)?.[0].competitionContext || null;
  for (const c of contracts) {
    if (c.dataFamily !== 'decp' || !HISTORY_COHORTS.has(c.cohortId) || c.modificationConflicts?.length || !c.buyerSiret || !c.contractId ||
        c.identityAmbiguous || !c.date || c.date < HISTORY_START || c.date > HISTORY_END ||
        !/^\d{8}-\d$/.test(c.cpv || '') || c.cpv.startsWith('000') ||
        !Array.isArray(c.initialConflicts) || c.initialConflicts.length) continue;
    const key = `${c.cohortId}:${c.buyerSiret}:${c.cpv.slice(0, 3)}`;
    if (duplicateShadow(c)) { supplierShadows.push([c, key]); continue; }
    if (!supplierGroups.has(key)) supplierGroups.set(key, []);
    supplierGroups.get(key).push(c);
  }
  for (const [key, group] of supplierGroups) {
    const known = group.filter(c => getSupplierIdentity(c) !== null);
    const bySupplier = new Map();
    known.forEach(c => { const id = getSupplierIdentity(c); if (!bySupplier.has(id)) bySupplier.set(id, []); bySupplier.get(id).push(c); });
    const receivers = [...group, ...supplierShadows.filter(([, k]) => k === key).map(([c]) => c)];
    receivers.forEach(c => {
      const id = getSupplierIdentity(c);
      if (id === null) return;
      const supplierRows = bySupplier.get(id) || [];
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
  // Colombia: each contract's share of its buyer's COP contract total for its signing year.
  const coYearTotals = new Map(), coYear = c => `${c.buyerNit || c.buyer}|${(c.date || '').slice(0, 4)}`;
  for (const c of contracts) {
    if (c.dataFamily !== 'secop2' || c.currency !== 'COP' || !Number.isFinite(c.amount)) continue;
    coYearTotals.set(coYear(c), (coYearTotals.get(coYear(c)) || 0) + c.amount);
  }
  for (const c of contracts) {
    if (c.dataFamily !== 'secop2') continue;
    const year = (c.date || '').slice(0, 4), complete = Boolean(CO_COMPLETE_YEARS[c.cohortId]?.has(year));
    const secop1 = CO_SECOP1_TOTALS[coYear(c)] || 0, total = (coYearTotals.get(coYear(c)) || 0) + secop1;
    c.coBuyerShare = { year, complete, total, secop1, share: c.currency === 'COP' && Number.isFinite(c.amount) && total > 0 ? c.amount / total : null };
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
        wins: wins.get(id).size, share: wins.get(id).size / known.size, coverage, sufficient: known.size >= 10 && coverage >= 0.8 && !UA_SAMPLE_COHORTS.has(c.cohortId) };
    }
  }
  // Ukraine: each contract's share of its buyer's UAH contract total for the tender's creation year.
  const uaYearTotals = new Map(), uaYear = c => `${c.cohortId}|${c.buyerId}|${(c.tenderCreated || '').slice(0, 4)}`;
  for (const c of contracts) {
    if (c.dataFamily !== 'prozorro' || c.currency !== 'UAH' || !Number.isFinite(c.amount)) continue;
    uaYearTotals.set(uaYear(c), (uaYearTotals.get(uaYear(c)) || 0) + c.amount);
  }
  for (const c of contracts) {
    if (c.dataFamily !== 'prozorro') continue;
    const year = (c.tenderCreated || '').slice(0, 4), complete = Boolean(UA_COMPLETE_YEARS[c.cohortId]?.has(year));
    const total = uaYearTotals.get(uaYear(c)) || 0;
    c.uaBuyerShare = { year, complete, total, share: c.currency === 'UAH' && Number.isFinite(c.amount) && total > 0 ? c.amount / total : null };
  }
  for (const c of contracts) {
    if (!NATIONAL_FAMILIES[c.dataFamily] || !nationalSupplierIdentity(c) || UA_SAMPLE_COHORTS.has(c.cohortId)) continue;
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
  if (contract.collectionId && mode) {
    const info = groupInfo({ ...contract, collectionId: null }, mode);
    return { key: `${contract.collectionId}::${info.key}`, label: `${contract.collectionLabel} · ${info.label}` };
  }
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
    if (c.dataFamily != null && !['decp', 'boamp', 'audit', 'secop2', 'dncp', 'prozorro', 'ted', 'fts', 'chile', 'koneps'].includes(c.dataFamily)) throw new Error(`${c.id} : invalid data family.`);
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
    if (c.procedureGroup != null) {
      const g = c.procedureGroup;
      if (!g || typeof g !== 'object' || typeof g.id !== 'string' || !g.id || !['lots', 'shared-identifier'].includes(g.kind) || typeof g.basis !== 'string' || !g.basis.trim() ||
          !Array.isArray(g.members) || g.members.length < 2 || !g.members.includes(c.id) || g.members.some(m => typeof m !== 'string' || !m) || new Set(g.members).size !== g.members.length ||
          (g.contractReference != null && typeof g.contractReference !== 'string') || (g.lotTitle != null && typeof g.lotTitle !== 'string')) throw new Error(`${c.id} : invalid procedure group.`);
    }
    if (c.verification != null) {
      const v = c.verification;
      if (!v || typeof v !== 'object' || !VERIFICATION_STATUSES[v.status] || !Array.isArray(v.sources) || v.sources.some(x => typeof x !== 'string') ||
          (v.amountRange != null && (!Array.isArray(v.amountRange) || v.amountRange.length !== 2 || v.amountRange.some(x => typeof x !== 'number' || !Number.isFinite(x) || x < 0) || v.amountRange[0] >= v.amountRange[1])) ||
          ['placeholder', 'resolvedPair', 'addedFromFeed', 'holdersAddedFromFeed', 'offersDisagree'].some(k => v[k] != null && typeof v[k] !== 'boolean') ||
          (v.majority != null && (typeof v.majority.amount !== 'number' || !(v.majority.amount > 0) || !Number.isInteger(v.majority.routes) || !Number.isInteger(v.majority.of) || v.majority.routes < 2 || v.majority.routes > v.majority.of))) throw new Error(`${c.id} : invalid verification.`);
    }
    if (c.amountSources != null && (!Array.isArray(c.amountSources) || c.amountSources.some(x => !x || typeof x.source !== 'string' || typeof x.label !== 'string' ||
        (x.amount != null && (typeof x.amount !== 'number' || !Number.isFinite(x.amount) || x.amount < 0))))) throw new Error(`${c.id} : invalid amount sources.`);
    if (c.unconfirmedHolders != null && (!Array.isArray(c.unconfirmedHolders) || c.unconfirmedHolders.some(h => !h || typeof h.id !== 'string' || typeof h.reason !== 'string'))) throw new Error(`${c.id} : invalid unconfirmed holders.`);
    if (c.possibleDuplicateOf != null && (!Array.isArray(c.possibleDuplicateOf) || !c.possibleDuplicateOf.length || !c.procedureGroup ||
        c.possibleDuplicateOf.some(id => typeof id !== 'string' || id === c.id || !c.procedureGroup.members.includes(id)))) throw new Error(`${c.id} : invalid possible duplicate.`);
    if (c.offersConflict != null) {
      const o = c.offersConflict;
      const counts = o && (o.feed != null ? o.feed : [o.notice]);
      if (!o || typeof o !== 'object' || c.offers != null || !Array.isArray(counts) || (o.feed != null ? typeof o.source !== 'string' : typeof o.noticeId !== 'string' || !o.noticeId) ||
          [o.decp, ...counts].some(v => v != null && (!Number.isInteger(v) || v < 0)) || counts.includes(o.decp)) throw new Error(`${c.id} : invalid offer conflict.`);
    }
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

// The source's own declaration of an award without competition: DECP/BOAMP directAward,
// TED and Find a Tender procedureDirect (a direct award or negotiated procedure without prior publication).
function declaredWithoutCompetition(c) { return c.directAward === true || c.procedureDirect === true; }
function recordCountry(c) {
  return c.country || ({ decp: 'FRA', boamp: 'FRA', secop2: 'COL', dncp: 'PRY', prozorro: 'UKR', koneps: 'KOR', chile: 'CHL', uk: 'GBR' }[c.dataFamily]) || '';
}
function selectContracts(contracts, { country = '', dateFrom = '', dateTo = '', buyer = '', supplier = '', procedure = '', search = '', minimum = 0, minScore = 0, flagged = false, official = false, adjudicated = false, investigation = false, indicator = '', legal = '', noticeContext = '', assessment = '', sector = '', project = '', verification = '', sort = 'score' } = {}) {
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
    if (country && recordCountry(c) !== country) return false;
    const day = typeof c.date === 'string' ? c.date.slice(0, 10) : '';
    if ((dateFrom || dateTo) && !/^\d{4}-\d{2}-\d{2}$/.test(day)) return false;
    if ((dateFrom && day < dateFrom) || (dateTo && day > dateTo)) return false;
    if (buyer && !normalize(`${c.buyer || ''} ${c.buyerId || ''}`).includes(normalize(buyer))) return false;
    if (supplier && !normalize(`${c.supplier || ''} ${(c.supplierNamesPublished || []).join(' ')}`).includes(normalize(supplier))) return false;
    if (procedure && !normalize(c.procedure || '').includes(normalize(procedure))) return false;
    if (verification && c.verification?.status !== verification) return false;
    const noticeMatch = !noticeContext || Boolean(evidence && (noticeContext === 'criteria' ? evidence.awardCriteria.length : noticeContext === 'explanation' ? evidence.procedureDescription || evidence.justifications.some(j => j.text) : noticeContext === 'correction' ? evidence.kind === 'correction' : noticeContext === 'ted' ? evidence.ted.length : false));
    const citations = legal && !['py-complaint', 'co-public', 'fr-software', 'direct'].includes(legal) ? getLegalContext(c) : [];
    const legalMatch = !legal || (legal === 'py-complaint' ? Boolean(c.complaints?.length) : legal === 'co-public' ? Boolean(c.secop2PublicCounterparty?.labelled) : legal === 'fr-software' ? Boolean(softwareMaintenanceContext(c)) : legal === 'direct' ? declaredWithoutCompetition(c) : legal === 'cited' ? citations.length > 0 : citations.some(item => item.article === legal));
    const evaluated = getAssessment(c);
    const assessmentMatch = !assessment || (assessment === 'unevaluated' ? scoreFor(c) == null : assessment === 'zero' ? scoreFor(c) === 0 : assessment === 'partial' ? evaluated.unknown > 0 || evaluated.unknownApplicability > 0 : false);
    const sectorMatch = !sector || getSector(c).code === sector;
    const projectMatch = !project || (project === '@documented' ? Boolean(c.project) : c.project?.id === project);
    return (!terms.length || terms.every(term => searchText(c).includes(term))) && assessmentMatch && noticeMatch && legalMatch && sectorMatch && projectMatch &&
      (minimum <= 0 || (c.amount > 0 && c.amount >= minimum)) && (minScore <= 0 || (scoreFor(c) != null && scoreFor(c) >= minScore)) &&
      (!flagged || getIndicators(c).length > 0) && (!official || c.officialFinding === true) && (!adjudicated || hasAdjudicatedCorruption(c)) && (!investigation || hasReportedInvestigation(c)) &&
      (!indicator || (indicator === 'official-finding' ? c.officialFinding === true : getIndicators(c).some(i => i.kind === indicatorKind(indicator))));
  });
  const direction = ['score-asc', 'amount-asc', 'date-asc', 'publication-asc', 'indicators-asc', 'offers'].includes(sort) ? 1 : ['sector', 'sector-desc', 'buyer', 'buyer-desc', 'supplier', 'supplier-desc'].includes(sort) ? (sort.endsWith('-desc') ? -1 : 1) : -1;
  const field = sort === 'recent-signal' ? 'recent-signal' : sort.startsWith('score') ? 'score' : sort.startsWith('amount') ? 'amount' : sort.startsWith('date') ? 'date' : sort.startsWith('indicators') ? 'indicators' : sort.startsWith('publication') ? 'publication' : sort.startsWith('sector') ? 'sector' : sort.startsWith('buyer') ? 'buyer' : sort.startsWith('supplier') ? 'supplier' : sort.startsWith('offers') ? 'offers' : sort;
  const raw = c => field === 'recent-signal' ? (scoreFor(c) > 0 && c.date ? Date.parse(c.date) : null) : field === 'score' ? scoreFor(c) : field === 'amount' ? (c.amount > 0 ? c.amount : null) : field === 'date' ? (c.date ? Date.parse(c.date) : null) :
    field === 'publication' ? (c.publicationDate ? Date.parse(c.publicationDate) : null) : field === 'sector' ? getSector(c).label : field === 'buyer' ? c.buyer : field === 'supplier' ? c.supplier :
    field === 'indicators' ? (scoreFor(c) == null ? null : getIndicators(c).length) :
    field === 'official' ? (c.officialFinding === true ? 1 : null) : field === 'offers' ? c.offers : field === 'increase' ? increaseFor(c) : null;
  return filtered.sort((a, b) => {
    const av = raw(a), bv = raw(b);
    const nullOrder = av == null ? (bv == null ? 0 : 1) : bv == null ? -1 : 0;
    if (nullOrder) return nullOrder;
    // Amounts are never compared across currencies: group by currency, then amount.
    if (field === 'amount') {
      const ac = recordCurrency(a) || '(currency unknown)', bc = recordCurrency(b) || '(currency unknown)';
      if (ac !== bc) return collator.compare(ac, bc);
    }
    if (field === 'sector' && av === 'Sector not specified' && bv !== av) return 1;
    if (field === 'sector' && bv === 'Sector not specified' && av !== bv) return -1;
    const comparison = typeof av === 'string' ? collator.compare(av, bv) : av === bv ? 0 : av > bv ? 1 : -1;
    return comparison * direction || ((scoreFor(b) ?? -1) - (scoreFor(a) ?? -1)) || (strengthFor(b)[0] - strengthFor(a)[0]) || (strengthFor(b)[1] - strengthFor(a)[1]) || collator.compare(a.id, b.id);
  });
}
