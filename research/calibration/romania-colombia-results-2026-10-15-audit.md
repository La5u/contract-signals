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

## Later on 2026-10-15: more decisions, value parsing, final run

- **Value parsing:** comma thousands separators (`1,478,296`) were read as decimals, so some 2024 values were 1,000 times too small; the 2017–2018 subsequent-contract files leave the RON value `NULL` and give it with its currency. Both fixed; all files re-normalised from scratch. The 2024 Q4 XLSX also continued on a second worksheet (now read). The 2022 Q1 file failed to parse after the `|` fix (delimiter and quote both `|`); fixed. 2023 Q4 has no signing date (publication date only): left unknown.
- **More decisions:** a full listing of the Council's decision sections (2,303 documents) gave 136 further cartel-infringement decisions; 18 concern procurement by their text (14 with text, 4 OCR'd), and a model review (not hand-checked) found 6 procurement cartels with 13 rigged procedures (118/2022, 127/2022, 225/2024, 128/2022, 58/2014, 49/2010). 118/2022 is under appeal (weight 0.91).

**Final Romanian result** (weighted by appeal outcome, one procedure per decision — the decision rule; 20 decisions linked, 17 buyers):

| Check | Rigged vs comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
| --- | --- | --- | --- | --- | --- |
| Buyer share ≥ 5 % | 45 % vs 19 % | 1.79 [1.07, 3.01] | 1.65 / 1.35 | 8.4 [1.0, 15.9] | **passes** |
| Supplier dependence ≥ 25 % | 41 % vs 13 % | 2.19 [1.16, 3.89] | 2.48 / 1.03 | 11.3 [2.1, 19.6] | **passes** (check half barely above 1) |
| Framework / subsequent | 38 % vs 25 % | 1.27 [0.73, 2.16] | | | fails |
| December signature | 18 % vs 10 % | 1.33 | | | fails |
| Concentration | 6 % vs 3 % | 1.09 | | | fails |
| Single offer | 20 % vs 30 % | 0.79 | | | fails |
| Repeated single offer / direct award | | 0.91 / 0.38 | | | fail |
| Direct award | 0 % vs 13 % | 0.38 | | | fails |

On all 75 linked procedures (31 buyers) buyer share is 1.95 [1.39, 2.99] and supplier dependence 2.09 [1.29, 3.54]. Nothing adopted; owner decision.
