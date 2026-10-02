# A small, no-money adoption experiment

This is a proposal for learning whether a public buyer or data publisher can use the explorer to inspect published procurement records and explain data gaps. It is not a validated service, procurement audit, or independent evaluation. Do not describe it as independently validated or as detecting wrongdoing.

## Feedback-period feature freeze

Following the owner's decision after the first outreach requests, keep functionality stable while awaiting feedback. Further changes are limited to bug fixes, performance improvements and testing; no new features, datasets, scoring rules or interaction redesigns without an explicit decision to end the freeze. The already-requested French branding, palette and favicon update is the final visual change before this freeze.

## A realistic first contact

Start with one municipality and one public-facing contact channel (for example, its procurement, open-data, or transparency mailbox). Ask for a short, voluntary usability conversation using only public records already published by the municipality or an official source. Do not ask staff to upload internal procurement files, change a live procurement, or make a decision based on the index. Keep the request small: one person, one publicly available sample, and about 20 minutes if they choose to participate. No payment, gift, procurement opportunity, or endorsement is offered or implied.

### Email to a municipality public contact

**Subject:** Optional 20-minute feedback on a public procurement data explorer

Hello,

I am working on a small, no-cost prototype for browsing published procurement records. It can display a local JSON/CSV file in the browser; the default is browse-only, with no scoring. It is not an audit tool and does not make findings about a municipality or supplier.

Would someone in your procurement, open-data, or transparency team be willing to spend about 20 minutes trying one publicly available record or dataset and tell me what is unclear or inconvenient? Please do not send internal, personal, confidential, or non-public files. There is no purchase, commitment, or endorsement requested; I would use feedback only to improve basic usability and documentation.

If useful, I can send the short instructions and questions in advance. If this is not relevant, no reply is needed.

Thank you,
[Name]
[Public contact details]

## Ask dataset publishers for clarification

Send questions to the publisher's published data/licensing contact, not to individual procurement staff. Keep the queries separate and concise. Ask about the actual API or dataset used, not a general endorsement of the project.

### Query 1 — remaining scope of reuse terms

**Subject:** Third-party content and exceptions in [dataset/API name]

Hello,

We understand [identify the official dataset and stated licence/reuse notice] to support reuse of the published dataset under [licence/terms]. Could you clarify whether those terms cover third-party material incorporated into [specific notice text/attachment/content], and what exceptions or exclusions apply? We are not asking you to re-confirm the dataset-level licence; we want to understand the remaining scope limits for this material. Attribution and your clarification would be recorded in our documentation.

Thank you,
[Name]

### Query 2 — field meaning and privacy

**Subject:** Published fields in [dataset/API name]

Hello,

We understand the official [dataset name] dataset, labelled [licence], to document reuse of these fields: [the specific name/status/identifier fields in scope]. For [other specific field(s), if any], could you clarify their meaning, source, and applicable reuse/publication status? In particular, are contact, identity, or bank/account fields intended for public reuse, or should they be excluded or minimised? We will not treat the dataset licence as blanket permission for fields it does not document.

Thank you,
[Name]

For BOAMP, DILA's legal notice and official data.gouv.fr dataset records support Licence Ouverte 2.0 for the published dataset; null BOAMP API catalogue fields do not leave that dataset licence unresolved. Remaining questions concern third-party notice content/attachments and privacy, not the dataset-level licence. The Annuaire business dataset likewise supports LO 2.0 for the project's limited name/status/identifier enrichment, not blanket coverage of every API field. See [data sources and licences](data-sources.md) and retained [source-rights evidence](source-rights-evidence.json).

## Self-service feedback task

Offer the public instructions and a small, already-published, non-sensitive sample file. Let the participant use their own device without sharing data or screen recordings. Ask them to think aloud if they wish; record only notes they agree to share. Stop if they reach a live case or disclose personal, confidential, or protected information.

Suggested task: “Using this published sample, find one row, identify its source link, and tell me what the result does and does not let you conclude. If relevant, try importing the sample: choose a file, map any CSV columns, inspect the preview, and decide whether you would load it. You do not need to opt in to scoring.”

Ask only a few neutral follow-ups:

- What did you expect to happen at each step?
- Was it clear that preview is not loading, and that confirmation is required?
- Could you find the source and distinguish a missing value from zero?
- What one change would make this easier or safer to use?

## Boundaries

Do not use the index to accuse, rank, blacklist, or publicly label a municipality, employee, supplier, or individual. Do not use it to make or automate eligibility, award, employment, enforcement, or investigative decisions. Do not infer corruption, illegality, intent, value-for-money, or supplier risk from a signal, score, missing value, or absence of a signal. Do not upload or solicit unpublished, confidential, personal, protected, or live-case material. Treat raw contact, identity/document, and bank/account fields as sensitive; minimise them and do not redistribute them simply because they appear in a public extract. `python tools/audit-personal-data.py` is a heuristic field-presence review of repository data, not privacy clearance for a participant's file. Verify any public record with its publisher and obtain qualified advice for legal or procurement decisions. Scores are editorial indicators, not probabilities, findings, or independent validation.

## Small usability criteria

Treat these as observations from a few voluntary sessions, not performance claims or a representative study. Note what happened without collecting names unless a participant explicitly consents.

- Participant can tell that the default is browse-only and scoring is off.
- Participant can distinguish choosing a file, CSV mapping, preview, and the final load confirmation.
- Participant can find the source and explain that a signal is not an allegation and “Not assessed” is not zero.
- Participant notices that missing currency is not treated as EUR and missing source metadata is not invented.
- Participant can identify where to ask a publisher about reuse terms or unclear fields.

Report concrete friction and unresolved questions, including any failure to complete a step. Do not call the exercise independent validation, accuracy testing, or proof of public-sector adoption.
