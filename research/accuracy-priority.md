# Accuracy-first work queue

Accuracy comes before expansion or scoring changes. Supplement fields only from exact official evidence after source/mapping checks. Do not guess, convert currencies, allocate notice totals to lots, sum supplier/version rows or treat absent amounts as zero.

## Completed reviews

- Inventory: 14 datasets / 18,501 rows (`accuracy-inventory.md`, `tools/audit-data-quality.py`). French DECP and BOAMP reconciliation found no reviewed-field mismatches (`accuracy-france-source-review.md`); signed documents and upstream truth remain unverified.
- All 1,537 amount gaps reconciled: 154 explicit zeros, 780 absent amounts, one negative amount, 526 unresolved DECP initial conflicts and 76 notice-only rows (`missing-amounts-review.md`, `tools/review-missing-amounts.py`). No supported replacement found. Three exact-ID API checks retained two zeros and one missing amount (`current-amount-recheck.md`).
- Fixed currency sorting/profiles, French opt-in threshold prerequisites, zero/missing explanations and history formatting. Legacy French EUR defaults remain documented. Hardened BOAMP numeric/date parsing, offer statistics and holder-reference pairing; saved-snapshot output is unchanged. Tests passed: 269 Python tests, JavaScript suites and browser tests; these check implementation, not factual accuracy.
- Frozen six-stratum documentary sample (`document-review-protocol.md`, `tools/prepare-document-review.py`): three exact BOAMP PDFs corroborate source fields but leave tax/contract truth unresolved; one document was not acquired. Paraguay’s scan agrees on total including VAT; its handwritten signature date needs independent review. DECP conflict remains unresolved (`document-review-results.md`).
- UK audit found one linked retained contract per published row and no observed multiplicity loss or amount fallback; three dates use notice-date fallback. Date semantics, latent importer risks and contract/award value agreement remain open (`uk-contract-multiplicity-review.md`).
- Dijon BOAMP 24-79759 uses the DECP ID for the procedure and lists six distinct lot contracts; three candidate pairings disagree on offers. Holder linkage and tax/basis remain unresolved; six private candidates stay unpublished and the grouped DECP row excluded (`decp-dijon-conflict-review.md`).

## Ukraine follow-up — 11 October 2026

[Review](ukraine-public-audit.md) and [correction history](ukraine-corrections-log.md): all 488 cached mappings/provenance checked; twelve module links and eleven amount-difference tenders retrieved. Seven differences have explicit net/excluding-VAT evidence; four amount cases and fourteen VAT-only differences remain unresolved. Six nonempty lists corroborate ten amendments, including the sole three-change flag; six omitted lists mean zero changes, verified from the API source. Current search has 506 entries, but historical truncation and date-filter equivalence remain unknown. No document body or independent legal/financial basis was established; scores, source fields and cohort stayed unchanged.

## Open gates before more data or weight changes

1. **Independent documents:** freeze a stratified sample of flagged, unflagged, zero, missing and conflicting records; verify contract/lot/version identity, amounts and dates against official originals. Record reviewer, retrieval date, source hash and discrepancies. Existing checks are not independent expert validation.
2. **Primary law:** verify scoring thresholds and applicability against legislation, especially provisional or secondary-source rules; leave unverified applicability unknown.
3. **UK multiplicity/fallback:** the cohort audit found no concrete loss, but the importer can select one of several contracts per award. Keep contract and award value provenance distinct; the nine missing-amount rows each have one counterpart, without proving value agreement.
4. **Paris/Ardèche history:** preserve typed holder IDs and review modification conflicts with tests and before/after evidence. Initial history omissions do not imply unchanged suppliers.
5. **Currency filter:** decide a currency-specific minimum-amount filter; the current numeric cutoff spans currencies without conversion.
6. **Importer guards:** review finite values, boolean numeric inputs, date meaning, reused IDs and exclusions across jurisdictions.
7. **Missing fields and Ukraine scope:** review field eligibility/privacy and exact document/discovery scope before expansion. Notice-only values are not contract gaps; current register names are not historical names. Zero-score rows, unmonitored contracts and unlabelled outcomes remain unknown. DASU/court findings need separate finality and exact-link review.

## Evidence enrichment after the relevant gate

Freeze IDs and required field/basis before low-volume official retrieval; keep URL, UTC time and SHA-256 with private responses under `~/.cache/contract-signals/`. Stop on refusal/rate limits; no retries, proxy bypass or unrelated collection. Framework ceilings, estimates, award totals, invoices and payments cannot replace contract values without matching scope/basis. Resolve DECP conflicts from contract/lot/version evidence, not the most plausible row. Keep notice-only contract evidence separately typed and preserve source declarations and correction provenance. Candidates require review; the inventory queue includes expected omissions, not proven errors.
