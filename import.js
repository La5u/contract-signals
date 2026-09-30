(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.ContractImport = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const MAX_TEXT = 25 * 1024 * 1024;
  const MAX_RECORDS = 20000;
  const CURRENCIES = new Set(typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('currency') : ['EUR', 'USD', 'GBP', 'CAD', 'AUD', 'CHF', 'JPY']);
  const ALIASES = {
    id: ['id', 'contract id', 'award id', 'identifier'], buyer: ['buyer', 'buyer name', 'purchaser', 'acheteur'],
    description: ['description', 'title', 'contract description'], amount: ['amount', 'value', 'contract value'],
    currency: ['currency', 'currency code'], offers: ['offers', 'number of offers', 'tenderers'], date: ['date', 'award date'],
    durationMonths: ['duration months', 'durationmonths'], cpv: ['cpv', 'cpv code'], procedure: ['procedure', 'procurement method'],
    supplier: ['supplier', 'supplier name', 'winner'], supplierId: ['supplier id', 'supplier identifier'],
    buyerSiret: ['buyer siret', 'buyerSiret'], directAward: ['direct award', 'directAward'], dataStatus: ['data status', 'dataStatus'],
    source: ['source', 'source url', 'sourceUrl']
  };
  const CANONICAL = Object.keys(ALIASES);
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  function fail(message) { throw new Error(message); }
  function textValue(v) { return typeof v === 'string' ? v.trim() : ''; }
  function num(v) {
    if (v === null || v === undefined || (typeof v === 'string' && !v.trim())) return null;
    if (typeof v === 'number') return Number.isFinite(v) ? v : null;
    if (typeof v !== 'string' || !/^-?(?:\d+\.?\d*|\.\d+)$/.test(v.trim())) return null;
    const n = Number(v); return Number.isFinite(n) ? n : null;
  }
  function bool(v) {
    if (typeof v === 'boolean') return v;
    if (typeof v !== 'string') return null;
    if (/^(true|yes|1)$/i.test(v.trim())) return true;
    if (/^(false|no|0)$/i.test(v.trim())) return false;
    return null;
  }
  function normalized(record, method, warnings, context = '') {
    if (!record || typeof record !== 'object' || Array.isArray(record)) fail('Each record must be an object.');
    const r = { ...record };
    const label = context || (r.id != null ? `record ${r.id}` : 'record');
    const numeric = key => {
      const value = r[key];
      if (value === null || value === undefined || value === '') { r[key] = null; return; }
      const parsed = num(value);
      if (parsed === null) fail(`${label}: invalid ${key} value.`);
      r[key] = parsed;
    };
    for (const key of ['amount', 'offers', 'durationMonths']) numeric(key);
    if (r.directAward !== null && r.directAward !== undefined && r.directAward !== '') {
      const parsed = bool(r.directAward);
      if (parsed === null) fail(`${label}: invalid directAward value.`);
      r.directAward = parsed;
    } else if (r.directAward === '') r.directAward = null;
    if (r.dataStatus == null || r.dataStatus === '') { r.dataStatus = 'unverified'; warnings.add('dataStatus defaulted to unverified for records without an explicit status.'); }
    if (typeof r.currency === 'string') r.currency = r.currency.trim();
    if (r.currency === '') r.currency = null;
    if (r.currency != null) {
      if (typeof r.currency !== 'string' || !/^[A-Za-z]{3}$/.test(r.currency.trim())) fail(`${label}: invalid currency value.`);
      r.currency = r.currency.trim().toUpperCase();
      if (!CURRENCIES.has(r.currency)) { warnings.add(`Unrecognized currency code ${r.currency}; currency was not retained.`); r.currency = null; }
    }
    if (r.currency == null && r.amount != null) warnings.add('Currency is missing or unrecognized; amounts are not assumed to be EUR.');
    if (method === 'french') { delete r.dataFamily; delete r.cohortId; r.assessmentMode = 'french'; }
    else r.assessmentMode = 'browse';
    return r;
  }
  function csvRows(input) {
    let s = input.charCodeAt(0) === 0xFEFF ? input.slice(1) : input;
    const first = s.split(/\r?\n/, 1)[0] || '';
    const count = delimiter => {
      let quoted = false, fields = 1;
      for (let i = 0; i < first.length; i++) {
        if (first[i] === '"' && quoted && first[i + 1] === '"') i++;
        else if (first[i] === '"') quoted = !quoted;
        else if (first[i] === delimiter && !quoted) fields++;
      }
      return fields;
    };
    const delim = count(';') > count(',') ? ';' : ',';
    const rows = []; let row = [], cell = '', quoted = false;
    for (let i = 0; i < s.length; i++) {
      const c = s[i];
      if (quoted) { if (c === '"' && s[i + 1] === '"') { cell += '"'; i++; } else if (c === '"') quoted = false; else cell += c; }
      else if (c === '"' && cell === '') quoted = true;
      else if (c === delim) { row.push(cell); cell = ''; }
      else if (c === '\n' || c === '\r') { if (c === '\r' && s[i + 1] === '\n') i++; row.push(cell); cell = ''; if (row.some(x => x !== '')) rows.push(row); if (rows.length > MAX_RECORDS + 1) fail('Import exceeds the 20,000 normalized record limit.'); row = []; }
      else cell += c;
    }
    if (quoted) fail('CSV contains an unterminated quoted field.');
    row.push(cell); if (row.some(x => x !== '')) rows.push(row);
    return rows;
  }
  function csv(input, mapping, warnings) {
    const rows = csvRows(input); if (!rows.length) fail('CSV has no header.');
    const headers = rows.shift().map(x => x.trim());
    if (headers.length > 1000) fail('CSV header exceeds the 1,000-column limit.');
    const headerSet = new Set();
    for (const header of headers) {
      const key = header.toLowerCase();
      if (headerSet.has(key)) fail(`CSV contains duplicate header ${header || '(blank)'}.`);
      headerSet.add(key);
    }
    const lookup = new Map(headers.map(h => [h, h]));
    const columns = {};
    for (const c of CANONICAL) {
      const chosen = own(mapping, c) ? mapping[c] : null;
      if (chosen != null) {
        if (typeof chosen !== 'string' || !lookup.has(chosen)) fail(`Invalid column mapping for ${c}.`);
        columns[c] = headers.indexOf(chosen);
      } else {
        const aliases = ALIASES[c].map(a => a.toLowerCase());
        columns[c] = headers.findIndex(h => aliases.includes(h.toLowerCase()));
      }
    }
    for (const c of ['id', 'buyer', 'description']) if (columns[c] < 0) fail(`CSV requires a ${c} column.`);
    const out = rows.map((cells, index) => {
      if (cells.length > headers.length) fail(`CSV row ${index + 2} has more fields than its header.`);
      const get = c => columns[c] < 0 ? '' : cells[columns[c]] || '';
      const record = { id: get('id').trim(), buyer: get('buyer').trim(), description: get('description').trim() };
      if (!record.id || !record.buyer || !record.description) fail(`CSV row ${index + 2} is missing a required value.`);
      for (const c of ['amount', 'offers', 'durationMonths']) {
        const value = get(c).trim();
        record[c] = value === '' ? null : num(value);
        if (value !== '' && record[c] === null) fail(`CSV row ${index + 2} (${record.id}): invalid ${c} value.`);
      }
      record.currency = get('currency').trim().toUpperCase() || null;
      record.date = get('date').trim() || null; record.cpv = get('cpv').trim() || null;
      record.procedure = get('procedure').trim() || null; record.supplier = get('supplier').trim() || null;
      record.buyerSiret = get('buyerSiret').trim() || null;
      const directAward = get('directAward').trim();
      record.directAward = directAward ? bool(directAward) : null;
      if (directAward && record.directAward === null) fail(`CSV row ${index + 2} (${record.id}): invalid directAward value.`);
      if (get('source').trim()) record.source = get('source').trim();
      if (get('dataStatus').trim()) record.dataStatus = get('dataStatus').trim();
      if (get('supplierId').trim()) record.supplierIds = [{ id: get('supplierId').trim() }];
      return record;
    });
    return out;
  }
  function ocidRecords(input, method, warnings) {
    let packages = Array.isArray(input) ? input : [input];
    const releases = []; const seen = new Set();
    for (const pkg of packages) {
      if (!pkg || typeof pkg !== 'object') fail('Invalid OCDS package.');
      const entries = Array.isArray(pkg.records) ? pkg.records : [];
      let usedCompiled = false;
      for (const entry of entries) {
        if (entry.compiledRelease) { releases.push(entry.compiledRelease); usedCompiled = true; }
        else if (Array.isArray(entry.releases) && entry.releases.length) releases.push(...entry.releases);
        else if (entry.url || entry.releases) fail(`Incomplete OCDS record entry${entry.id ? ` ${entry.id}` : ''}: release data is missing; fetch its URL or provide releases/compiledRelease.`);
        else if (entry.tender || entry.awards) releases.push(entry);
      }
      if (!usedCompiled && Array.isArray(pkg.releases)) releases.push(...pkg.releases);
      if (!entries.length && !Array.isArray(pkg.releases) && (pkg.tender || pkg.awards)) releases.push(pkg);
    }
    const byOcid = new Map();
    for (const rel of releases) {
      if (!rel || typeof rel !== 'object' || Array.isArray(rel) || rel.url && !rel.ocid) fail(`Incomplete OCDS release${rel?.url ? ` reference (${rel.url})` : ''}: release content is missing; fetch its URL.`);
      const ocid = textValue(rel.ocid);
      if (!ocid) fail('OCDS release is missing an OCID.');
      if (byOcid.has(ocid)) fail(`Multiple OCDS releases for OCID ${ocid}; select a single version explicitly.`);
      byOcid.set(ocid, rel);
    }
    const out = [];
    for (const [ocid, rel] of byOcid) {
      const parties = Array.isArray(rel.parties) ? rel.parties : [];
      const namedBuyer = rel.buyer?.name || (rel.buyer?.id != null ? parties.find(p => p.id === rel.buyer.id)?.name : null);
      const buyerParties = parties.filter(p => Array.isArray(p.roles) && p.roles.includes('buyer'));
      if (!namedBuyer && buyerParties.length > 1) fail(`OCDS release ${ocid} has multiple buyers and no explicit buyer reference.`);
      const buyer = namedBuyer || buyerParties[0]?.name || '';
      const awardList = Array.isArray(rel.awards) ? rel.awards : [];
      for (const award of awardList) {
        const awardId = textValue(award.id); if (!awardId) fail(`OCDS award under ${ocid} is missing an ID.`);
        const key = `${ocid}/${awardId}`; if (seen.has(key)) fail(`Duplicate OCDS award ${key}.`); seen.add(key);
        const suppliers = (award.suppliers || []).map(ref => (ref.id != null ? parties.find(p => p.id === ref.id) : null) || ref);
        const value = award.value || {};
        let date = null;
        if (award.date != null && award.date !== '') {
          if (typeof award.date !== 'string' || !/^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))?$/.test(award.date) || !Number.isFinite(Date.parse(award.date))) fail(`OCDS award ${key} has an invalid date.`);
          date = award.date.slice(0, 10);
          if (new Date(date).toISOString().slice(0, 10) !== date) fail(`OCDS award ${key} has an invalid calendar date.`);
        }
        const codes = [...new Set((award.items || rel.tender?.items || []).map(i => i.classification).filter(c => /^cpv$/i.test(c?.scheme || '')).map(c => c.id).filter(Boolean))];
        const cpv = codes.length === 1 ? codes[0] : null;
        if (codes.length > 1) warnings.add('Some awards cover multiple CPV classifications; no single sector was chosen arbitrarily.');
        const record = { id: key, ocid, awardId, buyer, description: award.title || rel.tender?.title || '', amount: value.amount ?? null, currency: value.currency || null,
          date, cpv,
          supplier: suppliers.map(p => p.name).filter(Boolean).join(', ') || null,
          supplierIds: suppliers.map(p => p.identifier?.id ? { id: String(p.identifier.id), identifierType: p.identifier.scheme || null } : p.id ? { id: String(p.id) } : null).filter(Boolean),
          offers: null, directAward: null };
        warnings.add('OCDS award records are published awards, not necessarily signed contracts; status should be verified before treating them as contracts.');
        if (out.length >= MAX_RECORDS) fail('Import exceeds the 20,000 normalized record limit.');
        out.push(normalized(record, method, warnings, `OCDS award ${key}`));
      }
    }
    return out;
  }
  function parse(text, { filename = '', method = 'browse', mapping = {} } = {}) {
    if (typeof text !== 'string') fail('Import text must be a string.');
    if (text.length > MAX_TEXT || new TextEncoder().encode(text).byteLength > MAX_TEXT) fail('File exceeds the 25 MiB import limit.');
    if (!text.trim()) fail('File is empty.');
    if (!['browse', 'french'].includes(method)) fail('Method must be browse or french.');
    if (!mapping || typeof mapping !== 'object' || Array.isArray(mapping)) fail('Mapping must be an object.');
    const warnings = new Set(); let data, format;
    const trimmed = text.replace(/^\uFEFF/, '').trim();
    if (/^[\[{]/.test(trimmed)) {
      try { data = JSON.parse(trimmed); } catch (_) { fail('Invalid JSON file.'); }
      const isRelease = value => value && typeof value === 'object' && !Array.isArray(value) && typeof value.ocid === 'string';
      const releaseArray = Array.isArray(data) && data.length > 0 && data.every(isRelease);
      const envelopeRecords = !Array.isArray(data) && Array.isArray(data.records) &&
        data.records.every(r => !r?.compiledRelease && !Array.isArray(r?.releases) && !r?.tender && !r?.awards && !r?.url);
      if (releaseArray) {
        format = 'ocds'; data = ocidRecords(data, method, warnings);
      } else if (Array.isArray(data) || envelopeRecords) {
        const records = Array.isArray(data) ? data : data.records;
        if (records.length > MAX_RECORDS) fail('Import exceeds the 20,000 normalized record limit.');
        format = 'json'; data = records.map(r => normalized(r, method, warnings, `record ${r?.id ?? '(unknown id)'}`));
      } else {
        format = 'ocds'; data = ocidRecords(data, method, warnings);
      }
    } else { format = 'csv'; data = csv(text, mapping, warnings).map(r => normalized(r, method, warnings)); }
    if (!data.length) fail('File contains no records.');
    if (data.length > MAX_RECORDS) fail('Import exceeds the 20,000 normalized record limit.');
    return { records: data, format, warnings: [...warnings] };
  }
  function columns(text, filename = '') {
    if (typeof text !== 'string' || text.length > MAX_TEXT) fail('Invalid or oversized import text.');
    const rows = csvRows(text);
    if (!rows.length) return [];
    const headers = rows[0].map(x => x.trim());
    if (headers.length > 1000) fail('CSV header exceeds the 1,000-column limit.');
    if (new Set(headers.map(h => h.toLowerCase())).size !== headers.length) fail('CSV contains duplicate headers.');
    return headers;
  }
  async function fingerprint(text, method = 'browse', mapping = {}) {
    const subtle = globalThis.crypto?.subtle;
    if (!subtle) fail('WebCrypto SHA-256 is unavailable.');
    const bytes = new TextEncoder().encode(JSON.stringify([text, method, mapping]));
    const hash = await subtle.digest('SHA-256', bytes);
    return [...new Uint8Array(hash)].map(b => b.toString(16).padStart(2, '0')).join('');
  }
  return { parse, columns, fingerprint };
});
