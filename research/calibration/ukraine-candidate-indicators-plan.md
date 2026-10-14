# Ukrainian candidate indicators: fixed list and decision rule (2026-10-13)

Research only. Written before any candidate below was computed on the verdict cohort, so the results cannot steer the list or the rule. Owner approval on 2026-10-13 ("okay do that"). No score changes without the owner.

## Data

- Cohort: `research/labels/ukraine-verdict-sweep-cohort.json.gz` (positives from the register sweep, same-buyer comparisons). Competitive procedures only, eligible finality only, as in [the points table](ukraine-verdict-sweep-points.md).
- Fields come from the cached official records (tender record, contracting-module record); no new requests.
- A candidate is *unknown* (not counted in either group) when a field it needs is missing.

## Candidates (fixed)

Award stage

| ID | Rule |
| --- | --- |
| C1 two-bidders | Exactly 2 offers on the awarded lot. |
| C2 only-qualified-bidder | 2+ offers, and every other bid on the lot was rejected (bid status unsuccessful/invalid, or an unsuccessful award to it on the lot). |
| C3 two-plus-disqualified | 2 or more better-ranked bidders disqualified before the award (`disqualifiedBefore` ≥ 2). |
| C4 short-tender-period | Tendering period (days) at or below the 25th percentile of comparison tenders of the same procedure type; unknown when that type has fewer than 10 comparison tenders. |
| C5 complaint | At least one complaint on the tender, a lot or an award. |
| C6 late-document-change | A tender-level document published or modified after the first day of the tendering period and less than 3 days before its end. |
| C7 december-award | The winning award is dated in December. |
| C8 fast-signature | Above-threshold open procedure (aboveThreshold, aboveThresholdUA, aboveThresholdEU) and the contract was signed less than 5 calendar days after the award. |

Price stage

| ID | Rule |
| --- | --- |
| C9 small-price-drop | Award value ≥ 98 % of the expected value of the lot (of the tender when there are no lots), same currency. |
| C10 just-below-threshold | Expected value of the tender between 90 % and 100 % of the open-tender threshold: UAH 1,500,000 for works, UAH 200,000 otherwise. |

Execution stage (contracting-module record; active changes only)

| ID | Rule |
| --- | --- |
| C11 price-change-amendment | A change with rationale itemPriceVariation or itemPriceChange. |
| C12 term-extension-amendment | A change with rationale durationExtension or fiscalYearExtension. |
| C13 quantity-cut-amendment | A change with rationale volumeCuts. |
| C14 early-termination | Contract terminated with amount paid below 90 % of its value. |

Supplier

| ID | Rule |
| --- | --- |
| C15 individual-supplier | Supplier identified by an individual tax number (RNOKPP), not a company code (EDRPOU). |

## Method (fixed)

Same as `tools/propose-indicator-points.py`: buyer-weighted rates, hit rate among convicted tenders first, then the comparison rate, LR shrunk toward 1 by a prior worth 10 buyers, 95 % intervals from 2,000 buyer resamples, points = 10 × log2(LR) floored at 0.

**Holdout.** Buyers are split in two by the first hex digit of SHA-256(buyer id): even → *learn*, odd → *check*. A scheme sits at one buyer, so its tenders stay on one side.

**Decision rule.** A candidate is put to the owner as a scoring proposal only if
1. its learn-half shrunk LR has a 95 % lower bound above 1, and
2. its check-half shrunk LR is above 1.

Its points are then proposed from all data. Every candidate is reported, including those that fail. With 15 candidates, about one could pass step 1 by chance; step 2 is there to catch that. A candidate with a high hit rate that fails the rule is still reported first, per the hit-rate rule, and can be shown as context.

## Implementation notes (added before the first run)

- Works (C10): `mainProcurementCategory` = works; older records without it count as works when the CPV starts with 45.
- Rejected bids (C2) also include an unsuccessful qualification of the bid (two-stage procedures).
- Complaints (C5) are counted on the tender, its awards and its qualifications.
- Early termination (C14): a contract that is not terminated is clear; a terminated one without an amount paid is unknown.

## Corrections after the first run (2026-10-13)

A code review (Sol) of the first run found implementation errors; the rules above are unchanged and the code now follows them. Both runs are reported in the results.
- C6 also counted documents dated after the end of the tendering period, and lot/item documents; it now counts only tender documents dated inside the window. A tender document without any date makes C6 unknown unless another document signals.
- C8 accepted a signature dated before the award; C9 fell back to the tender value when the awarded lot had none (now unknown).
- C2 with no bid list, C11–C13 with an active change without rationale, and C14 without a contract status are now unknown, not clear.
- C1, C3 and C15 come from the cohort row and are now known even when the tender record is not cached.

## Part 2: direct contracts (fixed 2026-10-13, before any listing was downloaded)

