# BOAMP ↔ DECP cross-source evidence

Reproduce offline: `python tools/build-boamp-decp-links.py`.
Tests: `python -m unittest discover -s tests -p test_build_boamp_decp_links.py -v`.

## Snapshot

Inputs: **3,010** explorer BOAMP/audit records, **2,997** DECP history records, **2,289** DECP city records and **8,386** raw BOAMP notices. `data/boamp-decp-links.json` records input-byte hashes, counts, statuses and official URLs without names, holder IDs or raw contract fields.

- **0 confirmed links; 9 unconfirmed pairs across 7 BOAMP lots.**
- **4 ambiguous pairs:** two for Paris 25-21317 lot 0001, two for Nantes 25-34782 lot 0003; none selected.
- **4 differing-CPV pairs**, comparing the first eight digits and ignoring DECP's check digit; warnings do not choose matches.
- Raw extraction recovered **15,757** unique notice/lot references; **2,957** explorer rows have one. None exactly matches a DECP reference under the same buyer; no notice/lot match is confirmed.

## Link rules

Every link requires an identical valid **14-digit buyer SIRET**. Confirmation needs an exact published reference = DECP `contractId`, or an existing exact notice ID **and** lot ID. BOAMP `CON-000x` is local to its notice and cannot be a DECP reference. No fuzzy, substring, subject, name, amount or SIREN matching.

Raw recovery reads `efac:SettledContract/efac:ContractReference/cbc:ID` only for a unique notice and one winning LotResult linked to one uniquely identified SettledContract. Duplicate results/contracts are not guessed; missing notices stay unknown. An explicit normalized `contractReference` may also supply the reference.

Without exact evidence, the same buyer, a shared holder explicitly typed SIRET and a valid equal contract date produce only a candidate. Retain multiple matches in both directions. Publication dates cannot substitute; BOAMP conclusion and DECP notification dates mean different events. The builder changes no scores or contract fields.

## Explorer

Details → Sources shows official URLs in both directions as **“Unconfirmed candidate only”**, with ambiguity/CPV warnings. A link requires the current record ID and source URL to match the artifact. Local imports receive no links. Schema/URL validation and optional loading keep the explorer usable when the artifact fails; links do not switch datasets. Snapshot hashes do not revalidate live source contents.
