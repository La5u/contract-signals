#!/usr/bin/env python3
"""Research only: Board of Audit and Inspection (감사원) reports as Korean labels: fetch, read with a model, check.

bai.go.kr serves its listings and files only through /api/, which its robots.txt disallows, so reports are taken
from 정책브리핑 (korea.kr, robots.txt allows all): each BAI press release (department code C00022) carries the
press release and, for audit results, the full public report (공개문 PDF). Reports are 공공누리 4유형 (non-commercial,
no derivatives): kept privately, only facts used.

Stages (all resumable, private cache ~/.cache/contract-signals/korea/bai/):
- `list`: release index from korea.kr list pages, year by year (--first-year..--last-year) -> index.jsonl.
- `fetch --sample N`: audit-result releases (titles that are not personnel, events, consulting, ...) in a seeded
  random order; per release the view page, its report PDF (attachment named 공개문/감사결과/전문, else any PDF that is
  not the press release) -> <newsId>/report.pdf and report.txt (pdftotext -layout). A report enters the sample when
  it has at least --min-terms procurement terms (계약, 입찰, 낙찰, 공사, 용역); stops at N.
- `extract`: one model call per chunk of report.txt (--chunk characters) through `opencode run` or `claude -p`, a
  fallback chain (default free DeepSeek, then Haiku when it fails or stalls), the court-ruling schema (tools/extract-korea-court-rulings.py) adapted to
  audit findings; chunk answers are merged into <newsId>/result.json.
- `check`: verbatim quotes, contracts per finding -> checked.jsonl in the court format, so
  `tools/match-korea-court-contracts.py --rulings bai/checked.jsonl --out bai/links.jsonl --days-out bai/days.txt`
  measures how many named contracts link to KONEPS.
"""
import argparse
import html
import importlib.util
import json
import os
import random
import re
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from polite_http import PoliteClient  # noqa: E402

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea/bai'
SITE = 'https://www.korea.kr'
LIST = SITE + '/briefing/pressReleaseList.do?repCodeType=&repCode=C00022&pageIndex={page}&startDate={lo}&endDate={hi}'
VIEW = SITE + '/briefing/pressReleaseView.do?newsId={nid}'
NOT_AUDIT = re.compile(r'인사|공모|사전컨설팅|채용|간담회|협약|포럼|세미나|교육|위원|발간|개최|국민제안|감사계획|원장|해명|설명자료|참고자료|수상|기념')
TERMS = re.compile(r'계약|입찰|낙찰|공사|용역')
CLAUDE = {'haiku', 'sonnet', 'opus'}
_spec = importlib.util.spec_from_file_location('court', Path(__file__).resolve().parent / 'extract-korea-court-rulings.py')
court = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(court)

