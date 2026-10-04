# Portugal BASE: bounded archive and rights inspection

Initial bounded inspection: 2026-09-30. A private national extraction was subsequently completed on AC power on 2026-10-01 (3,966 retained rows); nothing has been published. The 2026-10-02 battery-only [technical review](portugal-base-review.md) recommends withholding publication pending candidate-level checks. Neither extraction nor review provides independent factual verification or blanket legal clearance.

## 1. What is actually inside the downloads

The three private ZIPs each contain one deflated, unencrypted JSON member:

| ZIP | Member | Uncompressed bytes |
| --- | --- | ---: |
| `contratos2024.zip` | `Contratos2024.json` | 384,159,940 |
| `contratos2025.zip` | `Contratos2025.json` | 437,904,158 |
| `contratos2026.zip` | `Contratos2026.json` | 320,855,087 |

These are large, single JSON arrays—not CSV/XLSX or newline-delimited JSON. Do not load them into the browser or parse the whole array into memory. A later importer should read sequentially with a bounded buffer, validate records and write only the agreed buyer/date extract. Never extract files using unvalidated ZIP paths.

Inspection used ZIP directory metadata and small prefix-only passes. The reproducible report pass reads at most **64 KiB per annual JSON member**, parsing only the first **three complete records per year** (nine records total). Only field names, types and shape/count aggregates are retained in [`data/portugal-base-inspection.json`](../data/portugal-base-inspection.json). This initial prefix is not representative, is not the three-buyer cohort, and cannot establish completeness or nationwide field coverage. No raw sampled records or personal values were retained in the repository. Download provenance/hashes remain in [`data/portugal-base-downloads.json`](../data/portugal-base-downloads.json).

### Mapping observations and unresolved meanings

The nine sampled records share **39 top-level fields**. The following are field observations, not a complete data dictionary:

| Source field | Observed shape | Conservative future handling |
| --- | --- | --- |
| `idcontrato` | Digit-only string | Preserve as text; verify uniqueness/version conflicts and official source-link construction before publication. |
| `idprocedimento`, `idINCM`, `nAnuncio` | Strings, sometimes empty | Distinct identifiers; do not equate them with a TED procedure UUID without documented linkage. |
| `dataPublicacao` | `DD/MM/YYYY`-shaped text | Use this publication field for the planned date window after strict calendar parsing. No publication time/timezone is supplied by this shape. |
| `dataCelebracaoContrato`, `dataDecisaoAdjudicacao`, `dataFechoContrato` | Separate day-first date strings, some empty | Preserve their meanings as signing, decision and closure dates; never substitute for publication dates. Field-name meanings still need specification confirmation. |
| `adjudicante`, `adjudicatarios`, `concorrentes` | Lists of strings shaped `nine-digit NIF – name`; null also observed for competitors | Buyer, holder and competitor lists are separate. Parse conservatively; multiple holders/buyers remain explicit. Matching a buyer must use the exact NIF, never a name. |
| `cpv`, `tipoContrato`, `localExecucao`, `Lotes` | Lists; some null | Preserve multi-valued classifications/lots. Do not arbitrarily select one CPV or invent a lot-to-holder mapping. |
| `precoContratual`, `precoBaseProcedimento`, `PrecoTotalEfetivo` | JSON numbers | Distinguish declared contract price, base price and effective-total field; they are not interchangeable. The sample contains no explicit currency field: do not infer EUR merely from Portugal. Confirm units/currency from the official specification. |
| `prazoExecucao` | Integer | Unit not established by this inspection: do not map directly to months or assume days without a source specification. |
| `tipoprocedimento`, `regime`, `fundamentacao`, `fundamentAjusteDireto` | Strings | Preserve original wording. No French/TED eligibility or legal conclusion inferred automatically. |
| `descContrato`, `objectoContrato`, `Observacoes`, `linkPecasProc` | Strings, some empty | Free text or published links may contain personal material; minimize and review before public output. Do not fetch attachments automatically. |

**Zeros need context:** `PrecoTotalEfetivo` is zero in 7/9 sampled records, and `precoContratual` is zero in 1/9. These are sample counts, not prevalence estimates. Preserve source zero values, but do not interpret them as verified no-payment/no-cost outcomes or replace absent prices with zero. No price-increase/payment rule is justified by comparing these fields.

