# Privacy assessment (2026-11-09)

Controller: Lasu Shin, private person, France. French law and the GDPR apply to all processing, Korean data included (Art. 3(1)). This is the owner's working record, not legal advice.

## Record of processing (Art. 30)

| | |
| --- | --- |
| Purpose | Public scrutiny of procurement; finding contracts worth a closer look; reports to competent authorities |
| People | Sole traders and other individual suppliers; officials or parties named in decisions; visitors (host logs only) |
| Data | Pseudonym, contracts and amounts; privately: names, identifiers, addresses as published at source; sanctions and verdict links (Art. 10) |
| Sources | Official procurement portals, company registers, sanction lists, published decisions |
| Recipients | Public (pseudonymised output); Cloudflare, GitHub; Google Drive (encrypted, rarely used data); Anthropic, OpenAI; DeepSeek except French criminal rulings; authorities receiving reports |
| Transfers | United States (host, code, AI readers); China (DeepSeek); South Korea-origin data is imported, not exported |
| Retention | Published while useful for scrutiny; private copies have no end date (owner's decision 2026-11-09) |
| Security | Key and private list outside Git; private view on localhost only; raw snapshots not in Git |

## Legitimate interest (Art. 6(1)(f))

- **Interest:** public money oversight, a recognised and concrete interest. Art. 85 and LIL Art. 80 are claimed first, the balance below is the fallback.
- **Necessity:** names are not needed publicly, so they were replaced; linking a person's contracts is needed to measure concentration and repeat awards.
- **Balance:** data was already public and concerns business activity, and individuals are few. Against: a statistical flag can stigmatise a small trader, and pseudonyms remain linkable. Mitigation: no-wrongdoing notice, pseudonyms, objection route honoured even where the exemption would allow refusal.

## Impact assessment (Art. 35) — main risks

| Risk | Status |
| --- | --- |
| Person wrongly seen as suspect | Notice; no names published; hand check before any report |
| Re-identification from contract text, buyer or amount | Remains; contract descriptions are published as the source wrote them. LIL Art. 46 5° forbids re-identifying French decision parties: never link them to real people in published output |
| Sanction or verdict links (Art. 10) | Hashing does not take these outside Art. 10. Relies on Art. 85/LIL Art. 80; weakest point |
| Private list leaks | Stored only on the owner's machines, key separate |
| Transfer to China | French criminal rulings blocked from DeepSeek by `tools/extract-france-criminal-rulings.py`. Already read before the block: 1,369 files. Parties there are already reduced by the courts (for example "M. B...") |
| Indefinite private retention | Conflicts with storage limitation unless the journalism exemption holds; owner's decision |

## Owner actions still open

- LCEN: give the host full identity, since the site lists a name without a home address (non-professional route).
- Ask a lawyer whether reward money affects "non-professional" status and the journalism exemption.
