// Starts the record download for the dataset in the link while the other scripts load.
// script.js reuses these requests (takeDataset); it falls back to its own fetch if missing.
// Files are the browser copies: data/web/ omits archival fields the explorer never reads
// (tools/build-web-data.py).
(function () {
  const files = {
    tours: ['data/tours-notices.json'],
    consultations: ['data/consultations.json'],
    decp: ['data/web/decp-history.json', 'data/web/decp-cities.json'],
    boamp: ['data/contracts.json'],
    colombia: ['data/web/colombia-secop2.json'],
    paraguay: ['data/paraguay-dncp.json'],
    paraguay3: ['data/paraguay-dncp-3buyers.json'],
    ukraine: ['data/prozorro.json'],
    chile: ['data/chile-mp.json'],
    uk: ['data/uk-fts.json'],
    portugal: ['data/ted-portugal.json'],
    czechia: ['data/ted-czechia.json'],
    romania: ['data/ted-romania.json'],
  };
  // Interface language, decided once here (i18n.js uses it): only that dictionary is loaded.
  // Same order as i18n.js: ?lang=, the saved choice, then the browser's languages.
  const LANGS = ['en', 'es', 'fr'];
  let lang = 'en';
  try {
    const query = new URLSearchParams(location.search).get('lang');
    let saved = null;
    try { saved = localStorage.getItem('contract-signals-lang'); } catch { /* storage unavailable */ }
    lang = [query, saved].find(code => LANGS.includes(code)) ||
      [...(navigator.languages || [])].map(tag => String(tag).slice(0, 2).toLowerCase()).find(code => LANGS.includes(code)) || 'en';
  } catch { /* no location */ }
  window.I18N_BOOT_LANG = lang;
  // A parser-inserted deferred script keeps its place before i18n.js.
  if (lang !== 'en' && document.readyState === 'loading') document.write(`<script src="i18n-${lang}.js" defer></script>`);
  const aliases = { cities: 'decp', all: 'decp' };
  const started = new Map();
  window.DATASET_FILES = files;
  // The default view's first page, prepared ahead (tools/build-first-pages.cjs): shown while the
  // full dataset downloads.
  window.firstPageFile = key => `data/web/first/${key}.json`;
  // Returns the early request for a file once; later loads fetch again (fresh state).
  window.takeDataset = file => { const p = started.get(file); started.delete(file); return p; };
  if (location.protocol === 'file:') return;
  let key = '', params = new URLSearchParams();
  try { params = new URLSearchParams(location.hash.replace(/^#/, '')); key = params.get('dataset') || ''; } catch { /* no hash */ }
  key = aliases[key] || key || 'decp';
  const get = file => {
    const request = fetch(file).then(response => {
      if (!response.ok) throw new Error(`${file}: HTTP ${response.status}`);
      return response.json();
    });
    request.catch(() => {}); // reported when script.js awaits it
    started.set(file, request);
  };
  params.delete('dataset');
  if (files[key] && ![...params.keys()].length) get(window.firstPageFile(key));
  for (const file of files[key] || []) get(file);
})();
