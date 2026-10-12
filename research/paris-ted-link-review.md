# Paris BOAMP ↔ DECP: exact TED notice/version investigation

## Outcome

**Three exact BOAMP–TED award versions were verified; two remain unresolved after HTTP 429. No BOAMP–DECP contract link was verified, and no candidate, amount or date was changed.** Successful XMLs repeat BOAMP's long/compound references without linking them to short DECP IDs.

Evidence: [`../data/paris-ted-version-evidence.json`](../data/paris-ted-version-evidence.json). Discovery used 12 attempts, XML follow-up five: **17 TED attempts**, or **25** including the separate eight-request Paris-convention investigation.

| BOAMP | Exact TED award | XML outcome | Verified version |
|---|---|---|---|
| 25-21317 | [126421-2025](https://ted.europa.eu/en/notice/-/detail/126421-2025) | HTTP 200, 38,387 bytes | `01` |
| 25-21329 | [129139-2025](https://ted.europa.eu/en/notice/-/detail/129139-2025) | HTTP 200, 17,150 bytes | `01` |
| 25-37616 | [218409-2025](https://ted.europa.eu/en/notice/-/detail/218409-2025) | HTTP 429, 169 bytes | Unresolved |
| 25-45958 | [264382-2025](https://ted.europa.eu/en/notice/-/detail/264382-2025) | HTTP 429, 169 bytes | Unresolved |
| 25-47556 | [277338-2025](https://ted.europa.eu/en/notice/-/detail/277338-2025) | HTTP 200, 29,028 bytes | `01` |

Exact XML URLs: <https://ted.europa.eu/en/notice/126421-2025/xml>, <https://ted.europa.eu/en/notice/129139-2025/xml>, <https://ted.europa.eu/en/notice/218409-2025/xml>, <https://ted.europa.eu/en/notice/264382-2025/xml>, <https://ted.europa.eu/en/notice/277338-2025/xml>. Failure bodies are not notice evidence.

## Search correction and identities

**`checkQuerySyntax:true` checks syntax without executing the search.** The initial five queries and three earlier FT requests in `research/public-boamp-decp-investigation.md` were syntax checks. Empty `/notices` does not establish absence.

Official specification: <https://api.ted.europa.eu/api-v3.yaml>, `/components/schemas/PublicExpertSearchRequestV1/properties/checkQuerySyntax/description`. Documentation: <https://docs.ted.europa.eu/api/latest/index.html>, <https://docs.ted.europa.eu/api/latest/search.html>; discovery also used <https://api.ted.europa.eu/v3/api-docs> (404), `/swagger-ui/swagger-initializer.js` and `/v3/api-docs/swagger-config`.

The executed POST to <https://api.ted.europa.eu/v3/notices/search> used an OR of five terms:
`notice-identifier="<exact notice UUID>" OR procedure-identifier="<exact procedure UUID>"`.
Parameters: `fields:["publication-number","notice-identifier","procedure-identifier","publication-date"]`, `scope:"ALL"`, `limit:10`, `page:1`, `checkQuerySyntax:false`, `onlyLatestVersions:false`. Full request: `/requests/11/requestBody`; field enum: `/components/schemas/PublicExpertSearchRequestV1/properties/fields/enum`.

On 2026-10-11T10:12:53.490168+00:00 it returned HTTP 200, 45,513 bytes, `totalNoticeCount:10`, `timedOut:false`: five awards and five other notices. This covers that query/page, not TED's whole version history.

| BOAMP | Notice UUID | Procedure UUID | TED publication date | Search pointer |
|---|---|---|---|---|
| 25-21317 | `e1636ae4-00b5-4953-bb91-1326562ab9b2` | `7db0640e-05cd-480c-9b82-27190ec82767` | `2025-02-26+01:00` | `/notices/5` |
| 25-21329 | `b5a7b16d-0dac-4247-b831-c3d8ef3e59aa` | `79654cbe-7023-4199-beea-a64ff8594489` | `2025-02-26+01:00` | `/notices/6` |
| 25-37616 | `b59a2ac5-a516-4b3a-bae1-9dee55ce7a83` | `a0d77ee6-f0c5-4f69-93a2-0afd86106544` | `2025-04-04+02:00` | `/notices/7` |
| 25-45958 | `601ad136-b7b9-41cb-a8c5-d54d6c7181cc` | `dd41474e-9d84-46d0-8c01-e1a5983c4030` | `2025-04-24+02:00` | `/notices/8` |
| 25-47556 | `53ccebfe-965a-4586-9094-7fdc4a3e79d0` | `e20da72a-516f-4d5c-8c3c-16d548250107` | `2025-04-29+02:00` | `/notices/9` |

25-47556's BOAMP publication date is 2025-04-27; TED's April 29 is a separate publication event.

## Retained BOAMP and predecessor scope

`data/boamp-raw.json.gz`, retrieved 2026-09-25T12:05:56.859285+00:00, contains each target once at `/records/2322`, `2325`, `5981`, `7653`, `8022`, respectively. Decode `/donnees` and `/gestion` JSON strings. B = `/EFORMS/ContractAwardNotice`; N = `B/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/efext:EformsExtension/efac:NoticeResult`. Header `cbc:ID/#text`, `cbc:ContractFolderID`, `cbc:VersionID` supply notice UUID, procedure UUID and version; all BOAMP versions are `01`.

Retained header/extension citations are predecessors or placeholders, not the award's TED number:
- 25-21317: `3f8b0026-4c93-4c52-a89e-adf6f1bb04f2-01`; BOAMP predecessor `24-23927`; TED `121685-2024` (`/notices/0`).
- 25-21329: settled-contract citation `000000-2025`; no predecessor.
- 25-37616: `0737b64b-ec19-4b47-99e6-e984eb3265f3-01`; `24-139776`; TED `767819-2024` (`/notices/3`).
- 25-45958: `6eb206f3-1a1c-46a2-a969-5ed685289c9c-01` and five settled-contract citations `723965-2024`; `24-133353`, `24-141972`. TED `781839-2024` (`/notices/4`) and `723965-2024` (`/notices/2`, UUID `76fd7a6a-c22a-4a63-b860-7762ba4a31b7`) are predecessors, not award `264382-2025`.
- 25-47556: `48cc9005-524c-4062-b677-e1f990753a20-01`, two `00000-2025` placeholders; `24-131712`; TED `714215-2024` (`/notices/1`).

Stored citation suffixes remain intact; predecessor XML versions were not verified.

## DECP gate

Full references remain verbatim:
- 25-21317: `20242024S05075`, `20242024S05079`, `20242024S05078`. LOT-0001 candidates are `2024S05075` and `2024S05079`; the latter pattern belongs to another notice-local lot.
- 25-21329: `2025S015900000 / 2025HA0001GR` versus `2025S01590`; preserve both buyer scopes.
- 25-37616: `2025F026500000` versus `2025F02650`.
- 25-45958: `2025S029110000` through `2025S029150000`; LOT-0005 candidate `2025S02915`.
- 25-47556: `2025F026480000`, `2025F026490000`; LOT-0001 candidate `2025F02648`.

Every discovery has `exactCrosswalkForReview:false`. Promotion needs an explicit unique buyer `21750001600019` + full reference + DECP ID link. Notice/procedure/version agreement, local `CON-*`/`TEN-*` IDs, shortening patterns and amount agreement cannot supply it. Conclusion, award-decision and publication dates retain separate meanings.

## Reproduction and acquisition limits

The evidence files retain acquisition metadata, hashes and exact scalar pointers; XML pointers use expanded namespaces and 1-based siblings, JSON uses zero-based indices. Raw responses stay private in `~/.cache/contract-signals/paris-ted-exact-20261011/` and `~/.cache/contract-signals/paris-ted-xml-followup-20261011/` (directories 0700, files 0600). Transfers were HTTPS-only, 15 seconds maximum, 2 MiB maximum, without redirects, retries, authentication or bypass.

Offline commands:
```sh
python tools/investigate-paris-ted.py
python tools/investigate-paris-ted.py --replay-public data/paris-ted-link-evidence.json
python tools/investigate-paris-ted.py --replay-public data/paris-ted-version-evidence.json
python -m unittest discover -s tests -p test_investigate_paris_ted.py -v
python tools/investigate-paris-ted.py \
  --cached ~/.cache/contract-signals/paris-ted-exact-20261011/replay \
  --output /tmp/paris-ted-replayed.json
cmp /tmp/paris-ted-replayed.json data/paris-ted-link-evidence.json
```

Historical XML follow-up command (do not repeat or overwrite its directory):
```sh
python tools/investigate-paris-ted.py \
  --fetch "$HOME/.cache/contract-signals/paris-ted-xml-followup-20261011" \
  --xml-discoveries data/paris-ted-link-evidence.json --budget 5 \
  --output data/paris-ted-version-evidence.json
```

Future `--fetch NEW_PRIVATE_DIRECTORY --budget N` requires separate authorization, a new external directory and a reviewed budget of 1–12 accounting for prior attempts. Fetch is exclusive with cache/public replay. Only exact notice+procedure matches may yield XML URLs; verification also requires award root type and retained VersionID. Keep rate-limit failures unresolved.

Eleven tests cover privacy, exact identity/version gates, duplicate headers, predecessor separation, syntax-only semantics, acquisition bounds, offline replay and the two HTTP-429 failures.
