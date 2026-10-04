# BASE battery-only technical review

Reviewed 2026-10-02 by the coding assistant. **Current result: the authorized bounded candidate check passed, with no obvious incidental disclosures found by the checks below. Not publication approval.** The initial recommendation to withhold pending candidate checks is followed by the completed check in section 6 below. The owner has not performed a technical review and is not represented as having done so. This is a software/provenance review, not independent factual verification or legal clearance.

## What was actually checked

- Read the existing private `coverage.json` and `manifest.json`, importer, name-reveal/search/export code and synthetic tests. Checked cache permissions: directory 0700, documents 0600.
- No read/scan/hash of the 9.8 MiB candidate, no archive scan/extraction, no dataset regeneration, no browser/full-suite run, no publication or push.
- Manifest records candidate SHA-256 `309b17f2882f3ac2e171c82b5ee13e2835333965b67c477528d7256d45ea6a13`. This is a **reported fingerprint**, not freshly verified against candidate bytes in this review.
- Coverage arithmetic reconciles: 655,235 national rows = 649,666 nonmatching + 273 unknown-buyer + 5,296 matching rows. Matching rows = 3,986 in-window + 1,310 outside. In-window = 3,983 normalized + 3 rejected; normalized = 3,966 retained + 17 duplicates. No conflicting variants reported.
- Retained rows by buyer: 503933813 → 1,515; 508779472 → 100; 500051070 → 2,351. These sum to 3,966. Rejections: two subject failures and one supplier-shape failure; these aggregates do not identify which subject failure was an email.
- There are 277 buyer-parse-error rows, including 273 with no selected buyer identified. Do not subtract all 277 again: it is an overlapping error count. Their scope cannot be established from this report. `completeness: unknown` is appropriate; a complete national scan is not a complete cohort.

## Findings and small fixes

1. **Exact one-word protected holder names could survive in subjects.** Fixed extraction to redact them with word boundaries, with a regression test. Existing multiword matching handles case/whitespace, not accent changes, abbreviations or punctuation variants. There is no claim that all incidental personal data is detected.
2. **Publication validation omitted extraction's email rejection.** Added the same email check and a negative synthetic test.
3. **Protected payload validation accepted malformed base64 and oversized data.** Added strict, canonical base64 and decoded-size checks, with negative tests. These cheap checks do not establish decoded UTF-8 validity, correct holder code or absence of a decoded name in subjects.
4. **Bulk collection remains possible.** Record IDs, scrambling parameters and payloads are public. PBKDF2 adds cost, not access control. Deterministic short codes permit guessed-name matching without paying that cost and can collide. Do not describe the method as preventing bulk collection or as anonymization. The absolute claim in the existing `script.js` comment is incorrect; runtime code was not changed in this battery session.
5. **Fingerprints are integrity checks, not proof of privacy compliance.** An altered candidate with recomputed fingerprints may replace protected labels with clear names or reintroduce a holder name in subject text; no supplier IDs remain to independently reconstruct classification. Publication must not rely on schema validation alone.
6. Documentation saying no prefix-based classification is used was stale. The implementation uses blank/prefix rules as conservative protection routing; a blank NIF can represent a foreign organization. The label must not assert that every protected holder is a natural person.

The existing candidate was not changed and has **not** been shown to contain these defects. Extraction-code fixes do not retroactively fix candidate bytes. Never delete/overwrite the private evidence to force a rebuild.

## Bounded official source recheck

Two single requests, 12-second timeouts, maximum 128 KiB each; no retries, downloads or contacts:

- `https://dados.gov.pt/api/1/datasets/licenses/`: HTTP 200, 2,567 bytes; SHA-256 `d362536f6d41889af244c0ef77902c1efe384bc7ce57e16c158d307b025b0777`. `other-pd` remains “Outra (Domínio Público)”, no terms URL. Not CC0.
- `https://www.base.gov.pt/Base4/pt/utilidades/politica-de-privacidade/`: HTTP 200, 95,555 bytes; SHA-256 `9ef0dbc1fc64c847b397020cf7f068867cb4dd0b8f51d43f1bc2be6c7baf6f16`. Still contains the dados.gov.pt reference, 2,000-record portal limit, DPO address and GDPR wording. This limited presence check does not establish field-specific reuse permission.

