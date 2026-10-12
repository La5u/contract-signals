# DECP CPV check-digit review

## Integration follow-up

The candidate audit below preserves the **pre-correction** row/source hashes. After verifying those hashes and each original CPV, all **165** exact-prefix candidates were applied locally: **86 cities + 79 Paris/Ardèche**. No other normalized row fields changed. Raw evidence and initial alternatives remain untouched.

`data/decp-cpv-vocabulary.json` pins all **9,454** official main-vocabulary codes, the TED URL, archive hash and XML-member hash. `tools/decp_feeds.py:cpv_lookup` uses this vocabulary during future feed/portal imports, unions retained full-code observations, and withholds any conflicting prefix. It never calculates a digit or fuzzy-matches descriptions.

Coverage and BOAMP↔DECP link artifacts were rebuilt, and `node tools/review-score-v3.cjs` was rerun. Positive/zero counts and indicator-fire counts are unchanged; evaluated-check coverage increased (cities 3.23→3.26, Paris/Ardèche 3.73→3.74). Thresholds and weights were not changed. The empty notice-review v1 freeze remains untouched; `v2-cpv/plan.json` binds the corrected snapshots.

Regression coverage: `tests/test_decp_cpv_integration.py` verifies exact lookup, ambiguity/conflict refusal and vocabulary membership of all 5,286 current rows. Nothing was committed, pushed or deployed.

## Original candidate audit

The helper itself is candidate-only and never rewrites datasets. The findings and artifact below describe its pre-correction run.

## Findings

Eight-digit targets: 165; safe candidates: 165.
Statuses: `{"safe-exact-prefix": 165}`.
Distinct exact prefixes: 103.
Targets by cohort: `{"data/decp-cities.json": 86, "data/decp-history.json": 79}`.
Safe candidate support: `{"official-vocabulary-only": 105, "retained-full-code-supported": 60}`.
Existing codes: `{"full-in-vocabulary": 5121}`.

The requested ~128 is not the current snapshot count: both normalized cohorts are scanned, including feed and portal rows. No arbitrary cutoff is used.

## Method and sources

`tools/decp_feeds.py:cpv_lookup` already maps a prefix only when all retained full-code observations agree, including initial alternatives. It is cohort-local; this tool instead inspects the four retained raw extracts and optionally the official main CPV 2008 vocabulary. Feed/portal extracts currently supply eight-digit codes, not check digits. Full-code syntax alone is not vocabulary validation.

The official download is linked from https://ted.europa.eu/en/simap/cpv. Only `cpv_2008.xml` (main vocabulary) is read, never supplementary codes. Raw archive stays in a private external cache. No checksum algorithm, fuzzy match, description inference, nearest prefix, or truncation is used. All full-code evidence must agree exactly; ambiguous prefixes and prefixes absent from an available official vocabulary remain unresolved. Without the vocabulary, absence remains unknown rather than being labelled nonexistent.

## Reproduce and integrate

```sh
python tools/recover-decp-cpv.py --fetch --official --output research/decp-cpv-review.md
python tools/recover-decp-cpv.py --official --output /tmp/decp-cpv-candidates.json --format json
python -m unittest discover -s tests -p test_recover_decp_cpv.py
```

Offline runs omit `--fetch`; omit `--official` for retained-only review. The JSON below is the deterministic public-safe candidate artifact. It exports only CPV codes, relative source paths, row indices and hashes, never descriptions, names, supplier identifiers, feed UIDs or contract IDs. Indices are zero-based. Source hashes cover stored bytes (including gzip); row hashes cover canonical sorted-key UTF-8 JSON.

For another snapshot, integration requires a separately reviewed change: verify dataset/source hashes and the row hash plus exact old CPV, then apply only `safe-exact-prefix` candidates. The pre-correction candidates below have already been applied locally and must not be replayed against changed row hashes. Preserve provenance and all conflicts; do not rewrite initial alternatives or raw evidence. Prefer passing a reviewed unique mapping to `feed_fields` when rebuilding feed/portal cohorts. Rebuild dependent context/coverage and run regression tests: adding digits can make rows eligible for CPV-based contexts. This tool never applies changes; existing invalid full codes are counted, not repaired.

## Exact mappings, provenance and row candidates

