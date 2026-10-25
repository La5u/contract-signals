#!/usr/bin/env python3
"""Research only: find the federal contract numbers behind each US label case, one Sol thread per case.

Input: us-labels/sol-cases-1.tsv (case list, one row per case). For every case Sol searches the primary documents
(plea agreements, informations, indictments, complaints, settlement agreements, OIG reports, GAO protest decisions,
USAspending/FPDS pages) and writes us-labels/cases/<case_id>/contracts.json. Cases with that file are skipped, so
the run resumes; a usage-limit error stops every worker. Uses the shared app-server client of
tools/extract-korea-kftc-tenders.py (one process for all threads).
"""
import argparse
import csv
import importlib.util
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('kftc', TOOLS / 'extract-korea-kftc-tenders.py')
kftc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kftc)

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/us-labels'
PROMPT = """You are building a label set that links proven US federal procurement misconduct to the exact contracts in
FPDS/USAspending. The case below came from a press-release search; press releases rarely name contracts, but the
court and audit documents usually do. Look hard, using web search and fetching documents:

- justice.gov press releases AND their attached documents (plea agreement, information, indictment, settlement
  agreement PDFs under justice.gov/.../file/... or /media/...), the Antitrust Division case page
  (justice.gov/atr/case/...), U.S. Attorney's Office pages;
- court dockets (CourtListener / RECAP archive, Justia dockets, casetext) for the complaint, information, plea
  agreement, statement of facts, sentencing memo;
- agency OIG reports and semiannual reports (DoD IG / DCIS, VA OIG, GSA OIG, DHS OIG, SBA OIG, DOT OIG...),
  GAO bid-protest decisions, SBA size/status protest decisions, suspension/debarment notices (SAM exclusions);
- USAspending.gov / FPDS / SAM.gov / HigherGov / GovTribe pages for the companies, to find award IDs (PIIDs)
  that match the described contract (agency, place, years, description, value).

Case (TSV row from the list):
{row}

Write the file contracts.json in the current directory (and nothing else) with this JSON shape:
{{"case_id": "...",
  "documents_checked": [{{"url": "...", "kind": "plea agreement|information|indictment|complaint|settlement|press release|OIG report|GAO decision|docket|USAspending|other", "found_contract_ids": true|false}}],
  "companies": [{{"name": "as written in the source", "role": "defendant|co-conspirator|front company|winner|bribe payer|other", "uei": "", "duns": "", "cage": ""}}],
  "contracts": [{{"id": "PIID / task or delivery order / solicitation / IDV number exactly as written",
                 "id_kind": "contract|task_order|delivery_order|idv|solicitation|bpa|other",
                 "parent_idv": "", "agency": "", "office": "", "place": "", "years": "", "value_usd": "",
                 "awardee": "", "role_in_case": "rigged award|cover bid|kickback-tainted award|set-aside obtained by fraud|other",
                 "evidence": "short quote from the source naming the number", "source_url": "...",
                 "confidence": "stated in court/audit document|stated in press release|matched by me on USAspending (explain in evidence)"}}],
  "court_case_numbers": ["e.g. 1:19-cr-00123"],
  "notes": "what was not findable and why; corrections to the case row (wrong agency, years, outcome) with source"}}

Rules: never invent or guess a number. Only list a contract you saw named in a document, or one you matched
yourself on USAspending/FPDS with the reasoning in evidence and confidence "matched by me". Copy numbers exactly
(keep dashes). Do not include natural persons' names, addresses or personal identifiers. If nothing is findable
after a real search, write contracts as [] and explain in notes.
"""
MISSING = 'contracts.json is not in the working directory. Write it now in the JSON shape given, then stop.'
stop = threading.Event()


def work(server, row, header, out, model, effort, timeout):
    case = row[0]
    folder = out / case
    if (folder / 'contracts.json').exists() or stop.is_set():
        return case, 'skipped'
    folder.mkdir(parents=True, exist_ok=True)
    text = '\n'.join(f'{h}: {v}' for h, v in zip(header, row))
    answer, err, nudges = server.run(folder, PROMPT.format(row=text), model, effort, timeout,
                                     required=('contracts.json',), missing=MISSING)
    if 'usage limit' in (err + answer).lower():
        stop.set()
        return case, 'usage limit: ' + err[:200]
    path = folder / 'contracts.json'
    if not path.exists():
        return case, f'no file ({err[:200]})'
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        path.rename(folder / 'contracts.bad.json')
        return case, f'bad JSON: {e}'
    return case, f'{len(data.get("contracts") or [])} contracts, {len(data.get("documents_checked") or [])} documents'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cases', type=Path, default=BASE / 'sol-cases-1.tsv')
    ap.add_argument('--out', type=Path, default=BASE / 'cases')
    ap.add_argument('--only', help='comma-separated case ids')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--model', default='gpt-6.1-sol')
    ap.add_argument('--effort', default='medium')
    ap.add_argument('--timeout', type=int, default=1800)
    a = ap.parse_args()
    rows = list(csv.reader(a.cases.open(), delimiter='\t'))
    header, rows = rows[0], [r for r in rows[1:] if r and r[0].strip()]
    if a.only:
        wanted = set(a.only.split(','))
        rows = [r for r in rows if r[0] in wanted]
    server = kftc.AppServer()
    with ThreadPoolExecutor(a.workers) as pool:
        futures = [pool.submit(work, server, r, header, a.out, a.model, a.effort, a.timeout) for r in rows]
        for f in futures:
            case, message = f.result()
            print(f'{case}: {message}', flush=True)
    server.proc.terminate()


if __name__ == '__main__':
    main()
