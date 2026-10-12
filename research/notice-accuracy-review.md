# Notice-eligible accuracy review — preregistration protocol v1

## Finding and boundary

Implemented **preparation**, not a measured accuracy study. Task 1 of the current
HANDOFF open items needs a new denominator: the earlier 90-row sample's 76
unlinked records cannot be treated as accurate, inaccurate, or exempt from notice
duties. This helper does not reuse those outcomes or infer obligations from price.

Current checkout inspected: the two French DECP snapshots contain **5,286 rows**
(2,289 cities; 2,997 Paris/Ardèche). **1,571** have the exact published procedure
`Appel d'offres ouvert`. They do not establish, by themselves, the applicable
regime, buyer category, procurement-start date, contract classification,
Article 5 estimate/aggregation, exclusions, lot derogations or individual notice
duty. A declared contract amount, CPV prefix, municipal-looking name/SIRET,
notification date, or BOAMP/TED presence is not a substitute for those facts.
`nature: Marché` is not a works/supplies/services classification.

The initial **no-manifest freeze** records:

- **0 eligible / 0 selected**;
- **1,726 unknown**: 1,571 exact-open rows lacking reviewed eligibility evidence,
  plus 155 missing published procedure labels;
- **3,560 ineligible for this narrow study scope**: other published procedure
  labels. This does **not** establish that they lack notice obligations.

Plan: `~/.cache/contract-signals/notice-accuracy-review/v1/plan.json`.
Canonical plan SHA-256:
`5a0337fc8f22564c9d7ccd3651bfaeafbb31d1a4b8aac6335e1f8730f03dbf08`.
This is an immutable empty-sample checkpoint of insufficient evidence, not a
claim that the population contains no qualifying contracts. A reviewed manifest
requires a **new freeze path**, not an edit of this plan.

The preparation worker changed no published datasets, scores or common files. A subsequent integration corrected CPV check digits only; the original v1 freeze above remains untouched. A new empty freeze binds the corrected snapshots at `~/.cache/contract-signals/notice-accuracy-review/v2-cpv/plan.json`, hash `e726eaa2fe8474419f13935ff398e151d29a6b43b4321f528a13266bb7bd9e5a`. Counts and eligibility outcomes are unchanged. To reproduce preparation against current rows, pass `--plan ~/.cache/contract-signals/notice-accuracy-review/v2-cpv/plan.json`; do not overwrite or rerun the original default v1 path against changed inputs.

## Primary legal sources: bounded attempted review, not successful verification

Four official EUR-Lex requests were made with no retries, redirects, scripts or
secondary-resource fetching: 20-second limit/request and 2 MiB body cap. **All
returned HTTP 202 AWS WAF challenge pages (2,035 bytes each), not legislation.**
The bodies were inspected; **no primary legislative provisions were acquired or
verified in this run**. Stop rather than bypass the challenge or silently use a
secondary summary. Raw bodies, headers, UTC retrieval metadata and hashes are
private under:
`~/.cache/contract-signals/notice-accuracy-legal/20261010T234020Z/`.

| Instrument / attempted official URL | Raw response SHA-256 (challenge, not law) |
| --- | --- |
| [Directive 2014/24/EU](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32014L0024) | `75a048a53401637fabc59ddacf27b4fdb71748abbebbd0a2db232adce7155cde` |
| [Delegated Regulation 2019/1828](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32019R1828) | `13b12596b2ecbb24a8166ab8a34fa7e4afca06c1d06c850db235607285e5f7d7` |
| [Delegated Regulation 2021/1952](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32021R1952) | `fcf1bb7884821676aa0e5bcafc6e719cf8476cd2f3500da7d46afaa358831167` |
| [Delegated Regulation 2023/2495](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R2495) | `f8d74a93bc66e7accf5633c250205adf0c12f906cef4889974a7ffd9912ba273` |

**Candidate mapping only, pending actual primary-text and French applicability
review:** Directive Articles 1–4 (scope), 5 (valuation), 26–27 (open procedures),
50–52 (award notices/dispatch/publication), 74–76 and Annex XIV (specific
services); Articles 1–2 of the threshold regulations. Confirm the relevant dated
French transposition/publication rules as well; the tool does not supply legal
advice or decide precedence between EU and national texts.

| Start-date period | Works | Central supplies/ordinary services | Subcentral supplies/ordinary services |
| --- | ---: | ---: | ---: |
| 2020–2021 | EUR 5,350,000 | EUR 139,000 | EUR 214,000 |
| 2022–2023 | EUR 5,382,000 | EUR 140,000 | EUR 215,000 |
| 2024–2025 | EUR 5,538,000 | EUR 143,000 | EUR 221,000 |

These provisional constants are consistency checks, **not proof of the law**.
Admission additionally requires explicit reviewer-attested primary-law evidence
for the exact threshold/date/application and individual award-notice duty. A
challenge-page checksum must never be attested as reviewed legislation.
Unsupported years, utilities, concessions, defence, mixed classifications,
Annex XIV services, framework call-offs and DPS are outside v1. Extend only with
a separately reviewed/versioned protocol.

