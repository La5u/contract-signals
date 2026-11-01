#!/usr/bin/env python3
"""Read each earlier/later ruling pair in finality.jsonl; resumable, with the administrative-ruling runners.

--only accepts earlier ruling IDs or pair IDs (EARLIER__LATER). --check writes checked.jsonl and to-second.txt.
Long texts are excerpted, prioritising the operative part and passages citing the earlier case number.
"""
import argparse
import importlib.util
import json
import re
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
DEFAULT_INPUT = BASE / 'finality-2026-11-01/finality.jsonl'

PROMPT = """ruling.txt in this directory is a pair of French administrative court rulings, EARLIER and LATER.
Read the supplied texts and write result.json in this directory (nothing else), one JSON object:
- same_case: "yes" if the later ruling reviews the earlier ruling in the same litigation, otherwise "no".
- effect: "confirmed", "reversed", "partly_reversed", or "not_examined", describing the effect on the
  EARLIER ruling's finding about irregularity of the award, not merely the disposition or class of either ruling.
  Use not_examined for cassation not admitted, withdrawal, or decision on other grounds. Do not infer reversal
  merely from different outcome classes. If same_case is no, use not_examined.
- earlier_final_after_this: "yes" or "no"; yes only if this decision makes the earlier finding final.
- quote: a verbatim excerpt from the LATER text supporting the effect and finality, at most 250 characters.
- confidence: "high" or "low"; use low if the evidence is unclear or the excerpts are insufficient.
- explanation: brief explanation including whether cassation was not admitted, if applicable.
Copy the quote exactly from ruling.txt. Excerpts may omit parts of the original decisions; do not assume omitted
text supports a conclusion. When done, answer only: DONE.
"""
MISSING = 'result.json is missing. Write it as instructed, then answer only: DONE.'
EFFECTS = {'confirmed', 'reversed', 'partly_reversed', 'not_examined'}


def pairs(path):
    result = {}
    with path.open() as f:
        for line in f:
            row = json.loads(line)
            if row.get('class') not in {'A1', 'A2', 'A3', 'C'}:
                continue
            for later in row.get('later_rulings') or []:
                earlier, other = row['ruling'], later['ruling']
                result[earlier + '__' + other] = (earlier, other)
    return result


