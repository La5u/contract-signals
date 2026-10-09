# UK FTS contract multiplicity and value accuracy gate

## Scope and verdict

Read-only audit of **all 1,081 published rows** in `data/uk-fts.json` against
**all 516 saved release packages** in `data/uk-fts/raw/notices/`, performed on
2026-10-07. No sampling, network requests, importer execution, data rebuilds or
published-data changes. Existing user changes were left untouched.

**No concretely wrong amount/currency or date mapping was found within this
saved snapshot.** Every published row has exactly one linked contract, and all
1,081 amount/currency pairs and dates reproduce the existing importer rule.
There are **zero observed last-of-multiple selections**, **zero award-value
fallbacks**, and **zero identity-ambiguous rows**. These are measured results,
not evidence that the importer is safe on other releases.

The importer has two real **latent risks**: it silently retains the last
contract for a repeated `awardID`, and its award-value fallback is labelled as
contract value. Neither branch produced an observed wrong value here. Nine
rows have no amount/currency in either the linked contract or award; three
published dates are notice dates, not signature dates. These limitations must
not be turned into assurances of complete signed-contract-value/date accuracy.

## Exact identity method

`tools/audit-uk-contract-values.py` reads the manifest, published rows and every
saved `*.json.gz` notice package. It does not import or invoke the importer.

1. Index **every raw award** by `(release.id, award.id)`. Match each published
   row using its **full** `(noticeId, awardId)` pair. Require one raw candidate,
   one published row for that pair and one occurrence of the published row ID.
   Never select by a name, amount, array position, award suffix alone or date.
2. Check exact `procedureId == release.ocid`, the unique buyer-party ID,
   the single award supplier's ID against the row's `GB-FTS` supplier ID, and
   `lotId` against the award's sole related lot (or both absent). Check that the
   row ID equals the importer's full notice-plus-award-suffix construction;
   that construction is a consistency check, **not the join key**.
3. Recheck active status, exactly one supplier and at most one related lot.
   Check manifest/file completeness, release ID versus filename, duplicate
   award/contract IDs within releases, and contracts whose `awardID` is absent
   from that release's awards. Count eligible raw awards missing a published row.
4. Enumerate **all** contracts in the same release for which
   `contract.awardID == award.id`. This is a list, not a last-wins dictionary.
   Multiple linked contracts or ambiguous identity are gate exclusions—even
   if amounts/dates happen to agree. No sum, inferred allocation, "latest"
   contract selection or other resolution is attempted.
5. Separately reproduce the existing importer's selection rule for diagnosis:
   last linked contract, then `contract.value or award.value or {}` as a whole
   object; `dateSigned or award.date or release.date`, truncated to ten
   characters. Compare amount **and currency together**, and compare the date
   and publication date. Reproducing last-wins does not accept it as truth when
   multiple contracts exist. The helper records that case as excluded.

Names and contacts are neither matching evidence nor report output. Company
identifiers are not used to merge supplier accounts. This tests the published
FTS identity, not legal-entity identity or the factual accuracy of the notice.

## Full saved-source inventory

| Measure | Count |
| --- | ---: |
| Manifest notices / files present / raw releases | 516 / 516 / 516 |
| Missing manifest files / extra files / filename-ID mismatches | 0 / 0 / 0 |
| Raw awards / raw contracts | 1,233 / 1,086 |
| Raw awards with zero linked contracts | 147 |
| Raw awards with exactly one linked contract | 1,086 |
| Raw awards with two or more linked contracts | 0 |
| Orphan contracts / duplicate award IDs / duplicate contract IDs | 0 / 0 / 0 |
| Excluded inactive awards (first applicable reason) | 147 |
| Excluded multi-supplier awards (first applicable reason) | 5 |
| Excluded multi-lot awards after preceding checks | 0 |
| Eligible raw awards / published rows | 1,081 / 1,081 |
| Other-buyer releases / eligible awards without a published row | 0 / 0 |
| Duplicate published IDs / ambiguous or failed identity matches | 0 / 0 |

The five other singly linked contracts belong to excluded multi-supplier awards;
all 147 contract-less awards are inactive. Exclusions are ordered like the
importer, not overlapping counts of every condition.

## Published-row results

| Measure | Count |
| --- | ---: |
| Rows with exactly one linked contract | 1,081 |
| Rows with multiple linked contracts / excluded for ambiguity | 0 / 0 |
| Published amount/currency equals importer rule | 1,081 |
| Published date equals importer rule | 1,081 |
| Publication-date mismatches | 0 |
| Positive amounts from contract value | 1,072 |
| Missing amounts and currencies in both contract and award | 9 |
| Zero amounts / negative or other amount categories | 0 / 0 |
| Rows with nonempty award value objects | 0 |
| Amounts using award-value fallback | 0 |
| Signature-date source / award-date source / notice-date source | 1,078 / 0 / 3 |
| Rows with no published date | 0 |
| Contract-vs-award amount differences / currency conflicts | 0 / 0 |
| Partial contract value blocking an available award amount | 0 |
| Selected amount without currency / currency without amount | 0 / 0 |
| Award value incorrectly labelled contract basis | 0 |

