# France: indicator points from court findings — plan (drafted 2026-10-28, before any rate was computed)

Owner request (2026-10-28): calibrate France first, because all its points are editorial (12 single offer, 18 direct
award, 8–30 graduated). Same method as Korea ([korea-labels-plan.md](korea-labels-plan.md)), with the decision rule
of 2026-10-20, one range per continuous indicator (2026-10-25) and every standard indicator tested
([indicator-standard.md](indicator-standard.md)). Research only; no score, weight or dataset change without the owner.

Seen before this plan: counts of fetched rulings by court-reported outcome (below) and by Judilibre query; no
ruling has been read by a model, none has been linked, no rate has been computed.

## Labels

Three families, never pooled with one another. Each is rated alone with the decision rule.

| Family | Source | Finding |
| --- | --- | --- |
| **Irregular award** | Administrative courts' open data (opendata.justice-administrative.fr: tribunals from 2022-06, appeal courts from 2022-03, Conseil d'État from 2021-06); `tools/fetch-france-admin-rulings.py`, 20,900 procurement rulings kept | court finds the award of a named contract irregular (below) |
| **Criminal** | Judilibre (Cour de cassation, appeal courts, judicial tribunals; PISTE API); `tools/fetch-france-judilibre.py`, ~7,000 hits | conviction for favouritism (art. 432-14 code pénal) or its receipt, corruption (432-11, 433-1), influence peddling, unlawful taking of interest (432-12), misappropriation (432-15) or bid rigging (L. 420-6 code de commerce), tied to a named public contract |
| **Collusion** | Autorité de la concurrence decisions | not fetched yet; planned under the same rules as Korea's collusion family, added here before any rate is computed |

Regional audit chambers' reports (chambres régionales des comptes) would form an audit family as in Korea; not fetched,
out of this plan.

### Irregular-award family

A ruling is a **label** when the court holds that the award procedure of a specific contract broke the publicity or
competition rules of the code de la commande publique (or the pre-2019 codes and ordinances), in any of these actions:
pre-contractual summary challenge (L. 551-1, procedure annulled or ordered to be redone), contractual summary challenge
(L. 551-13), third-party challenge to validity (Tarn-et-Garonne; contract annulled, terminated or regularised), prefect
referral, or damages to an ousted bidder for an irregular award. The finding counts whatever the remedy (an
irregularity found but with no harm to the claimant still labels the contract).

Outcome classes, from the reader:

| Class | Meaning | Use |
| --- | --- | --- |
| A1 steering | criteria or specifications tailored to a firm, unequal information or negotiation, conflict of interest or impartiality breach, an offer accepted that should have been rejected | label; also reported alone (closest to corruption) |
| A2 no competition | no publicity or competition where required, wrong procedure, unlawful splitting, unlawful direct award or amendment that is in effect a new contract | label; also reported alone |
| A3 procedural | faulty offer analysis, criteria weighting or method not disclosed, abnormally low offer not examined, insufficient reasons given to the losing bidder | label |
| C challenged, not irregular | award challenged, court finds no irregularity | not a label; **second comparison** (below) |
| X other | contract execution disputes (payment, penalties, final account, termination, works damage), inadmissible, withdrawn, no need to rule, expert appointed | excluded |

Court-reported outcome ("Solution") is only a pre-filter for reading order, not a label: of 20,900 rulings,
6,382 are full or partial wins for the claimant (Satisfaction totale 2,601, partielle 3,781) and 9,452 are rejections;
many wins are execution disputes (class X). Reading order: wins first, then rejections (for class C and for
irregularities found in a ruling that rejects the claim on other grounds), then the rest.