Currency, duration units, zero-price semantics and field-specific personal-data reuse remain unresolved. Preserve unknowns and browse/unverified status. No new legal mandate was established; no email was sent. Earlier source evidence remains in `data/portugal-base-rights.json`.

## Verification and next decision

Passed only the offline synthetic suites: 43 importer tests (0.604 s), 5 archive-inspection tests (0.002 s), plus `git diff --check`. Tests use fast PBKDF2 fixtures except one shared fixed vector. No full-suite/CI/browser claim.

At the initial stop point, modest candidate processing still required authorization. The owner subsequently authorized the check; results follow below. Any deeper processing remains subject to the battery restriction. Any transformation needs a new separately preserved candidate and fingerprint. A national rebuild and browser/full-suite work still require heavy-processing authorization. Publication needs a separate owner release decision; do not invent a human reviewer or claim the owner personally checked the data.

## 6. Authorized existing-candidate check (same day)

The owner then asked the assistant to check the candidate. This authorized modest processing of the existing minimized file, not archives, a rebuild, bulk name decoding or publication.

- Read 10,255,719 candidate bytes; its SHA-256 matches `309b17f2882f3ac2e171c82b5ee13e2835333965b67c477528d7256d45ea6a13`. Coverage SHA-256 matches `3e165884aba2a23c711cd58445a7a11cdcdf204a81d2d785985c7791f8e0de39`. Manifest and current plan/download fingerprints match. Strict candidate and coverage validation passes, including the newly added email/base64 checks.
- 3,966 rows; 615 protected holder entries, 475 distinct codes, 3,462 unprotected holder entries, six subjects with redaction markers. Holder entries are not distinct suppliers or verified natural-person counts.
- Subjects and published supplier display names: zero matches for email addresses, isolated nine-digit sequences, the tested formatted Portuguese phone pattern, or Portuguese IBAN pattern. These are heuristic pattern results, not exhaustive contact/identifier detection.
- Seven contact/identity-word and thirteen sensitive-context-word matches were separately reviewed in their 20 description fields. Nineteen were ordinary procurement/service wording; contract 14409417 concerned a sensitive service but disclosed no individual's sensitive information. No actual personal contact details or individual sensitive disclosures were identified in those descriptions. Supplier fields were not included in that manual description review.
- Five deterministically spaced protected payload samples decoded as valid UTF-8 and had matching stable codes; no exact or accent-folded complete sampled holder name occurred in its own subject. Only five were decoded, not all 615.
- A bounded cheap dictionary audit compared 1,526,660 whitespace-normalized subject phrases (up to 16 words, also edge-punctuation-trimmed) against all 475 protected codes, with **zero matches**. This uses the public code algorithm without PBKDF2 and confirms the guessed-name weakness is practical. It does not rule out abbreviations, different accents, internal punctuation variants, longer names, or personal names unrelated to holders.
- No names or subject quotations are retained in this report. No private file was modified; no public dataset was created; no archive/network/browser/full-suite work occurred during this follow-up.

**Interpretation:** the existing candidate passes the bounded integrity/structure checks and the tested privacy heuristics. There is no evidence from these checks that it needs a rebuild. This does not establish complete cohort coverage, lawful reuse of every field, validity of every decoded payload, or comprehensive absence of incidental personal information. Publication and the public reversible-name design remain separate release decisions. The assistant can perform further technical checks when processing is authorized; no technical certification is requested from the inexperienced owner.

## 7. AC-power full-suite verification

The owner then confirmed AC power and authorized the full tests. `sh tests/run-all.sh` passed every JS suite and all 136 Python tests (~38 seconds), but the browser step initially could not start because the temporary Playwright module was absent. Installed the documented test-only `playwright@1.58.2` under `/tmp/procurement-browser`, then `node tests/browser.cjs` passed (~28 seconds): HTTP/file://, CSP, import, filters, panels, review notes, theme and mobile coverage. All suite components therefore passed after restoring the test dependency; no site dependency was added. About 66 seconds of test execution, plus installation. This tests the existing site/importer changes, not a bundled BASE selector or publication that has not been implemented. No rebuild, publication, commit or push.