**Important denominator:** no retained award has a nonempty value object, so
there are **zero comparable contract/award value pairs**. The zero conflict
counts do not establish agreement between those two bases; there is nothing to
compare. The 9 missing cases are absence, not declared zero and not importer
loss from an available award amount. They are not numeric-value-verified rows.

Published currencies are **GBP 1,064; EUR 3; USD 2; BGN 1; CHF 1; JPY 1;
missing 9**. Thus eight positive values are explicitly non-GBP. The helper
compares each against its own saved source currency; it does not convert, sum
across currencies or substitute GBP for absence. No currency mapping conflict
was observed.

All 1,081 rows carry the label:

> Contract value as published in the notice (GBP unless stated); not a payment,
> never converted.

For the 1,072 populated values the saved basis is indeed the linked contract's
value object. For nine rows the label is generic metadata with no value, not
proof that a contract value was published. The existing date note explicitly
allows award/notice-date fallback; the three notice dates are not mismatches,
but must not be represented as independently verified signature dates.

## Concrete errors versus latent importer risks

The relevant existing code is `tools/import-find-a-tender.py::notice_rows`:

- **Last-wins contract mapping:** `{c.get("awardID"): c for c in contracts}`
  discards earlier linked contracts before both amount and signature-date
  selection. A multi-contract award can silently publish one arbitrary
  contract's fields as the award row. **Observed affected rows: 0**, including
  across all raw awards. The audit helper excludes such rows instead of
  resolving them, even if the last contract reproduces the published values.
- **Basis mislabelling on fallback:** `contract.get("value") or
  award.get("value") or {}` can publish an award value under a fixed contract
  basis label. **Observed affected rows: 0**. No award fallback was exercised.
- **Whole-object, not fieldwise, fallback:** a truthy partial contract value
  (e.g. currency only) blocks an available award amount. A zero amount in a
  nonempty value object does not trigger fallback. **Observed affected rows:
  0**. Tests establish the behavior, not its frequency beyond this snapshot.
- **Real present limitations:** 9 missing values and 3 notice-date fallbacks.
  These are supported by the saved-source rule and are not demonstrated wrong
  mappings. No substitute amount/date was invented and no correction queue of
  positive recovery candidates is warranted by this audit.

**Gate decision:** no multiplicity/identity exclusion or source-mapping repair
is demonstrated for the current 1,081 rows. Keep the nine missing values out of
any numeric verification claim; retain currencies and date-source distinctions.
This is a narrow saved-source mapping pass, **not an overall data-quality,
legal-contract-value, payment, supplier-identity or procurement-truth pass**.
No importer change was made. Future inputs should be gated for unique exact
identity and unique linked contract before accepting a mapping, with explicit
amount-basis metadata if an award fallback is ever permitted.

## Reproduction, private evidence and validation

Aggregate-only run (reads inputs and prints JSON; writes no output files):

```sh
python tools/audit-uk-contract-values.py
python -m unittest discover -s tests -p 'test_audit_uk_contract_values.py' -v
```

Optional minimized private evidence, in a **new** directory:

```sh
python tools/audit-uk-contract-values.py \
  --private-dir "$HOME/.cache/contract-signals/accuracy-review/uk-contract-multiplicity-NEW"
```

The actual audit evidence is stored privately under
`~/.cache/contract-signals/accuracy-review/uk-contract-multiplicity-20261007/uk-contract-values.json`.
It enumerates all 1,086 raw contract-to-award links and all 1,081 matched rows'
linked contracts, source amount/currency and date fields, identity checks and
flags. It contains exact IDs but no names, contacts or narrative descriptions.
Directory/file modes are **0700/0600**; the helper exclusively creates the file
and refuses overwrite or repository output. This is evidence, not an automatic
correction queue. Public stdout/report contain no individual IDs or amounts.

**11 tests passed**, including the full saved-snapshot regression and synthetic
multiple-contract value/date conflicts, identical duplicate contracts (still
excluded), award fallback and label mismatch, no-contract fallback, partial
value blocking, empty object versus zero behavior, currency conflict, incorrect
published values, identity failures and missing-value/notice-date fallback.
Synthetic failures are not counted as observed published-data errors.

Input SHA-256 fingerprints:

- Published JSON: `edf5433d2e92685e4d07857e7f88f1e9c0bc11bce1d97e91bf4bfacc1a7b3ecf`
- Raw manifest: `1d5d13434031c765c1aa796ff7de42619d8d1497d0c19c035be62bf97b499b28`
- Raw notice files: `6132b17ad9987565dae64f37f1427dd673638ffcad769992b63dafd462848bf6`

The last fingerprint hashes, in sorted filename order, each UTF-8 filename,
a NUL byte and the binary SHA-256 digest of its saved compressed bytes. These
fingerprints pin the reviewed snapshot, not the current live service. No live
release, amendment, attachment, linked notice or independent contract evidence
was checked; historical release mappings need not describe current contracts.
