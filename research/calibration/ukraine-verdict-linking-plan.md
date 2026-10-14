# Linking verdicts without a tender ID to Prozorro tenders: fixed rules (2026-10-13)

Research only. Written before any verdict was linked. Owner request: the 39,797 verdict texts already downloaded hold more than the 235 that quote a tender ID ("analyze more … names, firms, addresses, anything"). No score changes without the owner.

## What the texts hold (measured 2026-10-13, all categories)

- 39,797 verdicts read (official crimes, art. 369 bribe offers, art. 190 fraud).
- 956 mention public procurement (Prozorro, public procurement, tender, open bidding, procurement procedure or contract); 235 of them quote a tender ID.
- 509 are not acquittals and quote no tender ID; 231 of those give an 8-digit company code (ЄДРПОУ) of the buyer or supplier. Most art. 190 fraud (19,431) and art. 369 (9,028) verdicts concern other things (phone scams, sales, bribes to police) and mention no procurement.
- Personal names are redacted (ОСОБА_N); company names and codes are not.

## Step 1: extraction (model review of local texts)

The reviewer reads each of the 509 texts and returns, for every procurement the verdict describes: buyer code, supplier code, contract number, contract date, year of the procurement, amount (UAH), CPV code, a short subject, whether it ran through Prozorro, and, as in the earlier review, outcome, the procurement's role (scheme / context), official involvement and stage. Only codes, numbers and dates are kept; no names of people.

## Step 2: matching (fixed)

For each extracted procurement of 2016 or later with a buyer code and a year:
1. List the buyer's tenders for that year (and the year before, when the contract date is in January–March) through the site search, up to 10 pages.
2. Shortlist tenders whose listed value is within ±25 % of the amount, or whose title holds the same CPV code (first 5 digits); at most 15 per procurement, nearest value first.
3. Fetch each shortlisted tender record and compare it with the verdict:
   - **S** supplier: a contract's or active award's supplier code equals the verdict's supplier code;
   - **N** contract number: equal after removing spaces, "№" and leading zeros;
   - **D** date: a contract signed within 7 days of the verdict's contract date;
   - **A** amount: a contract or award value within 1 % of the verdict's amount.
4. A tender is a **match** when it has S with one of N, D or A; or N with D; or N with A. The link is accepted only when exactly one tender matches; two or more matches, or none, leave the verdict unlinked.

A linked tender then goes through the same rules as quoted tenders: label from the review (scheme + conviction → corruption or fraud), finality as in the sweep, cohort and comparisons as before.

## Reporting

Linked tenders are flagged `linked: buyer code` and every result is reported with and without them. A spot check of 20 links (verdict passage next to the tender record) is reported with the results.

## Implementation notes (before the first match)

- Tool: `tools/link-ukraine-verdict-tenders.py` (match → finality → labels); own request cache `~/.cache/contract-signals/labels/verdict-link`.
- Only procurements that could become labels are searched (conviction, plea or mixed outcome; role scheme; not clearly outside Prozorro); the rest are counted by reason.
- Listing: all procedure types, as in the direct-contract census (competitive by tender date, direct and negotiated by type).
- When a verdict gives neither amount nor CPV, the shortlist takes tenders whose tendering ended within 180 days before the contract date.
- Amendment after the first extraction batch, before any match (2026-10-13): many verdicts name the buyer but print no code. The extraction now also returns buyer and supplier organisation names. A buyer without a code is resolved by name: the site search by name; hits whose buyer name equals the verdict's (lower case, quotes, punctuation and spaces removed); the code is taken from up to 3 such tenders' records and accepted only when they all agree. Evidence S also counts when the supplier's name in the record equals the verdict's supplier name (same normalisation). Batches reviewed before the change are reviewed again.

## Part B: bid-rigging judgments without a tender ID (fixed 2026-10-13, before any was linked)

945 commercial-court cases on AMCU bid-rigging decisions quote no tender ID (no judgment of the case does). Their texts name the buyer and the colluding bidders, usually with company codes. One judgment per case (the one with the most company codes) is reviewed by the model, which returns per tender described: buyer code or name, the bidders' codes, year, subject, CPV, expected value, and whether the case's AMCU decision is described as standing (the disposition itself comes from the automatic reading of the case's highest, latest judgment, as for quoted tenders).

Matching: the buyer's tenders of that year are listed as in part A and shortlisted by value (±25 %) or CPV; a tender **matches** when at least two of the named bidders' codes are among its bidders. A link is kept only when exactly one tender matches for that description, and only for cases whose decision stands. Linked tenders are flagged `linked: bidder codes` and reported with and without them.

Amendment to part B before any match (2026-10-13): the judgments seldom print the expected value or CPV (3 and 27 of the first 442 descriptions), so the value/CPV shortlist would be empty for almost all. When a description gives neither, the shortlist is the buyer-year's competitive tenders (open and other procedures with bids), nearest the printed date first, at most 40. The match rule is unchanged (at least two named bidder codes among the tender's bidders, exactly one matching tender); the wider shortlist only raises the chance of two matches, which leaves the description unlinked.

## Results (2026-10-14)

- Part A: 1,180 extracted procurements; 445 could be searched (the rest: not a label 698, no buyer 26, before 2016 11). Linked 116 (106 distinct tenders, 61 verdicts), ambiguous 4, no match 139, buyer name not resolved 186. Evidence: N+D+A 73, N+D+A+S 32, N+D+S 5, other pairs 6. Labels: 83 procurement fraud, 33 corruption. One verdict (107092765, a supplier selling overpriced sensors to 47 prisons) gives 47 links, so results are also reported one tender per court case.
- Spot check of 20 links (seeded order, at most 2 from that verdict): all 20 correct — buyer, contract number and signing date agree in every pair, supplier where the verdict names one; two differ in amount only because the record holds the amended value.
- Part B: about 1,050 tender descriptions from 762 cases; 17 could be searched (most are pre-Prozorro bulletin tenders, Prozorro.Sale auctions, or fine-collection suits naming no tender); 2 tenders linked (cases 924/978/17 and 926/368/20).
