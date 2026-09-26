# Chile method — Mercado Público checks (v3.0 framework)

**Checks for the Mercado Público cohort** (three purchasing units, licitaciones listed 2024-09 → 2026-08). Same vigilance-index framework as [score-v3.md](score-v3.md): two families, family maxima, cap at 100, `null` = “Not assessed”, unknowns never counted as zero. The checks are those of the shared national engine ([score-ukraine.md](score-ukraine.md), [score-ted.md](score-ted.md), [score-uk.md](score-uk.md)), read from the OCDS releases ChileCompra publishes. French, Colombian and Paraguayan rules are not applied. Amounts stay in CLP as published and are never converted; UTM bands in procedure names are Chilean monetary units, not points.

An editorial sorting tool, not a probability, not a measure of legal gravity, not a certificate of regularity.

## Data and selection

Source: the ChileCompra OCDS API (`api.mercadopublico.cl/APISOCDS/OCDS`), **CC0 1.0** in every release package. It lists **licitaciones** (public and private tenders) by month. **Direct deals (*trato directo*) are published as purchase orders and are not in this source**, so the direct-award checks are out of scope here, not clear.

The listing cannot be filtered by buyer, so the cohort was chosen in two steps:

1. **Map** (`--discover`): every tender code listed for each month (224,704 codes over 23 months; the API answered 404 “No se encontraron resultados” for August 2026 on 26 September 2026, recorded as an empty month). A code starts with the purchasing unit's prefix; one tender per prefix was read to learn the unit's buyer id and name: **4,582 prefixes**, 18 codes left unmapped.
2. **Announcement, 26 September 2026, before any tender or award of the chosen units was read.** Rule applied to the map only (volume and buyer name): per level, the unit with the most listed tenders, leaving out units above 500 tenders; for the municipal level, the municipality's own unit, not a department (education, health) unit.
   - national (ministry): **Ministerio de Obras Públicas**, unit `CL-MP-2015` (prefix 1019; its tenders are those of the Dirección General de Aguas), 274 tenders; the Subsecretaría de las Culturas, 540, is above the cap;
   - regional: **Gobierno Regional del Maule (VII Región)**, `CL-MP-2592`, 91 tenders;
   - municipal: **I. Municipalidad de Puente Alto**, `CL-MP-3414`, 479 tenders.

The tender and award release of each of the 844 codes were then downloaded (`--download`). The API reports some errors **inside an HTTP 200 body**: 47 award records answered a server error (`status 500`) on every one of three retries and are counted as unavailable, never as “no award”.

One row is one **active award to exactly one supplier**: 522 awards. Excluded: 144 unsuccessful, 70 cancelled and 35 status-less awards (tenders declared void or not awarded), 24 tenders with no award published, 19 awards split among several suppliers (the line items do not say which supplier won which item, so no per-supplier amount), 47 unavailable award records and 1 empty award package. Contact points are never imported.

## The eight checks

| Check | ID | Family | Eligibility / trigger | Weight |
| --- | --- | --- | --- | --- |
| Single offer in a competitive procedure | `cl-single-offer` | Competition | Licitación pública or privada; exactly one tenderer published on the tender | **12** |
| Award without competition | `cl-direct-award` | Competition | **Out of scope**: direct deals are not in this source | — |
| Repeated single-offer awards | `cl-repeated-single-offer` | Competition | This award is single-offer; same buyer and supplier RUT in ≥3 distinct tenders | **12 at 3 → 40 at 10** |
| Repeated awards without competition | `cl-repeated-direct` | Competition | **Out of scope** (as above) | — |
| Concentrated awards | `cl-concentration` | Competition | Same buyer and UNSPSC segment (the items' most frequent 2-digit segment); ≥10 tenders, ≥80 % with an identified winner, share ≥60 % | **12 at 60 % → 40 at 100 %** |
| Amount increase | `amount-increase` | Execution | **Out of scope**: modifications are not in this source | — |
| Short bidding period | `short-bidding-period` | Competition | **Out of scope** | — |
| Long declared duration | `long-contract` | Execution | **Out of scope** | — |

- **Tenderers** are the parties with the `tenderer` role on the award release: a count for the **whole tender, not per line item**. Rows exist only when the whole tender went to one supplier; a tenderer may still have bid on some items only, so “2 or more” does not prove that every item had competition. One tenderer does.
- **Licitación privada** (by invitation, 18 of 844 tenders) counts as competitive: the law requires invitations to several suppliers.
- **Supplier identity** is the RUT (Chilean tax number, `CL-RUT`), published for every retained supplier.

## Results

Reproduced by `tests/national.cjs`.

| Check | Signals | Clear | Unknown | Out of scope |
| --- | ---: | ---: | ---: | ---: |
| `cl-single-offer` | 71 | 448 | 3 | 0 |
| `cl-direct-award` | 0 | 0 | 0 | 522 |
| `cl-repeated-single-offer` | 14 | 57 | 3 | 448 |
| `cl-repeated-direct` | 0 | 0 | 0 | 522 |
| `cl-concentration` | 0 | 296 | 226 | 0 |

**71 awards with a signal, 449 zero, 2 not assessed** (two tender records unavailable). By unit: MOP 34 of 144, Puente Alto 32 of 328, Maule regional government 5 of 50. 71 awards had one tenderer, 67 two, 70 three, 64 four and 247 five or more.

- **Examples read.** The strongest lead: **Inducien Instruments S.A.** won eight Dirección General de Aguas tenders for current meters, gauging reels and spare parts as the only tenderer, several specifying a brand “o equivalente” (OTT, Gurley), a common reason for a single bid. The Universidad de Concepción won three limnology and water-sampling tenders alone. In Puente Alto, single tenders are small purchases (Adobe licences, wool shawls, event entertainment, catering, printing), one supplier three times. The Maule regional government's are printers, building insurance, cloud hosting, internet and an X-ray scanner.
- **Unflagged near-misses:** 448 awards with two or more tenderers; concentration is mostly unknown (226) because few buyer/segment groups reach ten tenders.

## Reproduction

```sh
python tools/import-chilecompra.py --offline               # rebuild from the raw releases
python tools/import-chilecompra.py --discover --download   # new map and records (network, over an hour)
node tests/national.cjs
```
