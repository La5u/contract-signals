#!/usr/bin/env python3
"""Research only: read administrative cartel-damages candidates into collusion findings."""
import argparse
import importlib.util
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('admin', HERE / 'extract-france-admin-rulings.py')
admin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(admin)
kor = admin.kor
BASE = admin.BASE

PROMPT = """ruling.txt in this directory is one French administrative-court ruling about a possible procurement cartel.
Read ALL of it (use your file tools; it can be long, so read it in parts and do not
stop early) and write result.json in this directory (nothing else), one JSON object:

cartel_held: "yes" if THIS court holds collusion or bid rigging affecting named public contracts, including when
  it relies on a competition decision and awards damages; "no" if it rejects that finding; "undecided" if it does
  not decide it here, including damages-only decisions relying on a finding in an earlier ruling. Distinguish an
  allegation or an overturned lower finding from what this court holds. Explain in finding and appeal_hints.
finding: {description (short), quote (verbatim excerpt of ruling.txt, at most 250 characters stating what was decided)}.
case: {case_no, court, decision_date, earlier_rulings and later_rulings (each a list of {court, case_no, date}),
  appeal_hints (including pending appeal, quashing, remand or damages-only ruling, as stated)}.
contracts: list EVERY contract or lot tied to the cartel, even where the court leaves the finding undecided:
  {buyer, object, lot, amount (euros as a number), amount_vat ("HT" / "TTC" / null), award_date, signature_date
   (dates YYYY-MM-DD or YYYY-MM if known), winner, winner_siren (only if printed), quote (verbatim excerpt of
   ruling.txt, at most 250 characters identifying the contract)}.
cartel_members: list of names as printed; competition_decisions: list of {authority, number, date} for decisions of
  the Autorité de la concurrence or its predecessor cited. confidence: "high" if clear and you read all of it,
  otherwise "low"; unsure: short note or null.

Rules: copy names, numbers and quotes exactly as in ruling.txt (quotes must be found verbatim in the file; copy them
from the file, do not retype). Never guess a buyer, date or amount that is not printed.
When done, answer only: DONE <number of contracts>.
"""
MISSING = admin.MISSING


def check(out, kind):
    rows, second = [], []
    for d in sorted(p for p in out.iterdir() if p.is_dir() and not p.name.startswith('.')):
        problems, res = [], None
        try:
            st = json.loads((d / 'status.json').read_text())
            if not st.get('ok'):
                problems.append('extraction failed')
            else:
                res = json.loads((d / 'result.json').read_text())
                if not isinstance(res, dict):
                    raise ValueError('result is not an object')
        except (OSError, ValueError):
            st = {}
            problems.append('missing or invalid status/result JSON')
        if res is not None:
            try:
                text = kor.squash((d / 'ruling.txt').read_text())
                if kind == 'cartel':
                    if res.get('cartel_held') not in ('yes', 'no', 'undecided'):
                        problems.append('invalid cartel_held')
                    quotes = [(res.get('finding') or {}).get('quote')]
                    contracts = res.get('contracts') or []
                    quotes += [c.get('quote') for c in contracts]
                    if res.get('cartel_held') == 'yes' and not contracts:
                        problems.append('cartel held without a named contract')
                    if res.get('cartel_held') in ('yes', 'no') and not quotes[0]:
                        problems.append('finding quote missing')
                else:
                    if not isinstance(res.get('relevant'), bool):
                        problems.append('invalid relevant')
                    findings = res.get('findings') or []
                    contracts = [c for f in findings for c in f.get('contracts') or []]
                    quotes = [f.get('quote') for f in findings] + [c.get('quote') for c in contracts]
                    if res.get('relevant') and not findings:
                        problems.append('relevant without findings')
                    if res.get('relevant') and not contracts:
                        problems.append('relevant without a named contract')
                    if any(not f.get('quote') for f in findings):
                        problems.append('finding quote missing')
                if any(not c.get('quote') for c in contracts):
                    problems.append('contract quote missing')
                bad = sum(1 for q in quotes if q and kor.squash(q) not in text)
                if bad:
                    problems.append(f'{bad} quote(s) not in ruling.txt')
                if res.get('confidence') != 'high':
                    problems.append('low confidence')
            except (OSError, TypeError, AttributeError):
                problems.append('missing text or malformed result fields')
        rows.append({'id': d.name, 'model': st.get('model'), 'problems': problems, 'result': res})
        if problems:
            second.append(d.name)
    with (out / 'checked.jsonl').open('w') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    (out / 'to-second.txt').write_text('\n'.join(second) + ('\n' if second else ''))
    print(f'{len(rows)} rulings checked, {len(second)} with problems (to-second.txt)')


def read(ids, args, prompt, ruling_text, kind):
    if args.only is not None:
        if not args.only:
            sys.exit('--only was given no rulings')
        unknown = set(args.only) - set(ids)
        if unknown:
            sys.exit('unknown or unselected IDs: ' + ', '.join(sorted(unknown)))
        ids = [rid for rid in ids if rid in set(args.only)]
    todo = []
    for rid in ids:
        st = args.out / rid / 'status.json'
        try:
            if not args.force and json.loads(st.read_text()).get('ok'):
                continue
        except (OSError, ValueError):
            pass
        todo.append(rid)
    todo = todo[:args.limit]
    kor.PROMPT, kor.MISSING, kor.ruling_text, kor.selected = prompt, MISSING, ruling_text, lambda rid: True
    kor.CLAUDE_LEAN[-1] = 'You extract data from French court rulings. Answer only with the JSON object asked for.'
    print(f'{len(todo)} rulings to read, {args.workers} workers, {args.model}', flush=True)
    if todo and args.model not in kor.CLAUDE_MODELS and not args.model.startswith(('opencode/', 'opencode-go/', 'gemini/', 'mistral/')):
        kor.kftc.server = kor.kftc.AppServer()
    done, lock = 0, threading.Lock()

    def task(rid):
        nonlocal done
        if kor.kftc.stop.is_set():
            return
        rid, state, info = kor.run_one(rid, args.model, args.effort, args.timeout, args.out)
        with lock:
            done += 1
            print(f'{done}/{len(todo)} {rid}: {state} {info}', flush=True)

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(task, todo))
    if kor.kftc.stop.is_set():
        sys.exit('stopped: usage limit reached; rerun after the reset')
    check(args.out, kind)


def parser(default_out, default_model, default_workers):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workers', type=int, default=default_workers)
    p.add_argument('--model', default=default_model)
    p.add_argument('--effort', default='medium')
    p.add_argument('--out', type=Path, default=default_out)
    p.add_argument('--timeout', type=int, default=1800)
    p.add_argument('--limit', type=int)
    p.add_argument('--only', nargs='*')
    p.add_argument('--force', action='store_true')
    p.add_argument('--check', action='store_true')
    return p


def main():
    p = parser(BASE / 'extract-cartel', 'gpt-6-luna', 12)
    args = p.parse_args()
    if args.workers < 1 or (args.limit is not None and args.limit < 0):
        p.error('workers must be positive and limit nonnegative')
    args.out.mkdir(parents=True, exist_ok=True)
    if args.check:
        return check(args.out, 'cartel')
    ids = (BASE / 'cartel-candidates.txt').read_text().split()
    missing = set(ids) - set(admin.paths())
    if missing:
        sys.exit('candidate IDs missing from corpus: ' + ', '.join(sorted(missing)))
    read(ids, args, PROMPT, admin.ruling_text, 'cartel')


if __name__ == '__main__':
    main()
