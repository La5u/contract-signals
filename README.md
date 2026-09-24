# Contract signals

A static explorer for published public-procurement records from France, Colombia and Paraguay. It flags contract characteristics that may deserve a closer look, such as awards without competition, single offers, repeated awards to the same supplier, or long durations. Every row links to its source and shows which checks could or could not be evaluated.

**A signal prompts a review. It is not an accusation.** A zero or missing label does not mean a contract is clean, and “Not assessed” is never zero.

## Use it

Open the published site, or run it locally from this folder:

```sh
python -m http.server 8000   # then open http://localhost:8000
```

You can also open `index.html` directly. If the browser blocks loading the data under `file://`, open the matching file from `data/` with the file picker.

- **Private by design:** no backend, account, cookies, analytics or uploads. All data is loaded from this site and processed in your browser.
- **Share a view:** search, filters, sort, page and page size are kept in the link after `#`. Browsers never send that part to a server. To point someone to one contract, search its ID and share the link.
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
| Colombia · MEN / Caldas / Usaquén — SECOP II contracts 2024–2026 | 7,560 | Colombian checks |
| Paraguay · Fernando de la Mora — DNCP OCDS | 84 | not assessed (no approved local method) |

Each dataset is a bounded cohort chosen before scoring. None of them is exhaustive or representative. Datasets are never merged, and amounts are never converted between currencies or summed across sources. For suppliers with a French SIREN, the explorer shows the **current** public name from the company register, not the name at the contract date. Companies with restricted register listings are not named. Provenance and gaps are in each `data/*-coverage.json`, and licences in [docs/data-sources.md](docs/data-sources.md).

## The vigilance index

`index = min(100, max(competition checks) + max(execution/duration checks))`: eight checks, each shown as *signal*, *evaluated*, *not assessable* or *out of scope*. Amounts, legal citations, company names and official findings never add points. Correlated signals in the same family are not summed. Thresholds are editorial choices, not calibrated probabilities. Colombia uses its own thresholds, and nothing is compared across countries.

- French method: [docs/score-v3.md](docs/score-v3.md)
- Colombian method: [docs/score-colombia.md](docs/score-colombia.md)
- Court outcomes and reported investigations (kept outside the index): [docs/adjudicated-outcomes.md](docs/adjudicated-outcomes.md)
- Paraguay pilot and other candidate countries: [docs/paraguay-pilot.md](docs/paraguay-pilot.md), [docs/international-pilots.md](docs/international-pilots.md)
- Dated history of every delivery, count and design decision: [docs/project-journal.md](docs/project-journal.md)

## Development

Plain HTML, CSS and JavaScript: no framework, build step, dependency or runtime API call. Importers under `tools/` use the Python standard library and keep raw source snapshots under `data/*/raw/`.

```sh
node tests/scoring-v3.cjs && node tests/score-review.cjs && node tests/rules.cjs
node tests/cities.cjs && node tests/tours.cjs && node tests/colombia.cjs && node tests/paraguay.cjs
node tests/outcomes.cjs && node tests/page-copy.cjs && node tests/view-export.cjs
python -m unittest discover -s tests -p 'test_*.py'
node tests/browser.cjs   # starts its own server on a free port (or PORT); needs Playwright, see below
```

Playwright is used only for tests and is installed outside the project: `npm install --prefix /tmp/procurement-browser playwright`. Set `PLAYWRIGHT_PATH` to use another location. After any change to `script.js`, run `node tools/review-score-v3.cjs` so the review report matches the new script hash. `python tools/enrich-suppliers.py` refreshes the supplier names (`--offline` re-applies the saved snapshot without network access).

## Licence

Code and documentation: [MIT](LICENSE). The data keeps its source licences; see [docs/data-sources.md](docs/data-sources.md).
