# UK FTS contract multiplicity and value accuracy gate

## Verdict

Offline audit on **2026-10-07** covered **all 1,081 published rows** in `data/uk-fts.json` and **all 516 saved packages** in `data/uk-fts/raw/notices/`.

**No wrong amount/currency or date mapping was found in this snapshot.** Each row has exactly one linked contract; all 1,081 pairs and dates reproduce the importer rule. Observed multiple-contract selections, award-value fallbacks and identity-ambiguous rows: **zero**.

Two latent importer risks remain: last-wins selection for repeated `awardID`, and award values labelled as contract values. Neither occurred here. **Nine** rows lack amount/currency; **three** dates come from notices, not signatures. The audit establishes saved-source mapping, not legal contract truth, payment or accuracy on future releases.

## Exact identity method

`tools/audit-uk-contract-values.py` reads the manifest, published rows and every saved `*.json.gz` package without invoking the importer.

1. Join by full **(release.id, award.id)** = **(noticeId, awardId)**. Require one raw candidate, one published pair and one occurrence of the row ID.
2. Check `procedureId == release.ocid`, unique buyer-party ID, the single award supplier's ID against the row's `GB-FTS` supplier ID, and sole related lot (or both absent). Importer's notice-plus-award-suffix row ID is a consistency check, not the join key.
3. Check active status, one supplier, at most one lot, manifest/file completeness, filename/release IDs, duplicate award/contract IDs, orphan contracts and eligible awards without published rows.
4. Enumerate **all** contracts with `contract.awardID == award.id` in the release. Multiple contracts or ambiguous identity exclude the row, even when fields agree; do not sum, allocate or choose “latest”.
5. Diagnose by reproducing last linked contract, then whole-object `contract.value or award.value or {}` and `dateSigned or award.date or release.date` truncated to ten characters. Compare amount **with currency**, date and publication date; reproducing last-wins does not approve it.

Names/contacts are not matching evidence or output. Supplier IDs do not merge accounts or establish legal-entity identity.

## Saved-source inventory

| Measure | Count |
|---|---:|
| Manifest notices / files / releases | 516 / 516 / 516 |
| Missing / extra files / filename-ID mismatches | 0 / 0 / 0 |
| Raw awards / contracts | 1,233 / 1,086 |
| Awards with zero / one / multiple linked contracts | 147 / 1,086 / 0 |
| Orphan contracts / duplicate award IDs / duplicate contract IDs | 0 / 0 / 0 |
| Excluded inactive / multi-supplier / multi-lot awards | 147 / 5 / 0 |
| Eligible awards / published rows | 1,081 / 1,081 |
| Other-buyer releases / eligible awards missing published rows | 0 / 0 |
| Duplicate published IDs / ambiguous or failed matches | 0 / 0 |

Exclusions use the importer's first applicable reason. All 147 contract-less awards are inactive; five singly linked contracts belong to excluded multi-supplier awards.

## Published results

| Measure | Count |
|---|---:|
| Unique linked contract / amount-currency matches / date matches | 1,081 / 1,081 / 1,081 |
| Multiple linked contracts / ambiguity exclusions / publication-date mismatches | 0 / 0 / 0 |
| Positive contract values / missing amount and currency | 1,072 / 9 |
| Zero / negative or other amounts | 0 / 0 |
| Nonempty award value objects / award-value fallbacks | 0 / 0 |
| Signature / award / notice date source | 1,078 / 0 / 3 |
| Rows without date | 0 |
| Contract-award amount differences / currency conflicts | 0 / 0 |
| Partial contract value blocking award amount | 0 |
| Amount without currency / currency without amount | 0 / 0 |
| Award value labelled contract basis | 0 |

**There are zero comparable contract/award value pairs:** no award has a nonempty value object. Zero conflicts therefore do not establish agreement. The nine missing cases are absence, not zero or importer loss of an available award amount, and are excluded from numeric verification.

Currencies: **GBP 1,064; EUR 3; USD 2; BGN 1; CHF 1; JPY 1; missing 9**. Eight positive values are non-GBP. Each was compared with its saved currency, without conversion or substituting GBP.

All rows carry “Contract value as published in the notice (GBP unless stated); not a payment, never converted.” The 1,072 populated values use contract value; for nine missing rows this is generic metadata. Existing date notes allow fallback, but the three notice dates are not verified signature dates.

## Importer risks and decision

In `tools/import-find-a-tender.py::notice_rows`:
- `{c.get("awardID"): c for c in contracts}` discards earlier linked contracts before amount/date selection. Multi-contract awards could publish arbitrary fields. Observed affected rows: **0** across all raw awards.
- `contract.get("value") or award.get("value") or {}` could label award value as contract value. Observed affected rows: **0**.
- Whole-object fallback means a truthy partial contract value blocks an available award amount; a nonempty zero-value object does not trigger fallback. Observed affected rows: **0**; synthetic tests establish behavior, not wider frequency.

**Decision:** no current multiplicity/identity exclusion or mapping repair is demonstrated. Keep nine missing values outside numeric claims and preserve currency/date-source distinctions. No importer change was made. Gate future inputs on unique identity and linked contract, with explicit basis metadata if award fallback is allowed.

## Reproduction and limits

```sh
python tools/audit-uk-contract-values.py
python -m unittest discover -s tests -p 'test_audit_uk_contract_values.py' -v
# Optional minimized evidence in a new private directory
python tools/audit-uk-contract-values.py \
  --private-dir "$HOME/.cache/contract-signals/accuracy-review/uk-contract-multiplicity-NEW"
```

Actual private evidence: `~/.cache/contract-signals/accuracy-review/uk-contract-multiplicity-20261007/uk-contract-values.json`. It lists **1,086** contract-award links and **1,081** matched rows' source fields/checks, without names, contacts or descriptions. Modes 0700/0600; exclusive creation refuses overwrite/repository output. Public output is aggregate-only. Snapshot fingerprints bind the reviewed files, not the live service.

**11 tests passed**, including saved-snapshot regression, multiple/duplicate contracts, fallback/basis mismatch, partial/empty/zero values, currency conflicts, wrong fields, identity failures and missing/notice-date cases. Synthetic errors are not observed dataset errors.

No live releases, amendments, attachments, linked notices or independent contracts were checked; historical mappings may not describe current contracts.
