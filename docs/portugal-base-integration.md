# Portugal BASE: bounded candidate audit and integration handoff

## Result

The existing plain-name private candidate was reused, not rebuilt. `data/portugal-base-candidate-manifest.json` is a **public aggregate audit, not contract records or release approval**. The candidate remains at:

```
~/.cache/contract-signals/base-candidate-plain-2026-10-16/candidate.json
```

Its SHA-256 is `4bfb01bd3cf7ad56eeb4fff1dd1c39c8785e8149bf714226581b3baf228d7d2a` (9,957,755 bytes). Strict current importer validation and coverage reconciliation pass. This is the current published-name/individual-flag design, **not** the obsolete scrambled-name candidate in `base-candidate/`.

- 3,966 retained rows: Infraestruturas de Portugal 1,515; CIM Cávado 100; Lisboa 2,351.
- Exact buyer NIF selection; source publication dates in `[2024-09-01, 2026-09-01)`.
- Existing extraction reported 655,235 national rows; **none were scanned again for this audit**. Historical archive hashes/counts are carried forward, not freshly verified against the ZIPs.
- 17 equivalent minimized duplicates removed; no conflicting minimized variants. Two subject failures and one holder-shape failure omitted. 277 buyer parse-error rows include 273 unknown-buyer rows. These overlap; do not subtract them twice. Coverage remains **unknown**, not complete national or complete buyer procurement coverage.
- 4,077 holder entries, including 615 prefix/blank-ID flagged individual-or-foreign entries. These are neither distinct suppliers nor verified natural-person counts.
- No email, isolated nine-digit identifier or tested Portuguese IBAN pattern in selected subjects/holder names. This is a heuristic check, not an exhaustive incidental-personal-data review. It does not establish that every named holder's publication is necessary or lawful.

## Rights and overlap gates

Read [portugal-base.md](portugal-base.md), [personal-data.md](personal-data.md) and `data/portugal-base-rights.json` before release. IMPIC's `other-pd` is an official Other/Public Domain category, **not CC0**, not the TED licence, and not privacy clearance. No new publisher clarification was obtained. Supplier tax IDs, unsuccessful bidder identities, contacts, notes and raw national archives remain excluded from public candidate records. Published supplier names are retained under the owner policy; flagged names are excluded from explorer exports.

The existing Portugal TED cohort has the same buyers and date window, but **exact record overlap is unknown**. BASE contract IDs cannot safely be joined to TED's notice-local `CON-0001` etc. BASE process/announcement IDs were not retained by this minimized candidate. Date/title/supplier similarities are not established identity links. Do not add the 3,966 BASE rows to 488 TED rows and call the result distinct contracts, or describe BASE as wholly additional coverage. A future bounded link audit needs justified identifiers and a separately preserved private mapping, not a national rebuild.

`precoContratual` is a declaration with unresolved currency and framework/lot basis. No effective-total, amount-increase or competition score is enabled. Do not sum these values or transfer TED scoring. If a bundled dataset is later released before amount semantics are established, prefer a separately fingerprinted derivative withholding `amount` (with an honest updated basis/schema and tests), rather than presenting framework values as individual awards.

## Reproduce without extraction or network

```sh
python tools/import-portugal-base.py --audit-candidate \
  --candidate-dir ~/.cache/contract-signals/base-candidate-plain-2026-10-16
python -m unittest discover -s tests -p 'test_import_portugal_base.py'
```

The audit enforces private directories/files, bounded JSON reads, candidate/coverage/plan/download fingerprints, strict candidate and coverage whitelists, and count reconciliation. It prints aggregate JSON only and performs no writes or archive reads. `--extract` remains a separate opt-in operation; it is unnecessary for this candidate.

## Parent registry instructions (do not register yet)

The candidate array is already compatible with the generic local JSON import workflow; keep `assessmentMode: browse`, `dataStatus: unverified` on **every row**. `date` means publication, with signing/award/closure dates separately labelled. Currency, offer count, duration months and direct-award classification stay unknown.

1. Complete candidate-level incidental-content/redistribution review and unresolved amount-basis decision. Do not invent a human reviewer or treat this audit as legal clearance.
2. If the unchanged candidate is approved, use the existing explicit `--publish-reviewed --candidate-dir ... --reviewer ... --candidate-sha256 ...` workflow. It writes `data/portugal-base.json` and `data/portugal-base-coverage.json`, without UI changes. Any transformation requires a new candidate fingerprint and corresponding validator/tests; never silently alter reviewed bytes.
3. Only after actual reviewed record files exist, parent may add a dataset key such as `portugal-base`, label **Portugal · BASE · 3 buyers (browse only)**, pointing at those two files. Do **not** point the registry at `portugal-base-candidate-manifest.json`. Mark it as BASE, not TED; explain the exact buyer/date scope, publisher attribution, unknown completeness/overlap and browse-only restrictions in metadata/translations.
4. Add registry/selection regression coverage ensuring every loaded row is Not assessed; no risk points, score totals, inferred currency, framework award totals or offer-count rules. Confirm individual-name export safeguards and publication/signing-date wording.

## Bounded verification

Passed 44 BASE importer/audit tests, five archive-inspection tests, six SEAP importer tests, the existing JS import-engine test and `git diff --check`. Both actual private files were also parsed with `import.js` and prepared with the current engine: 3,966 BASE and 149 SEAP rows accepted, with null scores throughout. These are bounded importer/engine checks, not a browser or full-suite claim.

No built-in registration, deployment, national reprocessing or raw redistribution was done here. Romania's separate bounded candidate and gates are documented in [romania-seap.md](romania-seap.md).