The sampled comparisons contain no direct contracts (the site search's date filter drops them), so direct contracting is tested against a **census** instead: for every buyer and year with an eligible convicted tender, the site search lists all of the buyer's tenders created that year, completed ones only (`status=complete`), by type: competitive (date filter), `reporting` and `negotiation`/`negotiation.quick` (type filter, located by year by bisecting the newest-first pages). Convicted tenders are removed from the census, which then serves as the comparison group; each buyer still counts once.

| ID | Rule (value = the listed tender value, UAH only) |
| --- | --- |
| D1 direct-contract | Reporting or negotiated procedure, any value. |
| D2 direct-contract-200k | Reporting or negotiated procedure with value ≥ UAH 200,000 (the open-tender threshold for goods and services). |
| D3 direct-contract-1.5m | Same, value ≥ UAH 1,500,000 (the works threshold). |

Same LR, interval, points and holdout rule as part 1. Expected weakness: direct contracts are the large majority of most buyers' tenders and prosecutions favour large amounts, so D1 mostly measures size; D2 and D3 address that.
- Implementation note (part 2, before results): buyer code 00000000 is a placeholder shared by many entities; its buyer-years have no census and its positives are left out of part 2.
- Addition (2026-10-14, before the census of the new buyer-years was downloaded): the census is repeated on the conviction cohort with linked tenders (`research/labels/ukraine-verdict-plus-linked-cohort.json.gz`), and one candidate is added: **D4 negotiated-procedure**, a `negotiation` or `negotiation.quick` procedure of any value, which is the scored `ua-direct-award` rule (18 points, editorial). Same LR, holdout and decision rule. Expected weakness: few convicted tenders used a negotiated procedure (about 14 rows), so the interval will be wide; a result that fails the rule leaves the 18 points as they are until the owner decides.

## Part 4: relative size and closeness to legal ceilings (fixed 2026-10-14, before any was computed)

Owner request (2026-10-14): fixed UAH amounts do not generalise across countries; test measures relative to the buyer and to the legal ceilings, each as a **separate** indicator next to D2 (which stays). Data already downloaded only: the census of part 2 (repeat on the linked cohort, `research/labels/ukraine-direct-contract-census-plus-linked.json.gz`, plus the cached search pages for titles) and the conviction cohort with linked tenders and its contract records. Same LR, interval, points and buyer-half holdout rule as part 1.

| ID | Rule | Data |
| --- | --- | --- |
| R1 buyer-share | The tender's value is **≥ 5 %** of the buyer's total value of completed tenders created the same year (all procedure types, UAH only, the tender included). Any procedure. Unknown without a UAH value. 1 % and 10 % reported for sensitivity only. | census |
| R2 increase-near-cap | Current contract amount above the signed amount by **≥ 90 % of the reference ceiling**, i.e. ≥ 9 % for Ukraine. Ceiling: the 10 % limit on unit-price increases (Law 922-VIII art. 41 part 5 point 2; the total amount may not rise at all except for taxes and regulated prices, per Ministry of Economy consultations). Any increase above 0 and ≥ 10 % reported for sensitivity only. Unknown without both amounts. | cohort contract records |
| R3 just-under-threshold | A direct-contract report (`reporting`) whose value is **80–100 %** (below 100 %) of the open-tender threshold that applies to it: Law 922-VIII art. 3 part 1, general buyers UAH 200,000 goods and services / 1.5 million works; buyers in special sectors (art. 2 part 1 point 4, record `kind` = `special`) UAH 1 million / 5 million. Works = CPV division 45 (row CPV, or the CPV code that starts the listed title). Unknown when buyer kind (from any cached tender record of the buyer) is not general/authority/central/social/special, or the category cannot be read. | census |

Expected weaknesses, stated in advance: R1 rewards small buyers' big purchases and may still mostly measure size; R2 is rare among competitive contracts; R3's thresholds changed little since 2016, but martial-law Resolution 1178 (from October 2022) widened direct contracting, so R3 is also reported before and from 2022 (sensitivity only). Thresholds come from secondary sources (Ministry consultations, legal journals); the primary text could not be fetched on 14 October 2026.

## Part 3: bid-rigging candidates (fixed 2026-10-13, before any was computed on any cohort)

Owner request: find new indicators, now that commercial-court judgments upholding AMCU bid-rigging decisions give a second label source ("collusion", [AMCU sweep](../../tools/sweep-ukraine-amcu-cases.py)). These candidates use the bid lists in the cached tender records; no new requests.

Scope: the awarded lot's bids (bids whose lot value points to the awarded lot; all bids when the tender has no lots), active or later rejected, from different bidder identifiers. A candidate is *unknown* when the tender record is not cached or its bids are hidden; *clear* when there are fewer bids than the rule needs.

| ID | Rule |
| --- | --- |
| K1 shared-contact | Two bidders share a telephone number (last 9 digits) or an e-mail address (lower case). |
| K2 shared-address | Two bidders share a street address in the same locality (lower case, punctuation and spaces removed). |
| K3 shared-document | Two bidders uploaded a document with the same file hash, ignoring hashes that also occur among the tender's own documents. |
| K4 close-submission | Two bids were submitted (bid `date`) less than 10 minutes apart. |
| K5 tight-bids | 3+ bids with values, and their coefficient of variation is below 3 %. |
| K6 close-runner-up | 2+ bids with values, and the second-lowest is at most 1 % above the lowest. |
| K7 all-bids-near-expected | 2+ bids with values, and every bid is at least 97 % of the lot's expected value (same currency). |
| K8 empty-cover-bid | A bid other than the winner's carries 2 documents or fewer. |

Method, holdout and decision rule as in part 1, applied to the collusion cohort (`research/labels/ukraine-amcu-cohort-full.json.gz`, one-per-case and all-tender versions). The same candidates are also computed on the conviction cohort as an independent check and reported next to them.

Expected bias, stated in advance: the Antimonopoly Committee builds its cases on exactly this kind of evidence (shared contacts, addresses, files, submission times), so K1–K4 hit rates among its cases overstate what they would catch among undetected collusion. Their LRs are an upper bound; the conviction cohort is the less selected check. The same applies to C5 complaints (complaints can start an investigation).

Personal data: contacts and addresses are compared inside one tender in memory; only the yes/no result is stored.
