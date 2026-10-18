# Romania SEAP: bounded private candidate, not a registered dataset

## Result (2026-10-17)

Only Romania work; no Portugal, shared registry, `script.js`, `index.html`, `style.css`, or deployment changes.

A single existing normalized **Contracte T1 2025** cache was read offline: 2,361,773 compressed bytes / 61,252,068 decoded bytes, **124,086 input rows**. Exact buyer-ID filtering selected **149 source rows**:

| Existing TED buyer | CUI | Selected SEAP rows |
| --- | --- | ---: |
| Ministerul Finanțelor | 4221306 | 109 |
| Județul Cluj | 4288110 | 13 |
| Municipiul Cluj-Napoca | 4305857 | 27 |

These are source rows, **not 149 distinct economic contracts or 149 additional contracts beyond TED**. There were no byte-equivalent normalized selected rows. Other duplicate/grouping questions remain unresolved. Source conclusion labels identify **114 framework rows** and **35 public-procurement-contract rows**. All 149 have parsable contract dates, but those dates were not selection filters.

Private candidate: `~/.cache/contract-signals/romania-seap/candidates/romania-seap-2025q1.json` (267,985 bytes in the audited snapshot, mode 0600). Private manifest is alongside it. Public aggregate manifest: [`../data/romania-seap-candidate-manifest.json`](../data/romania-seap-candidate-manifest.json), with input/output hashes and counts. No winner names, winner IDs or contract-level locators are in the public manifest.

This is a bounded pass through **one pre-existing quarter**, not a national rebuild or download. Initial 60,000- and 100,000-row budgets failed closed without emitting partial candidate files; final explicit budget is 200,000 rows / 96 MiB decoded, 8 MiB compressed, 256 KiB per line. No raw spreadsheet was converted. Header inspection used the existing environment and stopped at the header; its 21 columns contain no subject/title field.

## Rights and privacy gates

Read first: [data sources](data-sources.md), [personal-data rule](personal-data.md), [expansion gates](expansion.md), [generic import semantics](data-format.md).

One bounded official catalogue metadata request confirmed **CC BY 4.0** for `Achiziții publice 2025`. Publisher: **Autoritatea pentru Digitalizarea României**. The source URL, check time, response SHA-256, licence fields and exact quarter resource are in [`../data/romania-seap-rights.json`](../data/romania-seap-rights.json). This is positive dataset-level reuse evidence, **not** TED's separate free-reuse basis, and not privacy clearance or proof of field-level publication necessity. Resource mapping also exists in the old private package metadata; no procurement resource was downloaded here.

Attribute ADR / SEAP-SICAP / data.gov.ro; link the resource and CC BY 4.0; describe the minimization and generated descriptions. Do not apply the repository MIT licence to source data. The private normalization cache has no authenticated acquisition chain; hashes identify bytes, not source truth.

Candidate minimization:

- Keep published winner names privately without claiming that all winners are organizations. Supplier legal form is **unknown**. No name masking or invented entity classification.
- Drop **every winner CUI** rather than guessing which IDs might be personal; no contact, official/representative, address, bank, unsuccessful-bidder or enrichment fields.
- Keep buyer organizational IDs, national notice/lot/contract locators and line-level provenance privately for review. These free-text fields also need review before public release.
- Do not assign `supplierIndividual: false`: unknown is not a legal-person finding. Before public release apply the project-wide individual-supplier export treatment once supported classification is available.
- Candidate files are 0600 outside Git/web root. Review ongoing cache retention, correction/removal handling and published-name necessity; no upstream inquiry was sent.

**Decision:** rights declaration supports reuse in principle, but this delivery deliberately publishes only aggregate manifests. Human content/privacy review and identity semantics still gate public row-level publication.

## Browse-only and value semantics

Every row is `dataStatus: "unverified"`. No scoring or indicators are adopted, including TED scoring. `amount`, `currency`, `offers`, direct-award status and duration are unknown/null; the importer deliberately does not copy the source's `value_ron_num`. Framework ceilings are not payments or awarded-contract totals. Even the 35 non-framework-labelled rows need source-value/granularity review before adopting amounts. Never sum this candidate with TED.

The quarter filename is the extraction basis, **not** a verified publication-date window. The raw header has two columns named `Data publicare`; the normalizer does not disambiguate them, so no publication date is invented. Contract dates may predate the quarter and are explicitly labelled contract dates.

