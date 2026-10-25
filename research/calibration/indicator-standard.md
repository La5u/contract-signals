# Standard indicator definitions (owner decision 2026-10-24)

Every indicator is **universal** (tested in every country that has labels and the needed fields, whatever country it
came from; status in [cross-country-matrix.md](cross-country-matrix.md)) and **standardised**: one definition for all
countries, with any arbitrary number written as a parameter X that is set per country. Points stay per country, from
that country's own labels ([docs/indicators.md](../../docs/indicators.md)).

## Three kinds of indicator (owner decision 2026-10-24)

Every standard indicator is one of three kinds; the kind decides what may differ between countries.

1. **Count or category (no X).** The definition is identical everywhere: number of offers, December or weekend
   signature, individual supplier, amendment count, related bidders. Only the points per bin or category differ by
   country, from that country's labels.
2. **Legal threshold (legal X).** The rule refers to a limit set by each country's law (direct-contract limit,
   open-tender threshold, amendment cap, minimum notice period, publication deadline). X is read from the law and
   cited, never tuned on labels; a country without such a limit has the indicator out of scope with that reason.
3. **Continuous measure (bins).** The measure is standard (award ÷ reserve price, buyer share, price change, bid gap,
   notice days); each country's bins come from its own comparison data (quantiles of all records, placed without the
   labels), and each bin gets points from the labels. A fixed X (e.g. 95 %, 5 %, 20 %) is a former single cut-off of
   such a measure and is replaced by the bins.

Label-tuned X (step 3 below) is a last resort for kind 3 only, when bins cannot be estimated.

## How a parameter X is set (in this order)

1. **Legal X.** Where the country's law fixes a limit (small-value direct-contract limit, amendment cap, minimum notice
   period, publication deadline), X is that limit, read from the law, never tuned.
2. **Distributional bins.** For continuous measures, the measure is standard and the bins are the country's own
   comparison quantiles (all records, labels not used to place them); each bin gets points from the labels. The number
   of bins is chosen by cross-validation holding out whole cases; with few labels, fewer bins.
3. **Label-tuned X (last resort).** Only with enough labelled cases (at least the ≥ 10 labelled buyers of the decision
   rule, per held-out fold), chosen by cross-validation over whole cases, reported with its uncertainty; with fewer
   labels the common default X is used instead of a country-specific one.

Natural counts and categories have no X: they are identical everywhere.

## Bins and overlap