Legal review must establish the estimate at call dispatch or procurement
commencement, not award/notification year. It must establish the applicable
Article 5 valuation method: options, renewals, relevant aggregate lots and any
special valuation rules. Do not simply multiply an annual price by duration or
use a procedure/framework ceiling as a contract correction. Review the small-lot
derogation and exclusions explicitly. The ordinary notice rule concerns dispatch,
not merely the displayed publication date; framework call-offs, DPS and specific
services have special regimes. None is automatically admitted here.

Legal threshold scope is generally **at or above**; this study intentionally
requires **strictly above** the reviewed threshold. Equality is conservatively
excluded from this particular sampling frame, not declared legally exempt.

## Helper and manifest contract

`tools/prepare-notice-accuracy-review.py` is standard-library-only, offline and
read-only with respect to the checkout. It reads both complete snapshots and
optionally a private JSON manifest. No Node scores, URLs fetched, notice search,
import, supplier-name matching, price-based matching or amount repairs occur.

Manifest shape (`schemaVersion` is exactly `notice-accuracy-review-v1`):

```json
{
  "schemaVersion": "notice-accuracy-review-v1",
  "records": [
    {
      "dataset": "data/decp-cities.json",
      "rowId": "EXACT-PUBLISHED-ID",
      "rowSha256": "SHA256-OF-CANONICAL-COMPLETE-PUBLISHED-ROW",
      "reviewedBy": "PRIVATE-REVIEWER-ID",
      "reviewedOn": "2026-10-10",
      "facts": {
        "regime": {
          "value": "2014/24/EU-ordinary",
          "evidence": [
            {
              "path": "relative/private-evidence.pdf",
              "sha256": "SHA256-OF-ACTUAL-EVIDENCE-BYTES",
              "url": "https://www.legifrance.gouv.fr/EXACT-OFFICIAL-SOURCE",
              "locator": "dated article/page/field and exact applicability passage"
            }
          ]
        }
      }
    }
  ]
}
```

This abbreviated example is **not eligible**. Every following fact requires its
own nonempty evidence array with a real private file, byte hash, official HTTPS
source URL and precise locator (one file may support several facts):

| Fact | Required reviewed value |
| --- | --- |
| `regime` | `2014/24/EU-ordinary` |
| `procedure` | `open`, corroborating the exact published open label |
| `awardKind` | `standalone-awarded-contract` |
| `exclusions` | `reviewed-none-applicable` |
| `valuationBasis` | `estimated-total-excluding-vat-options-renewals` |
| `valuationScope` | `article-5-applicable-aggregate` |
| `currency` | `EUR` explicitly evidenced, not a dataset default |
| `lotTreatment` | `reviewed-no-derogation` |
| `noticeDuty` | `individual-award-notice-required`, primary-law and applicability evidence |
| `buyerCategory` | `central` or `subcentral`, evidenced for that buyer/date |
| `contractType` | `works`, `supplies`, or `ordinary-services`; reviewed scope, not CPV inference |
| `procurementStartDate` | exact ISO date of call dispatch/procurement commencement |
| `estimatedValue` | finite positive **decimal string**, legal estimated aggregate net value, not displayed award/contract value |
| `identityLink` | object with exact published `buyerSiret`, `contractId`, and nonempty reviewed `procedureId`, `documentVersion` |
| `thresholdRule` | object described below, with reviewed primary text and date/type/buyer applicability |

For example, a reviewed 2023 ordinary subcentral service rule would have:

```json
{
  "celex": "32021R1952",
  "amountEUR": "215000",
  "primaryTextReviewed": true,
  "dateType": "call-dispatch-or-procurement-commencement",
  "applicabilityReviewed": true
}
```

That object is only a reviewer assertion; it is not proof on its own. Neither the
helper nor booleans authenticate documents, qualifications or the legal reading.
Only EUR-Lex/Legifrance references are accepted for legal-duty/threshold facts.
Other references allow those hosts, BOAMP, TED, the Ministry data host and French
`.gouv.fr` hosts. An authentic buyer profile on another domain needs an explicitly
reviewed future allowlist revision; do not disguise it under a government URL.

Missing manifest/facts/reviewer/evidence, unknown buyer/type, unsupported date,
unreviewed threshold or unmatched identity stays **unknown**, never sampled.
Known incompatible scope or valuation basis stays **ineligible**, not a legal
exemption finding. Wrong hashes, stale row bindings, invalid numeric/date data,
duplicate JSON keys/identities, nonofficial references and manifests containing
absent identities cause a hard error. No implicit fallbacks or automatic joins.

## Reproducible selection and immutable private freeze

Fixed strata: `sources-agree`, `sources-disagree`, `single-source`,
`notice-checked`, `unknown`, taken only from published verification metadata.
They describe provenance, **not truth labels**. All eligible rows within a
stratum are ranked by SHA-256 of canonical JSON
`[protocolVersion, seed, dataset, rowId]`, with exact identity tie-breaks. Default
seed `notice-review-v1`; select at most ten per stratum. Record population and
selected counts for each stratum, including empty strata. No substitution between
strata, cherry-picking, score ranking, or replacements after reading outcomes.
Input row order does not change selection; byte changes still change the freeze.

