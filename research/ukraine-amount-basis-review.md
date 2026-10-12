# Ukraine: exact cached contract/award amount bases

## Completed live follow-up — 11 October 2026

The reserved acquisition was subsequently executed once: **11 exact frozen tender GETs, all HTTP 200**, capturing **2,561,091 bytes** in total. Every live contract/award financial tuple equals its cached counterpart. The seven explicit contract-net/award-excluding-VAT observations persist; the four amount differences remain unresolved. No field replacement, payment certification or scoring change follows. The public artifact now includes all eleven minimized request records, full-byte hashes and scalar pointers; default offline replay verifies them without private bodies.

This sequence is complete. Do not rerun the historical acquisition command below or clear its ledger with `--write`. Across discovery, modules, these tenders and the separately attempted attachment, the full review spent **29/30 requests**; the attachment's 302 stopped its sequence. See [overall audit](ukraine-public-audit.md) and [correction log](ukraine-corrections-log.md). Old minimized zero amendment counts below are snapshot claims, not newly verified absence of amendments.

## Historical preparation: scope and acquisition status

Offline review under frozen plan `6e8d5583760933a7dff4a00e9419fcd0af3bb7577f63b78b078ca5b3ece9dcbf` (`data/ukraine-public-audit-plan.json`; private freeze `~/.cache/contract-signals/ukraine-public-audit/v1/plan.json`). **No network requests were made in this delegation.** The public artifact has an empty live-request ledger. Contract-audit acquisition by a peer is outside this task; its results are neither claimed nor inferred here.

Only these new files are owned: `tools/audit-ukraine-amount-bases.py`, `tests/test_audit_ukraine_amount_bases.py`, `data/ukraine-amount-basis-evidence.json`, and this review. Existing dirty files remain untouched. No scores, weights, source contract values, labels, or shared files are changed. No commit/push.

## Cached findings

All **488** normalized rows were linked to their exact tender/internal contract/published contract/award/buyer/lot identities, with unique contract and award matches and a unique lot when applicable. Source file, row, compressed raw snapshot, decompressed source-byte hashes, JSON pointers and the published financial scalars are recorded in the artifact. Frozen selected/amount-queue pointers and identities are also checked. No heuristic match or substitute award is permitted.

- **11 amount differences**, all in the frozen queue of 11 distinct tender URLs.
- **25 amount/currency/VAT tuple differences**, hence **14 other tuple differences**.
- The 14 others are VAT-only: the same published amount/currency, contract VAT `false`, award VAT `true`. They remain unresolved; the flag mismatch alone does not explain the financial basis.
- **7 of the 11 amount differences have explicit basis evidence**: the published contract `amountNet` exactly equals the published award amount, currencies match, contract VAT is `true` and award VAT is `false`. This is stronger than observing a ratio or merely different flags. It supports a net-versus-VAT-included published basis, not a tax calculation, payment claim, or proof that the award was corrected.
- **4 amount differences remain unresolved**: both VAT flags are `true`; no cached metadata establishes why the contractual amount differs from the award. Three are EUR; one is UAH. No currency aggregation is performed.
- The remaining **463** have the same published tuple. This is not proof of accuracy or payment.

Absent fields, explicit null, false and zero are distinguished in tuple comparison; a missing VAT flag is never treated as false. The artifact preserves raw value presence states and the raw values, plus normalized amount/currency and their source pointer. The existing importer uses the contract value object when nonempty and otherwise the award value object. This fallback is disclosed and tested, not newly introduced or used to repair any row. Normalized rows do not publish a VAT field; the audit does not invent one.

### The 11 known amount cases

Amounts below are published scalars, not payments. “Net evidence” means explicit contract `amountNet` equals the award amount, with the VAT flags described above. Tender IDs identify the cases; the artifact provides full exact contract and award identities and source pointers.

| Tender ID | Currency | Contract amount | Award amount | Cached basis outcome |
|---|---|---:|---:|---|
| UA-2024-11-18-003142-a | EUR | 190267.15 | 190130.74 | Unresolved |
| UA-2025-03-06-014215-a | UAH | 12385910.51 | 12706074.08 | Unresolved |
| UA-2025-04-08-007367-a | EUR | 47191.0 | 47087.0 | Unresolved |
| UA-2025-06-06-005967-a | UAH | 1665999.6 | 1388333.0 | Net evidence |
| UA-2025-06-11-013329-a | UAH | 4211956.7 | 3509963.92 | Net evidence |
| UA-2025-10-15-015421-a | UAH | 755845.08 | 629870.9 | Net evidence |
| UA-2025-10-17-014252-a | EUR | 13242276.05 | 13224154.91 | Unresolved |
| UA-2026-01-22-018679-a | UAH | 5820000.0 | 4850000.0 | Net evidence |
| UA-2026-07-27-001301-a | UAH | 120556.8 | 100464.0 | Net evidence |
| UA-2026-08-04-006000-a | UAH | 302400.0 | 252000.0 | Net evidence |
| UA-2026-08-07-010890-a | UAH | 169896.0 | 141580.0 | Net evidence |

### Date/version/amendment inspection, not inferred causality

