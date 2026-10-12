# Ukraine accuracy corrections and safeguards

Dated 11 October 2026. Preserve source declarations and historical plans. This is an assistant-assisted methodological audit, not expert validation or proof that an underlying legal contract is wrong. No normalized data/scoring changes were applied.

## 1. Omitted amendment list was silently counted as zero

**Earlier method:** `tools/import-prozorro.py:minimized_changes` uses `contract.get('changes', [])`. A retrieved object without the field therefore becomes a stored integer zero, indistinguishable from an explicitly retrieved empty array. The full-cohort summary retained counts/types/dates/status, not original module body hashes, complete linking fields or field-presence state.

**New evidence:** In `data/ukraine-amendment-evidence.json`, six frozen sampled modules omit `changes`; all have exact `id`/`contractID`/`tender_id`/`awardID` matches. Their extract state is `unavailable`, with null counts and `changes:absent-no-schema-default-assumed`. The other six modules publish nonempty arrays; no sampled empty array was observed.

**Why the old interpretation is unsupported:** retrieval alone establishes neither an explicit empty list nor a schema default. Omission might legitimately serialize an empty list, but that rule/deployed applicability has not been validated. **This is not proof that those six contracts were amended or that all 469 old zero values are errors.** The new review does not silently rewrite them.

**Resolution (11 October 2026, public source code):** omission means no changes. Verified in the publisher's open-source API, [ProzorroUKR/openprocurement.api](https://github.com/ProzorroUKR/openprocurement.api) at commit `4dfb3a4d9e81f430dae2f22add9751159840e26f` (default branch, 9 October 2026):

- `src/openprocurement/contracting/core/procedure/models/contract.py:156`: `changes = ListType(ModelType(Change, required=True))`, an optional field with no default.
- `src/openprocurement/contracting/core/procedure/views/change.py:43-44`: the list is created only when the first change is posted (`if not contract.get("changes"): contract["changes"] = []`).
- `src/openprocurement/api/procedure/serializers/base.py:75-78`: the output serializer skips `None` and empty lists ("we don't show null in our outputs … and empty lists").
- The contract serializer hides only a fixed private-field blacklist (tokens, owner, revisions, config…), not `changes`. `opt_fields` filtering applies only to the listing/feed endpoint, and masking replaces change rationales without removing the key.

Observed data agrees. Across all **542** cached tender records, no list field anywhere is empty and the only nulls are three text fields. In the 12 sampled modules, `documents` and `milestones` are also omitted on some contracts, as `changes` is. Changes can be `pending` or `active` and both appear in the list, so the importer's active-only count (`minimized_changes`) is the correct reading.

**Disposition:** the six omitted lists are **zero changes**, and the importer's `contract.get('changes', [])` default matches publisher behaviour. The 469 stored zeros are methodologically sound for contracts whose module was retrieved; this does not re-verify each one. `data/ukraine-amendment-evidence.json` keeps its raw observation (`unavailable`, field absent) as recorded, because two frozen document plans pin its exact bytes. The corrected reading lives in `data/ukraine-amendment-counts.json`, built by `python tools/interpret-ukraine-amendments.py` (`--check` to verify). It binds the evidence hash and cited source lines, marks the six as `activeChangeCount: 0` with basis `omitted-field-publisher-omits-empty-lists`, and shows all 12 sampled counts agree with the stored snapshot. A null or malformed `changes` value would still stay unknown. Remaining caveat: verified against current code only. Contracts serialized by the pre-2023 standalone `openprocurement.contracting.api` stack were not inspected, but every module in this cohort was fetched from the current API.

**Safeguard:** preserve absent/null/malformed/empty/nonempty states; validate the publisher schema before using omission as known zero. Preserve exact module link fields, response hash, retrieval time, per-change IDs/statuses/date presence and unknown categories. Missing legal/financial explanation remains separate from count verification.

## 2. All 11 financial differences could not be described as explained basis differences

