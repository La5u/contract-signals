# Romanian SEAP data audit (2026-10-15)

After the multi-sheet error (about 400,000 contracts of 2021–2023 missed), every normalised SEAP file was audited for silent loss (row counts at export caps, key fields mostly empty, duplicate files, cross-file overlaps). Found and fixed in `tools/normalize-romania-seap.py`:

| Problem | Files | Fix |
| --- | --- | --- |
| Only the first sheet of old-format XLS read | 2021 Q2, 2022 Q3–Q4, 2023 Q1–Q2 (up to 4 sheets) | read every sheet, skip repeated headers |
| `|`-delimited CSV parsed as comma-delimited (key fields 100 % empty) | 2023 Q3, Q4 (371,679 rows) | `|` added to delimiter detection |
| Unquoted line breaks inside fields split records | 2017–2018 subsequent contracts | join lines until a record has the header's field count (fragments: 350,000 → 60,000 real records) |
| Unquoted commas inside free-text fields | 2016 (85,000 rows) | anchor-based row repair: 98 % repaired, 1 % dropped and counted |
| Header variants (typos, title row above header), Excel serial dates | 2022 Q4, 2023 Q1–Q2 | aliases, header detection, date conversion |
| Duplicate file | 2019 Q3 is a copy of Q2 | excluded; **real Q3 2019 is not published there** (gap) |
| Same contracts in several quarterly files | 2021–2023 | de-duplicated when loaded (buyer, contract number, award notice, winner, value, date) |
| 2024: only Q1 downloaded | 2024 | to fetch |

The normaliser now prints a warning when a file's row count equals a known export cap or a key field is empty in more than 20 % of rows. Colombian downloads were checked for pages at the 50,000-row limit: none.

Romanian results after the fixes (weighted, one procedure per decision, 15 buyers): buyer share LR 1.68 [0.95, 2.74], supplier dependence 2.15 [1.08, 4.26]; both still pass the decision rule narrowly.
