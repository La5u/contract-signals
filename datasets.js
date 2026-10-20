// The explorer's datasets, one entry per menu choice. Read by prefetch.js and script.js in the browser and by the
// tools (compare-score-revisions.cjs, snapshot-outputs.cjs, audit-data-quality.py), which parse the object below
// as JSON: keep it JSON. path: the published files; web: the slimmer browser copies when they differ
// (tools/build-web-data.py); remote: served from another host (coverage relative to it).
globalThis.DATASETS = {
  "global": {
    "remote": "global",
    "note": "All published collections, not unique contracts: overlapping representations are retained. Source-specific assessments are not comparable risk rankings. No combined currency totals. Unknown is not zero. Minimum amount uses native currency, not conversion. Only one bounded scan page is retained.",
    "sources": {
      "publisher": "Existing published registry collections (including KONEPS)",
      "links": [],
      "licence": "Each collection retains its own source and licence; select that collection for publication details."
    }
  },
  "tours": {
    "path": "data/tours-notices.json",
    "coverage": "data/tours-notices-coverage.json",
    "sources": {
      "publisher": "DILA — BOAMP; Publications Office of the EU — TED",
      "links": [
        [
          "BOAMP search",
          "https://www.boamp.fr/"
        ],
        [
          "BOAMP API used",
          "https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records"
        ],
        [
          "TED search",
          "https://ted.europa.eu/"
        ]
      ],
      "licence": "BOAMP: Licence Ouverte 2.0 (DILA legal notice and data.gouv.fr); TED legal notice applies. See docs/data-sources.md for scope.",
      "raw": "data/tours-notices/raw/",
      "reproduce": "python tools/import-tours-notices.py --offline",
      "collected": "BOAMP notices matched by the buyer’s exact SIRET, TED XML matched by UUID and version."
    },
    "note": "Tours · 2025 BOAMP/TED notices and linked references: 25 notices, 66 version/lot rows, including joint purchases. Rows represent documents, not individual contracts. Bidding periods require a complete notice chain."
  },
  "consultations": {
    "path": "data/consultations.json",
    "coverage": "data/consultations-coverage.json",
    "sources": {
      "publisher": "DILA — BOAMP",
      "links": [
        [
          "BOAMP search",
          "https://www.boamp.fr/"
        ],
        [
          "BOAMP API used",
          "https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records"
        ]
      ],
      "licence": "Licence Ouverte 2.0 (DILA legal notice and official data.gouv.fr records); incorporated third-party material may have separate rights.",
      "raw": "data/consultations-raw.json",
      "reproduce": "python tools/import-consultations.py --offline",
      "collected": "The first 10 initial BOAMP calls published on 3 February 2025, by identifier order."
    },
    "note": "10 BOAMP consultation notices published on 3 February 2025, with one linked correction and three award notices. Rows represent notices, not awarded contracts. Incomplete notice chains prevent bidding-period calculations."
  },
  "decp": {
    "path": [
      "data/decp-history.json",
      "data/decp-cities.json"
    ],
    "web": [
      "data/web/decp-history.json",
      "data/web/decp-cities.json"
    ],
    "coverage": "data/decp-france-coverage.json",
    "sources": {
      "publisher": "Ministère de l’Économie et des Finances — DECP (données essentielles de la commande publique); buyers’ own publication feeds and open-data lists",
      "links": [
        [
          "Dataset page · data.economie.gouv.fr",
          "https://data.economie.gouv.fr/explore/dataset/decp-2022-marches-valides/"
        ],
        [
          "API used (records endpoint)",
          "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records"
        ],
        [
          "DECP schema v2.0.4",
          "https://github.com/139bercy/decp-arr2022/blob/main/schemes/schema_decp_v2.0.4.json"
        ],
        [
          "Buyer feeds · national consolidated DECP (decp.info, Licence Ouverte 2.0)",
          "https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-consolidees-format-tabulaire"
        ],
        [
          "Ville de Nantes · concluded contracts 2025",
          "https://www.data.gouv.fr/datasets/marches-publics-conclus-en-2025-par-la-ville-de-nantes"
        ],
        [
          "Bordeaux Métropole datahub · contracts since 2024",
          "https://www.data.gouv.fr/datasets/marches-publics-de-bordeaux-metropole-et-des-communes-mutulalisees-depuis-2024"
        ]
      ],
      "licence": "Licence Ouverte v2.0 (Etalab) for every source",
      "raw": "data/decp-history-raw.json.gz, data/decp-cities-raw.json, data/decp-feeds-raw.json.gz, data/city-portals-raw.json.gz",
      "reproduce": "python tools/import-decp-paris-ardeche.py --offline && python tools/import-decp-cities.py --offline && python tools/build-decp-france-coverage.py",
      "collected": "Every DECP row for eight pre-selected buyer SIRETs (Ville de Paris, Département de l’Ardèche and six municipalities), notified 2024–2025, reconciled with the buyers’ own feeds and open-data lists. Three rows of the Paris 13 November dossier carry hand-curated fields."
    },
    "note": "France · DECP contracts of eight buyers (Ville de Paris, Ardèche, Rennes, Nantes, Bordeaux, Grenoble, Dijon, Tours), notified 2024–2025: 5,286 contracts. Amounts are compared across the Ministry dataset, buyer feeds and open-data lists; disagreements show as ranges. Coverage depends on source publication. Supplier names are current register names."
  },
  "boamp": {
    "path": "data/contracts.json",
    "coverage": "data/coverage.json",
    "sources": {
      "publisher": "DILA — BOAMP; Chambres régionales des comptes (audit dossiers)",
      "links": [
        [
          "BOAMP search",
          "https://www.boamp.fr/"
        ],
        [
          "BOAMP API used",
          "https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records"
        ],
        [
          "CRC reports · ccomptes.fr",
          "https://www.ccomptes.fr/fr/publications"
        ]
      ],
      "licence": "BOAMP: Licence Ouverte 2.0 (DILA legal notice and data.gouv.fr); CRC reports quoted with links.",
      "raw": "data/boamp-raw.json.gz",
      "reproduce": "python tools/import-boamp-sample.py --offline",
      "collected": "All 8,386 BOAMP award notices published February–April 2025; 3,000 unambiguous lots kept by SHA-256 order of their identifier. The two Mauges lots and eight CRC audit dossiers are documented by hand."
    },
    "note": "3,010 records: 3,000 BOAMP lots sampled from February–April 2025 publications, two Mauges lots and eight CRC audit dossiers. Audit dossiers may cover several orders rather than an individual contract. This sample does not provide a complete purchasing history."
  },
  "colombia": {
    "path": "data/colombia-secop2.json",
    "web": [
      "data/web/colombia-secop2.json"
    ],
    "coverage": "data/colombia-secop2-coverage.json",
    "sources": {
      "publisher": "Colombia Compra Eficiente — SECOP II, via datos.gov.co",
      "links": [
        [
          "Dataset page · datos.gov.co (jbjy-vk9h)",
          "https://www.datos.gov.co/Gastos-Gubernamentales/SECOP-II-Contratos-Electr-nicos/jbjy-vk9h"
        ],
        [
          "API used",
          "https://www.datos.gov.co/resource/jbjy-vk9h.json"
        ],
        [
          "SECOP II public search",
          "https://community.secop.gov.co/Public/Tendering/ContractNoticeManagement/Index"
        ]
      ],
      "licence": "CC BY-SA 4.0",
      "raw": "data/colombia-secop2/raw/",
      "reproduce": "python tools/import-colombia-secop2.py --offline",
      "collected": "Every SECOP II contract of three buyers announced before download, signed 2024-09-01 → 2026-09-01."
    },
    "note": "Colombia · SECOP II · MEN, Caldas and Usaquén. Signed September 2024–August 2026: 7,560 contracts, amounts in COP. Coverage depends on source publication; offer counts are unavailable."
  },
  "paraguay": {
    "path": "data/paraguay-dncp.json",
    "coverage": "data/paraguay-dncp-coverage.json",
    "sources": {
      "publisher": "Dirección Nacional de Contrataciones Públicas (DNCP), Paraguay",
      "links": [
        [
          "Public procurement portal · contrataciones.gov.py",
          "https://www.contrataciones.gov.py/"
        ],
        [
          "Open data and API documentation",
          "https://www.contrataciones.gov.py/datos/api/v3/doc/"
        ],
        [
          "Legal notice and licence (the OCDS packages cite /datos/legal, which now returns 404)",
          "https://www.contrataciones.gov.py/datos/aviso-legal"
        ]
      ],
      "licence": "CC BY 4.0",
      "raw": "data/paraguay-dncp/raw/",
      "reproduce": "python tools/import-paraguay-dncp.py --cohort fernando --offline",
      "collected": "Every process of the buyer whose call was published 2024-09-01 → 2025-09-01, then each full OCDS record by OCID."
    },
    "note": "Paraguay · DNCP · Fernando de la Mora. Calls published September 2024–August 2025: 88 processes, 84 retained contract entries, amounts in PYG. Displayed contract dates are period start dates, not signature dates. Amendments remain on their parent contracts."
  },
  "paraguay3": {
    "path": "data/paraguay-dncp-3buyers.json",
    "coverage": "data/paraguay-dncp-3buyers-coverage.json",
    "sources": {
      "publisher": "Dirección Nacional de Contrataciones Públicas (DNCP), Paraguay",
      "links": [
        [
          "Public procurement portal · contrataciones.gov.py",
          "https://www.contrataciones.gov.py/"
        ],
        [
          "Open data and API documentation",
          "https://www.contrataciones.gov.py/datos/api/v3/doc/"
        ],
        [
          "Legal notice and licence (the OCDS packages cite /datos/legal, which now returns 404)",
          "https://www.contrataciones.gov.py/datos/aviso-legal"
        ]
      ],
      "licence": "CC BY 4.0",
      "raw": "data/paraguay-dncp-3buyers/raw/ (records gzipped, exact response bytes)",
      "reproduce": "python tools/import-paraguay-dncp.py --cohort 3buyers --offline",
      "collected": "Every process of three buyers announced before download (one per government level) whose call was published 2024-09-01 → 2026-09-01, then each full OCDS record by OCID."
    },
    "note": "Paraguay · DNCP · MOPC, Central and Asunción. Calls published September 2024–August 2026: 339 processes, 293 retained contract entries, amounts in PYG. Amendments remain on their parent contracts; 92 multi-lot awards lack per-lot tenderer counts."
  },
  "ukraineSample": {
    "path": "data/prozorro-slice-2026-06-08/contracts.json",
    "coverage": "data/prozorro-slice-2026-06-08/coverage.json",
    "documents": "data/prozorro-slice-2026-06-08/documents/",
    "sources": {
      "publisher": "Prozorro (State enterprise Prozorro, Ministry of Economy of Ukraine)",
      "links": [
        [
          "Prozorro public portal",
          "https://prozorro.gov.ua/"
        ],
        [
          "Open-data reuse terms",
          "https://prozorro.gov.ua/openprocurement"
        ],
        [
          "Public API documentation",
          "https://prozorro-api-docs.readthedocs.io/"
        ],
        [
          "Public API used (official records)",
          "https://public-api.prozorro.gov.ua/api/2.5/tenders"
        ]
      ],
      "licence": "Prozorro open-data reuse terms: redistribution, including commercial reuse, permitted with source attribution; no named licence for API records",
      "raw": "private cache (official full-tender responses, SHA-256 per record in config.json)",
      "reproduce": "python tools/fetch-prozorro-slice.py --out <dir> --since 2026-06-01 --until 2026-09-01 --limit 3500, then python tools/import-prozorro.py --expansion-config data/prozorro-slice-2026-06-08/config.json --cache-dir <dir> --output-dir data/prozorro-slice-2026-06-08",
      "collected": "Random sample (SHA-256 ranking) of 3,500 of the 44,780 open tenders (aboveThreshold) with status complete, created June–August 2026, from the national Prozorro tender feed. No amount, indicator or label filter."
    },
    "note": "Ukraine · Prozorro · random sample of 3,500 completed open tenders (aboveThreshold) created June–August 2026, all buyers: 3,663 signed contracts. Per-tender checks only: repetition, concentration and buyer share need every tender of a buyer and are not assessed; amendments were not retrieved. Amounts in UAH, EUR or USD."
  },
  "ukraine": {
    "path": "data/prozorro.json",
    "coverage": "data/prozorro-coverage.json",
    "documents": "data/prozorro-documents/",
    "sources": {
      "publisher": "Prozorro (State enterprise Prozorro, Ministry of Economy of Ukraine)",
      "links": [
        [
          "Prozorro public portal",
          "https://prozorro.gov.ua/"
        ],
        [
          "Open-data reuse terms",
          "https://prozorro.gov.ua/openprocurement"
        ],
        [
          "Public API documentation",
          "https://prozorro-api-docs.readthedocs.io/"
        ],
        [
          "Public API used (official records)",
          "https://public-api.prozorro.gov.ua/api/2.5/tenders"
        ]
      ],
      "licence": "Prozorro open-data reuse terms: redistribution, including commercial reuse, permitted with source attribution; no named licence for API records",
      "raw": "data/prozorro/raw/ (official records gzipped, exact response bytes)",
      "reproduce": "python tools/import-prozorro.py --offline",
      "collected": "Search-discovered tenders for three preselected buyers, created 2024-09-01 → 2026-09-01, checked against the official API buyer field. Search completeness is not established; see docs/ukraine-audit.md."
    },
    "note": "Ukraine · Prozorro · Health, Vinnytsia and Dnipro. Tenders created September 2024–August 2026: 526 tenders, 488 signed contracts. Amounts in UAH, EUR or USD. Search coverage is unverified; wartime rules permit withheld publications."
  },
  "chile": {
    "path": "data/chile-mp.json",
    "coverage": "data/chile-mp-coverage.json",
    "sources": {
      "publisher": "Dirección de Compras y Contratación Pública (ChileCompra) — Mercado Público",
      "links": [
        [
          "Mercado Público · buscador de licitaciones",
          "https://www.mercadopublico.cl/Home/BusquedaLicitacion"
        ],
        [
          "OCDS API used (tender and award releases)",
          "https://api.mercadopublico.cl/APISOCDS/OCDS/listaOCDSAgnoMes/2025/03/0/10"
        ],
        [
          "CC0 1.0 public-domain dedication",
          "https://creativecommons.org/publicdomain/zero/1.0/"
        ]
      ],
      "licence": "CC0 1.0 (declared in every release package)",
      "raw": "data/chile-mp/raw/ (monthly listings, prefix map, tender and award releases gzipped, exact response bytes)",
      "reproduce": "python tools/import-chilecompra.py --offline",
      "collected": "Every licitación of three purchasing units announced before download (one per level), listed 2024-09 → 2026-08, chosen from a map of all 4,582 purchasing-unit prefixes."
    },
    "note": "Chile · Mercado Público · MOP (Dirección General de Aguas), Maule and Puente Alto. Listed September 2024–August 2026: 844 tenders, 522 single-supplier awards, amounts in CLP. Direct purchase orders (trato directo) are not included."
  },
  "uk": {
    "path": "data/uk-fts.json",
    "coverage": "data/uk-fts-coverage.json",
    "sources": {
      "publisher": "Find a Tender service (Cabinet Office, United Kingdom)",
      "links": [
        [
          "Find a Tender · search notices",
          "https://www.find-tender.service.gov.uk/Search"
        ],
        [
          "OCDS API used (release packages)",
          "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"
        ],
        [
          "Open Government Licence v3.0",
          "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
        ]
      ],
      "licence": "Open Government Licence v3.0",
      "raw": "data/uk-fts/raw/ (compact award index and full notices, gzipped exact response bytes)",
      "reproduce": "python tools/import-find-a-tender.py --offline",
      "collected": "Every award notice of three buyer accounts announced before download (one per level), released 2024-09-01 → 2026-09-01, chosen from a compact index of all 33,457 award releases in the window."
    },
    "note": "United Kingdom · Find a Tender · FCDO, Lincolnshire and Milton Keynes. Published September 2024–August 2026: 516 notices, 1,081 single-supplier awards, mostly GBP. Above-threshold and Procurement Act notices only; separate party IDs may split one supplier."
  },
  "portugal": {
    "path": "data/ted-portugal.json",
    "coverage": "data/ted-portugal-coverage.json",
    "sources": {
      "publisher": "Publications Office of the European Union — TED",
      "links": [
        [
          "TED search · ted.europa.eu",
          "https://ted.europa.eu/"
        ],
        [
          "TED Search API documentation",
          "https://docs.ted.europa.eu/api/latest/search.html"
        ],
        [
          "TED legal notice (reuse authorised)",
          "https://ted.europa.eu/en/legal-notice"
        ]
      ],
      "licence": "Free reuse, commercial or not (Commission Decision 2011/833/EU)",
      "raw": "data/ted-portugal/raw/ (official eForms XML gzipped)",
      "reproduce": "python tools/import-ted-cohorts.py --cohort portugal --offline",
      "collected": "Every TED award notice (can-standard) of three buyers announced before download, published 2024-09-01 → 2026-09-01, matched by identifier and its spelling variants."
    },
    "note": "Portugal · TED · Infraestruturas de Portugal, Cávado and Lisboa. Published September 2024–August 2026: 442 notices, 488 awarded lots, amounts in EUR. Below-threshold purchases are absent; 137 multi-winner results excluded. Cávado notices lack winning-tender links."
  },
  "czechia": {
    "path": "data/ted-czechia.json",
    "coverage": "data/ted-czechia-coverage.json",
    "sources": {
      "publisher": "Publications Office of the European Union — TED",
      "links": [
        [
          "TED search · ted.europa.eu",
          "https://ted.europa.eu/"
        ],
        [
          "TED Search API documentation",
          "https://docs.ted.europa.eu/api/latest/search.html"
        ],
        [
          "TED legal notice (reuse authorised)",
          "https://ted.europa.eu/en/legal-notice"
        ]
      ],
      "licence": "Free reuse, commercial or not (Commission Decision 2011/833/EU)",
      "raw": "data/ted-czechia/raw/ (official eForms XML gzipped)",
      "reproduce": "python tools/import-ted-cohorts.py --cohort czechia --offline",
      "collected": "Every TED award notice (can-standard) of three buyers announced before download, published 2024-09-01 → 2026-09-01, matched by IČO and its spelling variants."
    },
    "note": "Czechia · TED · Finance, Moravian-Silesian Region and Ostrava (including districts sharing its IČO). Published September 2024–August 2026: 661 notices, 630 awarded lots, CZK or EUR. Below-threshold purchases are absent; 122 results with multiple or missing winning references excluded."
  },
  "korea": {
    "remote": "korea",
    "coverage": "meta.json",
    "sources": {
      "publisher": "Public Procurement Service (조달청) — KONEPS (나라장터), open-standard contract data on data.go.kr",
      "links": [
        [
          "KONEPS (나라장터)",
          "https://www.g2b.go.kr/"
        ],
        [
          "Dataset page · data.go.kr (조달청_공공데이터개방표준서비스)",
          "https://www.data.go.kr/data/15058815/openapi.do"
        ],
        [
          "Data files used (separate host)",
          "@KOREA/"
        ]
      ],
      "licence": "data.go.kr: no restriction on use (이용허락범위 제한 없음); source attributed",
      "raw": "private cache (weekly API responses); published files: tools/build-korea-site.py",
      "reproduce": "python tools/fetch-korea-opnstd-contracts.py, tools/normalize-korea-opnstd.py, tools/build-korea-site.py",
      "collected": "Every contract published in the open-standard contract service with a contract or change date from 1 September 2024 to 1 September 2026, national download (all contracting institutions)."
    },
    "note": "South Korea · KONEPS · every contracting institution, contracts dated September 2024–August 2026 (2.7 million). Browse all institutions with sequential static-file scans, or choose a buyer. Korean checks are not set yet: contracts are shown for browsing and are not assessed. Amounts in KRW; the full record is on KONEPS."
  },
  "romania": {
    "path": "data/ted-romania.json",
    "coverage": "data/ted-romania-coverage.json",
    "sources": {
      "publisher": "Publications Office of the European Union — TED",
      "links": [
        [
          "TED search · ted.europa.eu",
          "https://ted.europa.eu/"
        ],
        [
          "TED Search API documentation",
          "https://docs.ted.europa.eu/api/latest/search.html"
        ],
        [
          "TED legal notice (reuse authorised)",
          "https://ted.europa.eu/en/legal-notice"
        ]
      ],
      "licence": "Free reuse, commercial or not (Commission Decision 2011/833/EU)",
      "raw": "data/ted-romania/raw/ (official eForms XML gzipped)",
      "reproduce": "python tools/import-ted-cohorts.py --cohort romania --offline",
      "collected": "Every TED award notice (can-standard) of three buyers announced before download, published 2024-09-01 → 2026-09-01, matched by identifier and its spelling variants."
    },
    "note": "Romania · TED · Finance, Cluj county and Cluj-Napoca. Published September 2024–August 2026: 299 notices, 321 awarded lots, RON or EUR. Below-threshold purchases are absent; 289 multi-winner results excluded."
  }
};
