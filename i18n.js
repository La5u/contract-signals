// Interface translation (Spanish, French). No build step, no network: dictionaries are
// plain scripts (i18n-es.js, i18n-fr.js) loaded before this file.
//
// Only interface text is translated: a text node is replaced when it matches an English
// interface string exactly, or a full-sentence pattern whose {slots} capture data values.
// Captured values stay as published (a slot is translated only if it is itself interface
// text), so source evidence — descriptions, justifications, names — is never altered.
(function () {
  const dicts = (typeof window !== 'undefined' && window.I18N_DICTS) || {};
  const NAMES = { en: 'English', es: 'Español', fr: 'Français' };
  const LOCALES = { en: 'en-IE', es: 'es-ES', fr: 'fr-FR' };
  const known = code => typeof code === 'string' && Object.hasOwn(NAMES, code);

  function chooseLanguage() {
    try {
      const fromQuery = new URLSearchParams(location.search).get('lang');
      if (known(fromQuery)) return fromQuery;
    } catch { /* no location */ }
    try {
      const saved = localStorage.getItem('contract-signals-lang');
      if (known(saved)) return saved;
    } catch { /* storage unavailable */ }
    for (const tag of (typeof navigator !== 'undefined' && navigator.languages) || []) {
      const base = String(tag).slice(0, 2).toLowerCase();
      if (known(base)) return base;
    }
    return 'en';
  }

  const lang = chooseLanguage();
  window.i18nLang = () => lang;
  window.i18nLocale = () => LOCALES[lang];
  window.I18N_LANGUAGES = NAMES;

  const norm = text => text.replace(/\s+/g, ' ').trim();
  const dict = lang === 'en' ? null : dicts[lang];
  const exact = new Map();
  const patterns = [];
  if (dict) {
    for (const [en, tr] of Object.entries(dict.exact || {})) exact.set(norm(en), tr);
    for (const [en, tr] of dict.patterns || []) {
      const slots = [];
      const source = norm(en).split(/(\{[a-z0-9]+\})/).map(part => {
        const slot = /^\{([a-z0-9]+)\}$/.exec(part);
        if (slot) { slots.push(slot[1]); return '([\\s\\S]+?)'; }
        return part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      }).join('');
      const literal = norm(en).split(/\{[a-z0-9]+\}/).sort((a, b) => b.length - a.length)[0];
      patterns.push({ re: new RegExp(`^${source}$`), slots, target: tr, literal, fixed: norm(en).replace(/\{[a-z0-9]+\}/g, '').length });
    }
    // More specific first: “Context: {a} · no points” must win over “Context: {a}”.
    patterns.sort((a, b) => b.fixed - a.fixed);
  }

  // A captured value is translated only when it is itself interface text (or a " · " list of
  // interface texts); anything else is data and stays exactly as published.
  function slotValue(value) {
    const key = norm(value);
    if (exact.has(key)) return exact.get(key);
    const parts = key.split(' · ');
    if (parts.length > 1 && parts.every(part => exact.has(part))) return parts.map(part => exact.get(part)).join(' · ');
    return value;
  }
  function translate(text) {
    if (!dict) return null;
    const key = norm(text);
    if (!key) return null;
    const lead = /^\s*/.exec(text)[0], trail = /\s*$/.exec(text)[0];
    if (exact.has(key)) return lead + exact.get(key) + trail;
    for (const p of patterns) {
      if (p.literal && !key.includes(p.literal)) continue;
      const m = p.re.exec(key);
      if (!m) continue;
      const values = Object.fromEntries(p.slots.map((slot, i) => [slot, slotValue(m[i + 1])]));
      return lead + p.target.replace(/\{([a-z0-9]+)\}/g, (_, slot) => values[slot] ?? '') + trail;
    }
    return null;
  }
  window.i18nTranslate = text => translate(text) ?? text;

  const SKIP = new Set(['SCRIPT', 'STYLE', 'CODE', 'BLOCKQUOTE', 'TEXTAREA']);
  const ATTRIBUTES = ['placeholder', 'title', 'aria-label'];
  const done = new WeakSet();
  function translateTree(root) {
    if (!dict || !root) return;
    if (root.nodeType === Node.TEXT_NODE) return translateText(root);
    if (root.nodeType !== Node.ELEMENT_NODE || SKIP.has(root.tagName) || root.closest?.('[data-no-i18n]')) return;
    for (const name of ATTRIBUTES) {
      const value = root.getAttribute(name);
      const tr = value && translate(value);
      if (tr && tr !== value) root.setAttribute(name, tr);
    }
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
      acceptNode: n => n.nodeType === Node.ELEMENT_NODE && (SKIP.has(n.tagName) || n.hasAttribute('data-no-i18n')) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      if (n.nodeType === Node.TEXT_NODE) translateText(n);
      else for (const name of ATTRIBUTES) {
        const value = n.getAttribute(name);
        const tr = value && translate(value);
        if (tr && tr !== value) n.setAttribute(name, tr);
      }
    }
  }
  function translateText(node) {
    if (done.has(node) || SKIP.has(node.parentElement?.tagName) || node.parentElement?.closest('[data-no-i18n]')) return;
    const tr = translate(node.nodeValue);
    done.add(node);
    if (tr != null && tr !== node.nodeValue) node.nodeValue = tr;
  }

  function mountSelector() {
    const select = document.querySelector('#lang');
    if (!select) return;
    for (const [code, name] of Object.entries(NAMES)) {
      const option = document.createElement('option');
      option.value = code;
      option.textContent = name;
      option.setAttribute('data-no-i18n', '');
      select.append(option);
    }
    select.value = lang;
    select.addEventListener('change', () => {
      try { localStorage.setItem('contract-signals-lang', select.value); } catch { /* storage unavailable */ }
      const url = new URL(location.href);
      if (select.value === 'en') url.searchParams.delete('lang'); else url.searchParams.set('lang', select.value);
      location.href = url.toString();
    });
  }

  if (typeof document === 'undefined') return;
  document.documentElement.lang = lang;
  const start = () => {
    mountSelector();
    if (!dict) return;
    translateTree(document.body);
    if (dict.title) document.title = dict.title;
    new MutationObserver(records => {
      for (const r of records) {
        if (r.type === 'characterData') { done.delete(r.target); translateText(r.target); }
        for (const n of r.addedNodes) translateTree(n);
      }
    }).observe(document.body, { childList: true, subtree: true, characterData: true });
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
