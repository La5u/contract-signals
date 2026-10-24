// The explorer page (index.html): loading, filters, table, record panel, review notes and exports.
// Scoring and records come from the engine files loaded before it (tools/engine.cjs).
'use strict';

function startExplorer() {
  const body = document.querySelector('#contracts');
  const status = document.querySelector('#status');
  const fileHelp = document.querySelector('#file-help');
  const controls = Object.fromEntries(['filter-country', 'date-from', 'date-to', 'filter-buyer', 'filter-supplier', 'filter-procedure', 'search', 'minimum', 'flagged', 'official', 'adjudicated', 'investigation', 'indicator', 'legal', 'notice-context', 'assessment', 'sort', 'sector', 'project', 'group-by', 'min-score', 'review', 'verification'].map(id => [id, document.getElementById(id)]));
  const datasetSelect = document.querySelector('#dataset');
  // datasets.js; South Korea's coverage is relative to its host.
  const datasets = Object.fromEntries(Object.entries(globalThis.DATASETS).map(([key, d]) =>
    [key, d.remote === 'korea' ? { ...d, coverage: `${KOREA_BASE}/${d.coverage}` } : d]));
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
    body.append(element('p', `Publisher: ${s.publisher}. Licence: ${s.licence}.`));
    const list = element('ul');
    for (const [label, url] of s.links) {
      if (/API|schema|licence|legal notice|reuse terms|dedication/i.test(label)) continue;
      const item = element('li'); item.append(sourceLink(url, label)); list.append(item);
    }
    const coverage = element('li'); const coverageLink = element('a', 'Extraction details (JSON)'); coverageLink.href = selected.coverage; coverage.append(coverageLink); list.append(coverage);
    const documentation = element('li'); const documentationLink = element('a', 'Source documentation'); documentationLink.href = 'docs/data-sources.md'; documentation.append(documentationLink); list.append(documentation);
    body.append(list);
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
  let boampDecpLinks = [];
  let publicLinkEvidence = [];
  let publicLinkResolutions = null;
  let supplierProceedings = new Map();
  const FRENCH_LINK_DATASETS = new Set(['decp', 'boamp', 'tours', 'consultations']);
  let linkEvidenceStarted = false;
  // South Korea: the buyer list loads with the dataset; one buyer's shard loads when it is chosen.
  let koreaBuyer = '', koreaMeta = null, koreaBuyers = null;
  let koreaScanController = null, koreaScanVersion = 0, koreaNationwide = false;
  let koreaScanPage = 0, koreaScanResult = null, koreaScanMessage = '', koreaSnapshotKey = '';
  const koreaScanPanel = document.querySelector('#korea-scan');
  const koreaScanStatus = document.querySelector('#korea-scan-status');
  const koreaScanNext = document.querySelector('#korea-scan-next');
  const koreaScanPrevious = document.querySelector('#korea-scan-previous');
  const koreaPicker = document.querySelector('#korea-picker');
  const koreaSearch = document.querySelector('#korea-search');
  const koreaResults = document.querySelector('#korea-results');
  const koreaJson = (path, signal) => fetch(`${KOREA_BASE}/${path}`, { signal, cache: 'no-store' }).then(response => {
    if (!response.ok) throw new Error(`${KOREA_BASE}/${path}: HTTP ${response.status}`);
    return response.json();
  });
  function koreaIndex() {
    if (!koreaBuyers) koreaBuyers = Promise.all([koreaJson('meta.json'), koreaJson('buyers.json')]).then(([meta, buyers]) => {
      koreaMeta = meta;
      return buyers;
    }).catch(error => { koreaBuyers = null; throw error; });
    return koreaBuyers;
  }
  function koreaShard(n, signal) {
    return koreaJson(`s/${String(n).padStart(4, '0')}.json`, signal);
  }
  function cancelKoreaScan(message = 'Filters changed. Scan again to apply the current filters.') {
    koreaScanVersion++;
    koreaScanController?.abort();
    koreaScanController = null;
    koreaScanResult = null;
    koreaScanMessage = message;
    if (koreaNationwide) {
      contracts = []; selectionMemo = null; rowsForExport = []; pageRowsForCopy = [];
      closeDetail({ restoreFocus: false });
    }
  }
  async function startKoreaScan(wantedPage = 0) {
    cancelKoreaScan('Scanning…');
    const version = koreaScanVersion;
    const controller = koreaScanController = new AbortController();
    koreaScanPage = wantedPage;
    const options = selectionOptions();
    // Review notes are also snapshotted: subsequent edits require a new scan.
    const reviewWanted = controls.review.value;
    const reviewSnapshot = structuredClone(reviews);
    const reviewPrefix = reviewScope() + '|';
    const reviewPredicate = c => {
      const mark = reviewSnapshot[c.collectionId ? `${c.collectionId}|${c.originalId}` : reviewPrefix + c.id]?.status || '';
      return !reviewWanted || (reviewWanted === '@none' ? !mark : reviewWanted === '@any' ? Boolean(mark) : mark === reviewWanted);
    };
    koreaSnapshotKey = koreaFilterKey();
    render();
    try {
      const scan = datasetSelect.value === 'global' ? scanPublishedPage : scanKoreaPage;
      const result = await scan({ meta: koreaMeta, buyers: datasetSelect.value === 'global' ? [] : await koreaIndex(), fetchShard: koreaShard,
        collections: Object.entries(datasets).filter(([key, value]) => key !== 'global' && !value.remote).map(([key, value]) => ({ key, label: `${key} · ${value.sources.publisher}` })),
        loadCollection: async (key, signal) => {
          const files = globalThis.DATASET_FILES?.[key] || [].concat(datasets[key].path);
          const parts = [];
          for (const file of files) {
            const response = await fetch(file, { signal });
            if (!response.ok) throw new Error(`${file}: HTTP ${response.status}`);
            parts.push(await response.json());
          }
          return parts.flat();
        },
        korea: async () => { const buyers = await koreaIndex(); return { meta: koreaMeta, buyers, fetchShard: koreaShard }; },
        offset: wantedPage * Math.min(200, pageSize), limit: Math.min(200, pageSize), signal: controller.signal,
        predicate: c => reviewPredicate(c) && selectContracts([c], options).length > 0,
        progress: p => { if (version === koreaScanVersion) {
          koreaScanStatus.textContent = `Scanning: ${p.examined.toLocaleString()} records checked · ${p.matches.toLocaleString()} matches so far (partial) · ${p.retained} retained.`;
        } }
      });
      if (version !== koreaScanVersion || controller.signal.aborted || !koreaNationwide) return;
      koreaScanController = null;
      koreaScanResult = result;
      contracts = result.rows;
      selectionMemo = null;
      page = 0;
      koreaScanMessage = `${datasetSelect.value === 'global' ? 'Collections scan' : 'Nationwide'} page ${wantedPage + 1}: ${result.rows.length} matches retained (page cap ${Math.min(200, pageSize)}). ${result.complete ? `${result.matches.toLocaleString()} total matches; scan complete.` : `At least ${result.matches.toLocaleString()} matches; count partial. More matches accessible with Next scan page.`} ${result.examined.toLocaleString()} records checked. Export covers this page only.`;
      render();
    } catch (error) {
      if (version !== koreaScanVersion) return;
      koreaScanController = null;
      koreaScanMessage = error.name === 'AbortError' ? 'Scan cancelled. Scan again to restart.' : `Scan failed; no complete results: ${error.message}. Retry with Scan.`;
      render();
    }
  }
  document.querySelector('#korea-all').addEventListener('click', () => chooseKoreaBuyer(''));
  document.querySelector('#korea-scan-start').addEventListener('click', () => startKoreaScan());
  document.querySelector('#korea-scan-cancel').addEventListener('click', () => { cancelKoreaScan('Scan cancelled. Scan again to restart.'); render(); });
  koreaScanNext.addEventListener('click', () => startKoreaScan(koreaScanPage + 1));
  koreaScanPrevious.addEventListener('click', () => startKoreaScan(Math.max(0, koreaScanPage - 1)));
  const koreaKey = text => String(text || '').toLowerCase().replace(/\s+/g, '');
  function showKoreaResults(buyers) {
    const wanted = koreaKey(koreaSearch.value);
    const found = [];
    for (const b of buyers) {
      if (!wanted || koreaKey(b[1]).includes(wanted) || b[0].startsWith(wanted)) found.push(b);
      if (found.length >= 30) break;
    }
    koreaResults.replaceChildren(...found.map(b => {
      const item = element('li');
      const button = element('button', `${b[1]} · ${b[2] || 'institution'} · ${b[3]} contracts`, 'link-button');
      button.type = 'button';
      button.addEventListener('click', () => chooseKoreaBuyer(b[0]));
      item.append(button);
      return item;
    }));
    if (!found.length) koreaResults.append(element('li', 'No contracting institution matches.', 'muted'));
  }
  function chooseKoreaBuyer(code) {
    koreaBuyer = code;
    pendingView = null;
    loadDataset();
  }
  koreaSearch.addEventListener('input', () => koreaIndex().then(showKoreaResults).catch(() => {}));
  async function loadKorea(version) {
    koreaPicker.hidden = false;
    const buyers = await koreaIndex();
    if (version !== loadVersion) return;
    showKoreaResults(buyers);
    const buyer = koreaBuyer && buyers.find(b => b[0] === koreaBuyer);
    if (!buyer) {
      koreaBuyer = '';
      koreaNationwide = true;
      koreaScanPanel.hidden = false;
      accept([]);
      startKoreaScan();
      return;
    }
    koreaSearch.value = buyer[1];
    status.textContent = `Loading ${buyer[3]} contracts of ${buyer[1]}…`;
    const shards = await Promise.all(koreaParts(buyer).map(n => koreaShard(n)));
    if (version === loadVersion) accept(shards.flatMap(shard => koreaRecords(koreaMeta, shard, buyer)));
  }
  // First-page preview (prefetch.js, tools/build-first-pages.cjs): the default view's top rows,
  // shown read-only until the full dataset is in. Filters, sorting, export and the record panel
  // would act on 50 rows only, so they stay locked.
  let previewing = false, previewTotal = 0;
  const lockedBefore = new Map();
  function setPreviewLock(on) {
    previewing = on;
    const elements = [...Object.values(controls), document.querySelector('#sort-field'), document.querySelector('#sort-direction'), ...document.querySelectorAll('.sort-header, #clear-filters')];
    for (const el of elements) {
      if (on) { lockedBefore.set(el, el.disabled); el.disabled = true; }
      else if (lockedBefore.has(el)) el.disabled = lockedBefore.get(el);
    }
    if (!on) lockedBefore.clear();
    document.querySelector('.table-wrap').inert = on;
    document.querySelector('#results').setAttribute('aria-busy', String(on));
  }
  // Optional: never delays the records; badges appear when it arrives. A missing or invalid file shows none.
  fetch('data/supplier-proceedings.json').then(response => {
    if (!response.ok) throw new Error('Supplier proceedings unavailable');
    return response.json();
  }).then(data => {
    supplierProceedings = validateSupplierProceedings(data);
    if (loaded && !usingLocalFile) {
      render();
      const record = openId && contracts.find(c => c.id === openId);
      if (record) renderDetail(record);
    }
  }).catch(error => console.warn('Supplier proceedings not shown:', error.message));
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
  if (Object.hasOwn(datasets, initialView.dataset)) datasetSelect.value = initialView.dataset;
  let pendingView = location.hash ? initialView : null;
  const datasetSelection = setupDatasetSelection(document.querySelector('#country'), datasetSelect, () => {
    pendingView = null;
    loadDataset();
  });
  // These new navigation labels live here because the shared dictionaries are generated
  // separately. Existing country names and cohort labels use the normal i18n observer.
  const selectionLabels = { en: ['Country', 'Source / cohort'], fr: ['Pays', 'Source / cohorte'], es: ['País', 'Fuente / cohorte'] };
  const selectionLanguage = uiLocale.slice(0, 2);
  const [countryLabel, sourceLabel] = selectionLabels[selectionLanguage] || selectionLabels.en;
  document.querySelector('#country-label').textContent = countryLabel;
  document.querySelector('#source-label').textContent = sourceLabel;
  // The full label joins the country and the selected source/cohort.
  const datasetLabel = () => {
    const option = datasetSelect.selectedOptions[0], country = option.dataset.country;
    return `${typeof i18nTranslate === 'function' ? i18nTranslate(country) : country} · ${option.textContent.replace(/^\s*[\u{1F1E6}-\u{1F1FF}]{2}/u, '').trim()}`;
  };
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
  let reviewsVersion = 0, selectionMemo = null;
  function saveReviews() {
    reviewsVersion++;
    try { localStorage.setItem(REVIEW_STORE, JSON.stringify(reviews)); reviewStorageWorks = true; } catch { reviewStorageWorks = false; }
  }
  const reviewScope = () => usingLocalFile ? `local:${localFileIdentity}` : datasetSelect.value;
  const reviewKey = c => c.collectionId ? `${c.collectionId}|${c.originalId}` : `${reviewScope()}|${c.id}`;
  const reviewOf = c => reviews[reviewKey(c)] || null;
  function setReview(c, patch) {
    const key = reviewKey(c);
    const entry = { ...(reviews[key] || {}), ...patch, updatedAt: new Date().toISOString() };
    if (!entry.status && !entry.note?.trim()) delete reviews[key]; else reviews[key] = entry;
    saveReviews();
    renderReviewSummary();
    if (koreaNationwide) render();
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
    document.querySelector('#review-filters').hidden = !counts.total && !controls.review.value;
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
      if (id === 'korea-buyer') { koreaBuyer = view[id] || ''; continue; }
      if (id === 'indicator' && view[id] && indicatorLabels.has(view[id]) && ![...controls[id].options].some(o => o.value === view[id])) {
        const option = element('option', indicatorLabels.get(view[id])); option.value = view[id]; controls[id].append(option);
      }
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
    for (const [, id] of VIEW_FIELDS) view[id] = id === 'open-record' ? openId : id === 'korea-buyer' ? (datasetSelect.value === 'korea' && !usingLocalFile ? koreaBuyer : '') : controls[id].value;
    for (const id of VIEW_FLAGS) view[id] = controls[id].checked;
    return view;
  }
  // replaceState keeps the link current without adding a history entry per keystroke.
  function writeView() {
    const hash = viewStateToHash(currentView());
    if (hash === location.hash) return;
    try { history.replaceState(null, '', hash || location.pathname + location.search); } catch { /* Some file:// contexts refuse history updates. */ }
  }
  const FILTER_VALUES = ['filter-country', 'date-from', 'date-to', 'filter-buyer', 'filter-supplier', 'filter-procedure', 'minimum', 'sector', 'group-by', 'project', 'assessment', 'min-score', 'indicator', 'notice-context', 'legal', 'review', 'verification'];
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
      element('p', `${p.contracts} contract(s)${p.firstDate ? ` · ${p.firstDate} → ${p.lastDate}` : ''} · ${p.assessed} assessed · ${p.flagged} with a signal (${pct(p.flagged, p.assessed)}). The table below now shows only these contracts. Compared with the ${p.scopeSize} records of the same dataset; amounts are never summed.`));
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
    if (koreaNationwide) {
      fillSelect(controls.indicator, [['', 'All indicators'], ...indicatorLabels].filter(([id], i) => id || i === 0));
      for (const id of ['notice-context', 'legal', 'verification', 'official', 'adjudicated', 'investigation']) {
        controls[id].closest('label').dataset.available = 'true';
        if (controls[id].options) for (const option of controls[id].options) option.hidden = false;
      }
      return;
    }
    const officialCount = contracts.filter(c => c.officialFinding === true).length;
    signalCounts = new Map();
    const present = new Set();
    // Counted per shared indicator kind, the value the filter matches (one row per kind).
    for (const c of contracts) {
      const kinds = new Set();
      for (const r of getAssessment(c).checks) {
        const kind = indicatorKind(r.id);
        if (!kind) continue;
        if (r.status !== 'not-applicable') present.add(kind);
        if (r.status === 'signal') kinds.add(kind);
      }
      for (const kind of kinds) signalCounts.set(kind, (signalCounts.get(kind) || 0) + 1);
    }
    if (officialCount) { present.add('official-finding'); signalCounts.set('official-finding', officialCount); }
    // Only offer context filters supported by the full loaded dataset, not the current results.
    const availableNotices = new Set();
    const availableLegal = new Set();
    const availableVerification = new Set(contracts.map(c => c.verification?.status).filter(Boolean));
    for (const c of contracts) {
      const e = c.noticeEvidence;
      if (e) {
        if (e.procedureDescription || e.justifications.some(j => j.text)) availableNotices.add('explanation');
        if (e.awardCriteria.length) availableNotices.add('criteria');
        if (e.kind === 'correction') availableNotices.add('correction');
        if (e.ted.length) availableNotices.add('ted');
      }
      if (declaredWithoutCompetition(c)) availableLegal.add('direct');
      for (const citation of getLegalContext(c)) { availableLegal.add('cited'); availableLegal.add(citation.article); }
      if (c.complaints?.length) availableLegal.add('py-complaint');
      if (c.secop2PublicCounterparty?.labelled) availableLegal.add('co-public');
      if (softwareMaintenanceContext(c)) availableLegal.add('fr-software');
    }
    for (const [id, available] of [['notice-context', availableNotices], ['legal', availableLegal], ['verification', availableVerification]]) {
      for (const option of controls[id].options) option.hidden = Boolean(option.value && !available.has(option.value));
      controls[id].closest('label').dataset.available = String(available.size > 0);
    }
    for (const [id, available] of [['official', officialCount > 0], ['adjudicated', contracts.some(hasAdjudicatedCorruption)], ['investigation', contracts.some(hasReportedInvestigation)]]) {
      controls[id].closest('label').dataset.available = String(available);
    }
    const activeIndicator = pendingView?.indicator || controls.indicator.value;
    if (activeIndicator && indicatorLabels.has(activeIndicator)) present.add(activeIndicator);
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
  // Sources that disagree are shown as the full range of their published amounts, never one pick.
  const formatAmount = c => Array.isArray(c.verification?.amountRange) ? c.verification.amountRange.map(a => moneyFor(c).format(a)).join(' – ') : c.amount == null ? '—' : c.amount === 0 ? 'declared 0 (likely undisclosed)' : ({ 'at-least': '≥ ', 'more-than': '> ', approximate: '≈ ' }[c.amountQualifier] || '') + moneyFor(c).format(c.amount);
  // In the table a range takes two lines (low, then “– high”), so it never runs into the next column.
  function amountCell(c) {
    const range = c.verification?.amountRange;
    if (!Array.isArray(range)) return element('td', formatAmount(c), 'numeric');
    const cell = element('td', null, 'numeric amount-range');
    cell.title = 'Sources disagree on the amount: range of the published values';
    // Whole units keep each line inside narrow columns; the record panel keeps the exact amounts.
    const options = moneyFor(c).resolvedOptions();
    const whole = new Intl.NumberFormat(options.locale, { style: 'currency', currency: options.currency, maximumFractionDigits: 0, minimumFractionDigits: 0 });
    cell.append(element('span', whole.format(range[0])), element('span', `– ${whole.format(range[1])}`));
    return cell;
  }
  function scoreChip(c) {
    const breakdown = getScoreBreakdown(c);
    const level = scoreLevel(breakdown.score, hasIncompleteData(c));
    const chip = element('span', breakdown.score == null ? 'Not assessed' : `${breakdown.score} / 100`, `score-chip level-${level.id}`);
    chip.title = `${level.label} — editorial index, not a probability nor legal gravity.`;
    return chip;
  }
  function selectionOptions() {
    return { country: controls['filter-country'].value, dateFrom: controls['date-from'].value, dateTo: controls['date-to'].value, buyer: controls['filter-buyer'].value, supplier: controls['filter-supplier'].value, procedure: controls['filter-procedure'].value, search: controls.search.value, minimum: Math.max(0, Number(controls.minimum.value) || 0), minScore: Number(controls['min-score'].value) || 0, flagged: controls.flagged.checked, official: controls.official.checked, adjudicated: controls.adjudicated.checked, investigation: controls.investigation.checked, indicator: controls.indicator.value, legal: controls.legal.value, noticeContext: controls['notice-context'].value, assessment: controls.assessment.value, sector: controls.sector.value, project: controls.project.value, verification: controls.verification.value, sort: controls.sort.value };
  }
  function koreaFilterKey() { return JSON.stringify([selectionOptions(), controls.review.value, reviewsVersion, pageSize, controls['group-by'].value]); }
  function render() {
    if (koreaNationwide && (koreaScanController || koreaScanResult) && koreaSnapshotKey !== koreaFilterKey()) cancelKoreaScan();
    syncSortHeaders();
    if (!loaded) return;
    // An active filter from a shared URL remains visible even when it matches no records.
    for (const id of ['notice-context', 'legal', 'verification', 'official', 'adjudicated', 'investigation']) {
      const control = controls[id];
      const active = control.type === 'checkbox' ? control.checked : Boolean(control.value);
      control.closest('label').hidden = control.closest('label').dataset.available !== 'true' && !active;
      if (active) {
        if (control.selectedOptions) control.selectedOptions[0].hidden = false;
      }
    }
    document.querySelector('.context-filters').hidden = [...document.querySelectorAll('.context-filters > label')].every(label => label.hidden);
    // Selection, sorting and grouping depend only on the controls, the records and review marks:
    // page changes and re-renders reuse them.
    const options = selectionOptions();
    const selectionKey = JSON.stringify([options, controls.review.value, controls['group-by'].value, reviewsVersion]);
    if (!selectionMemo || selectionMemo.records !== contracts || selectionMemo.profile !== activeProfile || selectionMemo.key !== selectionKey) {
      const pool = activeProfile ? contracts.filter(c => activeProfile.ids.has(c.id)) : contracts;
      const filtered = koreaNationwide ? (datasetSelect.value === 'global'
        ? [...new Set(contracts.map(c => c.collectionId))].flatMap(key => selectContracts(contracts.filter(c => c.collectionId === key), { sort: options.sort }))
        : selectContracts(contracts, { sort: options.sort })) : selectContracts(controls.review.value ? pool.filter(reviewMatch) : pool, options);
      selectionMemo = { records: contracts, profile: activeProfile, key: selectionKey, arrangement: arrangeGroups(filtered, controls['group-by'].value) };
    }
    const arrangement = selectionMemo.arrangement;
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
      row.append(dateCell, element('td', c.buyer), supplierCell);
      const objectCell = element('td');
      const button = element('button', c.description, 'row-toggle');
      button.type = 'button';
      button.setAttribute('aria-expanded', String(openId === c.id));
      button.setAttribute('aria-controls', 'detail-panel');
      button.title = `${c.description} — open details, evidence and sources`;
      objectCell.append(button, element('small', c.buyer, 'mobile-buyer'));
      if (c.collectionLabel) objectCell.append(element('small', `Collection: ${c.collectionLabel} · source record ${c.originalId}`, 'collection-context'));
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
      if (c.procedureGroup) objectCell.append(element('small', `${c.procedureGroup.kind === 'lots' ? `Lot ${c.lotId || '—'} of` : 'Shares identifier'} ${c.procedureGroup.contractId || c.contractId} · ${c.procedureGroup.members.length} contracts`, 'provenance'));
      if (c.offersConflict) objectCell.append(element('small', 'Offer counts disagree between buyer declarations', 'provenance'));
      if (c.possibleDuplicateOf?.length) objectCell.append(element('small', 'May be the same contract as another record', 'provenance'));
      if (c.verification?.status === 'sources-disagree') objectCell.append(element('small', 'Sources disagree on the amount', 'provenance'));
      else if (c.verification?.addedFromFeed) objectCell.append(element('small', c.feedSource?.startsWith('portal_') ? 'From the buyer’s open-data list only · not in DECP' : 'From the buyer’s feed only · not in the Ministry dataset', 'provenance'));
      const legalContext = getLegalContext(c);
      if (legalContext.length) objectCell.append(element('small', `Context · ${[...new Set(legalContext.map(item => item.article))].join(', ')} cited`, 'provenance'));
      if (c.initialConflicts?.length || c.identityAmbiguous) objectCell.append(element('small', 'Ambiguous identifier / versions · calculations excluded', 'provenance'));
      if (c.modificationConflicts?.length) objectCell.append(element('small', 'Conflicting modification versions', 'provenance'));
      if (c.officialFinding === true) objectCell.append(element('small', 'Official audit finding · not a conviction', 'provenance tone-official'));
      if (hasReportedInvestigation(c)) objectCell.append(element('small', 'Investigation reported at the time · current status unknown', 'provenance'));
      if (hasAdjudicatedCorruption(c)) objectCell.append(element('small', 'Final judgment linked to this contract', 'provenance'));
      for (const x of getSupplierProceedings(c, usingLocalFile ? null : supplierProceedings)) {
        const badge = element('small', `Supplier · ${PROCEEDING_STAGES[x.stage]} (${x.eventDate.slice(0, 4)}) · about the company, not this contract`, 'provenance tone-proceeding');
        const info = element('span', 'i', 'info-tip');
        info.tabIndex = 0; info.title = supplierProceedingNote(x); info.setAttribute('role', 'img'); info.setAttribute('aria-label', info.title);
        badge.append(info);
        objectCell.append(badge);
      }
      const sector = getSector(c);
      const sectorCell = element('td', sector.label);
      sectorCell.append(element('small', c.cpv || 'unknown CPV', 'provenance'));
      row.append(objectCell, sectorCell, amountCell(c), element('td', c.offers ?? '—', 'numeric'));
      const badges = element('td');
      // Every signal is shown, heaviest first. Within a family only the
      // heaviest counts; the others are marked as not added to the index.
      const counted = new Set();
      const ordered = [...indicators].sort((a, b) => b.weight - a.weight);
      for (const indicator of ordered) {
        const counts = !counted.has(indicator.family);
        counted.add(indicator.family);
        const familyName = indicator.family === 'execution' ? 'execution/duration' : indicator.family;
        const badge = element('span', KIND_SHORT[indicator.kind] || indicator.kindLabel, `badge severity-${indicator.severity}${counts ? '' : ' not-counted'}`);
        badge.title = `${indicator.label} (this jurisdiction's check). Raw weight ${indicator.weight} (${BASIS_NOTE[indicator.basis]}). ${counts ? `Counts for the ${familyName} family.` : `Not added: a heavier ${familyName} signal already counts.`} ${indicator.explanation}`;
        badges.append(badge);
      }
      for (const label of contextLabels(c)) {
        const badge = element('span', `Context: ${label.short}`, 'badge context');
        badge.title = label.long;
        badges.append(badge);
      }
      if (ordered.length) objectCell.append(element('small', `Signals: ${ordered.map(i => i.kindLabel).join(' · ')}`, 'mobile-signals'));
      for (const label of contextLabels(c)) objectCell.append(element('small', `Context: ${label.short}`, 'mobile-signals context'));
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
    if (previewing) {
      status.textContent = `Top ${pageRows.length} of ${previewTotal} records by index. Loading the full dataset to filter, sort and open records…`;
      pagination.hidden = true;
      copyPage.disabled = exportCsv.disabled = exportJson.disabled = true;
      return;
    }
    if (koreaNationwide) {
      pagination.hidden = true;
      koreaScanStatus.textContent = koreaScanMessage;
      koreaScanNext.disabled = !koreaScanResult?.hasMore || Boolean(koreaScanController);
      koreaScanPrevious.disabled = !koreaScanResult || koreaScanPage === 0 || Boolean(koreaScanController);
      document.querySelector('#korea-scan-cancel').disabled = !koreaScanController;
      status.textContent = koreaScanMessage;
      document.querySelector('#completeness').textContent = 'Static scan: counts, sorting, grouping, copy and exports cover only the displayed scan page. Published collection/record order determines membership. Sorting is within each collection, never a cross-country risk or currency ranking. Collections may overlap; records are not unique contracts. No combined amount totals.';
    }
    writeView();
  }

  // Side panel with everything known about one record, organised for review.
  function detailSection(id, title) {
    const section = element('section', null, 'detail-section');
    section.id = `detail-${id}`;
    section.append(element('h3', title, 'section-title'));
    return section;
  }
  // Prozorro document links: published in each tender record, stored per tender (tools/build-prozorro-documents.py),
  // loaded only when a record opens. Opening a link is the reader's own click; the site fetches no document.
  const PROZORRO_DOCS = 'https://public-docs.prozorro.gov.ua/get/';
  const documentShards = new Map();
  function prozorroDocuments(c, base) {
    const box = element('section', null, 'detail-documents');
    box.id = 'detail-documents';
    const top = element('p', null, 'documents-head');
    top.append(element('strong', 'Documents'));
    if (safeSource(c.portalUrl)) top.append(' · ', sourceLink(c.portalUrl, 'Prozorro page'));
    const status = element('span', ' · loading…', 'muted');
    top.append(status);
    box.append(top);
    const shard = c.procedureId.slice(0, 2);
    if (!documentShards.has(base + shard)) documentShards.set(base + shard, fetch(`${base}${shard}.json`).then(r => r.ok ? r.json() : Promise.reject(new Error(r.status))));
    const link = ([title, url]) => sourceLink(url.startsWith('https://') ? url : PROZORRO_DOCS + url, title);
    const group = (label, docs, open) => {
      if (!docs?.length) return;
      const row = element('div', null, 'doc-group');
      const shown = docs.length > 6 && !open ? docs.slice(0, 5) : docs;
      row.append(element('span', `${label} (${docs.length})`, 'doc-label'), ' ');
      shown.forEach((d, i) => row.append(i ? ' · ' : '', link(d)));
      if (shown.length < docs.length) {
        const more = element('details', null, 'doc-more');
        more.append(element('summary', `+${docs.length - shown.length} more`));
        docs.slice(shown.length).forEach((d, i) => more.append(i ? ' · ' : '', link(d)));
        row.append(' ', more);
      }
      box.append(row);
    };
    documentShards.get(base + shard).then(all => {
      const e = all[c.procedureId];
      if (!e) { status.textContent = ' · none listed'; return; }
      status.textContent = ` · links as of ${e.asOf}`;
      const award = e.a[c.awardId];
      const sameLot = a => (a.l || null) === (c.lotId || null);
      group('Award decision', award?.d, true);
      group('Winner’s offer', award?.b);
      Object.values(e.a).filter(a => a !== award && a.s === 'unsuccessful' && sameLot(a))
        .forEach(a => group(`Rejected: ${a.n || 'bidder'}`, a.d, true));
      group('Tender documents', e.t);
      if (box.childElementCount === 1) status.textContent = ` · none published (as of ${e.asOf})`;
    }).catch(() => { status.textContent = ' · could not load the document list'; });
    return box;
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
    if (c.collectionLabel) head.append(element('p', `Collection: ${c.collectionLabel} · source record ${c.originalId}. Assessment uses this source’s rules; not a cross-country ranking.`, 'collection-context'));
    const facts = element('dl', null, 'detail-facts');
    const fact = (label, ...values) => {
      if (!values.length || values[0] == null || values[0] === '') return;
      const box = element('div'); box.append(element('dt', label));
      const dd = element('dd'); dd.append(...values); box.append(dd); facts.append(box);
    };
    const profileButton = role => {
      if (koreaNationwide) return []; // A page is not a complete buyer/supplier profile.
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
    // Individuals (supplierIndividual) are shown as published, marked so; only exports leave them out.
    const individual = !names.length && Array.isArray(c.supplierIndividual) && Array.isArray(c.supplierNamesPublished) ? c.supplierIndividual : null;
    if (individual?.some(Boolean)) c.supplierNamesPublished.forEach((name, i) => {
      if (i) supplier.append(' / ');
      supplier.append(String(name));
      if (individual[i]) supplier.append(' ', element('small', 'individual', 'muted'));
    });
    else supplier.append(supplierName);
    const supplierIdText = ids.map(s => { const shown = displayIdentifier(s); return s.siren && !shown.includes(s.siren) ? `${shown} · SIREN ${s.siren}` : shown; }).join(' / ');
    if (supplierIdText && (names.length || !supplierIdText.includes(supplierName))) supplier.append(element('small', ` ${supplierIdText}`, 'muted'));
    const joint = jointOfferNote(c);
    if (joint) supplier.append(element('small', joint, 'provenance'));
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
    if (c.offersConflict) fact('Offers', c.offersConflict.feed ? `unknown — DECP ${c.offersConflict.decp ?? '—'}, buyer feed ${c.offersConflict.feed.join(' / ')}` : `unknown — DECP ${c.offersConflict.decp ?? '—'}, notice ${c.offersConflict.notice ?? '—'}`);
    else if (!c.noticeEvidence || offers != null) fact('Offers', offers == null ? '—' : String(offers));
    const procedureKind = NATIONAL_FAMILIES[c.dataFamily] ? (c.procedureDirect === true ? 'without competition' : c.procedureDirect === false ? 'competitive' : 'not classified') : null;
    fact('Procedure', [c.procedure || '—', c.procedureCode].filter(Boolean).join(' · '), ...(procedureKind ? [' · ', element('span', procedureKind)] : []));
    if (c.durationMonths != null || c.durationOriginal) fact('Duration', ...(c.durationMonths != null ? [`${c.durationMonths} `, element('span', 'months')] : [c.durationOriginal]));
    fact('Index', scoreChip(c));
    head.append(facts);
    const documentsBase = datasets[datasetSelect.value]?.documents;
    if (documentsBase && c.dataFamily === 'prozorro' && /^[a-f0-9]{2}/.test(c.procedureId || '')) head.append(prozorroDocuments(c, documentsBase));
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
    const manageNotes = element('button', 'Manage notes', 'link-button');
    manageNotes.type = 'button';
    manageNotes.id = 'manage-notes';
    manageNotes.addEventListener('click', () => document.querySelector('#notes-dialog').showModal());
    head.append(manageNotes);

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
        item.append(name, element('span', ` · ${signal.weight} pts, ${BASIS_NOTE[signal.basis]}`, 'muted'), ...(counts ? [] : [element('span', ' · not added (same family)', 'muted')]), element('p', briefReason(signal.explanation)));
        triggered.append(item);
      }
      why.append(triggered);
    } else if (!assessment.excludedReason) line(why, breakdown.score == null ? 'Not assessed: no check could be evaluated.' : 'No threshold crossed in the evaluated checks.');
    if (breakdown.score != null) {
      const parts = Object.entries(breakdown.families).filter(([, v]) => v > 0);
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
        (c.initialAlternatives || []).forEach((a, n) => list.append(element('li', `Variant ${n + 1}: ${a.amount == null ? 'amount unknown' : moneyFor(c).format(a.amount)}${c.cohortId === CITIES_COHORT ? ` · notified ${a.date || '—'} · ${a.procedure || '—'} · offers ${a.offers ?? '—'}` : ''}`)));
        record.append(list);
      }
      if (c.procedureGroup) {
        const g = c.procedureGroup;
        record.append(element('h4', g.kind === 'lots' ? `Lots of procedure ${g.contractId || c.contractId} (${g.members.length})` : `Contracts sharing identifier ${g.contractId || c.contractId} (${g.members.length})`));
        const reference = [g.lotTitle, g.contractReference ? `contract ref. ${g.contractReference}` : null].filter(Boolean).join(' · ');
        if (reference) line(record, reference);
        line(record, g.basis);
        const list = element('ul', null, 'sibling-list');
        for (const id of g.members) {
          const sibling = contracts.find(x => x.id === id);
          const subject = sibling && !sibling.lotId && sibling.description.length > 70 ? `${sibling.description.slice(0, 69)}…` : sibling?.description;
          const label = sibling ? `${sibling.lotId ? `Lot ${sibling.lotId}` : subject} · ${sibling.date || '—'} · ${sibling.amount == null ? 'amount unknown' : moneyFor(sibling).format(sibling.amount)} · offers ${sibling.offers ?? (sibling.offersConflict ? 'disputed' : '—')}${c.possibleDuplicateOf?.includes(id) ? ' · possibly the same contract' : ''}` : id;
          const item = element('li');
          if (id === c.id || !sibling) item.append(element('span', `${label}${id === c.id ? ' (this record)' : ''}`));
          else { const open = element('button', label, 'group-link'); open.type = 'button'; open.addEventListener('click', () => openDetail(id)); item.append(open); }
          list.append(item);
        }
        record.append(list);
        if (c.project) { const all = element('button', `Show the whole project (${c.project.title})`, 'group-link'); all.type = 'button'; all.addEventListener('click', () => showProject(c.project.id)); record.append(all); }
      }
      if (c.verification) {
        const v = c.verification;
        record.append(element('h4', `Amount sources · ${VERIFICATION_STATUSES[v.status]}`));
        const list = element('ul');
        for (const src of c.amountSources || []) {
          const value = src.amount == null ? 'no amount' : moneyFor(c).format(src.amount);
          list.append(element('li', `${src.label}: ${value}${src.amount != null && src.amount > 0 && src.amount <= 10 ? ' (placeholder, not used)' : ''}${src.id && src.id !== c.contractId ? ` · id ${src.id}` : ''}${src.consolidatorFlag ? ` · flagged “${src.consolidatorFlag}” by the consolidator` : ''}`));
        }
        record.append(list);
        [
          v.status === 'sources-disagree' ? `The sources disagree, so the full range is shown. For sorting, ${c.amount == null ? 'no single amount is used' : `${moneyFor(c).format(c.amount)} is used`}, by a fixed rule (the buyer’s own feed first, positive amounts over zero); it is not a resolution. Amount-based checks only count when every source leads to the same conclusion.` : null,
          v.holdersAddedFromFeed ? 'Some co-holders come from the buyer’s feed: the Ministry table lists at most three holders per contract.' : null,
          ...(c.unconfirmedHolders || []).map(h => `Holder ${h.id} is listed only by the Ministry dataset and is not counted: the award notice and the buyer’s feed name only the confirmed holder.`),
          v.majority ? `${v.majority.routes} of ${v.majority.of} publication routes give ${moneyFor(c).format(v.majority.amount)}. Every route is the buyer’s own declaration, so this is corroboration, not proof.` : null,
          v.status === 'single-source' ? (c.feedSource?.startsWith('portal_') ? 'Listed in the buyer’s open-data list of concluded contracts but absent from the DECP publications: not confirmed by a second source.' : v.addedFromFeed ? 'Published in the buyer’s own feed but absent from the Ministry dataset: not confirmed by a second source.' : 'Only the Ministry dataset publishes this contract: not confirmed by a second source.') : null,
          v.status === 'sources-agree' ? 'The Ministry dataset and the buyer’s own feed publish the same amount. Agreement between publications is not proof the amount is right.' : null,
          v.status === 'notice-checked' ? 'Amount, date and holder matched against the award notice (see the lots above).' : null,
          v.resolvedPair ? 'The Ministry dataset published two amounts for this contract; the buyer’s feed confirms one of them.' : null,
        ].filter(Boolean).forEach(text => line(record, text));
      }
      if (c.possibleDuplicateOf?.length) line(record, `May be the same contract as ${c.possibleDuplicateOf.length} other record(s) above: same holder, subject, notification date and framework, but a different declared amount or detail. Scored on its own; counted once in this buyer’s baselines (usual publication delay, repeated single offers, supplier concentration).`);
      if (c.offersConflict && !c.offersConflict.feed) line(record, `Offer count disputed: DECP ${c.offersConflict.decp ?? '—'}, notice ${c.offersConflict.noticeId} ${c.offersConflict.notice ?? '—'}${c.offersConflict.contractReference ? ` (contract ref. ${c.offersConflict.contractReference})` : ''}. Both are declarations by the same buyer; the count is treated as unknown.`);
      if (c.offersConflict?.feed) line(record, `Offer count disputed: Ministry dataset ${c.offersConflict.decp ?? '—'}, buyer feed ${c.offersConflict.feed.join(' / ')}. Both are declarations by the same buyer; the count is treated as unknown.`);
      if (c.modificationConflicts?.length) line(record, `Conflicting modifications: ${c.modificationConflicts.map(m => `${m.id} (${m.fields.join(', ')})`).join('; ')}.`);
      if (c.history?.length > 1) {
        const table = element('table', null, 'history-table');
        const thead = element('thead'); const heading = element('tr');
        for (const label of ['Event', 'Notified', 'Published', 'Amount']) { const th = element('th', label); th.scope = 'col'; heading.append(th); }
        thead.append(heading);
        const rows = element('tbody');
        for (const event of c.history) {
          const tr = element('tr');
          tr.append(element('td', event.kind === 'initial' ? 'Initial' : `Change ${event.id || '—'}`), element('td', event.date || '—'), element('td', event.publicationDate || '—'), element('td', event.amount == null ? '—' : moneyFor(c).format(event.amount)));
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
    const outside = detailSection('context', 'Context');
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
    for (const x of getSupplierProceedings(c, usingLocalFile ? null : supplierProceedings)) {
      line(outside, `Supplier ${x.supplier} · ${PROCEEDING_STAGES[x.stage]} by ${x.authority} (${x.eventDate}): ${x.wording} `, element('span', `${PROCEEDING_CAVEATS[x.stage]} `), element('span', `${PROCEEDING_SCOPE} `),
        element('span', `Published ${x.publishedAt}; checked ${x.verifiedAt}. `), sourceLink(x.sourceUrl, 'Source'), ...(x.copyUrl ? [' · ', sourceLink(x.copyUrl, 'Copy')] : []));
    }
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
      if (r.status === 'signal' && r.weight != null) item.append(' · ', element('span', `${r.weight} pts, ${BASIS_NOTE[r.basis]}`));
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
    if (!usingLocalFile && ['boamp', 'decp'].includes(c.dataFamily)) {
      const belongs = l => c.dataFamily === 'boamp' ? l.boampId === c.id && l.boampUrl === c.source : l.decpId === c.id && l.decpUrl === c.source;
      const crossLinks = (publicLinkResolutions?.activePairs || boampDecpLinks).filter(belongs);
      const dismissed = (publicLinkResolutions?.dismissedPairs || []).filter(belongs);
      if (crossLinks.length || dismissed.length) {
        verify.append(element('h3', 'Cross-source evidence · BOAMP ↔ DECP'));
        if (!publicLinkResolutions) {
          const pending = element('p', 'Heuristic candidates only: reviewed dispositions are unavailable or still loading. Some leads may have been dismissed. ', 'muted');
          const history = element('a', 'Review decision log'); history.href = 'research/link-corrections-log.md';
          pending.append(history); verify.append(pending);
        }
        const list = element('ul', null, 'verify-links');
        for (const l of crossLinks) {
          const isBoamp = c.dataFamily === 'boamp';
          const target = isBoamp ? 'DECP' : 'BOAMP';
          const item = element('li');
          const label = l.status === 'candidate' ? `Unconfirmed candidate only — ${target} official source` : `Confirmed exact identifiers — ${target} official source`;
          item.append(sourceLink(isBoamp ? l.decpUrl : l.boampUrl, label), ` · ${isBoamp ? l.decpId : l.boampId}`);
          if (l.status === 'candidate') item.append(' · Same buyer, holder SIRET and date; not proof of the same contract.');
          else item.append(` · ${l.basis.includes('buyer-published-contract-reference') ? 'Exact buyer + published contract reference.' : 'Exact buyer + notice + lot.'}`);
          const warnings = l.activeWarnings || l.warnings;
          if (warnings.some(w => w.startsWith('multiple-'))) item.append(' · Ambiguous: multiple possible records; none selected.');
          if (warnings.includes('different-cpv')) item.append(' · Warning: differing CPVs.');
          const review = publicLinkEvidence.find(p => p.boampId === l.boampId && p.decpId === l.decpId);
          if (review) {
            item.append(element('p', publicLinkEvidenceLabel(review)),
              element('p', `Published notice reference: ${review.publishedReference} · DECP contract ID: ${review.decpContractId}`, 'muted'),
              element('p', review.notes, 'muted'));
          }
          const noticeId = l.boampId.match(/^boamp-(\d{2}-\d+)-/)?.[1];
          const ted = publicLinkResolutions?.tedNotices.find(n => n.boampNoticeId === noticeId);
          if (ted) {
            const p = element('p');
            p.append(sourceLink(ted.url, ted.status === 'verified-notice-version' ? `TED — same notice/version ${ted.version} verified` : 'TED award locator — XML version unverified'),
              ' · Notice verification only; DECP contract linkage remains unconfirmed.');
            if (ted.httpStatus === '429') p.append(' XML returned HTTP 429; not retried.');
            item.append(p);
          }
          list.append(item);
        }
        verify.append(list, element('p', 'External official source links only. No dataset switch, field replacement or scoring effect.', 'muted'));
        if (dismissed.length) {
          verify.append(element('h4', 'Dismissed investigation leads'));
          const history = element('ul', null, 'verify-links');
          for (const l of dismissed) {
            const item = element('li');
            item.append(sourceLink(c.dataFamily === 'boamp' ? l.decpUrl : l.boampUrl, 'Dismissed pairing — audit source'),
              element('p', l.reason, 'muted'));
            history.append(item);
          }
          verify.append(history, element('p', 'Dismissal corrects a candidate mapping, not proof of a different legal contract. No replacement link is confirmed.', 'muted'));
        }
        if (publicLinkResolutions) {
          const audit = element('p');
          const log = element('a', 'Correction history'); log.href = 'research/link-corrections-log.md';
          const resolutions = element('a', 'Link resolutions (JSON)'); resolutions.href = 'data/public-link-resolutions.json';
          audit.append(log, ' · ', resolutions); verify.append(audit);
        }
        if (publicLinkEvidence.length) {
          const audit = element('p');
          const ledger = element('a', 'Public evidence ledger (JSON)'); ledger.href = 'data/public-link-evidence.json';
          const method = element('a', 'Reproduce this review'); method.href = 'docs/public-evidence.md';
          audit.append(ledger, ' · ', method); verify.append(audit);
        }
      }
    }
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
    if (previewing) return;
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
    if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey || document.querySelector('dialog[open]')) return;
    const typing = event.target.closest?.('input, select, textarea, [contenteditable="true"]');
    if (event.key === 'Escape' && openId && (!typing || detailPanel.contains(event.target))) { closeDetail(); return; }
    if (typing) return;
    if (event.key === '/') { event.preventDefault(); controls.search.focus(); }
    else if (openId && event.key === 'j') { event.preventDefault(); stepDetail(1); }
    else if (openId && event.key === 'k') { event.preventDefault(); stepDetail(-1); }
  });

  function accept(data, prepared = null) {
    if (usingLocalFile && koreaNationwide) {
      cancelKoreaScan('Local file loaded.');
      koreaNationwide = false;
      koreaScanPanel.hidden = true;
      koreaPicker.hidden = true;
    }
    if (previewing) setPreviewLock(false);
    contracts = prepared || prepareContracts(data);
    assessmentCache = new WeakMap();
    const sectors = [...new Map(contracts.map(c => { const s = getSector(c); return [s.code, s]; })).values()].sort((a, b) => a.code === 'unknown' ? 1 : b.code === 'unknown' ? -1 : a.label.localeCompare(b.label, 'en'));
    fillSelect(controls.sector, [['', 'All sectors'], ...(koreaNationwide ? [...Object.entries(CPV_SECTORS), ['unknown', 'Sector not specified']] : sectors.map(s => [s.code, `${s.code === 'unknown' ? '' : s.code + ' · '}${s.label}`]))]);
    projectCatalog = new Map(contracts.filter(c => c.project).map(c => [c.project.id, c.project]));
    fillSelect(controls.project, [['', 'All records'], ...(projectCatalog.size || koreaNationwide ? [['@documented', 'Documented projects only']] : []), ...[...projectCatalog.values()].map(p => [p.id, p.title])]);
    controls.project.disabled = !koreaNationwide && projectCatalog.size === 0;
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
    // A declared 0 is not a missing value (it often means undisclosed): counted apart.
    const zeroAmounts = contracts.filter(c => c.amount === 0).length;
    document.querySelector('#completeness').textContent = `Missing values: ${missing('amount')} amounts, ${missing('offers')} offer counts, ${contracts.filter(c => c.durationMonths == null && !c.durationOriginal).length} durations (${contracts.length} records).${zeroAmounts ? ` Amounts declared as 0: ${zeroAmounts}.` : ''}`;
    render();
    if (pendingOpen) openDetail(pendingOpen, { focus: false });
    pendingOpen = '';
  }
  function fail(error) {
    if (previewing) setPreviewLock(false);
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
  // Search: a paste, a cleared field or the first keystroke after a pause filters at once;
  // fast typing, one character at a time, is filtered once it stops.
  let searchTimer = 0, lastSearchInput = -Infinity, lastSearchValue = '';
  function searchInput() {
    if (koreaNationwide) { clearTimeout(searchTimer); refresh(); return; }
    const now = performance.now(), value = controls.search.value;
    const typed = Math.abs(value.length - lastSearchValue.length) === 1 && (value.startsWith(lastSearchValue) || lastSearchValue.startsWith(value));
    const immediate = !typed || now - lastSearchInput > 150;
    lastSearchInput = now; lastSearchValue = value;
    clearTimeout(searchTimer);
    if (immediate) refresh(); else searchTimer = setTimeout(refresh, 150);
  }
  Object.values(controls).forEach(control => control.addEventListener('input', control === controls.search ? searchInput : refresh));
  // Column headers sort too: first click descending (newest, largest, most), second ascending.
  // They drive the Sort control, so the link, page reset and export stay in step.
  const SORT_PAIRS = { date: ['date', 'date-asc'], publication: ['publication', 'publication-asc'], amount: ['amount', 'amount-asc'], indicators: ['indicators', 'indicators-asc'], score: ['score', 'score-asc'], buyer: ['buyer', 'buyer-desc'], supplier: ['supplier', 'supplier-desc'], sector: ['sector', 'sector-desc'], offers: ['offers-desc', 'offers'], increase: ['increase'], official: ['official'], 'recent-signal': ['recent-signal'] };
  const sortField = document.querySelector('#sort-field');
  const sortDirection = document.querySelector('#sort-direction');
  function syncSortControl() {
    const field = Object.keys(SORT_PAIRS).find(key => SORT_PAIRS[key].includes(controls.sort.value)) || 'score';
    sortField.value = field;
    sortField.querySelector('[value="recent-signal"]').hidden = field !== 'recent-signal';
    const pair = SORT_PAIRS[field];
    const ascending = ['buyer', 'supplier', 'sector'].includes(field) ? controls.sort.value === pair[0] : controls.sort.value === pair[1];
    sortDirection.disabled = pair.length === 1;
    sortDirection.textContent = ascending ? '↑' : '↓';
    sortDirection.setAttribute('aria-label', ascending ? 'Sort ascending' : 'Sort descending');
    sortDirection.title = pair.length === 1 ? 'Fixed sort direction' : ascending ? 'Sort ascending · click for descending' : 'Sort descending · click for ascending';
  }
  sortField.addEventListener('change', () => {
    controls.sort.value = SORT_PAIRS[sortField.value][0];
    controls.sort.dispatchEvent(new Event('input'));
  });
  sortDirection.addEventListener('click', () => {
    const pair = SORT_PAIRS[sortField.value];
    if (pair.length < 2) return;
    controls.sort.value = controls.sort.value === pair[0] ? pair[1] : pair[0];
    controls.sort.dispatchEvent(new Event('input'));
  });
  const sortHeaders = [...document.querySelectorAll('th[data-sort-key]')];
  function syncSortHeaders() {
    syncSortControl();
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
    const text = pageSummaryForCopy(pageRowsForCopy, { dataset: currentDatasetLabel + (koreaNationwide ? ` · static scan page ${koreaScanPage + 1} ONLY; counts and sorting are page-local` : ''),
      page: page + 1, totalPages: Math.max(1, Math.ceil(totalResultsForCopy / pageSize)), totalResults: totalResultsForCopy });
    copyStatus.textContent = await copyText(text) ? `${copiedCount} record summaries copied with source links.` : 'Unable to copy. Serve over localhost or select the rows manually.';
    const original = 'Copy page';
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
  const exportName = extension => `contract-signals-${usingLocalFile ? 'local-file' : datasetSelect.value}${koreaNationwide ? '-scan-page-' + (koreaScanPage + 1) : ''}-${new Date().toISOString().slice(0, 10)}.${extension}`;
  exportCsv.addEventListener('click', () => {
    if (!loaded || !rowsForExport.length) return;
    download(exportName('csv'), 'text/csv;charset=utf-8', '﻿' + rowsToCsv(rowsForExport));
    copyStatus.textContent = `${rowsForExport.length} ${koreaNationwide ? 'scan-page records (not nationwide totals)' : 'filtered records'} exported as CSV.`;
  });
  exportJson.addEventListener('click', () => {
    if (!loaded || !rowsForExport.length) return;
    download(exportName('json'), 'application/json', rowsToJson(rowsForExport, { dataset: currentDatasetLabel + (koreaNationwide ? ` · scan page ${koreaScanPage + 1} ONLY; published-order membership, page-local sorting; not a nationwide export` : ''), view: viewStateToHash(currentView()), exportedAt: new Date().toISOString() }));
    copyStatus.textContent = `${rowsForExport.length} ${koreaNationwide ? 'scan-page records (not nationwide totals)' : 'filtered records'} exported as JSON.`;
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
  const importDialog = document.querySelector('#import-dialog');
  const notesDialog = document.querySelector('#notes-dialog');
  document.querySelector('#open-import').addEventListener('click', () => importDialog.showModal());
  document.querySelector('#import-close').addEventListener('click', () => importDialog.close());
  document.querySelector('#notes-close').addEventListener('click', () => notesDialog.close());
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
      importStatus.textContent = `${preview.records.length} records loaded locally.`;
      importDialog.close();
    } catch (error) { importStatus.textContent = `Unable to load: ${error.message}`; }
    if (version === importVersion) confirmImport.disabled = false;
  });
  async function loadDataset() {
    datasetSelection.sync();
    const selected = datasets[datasetSelect.value];
    invalidateImport();
    cancelKoreaScan('Ready to scan.');
    koreaNationwide = false;
    koreaScanPanel.hidden = true;
    const version = ++loadVersion;
    activeProfile = null;
    loaded = false;
    closeDetail({ restoreFocus: false });
    usingLocalFile = false;
    currentDatasetLabel = datasetLabel();
    copyStatus.textContent = '';
    copyPage.textContent = 'Copy page';
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
    document.querySelector('#file-path').textContent = selected.remote ? `${KOREA_BASE}/` : [].concat(selected.path).join(' + ');
    document.querySelector('#file').value = '';
    fileHelp.hidden = location.protocol !== 'file:';
    controls.search.value = '';
    clearFilters();
    projectPanel.hidden = true;
    projectPanel.replaceChildren();
    viewport.scrollTop = 0;
    status.textContent = 'Loading data…';
    if (FRENCH_LINK_DATASETS.has(datasetSelect.value)) loadLinkEvidence();
    if (previewing) setPreviewLock(false);
    koreaPicker.hidden = !selected.remote;
    if (pendingView?.['korea-buyer'] != null && selected.remote) koreaBuyer = pendingView['korea-buyer'];
    if (selected.remote === 'global') {
      koreaPicker.hidden = true;
      koreaNationwide = true;
      koreaScanPanel.hidden = false;
      document.querySelector('#coverage-link').hidden = true;
      accept([]);
      startKoreaScan();
      return;
    }
    if (selected.remote === 'korea') {
      try { await loadKorea(version); } catch (error) { if (version === loadVersion) fail(error); }
      return;
    }
    showFirstPage(datasetSelect.value, version);
    try {
      const data = await fetchRecords(datasetSelect.value, selected.path);
      if (version === loadVersion) accept(data);
    } catch (error) { if (version === loadVersion) fail(error); }
  }
  // Only for the default view: index order, 50 rows, no filter, search or open record.
  function showFirstPage(key, version) {
    if (!globalThis.firstPageFile || !globalThis.DATASET_FILES?.[key] || location.protocol === 'file:' || parsedFiles.has(globalThis.DATASET_FILES?.[key]?.[0])) return;
    const view = pendingView ? viewStateToHash(pendingView) : '';
    const extra = new URLSearchParams(view.replace(/^#/, '')); extra.delete('dataset');
    if ([...extra.keys()].length || /[#&]open=/.test(location.hash) || controls.sort.value !== 'score' || pageSize !== 50) return;
    const file = globalThis.firstPageFile(key);
    (globalThis.takeDataset?.(file) || fetch(file).then(response => {
      if (!response.ok) throw new Error(`${file}: HTTP ${response.status}`);
      return response.json();
    })).then(first => {
      if (version !== loadVersion || loaded || first?.dataset !== key || !Array.isArray(first.rows)) return;
      previewTotal = first.total;
      setPreviewLock(true);
      contracts = first.rows;
      assessmentCache = new WeakMap();
      loaded = true;
      page = 0;
      render();
    }).catch(() => { /* The full dataset still loads. */ });
  }
  // A dataset may span several files (one per import); they are loaded as one list of records.
  // The browser copies (prefetch.js, data/web/) are used when present; the first request may
  // already be in flight from prefetch.js. Parsed files are kept, so returning to a dataset
  // does not download it again.
  const parsedFiles = new Map();
  function fetchRecords(key, path) {
    const files = globalThis.DATASET_FILES?.[key] || [].concat(path);
    return Promise.all(files.map(file => {
      if (!parsedFiles.has(file)) {
        const request = globalThis.takeDataset?.(file) || fetch(file).then(response => {
          if (!response.ok) throw new Error(`${file}: HTTP ${response.status}`);
          return response.json();
        });
        parsedFiles.set(file, request);
        request.catch(() => parsedFiles.delete(file));
      }
      return parsedFiles.get(file);
    })).then(parts => parts.flat());
  }
  // A pasted link or back/forward: reload only when the dataset differs.
  window.addEventListener('hashchange', () => {
    const view = hashToViewState(location.hash);
    const wanted = Object.hasOwn(datasets, view.dataset) ? view.dataset : usingLocalFile ? null : defaultDataset;
    if (wanted && (wanted !== datasetSelect.value || usingLocalFile || (wanted === 'korea' && (view['korea-buyer'] || '') !== koreaBuyer))) {
      datasetSelection.selectDataset(wanted);
      pendingView = view;
      loadDataset();
    } else if (previewing) {
      pendingView = view;
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
  // BOAMP↔DECP link evidence is shown only in French record panels: fetched with the first French dataset.
  function loadLinkEvidence() {
    if (linkEvidenceStarted) return;
    linkEvidenceStarted = true;
    fetch('data/boamp-decp-links.json').then(response => {
      if (!response.ok) throw new Error('Optional cross-source evidence unavailable');
      return response.json();
    }).then(data => {
      boampDecpLinks = validateBoampDecpLinks(data);
      const refresh = () => {
        if (openId && !usingLocalFile) {
          const record = contracts.find(c => c.id === openId);
          if (record) renderDetail(record);
        }
      };
      refresh();
      fetch('data/public-link-evidence.json').then(response => {
        if (!response.ok) throw new Error('Optional public evidence unavailable');
        return response.json();
      }).then(ledger => {
        publicLinkEvidence = validatePublicLinkEvidence(ledger, data);
        refresh();
      }).catch(() => { /* Missing, stale or invalid review does not suppress base candidate links. */ });
      fetch('data/public-link-resolutions.json').then(response => {
        if (!response.ok) throw new Error('Optional reviewed resolutions unavailable');
        return response.json();
      }).then(resolutions => {
        publicLinkResolutions = validatePublicLinkResolutions(resolutions, data);
        refresh();
      }).catch(() => { /* Stale or invalid dispositions cannot silently dismiss a lead. */ });
    }).catch(() => { /* Missing or invalid optional evidence must not block the explorer. */ });
  }
  loadDataset();
}

if (typeof document !== 'undefined') startExplorer();