**Finality.** The open data hold every published ruling of all three levels from 2022, so an appeal is looked up in it
(same parties, contract and earlier ruling's number cited). Final: Conseil d'État ruling, appeal ruling with no
cassation found after 6 months, or first-instance ruling with no appeal found after 6 months (summary orders: 15 days
for cassation, so 6 months is ample). An irregularity overturned on appeal is excluded. A finding with an appeal pending
gets weight p, read from the Conseil d'État's annual activity report (share of tribunal rulings upheld on appeal, contract
disputes if reported, else all matters); until that figure is read, **p = 0.91** (the Korean weight) with sensitivity 0
and 1. A weight w counts w among labels and 1 − w among comparisons, as in Korea.

**Contracts that never existed.** A pre-contractual challenge that annuls the procedure before signature leaves no
contract; the label then attaches to the relaunched procedure's contract only if the ruling or a later ruling names it.
Otherwise the case is listed as unlinkable, not guessed.

### Criminal family

Label: a conviction (any count) of an official, elected member, supplier or intermediary for one of the offences above,
where the ruling ties the offence to a specific public contract or tender. Acquittal on those counts, or a conviction
quashed by the Cour de cassation and not restored on remand, is excluded. One case = one set of facts: the trial,
appeal and cassation rulings of the same case count once, at the most final level found.

Finality as for administrative rulings, but within Judilibre: an appeal ruling with no cassation ruling found after
6 months is final; a cassation appeal dismissed confirms it. Pending weight p from the Cour de cassation's published
statistics (share of criminal appeals in cassation that are dismissed); until read, 0.91 with sensitivity 0 and 1.

Expected, stated in advance: Judilibre pseudonymises natural persons and the facts are often years older than the
ruling, while DECP starts in 2019 (sparsely before 2020). Few criminal cases will link; if fewer than 10 buyers link,
the family gets no French points and is reported only.

## Contracts and linking

Contracts: the consolidated national DECP (data.gouv.fr dataset 608c055b35eb4e6ee20eb325, tabular, `decp.parquet`;
copy of 2026-10-04 in `~/.cache/contract-signals/decp-national/`, refreshed before linking). Only contracts above the
DECP publication threshold are in it; the threshold in force each year is read from the code and stated in the results.

Linking a ruling to a DECP contract requires the buyer and **two** further agreements, accepted only when exactly one
contract (or lot) is left:

- buyer: the named public body resolved to its SIRET/SIREN through DECP buyer names (and the SIRENE register where DECP
  names are ambiguous); a département or region name alone does not count;
- object: ≥ 30 % shared character bigrams between the ruling's contract description and DECP `objet` (same rule as Korea);
- amount: equal to the euro, allowing excl./incl. VAT (× 1.2, or the stated rate);
- date: DECP `dateNotification` within 90 days of the award or signature date given in the ruling;
- winner: company name, or SIREN where printed, matching `titulaire_id`.

Lot-level when the ruling names the lot. Unresolved and ambiguous cases are listed with the reason. A hand check of 20
random accepted links is reported.

## Comparisons

1. **Main:** DECP contracts of the same buyer (SIRET; SIREN as sensitivity) notified in the same year, excluding
   labelled ones. Unlabelled, not proven clean. Buyer-weighted rates.
2. **Litigated (irregular-award family only):** contracts whose award was challenged and found regular (class C),
   linked by the same rules. This holds the selection into litigation fixed: litigants pick large, competitive,
   contested tenders. Reported beside the main comparison; points come from the main one, and a check whose rate
   reverses against the litigated comparison is flagged.
3. Bid-level checks (BID-COUNT, BID-VALID) also among explicitly competitive procedures only.

## Checks tested

Every standard indicator for which DECP has the fields; the standard definitions and kinds apply.

| Standard ID | French measure (DECP fields) | Kind / X |
| --- | --- | --- |
| BID-COUNT | `offresRecues` on competitive procedures; bins 1, 2, 3, 4–5, 6–10, 11+ | count (current FR `single-bid`, 12 points) |
| DIRECT | procedure "sans publicité ni mise en concurrence préalable" (current FR `direct-award`, 18) | category; amount control |
| NEAR-LIMIT | amount just under a legal limit: no-competition limit €40,000 excl. VAT from 2020-01-01 (€25,000 before), EU thresholds by period and contract type; other limits (temporary works exemptions, later changes) read from the code before computing | legal X; band width distributional |
| AMEND-COUNT | number of DECP modifications within 24 months of notification | count |
| AMEND-PRICE | last modified amount ÷ initial, % (current FR `amount-increase`, > 20 % from 8 to 30) | continuous, one range |
| TERM-EXTENSION | modification extending `dureeMois` | category |
| DURATION | `dureeMois` (current FR `long-contract`, from 120 months) | continuous, one range |
| SIGN-DATE | notification in December; on a weekend | category |
| BUYER-SHARE | amount ÷ buyer's yearly DECP total | continuous; size-like, value-band control |
| SUPPLIER-DEPENDENCE | supplier's share of the buyer's yearly total | continuous; size-like control |
| CONCENTRATION | supplier's share of the buyer's contracts in a CPV division, ≥ 10 contracts (current FR `supplier-concentration`, 12–30 from 60 %) | continuous, one range |
| REPEATED-SINGLE-BID | buyer's single-offer rate in the CPV division (current FR `repeated-single-bid`) | continuous, one range |
| REPEATED-DIRECT | direct awards by the same buyer to the same SIREN in the CPV division (current FR `repeated-direct-award`, 18–30 from 3) | count |
| NEW-SUPPLIER | no award between buyer and supplier in the 3 preceding years (from 2022 only; unknown before) | category |
| FRAMEWORK | call-off under a framework (`idAccordCadre`) | category (reported; frameworks change several measures) |
| CONSORTIUM | `typeGroupementOperateurs` joint or several | category |
| SUBCONTRACTING | `sousTraitanceDeclaree` | category |
| SUPPLIER-TYPE | holder identified other than by SIRET (foreign or other identifier) | category |
| ROUND-NUMBERS | round amount (as in A1–A7 of [untested-checks-plan.md](untested-checks-plan.md)) | category |
| LATE-PUBLICATION | `datePublicationDonnees` − `dateNotification` against the legal deadline (read from the code) and the buyer's baseline | legal + continuous |

Not testable nationally (fields not in DECP): NOTICE-PERIOD (current FR `short-bidding-period`) and notice changes,
PRICE-RATIO, BID-GAP, BID-SPREAD, BID-VALID, RELATED-BIDDERS. NOTICE-PERIOD is tested on the subset linked to BOAMP
notices if at least 10 labelled buyers have one; otherwise reported as untested.

Expected, stated in advance:

- **Circularity in the irregular-award family.** A2 findings are often "no competition", so DIRECT and REPEATED-DIRECT
  are partly circular in A2; an ousted bidder implies at least two offers, so BID-COUNT is biased against single offers
  among ousted-bidder cases. These checks are rated on the whole family as planned, and also on the cases that do not
  imply them (DIRECT outside A2; BID-COUNT on prefect and third-party challenges), and the difference is reported.
- Litigated tenders are larger than average: size-like checks will look strong before the value-band control.
- In the criminal family, favouritism convictions should concentrate on DIRECT, NEAR-LIMIT and repeated awards to the
  same supplier.

## Method and decision rule

Unchanged from Korea after the 2026-10-20 amendment, in `tools/propose-indicator-points.py`: at least 10 labelled
buyers; buyer-weighted rates (hit rate reported first); LR shrunk toward 1 by a prior worth 10 buyers; points =
10 × log2 of the shrunk LR at the 25th percentile of buyer resamples, floored at 0; all linked contracts as the basis,
one contract per case as robustness. Kind-3 indicators: one range [a, b) chosen by case-held-out cross-validation; a
second range only where the data clearly call for it, with the reason. Size-like checks earn points only under the
value-band control with labelled amounts ÷ 1.3.

**Which family sets the points.** As Korea's audit family: the irregular-award family's points for a check count only
if the criminal family does not contradict them (criminal family ≥ 10 labelled buyers and its LR's 95 % upper bound
below 1). A check's points are the largest among the families that count. A1 + A2 alone is reported beside the
whole family, not used for points.

## Reading

Each ruling is read once by Luna (`gpt-6-luna`) into a fixed JSON: relevance, action type, outcome class (A1–A3, C, X),
the court's finding quoted verbatim, contracts (buyer, object, lot, amount with VAT basis, award or signature date,
winner, SIREN if printed), earlier and later rulings cited, finality hints. Quotes are checked against the text;
rulings with a failed quote, low confidence or class A/C get a second reading by DeepSeek (free; Haiku when DeepSeek
hangs), and disagreements on class or contract identity are settled by a Terra reread. Agreement rates between readers
are reported. Jobs are resumable (Codex quota is shared).

