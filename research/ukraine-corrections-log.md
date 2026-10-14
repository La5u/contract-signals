# Ukraine accuracy corrections and safeguards
11 October 2026. Preserve source declarations and historical plans. This methodological audit is not expert validation; no normalized data or scoring changes were applied.

## 1. Omitted amendment list was silently counted as zero

`tools/import-prozorro.py:minimized_changes` uses `contract.get('changes', [])`, merging absent and empty arrays into zero. The old summary lacks full module hashes, linking fields and field-presence states. In `data/ukraine-amendment-evidence.json`, six exactly linked sampled modules omit `changes` and were recorded as `unavailable`, with null counts and `changes:absent-no-schema-default-assumed`; six contain nonempty arrays. No empty array was observed.
**Resolved:** omission means no changes. Publisher source [ProzorroUKR/openprocurement.api](https://github.com/ProzorroUKR/openprocurement.api), commit `4dfb3a4d9e81f430dae2f22add9751159840e26f` (default branch, 9 October 2026), establishes:

- `src/openprocurement/contracting/core/procedure/models/contract.py:156`: optional `changes = ListType(ModelType(Change, required=True))`, no default.
- `src/openprocurement/contracting/core/procedure/views/change.py:43-44`: creates the list on the first posted change.
- `src/openprocurement/api/procedure/serializers/base.py:75-78`: omits `None` and empty lists. The contract blacklist does not hide `changes`; `opt_fields` affects only listings/feeds, and rationale masking preserves the key.
All **542 cached tenders** contain no empty lists and only three null text fields; sampled modules also omit some `documents` and `milestones`. Both pending and active changes appear in lists, supporting the importer's active-only count. The six omissions are zero, and all **12 sampled counts agree** with the snapshot. The **469 stored zeros** are methodologically sound for retrieved modules, without individual re-verification. Current API code was checked; the pre-2023 standalone `openprocurement.contracting.api` stack was not, but all cohort modules were fetched from the current API.
Keep the raw evidence unchanged because two frozen document plans bind its bytes. `data/ukraine-amendment-counts.json` records the corrected interpretation (`activeChangeCount: 0`, basis `omitted-field-publisher-omits-empty-lists`), evidence hash and source lines. Verify with `python tools/interpret-ukraine-amendments.py`; regenerate with `--write`. Null or malformed values remain unknown. Preserve field states, exact module links, retrieval time, response hash, change IDs/statuses/dates and unknown categories; verify publisher rules before interpreting omission as zero.

## 2. All 11 financial differences could not be described as explained basis differences

`data/ukraine-amount-basis-evidence.json` supports **seven** explicit contract-net/award-amount equalities, with matching currency, contract VAT true and award VAT false. **Four amount differences and fourteen VAT-only differences remain unresolved.** Eleven fresh HTTP-200 responses retain cached financial scalars. Keep normalized contract amounts; do not substitute awards/net values or infer tax rates. Equality, later dates and cached zero amendment counts do not establish payment, amendment causality or signed-contract correctness. Distinguish basis, presence, currency and VAT.

## 3. A narrow host policy was mistaken for a document-access blocker

v1 rejected published URLs on `public-api.prozorro.gov.ua` because its allowlist admitted only two document-service hosts. This was a local policy error. Retained v1; `data/ukraine-amendment-document-plan-v2.json` keeps the same two document IDs/order/URL hashes and admits their exact official API paths. In `data/ukraine-amendment-document-evidence-v2.json`, document `38728a86391e4a36b8a3eee93fe3cb86` returned **302**, not followed; `6c896cc6a2b64954a0100a2c6347a019` was not attempted. Zero captured bytes describe unread redirect bytes, not an empty server body. Document contents and legal/financial basis remain unknown. Distinguish policy restrictions, redirects, extraction tools, refusals, oversize and absence; check the optional environment before claiming a PDF library is unavailable everywhere.

## 4. Current pagination cannot certify historical completeness

`data/ukraine-discovery-evidence.json` reports **506**, page size **20**, and **20/6/0** rows on pages **25/26/27**: no current 500 cap observed. The date-filter probe returned **6**, versus **134** historical creation-window IDs; equivalence remains unverified. Historical completeness is unknown; all **16** buyer-association mismatches remain excluded. Future fixed-window collection needs page evidence, stable totals, exact date semantics, beyond-total controls and primary-record buyer checks.

## 5. Signature-before-tender-ID dates are lifecycle observations, not proven errors

Three sampled signatures precede their tender-ID dates. All are reporting procedures, where signing can precede report creation. The ID date is not an established legal procedure-start or signature deadline; do not create an illegality flag or date correction.

The five flagged/seven zero-score rows are not reviewed positive/negative outcomes. Three active changes support the amendment threshold, not three increases or unlawful amendments. Minimized hashes cannot authenticate withheld bodies. Payments, legal applicability and a representative accuracy rate remain unknown.

## 6. Captcha pages were recorded as "no date shown"

14 October 2026. The register Review-page reader (`finality` in `tools/sweep-ukraine-verdicts.py` and `tools/link-ukraine-verdict-tenders.py`) wrote `no date shown` for any page containing the word "реєстр". All **84** such pages in the cache, and all 36 pages of a recheck that day, were captcha pages: no Review page of these verdicts was actually read. The **251** `entry_into_force` values in the published verdict label files now read `not read: the register page answered with a captcha`. **No label or finality class changes**: only an entry-into-force date counts as finality evidence, and these verdicts rest on the presumed rule or the appeal decisions in the export, as before. The reader (`page_state`) now records `no date shown` only when the page carries the field without a date, and stops at a captcha (no bypass).