**Competitor lists are not verified offer counts.** Missing lists are not zero competitors; a list length does not establish admissible bids or offers per lot. No competition score is enabled by this inspection.

## 2. Reuse evidence and why personal fields are public

Official statements/excerpts, response hashes and remaining questions are retained in [`data/portugal-base-rights.json`](../data/portugal-base-rights.json).

- IMPIC's official [dataset metadata](https://dados.gov.pt/api/1/datasets/contratos-publicos-portal-base-impic-contratos-de-2012-a-2026/) labels the export **`other-pd`**. The official [licence catalogue](https://dados.gov.pt/api/1/datasets/licenses/) resolves this to **“Outra (Domínio Público)”—Other (Public Domain)**, with no terms URL. This is positive publisher-declaration evidence, **not CC0 or a named standard licence**. Exact scope for incorporated text/material and expected attribution remains to clarify.
- BASE's [privacy/responsible-use page](https://www.base.gov.pt/Base4/pt/utilidades/politica-de-privacidade/) explicitly recommends obtaining raw data from **dados.gov.pt**. The downloads used that distribution channel, not a crawl of the contract-search interface. It also describes restrictions on automated portal searches; those restrictions must not be evaded.
- BASE's [publication explanation](https://www.base.gov.pt/Base4/pt/o-portal/o-que-publicitamos/) says contracts are published from reported contract-formation information, with later modification/execution reports. Its [reporting explanation](https://www.base.gov.pt/Base4/pt/o-portal/o-que-nos-comunicam/) describes data supplied by buyers, INCM and procurement platforms. This explains the general transparency/reporting pipeline—not a requirement to expose every participant identifier.
- The publication page is dated **16 December 2022**; reporting explanations cite 2018/2019 provisions. Their current applicability was not independently verified for these 2024–2026 exports. Do not represent them as a current field-by-field legal mandate.
- **Actual schema exposure:** holder and competitor lists contain NIF/name-shaped strings. A NIF/name pair may identify a natural person or sole trader, not only a company. The sample was not classified person-by-person. No conclusion is made about whether any specific disclosure is excessive or unlawful.
- The website privacy policy recognizes data-protection rights and provides an IMPIC DPO channel, but parts concern website users. Do not treat it as blanket permission to republish suppliers' or bidders' personal data. A public-domain category does not remove GDPR or other applicable obligations. A copyright footer on the website is not the same thing as the dataset's declared category.

### Minimal-publication policy for a later extract

| Material | Planned handling before publication |
| --- | --- |
| Three preselected public buyers' NIFs and names | Exact-match buyer filter and provenance, with organization identity verified. |
| Contract/process identifiers and source date fields | Retain only needed procurement identifiers and clearly labelled dates; verify source links and version handling. |
| Supplier names | Retain the published holder names needed to identify contract participants, including company and individual/sole-trader names where appropriate. Names are not suspicion labels. Blank NIFs and prefixes 1, 2, 3 or 45 route holders to conservative name protection, not a verified legal entity-type classification. Blank NIFs can also represent foreign entities; the display label is “Individual or foreign holder”. The minimized cohort still requires a publication-purpose/incidental-data review before redistribution. |
| Supplier NIFs | Strip the numeric prefix from holder display strings; do not include supplier IDs in the public candidate, search, exports or reports. Published names and personal identifier numbers are separate decisions. |
| Unsuccessful competitors' names/NIFs | Omit by default from the public extract; no need to republish named bidder lists for browse-only contract review. Any later aggregate count needs separately verified semantics. |
| Free text and document links | Review the selected cohort for incidental personal details. Keep verified contract subject/source links; omit unnecessary notes and avoid automatic attachment downloads. |
| Extra contact, address, bank or representative data if encountered later | Do not retain by default. This tiny sample does not prove these are absent from the full files or linked documents. |
| National raw archives | Keep outside Git/web root in the private cache. Do not redistribute unchanged national archives. After a minimized, reproducible extract is validated, review cache retention; delete when no longer needed rather than treating storage as indefinite approval. |

### Narrow publisher questions (not sent)