PROMPT = """The text after the line ===REPORT=== is (part {part} of {parts} of) one public audit report of the Korean
Board of Audit and Inspection (감사원 감사결과 공개문). Read ALL of it and answer with ONLY one JSON object (no code
fence, no other text):

relevant: true if this part states an irregularity in the award or performance of one or more SPECIFIC public
  contracts or tenders (bid rigging, cover bids, leaked prices, favouritism or steering in an award, split or
  unjustified direct contracts, bribery or entertainment by a contractor, fraud, inflated or unjustified price or
  design changes, false inspection or completion, paying for work not done, unqualified contractor). false otherwise
  (policy, personnel, budget or management findings that name no contract).
relevant_reason: one short sentence.
case: {{case_no: null, court: "감사원", level: "audit", decision_date: null, kind: "audit", lower_case_nos: [],
  outcome: "audit_finding", outcome_note: the requested action as printed (e.g. 징계요구, 주의요구, 통보, 고발),
  outcome_quote: null}}.
findings: list, one per audit finding (지적사항) tied to contracts:
  {{offence (the irregularity in Korean as the report names it, e.g. 입찰 담합, 수의계약 부당 체결, 계약금액 부당 증액,
   부당 설계변경, 준공검사 부적정, 금품수수),
   proven: true,
   official_role (the official's position as printed, if any),
   stated_count (if the report says how many contracts, e.g. "총 15건" -> 15, else null),
   contracts: list, EVERY contract or tender tied to this finding that the report names or describes; for a table,
     every row:
     {{buyer (발주기관/계약기관/수요기관 as printed), buyer_public (true / false / null), contract_name (as printed, null if
      not given), contract_kind ("공사" / "용역" / "물품" / null), procedure ("일반경쟁" / "제한경쟁" / "지명경쟁" /
      "수의계약" / "협상에의한계약" / null, only if stated), notice_no, notice_date, opening_date, contract_date
      (YYYY-MM-DD or YYYY-MM or null), year (contract or tender year as an integer if any date is known), amount
      (계약금액/낙찰금액 in won as an integer, null if not stated; convert 천원/백만원/억원 only when the unit is printed),
      amount_kind ("contract" / "award" / "estimate" / null; never put an overpayment or bribe in amount),
      supplier (the contractor as printed; masked names like A업체 or ◇◇건설 stay as printed),
      quote (verbatim excerpt of the text, at most 200 characters, that names this contract)}}
   bribe_amount (illicit gain in won, if stated, else null),
   action (the measures the report requests for this finding, as printed, e.g. 징계요구, 주의요구, 통보, 시정요구,
     고발, 수사요청, 변상판정, 회수/환수 요구),
   action_class ("recovery" if money is to be recovered, repaid, corrected or a fine imposed; "referral" if 고발 or
     수사요청; "discipline" if only 징계/주의/통보 or similar; when several apply, the first in this order),
   recovered_amount (amount in won to be recovered, repaid or corrected, if stated, else null),
   quote (verbatim excerpt, at most 200 characters, stating the finding)}}.
confidence: "high" if the text was clear; "low" if anything was unclear or cut off.
unsure: short note on what is unclear, else null.

Rules: copy names, numbers and quotes exactly as in the text (quotes must be found verbatim in the text; copy them,
do not retype). Never guess a buyer, date or amount that is not printed. If relevant is false, findings may be [].
===REPORT===
"""


def text_of(fragment):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', fragment))).strip()


def list_stage(client, pages, first_year, last_year):
    """Release index, one calendar year at a time (the list shows the last year unless dates are given)."""
    index = BASE / 'index.jsonl'
    seen = {json.loads(l)['newsId'] for l in open(index)} if index.exists() else set()
    with open(index, 'a') as f:
        for year in range(last_year, first_year - 1, -1):
            previous = None
            for page in range(1, pages + 1):
                body = client.get(LIST.format(page=page, lo=f'{year}-01-01', hi=f'{year}-12-31')).body.decode('utf-8', 'replace')
                items = re.findall(r'pressReleaseView\.do\?newsId=(\d+)[^>]*>(.*?)</a>', body, re.S)
                new = 0
                for nid, inner in items:
                    if nid in seen:
                        continue
                    seen.add(nid)
                    t = text_of(inner)
                    m = re.search(r'(\d{4}-\d\d-\d\d)', t)
                    title = re.split(r'\s+자세한 내용은|\s+\d{4}-\d\d-\d\d', t)[0]
                    half = len(title) // 2   # the list repeats the title (heading + summary)
                    if title[:half].strip() == title[half:].strip():
                        title = title[:half].strip()
                    f.write(json.dumps({'newsId': nid, 'title': title, 'date': m and m.group(1)}, ensure_ascii=False) + '\n')
                    new += 1
                print(f'{year} page {page}: {len(items)} items, {new} new', flush=True)
                ids = [nid for nid, _ in items]
                if not ids or ids == previous:  # past the last page the list repeats it
                    break
                previous = ids


def report_pdf(client, nid):
    """The report attachment of one release: (file name, bytes) or None."""
    body = client.get(VIEW.format(nid=nid)).body.decode('utf-8', 'replace')
    files = []
    for fid in dict.fromkeys(re.findall(r'download\.do\?fileId=(\d+)&(?:amp;)?tblKey=GMN', body)):
        i = body.find(f'fileId={fid}')
        near = text_of(body[max(0, i - 600):i + 200])
        names = re.findall(r'[^\s]*?[^\s/]+\.(?:pdf|hwpx?|PDF)', near)
        files.append((fid, names[-1] if names else ''))
    pdfs = [(fid, n) for fid, n in files if n.lower().endswith('.pdf') and '보도' not in n]
    best = [x for x in pdfs if re.search(r'공개문|감사결과|전문', x[1])] or pdfs
    if not best:
        return None
    fid, name = best[0]
    return name, client.get(f'{SITE}/common/download.do?fileId={fid}&tblKey=GMN').body


