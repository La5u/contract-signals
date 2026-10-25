#!/usr/bin/env python3
"""Research only: read Korean court rulings (law.go.kr precedents) with Luna or Sol for corruption labels, then check them.

Input: ~/.cache/contract-signals/korea/prec/decisions/<serial>.xml.gz (tools/fetch-korea-lawgokr.py --target prec).
Rulings dated before 2010 (contracts before the KONEPS download), tax, family and patent cases, and rulings without
procurement and public-sector terms (local pre-filter, see PROC) are skipped without a model.
Per ruling, ruling.txt is written to prec/extract/<serial>/ and the model is asked to write result.json there: whether
the ruling concerns a specific public contract or tender, the outcome, and every contract it names (buyer, name, dates,
amount, supplier as printed) with verbatim quotes. Resumable: rulings with a status.json are skipped.
Stops every worker at the usage limit; rerun after the reset.

`--check` only (re)runs the checks and writes prec/extract/checked.jsonl, one line per ruling with `problems` listed
(invalid JSON, quote not in ruling.txt, relevant but no contract, a finding without contracts, 10+ contracts
read by Luna, low confidence, ...); rulings with problems are listed
in prec/extract/to-sol.txt for a second reading (`--model haiku` / `sonnet` use `claude -p` instead of Codex,
e.g. while Codex is out of usage) with `--model gpt-6.1-sol --only $(cat to-sol.txt) --force`.
"""
import argparse
import gzip
import html
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('kftc', HERE / 'extract-korea-kftc-tenders.py')
kftc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kftc)

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea/prec'
SKIP_KINDS = {'세무', '가사', '특허'}
FIELDS = ('사건명', '사건번호', '선고일자', '법원명', '사건종류명', '판결유형', '판시사항', '판결요지', '참조조문', '참조판례', '판례내용')

PROMPT = """ruling.txt in this directory is one Korean court ruling (판결/결정) found by a keyword search for procurement
offences. Many are unrelated. Read ALL of it (use your file tools; it can be long, so read it in parts and do not
stop early) and write result.json in this directory (nothing else), one JSON object:

relevant: true if the court rules on an offence or violation in the award or performance of one or more SPECIFIC
  contracts or tenders of a buyer (bribery for a contract, tender obstruction, bid rigging, cover bids, leaked
  reserve/base prices, split or steered direct contracts, false inspection or completion documents, fraud or inflated
  billing, breach of trust in purchasing, abuse of office in a contract, debarment for such conduct, damages for bid
  rigging). Also true when the defendant is acquitted, so we can exclude the contract. false otherwise (e.g. bribery
  unrelated to any contract, a tax or labour case that only mentions a contract, contracts named only as background).
relevant_reason: one short sentence.
case: {case_no (사건번호), court (법원명), level ("대법원" / "고등법원" / "지방법원" / other as printed), decision_date
  (YYYY-MM-DD), kind ("criminal" / "administrative" / "civil"), lower_case_nos (원심/제1심 사건번호 printed in the ruling,
  list), outcome: one of "convicted", "partly_convicted", "acquitted", "appeal_dismissed" (the lower ruling stands),
  "quashed_remanded", "sanction_upheld", "sanction_annulled", "liability_found", "no_liability", "other";
  outcome_note (short: what stands after this ruling, e.g. "상고기각: 원심 유죄 확정"), outcome_quote (verbatim, at most 200
  characters, usually from 주문 or the conclusion)}.
findings: list, one per offence or violation the court rules on that is tied to contracts:
  {offence (as named in Korean, e.g. 뇌물수수, 뇌물공여, 입찰방해, 공정거래법위반(입찰담합), 배임수재, 건설산업기본법위반,
   사기, 직권남용, 허위공문서작성, 공무상비밀누설, 부정당업자제재),
   proven (true if the court finds it proven or upholds it, false if acquitted / annulled on it, null if not decided
     here, e.g. remanded),
   official_role (the public official's position as printed, if any, e.g. "○○시청 계약담당 6급"),
   stated_count (if the ruling says how many contracts/tenders, e.g. "총 15회" -> 15, else null),
   contracts: list, EVERY contract or tender tied to this finding that the ruling names or describes; for a table or
     list, every row:
     {buyer (발주처/수요기관/계약기관 as printed), buyer_public (true: government body, local government, education
      office, public corporation or institution, military, public school or hospital; false: private company; null:
      unclear), contract_name (공사명/용역명/물품명 as printed, null if not given), contract_kind ("공사" / "용역" /
      "물품" / null), procedure ("일반경쟁" / "제한경쟁" / "지명경쟁" / "수의계약" / "협상에의한계약" / null, only if
      stated), notice_no (공고번호 if printed), notice_date, opening_date, contract_date (YYYY-MM-DD or YYYY-MM or
      null), year (the contract or tender year as an integer if any date is known), amount (계약금액/낙찰금액 in won
      as an integer, null if not stated; convert 만원/억원 only when the unit is printed), amount_kind ("contract" /
      "award" / "estimate" / null; never put a bribe in amount),
      supplier (the contractor as printed, masked names like 공소외 1 주식회사 or ○○건설 stay as printed),
      quote (verbatim excerpt of ruling.txt, at most 200 characters, that names this contract)}
   bribe_amount (total bribe or illicit gain in won, if stated, else null),
   quote (verbatim excerpt, at most 200 characters, stating the finding)}.
confidence: "high" if the text was clear and you read all of it; "low" if anything was unclear, cut off, or you are
  unsure whether a contract belongs to a finding.
unsure: short note on what is unclear, else null.

Rules: copy names, numbers and quotes exactly as in ruling.txt (quotes must be found verbatim in the file; copy them
from the file, do not retype). Never guess a buyer, date or amount that is not printed. If relevant is false, findings
may be []. When done, answer only: DONE <number of contracts>.
"""

