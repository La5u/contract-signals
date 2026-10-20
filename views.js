// Views of records: page summaries, URL view state, South Korea's static files, profiles, exports, and
// the DOM helpers for links and evidence shared by the explorer.
'use strict';

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
      `Declared amount: ${c.amount == null ? 'unknown' : c.amount === 0 ? 'declared 0 (likely undisclosed)' : `${c.amount} ${recordCurrency(c) || '(currency unknown)'}`} (not an audited payment)`,
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
const VIEW_FIELDS = [['country', 'filter-country', ''], ['from', 'date-from', ''], ['to', 'date-to', ''], ['buyer', 'filter-buyer', ''], ['supplier', 'filter-supplier', ''], ['procedure', 'filter-procedure', ''], ['q', 'search', ''], ['sort', 'sort', 'score'], ['min', 'minimum', ''], ['sector', 'sector', ''], ['group', 'group-by', ''],
  ['project', 'project', ''], ['assessment', 'assessment', ''], ['index', 'min-score', '0'], ['indicator', 'indicator', ''],
  ['notice', 'notice-context', ''], ['legal', 'legal', ''], ['verif', 'verification', ''], ['open', 'open-record', ''], ['buyer', 'korea-buyer', '']];
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

// Datasets merged into another, or removed, keep working in old links (the combined view was removed after v3.7).
const DATASET_ALIASES = { cities: 'decp', all: 'decp' };

// Local copies (tools/build-korea-site.py output, linked as korea-site/) are used when serving from this machine.
const KOREA_BASE = globalThis.location && /^(127\.0\.0\.1|localhost)$/.test(globalThis.location.hostname) ? `${globalThis.location.origin}/korea-site` : 'https://kr.contracts.lasu.dev';
// South Korea: every contracting institution's contracts, as static files on a separate host
// (tools/build-korea-site.py; never in the repository). A shard holds several buyers' rows as arrays;
// this turns one buyer's rows into explorer records. Individual businesses keep their published trade
// name, flagged; their registration number is not in the files (docs/personal-data.md).
function koreaRecords(meta, shard, buyer, rows = shard.buyers[buyer[0]] || []) {
  const [code, buyerName] = buyer;
  const col = Object.fromEntries(meta.columns.map((k, i) => [k, i]));
  return rows.map(r => {
    const g = k => r[col[k]] ?? null;
    const kind = meta.supplierKinds[g('supplierKind')] || 'unknown';
    const supplier = g('supplier');
    const demand = g('demand') == null ? null : shard.demand[g('demand')];
    const legal = g('legalRef') == null ? null : shard.legal[g('legalRef')];
    const method = g('method') == null ? null : meta.methods[g('method')];
    const type = g('businessType') == null ? null : meta.businessTypes[g('businessType')];
    const linkKind = g('linkKind') == null ? null : meta.linkKinds[g('linkKind')];
    const parts = [g('linkContract'), g('linkChangeOrder'), linkKind];
    const source = parts.every(Boolean) ? parts.reduce((url, part) => url.replace('{}', encodeURIComponent(part)), meta.link) : null;
    const original = g('originalAmount'), latest = g('latestAmount'), versions = g('versions');
    const notes = [demand && demand !== buyerName ? `Requesting institution (수요기관): ${demand}.` : null,
      legal ? `Legal ground cited: ${legal}.` : null, g('joint') ? 'Joint contract (공동계약).' : null].filter(Boolean).join(' ');
    return {
      id: `koneps-${g('contractNo')}`, cohortId: `koneps-${code}`, dataFamily: 'koneps', country: 'KOR', dataStatus: 'verified',
      buyer: buyerName, buyerId: code, description: g('name') || g('contractNo'),
      supplier: supplier || null, supplierNamesPublished: supplier ? [supplier] : [], supplierIndividual: supplier ? [kind === 'individual'] : [],
      supplierIds: g('supplierBizrno') ? [{ id: g('supplierBizrno'), identifierType: 'KR-BRN' }] : [],
      procedure: [method, type].filter(Boolean).join(' · ') || null, contractId: g('contractNo'), noticeId: g('noticeNo'),
      date: g('date'), dateNote: g('dateIsFirstChange') ? `Signed before ${meta.period?.[0] || 'the period'}: this is the date of its first change in the period.` : 'Contract date (계약체결일자).',
      amount: typeof latest === 'number' ? latest : null, currency: 'KRW',
      amountBasis: original != null && original !== latest ? `Contract amount of the latest version in the period; the original contract was ${original} KRW (${versions} versions).` : 'Contract amount (계약금액) of the latest version in the period.',
      notes: notes || null, source, sourceLabel: 'KONEPS (나라장터) contract page',
    };
  });
}
// A page is a bounded window in published shard/buyer/row order, NOT a global sort.
// Later pages rescan from the start: no growing cursor history or retained shard cache.
// A buyer too big for one file lists its shards (oldest contracts first) in a sixth entry.
const koreaParts = buyer => Array.isArray(buyer[5]) ? buyer[5] : [buyer[4]];
async function scanKoreaPage({ meta, buyers, fetchShard, predicate, offset = 0, limit = 50,
  signal, progress = () => {}, yieldTask = () => new Promise(resolve => setTimeout(resolve, 0)) }) {
  limit = Math.max(1, Math.min(200, Math.floor(limit) || 50));
  offset = Math.max(0, Math.floor(offset) || 0);
  const check = () => { if (signal?.aborted) { const e = new Error('Scan cancelled'); e.name = 'AbortError'; throw e; } };
  const groups = new Map();
  for (const b of buyers) for (const n of koreaParts(b)) {
    if (!groups.has(n)) groups.set(n, []);
    groups.get(n).push(b);
  }
  const rows = [];
  let examined = 0, matches = 0, shards = 0;
  for (const n of [...groups.keys()].sort((a, b) => a - b)) {
    check();
    const shard = await fetchShard(n, signal);
    check();
    for (const buyer of groups.get(n)) {
      const raw = shard.buyers?.[buyer[0]];
      if (!Array.isArray(raw) || (!buyer[5] && raw.length !== buyer[3])) throw new Error(`Incomplete shard ${n} for buyer ${buyer[0]}; retry after publication completes.`);
      for (let i = 0; i < raw.length; i += 256) {
        check();
        const batch = prepareContracts(koreaRecords(meta, shard, buyer, raw.slice(i, i + 256)));
        for (const c of batch) {
          examined++;
          if (!predicate(c)) continue;
          matches++;
          if (matches <= offset) continue;
          if (rows.length === limit) return { rows, examined, matches, shards, hasMore: true, complete: false };
          rows.push(c);
        }
        progress({ examined, matches, shards, retained: rows.length });
        await yieldTask();
        check();
      }
    }
    shards++;
  }
  return { rows, examined, matches, shards, hasMore: false, complete: true };
}