def fetch_stage(client, sample, min_terms, seed):
    rows = [json.loads(l) for l in open(BASE / 'index.jsonl')]
    rows = [r for r in rows if not NOT_AUDIT.search(r['title'])]
    random.Random(seed).shuffle(rows)
    chosen = BASE / 'sample.txt'
    picked = chosen.read_text().split() if chosen.exists() else []
    for r in rows:
        if len(picked) >= sample:
            break
        nid, work = r['newsId'], BASE / r['newsId']
        if nid in picked or (work / 'skip.json').exists():
            continue
        work.mkdir(parents=True, exist_ok=True)
        if not (work / 'report.txt').exists():
            got = report_pdf(client, nid)
            if not got:
                (work / 'skip.json').write_text(json.dumps({'reason': 'no report PDF', **r}, ensure_ascii=False))
                continue
            (work / 'report.pdf').write_bytes(got[1])
            subprocess.run(['pdftotext', '-layout', str(work / 'report.pdf'), str(work / 'report.txt')], check=True)
            (work / 'meta.json').write_text(json.dumps({**r, 'file': got[0]}, ensure_ascii=False))
        text = (work / 'report.txt').read_text()
        terms = len(TERMS.findall(text))
        if terms < min_terms:
            (work / 'skip.json').write_text(json.dumps({'reason': f'{terms} procurement terms', **r}, ensure_ascii=False))
            continue
        picked.append(nid)
        chosen.write_text('\n'.join(picked) + '\n')
        print(f'{len(picked)}/{sample} {nid} {r["date"]} {r["title"][:50]} ({len(text)} chars, {terms} terms)', flush=True)