```json
{
  "candidates": [
    {
      "candidateCpv": "92521000-9",
      "dataset": "data/decp-cities.json",
      "oldCpv": "92521000",
      "rowIndex": 1858,
      "rowSha256": "43e635bb6a3afc789d3061131bdaf5ccc35955880f9b21ad5751443b17fdc93f",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45431100-8",
      "dataset": "data/decp-cities.json",
      "oldCpv": "45431100",
      "rowIndex": 1894,
      "rowSha256": "2b0f0f25fef3141b8597eeac15369f8bab59054c8fd6f6ff275df764123b01e3",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45320000-6",
      "dataset": "data/decp-cities.json",
      "oldCpv": "45320000",
      "rowIndex": 1899,
      "rowSha256": "e9ddfbddde6c35861e94a866d19645c056d2f0d136da5556e1f14ac900ba4d58",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "37000000-8",
      "dataset": "data/decp-cities.json",
      "oldCpv": "37000000",
      "rowIndex": 1915,
      "rowSha256": "297fa46efd5b1d2162ad9258880dcd08b145303ed4b4327352655aa07057a991",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "31000000-6",
      "dataset": "data/decp-cities.json",
      "oldCpv": "31000000",
      "rowIndex": 1916,
      "rowSha256": "6940501fb63f9a67d7cccc0eba1afafeb89c3224b4e0282e4c74313cb054d1c1",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39710000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "39710000",
      "rowIndex": 1917,
      "rowSha256": "5bfe1f8e3be61cc0c17d58e81d7ae50590b844bef5f2cede7032a6af5de44946",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "37000000-8",
      "dataset": "data/decp-cities.json",
      "oldCpv": "37000000",
      "rowIndex": 1918,
      "rowSha256": "a00724eba0b542da30be20c8cddb041f84aef54618f70fa7b3eb36bbf39a71c2",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "03300000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "03300000",
      "rowIndex": 1921,
      "rowSha256": "e0483e9fed4597dfd3d71d1a156f68d7857b9887937c7da3d98557814a10a332",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "03200000-3",
      "dataset": "data/decp-cities.json",
      "oldCpv": "03200000",
      "rowIndex": 1922,
      "rowSha256": "9175a52556dab62eb04728c103f2d50dd940ddb1f0e550541f3eee209fa1e840",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15500000-3",
      "dataset": "data/decp-cities.json",
      "oldCpv": "15500000",
      "rowIndex": 1923,
      "rowSha256": "688695c837433186b2e3c1a39cd1161fa5a8da7376c094ceb746691ed0af7e5d",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15600000-4",
      "dataset": "data/decp-cities.json",
      "oldCpv": "15600000",
      "rowIndex": 1924,
      "rowSha256": "a19d4a2fe605deec7aa8f5bc7c4381df401da39b13ea5cadc93073b8d806f4a9",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15320000-7",
      "dataset": "data/decp-cities.json",
      "oldCpv": "15320000",
      "rowIndex": 1925,
      "rowSha256": "afdb696a769e65f60701b49fda6cc4fb61889519d828d11f6bcd14eee162e0a5",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15910000-0",
      "dataset": "data/decp-cities.json",
      "oldCpv": "15910000",
      "rowIndex": 1926,
      "rowSha256": "57833aed82c3b130349ae9421b5716590ff41204e6bac9b6720525a5a9ead7f7",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "79417000-0",
      "dataset": "data/decp-cities.json",
      "oldCpv": "79417000",
      "rowIndex": 1945,
      "rowSha256": "2d51840a82a9e6c6a8c12c3cde07d0f270011f94d6691ddbcb7969fa14c8ce7f",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71620000-0",
      "dataset": "data/decp-cities.json",
      "oldCpv": "71620000",
      "rowIndex": 1969,
      "rowSha256": "048e6266f5e8f9544be8e2f632a931814daac064d62be151a9ebbb3ae23e95d6",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "92111230-3",
      "dataset": "data/decp-cities.json",
      "oldCpv": "92111230",
      "rowIndex": 1977,
      "rowSha256": "c967be92ab634c7f8224112a10526a1306bb8d238f10b225672cc760d669281f",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45261220-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "45261220",
      "rowIndex": 1996,
      "rowSha256": "0a8f9a825294891352bbc5b9910c11ba7d2b0dedca51e1f0eede666b64915df1",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "34114400-3",
      "dataset": "data/decp-cities.json",
      "oldCpv": "34114400",
      "rowIndex": 2003,
      "rowSha256": "4f7fe6b38742a9bd276590a8bee33159beed84f77146dc17269dc6c1e1450919",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15300000-1",
      "dataset": "data/decp-cities.json",
      "oldCpv": "15300000",
      "rowIndex": 2006,
      "rowSha256": "c365143d9e15212dd4d05d6d8da95e267ef0b887081ba4d5b59b63c738ed129d",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "85312510-7",
      "dataset": "data/decp-cities.json",
      "oldCpv": "85312510",
      "rowIndex": 2007,
      "rowSha256": "fdbb7eed090fc5f550576a960ce5a7ef4c20f8647ce1d22757e12374dbca5d34",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15900000-7",
      "dataset": "data/decp-cities.json",
      "oldCpv": "15900000",
      "rowIndex": 2025,
      "rowSha256": "f6ba8a152e11c373c7d11acb897c30bc7b6efe00c9927795a1603fffb5f6e1cd",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71352000-0",
      "dataset": "data/decp-cities.json",
      "oldCpv": "71352000",
      "rowIndex": 2030,
      "rowSha256": "84b10e0073ae61e6e2cecbb6ab3766fa7d549ab1a419d0db2eb9ba657aec10ec",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39142000-9",
      "dataset": "data/decp-cities.json",
      "oldCpv": "39142000",
      "rowIndex": 2047,
      "rowSha256": "0a6cdbf4880568e124beb0b09d57de670b7d13fdc957c5502ab1928843ba3b94",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "44316400-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "44316400",
      "rowIndex": 2048,
      "rowSha256": "bee0d360e084c24ba94efd7498b5f882ad923529e3e1fb096eae98b512cca00a",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "44511000-5",
      "dataset": "data/decp-cities.json",
      "oldCpv": "44511000",
      "rowIndex": 2049,
      "rowSha256": "c67f291bae5214180aa58ac4e1f4d69e4c581603932412b5b5f4ee6ef64249d6",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "44316400-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "44316400",
      "rowIndex": 2050,
      "rowSha256": "3307a51cd219d3a6b3b6f0fbb5a99aafe778ff0c2b27f9a8b14ddbb8f4c06f1b",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "16160000-4",
      "dataset": "data/decp-cities.json",
      "oldCpv": "16160000",
      "rowIndex": 2051,
      "rowSha256": "22bda10d11f8b0aec84211866da1d23f2ffc26e04987d5e4df11ae92d40cf626",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "44115220-7",
      "dataset": "data/decp-cities.json",
      "oldCpv": "44115220",
      "rowIndex": 2052,
      "rowSha256": "51b722c934edd631112837473d5897c94f21bf241317b510954c835a2316f010",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39142000-9",
      "dataset": "data/decp-cities.json",
      "oldCpv": "39142000",
      "rowIndex": 2053,
      "rowSha256": "0292d35078132397e90ae21919cc8fb9038fdb40c7279b4d373ca3c465f974f8",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "43261000-0",
      "dataset": "data/decp-cities.json",
      "oldCpv": "43261000",
      "rowIndex": 2056,
      "rowSha256": "e8639af86d5fbd3208d4481efd1048a34a00a7e98425c3f2910dd03a63c90077",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "03413000-8",
      "dataset": "data/decp-cities.json",
      "oldCpv": "03413000",
      "rowIndex": 2058,
      "rowSha256": "834832c6e6d610dee3cc2243ba68989b1cea95a0f0c49beba0de1e974c043ff2",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "31224500-7",
      "dataset": "data/decp-cities.json",
      "oldCpv": "31224500",
      "rowIndex": 2061,
      "rowSha256": "f843e8f7f859b0e5cef7cbc7bb4030659bfdd9e1e4ca8f2ed4ceb7b0703d3ab1",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "85210000-3",
      "dataset": "data/decp-cities.json",
      "oldCpv": "85210000",
      "rowIndex": 2063,
      "rowSha256": "5e225fa59014f4f464734b0d6a710188a62dac35fbae159f14f85d3c40c6b546",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50720000-8",
      "dataset": "data/decp-cities.json",
      "oldCpv": "50720000",
      "rowIndex": 2066,
      "rowSha256": "d65dd1b61657277f721d423cb68c217cd889e0e3642d00571fbd6bbe91cd194a",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50730000-1",
      "dataset": "data/decp-cities.json",
      "oldCpv": "50730000",
      "rowIndex": 2071,
      "rowSha256": "20c7ee41e5764edac1803837d083e5fc5ef5dfa050257609337fe789c1b15af8",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45112340-0",
      "dataset": "data/decp-cities.json",
      "oldCpv": "45112340",
      "rowIndex": 2077,
      "rowSha256": "965229591a83aa3a19f4a49a31a11a05d0fa4e504ac2cc1292a83facc2703774",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45453100-8",
      "dataset": "data/decp-cities.json",
      "oldCpv": "45453100",
      "rowIndex": 2078,
      "rowSha256": "019c82cb826f39c1058a467ad90bb051d2b961413273a87e2528dab928bec657",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45223000-6",
      "dataset": "data/decp-cities.json",
      "oldCpv": "45223000",
      "rowIndex": 2079,
      "rowSha256": "a2bf3a1a2069f44eba3dc5484664e82bf8946db581fb7d1fceea125aceba2e9c",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45262300-4",
      "dataset": "data/decp-cities.json",
      "oldCpv": "45262300",
      "rowIndex": 2080,
      "rowSha256": "d26fd63896cf7afc7ad843748de4e6a942409b5d708ff5782a46c9f166fb5848",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45453100-8",
      "dataset": "data/decp-cities.json",
      "oldCpv": "45453100",
      "rowIndex": 2083,
      "rowSha256": "dce198c9f83ef5b9d2cb41fbce6ab72700014caba991a8c0d85b4d142745b487",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45262510-9",
      "dataset": "data/decp-cities.json",
      "oldCpv": "45262510",
      "rowIndex": 2104,
      "rowSha256": "5b4035f1b31b247fc8059dcdcbc81e420aa6c97434d83218e153641473536575",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45262100-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "45262100",
      "rowIndex": 2113,
      "rowSha256": "f4986ec5faee12653f11c915ed5893c373a8a0c266438129ac09bece4fee1523",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45262510-9",
      "dataset": "data/decp-cities.json",
      "oldCpv": "45262510",
      "rowIndex": 2114,
      "rowSha256": "e332952ddc3cb5e8820e2de436802f008b7d3478c17c0a2910085fcaac527eb1",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45232454-9",
      "dataset": "data/decp-cities.json",
      "oldCpv": "45232454",
      "rowIndex": 2120,
      "rowSha256": "c01d6150f0f6c2c86686cfd79e74e2509dc772d4d0ecc25349e3f91ac32bb717",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "03451200-8",
      "dataset": "data/decp-cities.json",
      "oldCpv": "03451200",
      "rowIndex": 2138,
      "rowSha256": "5c91d985f0c513be4be3ac233fb7d26264eaf69f0e8a0c38b880ddbb1d6e288a",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "03144000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "03144000",
      "rowIndex": 2140,
      "rowSha256": "5c9f5c60d55fe2abba2fca50269b0b98a9b7a24a8b953829d3812f62f2bac7cb",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "43324100-1",
      "dataset": "data/decp-cities.json",
      "oldCpv": "43324100",
      "rowIndex": 2141,
      "rowSha256": "ef33862bf364d9aba8cdee50f1ad62200c0a5365658c037db6881462d0c5f8cc",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "09331200-0",
      "dataset": "data/decp-cities.json",
      "oldCpv": "09331200",
      "rowIndex": 2162,
      "rowSha256": "6ba569b41ec0b48f06304eb3104e0fc259dbfcc7656fd979cd4a2ffd6fc1735f",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "34114400-3",
      "dataset": "data/decp-cities.json",
      "oldCpv": "34114400",
      "rowIndex": 2169,
      "rowSha256": "22526b2d0f2958d675bf5f96cb76b85f9303251cb3be8d194409d5041593ac2e",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "85312510-7",
      "dataset": "data/decp-cities.json",
      "oldCpv": "85312510",
      "rowIndex": 2170,
      "rowSha256": "0517684645054d9f9ef3af7ad5230d671ac090ecc50416bc197c45a8170982ba",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "80580000-3",
      "dataset": "data/decp-cities.json",
      "oldCpv": "80580000",
      "rowIndex": 2212,
      "rowSha256": "e07ac901f9c8847bc221a360f6226619a648fc3cc318edf348dcae65ab586a65",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72415000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72415000",
      "rowIndex": 2225,
      "rowSha256": "d92ff5d61c8d0b9e4cdd82dd9a2b178456441a4c44228861a24d1d0c127155b2",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "44113900-4",
      "dataset": "data/decp-cities.json",
      "oldCpv": "44113900",
      "rowIndex": 2233,
      "rowSha256": "7aecd0bc3380374bae483afedd82a09b13e1d6a3b110e3d6ddee98fdf1ada971",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "44113900-4",
      "dataset": "data/decp-cities.json",
      "oldCpv": "44113900",
      "rowIndex": 2234,
      "rowSha256": "4f75d857f1a7ec4547e2b32cfe670895c0a895be66b5f35b798692df33ddb735",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72250000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72250000",
      "rowIndex": 2241,
      "rowSha256": "f9cd4384befabd0b8f898fbd5e83556851b39f8cf6e388274f3c711098a0dbae",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72250000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72250000",
      "rowIndex": 2242,
      "rowSha256": "dec010fa3c2c8be1346456351839dc064971db874aabf58b627177f3eb0a9acb",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72250000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72250000",
      "rowIndex": 2243,
      "rowSha256": "a1a53c506c07b4a8d8b9c3738e3b433c4c7cb3de132b6f37906940fb37d4384a",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72250000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72250000",
      "rowIndex": 2244,
      "rowSha256": "d50e0141e02f33ec3c083d7309bef232d92bfdf687f34367d8e4127d413ed2c2",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72250000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72250000",
      "rowIndex": 2245,
      "rowSha256": "e76a7dc9144b7513f2481595f37e26fd9224de28f7569b8c23d6131c2f99d775",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72250000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72250000",
      "rowIndex": 2246,
      "rowSha256": "638c3666e5a32d1a45791619220417494bd71fca1697d044693cd371629b2aef",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72250000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72250000",
      "rowIndex": 2247,
      "rowSha256": "8309e963c316fa0a1fc78deccdfb82a5892564173b0c8ce0d0c156447f02d569",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72250000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72250000",
      "rowIndex": 2248,
      "rowSha256": "9e31f6319842287e25aefd2d31a75ca11ef3a5d85323d11373c51d3f423987c8",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72250000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72250000",
      "rowIndex": 2249,
      "rowSha256": "68ef25013d2f7ca3452853b916f3b247945a92dd5d2cdb5b35ee272dff0ce26e",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72250000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72250000",
      "rowIndex": 2250,
      "rowSha256": "598d1f2caa8a91b889b886fa8f6549dbd3dc54c2959c21c40f5456cfce0dd430",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72250000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72250000",
      "rowIndex": 2251,
      "rowSha256": "870631bce8d7f8c44af09aa5f665e7cd1a091c94eb04c24302171bc4e1e312ae",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72250000-2",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72250000",
      "rowIndex": 2252,
      "rowSha256": "58e8f648778d76f0979266715889c1267fecd7559b5d13c135481d3acf9e6420",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72315100-7",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72315100",
      "rowIndex": 2253,
      "rowSha256": "7c7d7b98cf6b7d4ee81aaf1b581ae9f551c37e2296181c9ecb506471b91cf3ed",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72315100-7",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72315100",
      "rowIndex": 2254,
      "rowSha256": "814ad1187938ad5a0fa9ea2559e4052ae5f11f6c35dde49de214e9e1c36fc002",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72315100-7",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72315100",
      "rowIndex": 2255,
      "rowSha256": "5b52bc3b75f529ab4e83d58c16812ec571f4b5d0e52f4fafdc473a357e1b42dc",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72315100-7",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72315100",
      "rowIndex": 2256,
      "rowSha256": "df919fd51a1c000c004f7c8de0d2df240feb4335b7a32cef47f8a6747097abe1",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71316000-6",
      "dataset": "data/decp-cities.json",
      "oldCpv": "71316000",
      "rowIndex": 2257,
      "rowSha256": "ba155da84ab8ade40caefb701106136391d76d3a490b0669693027a3a946919e",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71316000-6",
      "dataset": "data/decp-cities.json",
      "oldCpv": "71316000",
      "rowIndex": 2258,
      "rowSha256": "45c642e4591d7aee250db81a4bc619b04a6389c4899b65b876c99fff7f858454",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71316000-6",
      "dataset": "data/decp-cities.json",
      "oldCpv": "71316000",
      "rowIndex": 2259,
      "rowSha256": "97bbdf6f60bffc561a4845197186dfb643f5dbf4785fad1cf6d8863e56cbe04a",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71316000-6",
      "dataset": "data/decp-cities.json",
      "oldCpv": "71316000",
      "rowIndex": 2260,
      "rowSha256": "b611df4d7f68a8691cbce18d728f5db65c9a0f09a1d1ba73987354925e422fd9",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72316000-3",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72316000",
      "rowIndex": 2261,
      "rowSha256": "d4234927c7e4afcd6b665c33bc40834e2f667bc605dbf6f30f87e87f30bc5510",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72316000-3",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72316000",
      "rowIndex": 2262,
      "rowSha256": "061f463748e902055d65e4b252054b1d984e05a7fc23580a17e6a6c48aa8530a",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72316000-3",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72316000",
      "rowIndex": 2263,
      "rowSha256": "1c2b2cccb3741dd3d1cc62c8e7c7a282ac14ebe03ee6aa94ecff074d71347880",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72316000-3",
      "dataset": "data/decp-cities.json",
      "oldCpv": "72316000",
      "rowIndex": 2264,
      "rowSha256": "a7de57842bf2686b3fc8d22a01109fe4c6bb1c476779a69ee664a886a314378c",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "79951000-5",
      "dataset": "data/decp-cities.json",
      "oldCpv": "79951000",
      "rowIndex": 2265,
      "rowSha256": "825b845905b9b8cf993b39bb1702cb860cd3fd1fcfb17739d0e7646c89efd1b7",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15894300-4",
      "dataset": "data/decp-cities.json",
      "oldCpv": "15894300",
      "rowIndex": 2276,
      "rowSha256": "1aa28aa86b418b7c6735c3f85c71f4b80a6597509c6a3d89a5f5f1038e04bc97",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15894000-1",
      "dataset": "data/decp-cities.json",
      "oldCpv": "15894000",
      "rowIndex": 2277,
      "rowSha256": "ed5d9ef9782e9f58d203538999354bbcebc4cd39b591c6a110fd9ee2beeaf089",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "55900000-9",
      "dataset": "data/decp-cities.json",
      "oldCpv": "55900000",
      "rowIndex": 2280,
      "rowSha256": "3ebecc8f40f950c775043497012abd382e130ff1b7b1a24e3f70130e6b281d3d",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "55900000-9",
      "dataset": "data/decp-cities.json",
      "oldCpv": "55900000",
      "rowIndex": 2281,
      "rowSha256": "cac162ce58eb7cde17ed80cf04d211d9ea0242962fcd8aa758f1b97e9f57833f",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "55900000-9",
      "dataset": "data/decp-cities.json",
      "oldCpv": "55900000",
      "rowIndex": 2282,
      "rowSha256": "1d3c266c45f23b1519e83e88db2fce1d3e2a8f935c12add36f73362d8d00614c",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "31000000-6",
      "dataset": "data/decp-cities.json",
      "oldCpv": "31000000",
      "rowIndex": 2284,
      "rowSha256": "2e25763b6d9b484a8cf8edd94f02120d0d58bd6b2ddd114044011241db5dcfa9",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "55240000-4",
      "dataset": "data/decp-cities.json",
      "oldCpv": "55240000",
      "rowIndex": 2285,
      "rowSha256": "6dbf061406b03929d64914a29e2c82b66ba68eff0cbdcb141a4ee756b52d1c43",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "18110000-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "18110000",
      "rowIndex": 5,
      "rowSha256": "319a994399cdb0bfcc2240d304e05b22ed98f3335ac2201daa1ec7985a95fbf2",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "18110000-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "18110000",
      "rowIndex": 6,
      "rowSha256": "8d83b30db348c7675d52251b3f11aa302ac7943184eaa0e61578236fb6715a6d",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "18110000-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "18110000",
      "rowIndex": 7,
      "rowSha256": "6cf0be6857d7b526e77da72e0b948914e68025fd259b1c2762ab03b654ee89fe",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "18110000-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "18110000",
      "rowIndex": 8,
      "rowSha256": "c9e35f92a8dd394540e1ad7b96a877e8cb8abc53960850d5717fffbf39dbbc36",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "18110000-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "18110000",
      "rowIndex": 9,
      "rowSha256": "7ebe7717340e81a1a9571070a862fbb208246d022eae5afd95bd1e4166eac1a1",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "18110000-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "18110000",
      "rowIndex": 10,
      "rowSha256": "fc99800eb03c89849033a4a394767fbee06646696fb0ba9f8bf5f7758daf9170",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "18110000-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "18110000",
      "rowIndex": 11,
      "rowSha256": "3c3ae50a1077fc4c23af288801d416b9705588c9c1824a64975a0ac26ad97351",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "18512200-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "18512200",
      "rowIndex": 12,
      "rowSha256": "070f6ae8e329d0fd9fb7bcf0b9b6dd5086fd2d05d40cda5184e65aef08bf11f2",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "18512200-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "18512200",
      "rowIndex": 13,
      "rowSha256": "0e2fdfc432b274c03391bd186053f65bae4b415682a54a8b5845ad614fd32753",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "18110000-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "18110000",
      "rowIndex": 14,
      "rowSha256": "72d63461303c3f2f6abfa1c19a02dcae8e41e1380a4d8967e57a07cb996ebf20",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "34420000-7",
      "dataset": "data/decp-history.json",
      "oldCpv": "34420000",
      "rowIndex": 15,
      "rowSha256": "096eaa6e4d16ca92702d2c437b52e04a4d885d8003103505f4a8ba02e0ba4a87",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "34422000-7",
      "dataset": "data/decp-history.json",
      "oldCpv": "34422000",
      "rowIndex": 17,
      "rowSha256": "c94e93177c8cabc4cc5264cd2df3cf8a7d4d8690e93288faea81422e78de43da",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "90511100-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "90511100",
      "rowIndex": 37,
      "rowSha256": "55351079b2875ad3789932511118c9b613c411fd19f5ef984fcb3cae6959f6db",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "79311100-8",
      "dataset": "data/decp-history.json",
      "oldCpv": "79311100",
      "rowIndex": 40,
      "rowSha256": "609de93fb4219e38b38efbcd6965c1657893fc9e889ed56d16d7e4932ed0394a",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71315400-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "71315400",
      "rowIndex": 41,
      "rowSha256": "93a5d74f6e180bbe2d1ccfbf4294cc0fd0cd9fd871c684ef456ada3f616465b3",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71315400-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "71315400",
      "rowIndex": 42,
      "rowSha256": "f26b0f6f23efb56e66fae2b0dd80ec2fb12bb0a0b725e6e9bf98e2758d7de676",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "85147000-1",
      "dataset": "data/decp-history.json",
      "oldCpv": "85147000",
      "rowIndex": 48,
      "rowSha256": "278aa046d8bdc85d2ac76b6aad4d8303442c87d608fe47fd32f01d95f7494162",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50312300-8",
      "dataset": "data/decp-history.json",
      "oldCpv": "50312300",
      "rowIndex": 50,
      "rowSha256": "45aa1b81523c7561a5ba6a57e45e5117c2c2ba3ab0f1da7240c692f22f845795",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45421100-5",
      "dataset": "data/decp-history.json",
      "oldCpv": "45421100",
      "rowIndex": 57,
      "rowSha256": "777f3b38c64ff0f39a573bd98871c3cf784293e863acc06cee95be5c66f1cf6b",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "22114000-2",
      "dataset": "data/decp-history.json",
      "oldCpv": "22114000",
      "rowIndex": 68,
      "rowSha256": "3f68a3d4a2236a7f67e2f53e56af851bbbb4000762aa6512e9e0d755cafc7e32",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "22114000-2",
      "dataset": "data/decp-history.json",
      "oldCpv": "22114000",
      "rowIndex": 69,
      "rowSha256": "44c2f07902f1de29cb576a70915c409ec58cae4c9a9a200476736a158e78ae49",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "22114000-2",
      "dataset": "data/decp-history.json",
      "oldCpv": "22114000",
      "rowIndex": 70,
      "rowSha256": "d0f93758014acbc84a6ae21798f06694fcc64b7c41eab2dff7a6b69287e34ac3",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45212140-9",
      "dataset": "data/decp-history.json",
      "oldCpv": "45212140",
      "rowIndex": 78,
      "rowSha256": "f7e18c4528a636251d5b97e63927ea7f98a24adc57c162253ac7f95ad8519023",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "22315000-1",
      "dataset": "data/decp-history.json",
      "oldCpv": "22315000",
      "rowIndex": 85,
      "rowSha256": "74b7c15775f18d40eb4d5357228d5cfdc0ba486141eb9d26f112b7e9390b4a30",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "34144700-5",
      "dataset": "data/decp-history.json",
      "oldCpv": "34144700",
      "rowIndex": 92,
      "rowSha256": "17478409f75bce4fe3f3e685aa70b116d321653606764c26a1fdf4b65988da4d",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "03451000-6",
      "dataset": "data/decp-history.json",
      "oldCpv": "03451000",
      "rowIndex": 120,
      "rowSha256": "23ad7caa7ddf3d67920a83e9130af58b17589709c230c1ad2a0b10d7a3aa490b",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "03451000-6",
      "dataset": "data/decp-history.json",
      "oldCpv": "03451000",
      "rowIndex": 121,
      "rowSha256": "c023b5f9e2588518681f2aab260c09ab6eba0e260836dd7ca7f2adeee39ef9de",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "22114000-2",
      "dataset": "data/decp-history.json",
      "oldCpv": "22114000",
      "rowIndex": 131,
      "rowSha256": "03d899f2b0a980bc2770b2bbef8e098b69bb068a3096fa961912df3b5f1368ed",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "03451000-6",
      "dataset": "data/decp-history.json",
      "oldCpv": "03451000",
      "rowIndex": 196,
      "rowSha256": "e6a6ccaee003e5d1386bedfb665524feb105907068d4afde723853a81c632756",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "44619000-2",
      "dataset": "data/decp-history.json",
      "oldCpv": "44619000",
      "rowIndex": 202,
      "rowSha256": "3bb8c6ae71eb32849f1a9f488b79b081e73986301332e6db02868d8f38056393",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39130000-2",
      "dataset": "data/decp-history.json",
      "oldCpv": "39130000",
      "rowIndex": 218,
      "rowSha256": "0265773282eb51bf02d091c1fca5b50b192e4b7f03cbf2f78aef63578f66267d",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39130000-2",
      "dataset": "data/decp-history.json",
      "oldCpv": "39130000",
      "rowIndex": 222,
      "rowSha256": "7543eaaf91a3ed05710552439ed7f8f430b93fdbd9445086cdc65b38b13a38f9",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39113000-7",
      "dataset": "data/decp-history.json",
      "oldCpv": "39113000",
      "rowIndex": 223,
      "rowSha256": "aabe85536b379990e2a328c64fb2f89da625f1fbbdd73ed2a933abee2e70e275",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39113000-7",
      "dataset": "data/decp-history.json",
      "oldCpv": "39113000",
      "rowIndex": 224,
      "rowSha256": "d706c6277060e671a74474eeef67fdee3c580d2ba965a0c0f16c8c176c52b711",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39130000-2",
      "dataset": "data/decp-history.json",
      "oldCpv": "39130000",
      "rowIndex": 225,
      "rowSha256": "a2f1c0fc0542dc5e0d2684efeb94ee1d57284193ad9795d8b155cabdeb8b41d2",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "18110000-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "18110000",
      "rowIndex": 226,
      "rowSha256": "68afcc342614fbf1230cefb73671c206fe6bcbf5ddf489c40c2b6cb520f107de",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "18110000-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "18110000",
      "rowIndex": 227,
      "rowSha256": "8e9464d9bdeda8629f352434cd6c2ebe0b97c1642c52cb8a3846542807e8bf33",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "18110000-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "18110000",
      "rowIndex": 228,
      "rowSha256": "e6ba4a96c70a5e222d18d72049e8f588efe44b89424e7bf070c910624a588eaf",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "34913200-2",
      "dataset": "data/decp-history.json",
      "oldCpv": "34913200",
      "rowIndex": 236,
      "rowSha256": "6d63485980b5dfdfd702743f80fcaa17232b62e7790283aaa2761a1901c6d484",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "92622000-7",
      "dataset": "data/decp-history.json",
      "oldCpv": "92622000",
      "rowIndex": 255,
      "rowSha256": "9ab5ae5208fb88195ee75070aee1eeb60061b49f9d8964e42246b9104914e4cd",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50324100-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "50324100",
      "rowIndex": 263,
      "rowSha256": "336885e9055ae5ad0711b53d0e7bff2a0d76ff1532d467fd7c44b52b8dd005ea",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72100000-6",
      "dataset": "data/decp-history.json",
      "oldCpv": "72100000",
      "rowIndex": 270,
      "rowSha256": "8fe4f34cf70b77bf96eb9b9f0352bce6f8e2f7187c0f0526190419c7644575c3",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "75231240-8",
      "dataset": "data/decp-history.json",
      "oldCpv": "75231240",
      "rowIndex": 300,
      "rowSha256": "55b4815e8c767c9b6e5f622e235568da998b1a9bfa0e6a150ddeee39f9b51dc7",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71317000-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "71317000",
      "rowIndex": 378,
      "rowSha256": "a1ccee9e717811dc7f3c0caf07bf0378aa51a196676528ccd3002c85dfe2a2c9",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50870000-4",
      "dataset": "data/decp-history.json",
      "oldCpv": "50870000",
      "rowIndex": 415,
      "rowSha256": "ff68de52c4be0ec0b19b2622dfd1188d191ccdfbf420c6a8595941b336686a1e",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71317000-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "71317000",
      "rowIndex": 462,
      "rowSha256": "3591044afe084ec97c10c7b5dcc527c6e8a6dea1c606a27ab87b9c12a9cfe516",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "63000000-9",
      "dataset": "data/decp-history.json",
      "oldCpv": "63000000",
      "rowIndex": 480,
      "rowSha256": "1f257ec373b25a3e0170289950834613cde3118aab6d7f8e660af0b0f529a0f5",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50324100-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "50324100",
      "rowIndex": 734,
      "rowSha256": "b85d8bceb936b4a7dc5ee904adee35398a9536a8678d5dea16b6028ed2862e1d",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50870000-4",
      "dataset": "data/decp-history.json",
      "oldCpv": "50870000",
      "rowIndex": 816,
      "rowSha256": "98b186a582c70847e190b5b36eb68ec9feac30604c758a79a1fdb20ceae1fd27",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71317000-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "71317000",
      "rowIndex": 840,
      "rowSha256": "f8a8d063e5118b18fde5a63096e40537dad54db927b6897043b37d76b47ee00c",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "66171000-9",
      "dataset": "data/decp-history.json",
      "oldCpv": "66171000",
      "rowIndex": 852,
      "rowSha256": "5c4865ca9ff5ed539a628da068a55b90d4324d141a38892d9cb1ac4e5dcbdeea",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "79421000-1",
      "dataset": "data/decp-history.json",
      "oldCpv": "79421000",
      "rowIndex": 853,
      "rowSha256": "a881b1d9217e018619ecbc51ced6356108528fcbed781e8955d4b6574dc355ed",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72212600-5",
      "dataset": "data/decp-history.json",
      "oldCpv": "72212600",
      "rowIndex": 862,
      "rowSha256": "42fff774a25c2cebf1f3f30d53b927cd2f24309604a340276ed06228773bc98f",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45112360-6",
      "dataset": "data/decp-history.json",
      "oldCpv": "45112360",
      "rowIndex": 919,
      "rowSha256": "57e3be1f4cfa46ffd157c1698813613686f29461b24efcc4272aa50c36efbe26",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45331200-8",
      "dataset": "data/decp-history.json",
      "oldCpv": "45331200",
      "rowIndex": 935,
      "rowSha256": "566608143afc6174c60f8afda8c95a81b96d9a1e0f20bc84d81759bbe5519337",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45331200-8",
      "dataset": "data/decp-history.json",
      "oldCpv": "45331200",
      "rowIndex": 936,
      "rowSha256": "0ba36890b3743aff98fce6ce58ebf2b4ddc8e4c3af568c9e7d2748bb0ece0c16",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45331200-8",
      "dataset": "data/decp-history.json",
      "oldCpv": "45331200",
      "rowIndex": 948,
      "rowSha256": "3a46b485a5efbb51f37827007f0828143d6e6be97a377c1b5426cd4569471920",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45261200-6",
      "dataset": "data/decp-history.json",
      "oldCpv": "45261200",
      "rowIndex": 1045,
      "rowSha256": "ffdf3f4fa9e8f0042547a7ecc189e85813218e56b220bd26cbc7675168dacc0b",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "44521110-2",
      "dataset": "data/decp-history.json",
      "oldCpv": "44521110",
      "rowIndex": 1263,
      "rowSha256": "db043b37066d1e6f438399ac7c36762e3212ff4f1902f2ad625407455aecd2ab",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45112730-1",
      "dataset": "data/decp-history.json",
      "oldCpv": "45112730",
      "rowIndex": 1288,
      "rowSha256": "916bc0847001c756c5d701746afb29e0cf945eb236c4be01fe49eb95d36cee9e",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39831000-6",
      "dataset": "data/decp-history.json",
      "oldCpv": "39831000",
      "rowIndex": 1309,
      "rowSha256": "4dfa54ff970e210a8ddf4bd60c62fc5e869264d15a4dbad4882b7b0aa6a4e40d",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39192000-4",
      "dataset": "data/decp-history.json",
      "oldCpv": "39192000",
      "rowIndex": 1318,
      "rowSha256": "bbf9cf005fff0fe8fa0ef60a5c5e15a5fb8bb6298baee5d7840f7ef1e95e9e09",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "33651600-4",
      "dataset": "data/decp-history.json",
      "oldCpv": "33651600",
      "rowIndex": 1356,
      "rowSha256": "7ce0c2140ac75bf1977398c3d1239834c5ba70f85fec3c396c84278e1a0c946f",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "43310000-9",
      "dataset": "data/decp-history.json",
      "oldCpv": "43310000",
      "rowIndex": 1362,
      "rowSha256": "782de80c597f2bd7139bc2b4c50706e8037b5e455156cf6402175206690863c0",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "43310000-9",
      "dataset": "data/decp-history.json",
      "oldCpv": "43310000",
      "rowIndex": 1363,
      "rowSha256": "41a7262131207482c244d240ef6d92e09700f0857cfa65a58b539850ccff2d56",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50117100-9",
      "dataset": "data/decp-history.json",
      "oldCpv": "50117100",
      "rowIndex": 1819,
      "rowSha256": "128df415316db88f2130d1701283beaebe8fc7f598564b7301121e0af6cb8dd3",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "60444100-3",
      "dataset": "data/decp-history.json",
      "oldCpv": "60444100",
      "rowIndex": 1839,
      "rowSha256": "aa885599048a9465607383aa02e40222247d57df4751029d7a94a19921dcd239",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "55320000-9",
      "dataset": "data/decp-history.json",
      "oldCpv": "55320000",
      "rowIndex": 1938,
      "rowSha256": "7b5a76d8c9a76f9f49593f89d840a3d2da33037f4c734f78ab638f2559705518",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "22315000-1",
      "dataset": "data/decp-history.json",
      "oldCpv": "22315000",
      "rowIndex": 1955,
      "rowSha256": "b2e8bc07c22df7d027c104dbc719d5c810ca21413dd2e2668e6aad89d3b298f6",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71631100-1",
      "dataset": "data/decp-history.json",
      "oldCpv": "71631100",
      "rowIndex": 1975,
      "rowSha256": "b048647437918248aeef6d95b2bc65f1aeaddc6ee27e8389709f56b8f02879a2",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71631100-1",
      "dataset": "data/decp-history.json",
      "oldCpv": "71631100",
      "rowIndex": 1976,
      "rowSha256": "e65c14ec98ef877cffb95b0f8a35e45c22b24e863ed40ad0d63bc6dfdf824b03",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71631100-1",
      "dataset": "data/decp-history.json",
      "oldCpv": "71631100",
      "rowIndex": 1977,
      "rowSha256": "cd71ff27dfc9f564dac1c0b8746ae379916e2effee91d3af6fc71a6278674f9f",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "03121210-0",
      "dataset": "data/decp-history.json",
      "oldCpv": "03121210",
      "rowIndex": 2004,
      "rowSha256": "af347daa9802af5f748ee41623704e8630b779a8c721439895727c21aa8b8ae1",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72420000-0",
      "dataset": "data/decp-history.json",
      "oldCpv": "72420000",
      "rowIndex": 2011,
      "rowSha256": "bdee1b229217324ace1c67d48e346cb10c933ea5b6c5058380101088e72134d3",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50116000-1",
      "dataset": "data/decp-history.json",
      "oldCpv": "50116000",
      "rowIndex": 2017,
      "rowSha256": "ef487c89ead64ee2e6d36ef974d2a1ca6a729258e66871ccc0bfa61877015d26",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45232150-8",
      "dataset": "data/decp-history.json",
      "oldCpv": "45232150",
      "rowIndex": 2278,
      "rowSha256": "d065665a27f388eb77f99659718cd86da3b2f5e80637d3216c9f64f69da2ea5e",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45112723-9",
      "dataset": "data/decp-history.json",
      "oldCpv": "45112723",
      "rowIndex": 2414,
      "rowSha256": "4ee42ebeda4ffa3c6a866d1946e661a7acfc32de0b1a06fbfd4b1a10300d2e88",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45112723-9",
      "dataset": "data/decp-history.json",
      "oldCpv": "45112723",
      "rowIndex": 2415,
      "rowSha256": "d6f46652ac4b6280968a9a71bc5875282dcc39fcb205362629afb3f7b1b05d5c",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "48326100-0",
      "dataset": "data/decp-history.json",
      "oldCpv": "48326100",
      "rowIndex": 2434,
      "rowSha256": "fe260961a44a1039da7de1af4eefb1365b41a48b1ebccad75938d1463b63dee9",
      "status": "safe-exact-prefix"
    }
  ],
  "counts": {
    "safe-exact-prefix": 165
  },
  "existingCodeValidation": {
    "full-in-vocabulary": 5121
  },
  "officialVocabularyUsed": true,
  "prefixMappings": [
    {
      "candidateCpv": "03121210-0",
      "observedFullCodes": {
        "03121210-0": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"03121210-0\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "03121210",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "03144000-2",
      "observedFullCodes": {
        "03144000-2": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"03144000-2\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "03144000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "03200000-3",
      "observedFullCodes": {
        "03200000-3": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"03200000-3\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "03200000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "03300000-2",
      "observedFullCodes": {
        "03300000-2": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"03300000-2\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "03300000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "03413000-8",
      "observedFullCodes": {
        "03413000-8": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"03413000-8\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "03413000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "03451000-6",
      "observedFullCodes": {
        "03451000-6": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"03451000-6\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "03451000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "03451200-8",
      "observedFullCodes": {
        "03451200-8": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"03451200-8\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "03451200",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "09331200-0",
      "observedFullCodes": {
        "09331200-0": [
          {
            "rowIndex": 2788,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"09331200-0\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "09331200",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15300000-1",
      "observedFullCodes": {
        "15300000-1": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"15300000-1\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "15300000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15320000-7",
      "observedFullCodes": {
        "15320000-7": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"15320000-7\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "15320000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15500000-3",
      "observedFullCodes": {
        "15500000-3": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"15500000-3\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "15500000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15600000-4",
      "observedFullCodes": {
        "15600000-4": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"15600000-4\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "15600000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15894000-1",
      "observedFullCodes": {
        "15894000-1": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"15894000-1\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "15894000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15894300-4",
      "observedFullCodes": {
        "15894300-4": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"15894300-4\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "15894300",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15900000-7",
      "observedFullCodes": {
        "15900000-7": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"15900000-7\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "15900000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "15910000-0",
      "observedFullCodes": {
        "15910000-0": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"15910000-0\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "15910000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "16160000-4",
      "observedFullCodes": {
        "16160000-4": [
          {
            "rowIndex": 1016,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 1017,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 1591,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"16160000-4\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "16160000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "18110000-3",
      "observedFullCodes": {
        "18110000-3": [
          {
            "rowIndex": 1377,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1378,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1380,
            "source": "data/decp-cities-raw.json"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"18110000-3\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "18110000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "18512200-3",
      "observedFullCodes": {
        "18512200-3": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"18512200-3\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "18512200",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "22114000-2",
      "observedFullCodes": {
        "22114000-2": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"22114000-2\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "22114000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "22315000-1",
      "observedFullCodes": {
        "22315000-1": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"22315000-1\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "22315000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "31000000-6",
      "observedFullCodes": {
        "31000000-6": [
          {
            "rowIndex": 2396,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 2721,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"31000000-6\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "31000000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "31224500-7",
      "observedFullCodes": {
        "31224500-7": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"31224500-7\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "31224500",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "33651600-4",
      "observedFullCodes": {
        "33651600-4": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"33651600-4\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "33651600",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "34114400-3",
      "observedFullCodes": {
        "34114400-3": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"34114400-3\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "34114400",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "34144700-5",
      "observedFullCodes": {
        "34144700-5": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"34144700-5\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "34144700",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "34420000-7",
      "observedFullCodes": {
        "34420000-7": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"34420000-7\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "34420000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "34422000-7",
      "observedFullCodes": {
        "34422000-7": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"34422000-7\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "34422000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "34913200-2",
      "observedFullCodes": {
        "34913200-2": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"34913200-2\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "34913200",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "37000000-8",
      "observedFullCodes": {
        "37000000-8": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"37000000-8\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "37000000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39113000-7",
      "observedFullCodes": {
        "39113000-7": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"39113000-7\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "39113000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39130000-2",
      "observedFullCodes": {
        "39130000-2": [
          {
            "rowIndex": 1346,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1375,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1376,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1774,
            "source": "data/decp-cities-raw.json"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"39130000-2\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "39130000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39142000-9",
      "observedFullCodes": {
        "39142000-9": [
          {
            "rowIndex": 174,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 175,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"39142000-9\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "39142000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39192000-4",
      "observedFullCodes": {
        "39192000-4": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"39192000-4\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "39192000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39710000-2",
      "observedFullCodes": {
        "39710000-2": [
          {
            "rowIndex": 1601,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"39710000-2\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "39710000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "39831000-6",
      "observedFullCodes": {
        "39831000-6": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"39831000-6\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "39831000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "43261000-0",
      "observedFullCodes": {
        "43261000-0": [
          {
            "rowIndex": 2566,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"43261000-0\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "43261000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "43310000-9",
      "observedFullCodes": {
        "43310000-9": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"43310000-9\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "43310000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "43324100-1",
      "observedFullCodes": {
        "43324100-1": [
          {
            "rowIndex": 748,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 2028,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"43324100-1\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "43324100",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "44113900-4",
      "observedFullCodes": {
        "44113900-4": [
          {
            "rowIndex": 2732,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 2733,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"44113900-4\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "44113900",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "44115220-7",
      "observedFullCodes": {
        "44115220-7": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"44115220-7\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "44115220",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "44316400-2",
      "observedFullCodes": {
        "44316400-2": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"44316400-2\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "44316400",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "44511000-5",
      "observedFullCodes": {
        "44511000-5": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"44511000-5\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "44511000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "44521110-2",
      "observedFullCodes": {
        "44521110-2": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"44521110-2\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "44521110",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "44619000-2",
      "observedFullCodes": {
        "44619000-2": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"44619000-2\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "44619000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45112340-0",
      "observedFullCodes": {
        "45112340-0": [
          {
            "rowIndex": 1929,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45112340-0\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45112340",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45112360-6",
      "observedFullCodes": {
        "45112360-6": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45112360-6\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45112360",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45112723-9",
      "observedFullCodes": {
        "45112723-9": [
          {
            "rowIndex": 457,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 458,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 523,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 544,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 547,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 572,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 595,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1034,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1110,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1185,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1186,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1393,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1394,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1395,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1396,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1416,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1423,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1424,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1425,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1429,
            "source": "data/decp-cities-raw.json"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45112723-9\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45112723",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45112730-1",
      "observedFullCodes": {
        "45112730-1": [
          {
            "rowIndex": 212,
            "source": "data/decp-cities-raw.json"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45112730-1\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45112730",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45212140-9",
      "observedFullCodes": {
        "45212140-9": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45212140-9\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45212140",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45223000-6",
      "observedFullCodes": {
        "45223000-6": [
          {
            "rowIndex": 2567,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 2622,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45223000-6\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45223000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45232150-8",
      "observedFullCodes": {
        "45232150-8": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45232150-8\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45232150",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45232454-9",
      "observedFullCodes": {
        "45232454-9": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45232454-9\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45232454",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45261200-6",
      "observedFullCodes": {
        "45261200-6": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45261200-6\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45261200",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45261220-2",
      "observedFullCodes": {
        "45261220-2": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45261220-2\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45261220",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45262100-2",
      "observedFullCodes": {
        "45262100-2": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45262100-2\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45262100",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45262300-4",
      "observedFullCodes": {
        "45262300-4": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45262300-4\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45262300",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45262510-9",
      "observedFullCodes": {
        "45262510-9": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45262510-9\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45262510",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45320000-6",
      "observedFullCodes": {
        "45320000-6": [
          {
            "rowIndex": 216,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45320000-6\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45320000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45331200-8",
      "observedFullCodes": {
        "45331200-8": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45331200-8\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45331200",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45421100-5",
      "observedFullCodes": {
        "45421100-5": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45421100-5\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45421100",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45431100-8",
      "observedFullCodes": {
        "45431100-8": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45431100-8\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45431100",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "45453100-8",
      "observedFullCodes": {
        "45453100-8": [
          {
            "rowIndex": 1223,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 1224,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 1225,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 1226,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 1227,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 1228,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 1804,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"45453100-8\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "45453100",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "48326100-0",
      "observedFullCodes": {
        "48326100-0": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"48326100-0\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "48326100",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50116000-1",
      "observedFullCodes": {
        "50116000-1": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"50116000-1\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "50116000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50117100-9",
      "observedFullCodes": {
        "50117100-9": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"50117100-9\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "50117100",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50312300-8",
      "observedFullCodes": {
        "50312300-8": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"50312300-8\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "50312300",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50324100-3",
      "observedFullCodes": {
        "50324100-3": [
          {
            "rowIndex": 1456,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1787,
            "source": "data/decp-cities-raw.json"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"50324100-3\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "50324100",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50720000-8",
      "observedFullCodes": {
        "50720000-8": [
          {
            "rowIndex": 2299,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 2300,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"50720000-8\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "50720000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50730000-1",
      "observedFullCodes": {
        "50730000-1": [
          {
            "rowIndex": 486,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 487,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"50730000-1\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "50730000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "50870000-4",
      "observedFullCodes": {
        "50870000-4": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"50870000-4\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "50870000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "55240000-4",
      "observedFullCodes": {
        "55240000-4": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"55240000-4\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "55240000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "55320000-9",
      "observedFullCodes": {
        "55320000-9": [
          {
            "rowIndex": 317,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 318,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1314,
            "source": "data/decp-cities-raw.json"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"55320000-9\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "55320000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "55900000-9",
      "observedFullCodes": {
        "55900000-9": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"55900000-9\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "55900000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "60444100-3",
      "observedFullCodes": {
        "60444100-3": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"60444100-3\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "60444100",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "63000000-9",
      "observedFullCodes": {
        "63000000-9": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"63000000-9\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "63000000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "66171000-9",
      "observedFullCodes": {
        "66171000-9": [
          {
            "rowIndex": 2,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1345,
            "source": "data/decp-cities-raw.json"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"66171000-9\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "66171000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71315400-3",
      "observedFullCodes": {
        "71315400-3": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"71315400-3\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "71315400",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71316000-6",
      "observedFullCodes": {
        "71316000-6": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"71316000-6\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "71316000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71317000-3",
      "observedFullCodes": {
        "71317000-3": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"71317000-3\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "71317000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71352000-0",
      "observedFullCodes": {
        "71352000-0": [
          {
            "rowIndex": 972,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 973,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 974,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 975,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"71352000-0\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "71352000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71620000-0",
      "observedFullCodes": {
        "71620000-0": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"71620000-0\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "71620000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "71631100-1",
      "observedFullCodes": {
        "71631100-1": [
          {
            "rowIndex": 1285,
            "source": "data/decp-cities-raw.json"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"71631100-1\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "71631100",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72100000-6",
      "observedFullCodes": {
        "72100000-6": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"72100000-6\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "72100000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72212600-5",
      "observedFullCodes": {
        "72212600-5": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"72212600-5\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "72212600",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72250000-2",
      "observedFullCodes": {
        "72250000-2": [
          {
            "rowIndex": 2860,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"72250000-2\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "72250000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72315100-7",
      "observedFullCodes": {
        "72315100-7": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"72315100-7\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "72315100",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72316000-3",
      "observedFullCodes": {
        "72316000-3": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"72316000-3\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "72316000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72415000-2",
      "observedFullCodes": {
        "72415000-2": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"72415000-2\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "72415000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "72420000-0",
      "observedFullCodes": {
        "72420000-0": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"72420000-0\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "72420000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "75231240-8",
      "observedFullCodes": {
        "75231240-8": [
          {
            "rowIndex": 1076,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1077,
            "source": "data/decp-cities-raw.json"
          },
          {
            "rowIndex": 1078,
            "source": "data/decp-cities-raw.json"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"75231240-8\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "75231240",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "79311100-8",
      "observedFullCodes": {
        "79311100-8": [
          {
            "rowIndex": 423,
            "source": "data/decp-cities-raw.json"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"79311100-8\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "79311100",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "79417000-0",
      "observedFullCodes": {
        "79417000-0": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"79417000-0\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "79417000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "79421000-1",
      "observedFullCodes": {
        "79421000-1": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"79421000-1\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "79421000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "79951000-5",
      "observedFullCodes": {
        "79951000-5": [
          {
            "rowIndex": 933,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "rowIndex": 1098,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"79951000-5\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "79951000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "80580000-3",
      "observedFullCodes": {
        "80580000-3": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"80580000-3\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "80580000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "85147000-1",
      "observedFullCodes": {
        "85147000-1": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"85147000-1\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "85147000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "85210000-3",
      "observedFullCodes": {
        "85210000-3": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"85210000-3\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "85210000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "85312510-7",
      "observedFullCodes": {
        "85312510-7": [
          {
            "rowIndex": 1033,
            "source": "data/decp-history-raw.json.gz"
          },
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"85312510-7\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "85312510",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "90511100-3",
      "observedFullCodes": {
        "90511100-3": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"90511100-3\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "90511100",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "92111230-3",
      "observedFullCodes": {
        "92111230-3": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"92111230-3\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "92111230",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "92521000-9",
      "observedFullCodes": {
        "92521000-9": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"92521000-9\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "92521000",
      "status": "safe-exact-prefix"
    },
    {
      "candidateCpv": "92622000-7",
      "observedFullCodes": {
        "92622000-7": [
          {
            "member": "cpv_2008.xml",
            "selector": "CPV[@CODE=\"92622000-7\"]",
            "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
          }
        ]
      },
      "prefix": "92622000",
      "status": "safe-exact-prefix"
    }
  ],
  "safeCandidateSupport": {
    "official-vocabulary-only": 105,
    "retained-full-code-supported": 60
  },
  "schemaVersion": "decp-cpv-review-v1",
  "sources": [
    {
      "path": "data/decp-cities-raw.json",
      "sha256": "0c708c533e8f5b95571ef17b5a9b65649a2af087d79ea6d6c76980e381dc59d7"
    },
    {
      "path": "data/decp-history-raw.json.gz",
      "sha256": "d759bfaf97d468aa95fa15b4f0b7e657739ceb052b1b8f8afc731e1ad32b419e"
    },
    {
      "path": "data/decp-feeds-raw.json.gz",
      "sha256": "58a17d104540b29e734052dfdb1e9f12afd1bc6fa914e2852a9b76b0cfcda922"
    },
    {
      "path": "data/city-portals-raw.json.gz",
      "sha256": "886c14b864ebca15630b6ec7d0c524d2e073b098e79904084133b6fd6c96a5d7"
    },
    {
      "fullCodes": 9454,
      "member": "cpv_2008.xml",
      "memberSha256": "542fb7a8f35f5d0e377fd0ee621e78d0804705578c4c913dc90ec012310e59ff",
      "sha256": "4129cbbce332c89ee7ce49b74aefa02f31848480d4c885f91cfb015191259146",
      "source": "https://ted.europa.eu/documents/d/ted/cpv_2008_xml"
    },
    {
      "path": "data/decp-cities.json",
      "sha256": "7a85985ea87fe363a1ecf5e00d8da4e9d2d2f2bfde30525e21bad8b614074c6d"
    },
    {
      "path": "data/decp-history.json",
      "sha256": "26b3fedc2daa5f504f1c472b60e6f17204c84a88413a2d24aa11612a6b0d3ef9"
    }
  ],
  "targetCountsByDataset": {
    "data/decp-cities.json": 86,
    "data/decp-history.json": 79
  }
}
```