// Bounded published-order union. Assess each ordinary collection in isolation.
async function scanPublishedPage({ collections, loadCollection, korea, predicate, offset = 0, limit = 50,
  signal, progress = () => {}, yieldTask = () => new Promise(resolve => setTimeout(resolve, 0)) }) {
  limit = Math.max(1, Math.min(200, Math.floor(limit) || 50));
  offset = Math.max(0, Math.floor(offset) || 0);
  const rows = [];
  let examined = 0, matches = 0;
  const check = () => { if (signal?.aborted) { const e = new Error('Scan cancelled'); e.name = 'AbortError'; throw e; } };
  const context = (c, key, label) => {
    getAssessment(c); // Freeze source assessment before namespacing the display identifier.
    c.collectionId = key; c.collectionLabel = label; c.originalId = c.id;
    c.id = `${key}::${c.id}`;
    return c;
  };
  for (const { key, label } of collections) {
    check();
    const records = prepareContracts(await loadCollection(key, signal));
    check();
    for (let i = 0; i < records.length; i++) {
      const c = context(records[i], key, label);
      examined++;
      if (predicate(c)) {
        matches++;
        if (matches > offset) {
          if (rows.length === limit) return { rows, examined, matches, hasMore: true, complete: false };
          rows.push(c);
        }
      }
      if (i % 256 === 255) {
        progress({ examined, matches, retained: rows.length });
        await yieldTask(); check();
      }
    }
    progress({ examined, matches, retained: rows.length });
    await yieldTask(); check();
  }
  const result = await scanKoreaPage({ ...await korea(signal), signal,
    offset: Math.max(0, offset - matches), limit: Math.max(1, limit - rows.length),
    predicate: c => predicate(context(c, 'korea', 'South Korea · KONEPS')),
    progress: p => progress({ examined: examined + p.examined, matches: matches + p.matches,
      retained: Math.min(limit, rows.length + p.retained) }), yieldTask });
  const hasMore = rows.length === limit ? result.matches > 0 : result.hasMore;
  if (rows.length < limit) rows.push(...result.rows);
  return { rows, examined: examined + result.examined, matches: matches + result.matches,
    hasMore, complete: !hasMore && result.complete };
}

