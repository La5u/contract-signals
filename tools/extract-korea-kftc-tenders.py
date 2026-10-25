#!/usr/bin/env python3
"""Research only: extract the rigged tenders of KFTC bid-rigging decisions with Sol, then check what it wrote.

Input: ~/.cache/contract-signals/korea/ftc/images/<serial>/ (decision.txt + img*.png, tools/fetch-korea-kftc-images.py).
Per decision, the files are copied to ftc/extract/<serial>/ and `sol -w -m <model> -C` that copy is asked to write meta.json and
tenders.jsonl there (files, not its answer, so long tender lists are not cut). Tesseract cannot read the table grids;
Sol reads the images. Resumable: decisions with a status.json are skipped (--redo-failed retries failed ones).
Stops every worker when Sol reports its usage limit (exit 75); rerun after the reset.

`--backend app-server` (default) runs every worker's thread in one `codex app-server --stdio` process instead of a
~250 MB `codex exec` per worker, so many more can run at once; a thread that answers without writing the files is
asked again in the same thread (twice at most). `--backend sol` uses the `sol` command.

`--check` only (re)runs the checks and writes ftc/extract/checked.jsonl: each tender with `problems` listed
(winner not among the bids, award ÷ reserve price off the printed bid rate, text quote not in decision.txt,
fewer tenders than the stated count, ...). Problems are flags for review, never silent fixes.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import to_int  # noqa: E402

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea/ftc'

PROMPT = """This directory holds one Korean Fair Trade Commission (공정거래위원회) bid-rigging decision: decision.txt (the
text; markers like [IMAGE img003.png] show where table images sit) and the images img*.png. The tender tables
(buyer, tender, dates, bidders, bid amounts, winner) are usually only in the images: open EVERY image with your
image viewing tool, in order, and do not stop early however many there are. Do not run OCR tools; read the images.

Write two files in this directory (nothing else):

1. meta.json, one JSON object:
   case_no (사건번호), decision_date (YYYY-MM-DD), respondents (list of company names as printed),
   stated_count (the number of rigged tenders the decision states, e.g. "총 66건" -> 66, else null),
   stated_count_quote (verbatim text from decision.txt containing that number, else null),
   listed (true if the decision lists the rigged tenders individually, false if it only gives totals),
   private_buyers_only (true if every rigged tender was run by a private company, not a public body),
   notes (short; anything that affects the tender list, e.g. "table img014 cut off", "amounts in 천원").