A graded indicator is one variable with mutually exclusive bins; a record falls in exactly one bin and gets that bin's
points (never the sum of several bins). Bins may be counter-signals (a likelihood ratio below 1 gives 0 points under
the current rule). Checks that measure the same thing are merged into one graded indicator rather than kept as
overlapping yes/no checks (B1, B2 and Ukraine's C1 become one bid-count indicator).

## Catalogue (first version; IDs are standard and replace country-local letters over time)

| Standard ID | Kind | Measure | Parameter | Unit and notes | Local IDs so far |
|---|---|---|---|---|---|
| BID-COUNT | count | Number of offers submitted on the awarded lot | none; bins 1, 2, 3, 4–5, 6–10, 11+ | offers per lot; framework mini-competitions and e-auction rounds counted as their own procedures | KR B1, B2; UA C1, `ua-single-offer`; RO single offer |
| BID-VALID | category | Offers rejected or disqualified on the awarded lot | none; categories: only one valid of 2+; 1+ better-ranked offer rejected; 2+ better-ranked rejected | as BID-COUNT | KR B6; UA C2, C3, `ua-better-bid-disqualified` |
| PRICE-RATIO | continuous | Award ÷ reserve or expected price | distributional bins | the country's reference price (KR reserve price 예정가격; UA expected value) | KR K6 (≥ 95 %); UA C9 (≥ 98 %), KR UA-C9 |
| BID-GAP | continuous | Gap between lowest and second offer, relative to the spread of the others | distributional bins, within BID-COUNT bin | ≥ 3 valid offers | KR B5; UA K6 |
| BID-SPREAD | continuous | Coefficient of variation of valid offers | distributional bins, within BID-COUNT bin | ≥ 3 valid offers | KR B4; UA K5 |
| DIRECT | legal + continuous (amount) | Award without competition | legal X: the country's direct-award routes; amount bins | | KR G2, UA-D2; UA D1–D4; RO, CO direct award |
| NEAR-LIMIT | legal | Amount just under a legal limit | legal X (each limit) | band width distributional | KR K3, N7; UA C10, R3 |
| BUYER-SHARE | continuous | Contract ÷ buyer's yearly total | distributional bins | size-like: value-band control | KR G3; UA R1; RO, CO buyer share |
| SUPPLIER-DEPENDENCE | continuous | Supplier's share of the buyer's yearly total | distributional bins | | KR N4; RO, CO |
| CONCENTRATION | continuous | Supplier's share of the buyer's awards in a business type | distributional bins | | KR G4; `*-concentration` |
| NEW-SUPPLIER | category (X = 3 years, data window) | No award between buyer and supplier in the previous X years | X = 3 (default) | needs X earlier years | KR N5; RO, CO |
| AMEND-COUNT | count | Number of amendments | none; bins 0, 1, 2, 3–4, 5+ | within the same window | KR G5; UA `ua-contract-amendments` |
| AMEND-PRICE | continuous (+ A1 category) | Price change after award, % of the original | distributional bins; plus A1 round percentage | | KR G6, UA-C11, A1, A2; UA C11, R2 |
| AMEND-CUT | category | Price or quantity cut after award | none | | KR UA-C13; UA C13 |
| TERM-EXTENSION | category + continuous | Term extended after award | none (any), plus distributional bins of the extension | | UA C12; CO `secop2-term-extension` |
| NOTICE-PERIOD | legal + continuous | Days from notice to bid deadline | legal X (minimum) and distributional bins | | KR N6; UA C4; FR `short-bidding-period` |
| SIGN-DATE | category | December / weekend signature | none | | KR N1, N2; UA C7 |
| SUPPLIER-TYPE | category | Individual (sole trader) supplier | none | | KR UA-C15; UA C15 |
| SUPPLIER-AGE | continuous | Supplier registered less than X days before the award | distributional bins | registry needed | UA related-parties R3 |
| RELATED-BIDDERS | category | Bidders share an owner, CEO, contact, address or document | none (categories) | registry or bid documents | KR B9; UA K1–K3, R1 |
| ROUND-NUMBERS | category | Round budget, amount or percentage; Benford deviation per supplier | significant digits (none) | | A1–A7 ([untested-checks-plan.md](untested-checks-plan.md)) |
| LATE-PUBLICATION | legal + continuous | Publication delay after signature | legal X (deadline) and buyer baseline | | `late-publication` |

Not yet standardised (one country so far): bid rotation (KR B10), repeated quote pair (KR B11), exact floor hit (KR
B8), complaints (UA C5), late document change (UA C6), fast signature (UA C8), early termination (UA C14), split
contracts (KR K4).

## Legal X per country (kind 2; cited values only, gaps to be read from the law, never guessed)

| Threshold | Korea | Ukraine | Romania | Colombia |
|---|---|---|---|---|
| Small-value direct contract (goods/services) | 추정가격 20,000,000 KRW (22,000,000 with VAT; as cited in the data: 국가계약법 제26조제1항5호가2목, 지방계약법 제25조제1항5호나목); `SMALL_LIMIT` | – (see open-tender threshold) | to read | to read |
| Open-tender threshold | – | UAH 200,000 goods/services, UAH 1,500,000 works (Law 922-VIII; plan C10, D2, D3) | to read | to read |
| Amendment cap | none found for total amounts | 10 % on unit prices (Law 922-VIII art. 41 part 5 point 2; plan R2) | to read | to read |
| Minimum notice period | works 7 / 15 / 40 days by estimated price < 1 bn / < 5 bn / above; goods and services 7 (N6, `notice_checks`) | to read | to read | to read |
| Notice-price breakpoints (just below) | 100 M, 200 M, 300 M, 1 bn, 5 bn, 10 bn, 20 bn, 30 bn KRW (`NOTICE_THRESHOLDS`, N7) | as open-tender threshold | to read | to read |

## Per-country curves now; global pooling deferred (owner 2026-10-24)

Continuous indicators (kind 3) get a full curve per country: rate and likelihood ratio per bin, smoothed (bins or a
monotone fit), the best cut-off found by cross-validation over whole held-out cases and reported with its uncertainty;
graded points come from the curve. This is a main goal, not a last resort. A global starting curve with partial
pooling (empirical Bayes, within one label family and one standard definition) is **deferred**: with 3–4 labelled
countries the between-country variance cannot be estimated and Korea's label count would dominate. Trigger to revisit:
a label family with at least 5 countries, each with at least 10 labelled buyers. Until then each country's points come
only from its own labels (docs/indicators.md, unchanged); curves are compared side by side in
[cross-country-matrix.md](cross-country-matrix.md). First country: Korea.
