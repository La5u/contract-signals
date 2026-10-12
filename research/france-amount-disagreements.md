# French amount disagreements: conservative offline queue

## Result

The current published files still contain **885 `verification.status == sources-disagree` records**, not a newly inferred set of monetary discrepancies. The cohort shorthand in HANDOFF needs qualification:

| Current cohort | Population | Disagreements | Declared max/min > 2× |
|---|---:|---:|---:|
| Paris/Ardèche | 2,997 | 788 | 486 |
| Six cities | 2,289 | 97 | 33 |
| Total | 5,286 | **885** | **519** |

The 788 comprise **782 Ville de Paris and 6 Département de l’Ardèche**, not 788 Paris contracts. The cities comprise **91 Nantes, 4 Grenoble, 1 Dijon and 1 Bordeaux**; Rennes and Tours have none in this status. The current cities population is 2,289, not the older 2,299 handoff figure.

**Resolutions: zero.** All 885 have exact buyer-SIRET/contract-ID declaration evidence in the reviewed raw snapshots. Only **one** has an exact additional buyer-portal declaration in the normalized Nantes/Bordeaux portal snapshot. Those declarations are not signed contract evidence or independent votes.

The retained random-sample BOAMP search responses yield parseable eForms lot candidates for **25** disagreement records (19 Paris/Ardèche, 6 cities). They are search candidates, not validated contract matches. Across the explicitly reviewed notice caches and retained BOAMP raw snapshot, **zero** meet this tool’s strict conjunction of contracting-buyer identifier and complete, equal settled-contract reference. This does **not** mean the contracts lack award notices: notice references can differ from DECP IDs, buyer IDs can be missing or placeholders, and the retained caches are incomplete.

Candidate lot fragments contain 329 payable-amount fields (period unknown), 376 maximum-amount fields and 57 other amount fields. These are **field occurrences across potentially unrelated lots and repeat notices**, not contract counts or resolutions. No estimate field occurs in these candidate fragments. Annual/full-term equivalence is **not established**. The older claim that disagreements are “mostly basis differences” remains a hypothesis, not a finding established for these 885 rows.

## Repeatable execution and private output

```sh
python tools/review-france-amount-disagreements.py
python -m unittest discover -s tests -p test_review_france_amount_disagreements.py -v
```

Each execution creates a new mode-0700 directory under:

`~/.cache/contract-signals/france-amount-disagreements/run-*/`

Files are mode 0600:

- `queue.jsonl`: all 885 records in existing dataset order; identities, published amounts/ranges, separate amount-source declarations, exact raw buyer-row pointers, scoped notice evidence, candidate linkage limits, duration, ratio diagnostic, status and explicit unknowns.
- `provenance.json`: SHA-256 and byte count for every consumed file, source metadata where present, and original response retrieval entries (URL, retrieval time, status, hash).
- `summary.json`: aggregate counts and policy.

There is no network code, no fetch option, no automatic replacement, no majority resolution and no production sorting change. The queue can be regenerated from the same snapshots; tests compare two complete offline builds and check that the normalized inputs remain unchanged. Paths/provenance and raw notice details remain private rather than being copied into this note.

## Reviewed source inventory

1. **Normalized inputs at initial review, before CPV-only corrections:** `data/decp-history.json` and `data/decp-cities.json`. Snapshot hashes respectively:
   - `26b3fedc2daa5f504f1c472b60e6f17204c84a88413a2d24aa11612a6b0d3ef9`
   - `7a85985ea87fe363a1ecf5e00d8da4e9d2d2f2bfde30525e21bad8b614074c6d`
2. **Ministry declaration snapshots:** `data/decp-history-raw.json.gz` (retrieved 2026-09-25) and `data/decp-cities-raw.json` (retrieved 2026-09-15). Each matched row retains its `/records/N` pointer, declared initial amount and separately identified modification amount. A modification is a revised declared total, never an increment to sum.
3. **Buyer feeds through a third-party consolidator:** `data/decp-feeds-raw.json.gz`; resource dated 2026-10-04, retrieved 2026-10-04. Exact buyer + contract joins only; sourceDataset/sourceFile, current/modification flags and duration are retained. These are not direct signed buyer documents. Aliased/truncated feed IDs are deliberately not silently joined.
4. **Buyer open-data lists:** `data/city-portals-raw.json.gz`, with source metadata for Nantes 2024/2025 and Bordeaux City, retrieved 2026-10-08. This normalized snapshot documents correction of the Nantes 2024 published buyer-SIRET error; this review neither repeats nor expands that correction. The underlying private portal cache is supplementary raw evidence, not a new independent source vote.
5. **Notice evidence:** `data/boamp-raw.json.gz`; manifested private responses under `accuracy-sample-20261008/responses*`, `paris-pairs-20261008`, and `decp-conflict-dijon/project-notices-20261008`. Only HTTP-200, non-truncated responses with matching manifest SHA-256 are accepted. **One truncated cached response is excluded**; the later resumed response can independently be accepted. No new documents were fetched.

The new review does not reuse `tools/accuracy-sample.py`’s “any printed amount matches” confirmation rule. Its search labels are retained only to associate unvalidated candidates with queue records. General buyer-profile URLs, name similarity, substring contract references and matching numeric values are not exact linkage.

## Basis and resolution policy

- **Annual / full term:** unknown unless an exact-linked document explicitly defines the monetary field’s covered period and renewal scope. A 2×/4× ratio or a 48-month duration is not enough. Do not multiply an amount by duration, sum coholders or annualize a maximum.
- **Maximum:** preserve the structured maximum field and its lot-result scope. A ceiling is not an estimate, tender price, annual spend or actual spend.
- **Estimate:** preserve a structured estimated field if encountered; do not substitute it for a maximum or payable amount.
- **Tender payable amount:** preserve currency and field pointer; the field alone does not establish annual versus full-term coverage.
- **Unknown monetary field:** retain it as unknown, not as a candidate replacement.
- **Procedure totals:** exclude notice-level totals from lot-level comparisons. Multiple result links to one tender are rejected rather than guessed.
- **Tax, amendments and timing:** declared initial amounts, revised totals and notice amounts need independently verified tax/period/version alignment. Current supplier-register names are not historical contract identities.

The parser covers the retained conventional eForms extension shape, not every legacy BOAMP schema or every possible extension/list encoding. Unsupported layouts fail closed. Duplicate/repeated candidate notices remain visible rather than being counted as independent corroboration. Absence from the exact index is therefore a queue status, not evidence of absence of a notice.

## Manual continuation

The private queue allows two useful review passes without changing its order: inspect records with search candidates first for exact reference/lot/buyer linkage; inspect the 519 >2× disagreements for explicit period/maximum/estimate definitions. Neither diagnostic is a resolution recommendation. Acquire a small number of exact official buyer award/notification or signed-contract documents only after identifying the contract and lot. Record the document URL, retrieval time, hash, page/field, currency, tax, period, amendments and renewal scope. If these cannot be established, leave the disagreement unresolved.

**Integration follow-up:** The offline queue was regenerated after 165 CPV-only corrections. All counts and unresolved outcomes above are unchanged; the new private run records current input hashes. Amounts, bases and sorting were not changed.

**Validation:** 9 focused tests pass, including distinct amount semantics, exclusion of procedure totals, ambiguity rejection, exact-reference keys, non-finite/negative handling, zero-safe ratios, ratio/matching-number non-resolution, unsupported notices, and repeatable read-only full offline builds. Only the three task-owned new files are changed; no shared files, datasets, HANDOFF, commits or pushes.
