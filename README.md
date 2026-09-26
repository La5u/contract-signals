# Contract signals

A static explorer for published public-procurement records from France, Chile, Colombia, Paraguay, Portugal, Romania, Ukraine and the United Kingdom. It flags contract characteristics that may deserve a closer look, such as awards without competition, single offers, repeated awards to the same supplier, or long durations. Every row links to its source and shows which checks could or could not be evaluated.

**A signal prompts a review. It is not an accusation.** A zero or missing label does not mean a contract is clean, and “Not assessed” is never zero.

## Use it

Open the published site, or run it locally from this folder:

```sh
python -m http.server 8000   # then open http://localhost:8000
```

You can also open `index.html` directly. If the browser blocks loading the data under `file://`, open the matching file from `data/` with the file picker.

- **Private by design:** no backend, account, cookies, analytics or uploads. All data is loaded from this site and processed in your browser.
- **Share a view:** search, filters, sort, page and page size are kept in the link after `#`. Click the Date, Declared amount, Indicators or Index heading to sort by it (click again to reverse). Browsers never send that part to a server. To point someone to one contract, search its ID and share the link.
- **Export:** *Export CSV* / *Export JSON* downloads every filtered record, not just the current page. An empty index means not assessed. *Copy page summary* copies the visible page as sourced notes.
- **Your own data:** *Open your own JSON file* reads a file locally and never uploads it. Format and scoring caveats: [docs/data-format.md](docs/data-format.md).

## Datasets

| Dataset | Records | Scoring |
| --- | ---: | --- |
| France · Paris & Ardèche — DECP contracts 2024–2025 | 2,594 | French v3 checks |
| France · six cities (Rennes, Nantes, Bordeaux, Grenoble, Dijon, Tours) — DECP 2024–2025 | 1,270 | French v3 checks |
| France · Tours — BOAMP/TED notices | 66 | documents, not assessed |
| France · 3 Feb 2025 — BOAMP consultation notices | 10 | documents, not assessed |
| France · nationwide BOAMP award sample + 8 CRC audit dossiers | 3,010 | French v3 checks; audit findings outside the index |
| Chile · MOP / Maule region / Puente Alto — Mercado Público licitaciones 2024–2026 | 522 | Chilean checks |
| Colombia · MEN / Caldas / Usaquén — SECOP II contracts 2024–2026 | 7,560 | Colombian checks |
| Paraguay · Fernando de la Mora — DNCP OCDS 2024–2025 | 84 | Paraguayan checks |
| Paraguay · MOPC / Central / Asunción — DNCP OCDS 2024–2026 | 293 | Paraguayan checks |
| Portugal · Infraestruturas de Portugal / CIM Cávado / Lisboa — TED award notices 2024–2026 | 493 | EU eForms checks |
| Romania · Ministry of Finance / Cluj county / Cluj-Napoca — TED award notices 2024–2026 | 356 | EU eForms checks |
| Ukraine · Ministry of Health / Vinnytsia region / Dnipro — Prozorro contracts 2024–2026 | 488 | Ukrainian checks |
| United Kingdom · FCDO / Lincolnshire / Milton Keynes — Find a Tender award notices 2024–2026 | 1,081 | UK checks |

Each dataset is a bounded cohort chosen before scoring. None of them is exhaustive or representative. Datasets are never merged, and amounts are never converted between currencies or summed across sources. For suppliers with a French SIREN, the explorer shows the **current** public name from the company register, not the name at the contract date. Companies with restricted register listings are not named. Provenance and gaps are in each `data/*-coverage.json`, and licences in [docs/data-sources.md](docs/data-sources.md).

**Check it yourself.** *Sources and how to verify*, above the table, gives each dataset's publisher, portal, API, licence, raw snapshot and rebuild command. Every row has a *Verify it yourself* section with the official pages and documents published for that contract (for Paraguay: the award page with tenderers and evaluation report, the call page, and the signed-contract PDFs), plus the identifiers to search on the portal if a link moves. Copied summaries and CSV/JSON exports carry the same links (`verifyUrls`).

## The vigilance index

