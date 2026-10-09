# Accuracy-first work queue

Accuracy review is the owner's priority, ahead of expansion or scoring changes. Only after source/mapping checks should missing fields be supplemented from exact, documented official evidence. Do not guess, convert currencies, allocate notice totals to lots, sum supplier/version rows, or treat absent amounts as zero. Changes remain local; no push or deployment has been performed.

## Completed in this session

- Structural inventory of 14 published datasets / 18,501 rows: `accuracy-inventory.md` and `tools/audit-data-quality.py`.
- French source-to-normalized reconciliation for DECP cities, Paris/Ardèche and the BOAMP sample: `accuracy-france-source-review.md`. Regeneration and independent reviewed-field checks found no mismatches. This does not verify signed documents or upstream truth.
- Reconciliation of every published zero/null amount against retained evidence: `missing-amounts-review.md` and `tools/review-missing-amounts.py`. Of 1,537 gaps: 154 explicit zeros, 780 absent amounts, one negative source amount, 526 unresolved DECP initial conflicts, 76 notice-only rows. No supported replacement amount found.
- An additional 488 Ukraine contract-value provenance checks; 11 contract/award differences retained as distinct bases, not corrections.
- Three preregistered exact-ID live official API checks: `current-amount-recheck.md`. Two zeros and one missing amount persist; no positive replacement candidates. This small check is not a representative assessment of current upstream completeness.
- Corrected currency sorting/profile assumptions, French opt-in threshold prerequisites, zero-versus-missing explanations and history formatting. Legacy French EUR defaults remain deliberate and documented, not globally removed. Published scores in the score-review cohorts are unchanged.
- Hardened BOAMP parsing for finite amounts/durations, calendar dates, offers-statistic conflicts/text nodes, and holder-reference pairing. Saved-snapshot build is unchanged; no source dataset was rebuilt.
- Full suite passed: 269 Python tests, JavaScript suites including new currency regressions, and browser tests. These validate implementation behaviour, not factual contract accuracy.

## Subsequent bounded pass

- Frozen six-stratum sample: `document-review-protocol.md` and `tools/prepare-document-review.py`.
- First documentary outcomes: `document-review-results.md`. Three exact BOAMP notice PDFs corroborate the reviewed source fields, with tax/underlying contract truth still unresolved; one BOAMP document was not acquired within the request budget. The linked Paraguay scan agrees on total amount and explicitly includes VAT; its handwritten signature date is a private candidate pending independent review. The DECP conflict remains unresolved after comparison with the cached national snapshot. No published fields were filled.
- Full UK contract-per-award audit: `uk-contract-multiplicity-review.md`. Every published row has exactly one linked retained contract and matches the importer amount/currency/date rule; no concrete multiplicity loss or amount fallback observed. Three dates use notice-date fallback. Latent importer risks and date semantics remain open; absence of comparable award values does not prove contract/award agreement.

- Dijon conflict follow-up: `decp-dijon-conflict-review.md`. Exact official BOAMP notice 24-79759 uses the DECP ID as a procedure identifier and lists distinct lot contracts corresponding to the six amounts. Three candidate lot pairings disagree on offer counts. Individual holder linkage and tax/basis remain unresolved; six private candidates are not published and the grouped DECP row stays excluded. Do not choose the lone national row or invent a combined amount.

## Open accuracy gates — before more data or weight changes

1. **Independent documentary validation.** Freeze a stratified review sample containing flagged, unflagged, zero, missing and conflicting records. Verify exact contract/lot/version identities and amounts/date semantics against original official documents; record reviewer, retrieval date, source hash and unresolved discrepancies. Existing reviews are assistant source/mapping checks, not independent expert validation.
2. **Primary legal verification.** Check scoring-critical threshold texts and applicability against primary legislation, especially rules currently documented as provisional/secondary-source based. Keep unverified legal applicability unknown; do not call the current work a completed legal audit.
3. **UK contract-per-award multiplicity and fallback basis.** The importer can select one contract where multiple contracts reference an award; inspect the full cohort before changing granularity. Contract and award values must have distinct provenance. The nine UK missing-amount rows have one counterpart each, but that does not clear the rest of the cohort.
4. **Paris/Ardèche history fidelity.** Preserve typed known holder IDs and review modification-conflict handling, with tests and before/after evidence. Currently documented initial history omissions do not justify assuming unchanged suppliers.
5. **Mixed-currency minimum-amount filtering.** One numeric cutoff currently operates across currencies. Decide a currency-specific filter/UI before changing semantics; no conversion or universal purchasing-value comparison should be implied.
6. **Other importer numeric/temporal guards.** Review finite values, boolean numeric inputs, chronological meaning, reused IDs and exclusion logic across jurisdictions. Structural validity does not clear these paths.
7. **Other missing fields.** Offers, dates, durations and supplier names need source-specific eligibility and privacy review. A notice row's absent contract value is not a repairable contract gap. Current register names are not historical supplier names.

## Bounded evidence enrichment, after the relevant gate

- Freeze exact candidate IDs and the required field/basis before retrieval. Prefer low-volume official APIs; retain responses privately, with URL, UTC retrieval time and SHA-256. Stop on refusal/rate limits; no retries, proxy bypass or broad unrelated collection.
- For zero amounts, seek exact contract values or explicit upstream corrections. A framework ceiling, tender estimate, award total, invoice or paid amount is separate context, never a substitute without matching scope and basis.
- For DECP conflicts, inspect contract/lot/version semantics and official buyer publication. Do not resolve by choosing the latest, smallest, largest or most plausible row without evidence.
- For notice-only datasets, add linked awarded-contract evidence only through exact documented identifiers and keep it separately typed; do not turn consultation records into inferred contracts.
- New evidence is a candidate until reviewed; preserve original source declarations, uncertainty and correction provenance. No published amount has been filled in this session.

All exact-ID evidence queues and live responses remain under `~/.cache/contract-signals/`, outside the served repository. The broad inventory queue includes expected omissions and is not a list of proven errors.