function hashToViewState(hash) {
  const params = new URLSearchParams(String(hash || '').replace(/^#/, ''));
  const requested = params.get('dataset') || '';
  const state = { dataset: DATASET_ALIASES[requested] || requested };
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
  for (const c of rows) if (c.amount > 0) {
    const cur = recordCurrency(c) || '(currency unknown)';
    currencies[cur] ??= { contracts: 0, largest: 0 };
    currencies[cur].contracts++;
    currencies[cur].largest = Math.max(currencies[cur].largest, c.amount);
  }
  const dates = rows.map(c => c.date).filter(Boolean).sort();
  const scores = rows.map(getVigilanceScore);
  return { role, key, name: role === 'buyer' ? rows[0].buyer : (supplierNames(rows[0])[0] || rows[0].supplier), 
    ids: new Set(rows.map(c => c.id)), contracts: rows.length, assessed: scores.filter(x => x != null).length, flagged: scores.filter(x => x > 0).length,
    firstDate: dates[0] || null, lastDate: dates[dates.length - 1] || null, kinds: rate(rows), baseline: rate(scope), scopeSize: scope.length,
    counterparts: [...counterparts.values()].sort((a, b) => b.contracts - a.contracts || b.flagged - a.flagged || a.name.localeCompare(b.name)).slice(0, 10), currencies };
}

// Export the whole filtered view as flat records. Unknown stays empty, never zero.
const EXPORT_CAVEAT = 'Published declarations and heuristic signals only. A flag is not proof of wrongdoing; zero or no label is not clearance. Declared amounts are not audited payments; never sum amounts across datasets or currencies. Current supplier names are a register snapshot, not historical names.';
const EXPORT_COLUMNS = ['collectionId', 'collectionLabel', 'originalId', 'id', 'date', 'buyer', 'buyerId', 'supplier', 'supplierCurrentName', 'supplierIds', 'description', 'cpv', 'sector', 'procedure',
  'amount', 'amountLow', 'amountHigh', 'amountVerification', 'currency', 'offers', 'durationMonths', 'index', 'indexStatus', 'signals', 'signalPoints', 'context', 'officialFinding', 'investigationReported', 'dataStatus', 'source', 'verifyUrls'];

function exportRecord(c) {
  const score = getVigilanceScore(c);
  return {
    collectionId: c.collectionId ?? null, collectionLabel: c.collectionLabel ?? null, originalId: c.originalId ?? c.id,
    id: c.id, date: c.date ?? null, buyer: c.buyer, buyerId: c.buyerSiret || c.buyerNit || c.buyerId || null, supplier: exportSupplier(c),
    supplierCurrentName: supplierNames(c).join('; ') || null,
    supplierIds: (c.supplierIds || []).map(s => `${s.identifierType || 'identifier'} ${s.id}`).join('; ') || null,
    description: c.description, cpv: c.cpv ?? null, sector: getSector(c).label, procedure: c.procedure ?? null,
    amount: c.amount ?? null, amountLow: c.verification?.amountRange?.[0] ?? c.amount ?? null, amountHigh: c.verification?.amountRange?.[1] ?? c.amount ?? null,
    amountVerification: c.verification?.status ?? null, currency: c.amount == null ? null : recordCurrency(c), offers: c.offers ?? null, durationMonths: c.durationMonths ?? null,
    index: score, indexStatus: score == null ? 'not assessed' : 'assessed', signals: getIndicators(c).map(i => i.kindLabel).join('; ') || null,
    signalPoints: getIndicators(c).map(i => `${i.kindLabel}: ${i.weight} (${i.basis})`).join('; ') || null,
    context: contextLabels(c).map(l => l.short).join('; ') || null,
    officialFinding: c.officialFinding === true, investigationReported: hasReportedInvestigation(c), dataStatus: c.dataStatus,
    source: safeSource(c.processUrl) || safeSource(c.source) || null,
    verifyUrls: verificationLinks(c).map(l => l.url).join(' ') || null
  };
}

// Suppliers flagged as individuals (supplierIndividual) are shown on screen as published but left out of exports.
function exportSupplier(c) {
  const names = c.supplierNamesPublished, individual = c.supplierIndividual;
  if (!Array.isArray(individual) || !Array.isArray(names) || !individual.some(Boolean)) return c.supplier ?? null;
  return names.map((name, i) => individual[i] ? 'individual (name in the explorer)' : name).join(' / ');
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

// First sentence of a check's reason: the record's own fact, without the method text.
function briefReason(text) {
  // Translate the whole sentence first (the dictionaries hold full reasons), then shorten.
  const full = String(text || '').trim();
  const s = typeof i18nTranslate === 'function' ? i18nTranslate(full) : full;
  const m = /^(.+?(?<!\b(?:Art|art|No|no|Nº|n|cf))[.!?])\s+(?=[\p{Lu}\d“"(«])/u.exec(s);
  return m ? m[1] : s;
}

// Optional cross-source evidence: kept outside contract records and scoring.
function validateBoampDecpLinks(data) {
  const paths = ['data/contracts.json', 'data/decp-history.json', 'data/decp-cities.json', 'data/boamp-raw.json.gz'];
  const official = value => {
    if (typeof value !== 'string') return false;
    try {
      const u = new URL(value);
      return u.protocol === 'https:' && !u.username && !u.password && (!u.port || u.port === '443') &&
        ['www.boamp.fr', 'boamp.fr', 'data.economie.gouv.fr', 'www.data.gouv.fr', 'data.gouv.fr', 'data.nantesmetropole.fr', 'opendata.bordeaux-metropole.fr'].includes(u.hostname);
    } catch (_) { return false; }
  };
  const invalid = () => { throw new Error('Invalid BOAMP/DECP link artifact'); };
  if (!data || data.schemaVersion !== 1 || !Array.isArray(data.sources) || data.sources.length !== paths.length ||
      !Array.isArray(data.links) || !data.counts) invalid();
  for (const path of paths) {
    const sources = data.sources.filter(s => s && s.path === path);
    if (sources.length !== 1 || !/^[a-f0-9]{64}$/.test(sources[0].sha256) ||
        !Number.isInteger(sources[0].count) || sources[0].count < 0) invalid();
  }
  const seen = new Set();
  const basis = ['buyer-published-contract-reference', 'buyer-exact-notice-lot', 'buyer-holder-siret-same-date'];
  const warnings = ['unconfirmed-no-exact-reference', 'different-cpv', 'multiple-decp-matches', 'multiple-boamp-matches'];
  for (const l of data.links) {
    if (!l || typeof l.boampId !== 'string' || !l.boampId.startsWith('boamp-') ||
        typeof l.decpId !== 'string' || !l.decpId.startsWith('decp-') ||
        !['confirmed', 'candidate'].includes(l.status) || !official(l.boampUrl) || !official(l.decpUrl) ||
        !Array.isArray(l.basis) || !l.basis.length || l.basis.some(b => !basis.includes(b)) ||
        !Array.isArray(l.warnings) || l.warnings.some(w => !warnings.includes(w))) invalid();
    if (l.status === 'candidate' ? (l.basis.length !== 1 || l.basis[0] !== 'buyer-holder-siret-same-date' ||
        !l.warnings.includes('unconfirmed-no-exact-reference')) :
        (l.basis.includes('buyer-holder-siret-same-date') || l.warnings.includes('unconfirmed-no-exact-reference'))) invalid();
    const key = JSON.stringify([l.boampId, l.decpId]);
    if (seen.has(key)) invalid();
    seen.add(key);
  }
  const counts = {
    confirmed: data.links.filter(l => l.status === 'confirmed').length,
    candidate: data.links.filter(l => l.status === 'candidate').length,
    ambiguous: data.links.filter(l => l.warnings.some(w => w.startsWith('multiple-'))).length,
    differentCpv: data.links.filter(l => l.warnings.includes('different-cpv')).length,
  };
  for (const [key, count] of Object.entries(counts)) if (data.counts[key] !== count) invalid();
  if (!Number.isInteger(data.counts.rawNoticeLotReferences) || data.counts.rawNoticeLotReferences < 0) invalid();
  return data.links;
}

// Reviewed findings remain annotations, never contract fields or scoring inputs.
function validatePublicLinkEvidence(data, linkArtifact) {
  const links = validateBoampDecpLinks(linkArtifact);
  const conclusions = ['reference-pattern-supported-unconfirmed', 'lot-compatible-unconfirmed',
    'disfavored-notice-lot-mapping-not-proven-different-legal-contract'];
  const invalid = () => { throw new Error('Invalid public link evidence ledger'); };
  if (!data || data.schemaVersion !== 1 || data.confirmed !== 0 || data.resolved !== 0 ||
      !data.sourceHashes || !Array.isArray(data.pairs) || data.pairs.length !== links.length) invalid();
  for (const s of linkArtifact.sources) if (data.sourceHashes[s.path] !== s.sha256) invalid();
  const seen = new Set();
  return data.pairs.map(p => {
    if (!p || !conclusions.includes(p.conclusion) || p.confirmed !== false || p.linkStatus !== 'candidate' ||
        p.resolution !== null || typeof p.notes !== 'string' || p.notes.length > 2000 ||
        typeof p.publishedReference !== 'string' || !p.publishedReference || p.publishedReference.length > 200 ||
        typeof p.decpContractId !== 'string' || !p.decpContractId || p.decpContractId.length > 200) invalid();
    const link = links.find(l => l.boampId === p.boampId && l.decpId === p.decpId &&
      l.boampUrl === p.boampUrl && l.decpUrl === p.decpUrl && l.status === 'candidate');
    const key = JSON.stringify([p.boampId, p.decpId]);
    if (!link || seen.has(key)) invalid();
    seen.add(key);
    return { boampId: p.boampId, decpId: p.decpId, conclusion: p.conclusion, notes: p.notes,
      publishedReference: p.publishedReference, decpContractId: p.decpContractId };
  });
}

function validatePublicLinkResolutions(data, linkArtifact) {
  const links = validateBoampDecpLinks(linkArtifact);
  const invalid = () => { throw new Error('Invalid public link resolutions'); };
  if (!data || data.schemaVersion !== 1 || !data.sourceHashes || !data.counts ||
      !Array.isArray(data.activePairs) || !Array.isArray(data.dismissedPairs) || !Array.isArray(data.tedNotices)) invalid();
  for (const s of linkArtifact.sources) if (data.sourceHashes[s.path] !== s.sha256) invalid();
  const seen = new Set();
  for (const [rows, dismissed] of [[data.activePairs, false], [data.dismissedPairs, true]]) {
    for (const p of rows) {
      const key = JSON.stringify([p.boampId, p.decpId]);
      const original = links.find(l => l.boampId === p.boampId && l.decpId === p.decpId &&
        l.boampUrl === p.boampUrl && l.decpUrl === p.decpUrl && l.status === p.status);
      if (!original || seen.has(key)) invalid();
      seen.add(key);
      if (dismissed) {
        if (p.disposition !== 'dismissed-notice-lot-candidate' || p.status !== 'candidate' ||
            p.replacementLinkConfirmed !== false || typeof p.reason !== 'string' || !p.reason || p.reason.length > 2000) invalid();
      } else if (p.disposition !== p.status || !Array.isArray(p.activeWarnings) ||
          p.activeWarnings.some(w => !['unconfirmed-no-exact-reference', 'different-cpv', 'multiple-decp-matches', 'multiple-boamp-matches'].includes(w))) invalid();
    }
  }
  if (seen.size !== links.length || data.counts.heuristicPairs !== links.length ||
      data.counts.activePairs !== data.activePairs.length || data.counts.dismissedPairs !== data.dismissedPairs.length ||
      data.counts.confirmedDecpLinks !== data.activePairs.filter(p => p.status === 'confirmed').length ||
      data.counts.ambiguousActivePairs !== data.activePairs.filter(p => p.activeWarnings.some(w => w.startsWith('multiple-'))).length) invalid();
  for (const p of data.activePairs) {
    const original = links.find(l => l.boampId === p.boampId && l.decpId === p.decpId);
    if (p.activeWarnings.includes('multiple-decp-matches') !== (data.activePairs.filter(l => l.boampId === p.boampId).length > 1) ||
        p.activeWarnings.includes('multiple-boamp-matches') !== (data.activePairs.filter(l => l.decpId === p.decpId).length > 1) ||
        p.activeWarnings.includes('different-cpv') !== original.warnings.includes('different-cpv') ||
        p.activeWarnings.includes('unconfirmed-no-exact-reference') !== original.warnings.includes('unconfirmed-no-exact-reference')) invalid();
  }
  const notices = new Set();
  for (const n of data.tedNotices) {
    if (!n || !/^\d{2}-\d+$/.test(n.boampNoticeId) || notices.has(n.boampNoticeId) ||
        !links.some(l => l.boampId.startsWith(`boamp-${n.boampNoticeId}-`)) ||
        !/^[1-9]\d{0,5}-20\d{2}$/.test(n.publicationNumber) ||
        n.url !== `https://ted.europa.eu/en/notice/-/detail/${n.publicationNumber}` ||
        !['verified-notice-version', 'unverified-notice-version'].includes(n.status) ||
        !/^\d{2}$/.test(n.version) || n.decpCrosswalkConfirmed !== false ||
        (n.status === 'verified-notice-version' && n.httpStatus !== '200')) invalid();
    notices.add(n.boampNoticeId);
  }
  if (data.counts.verifiedTedNoticeVersions !== data.tedNotices.filter(n => n.status === 'verified-notice-version').length ||
      data.counts.unverifiedTedNoticeVersions !== data.tedNotices.filter(n => n.status === 'unverified-notice-version').length) invalid();
  return data;
}

function publicLinkEvidenceLabel(p) {
  return p.conclusion === 'reference-pattern-supported-unconfirmed' ? 'Reference-pattern evidence; still unconfirmed.' :
    p.conclusion === 'lot-compatible-unconfirmed' ? 'Lot-compatible candidate; no identifier bridge.' :
    'Disfavored notice-lot mapping; not proof of a different legal contract.';
}

// Keep dataset IDs as the unit of loading and URL state. Country is only navigation:
// no combined country dataset, and no extra country parameter in shared links.
function setupDatasetSelection(countrySelect, datasetSelect, onChange) {
  const options = [...datasetSelect.options];
  const remembered = new Map();
  const countries = [...new Set(options.map(option => option.dataset.country))];
  for (const country of countries) {
    const option = countrySelect.ownerDocument.createElement('option');
    option.value = country;
    const flag = options.find(item => item.dataset.country === country).textContent.match(/[\u{1F1E6}-\u{1F1FF}]{2}/u)?.[0];
    option.textContent = `${flag ? flag + ' ' : ''}${country}`;
    countrySelect.append(option);
  }
  function sync() {
    const selected = options.find(option => option.value === datasetSelect.value);
    if (!selected) return;
    const country = selected.dataset.country;
    countrySelect.value = country;
    remembered.set(country, selected.value);
    // Reuse the option nodes: preserve their IDs, metadata and translated text.
    datasetSelect.replaceChildren(...options.filter(option => option.dataset.country === country));
    datasetSelect.value = selected.value;
  }
  countrySelect.addEventListener('change', () => {
    const country = countrySelect.value;
    const candidates = options.filter(option => option.dataset.country === country);
    datasetSelect.replaceChildren(...candidates);
    datasetSelect.value = remembered.get(country) || candidates[0].value;
    sync();
    onChange();
  });
  datasetSelect.addEventListener('change', () => { sync(); onChange(); });
  // Deep links can select an option which is currently detached from the menu.
  function selectDataset(id) {
    const option = options.find(option => option.value === id);
    if (!option) return false;
    datasetSelect.replaceChildren(...options.filter(item => item.dataset.country === option.dataset.country));
    datasetSelect.value = id;
    sync();
    return true;
  }
  sync();
  return { sync, selectDataset };
}
