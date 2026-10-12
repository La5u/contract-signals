# Paris BOAMP ↔ DECP: exact TED notice/version investigation

## XML follow-up — three exact award versions verified

After the initial 12-attempt discovery stage, a **separately bounded five-attempt XML stage** fetched only the five already discovered award URLs. Its public evidence is [`../data/paris-ted-version-evidence.json`](../data/paris-ted-version-evidence.json): it retains the original 12 attempts and adds five, with explicit `requestAccounting` (17 total TED-stage attempts). The separate Paris-convention investigation used another eight requests: **25 new attempts in this overall follow-up**, not 25 XML downloads.

| BOAMP | Exact TED award | XML outcome | BOAMP/TED UUID + procedure UUID + version |
|---|---|---|---|
| 25-21317 | [126421-2025](https://ted.europa.eu/en/notice/-/detail/126421-2025) | HTTP 200, 38,387 bytes | Verified, version `01` |
| 25-21329 | [129139-2025](https://ted.europa.eu/en/notice/-/detail/129139-2025) | HTTP 200, 17,150 bytes | Verified, version `01` |
| 25-37616 | [218409-2025](https://ted.europa.eu/en/notice/-/detail/218409-2025) | HTTP 429, 169 bytes | Not verified; no retry/bypass |
| 25-45958 | [264382-2025](https://ted.europa.eu/en/notice/-/detail/264382-2025) | HTTP 429, 169 bytes | Not verified; no retry/bypass |
| 25-47556 | [277338-2025](https://ted.europa.eu/en/notice/-/detail/277338-2025) | HTTP 200, 29,028 bytes | Verified, version `01` |

Acquisition timestamps, exact URLs and body hashes are `/requests/12` through `/requests/16`. XML scalar pointers use expanded namespace names and 1-based sibling indices; JSON pointers in the search evidence remain zero-based. Raw XML remains in the external private cache `~/.cache/contract-signals/paris-ted-xml-followup-20261011/`, not the website. Selected header/contract-reference/date fields are public. Three successful XMLs repeat the same long/compound references already present in BOAMP; **none contains an explicit long-reference-to-short-DECP-ID crosswalk**. The two failure bodies are not parsed as notice evidence.

**A verified BOAMP↔TED notice/version is not a verified BOAMP↔DECP contract link.** No DECP candidate was promoted; no amount or date was changed. This adds exact notice/version corroboration, not independent legal-contract ground truth or a measured accuracy rate.

The original discovery record below is preserved as a historical stage result; its “not downloaded” statements apply only to that initial stage.

## Initial discovery outcome and limits

**Five exact award notice UUIDs were located in official TED search results. No award XML was downloaded, no TED version was independently verified, and no BOAMP↔DECP contract crosswalk was established.** The distinction between a notice identity and a legal-contract identity remains essential.

The investigation used **12 network attempts total**, including documentation discovery. The last attempt executed one exact-identity query and returned ten notices: five target awards and five other notices in their procedures. The ceiling was exhausted immediately after that response. No XML acquisition was attempted after the ceiling; the URLs below are verified publication-number-derived locators, **not fetched XML evidence**. This is a useful discovery result, not a completed XML-version investigation.

A critical correction emerged from the official OpenAPI specification: **`checkQuerySyntax:true` checks syntax but does not execute the search query.** The five initial queries in this investigation were syntax checks, not zero-hit searches. The three earlier FT requests described in `research/public-boamp-decp-investigation.md` also used that parameter. Their empty `/notices` therefore do not establish absence, and should not be read as executed zero-result searches. That earlier file was not edited.

No candidate pair was promoted, rejected anew, reassigned, or normalized. Equal buyer, holder, dates, amounts, procedure UUID, or raw-format patterns cannot supply the missing contract crosswalk.

## Scope and retained BOAMP provenance

Only notices **25-21317, 25-21329, 25-37616, 25-45958, 25-47556** were inspected. Each occurs exactly once in `data/boamp-raw.json.gz`, at zero-based `/records/2322`, `/records/2325`, `/records/5981`, `/records/7653`, `/records/8022`, respectively.

- Raw gzip SHA-256: `e6839c41712d0001c33d200efc9fd31042b280a7dc5f1ac0601ca6acd1f66f9d`.
- Retained snapshot `/retrievedAt`: `2026-09-25T12:05:56.859285+00:00`.
- Decode each record's `/donnees` JSON string before applying the evidence pointers.
- Header prefix **B**: `/EFORMS/ContractAwardNotice`.
- Result prefix **N**: `B/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/efext:EformsExtension/efac:NoticeResult`.
- `B/cbc:ID/#text` is notice UUID; `B/cbc:ContractFolderID` is procedure UUID; `B/cbc:VersionID` is retained notice version. **All five BOAMP versions are `01`**; the fetched search fields do not verify that TED version.
- `/gestion` is also JSON-encoded. Its `REFERENCE/ANNONCE_ANTERIEUR` values are BOAMP predecessor references, not award TED publication numbers.

The machine-readable ledger preserves exact header, extension reference, notice-local contract ID, contract-reference and date pointers. It does not publish contacts, buyer names, supplier names, descriptions, full XML, or whole search responses.

## Exact identity search results

The executed request was POST <https://api.ted.europa.eu/v3/notices/search>, using an OR of five parenthesized terms, each:

```text
notice-identifier="<exact notice UUID>" OR procedure-identifier="<exact procedure UUID>"
```

Request parameters: `fields:["publication-number","notice-identifier","procedure-identifier","publication-date"]`, `scope:"ALL"`, `limit:10`, `page:1`, **`checkQuerySyntax:false`**, `onlyLatestVersions:false`. No FT/substring, buyer-name, title, fuzzy-reference or formatting-normalization query was used. The exact complete request is `/requests/11/requestBody` in the ledger. Official field names are present in `/components/schemas/PublicExpertSearchRequestV1/properties/fields/enum` in the OpenAPI YAML.

Response acquisition: `2026-10-11T10:12:53.490168+00:00`, HTTP 200, 45,513 bytes, SHA-256 `0c2ff9f5f0c6a554b66bf2672405cb312531026605c080d0bf7f7a1185f62756`; `/totalNoticeCount:10`, `/timedOut:false`. The ten returned rows equal the reported count for this one query/page, not an independent certification of TED's entire version history.

| BOAMP award | Exact notice UUID | Exact procedure UUID | TED publication | TED publication date | Response pointer |
|---|---|---|---|---|---|
| 25-21317 | `e1636ae4-00b5-4953-bb91-1326562ab9b2` | `7db0640e-05cd-480c-9b82-27190ec82767` | `126421-2025` | `2025-02-26+01:00` | `/notices/5` |
| 25-21329 | `b5a7b16d-0dac-4247-b831-c3d8ef3e59aa` | `79654cbe-7023-4199-beea-a64ff8594489` | `129139-2025` | `2025-02-26+01:00` | `/notices/6` |
| 25-37616 | `b59a2ac5-a516-4b3a-bae1-9dee55ce7a83` | `a0d77ee6-f0c5-4f69-93a2-0afd86106544` | `218409-2025` | `2025-04-04+02:00` | `/notices/7` |
| 25-45958 | `601ad136-b7b9-41cb-a8c5-d54d6c7181cc` | `dd41474e-9d84-46d0-8c01-e1a5983c4030` | `264382-2025` | `2025-04-24+02:00` | `/notices/8` |
| 25-47556 | `53ccebfe-965a-4586-9094-7fdc4a3e79d0` | `e20da72a-516f-4d5c-8c3c-16d548250107` | `277338-2025` | `2025-04-29+02:00` | `/notices/9` |

The 25-47556 retained BOAMP publication is `2025-04-27`, whereas TED returns April 29. These are separate publication events, not a reason to change the notice UUID or silently reconcile dates.

Exact XML locators, **not downloaded**:

- <https://ted.europa.eu/en/notice/126421-2025/xml>
- <https://ted.europa.eu/en/notice/129139-2025/xml>
- <https://ted.europa.eu/en/notice/218409-2025/xml>
- <https://ted.europa.eu/en/notice/264382-2025/xml>
- <https://ted.europa.eu/en/notice/277338-2025/xml>

## Header/extension citations are not the award publication

No inspected award has its own published TED number in the retained header/extension fields. No predecessor number or placeholder was substituted for it.

| BOAMP | Exact cited references in decoded retained body | BOAMP predecessors in decoded gestion |
|---|---|---|
| 25-21317 | `B/cac:TenderingProcess/cac:NoticeDocumentReference/cbc:ID` = `3f8b0026-4c93-4c52-a89e-adf6f1bb04f2-01` | `24-23927` |
| 25-21329 | `N/efac:SettledContract/cac:NoticeDocumentReference/cbc:ID` = `000000-2025` (placeholder) | None |
| 25-37616 | `B/cac:TenderingProcess/cac:NoticeDocumentReference/cbc:ID` = `0737b64b-ec19-4b47-99e6-e984eb3265f3-01` | `24-139776` |
| 25-45958 | TenderingProcess reference = `6eb206f3-1a1c-46a2-a969-5ed685289c9c-01`; each `N/efac:SettledContract/{0..4}/cac:NoticeDocumentReference/cbc:ID` = `723965-2024` | `24-133353`, `24-141972` |
| 25-47556 | TenderingProcess reference = `48cc9005-524c-4062-b677-e1f990753a20-01`; both `N/efac:SettledContract/{0,1}/cac:NoticeDocumentReference/cbc:ID` = `00000-2025` (placeholder) | `24-131712` |

The notation `{0..4}` above is a table shorthand, not a literal JSON pointer; the ledger enumerates all exact indices.

The executed search also returned:

| TED number | Search pointer | UUID/relation |
|---|---|---|
| `121685-2024` | `/notices/0` | `3f8b0026-4c93-4c52-a89e-adf6f1bb04f2`, cited predecessor of 25-21317 |
| `714215-2024` | `/notices/1` | `48cc9005-524c-4062-b677-e1f990753a20`, cited predecessor of 25-47556 |
| **`723965-2024`** | `/notices/2` | `76fd7a6a-c22a-4a63-b860-7762ba4a31b7`, **predecessor, not award 264382-2025** |
| `767819-2024` | `/notices/3` | `0737b64b-ec19-4b47-99e6-e984eb3265f3`, cited predecessor of 25-37616 |
| `781839-2024` | `/notices/4` | `6eb206f3-1a1c-46a2-a969-5ed685289c9c`, another cited predecessor of 25-45958 |

The `-01` suffixes in retained UUID citations are preserved, not stripped from stored evidence. Their base UUIDs appear in search metadata; predecessor version `01` was not independently checked in XML.

## DECP pair gate remains closed

The retained full contract references are unchanged:

- 25-21317: `20242024S05075`, `20242024S05079`, `20242024S05078`. Current LOT-0001 candidates include `2024S05075` and `2024S05079`; the latter reference pattern belongs to another notice-local contract/lot, as already documented.
- 25-21329: `2025S015900000 / 2025HA0001GR` versus candidate `2025S01590`. The compound reference must not be collapsed into one buyer's contract.
- 25-37616: `2025F026500000` versus `2025F02650`.
- 25-45958: references `2025S029110000` through `2025S029150000`; candidate LOT-0005 uses `2025S02915`.
- 25-47556: `2025F026480000`, `2025F026490000`; candidate LOT-0001 uses `2025F02648`.

Contract conclusion and award-decision dates are separate scalar fields in the ledger, as are BOAMP/TED publication dates. Notice-local `CON-*`/`TEN-*` identifiers do not equal DECP contract IDs. Repeated-year removal, terminal-zero removal, splitting compound references, or amount agreement is not an explicit source crosswalk.

**`exactCrosswalkForReview:false` for every discovery and the overall ledger.** No published source uniquely joins buyer SIRET `21750001600019`, the full declared notice contract reference, and a current DECP contract identifier in this investigation. The search response only supplies notice/procedure/publication identities. Even an eventual UUID/version-confirmed XML would need separate explicit crosswalk evidence before promoting a candidate.

## Request accounting, documentation and privacy

All attempts, including the failed documentation path, are retained in order in `/requests`. Each has its source URL, request body where applicable, UTC start timestamp, HTTP status, transferred byte count and SHA-256. Six attempts were documentation acquisition/discovery, five were syntax-only checks, and one was an executed exact query.

| Attempt | Purpose | HTTP |
|---:|---|---:|
| 1 | `https://docs.ted.europa.eu/api/latest/index.html` | 200 |
| 2 | `https://docs.ted.europa.eu/api/latest/search.html` (anonymous Search API documentation) | 200 |
| 3 | `https://api.ted.europa.eu/v3/api-docs` (unsuccessful OpenAPI path) | 404 |
| 4–8 | Individual exact notice/procedure UUID **syntax checks only** | 200 |
| 9 | Swagger initializer, `/swagger-ui/swagger-initializer.js` | 200 |
| 10 | Discovered `/v3/api-docs/swagger-config` | 200 |
| 11 | Discovered official `/api-v3.yaml` | 200 |
| 12 | Executed combined exact-identity query | 200 |

Official OpenAPI URL: <https://api.ted.europa.eu/api-v3.yaml>, fetched `2026-10-11T10:11:58.023337+00:00`, SHA-256 `434a0ef814bfeb3826bd005d243d2dbee0cad264edeb1c9584f42c8621f0c444`. Exact semantic locator: `/components/schemas/PublicExpertSearchRequestV1/properties/checkQuerySyntax/description`. Its description explicitly says that when true, the query syntax is checked **but the search query is not executed**. The ledger contains a short scalar paraphrase, not a copied documentation body. The first helper's JSON-minimization diagnostic for HTML documentation was not treated as an HTTP failure.

Every transfer was HTTPS-only, **15-second maximum elapsed request time**, at most **2 MiB body**, no redirects, no retries, no authentication, no challenge bypass, and no buyer contact. No further requests are authorized or suggested as already performed by this report.

Private cache: `~/.cache/contract-signals/paris-ted-exact-20261011/`; acquisition/replay directories mode 0700, response/manifest files mode 0600. Raw search responses may contain links or incidental text, and remain private. There is no raw XML in the repository or cache from this run. Public JSON contains only selected identifier/date scalars, exact pointers, request/provenance metadata and conservative classifications.

## Reproduction

Only the four task-owned new files were created. Existing dataset/link artifacts, scripts, HANDOFF and prior research were left untouched. No commit or push was made.

Default is **no network** and needs only the retained repository BOAMP snapshot:

```sh
python tools/investigate-paris-ted.py
```

Public minimized evidence can be replayed without any private cache:

```sh
python tools/investigate-paris-ted.py --replay-public data/paris-ted-link-evidence.json
python -m unittest discover -s tests -p test_investigate_paris_ted.py -v
```

Explicit offline private-cache processing, reproducing the current public ledger:

```sh
python tools/investigate-paris-ted.py \
  --cached ~/.cache/contract-signals/paris-ted-exact-20261011/replay \
  --output /tmp/paris-ted-replayed.json
cmp /tmp/paris-ted-replayed.json data/paris-ted-link-evidence.json
```

For a **separately authorized future run**, `--fetch NEW_PRIVATE_DIRECTORY --budget N` is mutually exclusive with cache/public replay. The directory must be new and outside the repository; existing acquisition paths are refused, so there are no implicit retries. Budget must be 1–12 and must subtract any prior attempts in that investigation. The corrected plan executes one exact query, then derives official XML URLs only for rows whose **notice UUID and procedure UUID both match** a target, never for a predecessor or an arbitrary returned URL. XML processing requires award root type, exact notice UUID, exact procedure UUID and retained `VersionID` before marking the award version verified. It still does not claim a DECP crosswalk. No future run was performed here.

Eleven tests cover synthetic reference preservation, search/XML privacy (including nested contact IDs), version/procedure mismatch and duplicate-header refusal, predecessor separation, syntax-only semantics, request/body bounds, exclusive private acquisition, offline default execution, cache hash/ceiling checks, and replay of the public discovery and version evidence. Separate XML-stage accounting and the two actual HTTP-429 failures are regression-tested.

Replay the new minimized version evidence without private cache or network:

```sh
python tools/investigate-paris-ted.py --replay-public data/paris-ted-version-evidence.json
```

The performed follow-up command was:

```sh
python tools/investigate-paris-ted.py \
  --fetch "$HOME/.cache/contract-signals/paris-ted-xml-followup-20261011" \
  --xml-discoveries data/paris-ted-link-evidence.json --budget 5 \
  --output data/paris-ted-version-evidence.json
```

Do not repeat that command or overwrite its acquisition directory. Future acquisitions require a new path and separately reviewed request budget; rate-limit failures are not permission to retry or bypass controls. `priorDiscoveryLedgerSha256` fingerprints the parsed prior JSON object serialized with sorted keys, UTF-8, `ensure_ascii=false` and Python's default JSON separators, rather than exact input-file bytes.
