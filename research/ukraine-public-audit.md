# Ukraine public-only accuracy audit — 11 October 2026

## Result

Bounded review of the **existing 488-contract cohort**, not expansion, calibration or independent expert validation. Source records, website/index inputs, weights and scores are unchanged. No buyer contact, commit, push or deployment.

| Check | Supported result | Still unknown |
| --- | --- | --- |
| Cached identities/provenance | All 488 exact tender/contract/award/buyer/lot mappings and normalized amount/currency provenance verified | Upstream factual truth, signatures, payments and complete discovery |
| Contract/award amount differences | 7 of 11 have explicit contract `amountNet` equal to the VAT-excluded award amount in the same currency; all 11 fresh tender responses retain the cached financial fields | Cause/basis of 4 amount differences; signed-document reconciliation |
| Other financial differences | 14 more cases have identical amount/currency but differing VAT flags | Their basis; not automatic corrections |
| Sampled amendment modules | All 12 exact module links verified; 6 nonempty arrays contain 10 uniquely identified active changes with dated signatures, matching the frozen nonzero counts | None for counts: the 6 omitted `changes` fields mean zero changes (publisher serializer omits empty lists; verified in source, see correction log). Marked in `data/ukraine-amendment-counts.json`: 12/12 agree with stored counts |
| Three-amendment flag | Sole threshold case has 3 active changes: 1 quality-improvement and 2 fiscal-year-extension categories | Legality, monetary effect, independent document explanation |
| Discovery | Current Vinnytsia all-time search reports 506 entries, 20/page; pages 25/26/27 yield 20/6/0, with no current 500 cap observed | Historical completeness; intermediate pages unqueried; portal date-filter semantics |
| Primary attachments | One exact published document URL returned HTTP 302, not followed; sequence stopped before second document | Document contents, statutory/financial basis and authenticity |

**No amount replacements are justified.** Seven net/gross basis observations are not seven corrected prices or independently validated contracts. The 18 unresolved financial-tuple differences are 4 amount cases plus 14 VAT-only cases. Equal financial tuples in the other 463 rows are not proof of accuracy.

## Selection and timing

`tools/prepare-ukraine-public-audit.py` deterministically reproduces `data/ukraine-public-audit-plan.json`:

- Public/source/row/compressed-snapshot hashes and complete exact identity bindings.
- Round-robin selection across procedure class × amendment-count band × existing-score strata; SHA256 ranking within strata.
- **12 selected: 5 flagged and 7 zero-score**, covering reporting/competitive procedures and counts 0, 1–2 and 3+. Zero-score rows are not reviewed negatives or clean contracts.
- All **11 known amount differences** form a separate diagnostic queue, not a random benchmark.
- Frozen SHA256: **`6e8d5583760933a7dff4a00e9419fcd0af3bb7577f63b78b078ca5b3ece9dcbf`**. Private read-only copy: `~/.cache/contract-signals/ukraine-public-audit/v1/plan.json` (0400).
- Selection followed the existing snapshot inventory and unrelated discovery probes, but preceded fresh contract/tender/document retrieval. The existing amendment counts and scores were already known. Do not call this a blinded or representative accuracy validation.
- Supplementary document selection had its own pre-body freeze, after module metadata retrieval. v1 was blocked by an unnecessarily narrow host policy; v2 preserved the same document order/URLs while admitting the official API's own published download endpoint. Both historical plans are retained.

## Actual request accounting

**29 attempts / ceiling 30:** 5 discovery POSTs + 12 contracting-module GETs + 11 amount-tender GETs + 1 attachment GET. The first 28 returned HTTP 200; the attachment returned 302 and was not followed. One slot is unused, but the stopped document sequence is closed—no retry or replacement is authorized by this record.

No metadata refetches, additional buyers, national feed crawl, authentication, challenge bypass, OCR service or document uploads. Requests had 2 MiB caps and at least one second between starts within each serial stage. The historical discovery run used a configured 15-second socket timeout; its hardened future helper adds a wall deadline. The later module/tender/document acquisitions enforce 15-second total transfer/wall limits. No redirects or retries were followed.

Full fresh responses remain outside Git in private 0700 directories/0600 files. Published evidence contains exact identifiers, source URLs or explicit API pointers plus download-URL hashes, response hashes, field locators and minimized financial/date/status/category scalars—not contacts, supplier identifiers, descriptions or document text. Signed query URLs and redirect destinations are not published. A minimized extract cannot reconstruct or independently authenticate a full response hash. Hashes provide local integrity and acquisition commitments, not remote signatures.

## Offline reproduction

All following commands use repository snapshots and public minimized evidence, **not private caches/freezes and not the network**:

```sh
python tools/audit-ukraine-discovery.py
python tools/audit-ukraine-amendments.py
python tools/audit-ukraine-amount-bases.py
python tools/review-ukraine-amendment-documents.py
python tools/review-ukraine-amendment-documents.py --version 1
```

The preparation command verifies or creates an external immutable freeze; unlike the replay commands it intentionally requires private storage:

```sh
python tools/prepare-ukraine-public-audit.py
```

Stale frozen inputs fail closed. Do not overwrite v1 or carry dispositions automatically after rebuilding inputs. A new source/selection version requires renewed review. Opt-in acquisition switches are not permission to repeat this completed run.

## Durable corrections and next gates

See [correction log](ukraine-corrections-log.md), [amendment review](ukraine-amendment-review.md), [financial review](ukraine-amount-basis-review.md), [discovery review](ukraine-discovery-review.md), and [attachment history](ukraine-amendment-document-review.md).

1. ~~Verify the published contracting schema's treatment of omitted `changes`.~~ **Done 11 October 2026:** omission means no changes (serializer drops empty lists; see [correction log](ukraine-corrections-log.md)). The importer's zero default is correct; this does not re-verify each of the 469 stored zeros. Preserve the old snapshot; any enrichment needs full module link/hash/presence provenance.
2. A separately reviewed attachment plan could permit an explicit publisher redirect with host/bounds/privacy checks. The current no-redirect plan cannot acquire these documents. No legal conclusion from rationale categories alone.
3. Seek exact historical versions or explicit documents for the 4 unresolved amount cases and 14 VAT-only differences; no ratio, currency conversion or award substitution.
4. Verify portal date-filter semantics and a complete, fixed-window listing before expansion. Current 506 versus historical 500 may reflect ordinary time drift; neither proves historical truncation. All 16 original buyer-association mismatches remain excluded.
5. Any DASU/court outcome follow-up needs exact tender/contract linkage, outcome scope and dated finality evidence. Audit selection is biased; absent matches remain unknown; zero scores and same-buyer comparisons are not corruption-negative labels. Research outcome cohorts remain separate from this source audit and from the website index.

Attribution: **Prozorro, Ministry of Economy of Ukraine / State enterprise Prozorro**. Publisher reuse terms permit open-data reuse with attribution but name no standard API-data licence; do not infer CC BY, MIT, attachment redistribution permission or privacy clearance. No attachment contents are redistributed here.
