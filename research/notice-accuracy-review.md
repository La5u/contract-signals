# Notice-eligible accuracy review — preregistration protocol v1

## Finding and boundary

Preparation only; no accuracy outcomes or rate. The earlier 90-row sample's **76 unlinked rows** cannot be classified as accurate, inaccurate or notice-exempt.

French snapshots contain **5,286 rows (2,289 cities; 2,997 history)**. **1,571** have exact procedure `Appel d'offres ouvert`. Labels, declared amounts, CPV, buyer names/SIRETs, notification dates and notice presence do not establish legal scope, estimates, start dates or notice duties. `nature: Marché` does not classify works/supplies/services.

No-manifest freeze:

- **0 eligible/selected**;
- **1,726 unknown**: 1,571 open rows without eligibility evidence plus 155 missing procedure labels;
- **3,560 outside narrow scope**: other labels, without determining their notice obligations.

Original checkpoint: `~/.cache/contract-signals/notice-accuracy-review/v1/plan.json`. Later CPV-only corrections leave counts unchanged; current checkpoint: `~/.cache/contract-signals/notice-accuracy-review/v2-cpv/plan.json`. Use `--plan` with that path for current rows. Reviewed evidence requires a new freeze path; do not overwrite v1. Plans retain canonical hashes and input/evidence bindings for local tamper detection, not an external timestamp.

## Legal evidence still missing

The attempted official sources were [Directive 2014/24/EU](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32014L0024), [Delegated Regulation 2019/1828](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32019R1828), [Delegated Regulation 2021/1952](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32021R1952), [Delegated Regulation 2023/2495](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R2495). All returned **HTTP 202 WAF challenges**, not legislation. No primary provisions were verified; do not bypass or attest challenge pages as law. Private responses: `~/.cache/contract-signals/notice-accuracy-legal/20261010T234020Z/`.

Pending primary/French applicability review: Directive **Articles 1–4** scope, **5** valuation, **26–27** open procedure, **50–52** notices, **74–76/Annex XIV** specific services; threshold regulations **Articles 1–2**.

| Start-date period | Works | Central supplies/ordinary services | Subcentral supplies/ordinary services |
| --- | ---: | ---: | ---: |
| 2020–2021 | EUR 5,350,000 | EUR 139,000 | EUR 214,000 |
| 2022–2023 | EUR 5,382,000 | EUR 140,000 | EUR 215,000 |
| 2024–2025 | EUR 5,538,000 | EUR 143,000 | EUR 221,000 |

These constants are provisional consistency checks. Admission requires reviewed primary-law evidence for threshold/date/application and individual notice duty. Unsupported years, utilities, concessions, defence, mixed classifications, Annex XIV services, framework call-offs and DPS are outside v1; extensions need a reviewed/versioned protocol.

Use call dispatch/procurement commencement, not award year. Review Article 5 estimates, options, renewals, aggregate lots, special valuation, small-lot derogation and exclusions. Notice duty concerns dispatch, not just publication. Do not infer estimates by multiplying annual prices or using ceilings. The study requires **strictly above** threshold; legal scope generally includes equality, so excluding equality is a study boundary, not exemption.

## Helper and manifest

`tools/prepare-notice-accuracy-review.py` reads both snapshots and an optional private manifest offline. It does not search notices, match suppliers/prices or repair amounts.

Manifest: exact `schemaVersion: notice-accuracy-review-v1`, `records` array. Each record binds `dataset` (e.g. `data/decp-cities.json`), `rowId`, canonical complete `rowSha256`, `reviewedBy`, `reviewedOn`, and `facts`. Each fact has `value` and nonempty `evidence`: private file `path`, byte `sha256`, official HTTPS `url`, precise `locator`. One file may support several facts.

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

`thresholdRule` example for 2023 ordinary subcentral services:

```json
{
  "celex": "32021R1952",
  "amountEUR": "215000",
  "primaryTextReviewed": true,
  "dateType": "call-dispatch-or-procurement-commencement",
  "applicabilityReviewed": true
}
```

Assertions/booleans do not authenticate documents or expertise. Legal facts accept only EUR-Lex/Legifrance; other facts also accept BOAMP, TED, Ministry data and French `.gouv.fr`. Other buyer-profile domains need a reviewed allowlist revision.

- Missing facts/reviewer/evidence, unknown buyer/type, unsupported dates, unreviewed thresholds or unmatched identity → **unknown**, unsampled.
- Known incompatible scope/basis → **ineligible**, not legally exempt.
- Wrong/stale hashes, invalid dates/numbers, duplicate JSON keys/identities, nonofficial URLs or absent identities → hard error. No automatic joins/fallbacks.

## Selection and private freeze

Fixed published-provenance strata: `sources-agree`, `sources-disagree`, `single-source`, `notice-checked`, `unknown`. They are not truth labels. Rank eligible rows by SHA-256 of canonical `[protocolVersion, seed, dataset, rowId]`, exact-identity tie-break; default seed **notice-review-v1**, at most **ten per stratum**. Record empty strata too. No substitutions, score ranking or post-outcome replacements; input order does not affect selection.

Review unit is a published row, not a proven unique contract. Any accuracy estimate needs stratum weights, uncertainty, clustering and a bounded denominator; an unweighted percentage is unsuitable. Prior exposure, especially notice-checked cases, must be reported separately from independent blinded validation.

Evidence/manifests/plans stay outside repository/server roots. Directories **0700**, evidence/manifest without group/other permissions, exclusive freeze **0400**. Reject symlinks/traversal; identical reruns leave bytes/mtime unchanged, differing/writable/tampered freezes fail. Do not silently overwrite partial writes; investigate and use a new path.

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

Freeze the complete eligibility frame before field outcomes. A qualified reviewer should assess scope without selecting on apparent accuracy. Prospective changes to seed/frame/evidence need a recorded amendment and new version/path.

## Later acquisition and outcomes

Not performed here. Preregister exact endpoints/documents, at most **two requests per selected row/100 total**, **20-second timeout**, **12 MiB cap**, no retries/redirects. Stop on refusal/rate limit; retain failures without replacement. Additional discovery needs prospective amendment. This helper has no fetcher.

Separate outcomes from the immutable plan, linked by `planSha256`. Record reviewer, document/hash/URL/UTC/status/version, page/field, exact buyer/procedure/contract/lot linkage, prior exposure, access and comparability. Amount/title/name or notice-local lot ID alone is insufficient.

Compare tax/currency, annual/total/lot/procedure scope, tender/estimate/ceiling, initial/amended totals, and conclusion/signature/notification/publication dates. Retain conflicting variants; no conversions, holder/version sums, null-to-zero or ceiling allocation. Buyer contracts/offer-analysis documents may be needed beyond notice declarations.

Per-field outcomes: `corroborated`, `contradicted`, `unresolved-basis`, `ambiguous-link`, `unavailable`, `nonmatching`, `not-applicable`, plus actual private values/bases and qualified second-review status. Unavailable/unresolved rows stay in denominator with coverage, neither success nor error. Corrections preserve frozen versions; rejected eligibility requires recorded deviation, not replacement.

**Publish no measured accuracy until outcomes and analysis/denominator are independently reviewed.** Assistant preparation is not expert validation.

## Validation

**14 tests passed**: thresholds/strict boundaries, no inference, missing evidence, exact-open scope, exclusions, primary-rule checks, invalid/stale/hash/duplicate input, deterministic selection and private immutable freezes. Synthetic files test mechanics, not provisional legal constants.