Send source/schema questions to the published role address **suporte.portal@base.gov.pt**; personal-field publication/correction questions can be directed to **DPO@impic.pt**, as listed on BASE's official policy. Do not include actual personal values in the initial question.

> Estamos a preparar um pequeno extrato dos dados publicados no dados.gov.pt, limitado a três entidades adjudicantes e a um período fixo. O catálogo identifica o conjunto como “Outra (Domínio Público)”. Podem confirmar o âmbito dessa declaração e indicar a especificação atual dos campos, em particular a moeda dos preços, a unidade de `prazoExecucao` e o significado de valores zero em `PrecoTotalEfetivo`?
>
> As listas de adjudicatários e concorrentes incluem NIF e nome. Qual é o fundamento e âmbito de publicação quando identificam pessoas singulares, e quais são as regras de reutilização, conservação e correção? Pretendemos omitir os concorrentes identificados e minimizar os dados pessoais no extrato público.

## Reproduce the lightweight inspection

```sh
python tools/inspect-base-archives.py          # ZIP directory + bounded prefixes; no network
python tools/inspect-base-archives.py --write  # retain aggregate schema report only
```

These inspection commands require no full-file scan/hash, whole extraction, cohort filtering, browser test or dataset rebuild. The private extraction was completed separately on 2026-10-01; any new heavy processing still requires authorization. No source inquiries were sent, and no BASE cohort is currently available in the explorer.

## Implemented candidate importer

```sh
python tools/import-portugal-base.py                 # frozen plan only; no archive reads or network
# Run later, when heavy processing is acceptable:
python tools/import-portugal-base.py --extract
# Review the exact private candidate, its names, subject text, omissions and scope first:
python tools/import-portugal-base.py --publish-reviewed \
  --reviewer 'reviewer-or-role' --candidate-sha256 '<hash from private manifest>'
```

`--extract` verifies archive hashes, then streams one JSON record at a time (64 KiB chunks, 1 MiB maximum record, depth/row/output limits). It filters exact buyer NIFs and strictly parsed publication dates. Parsing errors abort; selected-record normalization failures and missing/invalid dates are counted with review reasons, not silently skipped. These omissions prevent a completeness claim. Conflicting **minimized** variants of the same contract ID are all withheld; equivalent minimized records are deduplicated, not treated as evidence that complete source versions are identical.

The private output defaults to `~/.cache/contract-signals/base-candidate/`: `candidate.json`, `coverage.json`, `manifest.json`, with mode 0600 files in a mode 0700 directory. Existing candidates are not overwritten. This stage does not publish, register a menu option or contact external services.

Company supplier names are retained after removing the NIF prefix, including multiple holders. Holders with blank NIFs or prefixes 1, 2, 3 or 45 have names stored reversibly scrambled, with stable codes in ordinary lists/search/exports and a per-record reveal button. This is a bulk-collection deterrent, not secrecy or anonymization: all decoding inputs are public and codes allow guessed-name matching. The rule routes protection; it does not establish every holder's legal entity type. A malformed holder string goes to the normalization-review queue rather than exposing an identifier as a name. Unsuccessful bidder identities, supplier IDs, incidental notes and unrelated raw fields are excluded. Exact protected-name repeats are redacted from subjects, and detected emails/nine-digit identifiers cause rejection; variants and other incidental details still require review. See the [technical review](portugal-base-review.md) for remaining limits.

Normalized records use valid source URLs and text notes accepted by the explorer. `date` is explicitly the publication date; signing/decision/closure dates remain separately labelled. Currency, duration months, direct-award classification and offer counts remain unknown. **`assessmentMode: browse` and `dataStatus: unverified` remain mandatory**, even after publication review: names identify published participants, not investigated people or independently verified facts.

`--publish-reviewed` reads only the private candidate and small provenance documents, verifies its explicit SHA-256 and strict field whitelist/reconciled counts, and requires reviewer confirmation. It refuses empty cohorts, modified fingerprints and differing existing published files. It writes `data/portugal-base.json` and `data/portugal-base-coverage.json`; it does not change the UI or infer a scoring method. The reviewed file can be opened through the existing local JSON import workflow. A bundled selector entry should only be added after actual reviewed records exist, avoiding an empty/fictitious dataset meanwhile.
