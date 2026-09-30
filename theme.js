// Apply the saved colour theme before the first paint; the choice stays in this browser.
try { const t = localStorage.getItem('contract-signals-theme'); if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t; } catch (_) { /* Storage blocked: follow the system theme. */ }