## Order of work

1. Reading: administrative wins (~6,400), then rejections, then Judilibre (~7,000 hits, after a keyword pre-filter
   for a named contract).
2. Finality lookups within each source; p read from the two official reports.
3. Linking to DECP (refreshed), hand check of 20 links.
4. Rates per check and family; results in `france-labels-results.md`. Any change to this plan after a rate has been
   seen is added below as a dated amendment saying what had been seen.

## Note 2026-10-29: the pending-appeal weight p (no rate of any check computed yet)

Read from the Conseil d'État's activity report for 2024 (Rapport public 2025, *Bilan d'activité statistique*,
tables 15–16; <https://www.conseil-etat.fr/content/download/228242/file/CE_RA_2024_PDFweb_.pdf>, all matters, no
contract-specific figure). Cassation appeals against appeal-court rulings: admitted 28.4 / 23.5 / 26.5 / 27.2 / 23.2 %
in 2020–2024; of admitted cases, cassation 60 / 59.3 / 58.3 / 63.4 / 58.1 %. Over the five years, about 15.4 % of
appeal-court rulings challenged in cassation are quashed, so **p = 0.85 for a finding of a cour administrative d'appel
with a cassation appeal pending** (sensitivity 0 and 1 unchanged). The report does not give the share of tribunal
judgments overturned on appeal; a tribunal's yearly report cites a national average of 15.8 % for 2024 (TA Guadeloupe,
bilan annuel 2024), not yet checked against an official table, so **tribunal findings with an appeal pending keep
0.91** until that figure is read from the cours administratives d'appel's own statistics.