MISSING = """result.json is not in the working directory. Write it now, exactly as the instructions above say, then
answer only: DONE <number of contracts>."""


def ruling_text(serial):
    root = ET.fromstring(gzip.decompress((BASE / 'decisions' / f'{serial}.xml.gz').read_bytes()))
    meta = {f: (root.findtext(f) or '').strip() for f in FIELDS}
    parts = []
    for f in FIELDS:
        v = re.sub(r'<br\s*/?>', '\n', meta[f])
        v = html.unescape(re.sub(r'<[^>]+>', '', v))
        v = re.sub(r'[ \t　]+', ' ', v)
        v = re.sub(r'\n\s*\n+', '\n', v).strip()
        if v:
            parts.append(f'【{f}】\n{v}' if f in ('판시사항', '판결요지', '참조조문', '참조판례', '판례내용') else f'{f}: {v}')
    return meta, '\n\n'.join(parts) + '\n'


# Local pre-filter (saves model usage): at least 3 procurement terms and a public-sector term, or a cartel/agency term.
# On the first 673 rulings read by a model it dropped 167, none naming a public contract from 2010 on once 담합 and
# 대행계약 were added.
PROC = re.compile(r'입찰|낙찰|수의계약|계약금액|공사|납품|용역|발주|조달')
PUB = re.compile(r'시청|군청|구청|도청|[시군구]장|교육청|교육감|공사|공단|공기업|공공기관|지방자치단체|국가|조달청|청장|공무원|'
                 r'한국\S+원|시설관리')
ALWAYS = re.compile(r'담합|대행계약')


def selected(serial):
    meta, text = ruling_text(serial)
    if meta['선고일자'][:4] < '2010' or meta['사건종류명'] in SKIP_KINDS:
        return False
    return bool(ALWAYS.search(text)) or (len(PROC.findall(text)) >= 3 and bool(PUB.search(text)))


def pending(only, out, force):
    serials = sorted(p.name[:-7] for p in (BASE / 'decisions').glob('*.xml.gz'))
    if only:
        serials = [s for s in serials if s in only]
    todo = []
    for s in serials:
        if (out / s / 'status.json').exists() and not force:
            st = json.loads((out / s / 'status.json').read_text())
            if st.get('ok') or st.get('skipped'):
                continue
        todo.append(s)
    return todo


CLAUDE_MODELS = {'haiku', 'sonnet', 'opus'}
STRONG = {'gpt-6.1-sol', 'sonnet', 'opus'}  # second readers: their results are not sent for another reading


CLAUDE_INLINE_LIMIT = 120_000  # characters; longer rulings are cut, marked low confidence and go to a second reader
# Lean `claude -p`: no tools (one turn, the ruling pasted in), no MCP servers, skills, settings, CLAUDE.md or default
# system prompt. Measured 2026-10-22: ~570 tokens of fixed context per run instead of ~7,800.
CLAUDE_LEAN = ['--tools', '', '--strict-mcp-config', '--disable-slash-commands', '--setting-sources', '',
               '--no-session-persistence', '--output-format', 'json',
               '--system-prompt', 'You extract data from Korean court rulings. Answer only with the JSON object asked for.']


