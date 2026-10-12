# BOAMP ↔ DECP cross-source evidence

Reproduce: `python tools/build-boamp-decp-links.py` (offline). Tests:
`python -m unittest discover -s tests -p test_build_boamp_decp_links.py -v`.

## Current snapshot

Inputs: 3,010 explorer BOAMP/audit records, 2,997 DECP history records,
2,289 DECP city records, and 8,386 raw BOAMP notices. The compact public
`data/boamp-decp-links.json` records SHA-256 hashes of the exact input bytes,
input counts, link statuses and official URLs. No timestamps, names, holder
identifiers, raw notice bodies or copied contract fields are exported.

- **0 confirmed links; 9 unconfirmed candidate pairs**, spanning 7 BOAMP lots.
- **4 pairs ambiguous**: two Paris candidates for notice 25-21317 lot 0001;
  two Nantes candidates for notice 25-34782 lot 0003. None selected.
- **4 pairs with differing CPVs** (first eight digits compared, ignoring the
  DECP check digit). These are warnings, not grounds for choosing a match.
- Raw extraction recovered 15,757 unique notice/lot published references;
  2,957 current explorer rows have one. None exactly matches a DECP contract
  reference under the same buyer. There are no confirmed notice/lot matches.

## Conservative rules

A valid, identical 14-digit buyer SIRET is required for every link. Confirmation
requires either exact equality of a published contract reference and DECP
`contractId`, or a pre-existing exact notice ID **and** lot ID. No substring,
subject, name, amount, SIREN or fuzzy matching is used. BOAMP `contractId` is
ignored: `CON-000x` identifies an eForms settled contract within its notice,
not a DECP reference; such values are also rejected as published references.

Raw recovery reads `efac:SettledContract/efac:ContractReference/cbc:ID` only when
the notice occurs once and the lot has one winning LotResult referencing one
uniquely identified SettledContract. It does not guess among duplicate results,
contracts or notices. Missing raw notices stay unknown. An explicit normalized
`contractReference`, if present, can also supply the published reference.

Without exact evidence, identical buyer SIRET, at least one shared holder SIRET
explicitly typed SIRET, and the same valid contract date produce a **candidate
only**. Publication dates are never substituted. Multiple matches in either
direction are retained and flagged; date equality is not proof of identity
(BOAMP conclusion and DECP notification dates have different meanings).
No score, amount, offers or dataset is replaced or reconciled by this builder.

## Explorer

Details → Sources exposes external official cross-source URLs in both
directions. Current links are explicitly labelled **“Unconfirmed candidate
only”**, with ambiguity and differing-CPV warnings. They do not switch the
explorer dataset. The optional artifact is schema/URL validated; missing,
malformed or failed loading does not block the explorer. Local user imports
never receive these links. A link is shown only when its current record ID and
source URL agree with the artifact. Input hashes document the build snapshot;
they are not a live revalidation of external source contents.