There is **no published contract subject** in this export. Generic import requires `description`, so each description is explicitly generated as `SEAP contract export row (subject not supplied)`, optionally followed by the source CPV code. The source winner name remains a separate field. The normalizer now recognizes `Denumire CPV` as `cpv_label`, not a contract title; existing cached rows were not rebuilt.

IDs combine the quarter, normalized-input hash prefix and source line. This preserves row identity within a snapshot; it is **not** a stable national contract identifier across revised exports. Exact repeated rows are counted, not silently deduplicated or summed.

## Honest TED overlap assessment

Existing `data/ted-romania.json`: **321 retained lots**, the same three buyer IDs, publication dates September 2024–August 2026. SEAP Q1 labels and source contract dates are not equivalent to that TED publication window.

**Record-level overlap is unresolved, not zero.** The initial candidate extraction performed no join. A subsequent bounded audit recovered native contract references from 162 cached TED XML notices: 26 shared buyer/reference/date keys touch 38 SEAP rows and 35 TED rows. These remain candidate links, not confirmed duplicate identities; see [the verification and publication decision](expansion-candidate-decision.md). TED normalized `contractId` values are internal eForms `CON-*` references; SEAP `contract_no` is a national reference. SEAP CAN/SCN national notice references are not retained in the normalized TED file. Same buyer, winner name, subject, amount or date does not establish identity. Public manifest uses `confirmedRecordLinks: null`, deliberately not `0`.

Next bounded audit: adjudicate the recovered buyer/reference/date candidate links using selected SEAP notice/lot/contract IDs and relevant cached TED XML; distinguish lots, suppliers and framework/call-off relationships. Verify identifier scope and date/lot distinctions. Publish minimized exact links only after source evidence and privacy review; ambiguous links stay unknown. No national download is needed for that step.

## Reproduce and inspect locally

```sh
python -m unittest discover -s tests -p 'test_import_romania_seap.py'
node tests/import-engine.cjs
python tools/import-romania-seap.py \
  --manifest data/romania-seap-candidate-manifest.json
```

The tool is stdlib-only, offline, fixed to one quarter, with exact buyer matching and hard input/output limits. Cache override `--cache /private/path` must remain outside the repository. Missing inputs or exceeded budgets fail instead of producing a partial cohort. It does **not** run `normalize-romania-seap.py` or obtain new data. The optional public manifest contains only aggregates, fixed organization IDs and provenance hashes.

For local review use **Import a dataset → Browse only · no scoring**, select the private JSON, preview, then load. Do not opt into French checks or declare the rows verified. Six synthetic Python tests and existing import-engine tests pass. Additionally the actual 149-row private file was parsed with `import.js`, prepared with the current engine and asserted to have null scores throughout. No browser/full-suite run was needed.

## Precise parent integration instructions

**No registry entry now.** The public candidate manifest is not a records file and must not be used as a dataset `path`. Do not copy the private file into `data/` merely to make the registry load it.

1. The current deliverable is already explorer-ready through **local generic import**, without registry edits. It intentionally omits `dataFamily`: the current engine rejects unregistered families such as `romania-seap`, and calling this `ted` would misrepresent source/scoring.
2. After a documented publication decision, copy a reviewed, minimized record array to a new path such as `data/romania-seap-2025q1.json`; write a matching coverage record that retains this selection, rights, generated-description caveat and unresolved overlap. Preserve `dataStatus: unverified`, null amounts and `source`/line provenance.
3. If parent adds a built-in dataset, use a **separate browse-only method** and key, proposed `romaniaSeap`, with record path `data/romania-seap-2025q1.json` and coverage path `data/romania-seap-candidate-manifest.json` only once that manifest is updated to describe the reviewed public snapshot. Never point it at `data/ted-romania.json`, replace the existing `romania` TED entry, inherit TED scoring, or merge spending totals.
4. Parent owns any required central dataset/menu/metadata/no-scoring routing and source-label changes. Suggested label: **Romania · SEAP · three buyers · Q1 2025 · browse only**. Publisher/attribution: ADR, SEAP/SICAP via data.gov.ro; licence CC BY 4.0; extraction: exact CUI match in one quarter export, publication-date meaning unresolved.
5. Integration tests must assert all rows remain **Not assessed**, no framework amount enters totals, no supplier IDs leak, individual-export treatment is correct, and the existing TED Romania cohort is unchanged. The current generic import route has been tested; no untested built-in registry snippet is claimed to work.