def run_claude(work, model, timeout):
    """One lean `claude -p` run; the JSON answer is written to result.json here."""
    try:
        proc = subprocess.run(['claude', '-p', '--model', model, *CLAUDE_LEAN], input=inline_prompt(work, CLAUDE_INLINE_LIMIT),
                              text=True, capture_output=True, timeout=timeout, cwd=work)
    except subprocess.TimeoutExpired:
        return '', f'timeout after {timeout} s', 0
    try:
        reply = json.loads(proc.stdout)
        out, err = reply.get('result') or '', '' if not reply.get('is_error') else str(reply.get('result'))[-1000:]
    except json.JSONDecodeError:
        out, err = proc.stdout, (proc.stderr or proc.stdout)[-1000:] or 'no reply'
    if re.search(r'usage limit|session limit|rate.?limit|limit reached', err, re.I):
        return '', 'usage limit: ' + err, 0
    return save_json_answer(work, out, err)


INLINE_LIMIT = 100_000  # characters of ruling.txt pasted into an opencode message (free models: ~128k-token context)


def inline_prompt(work, limit):
    """The extraction prompt with ruling.txt pasted in, for models answering with the JSON object instead of a file."""
    text = (work / 'ruling.txt').read_text()
    cut = len(text) > limit
    prompt = (PROMPT.replace('ruling.txt in this directory is', 'The text after the line ===RULING=== is')
              .replace('Read ALL of it (use your file tools; it can be long, so read it in parts and do not\nstop early) and '
                       'write result.json in this directory (nothing else), one JSON object:',
                       'Read ALL of it and answer with ONLY one JSON object (no code fence, no other text):')
              .replace('quotes must be found verbatim in the file; copy them\nfrom the file', 'quotes must be found verbatim '
                       'in the text; copy them\nfrom the text')
              .replace('When done, answer only: DONE <number of contracts>.', '')
              + ('\nThe text is cut off at the end; set confidence "low".' if cut else '')
              + '\n===RULING===\n' + text[:limit])
    return prompt


def save_json_answer(work, out, err):
    start, end = out.find('{'), out.rfind('}')
    try:
        res = json.loads(out[start:end + 1])
    except (ValueError, json.JSONDecodeError):
        return out[-300:], err or 'no JSON object in the answer', 0
    (work / 'result.json').write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return f'DONE {sum(len(f.get("contracts") or []) for f in res.get("findings") or [])}', err, 0


def run_opencode(work, model, timeout):
    """One `opencode run` (free hosted models such as opencode/deepseek-v4.1-flash-free): the ruling is pasted into the
    message and the JSON answer is written to result.json here, so the model needs no file or shell tools."""
    try:
        proc = subprocess.run(['opencode', 'run', '--pure', '-m', model], input=inline_prompt(work, INLINE_LIMIT),
                              text=True, capture_output=True, timeout=timeout, cwd=work)
        out, err = proc.stdout, '' if proc.returncode == 0 else (proc.stderr or proc.stdout)[-1000:]
    except subprocess.TimeoutExpired:
        return '', f'timeout after {timeout} s', 0
    return save_json_answer(work, out, err)