def excerpt(text, earlier, limit=45000):
    if len(text) <= limit:
        return text
    # Reserve space for the introduction, references and the end (which contains the dispositif).
    # Merge overlapping windows so passages remain verbatim and in source order.
    number = re.search(r'_(.+)_\d{8}$', earlier)
    needles = re.findall(r'\d{2}[A-Z]{2}\d{4,6}|\d{6,8}', number.group(1), re.I) if number else []
    windows = [(0, 6000), (len(text) - 15000, len(text))]
    headings = list(re.finditer(r'(?im)^\s*(?:D\s*[ÉE]\s*C\s*I\s*D\s*E|ORDONNE)\s*:', text))
    if headings:
        start = headings[-1].start()
        windows.append((start, min(len(text), start + 6000)))
    reference_budget = limit - 28000
    for needle in needles:
        pattern = r'\s*'.join(map(re.escape, needle))
        for match in re.finditer(pattern, text, re.I):
            if reference_budget <= 0:
                break
            start = max(0, text.rfind('\n', 0, max(0, match.start() - 1000)))
            end = min(len(text), match.end() + min(2000, reference_budget))
            if end - start > reference_budget:
                start = max(0, match.start() - reference_budget // 3)
                end = min(len(text), start + reference_budget)
            windows.append((start, end))
            reference_budget -= end - start
    merged = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return '\n[... omitted ...]\n'.join(text[start:end] for start, end in merged) + '\n[... excerpts from longer ruling ...]\n'



def ruling_text(pair):
    earlier, later = pair.split('__', 1)
    _, first = admin.ruling_text(earlier)
    _, second = admin.ruling_text(later)
    return {}, '=== EARLIER ===\n' + excerpt(first, earlier) + '\n=== LATER ===\n' + excerpt(second, earlier)


def check(out):
    rows, second = [], []
    for d in sorted(p for p in out.iterdir() if p.is_dir() and not p.name.startswith('.') and '__' in p.name):
        earlier, later = d.name.split('__', 1)
        try:
            st = json.loads((d / 'status.json').read_text())
        except (OSError, ValueError):
            st = {}
        problems, res = [], None
        if not st.get('ok'):
            problems.append('extraction failed')
        else:
            try:
                res = json.loads((d / 'result.json').read_text())
                if not isinstance(res, dict):
                    raise ValueError('not an object')
            except (OSError, ValueError):
                problems.append('result.json not valid JSON object')
        if res is not None:
            for key, allowed in [('same_case', {'yes', 'no'}), ('effect', EFFECTS),
                                 ('earlier_final_after_this', {'yes', 'no'})]:
                if res.get(key) not in allowed:
                    problems.append(f'{key} invalid or missing')
            if res.get('confidence') != 'high':
                problems.append('low confidence')
            quote = res.get('quote')
            try:
                later_text = (d / 'ruling.txt').read_text().split('=== LATER ===\n', 1)[1]
            except (OSError, IndexError):
                later_text = ''
            if not isinstance(quote, str) or not quote.strip() or kor.squash(quote) not in kor.squash(later_text):
                problems.append('quote missing or not in later ruling.txt')
        rows.append({'id': d.name, 'earlier': earlier, 'later': later, 'model': st.get('model'),
                     'problems': problems, 'result': res})
        if problems:
            second.append(d.name)
    (out / 'checked.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
    (out / 'to-second.txt').write_text(''.join(x + '\n' for x in second))
    print(f'{len(rows)} pairs read, {len(second)} with problems')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    p.add_argument('--out', type=Path, default=BASE / 'extract-appeal-effects')
    p.add_argument('--workers', type=int, default=12)
    p.add_argument('--model', default='gpt-6.1-terra')
    p.add_argument('--effort', default='medium')
    p.add_argument('--timeout', type=int, default=1800)
    p.add_argument('--only', nargs='*')
    p.add_argument('--limit', type=int)
    p.add_argument('--force', action='store_true')
    p.add_argument('--check', action='store_true')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    if a.check:
        return check(a.out)
    if a.only is not None and not a.only:
        sys.exit('--only was given no rulings or pairs')
    selected = set(a.only or [])
    todo = []
    for pair, (earlier, later) in sorted(pairs(a.input).items()):
        if selected and pair not in selected and earlier not in selected:
            continue
        status = a.out / pair / 'status.json'
        if status.exists() and not a.force:
            try:
                if json.loads(status.read_text()).get('ok'):
                    continue
            except (OSError, ValueError):
                pass
        todo.append(pair)
    todo = todo[:a.limit]
    kor.PROMPT, kor.MISSING, kor.ruling_text, kor.selected = PROMPT, MISSING, ruling_text, lambda _: True
    # The inline runners need the pair prompt, not the administrative-ruling prompt's rewriting rules.
    kor.inline_prompt = lambda work, limit: (PROMPT.replace('write result.json in this directory (nothing else), one JSON object:',
        'answer with only one JSON object:').replace('When done, answer only: DONE.', '')
        + '\n===RULING===\n' + (work / 'ruling.txt').read_text()[:limit])
    print(f'{len(todo)} pairs to read, {a.workers} workers, {a.model}', flush=True)
    if todo and a.model not in kor.CLAUDE_MODELS and not a.model.startswith(('opencode/', 'opencode-go/')):
        kor.kftc.server = kor.kftc.AppServer()
    done, lock = 0, threading.Lock()
    def task(pair):
        nonlocal done
        if kor.kftc.stop.is_set():
            return
        _, state, info = kor.run_one(pair, a.model, a.effort, a.timeout, a.out)
        with lock:
            done += 1
            print(f'{done}/{len(todo)} {pair}: {state} {info}', flush=True)
    with ThreadPoolExecutor(a.workers) as pool:
        list(pool.map(task, todo))
    if kor.kftc.stop.is_set():
        sys.exit('stopped: usage limit reached; rerun after the reset')
    check(a.out)


if __name__ == '__main__':
    main()
