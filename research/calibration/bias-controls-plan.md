# Bias controls for the strongest checks (plan, fixed 2026-10-20 before any result was computed)

The checks with the most points are the ones whose labels are most selected:

- **Buyer share** (`ua-buyer-share`, 30 points; Colombia 14): prosecutors favour large amounts, and a tender of at least 5 % of its buyer's year is usually a large tender. Its LR may partly measure what gets prosecuted.
- **K1 shared contact / K2 shared address** (AMCU cohort, 36 and 29 decision points, not scored): the Antimonopoly Committee finds cartels through exactly this evidence ([candidate plan](ukraine-candidate-indicators-plan.md), expected bias). Among court convictions K1 fires on 1 of 249 tenders.

Decision rule unchanged (owner, 2026-10-20): points = 10 × log2 of the LR at the 25th bootstrap percentile, at least 10 labelled buyers. The controlled estimate replaces the unadjusted one as the basis for points; less certainty means fewer points.

## 1. Buyer share against size (`tools/ukraine-buyer-share-size.py`)

Same rows as R1 (convicted tenders, verdict-plus-linked cohort, against the census of the same buyer-years). Value bands in UAH: < 50k, 50k–200k, 200k–1M, 1M–5M, 5M–20M, ≥ 20M.

- **A, size-standardised (decision basis):** comparison tenders reweighted so their band mix matches the convicted tenders' (weight = share among convicted / share among comparisons, normalised per buyer so each buyer still counts once). Reported also per buyer half.
- **B, within band:** R1 LR inside each band with at least 10 convicted buyers.
- **C, size alone:** "value ≥ V", V the census value whose convicted hit rate is closest to R1's; what a pure size check would score, for comparison.

Reading: if A stays well above 1 and B is above 1 in most bands, buyer share carries evidence beyond size and keeps the A points; if A falls to about 1, it is a size proxy and its points go.

## 2. K1 / K2 against detection (`tools/ukraine-amcu-evidence-split.py`)

Each AMCU case's judgment texts (cached) are classified for the evidence cited: shared telephone or e-mail (contact), shared address, same IP address. Classifier validated on at least 40 hand-read cases before use.

- **Decision basis:** K1 and K2 LR on AMCU cases whose judgments cite **none** of contact, address or IP (cases found by other means). Also reported: cases citing them (expected to be inflated) and the conviction cohort (already measured).
- Same split for K3 shared document, K4 close submission and R1-related parties where the features exist, since the AMCU also relies on file metadata and submission times.

Reading: the "none cited" estimate is still an upper bound (a judgment may omit evidence the decision used), so it is the most the AMCU cohort can support.