## Note 2026-10-29: cartel damages rulings go to the collusion family (no rate of any check computed yet)

Seen: the first 35 DeepSeek second readings against Luna's. They agree on 21 of 35 classes (Luna gave no class
for one). 8 of the 13 disagreements are buyers' damages suits against bid-rigging cartels (Île-de-France school
building and others): Luna classed them A1/A2, DeepSeek X. Under the prompt's definition DeepSeek is right (the court
rules on damages, not on the lawfulness of the award), but a buyer awarded cartel damages on a named contract is
proven collusion. So these rulings leave the irregular-award family and become **collusion labels** (same rules as
Korea's collusion family: the contracts named in the ruling, finality as above). Candidates: rulings that mention
*entente*, *pratique anticoncurrentielle*, *concertation frauduleuse* or L. 420-1 at least three times (125: 79
TA, 25 CAA, 8 CE, 13 ordinances; list in `~/.cache/contract-signals/france-admin/cartel-candidates.txt`). They get
their own short reading (cartel held or not, contracts and lots, members) instead of A1–A3. The irregular-award
prompt is not changed; its A/X classes for these rulings are ignored.
Terra settled the other 5 disagreements: it sided with Luna once (A1) and classed the other 4 X, so Luna over-reads
irregularities; every Luna A or C keeps its second reading. Two of the 4 are rulings on the amount of damages only,
after an earlier ruling held the award irregular: the earlier ruling (in `lower_rulings` or cited) is the label, and
is looked up in the corpus.

## Note 2026-10-30: Haiku as second reader; rejections cut by a keyword filter (no rate of any check computed yet)

The owner has too little Codex quota for the reading as planned (Terra second reading of 1,111 wins, Luna reading of
every rejection), and the DeepSeek free tier is at its usage limit. Seen before this change: Terra's second reading
of 321 rulings (same class as Luna on 272; 33 Luna A/C moved to X, 1 X moved to A1) and a Haiku pilot on 40 of them
(the 33 moves plus 7 agreements): Haiku agrees with Terra on 20 of the 25 Luna-A rulings, but keeps C on 9 of the 12
rulings Terra made X because the court rejected the claim without ruling on the irregularity.

1. **Second reading by Haiku** (lean `claude -p`), for the Luna A/C rulings Terra has not read. Not sent for a second
   reading: Luna X rulings whose only problem is a quote not found verbatim (196; Terra changed the class of 1 of 118
   such rulings). Rulings whose result was not valid JSON are reread.
2. **Terra settles disagreements** when Codex has quota: every A class where Haiku and Luna differ, and every C/X
   disagreement (Haiku is not trusted on C). Under the definitions above, C requires the court to find no
   irregularity; a rejection that leaves the irregularity undecided is X.
3. **Rejections: keyword pre-filter, then a subset.** A ruling is award-related if it mentions L. 551-1 / L. 551-13,
   référé (pré)contractuel, contestation de validité / Tarn-et-Garonne, obligations de publicité et de mise en
   concurrence, an irregular / abnormally low / unacceptable offer, award criteria, the rejection of an offer or the
   award of the contract. On Luna's 6,382 classified wins this keeps 742 of 792 A/C (94 %) and drops 4,269 of 5,585 X.
   It keeps 5,537 of 10,745 rulings whose outcome starts with "Rejet". Read: all of them that also say the claimant was
   not harmed, the irregularity had no effect or is "à le supposer établi" (809: irregularities found or assumed
   in a rejected claim), plus a random sample of 500 of the other award-related rejections (seed 1) for class C. First
   reader Haiku; 30 of them are reread by Terra to measure Haiku as a first reader.
4. Agreement rates between readers are reported as before.

## Note 2026-10-30 (later): third reader for Haiku/Luna disagreements (no rate of any check computed yet)

Codex reached its weekly limit (until 2026-11-04) after Terra had settled 20 of the 140 rulings (110 Haiku/Luna class
disagreements, 30 Haiku rejection readings). The others get DeepSeek (free) as a third reader; a class held by two of
the three readers (Luna, Haiku, DeepSeek) is kept, and rulings where all three differ wait for Terra. Seen so far: of
the 110 disagreements Terra sided with Luna on 5 and with Haiku on 7; DeepSeek with Haiku on 27 and with Luna on 10;
61 still unsettled (DeepSeek's free tier stopped after ~45 rulings). Of 13 Haiku rejection readings checked, Terra or
DeepSeek agree on 11; Terra found an irregularity in 2 that Haiku read as X and C.

## Note 2026-10-30: supplier checks added (no rate of any check computed yet)

Owner 2026-10-30: focus on France and Korea, and look for more indicators; the checks above are mostly about the
procedure, while favouritism is often visible in who wins. Seen before this note: only field coverage in the
consolidated DECP of 2026-10-04 (3,308,334 rows): winner's distance from the buyer filled on 80 %, activity code (NAF)
96 %, size category 94 %, identified by SIRET 97 %. No label has been linked and no rate computed. Added, with the same
decision rule, families and comparisons as the checks above:

| Standard ID | French measure | Kind |
| --- | --- | --- |
| SUPPLIER-DISTANCE | `titulaire_distance` (km, winner's establishment to buyer, from the DECP enrichment) | continuous, one range; local winners are expected in works, so also reported within contract type |
| SUPPLIER-SIZE | `titulaire_categorie` (PME / ETI / GE, from SIRENE) | category; size-like, value-band control |
| SUPPLIER-AGE | months from the winner's creation (`dateCreationUniteLegale`, SIRENE stock) to `dateNotification` | continuous, one range |
| SUPPLIER-CLOSED | winner's legal unit ceased (`etatAdministratifUniteLegale` = C) within 24 months after notification | category; only contracts notified ≥ 24 months before the SIRENE extract |
| ACTIVITY-MISMATCH | winner's NAF division outside the divisions that win ≥ 1 % of the contracts of the same CPV division nationally | category |
| SUPPLIER-SHARE-NEW | first award of the winner by this buyer and the winner's share of the buyer's yearly total ≥ 25 % | category (NEW-SUPPLIER × SUPPLIER-DEPENDENCE, stated in advance as the favouritism pattern) |

SIRENE (INSEE, stock of legal units, Licence Ouverte) is downloaded once for the creation and closure dates; the
extract date is stated in the results. Expected, stated in advance: SUPPLIER-SIZE and SUPPLIER-DISTANCE are confounded
with contract type and size (large firms win large works far away), so they earn points only under the value-band
control and are reported by contract type.

## Note 2026-10-30: linking rulings to DECP contracts is probabilistic (no rate of any check computed yet)

`tools/link-france-admin-rulings.py` links each contract named in an A1/A2/A3/C ruling to a DECP contract. Earlier
versions accepted a link by hand-set rules: word-overlap cutoffs, at least three agreeing fields, a veto on
contradicting fields, and a minimum word length for names. A hand check of 20 found 5 wrong; after the veto 2–3 were
still doubtful. Owner, 2026-10-30: replace the cutoffs with graded evidence. The linker now uses Fellegi–Sunter record
linkage:

- Every DECP contract of the resolved buyer is a candidate. Each field gets a graded level. For the description and the
  winner, the level is the share of the named words found, with each word weighted by log2(N / its frequency) among
  that buyer's contracts or suppliers. A rare name therefore counts more than a common word, and no word length is
  required. The winner's top level is an equal SIREN. The amount is equal (±1 €, with or without VAT) or not. The date
  gap falls in bands (7, 30, 90, 365 days). A field missing on either side adds nothing.
- The weight of each level is log2(m / u), with m and u estimated by EM over all 1.6 million candidate pairs. Estimated
  weights: description −6.5 (nothing shared) to +7.8 (all); winner −0.9 to +6.9; equal amount +5.1; date within a week
  +3.8, over a year −0.6.
- Probability of a candidate: its likelihood ratio × prior 1/N, against prior odds that the contract is in DECP at all
  (0.5 when signed or unknown, 0.2 when the ruling says it was not signed). Several DECP publications of one contract
  (same SIREN, dates within 7 days, same or missing amount) add up.
- A link is accepted at probability ≥ 0.9, and the probability is stored with it.

Result: 128 contracts linked (A1 17, A2 10, A3 29, C 72). The rule-based version linked 209. Hand check of 20 accepted
links (seed 21): 20 right. In the 0.5–0.9 band (132 contracts), 8 of 12 checked were right, which fits their stated
probabilities. The misses there are mostly large buyers whose ruling gives no date or amount, so a later stage could
weight label contracts by their link probability instead of using a cut. Rulings whose procedure was annulled and
then relaunched correctly stay unlinked: the relaunched contract is not the one that was litigated.

## Note 2026-10-30 (later): no fixed cutoffs in the supplier checks or the linking (no rate of any check computed yet)

Owner, 2026-10-30, asked whether anything arbitrary remained. Three supplier checks in the note above had fixed
cutoffs. Following the one-range rule, each becomes a continuous measure with one cross-validated range [a, b), like
SUPPLIER-AGE:

| Standard ID | Was | Now (continuous, one CV range) |
| --- | --- | --- |
| SUPPLIER-CLOSED | ceased within 24 months of notification | months from notification to the legal unit's closure; units still active count as censored at the SIRENE extract date, and a range can only be chosen where every contract in it was observable that long |
| ACTIVITY-MISMATCH | winner's NAF division wins < 1 % of the CPV division | share of the CPV division's contracts (national, other buyers) won by the winner's NAF division |
| SUPPLIER-SHARE-NEW | first award by this buyer and ≥ 25 % of its yearly total | for first awards of a winner by a buyer, the winner's share of the buyer's yearly total |

Linking (`tools/link-france-admin-rulings.py`): the remaining hand-set choices go as well:
- Level edges are finer: 7 description and winner levels, plus SIREN equal; 11 date levels. EM, not the edges, now
  shapes the weights.
- The amount is graded by |ln ratio| and allows every French VAT rate (5.5, 10, 20 %), not only equality with or
  without 20 %.
- The buyer name is a weighted field. The 10 best-matching names with overlap ≥ 0.5 are candidates (blocking, which
  only limits the search), instead of a 0.6 cutoff and dropping buyers with more than 5 SIRENs.
- The prior that the contract is in DECP at all is estimated per signed / not signed / unknown.
- There is no 0.9 acceptance cut: every best candidate is stored with its probability, and label rates weight each
  contract by it.

Duplicate grouping (same SIREN, dates within 7 days) stays: it decides whether two records are one publication, not
how much evidence a field gives.

Result of the linking changes (same day). Two estimation fixes were needed before the weights made sense:
- Estimating m and u freely let EM pick up "right buyer" instead of "right contract": an equal amount weighed only
  +2.3, and the not-signed group got a higher prior than the signed one.
- Fixing u to the level shares among all pairs was not enough; equal amount still weighed only +3. EM still treated
  pairs independently, so several lots of one tender could all be "the" match.

The final EM uses the same model as the linking: each named contract is at most one of its candidates, or none.
Estimated weights (log2):
- SIREN equal +12.7; winner name fully found +9.1, nothing shared −4.8
- description fully found +8.5, nothing shared −5.8
- amount equal +7.3, off by more than ×2 −2.9
- same day +6.7, over two years apart −2.8
- buyer name exact +0.9, overlap below 0.9 about −2 to −3

The prior that a named contract is in DECP is 0.25 if the ruling says it was signed and 0.41 if it does not say.
Contracts the ruling says were not signed (615) are no longer linked: a DECP match could only be the relaunched
procedure.

Expected links (sum of probabilities): A1 26.9, A2 13.4, A3 50.7, C 193.9; at p ≥ 0.9: 17, 6, 28, 113. Hand check
(seed 31):
- 20 of 20 right at p ≥ 0.9.
- 10 or 11 of 12 right at 0.5–0.9 (mean stated probability about 0.75), so the probabilities lean conservative.
- One wrong buyer: "communauté d'agglomération du Sud (CASUD)" (Réunion) linked to Grand Sud Caraïbe (Guadeloupe).
  The buyer field counts only −2 to −3 below overlap 0.9.

Weighting by probability therefore slightly undercounts linked labels; it does not add wrong ones.

## Note 2026-10-30 (evening): class per ruling by Dawid–Skene; DeepSeek reads every ruling (no rate of any check computed yet)

Owner, 2026-10-30: replace the settling rules with graded evidence and have DeepSeek read every ruling (OpenCode Go;
7,537 rulings, 6 workers, about 12 hours; `~/.local/share/contract-signals/france-deepseek-full.sh`, rerun to resume).
The old rules were: Terra's reading wins; else a majority; else a single reading.

The class of each ruling now comes from Dawid–Skene. EM estimates each reader's confusion matrix (true class → class
read; Jeffreys pseudo-counts 0.5) and the class frequencies, separately for court-reported wins (first read by Luna)
and rejections (first read by Haiku). Each ruling gets a probability per class. Readers are identified by model:
DeepSeek's free and Go routes count as one reader, and so do Haiku's first and second readings. Second readings were
chosen from the first reading's class. EM still holds, because that choice depends only on observed readings.
- The most probable class decides which rulings are linked.
- Its probability is stored, and a label counts as class probability × link probability.
- The contracts are taken from the most accurate reader who read that class.

First run, with 216 of the DeepSeek readings in. Estimated accuracy per true class:

| Reader | A1 | A2 | A3 | C | X |
| --- | --- | --- | --- | --- | --- |
| Luna | 0.85 | 0.34 | 0.82 | 0.50 | 0.99 |
| Haiku | 0.86 | 0.86 | 0.96 | 0.86 | 0.96 |
| DeepSeek | 0.74 | 0.61 | 0.87 | 0.81 | 0.97 |
| Terra | 0.92 | 0.43 | 0.90 | 0.81 | 0.98 |

Expected rulings: A1 251, A2 63, A3 437, C 750. Expected labelled links: A1 40, A2 17, A3 68, C 190.

Luna's accuracy on X cannot be estimated well yet: almost no ruling Luna read as X has a second reading. Rerun the
linker when the DeepSeek reading is complete.

## Note 2026-11-01: all readings in; classes and links rerun (no rate of any check computed yet)

DeepSeek has read every ruling, and Terra has reread 318 rulings and settled 22 Haiku/Luna ties (Haiku 13, Luna 7,
neither 2). Luna's second folder `extract-luna` joined the readers. Dawid–Skene settled 7,691 of 7,692 rulings; one has
no reading. The output is `france-admin/links-2026-11-01/` (same DECP copy of 2026-10-30); the old `links/` is kept.

Estimated accuracy per true class:

| Reader | A1 | A2 | A3 | C | X |
| --- | --- | --- | --- | --- | --- |
| Luna | 0.95 | 0.86 | 0.85 | 0.98 | 0.995 |
| Haiku | 0.85 | 0.89 | 0.96 | 0.97 | 0.985 |
| DeepSeek | 0.90 | 0.86 | 0.94 | 0.94 | 0.997 |
| Terra | 0.90 | 0.71 | 0.97 | 0.82 | 0.99 |

Expected rulings: A1 273, A2 66, A3 471, C 667. Expected labelled links: A1 41, A2 17, A3 79, C 193; at p ≥ 0.9: 20, 9,
41, 107. The estimated prior that a named contract is in DECP is 0.25 if signed and 0.38 if not stated, so linking, not
reading, now limits the family. The 351 tribunal judgments Luna read as X have no second reading; Terra found no missed
A or C among 569 X rulings, so they stay out.