2. tenders.jsonl, one JSON object per line, one per rigged tender or lot (부당한 공동행위의 대상이 된 입찰).
   Only tenders the decision finds rigged; not tenders merely mentioned as background. Fields:
   buyer (발주처/수요기관 as printed), buyer_public (true for a government body, local government, education
     office, public corporation or institution; false for a private company; null if unclear),
   procurement_system ("나라장터" / "자체" (buyer's own e-bidding system) / null, only if the decision says so),
   tender_name (as printed), lot (lot/구역/분류 if any, else null),
   notice_no (나라장터 공고번호 if printed, else null), notice_date, opening_date (투찰일/개찰일), contract_date
     (YYYY-MM-DD or null),
   winner (낙찰자/계약자 as printed), winner_basis (how you know: e.g. "img012 비고 '낙찰'", "img012 순위 1",
     "text: '...낙찰받았다'"; the winner is the firm marked 낙찰/계약/낙찰예정자/1순위 or named as winner, which is NOT
     always the lowest bid or the first row),
   award_amount (the winner's 낙찰금액 / 계약금액 / 투찰금액, integer won, else null),
   base_price (기초금액), reserve_price (예정가격), estimated_price (추정가격) (integers in won or null),
   bid_rate (the winner's 투찰률/낙찰률 in percent as printed, else null),
   bids (list of {name, amount, rate, rank, note} for every bidder shown, values as printed, converted to won;
     [] if not shown),
   source (image file names and/or a verbatim quote from decision.txt that the fields come from),
   text_quote (if any field comes from decision.txt, one verbatim excerpt of it, at most 200 characters, else null).

Copy names and numbers exactly as printed. Convert 천원/백만원/억원 to won only when the table or text states the
unit, and say so in source. Masked names (☆☆☆, ●●●, A사) stay as printed. If a table is unreadable, still write
the row with what you can read and say so in source. If the decision lists no tenders individually, write one line
{"tender_name": "UNLISTED", "count": <number or null>, "text_quote": "..."} plus any tenders it does name.

When done, answer only: DONE <number of tender lines>.
"""

MISSING = """meta.json and/or tenders.jsonl are not in the working directory. Write both files now, exactly as the
instructions above say (open the images if you have not), then answer only: DONE <number of tender lines>."""

lock = threading.Lock()
stop = threading.Event()


class AppServer:
    """One `codex app-server` process serving every worker's thread (instead of one ~250 MB `codex exec` each)."""

    def __init__(self):
        self.proc = subprocess.Popen(['codex', 'app-server', '--stdio'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.next_id, self.replies, self.events, self.send_lock = 0, {}, {}, threading.Lock()
        threading.Thread(target=self.read, daemon=True).start()
        self.request('initialize', {'clientInfo': {'name': 'contract-signals-kftc', 'version': '1'}})
        self.send({'method': 'initialized', 'params': {}})

    def send(self, msg):
        with self.send_lock:
            self.proc.stdin.write(json.dumps(msg) + '\n')
            self.proc.stdin.flush()

    def read(self):
        for line in self.proc.stdout:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            if 'id' in m and 'method' in m:  # a request from the server (approval etc.): never granted
                self.send({'id': m['id'], 'error': {'code': -32601, 'message': 'not supported by this client'}})
            elif 'id' in m:
                box = self.replies.get(m['id'])
                if box:
                    box.append(m)
                    box[0].set()
            else:
                tid = (m.get('params') or {}).get('threadId')
                q = self.events.get(tid)
                if q is not None:
                    q.append(m)
                    q[0].set()
        for box in list(self.replies.values()) + list(self.events.values()):  # server died: wake everyone
            box[0].set()

    def request(self, method, params, timeout=120):
        with self.send_lock:
            self.next_id += 1
            rid = self.next_id
        box = self.replies[rid] = [threading.Event()]
        self.send({'id': rid, 'method': method, 'params': params})
        if not box[0].wait(timeout) or len(box) < 2:
            raise RuntimeError(f'{method}: no reply')
        del self.replies[rid]
        if 'error' in box[1]:
            raise RuntimeError(f'{method}: {box[1]["error"]}')
        return box[1]['result']

    def turn(self, tid, text, effort, timeout):
        """Run one turn; returns (final answer, error text or '')."""
        q = self.events[tid]
        res = self.request('turn/start', {'threadId': tid, 'effort': effort, 'input': [{'type': 'text', 'text': text}]})
        turn_id = (res.get('turn') or {}).get('id')
        answer, errors, deadline = '', [], time.time() + timeout
        while True:
            q[0].wait(max(1, deadline - time.time()))
            q[0].clear()
            while len(q) > 1:
                m = q.pop(1)
                method, params = m.get('method'), m.get('params') or {}
                if method == 'item/completed' and params.get('item', {}).get('type') == 'agentMessage':
                    answer = params['item'].get('text') or answer
                elif method == 'error' and not params.get('willRetry'):  # "Reconnecting... n/5" retries itself
                    errors.append(json.dumps(params.get('error', params), ensure_ascii=False)[:500])
                elif method == 'turn/completed':
                    turn = params.get('turn') or {}
                    if turn.get('error'):
                        errors.append(json.dumps(turn['error'], ensure_ascii=False)[:500])
                    return answer, '\n'.join(errors)
            if self.proc.poll() is not None:
                return answer, '\n'.join(errors + ['app-server exited'])
            if time.time() > deadline:
                try:
                    self.request('turn/interrupt', {'threadId': tid, 'turnId': turn_id})
                except RuntimeError:
                    pass
                return answer, '\n'.join(errors + [f'timeout after {timeout} s'])

    def run(self, work, prompt, model, effort, timeout, required=('tenders.jsonl', 'meta.json'), missing=MISSING):
        res = self.request('thread/start', {'model': model, 'cwd': str(work), 'sandbox': 'workspace-write',
                                            'approvalPolicy': 'never', 'ephemeral': True})
        tid = res['thread']['id']
        self.events[tid] = [threading.Event()]
        try:
            answer, err = self.turn(tid, prompt, effort, timeout)
            nudges = 0
            while not err and nudges < 2 and not all((work / f).exists() for f in required):
                nudges += 1  # answered without writing the files: ask again in the same thread
                answer, err = self.turn(tid, missing, effort, timeout)
            return answer, err, nudges
        finally:
            self.events.pop(tid, None)
            try:
                self.request('thread/unsubscribe', {'threadId': tid}, timeout=30)
            except RuntimeError:
                pass


server = None


def prepare(serial, out):
    src, work, prev = BASE / 'images' / serial, out / serial, out / '.prev' / serial
    if work.exists():  # kept until this run finishes, so a usage-limit stop does not lose the previous result
        if prev.exists():
            shutil.rmtree(prev)
        prev.parent.mkdir(exist_ok=True)
        work.rename(prev)
    work.mkdir(parents=True)
    for f in src.iterdir():
        if f.name == 'decision.txt' or f.suffix == '.png':
            shutil.copy2(f, work / f.name)
    return work


def restore(serial, work):
    shutil.rmtree(work)
    prev = work.parent / '.prev' / serial
    if prev.exists():
        prev.rename(work)


def finish(serial, work, ok, status):
    if ok:  # a failed rerun leaves the previous result in .prev/
        shutil.rmtree(work.parent / '.prev' / serial, ignore_errors=True)
    status.update({'serial': serial, 'ok': ok, 'images': len(list(work.glob('*.png'))),
                   'finished': time.strftime('%Y-%m-%dT%H:%M:%S')})
    for f in work.glob('*.png'):  # the originals stay in images/; keep only the model's output here
        f.unlink()
    (work / 'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=1))


def run_one_app(serial, model, effort, timeout, out):
    work, started = prepare(serial, out), time.time()
    for attempt in range(6):
        try:
            answer, err, nudges = server.run(work, PROMPT, model, effort, timeout)
        except RuntimeError as e:
            answer, err, nudges = '', str(e), 0
        if re.search(r'usage limit|usageLimit', err, re.I):
            stop.set()
            restore(serial, work)
            return serial, 'usage-limit', err[-300:]
        if 'capacity' not in err.lower() or stop.is_set():
            break
        time.sleep(60 * (attempt + 1))  # "model is at capacity" is transient
    ok = not err and (work / 'tenders.jsonl').exists() and (work / 'meta.json').exists()
    finish(serial, work, ok, {'backend': 'app-server', 'answer': answer[-500:], 'stderr': err[-2000:],
                              'nudges': nudges, 'seconds': round(time.time() - started), 'model': model,
                              'effort': effort})
    return serial, 'ok' if ok else 'failed', (answer[-200:] or err[-200:]) + (f' (nudged {nudges}x)' if nudges else '')


def run_one(serial, model, effort, timeout, out):
    work = prepare(serial, out)
    started = time.time()
    for attempt in range(6):  # "model is at capacity" is transient: back off and retry
        try:
            proc = subprocess.run(['sol', '-w', '-m', model, '-e', effort, '-C', str(work)], input=PROMPT, text=True,
                                  capture_output=True, timeout=timeout)
            code, answer, err = proc.returncode, proc.stdout.strip(), proc.stderr.strip()[-2000:]
        except subprocess.TimeoutExpired:
            code, answer, err = -1, '', f'timeout after {timeout} s'
        if code == 0 or 'at capacity' not in err or stop.is_set():
            break
        time.sleep(60 * (attempt + 1))
    if code == 75:
        stop.set()
        restore(serial, work)
        return serial, 'usage-limit', err
    ok = code == 0 and (work / 'tenders.jsonl').exists() and (work / 'meta.json').exists()
    finish(serial, work, ok, {'backend': 'sol', 'exit': code, 'answer': answer[-500:], 'stderr': err,
                              'seconds': round(time.time() - started), 'model': model, 'effort': effort})
    return serial, 'ok' if ok else 'failed', answer[-200:] or err[-200:]


def pending(redo_failed, only, out, force=False):
    todo = []
    for d in sorted((BASE / 'images').iterdir(), key=lambda p: -int(p.name)):
        if only and d.name not in only:
            continue
        status = out / d.name / 'status.json'
        if status.exists() and not (force and only) and (json.loads(status.read_text())['ok'] or not redo_failed):
            continue
        todo.append(d.name)
    return todo


def squash(s):
    return re.sub(r'\s+', '', s or '')


def to_float(v):
    try:
        return float(str(v).replace('%', '').strip())
    except (TypeError, ValueError):
        return None


def norm_name(s):
    return re.sub(r'(주식회사|유한회사|합자회사|\(주\)|\(유\)|㈜|\W)', '', s or '')


def check_tender(t, text):
    problems = []
    if t.get('tender_name') == 'UNLISTED':
        return problems
    winner, bids = norm_name(t.get('winner')), t.get('bids') or []
    if not winner:
        problems.append('no winner')
    elif bids and not any(norm_name(b.get('name')) == winner for b in bids if isinstance(b, dict)):
        problems.append('winner not among bids')
    award, reserve, rate = to_int(t.get('award_amount')), to_int(t.get('reserve_price')), to_float(t.get('bid_rate'))
    if award and reserve and rate and abs(100 * award / reserve - rate) > 0.05:
        problems.append(f'award/reserve {100 * award / reserve:.3f}% vs bid_rate {rate}')
    if award and reserve and not 0.5 < award / reserve < 1.2:
        problems.append('award far from reserve price')
    for b in bids:
        if isinstance(b, dict) and norm_name(b.get('name')) == winner and to_int(b.get('amount')) and award \
                and to_int(b.get('amount')) != award:
            problems.append('award differs from winner bid')
    quote = t.get('text_quote')
    if quote and squash(quote)[:120] not in squash(text):
        problems.append('text_quote not in decision.txt')
    if t.get('notice_no') and not re.fullmatch(r'\d{11}(-\d+)?', str(t['notice_no']).strip()):
        problems.append('odd notice_no')
    return problems


def retried_only(st, work):
    lines = [l for l in (st.get('stderr') or '').splitlines() if l.strip()]
    return (st.get('backend') == 'app-server' and (st.get('answer') or '').startswith('DONE') and lines
            and all(re.search(r'Reconnecting\.\.\.|responseStreamDisconnected|wss://chatgpt\.com', l) for l in lines)
            and (work / 'tenders.jsonl').exists() and (work / 'meta.json').exists())


def check(out):
    rows, summary = [], {'decisions': 0, 'tenders': 0, 'flagged': 0, 'failed': [], 'count_short': [], 'mostly_empty': []}
    for work in sorted(out.iterdir()):
        status = work / 'status.json'
        if not work.is_dir() or not status.exists():
            continue
        st = json.loads(status.read_text())
        if not st['ok'] and retried_only(st, work):  # marked failed by an earlier version that counted retries
            st.update(ok=True, reclassified='only retried reconnect errors; files written')
            status.write_text(json.dumps(st, ensure_ascii=False, indent=1))
        if not st['ok']:
            summary['failed'].append(work.name)
            continue
        text = (BASE / 'images' / work.name / 'decision.txt').read_text()
        try:
            meta = json.loads((work / 'meta.json').read_text())
        except json.JSONDecodeError as e:
            summary['failed'].append(f'{work.name} meta.json: {e}')
            continue
        tenders, bad = [], 0
        for line in (work / 'tenders.jsonl').read_text().splitlines():
            if line.strip():
                try:
                    tenders.append(json.loads(line))
                except json.JSONDecodeError:
                    bad += 1
        summary['decisions'] += 1
        listed = [t for t in tenders if t.get('tender_name') != 'UNLISTED']
        stated = to_int(meta.get('stated_count'))
        decision_problems = []
        if bad:
            decision_problems.append(f'{bad} unparsable lines')
        if meta.get('stated_count_quote') and squash(meta['stated_count_quote'])[:120] not in squash(text):
            decision_problems.append('stated_count_quote not in decision.txt')
        empty = [t for t in listed if not t.get('winner') and not t.get('award_amount')]
        if listed and len(empty) >= len(listed) / 2 and not meta.get('private_buyers_only'):
            decision_problems.append(f'{len(empty)} of {len(listed)} rows without winner or amount')
            summary['mostly_empty'].append(work.name)  # often the model skipped the tables: redo with Sol
        if stated and meta.get('listed') and len(listed) < stated:
            decision_problems.append(f'{len(listed)} listed < stated {stated}')
            summary['count_short'].append(work.name)
        for i, t in enumerate(tenders):
            problems = check_tender(t, text) + decision_problems
            summary['tenders'] += 1
            summary['flagged'] += bool(problems)
            rows.append({'serial': work.name, 'i': i, 'case_no': meta.get('case_no'),
                         'decision_date': meta.get('decision_date'), **t, 'problems': problems})
    with open(out / 'checked.jsonl', 'w') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    summary['count_short'] = len(summary['count_short'])
    (out / 'mostly-empty.txt').write_text('\n'.join(summary['mostly_empty']) + '\n')
    summary['mostly_empty'] = len(summary['mostly_empty'])
    print(json.dumps(summary, ensure_ascii=False, indent=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--model', default='gpt-6.1-sol', help='Codex model, e.g. gpt-6-luna')
    parser.add_argument('--backend', choices=['app-server', 'sol'], default='app-server')
    parser.add_argument('--effort', default='medium')
    parser.add_argument('--out', type=Path, default=BASE / 'extract')
    parser.add_argument('--timeout', type=int, default=3600, help='seconds per decision')
    parser.add_argument('--limit', type=int, help='at most this many decisions this run')
    parser.add_argument('--only', nargs='*', help='these decision serials only')
    parser.add_argument('--redo-failed', action='store_true')
    parser.add_argument('--force', action='store_true', help='with --only: redo those decisions even if done')
    parser.add_argument('--check', action='store_true', help='only check existing output')
    args = parser.parse_args()
    if args.check:
        return check(args.out)
    todo = pending(args.redo_failed, set(args.only or []), args.out, args.force)[:args.limit]
    print(f'{len(todo)} decisions to extract, {args.workers} workers, {args.backend}', flush=True)
    global server
    if args.backend == 'app-server' and todo:
        server = AppServer()
    done = 0

    def task(serial):
        nonlocal done
        if stop.is_set():
            return
        serial, state, info = (run_one_app if args.backend == 'app-server' else run_one)(
            serial, args.model, args.effort, args.timeout, args.out)
        with lock:
            done += 1
            print(f'{done}/{len(todo)} {serial}: {state} {info}', flush=True)

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(task, todo))
    if stop.is_set():
        sys.exit('stopped: Sol usage limit reached; rerun after the reset')
    check(args.out)


if __name__ == '__main__':
    main()