def ask(prompt, model, timeout, cwd):
    if model in CLAUDE:
        cmd = ['claude', '-p', '--model', model, *court.CLAUDE_LEAN]
    elif model.startswith('opencode/'):
        cmd = ['opencode', 'run', '--pure', '-m', model]
    else:  # Codex models (gpt-6-luna, gpt-6.1-sol) through `sol`, which prints only the final answer
        cmd = ['sol', '-e', 'low', '-m', model]
    # own process group: on timeout the whole group is killed (opencode's children otherwise keep the pipe open
    # and subprocess.run waits forever)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            cwd=cwd, start_new_session=True)
    try:
        out, _ = proc.communicate(prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise
    if model in CLAUDE:  # --output-format json: the answer is the envelope's `result` string
        out = json.loads(out).get('result') or ''
    start, end = out.find('{'), out.rfind('}')
    res = json.loads(out[start:end + 1])
    if not isinstance(res, dict) or 'findings' not in res:
        raise ValueError('answer is not the requested object')
    return res


def extract_one(nid, model, chunk, timeout):
    work = BASE / nid
    if (work / 'result.json').exists():
        return nid, 'done before'
    text = (work / 'report.txt').read_text()
    parts = [text[i:i + chunk] for i in range(0, len(text), chunk)] or ['']
    merged = {'relevant': False, 'relevant_reason': [], 'case': None, 'findings': [], 'confidence': 'high',
              'unsure': [], 'model': model, 'part_models': [], 'parts': len(parts)}
    for k, part in enumerate(parts, 1):
        cache = work / f'part-{k}.json'
        if cache.exists():
            res = json.loads(cache.read_text())
        else:
            res = None
            for m in model.split(','):  # e.g. free DeepSeek first, Haiku when it stalls or fails twice
                for attempt in range(2):
                    try:
                        res = ask(PROMPT.format(part=k, parts=len(parts)) + part, m, timeout, work)
                        res['model'] = m
                        break
                    except (ValueError, subprocess.TimeoutExpired):
                        time.sleep(10)
                if res:
                    break
            if not res:
                return nid, f'part {k}: every model failed'
            cache.write_text(json.dumps(res, ensure_ascii=False, indent=1))
        merged['part_models'].append(res.get('model'))
        merged['relevant'] |= bool(res.get('relevant'))
        merged['relevant_reason'].append(res.get('relevant_reason'))
        merged['case'] = merged['case'] or res.get('case')
        merged['findings'] += res.get('findings') or []
        if res.get('confidence') != 'high':
            merged['confidence'] = 'low'
        if res.get('unsure'):
            merged['unsure'].append(res['unsure'])
    meta = json.loads((work / 'meta.json').read_text())
    merged['case'] = {**(merged['case'] or {}), 'case_no': f'감사원 {meta["title"]}', 'decision_date': meta['date']}
    (work / 'result.json').write_text(json.dumps(merged, ensure_ascii=False, indent=1))
    return nid, f'{len(parts)} parts, {len(merged["findings"])} findings, ' \
                f'{sum(len(f.get("contracts") or []) for f in merged["findings"])} contracts'


def squash(s):
    return re.sub(r'\s+', '', s or '')


def check_stage():
    rows = []
    for nid in (BASE / 'sample.txt').read_text().split():
        work = BASE / nid
        if not (work / 'result.json').exists():
            continue
        res = json.loads((work / 'result.json').read_text())
        text = squash((work / 'report.txt').read_text())
        problems = []
        quotes = [c.get('quote') for f in res['findings'] for c in f.get('contracts') or []] + \
                 [f.get('quote') for f in res['findings']]
        missing = sum(1 for q in quotes if q and squash(q) not in text)
        if missing:
            problems.append(f'{missing} quote(s) not in report.txt')
        if res['relevant'] and not any(f.get('contracts') for f in res['findings']):
            problems.append('relevant but no contract')
        if res.get('confidence') != 'high':
            problems.append('low confidence')
        rows.append({'serial': nid, 'model': res.get('model'), 'problems': problems, 'result': res})
    with open(BASE / 'checked.jsonl', 'w') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    contracts = [c for r in rows for fi in r['result']['findings'] for c in fi.get('contracts') or []]
    print(json.dumps({'reports': len(rows), 'relevant': sum(r['result']['relevant'] for r in rows),
                      'findings': sum(len(r['result']['findings']) for r in rows), 'contracts': len(contracts),
                      'with_name': sum(bool(c.get('contract_name')) for c in contracts),
                      'with_amount': sum(bool(c.get('amount')) for c in contracts),
                      'with_date': sum(bool(c.get('contract_date') or c.get('year')) for c in contracts),
                      'with_supplier': sum(bool(c.get('supplier')) for c in contracts),
                      'with_problems': sum(bool(r['problems']) for r in rows)}, ensure_ascii=False, indent=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('stage', choices=['list', 'fetch', 'extract', 'check'])
    parser.add_argument('--pages', type=int, default=40, help='list: korea.kr list pages per year (10 releases each)')
    parser.add_argument('--sample', type=int, default=20)
    parser.add_argument('--min-terms', type=int, default=30)
    parser.add_argument('--seed', type=int, default=20261024)
    parser.add_argument('--model', default='opencode/deepseek-v4.1-flash-free,haiku',
                        help='comma-separated fallback chain of opencode/<model>, haiku/sonnet (claude -p) or a Codex model (sol)')
    parser.add_argument('--first-year', type=int, default=2016)
    parser.add_argument('--last-year', type=int, default=2026)
    parser.add_argument('--chunk', type=int, default=90_000, help='characters per model call')
    parser.add_argument('--timeout', type=int, default=420)
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--reverse', action='store_true',
                        help='extract: read the sample from the end (a second run with another model meets the first)')
    args = parser.parse_args()
    BASE.mkdir(parents=True, exist_ok=True)
    client = PoliteClient(log_path=BASE / 'requests.jsonl')
    if args.stage == 'list':
        list_stage(client, args.pages, args.first_year, args.last_year)
    elif args.stage == 'fetch':
        fetch_stage(client, args.sample, args.min_terms, args.seed)
    elif args.stage == 'extract':
        todo = (BASE / 'sample.txt').read_text().split()
        todo = [n for n in (todo[::-1] if args.reverse else todo) if not (BASE / n / 'result.json').exists()]
        with ThreadPoolExecutor(args.workers) as pool:
            for nid, state in pool.map(lambda n: extract_one(n, args.model, args.chunk, args.timeout), todo):
                print(nid, state, flush=True)
    else:
        check_stage()


if __name__ == '__main__':
    main()