**Earlier wording:** the work queue/handoff broadly called the 11 contract/award differences distinct bases, not corrections. That was conservative about replacement, but did not establish an explanation for each difference.

**New evidence:** `data/ukraine-amount-basis-evidence.json` records full row bindings, source hashes and contract/award value pointers. **Seven** cases have explicit contract `amountNet` equal to award `amount`, matching currency, contract VAT true and award VAT false. **Four** amount differences have no established explanation. **Fourteen additional VAT-only differences** also remain unresolved. Eleven fresh HTTP-200 tender requests preserve the cached financial scalars.

**Disposition:** retain every normalized contract amount; record the seven explicit net-basis observations separately. Never substitute award/net values or infer a tax rate. Equality and later publication dates are not proof of payment, amendment causality or signed-contract correctness. The cached summary's zero counts are old source assertions, subject to item 1—not newly verified absence of amendments.

**Safeguard:** distinguish monetary basis, field presence, currency and VAT; prefer explicit `amountNet`/scope evidence over ratios. Preserve unexplained differences rather than labelling all as benign basis changes.

## 3. A narrow host policy was mistaken for a document-access blocker

**Initial v1 diagnostic:** supplementary document selection rejected the actual public API host because the allowlist admitted only two document-service hosts. The selected URLs were public publisher URLs on `public-api.prozorro.gov.ua`. This was our overly narrow policy, **not evidence that the publisher or PDFs were inaccessible**.

**Correction:** retained v1 unchanged and froze v2 (`data/ukraine-amendment-document-plan-v2.json`) with the same two document IDs/order/URL hashes. Permitted only their exact native official API paths, without hostname rewriting, signing or replacement selection.

**Observed v2 outcome:** first document `38728a86391e4a36b8a3eee93fe3cb86` returned **HTTP 302**, not followed; second document `6c896cc6a2b64954a0100a2c6347a019` was not attempted after the stop. See `data/ukraine-amendment-document-evidence-v2.json`. Captured zero bytes/hash describe unread redirect bytes, not a complete empty server response. No body facts or legal/financial basis were established.

**Safeguard:** distinguish a local allowlist restriction, missing local extraction tool, HTTP redirect, refusal, oversize and genuine absence. Admit exact official publisher endpoints through a new reviewed plan when warranted; never change URLs or follow redirects silently. Check the already-installed optional environment before claiming a PDF library is unavailable everywhere.

## 4. Current pagination cannot certify historical completeness

**Earlier concern:** Vinnytsia's historical all-time search total was exactly 500, suggesting a possible cap.

**New evidence:** five requests in `data/ukraine-discovery-evidence.json`: current total 506, page size 20, boundary pages 25/26/27 contain 20/6/0 rows. A current cap at 500 was not observed. The date-filter probe returned 6, not the historical creation-window list's 134; filter equivalence is unverified.

**Disposition:** historical completeness remains unknown, not certified or newly disproved. No census or cohort expansion. All 16 original buyer-association mismatches stay excluded.

**Safeguard:** retain page bodies/minimized IDs, page size, stable totals, exact date semantics and beyond-total controls when collecting a future fixed-window list; check actual buyer attribution on primary records.

## 5. Signature-before-tender-ID dates are lifecycle observations, not proven errors

Three sampled module signature dates precede the date embedded in their tender ID. They are reporting procedures: a contract can be signed before its procurement report is created. The ID date is not independently established as the legal procedure-start or signature deadline. Do not turn the audit's descriptive calendar comparison into an illegality flag or automatic date correction.

## Overall evidence limits

Frozen sample: five flagged/seven zero-score rows, not reviewed positive/negative outcomes. Three active changes corroborate the sole amendment threshold flag, **not three increases or unlawful amendments**. Public hashes/pointers support reproducibility of the minimized review, not remote authentication or reconstruction of withheld bodies. Primary-document contents, legal applicability, payments and a representative accuracy rate remain unknown.