Review unit is the **published dataset row**, not an independently established
unique contract. Shared procedures/holders and possible duplicates require
cluster-aware interpretation. Do not present an unweighted stratified percentage
as population accuracy. Any later estimate needs a separate analysis plan with
stratum weights, uncertainty, clustering, and an explicitly bounded denominator.

The canonical plan hash excludes only `planSha256`. It covers complete source
byte hashes, complete per-row canonical hashes, helper hash, manifest byte hash,
reviewed evidence hashes/references, classifications, seed, strata and selection.
No wall-clock timestamp, outcome data or score-dependent selection enters it.

Evidence, manifests and plans must be outside the repository/static server root.
Private evidence files/manifest must have no group/other permissions; evidence
directories are private. Symlinks and path traversal are rejected. Freeze directory
must be 0700 or stricter; exclusive `O_EXCL` creation produces a 0400 regular file.
An identical rerun verifies the hash and leaves bytes/mtime untouched. A differing,
writable or tampered existing freeze is refused. No ancestor permissions are
changed. Permission/hash controls are local immutability and tamper detection,
not an external timestamp or protection from the file owner/root replacing it.
A failed partial write is deliberately not silently overwritten; investigate and
use a new path if necessary.

```sh
# Initial no-evidence checkpoint; no network and no selected rows:
python3 tools/prepare-notice-accuracy-review.py

# After a qualified reviewer supplies actual evidence, use a NEW private path:
python3 tools/prepare-notice-accuracy-review.py \
  --manifest "$HOME/.cache/contract-signals/notice-accuracy-review/eligibility.json" \
  --evidence-dir "$HOME/.cache/contract-signals/notice-accuracy-review/evidence" \
  --plan "$HOME/.cache/contract-signals/notice-accuracy-review/reviewed-v1/plan.json"

python3 -m unittest discover -s tests -p 'test_prepare_notice_accuracy_review.py' -v
```

Do not change seed, frame or evidence after seeing accuracy outcomes to obtain a
more convenient sample. Record prospective amendments and use a new version/path.
The existing reviewed/sampled cases, especially `notice-checked`, have potential
prior-outcome contamination. Flag this and report separately; they cannot become
an independent blinded validation merely through a new freeze.

## Subsequent document-review and outcome protocol (not performed here)

Separate eligibility review from field-accuracy review. A qualified eligibility
reviewer should review scope without selecting on apparent field correctness.
Freeze the complete eligibility frame and manifest before opening selected field
outcomes. Keep prior exposure and reviewer independence explicit. Assistant-led
preparation and assertions are not independent expert validation.

For later acquisition, preregister exact endpoints/documents and a budget of at
most **two requests per selected row, at most 100 requests total**, no retries or
redirect following, 20-second timeout/request, 12 MiB response cap/request. Stop
on refusal/rate limits; keep failures, no replacement. This helper implements no
fetcher. Preserve URL, UTC access time, HTTP status, byte checksum, version and
response limits privately. Any additional discovery needs a prospective amendment.

Keep outcomes in a separate private artifact linked to `planSha256`, never mutate
the plan. For each row and each field record reviewer, source/document hash,
page/field locator, precise buyer/procedure/contract/lot/version matching, prior
exposure, access result and comparability. Exact identifiers must be corroborated;
a matching amount/title/name or a notice-local lot ID alone is insufficient.

Compare like with like: tax, currency, total/annual/lot/procedure scope, winning
price versus estimate/framework maximum, initial amount versus new amended total,
and conclusion/signature versus notification/publication dates. No currency
conversion, summing holders/versions, null-to-zero, ceiling allocation or priority
by plausibility. Where sources disagree, retain all variants and basis evidence.
A notice is another official declaration, not proof of signed contractual truth.
Buyer contracts and offer-analysis documents may be necessary.

Per-field outcomes: `corroborated`, `contradicted`, `unresolved-basis`,
`ambiguous-link`, `unavailable`, `nonmatching`, `not-applicable`; include the actual
values/bases privately and a separate qualified second-review status. Unavailable
or unresolved cases remain in the frozen denominator with coverage reported;
they are neither successes nor errors. A later correction does not silently
replace the frozen version. Rejected eligibility evidence warrants a recorded
protocol deviation, not an unrecorded sample replacement.

**Do not publish measured accuracy until outcomes have been reviewed and the
analysis/denominator independently checked.** This task produced zero accuracy
outcomes, no factual corrections, no corruption labels, and no accuracy rate.

## Focused tests

14 tests passed via the command above. Synthetic proof files test mechanics only:
all supported date/type/buyer threshold combinations and strict boundary;
no amount/date inference; missing fact/evidence; exact-open scope; unknown
buyer/type/identity; framework/derogation/basis exclusions; primary-rule checks;
invalid/stale/hash-invalid input; deterministic order-independent selection;
source hashes; duplicate identities/keys; exclusive read-only idempotent freeze;
tamper, public-path, insecure-directory and symlink rejection. These tests do not
verify the provisional threshold constants against legislative text.