`index = min(100, max(competition checks) + max(execution/duration checks))`: eight checks, each shown as *signal*, *evaluated*, *not assessable* or *out of scope*. Amounts, legal citations, company names and official findings never add points. Correlated signals in the same family are not summed. Thresholds are editorial choices, not calibrated probabilities. Colombia, Paraguay, Ukraine and the TED cohorts (Portugal, Romania) use their own checks, and nothing is compared across countries. TED holds only procedures above the EU thresholds, so the Portuguese and Romanian cohorts are not a picture of those countries' procurement.

- French method: [docs/score-v3.md](docs/score-v3.md)
- Colombian method: [docs/score-colombia.md](docs/score-colombia.md)
- Paraguayan method: [docs/score-paraguay.md](docs/score-paraguay.md)
- Ukrainian method: [docs/score-ukraine.md](docs/score-ukraine.md)
- Portugal and Romania (TED eForms) method: [docs/score-ted.md](docs/score-ted.md)
- Court outcomes and reported investigations (kept outside the index): [docs/adjudicated-outcomes.md](docs/adjudicated-outcomes.md)
- Paraguay pilot notes and other candidate countries: [docs/paraguay-pilot.md](docs/paraguay-pilot.md), [docs/international-pilots.md](docs/international-pilots.md)
- Dated history of every delivery, count and design decision: [docs/project-journal.md](docs/project-journal.md)

## Development

Plain HTML, CSS and JavaScript: no framework, build step, dependency or runtime API call. Importers under `tools/` use the Python standard library and keep raw source snapshots in `data/` (large ones gzipped, byte-exact).

```sh
sh tests/run-all.sh            # every suite; NO_BROWSER=1 skips the Chromium test
```

The browser test needs Playwright, installed outside the project: `npm install --prefix /tmp/procurement-browser playwright` (set `PLAYWRIGHT_PATH` for another location, `CHROMIUM_PATH` for another browser). GitHub Actions runs the same script on every push (`.github/workflows/tests.yml`). After any change to `script.js`, run `node tools/review-score-v3.cjs` so the review report matches the new script hash.

Every dataset can be rebuilt offline from its raw snapshot:

| Dataset | Rebuild |
| --- | --- |
| Paris & Ardèche DECP | `python tools/import-decp-paris-ardeche.py --offline` |
| Six cities DECP | `python tools/import-decp-cities.py --offline` |
| Tours notices | `python tools/import-tours-notices.py --offline` |
| 3 Feb 2025 consultations | `python tools/import-consultations.py --offline` |
| Nationwide BOAMP sample | `python tools/import-boamp-sample.py --offline` |
| Chile (Mercado Público) | `python tools/import-chilecompra.py --offline` |
| Colombia SECOP II | `python tools/import-colombia-secop2.py --offline` |
| Paraguay DNCP | `python tools/import-paraguay-dncp.py --cohort fernando\|3buyers --offline` |
| Portugal, Romania (TED) | `python tools/import-ted-cohorts.py --cohort portugal\|romania --offline` |
| Ukraine (Prozorro) | `python tools/import-prozorro.py --offline` |
| United Kingdom (Find a Tender) | `python tools/import-find-a-tender.py --offline` |

`--download` fetches a new snapshot instead; it is not a fixed archive (the DECP index, for instance, keeps only the latest modification of each contract). `python tools/enrich-suppliers.py` refreshes French supplier names and `python tools/fetch-dncp-sanctions.py` the Paraguayan sanction snapshot (`--offline` re-applies either).

## Hosting

Any static host works; all paths are relative. For Cloudflare Pages: no build command, output directory `/`. `_headers` sets a Content Security Policy that only allows the site's own files, plus `Referrer-Policy: no-referrer`. Keep Rocket Loader, Email Address Obfuscation and Web Analytics off: they rewrite pages or add scripts. The largest file, `data/colombia-secop2.json` (15.6 MB), is under Cloudflare Pages' 25 MiB per-file limit.

## Licence

Code and documentation: [MIT](LICENSE). The data keeps its source licences; see [docs/data-sources.md](docs/data-sources.md).
