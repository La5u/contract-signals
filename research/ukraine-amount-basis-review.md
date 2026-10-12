# Ukraine: exact cached contract/award amount bases

11 October 2026. **11 frozen tender GETs, all HTTP 200**, returned **2,561,091 bytes**. All live financial tuples equal their cached counterparts. **Seven amount differences have explicit net-basis evidence; four amount differences and fourteen VAT-only differences remain unexplained.** Retain normalized contract amounts. See [overall audit](ukraine-public-audit.md) and [correction log](ukraine-corrections-log.md).

All **488 rows** have exact, unique tender/contract/award/buyer/lot mappings. Of **25 amount/currency/VAT differences**, 11 differ in amount and 14 only in VAT (contract false, award true). Seven amount cases have contract `amountNet` equal to award amount, matching currency, contract VAT true and award VAT false. The four unexplained amount cases have both VAT flags true: three EUR, one UAH. The other **463** tuples match; matching values and active/signed/terminated status do not establish accuracy or payment.
Field absence, null, false and zero remain distinct. The importer uses a nonempty contract value object, otherwise the award object; this existing fallback is tested. Normalized rows have no VAT field. Evidence: `data/ukraine-amount-basis-evidence.json`; plan: `data/ukraine-public-audit-plan.json`; private freeze: `~/.cache/contract-signals/ukraine-public-audit/v1/plan.json`.
“Net evidence” means the explicit equality and VAT flags above. Amounts are published values, not payments; full contract/award identities and pointers are in the evidence.

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

For all 11, embedded contract `date` follows award `date` and equals tender `dateModified`; embedded `dateSigned` is absent. These single snapshots cannot explain financial changes. `data/prozorro-contract-changes.json` (retrieved `2026-10-09T21:31:45.865809+00:00`) adds:

- Four unresolved cases have zero stored changes. Award → contract dates, respectively: **2025-06-10 → 2025-06-13; 2025-05-16 → 2025-06-12; 2025-05-14 → 2025-05-18; 2026-02-11 → 2026-02-20**. These are chronology, not explanations or freshly verified amendment absence.
- UA-2025-06-06-005967-a and UA-2025-06-11-013329-a each have two `fiscalYearExtension` changes signed in December 2025 and January 2026, after embedded contracts dated July 2025. Summary status is terminated; older embedded status is active. Different snapshots do not establish that extensions caused the net/gross difference.
- UA-2026-01-22-018679-a has one `priceReductionWithoutQuantity` change dated **2026-04-01**, before the embedded contract date **2026-04-02**. No before/after amounts quantify its effect.
- The other four net-evidence cases have zero stored changes. The summary is not a historical financial ledger.

## Reproduction

```sh
python tools/audit-ukraine-amount-bases.py
python -m unittest discover -s tests -p test_audit_ukraine_amount_bases.py -v
```

Offline replay needs only public evidence and repository snapshots. It checks frozen sources, exact links and financial analysis, rejecting stale or malformed inputs. Public extracts exclude personal details and document text; hashes support local integrity but cannot authenticate or reconstruct withheld live bodies. Tests: `tests/test_audit_ukraine_amount_bases.py`.
Historical acquisition command, **completed once; do not repeat or clear its live evidence with `--write`**:

```sh
python tools/audit-ukraine-amount-bases.py --fetch \
  --private-dir "$HOME/.cache/contract-signals/ukraine-amount-bases-$(date -u +%Y%m%dT%H%M%SZ)" \
  --live-evidence
```
Acquisition requires the matching private freeze, an existing parent and a new external 0700 directory with exclusive 0600 files, without symlink traversal. Limits: 11 exact tender URLs, 15-second wall deadline, 2 MiB cap plus oversize sentinel, one-second start spacing, no retries/redirects/authentication/proxy credentials, stop on any failure including 403/429. Without `--live-evidence`, fetch leaves public evidence unchanged. There is no persistent cross-run budget manager. These 11 known differences are a diagnostic queue, not a random accuracy benchmark; historical versions and signed-document reconciliation remain missing.