def run_one(serial, model, effort, timeout, out):
    work = out / serial
    if not selected(serial):
        work.mkdir(parents=True, exist_ok=True)
        (work / 'status.json').write_text(json.dumps({'serial': serial, 'ok': False, 'skipped': 'date, kind or pre-filter'}))
        return serial, 'skipped', ''
    prev = out / '.prev' / serial
    if work.exists():  # kept until this run finishes, so a failed rerun does not lose the previous result
        shutil.rmtree(prev, ignore_errors=True)
        prev.parent.mkdir(exist_ok=True)
        work.rename(prev)
    work.mkdir(parents=True)
    (work / 'ruling.txt').write_text(ruling_text(serial)[1])
    started = time.time()
    for attempt in range(6):
        try:
            if model in CLAUDE_MODELS:
                answer, err, nudges = run_claude(work, model, timeout)
            elif model.startswith('opencode/'):
                answer, err, nudges = run_opencode(work, model, timeout)
            else:
                answer, err, nudges = kftc.server.run(work, PROMPT, model, effort, timeout, ('result.json',), MISSING)
        except RuntimeError as e:
            answer, err, nudges = '', str(e), 0
        if re.search(r'usage limit|usageLimit', err, re.I):
            kftc.stop.set()
            shutil.rmtree(work)
            if prev.exists():
                prev.rename(work)
            return serial, 'usage-limit', err[-300:]
        if 'capacity' not in err.lower() or kftc.stop.is_set():
            break
        time.sleep(60 * (attempt + 1))
    ok = not err and (work / 'result.json').exists()
    if ok:
        shutil.rmtree(prev, ignore_errors=True)
    elif prev.exists():  # keep the earlier result
        shutil.rmtree(work)
        prev.rename(work)
    status = {'serial': serial, 'ok': ok, 'model': model, 'effort': effort, 'answer': answer[-300:],
              'stderr': err[-1000:], 'nudges': nudges, 'seconds': round(time.time() - started),
              'finished': time.strftime('%Y-%m-%dT%H:%M:%S')}
    if ok or not (work / 'status.json').exists():
        (work / 'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=1))
    return serial, 'ok' if ok else 'failed', answer[-120:] or err[-200:]


def squash(s):
    return re.sub(r'\s+', '', s or '')


def check(out):
    rows, to_sol = [], []
    for d in sorted(p for p in out.iterdir() if p.is_dir() and not p.name.startswith('.')):
        st = json.loads((d / 'status.json').read_text()) if (d / 'status.json').exists() else {}
        if st.get('skipped'):
            continue
        problems, res = [], None
        if not st.get('ok'):
            problems.append('extraction failed')
        else:
            try:
                res = json.loads((d / 'result.json').read_text())
            except (json.JSONDecodeError, OSError):
                problems.append('result.json not valid JSON')
        if res is not None:
            text = squash((d / 'ruling.txt').read_text())
            if res.get('relevant') is None:
                problems.append('relevant missing')
            if res.get('confidence') != 'high':
                problems.append('low confidence')
            quotes = [('outcome', (res.get('case') or {}).get('outcome_quote'))]
            contracts = 0
            for f in res.get('findings') or []:
                quotes.append(('finding', f.get('quote')))
                for c in f.get('contracts') or []:
                    contracts += 1
                    quotes.append(('contract', c.get('quote')))
                if f.get('stated_count') and len(f.get('contracts') or []) < f['stated_count']:
                    problems.append(f'fewer contracts than stated ({len(f.get("contracts") or [])} < {f["stated_count"]})')
            bad = sum(1 for _, q in quotes if q and squash(q) not in text)
            if bad:
                problems.append(f'{bad} quote(s) not in ruling.txt')
            if res.get('relevant') and not contracts:
                problems.append('relevant but no contract')
            elif res.get('relevant') and any(not f.get('contracts') for f in res.get('findings') or []):
                problems.append('finding without contracts')
            if res.get('relevant') and contracts >= 10 and st.get('model') not in STRONG:
                problems.append('many contracts (the fast models lump or miss them in long rulings)')
        row = {'serial': d.name, 'model': st.get('model'), 'problems': problems, 'result': res}
        rows.append(row)
        # a second reading only where it can change a label: a public (or unclear) contract from 2010 on or unknown year
        matters = res is None or any((c.get('year') or 9999) >= 2010 and c.get('buyer_public') is not False
                                     for f in res.get('findings') or [] for c in f.get('contracts') or [])
        if problems and matters and st.get('model') not in STRONG:
            to_sol.append(d.name)
    with open(out / 'checked.jsonl', 'w') as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    (out / 'to-sol.txt').write_text('\n'.join(to_sol) + ('\n' if to_sol else ''))
    rel = [r for r in rows if r['result'] and r['result'].get('relevant')]
    print(f'{len(rows)} rulings read, {len(rel)} relevant, '
          f'{sum(len(c.get("contracts") or []) for r in rel for c in r["result"].get("findings") or [])} contracts, '
          f'{sum(1 for r in rows if r["problems"])} with problems, {len(to_sol)} for Sol (to-sol.txt)')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--workers', type=int, default=16)
    parser.add_argument('--model', default='gpt-6-luna', help='Codex model, haiku / sonnet / opus (claude -p), or opencode/<model> (opencode run, e.g. free models)')
    parser.add_argument('--effort', default='medium')
    parser.add_argument('--out', type=Path, default=BASE / 'extract')
    parser.add_argument('--timeout', type=int, default=1800, help='seconds per ruling')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--only', nargs='*')
    parser.add_argument('--force', action='store_true', help='redo rulings even if done')
    parser.add_argument('--check', action='store_true', help='only check existing output')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.check:
        return check(args.out)
    if args.only is not None and not args.only:
        sys.exit('--only was given no rulings (an empty list would otherwise mean all of them)')
    todo = pending(set(args.only or []), args.out, args.force)[:args.limit]
    print(f'{len(todo)} rulings to read, {args.workers} workers, {args.model}', flush=True)
    if todo and args.model not in CLAUDE_MODELS and not args.model.startswith('opencode/'):
        kftc.server = kftc.AppServer()
    done, lock = 0, threading.Lock()

    def task(serial):
        nonlocal done
        if kftc.stop.is_set():
            return
        serial, state, info = run_one(serial, args.model, args.effort, args.timeout, args.out)
        with lock:
            done += 1
            if state != 'skipped':
                print(f'{done}/{len(todo)} {serial}: {state} {info}', flush=True)

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(task, todo))
    if kftc.stop.is_set():
        sys.exit('stopped: usage limit reached; rerun after the reset')
    check(args.out)


if __name__ == '__main__':
    main()