For all 11, the embedded contract `date` is later than the award `date`; the tender `dateModified` equals that contract date in the cached tender response. No `dateSigned` is present in these embedded contract records. These are single snapshots, not a sequence of historical financial versions. Later publication cannot by itself establish a negotiation, exchange-rate change, amendment, tax correction, or payment.

The independently cached contracting-module summary (`data/prozorro-contract-changes.json`, retrieved `2026-10-09T21:31:45.865809+00:00`) was also inspected and is preserved with source hash and exact contract pointer:

- The four unresolved cases each have **zero published changes** in that summary. Award → embedded contract dates are respectively 2025-06-10 → 2025-06-13, 2025-05-16 → 2025-06-12, 2025-05-14 → 2025-05-18, and 2026-02-11 → 2026-02-20. This provides chronology, not an explanation for their amount gaps.
- UA-2025-06-06-005967-a and UA-2025-06-11-013329-a each have two changes, type `fiscalYearExtension`, with signed dates in December 2025 and January 2026. Those dates postdate their embedded tender contracts (July 2025). The summary has terminated status while the older embedded tender contracts are active: evidence of distinct source snapshots, not financial-version reconciliation. It cannot establish that those extensions caused the earlier net/gross difference.
- UA-2026-01-22-018679-a has one `priceReductionWithoutQuantity` change dated 2026-04-01, before the embedded contract date 2026-04-02. No before/after financial amounts are supplied in the summary. A price change may be relevant, but its contribution is not quantified or causally certified. The explicit net/award equality remains the narrower basis observation.
- The other four net-evidence cases have zero published changes in the cached contracting summary.

The summary’s source bytes are hash-verified locally, but its original HTTP full bodies are not supplied here. It must not be described as a historical value ledger. Active/signed/terminated status is never proof of payment.

## Offline reproduction and fail-closed behavior

```sh
python tools/audit-ukraine-amount-bases.py
python -m unittest discover -s tests -p test_audit_ukraine_amount_bases.py -v
```

Default operation only reads the committed public artifact and frozen repository snapshots, revalidates all planned source/raw hashes and exact identities, regenerates the cached baseline and analysis, and prints the summary. It neither opens the private acquisition cache nor rewrites evidence. Changed source bytes, plan, rows, bindings, endpoints, public baseline or malformed live extraction fail closed. `--write` explicitly regenerates the cached artifact (and clears its live ledger); do not use it to replace acquired live evidence accidentally.

The public scalar extracts reproduce the financial analysis after acquisition **without the private cache**. Their scalar hash is checkable, but a full source-byte hash **cannot be reverified from a minimized extract**. Live full-byte verification requires the private bodies; repository gzip snapshots can still be verified locally. Neither minimized hashes nor ledgers are cryptographic proof of remote authenticity.

Public extraction excludes personal contacts, titles, descriptions, supplier identities and document contents. Only exact mapping identifiers, financial values and limited date/status/amendment metadata are retained. Public buyer identifiers are included solely for the required exact buyer linkage.

## Historical planned acquisition (subsequently executed once; do not repeat)

Run only after coordinating the peer’s separate contract-audit acquisition/budget. Do not repeat a partially successful run casually; there is no persistent cross-run budget manager. The 11 cases are **all known snapshot amount differences**, a nonrepresentative diagnostic queue, **not a new random accuracy benchmark**.

```sh
python tools/audit-ukraine-amount-bases.py --fetch \
  --private-dir "$HOME/.cache/contract-signals/ukraine-amount-bases-$(date -u +%Y%m%dT%H%M%SZ)" \
  --live-evidence
```

The parent cache directory must already exist. The run directory must not exist: it is created exclusively outside Git, without symlink traversal, mode `0700`; bodies and per-attempt ledgers are exclusive `0600` files. The private frozen plan must equal the validated public plan before acquisition starts.

- At most **11 GET attempts**, each at its exact frozen distinct tender URL, once only.
- **15-second wall-time deadline per attempt**, **2 MiB body cap** (one extra byte may be read to detect oversize; never claimed as a complete body), **one-second minimum spacing between starts**.
- No retries, redirects, authentication, cookies or environmental proxy credentials. Any failure stops; in particular **403/429 stop immediately without further attempts**.
- Ledger records method, URL, UTC time, HTTP status, byte count, complete full-byte SHA-256 when available, minimized pointer/scalar extraction, and sanitized failure state. Incomplete/oversized bodies never receive a complete-body hash claim.
- Live records must satisfy exact identities; array positions may change, but IDs cannot be remapped heuristically. Public replay rechecks allowed pointers, endpoints, distinct-request budget, identities and scalar analysis. Live outcomes compare both published values to the immutable cached snapshot, rather than replacing it.

`--fetch` without `--live-evidence` keeps public evidence unchanged and prints the live summary; private ledgers/bodies still record the run. With `--live-evidence`, the owned public JSON artifact includes the minimized acquisition ledger. A subsequent default offline invocation replays it without opening the private cache. This prose remains the cached review; new live findings are in the JSON summary.

Blocked scope remains: no additional tender/contract/document requests, no historical-version acquisition, no paid claims, no tax conversion, no mixed-currency sums, no value replacement, no legal conclusions, no scoring/weight changes, no corruption labels, no representative-accuracy claims.
