# Cross-country test matrix

Owner rule (2026-10-24): **every check is tested in every country that has labels and the needed fields**, whatever
country it came from. A check that works in Korea may work in Ukraine and the reverse; one that failed in one country
may work in another. Each country is still tested on its own labels, and one country's result never moves another
country's points ([docs/indicators.md](../../docs/indicators.md)).

Rows are concepts; cells give the country's own ID and its result. Letter IDs are local to each country's plan and
collide across countries (Ukraine's K1–K8 are collusion checks, Korea's K1–K6 Korean-law checks; Ukraine uses R1–R3 for
both size and related-party checks), so always read the ID together with its column.

Legend: **pts** earned points by that country's decision rule · **no** tested, no points · **~** mixed (passes in some
label sets only, or passes but not valid/adopted) · **see** tested, result in the linked file · **·** not tested yet,
data available or likely · **–** no data (field missing; say which when testing).

Label sets: Korea = KFTC bid rigging (collusion), court convictions, Board of Audit findings (separate families,
[korea-labels-plan.md](korea-labels-plan.md)); Ukraine = court convictions and AMCU collusion decisions
([ukraine-candidate-indicators.md](ukraine-candidate-indicators.md), `ukraine-amcu-*`); Romania = Competition Council
bid-rigging decisions; Colombia = convictions ([romania-colombia-results-2026-10-15-audit.md](romania-colombia-results-2026-10-15-audit.md)).
Korea results are the collusion family unless noted ([korea-collusion-results.md](korea-collusion-results.md)).

## Competition and procedure

| Concept | Korea | Ukraine | Romania | Colombia |
|---|---|---|---|---|
| Single offer | B1 no | `ua-single-offer` ~ (1 point after calibration) | no | – (no offers table) |
| Two or three bids | B2 pts; UA-C1 exactly two **pts (15–16, uncontrolled)** | C1 two-bidders no | · | – |
| Award close to the reserve / expected price | K6 pts; UA-C9 ≥ 98 % pts (6–7) | C9 small-price-drop no | · | · |
| Restricted or invited competition | K5 pts (courts too) | · | · | · |
| Direct / private contract | G2 no; UA-D2 no | D1 no; D2 ≥ UAH 200k pts | no | no |
| Repeated direct awards to one supplier | U2 no | · | no | no |
| Better-ranked bidders disqualified | B6 no | C3 ~ | · | – |
| Short notice or tender period | N6 no | C4 no | · | · |
| Just below a threshold | K3 no, N7 no | C10 no; R3 ~ (not valid) | · | · |
| Split contracts | K4 no | · | · | · |
| Complaint filed | – | C5 no | · | · |
| Late change of tender documents | – | C6 no | · | · |
| Fast signature after award | · | C8 no | · | · |
| Only one valid bid among several | UA-C2 **pts (10–13, uncontrolled)** | C2 only-qualified-bidder no | · | – |


## Bids and bidders (collusion screens)

| Concept | Korea | Ukraine (AMCU labels) | Romania | Colombia |
|---|---|---|---|---|
| Low bid dispersion / tight bids | B4 pts (live; ~0 under controls); UA-K5 CV < 3 % no | K5 tight-bids see | · | – |
| Large first gap / close runner-up | B5 pts (stopgap; ≤ 2 controlled) | K6 close-runner-up see | · | – |
| All bids near the expected value | · | K7 see | · | – |
| Bids just above the lower limit | B3 no | · | · | – |
| Exact floor hit | B8 no | · | · | – |
| Bids submitted close in time | B7 no (0–2) | K4 close-submission see | · | – |
| Shared CEO / contact / address / owner | B9 shared CEO no | K1 contact, K2 address see; R1 shared owner ~ (AMCU only) | · | – |
| Shared documents | – | K3 see | – | – |
| Empty cover bid | – | K8 see | – | – |
| Rotation of winners | B10 no | · | · | – |
| Repeated quote pair | B11 no | · | · | – |

## Size, concentration and suppliers

| Concept | Korea | Ukraine | Romania | Colombia |
|---|---|---|---|---|
| Buyer share ≥ 5 % of yearly procurement | G3 pts (size-like) | R1 pts | ~ (passes; not adopted, framework ceilings) | pts |
| Supplier dependence ≥ 25 % | N4 pts | · | ~ (passes; not adopted) | no |
| Concentration (one supplier wins most) | G4 pts | `ua-concentration` · | no | no |
| First-time supplier | N5 no (audit pilot 2–6) | · | no | no |
| Individual (sole-trader) supplier | UA-C15 no | C15 no | · | · |
| Young winner (registered < 1 year) | · (firm-info founding date) | R3 young-winner no | · | · |
| Buyer official owns the winner | – | R2 official-owner no (never fires) | – | – |

## Timing and execution

| Concept | Korea | Ukraine | Romania | Colombia |
|---|---|---|---|---|
| December signature | N1 no | C7 no | no | no |
| Weekend signature | N2 no | · | no | no |
| Three or more amendments | G5 no (2.6 one per case earlier) | `ua-contract-amendments` · | – | – |
| Amount increase > 20 % | G6 no; UA-C11 any increase no | C11 price change no; R2 near the 10 % cap no | – | · |
| Term extension | – (`period` empty in ~97 % of versions) | C12 pts | – | `secop2-term-extension` · |
| Quantity cut | UA-C13 amount cut no | C13 no | – | – |
| Early termination | · | C14 no | – | · |
| Published long after the contract | – | – | `late-publication` · | – |

## Round numbers and digits (A, owner idea 2026-10-24; definitions in [untested-checks-plan.md](untested-checks-plan.md))

| Concept | Korea | Ukraine | Romania | Colombia |
|---|---|---|---|---|
| A1 round-percentage increase | no (too rare) | · | – | · |
| A2 same step repeated | no (2 tenders) | · | – | · |
| A3/A4 round contract amount | no | · | · | · |
| A5/A6 round budget | no (within buyer: ×1.07 cartel, ×0.2–0.5 courts) | · (`value.amount`) | · | · |
| A7 Benford deviation per supplier | no (labelled firms deviate less) | · | · | · |

## Next tests, by expected value

1. Ukraine: K6 award close to expected price is already C9 (no); test B2-style "2–3 bids" on court labels, the A
   series (expected values set by hand), K5-like restricted procedures if Prozorro has one, N4/N5 supplier checks.
2. Korea: done 2026-10-24 for C1, C2, C9, C11, C13, C15, D2, K5 (`korea-collusion-results.md`); C1/C2 need the
   bidder-count controls; still open: R3 young winner (firm-info API), C12 (needs another period source).
   Ukraine next: Korea's winners B2-style counts are C1 there (no); test K5 restricted procedures, B5 gap, A series.
3. Romania and Colombia: B2/B4/B5/K6 need bids or reserve prices (SEAP offer counts for Romania), the A series.
4. United States, once labels exist: every row with data.
