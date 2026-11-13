#!/usr/bin/env python3
"""Research only: read French administrative-court procurement rulings with Luna (or a second reader) into a fixed JSON
for the irregular-award labels (research/calibration/france-labels-plan.md, "Reading").

Input: ~/.cache/contract-signals/france-admin/rulings/{TA,CAA,CE}/<id>.xml (tools/fetch-france-admin-rulings.py).
Per ruling, ruling.txt is written to france-admin/extract/<id>/ and the model writes result.json there: relevance,
action type, outcome class (A1 steering, A2 no competition, A3 procedural, C challenged but regular, X other), the
court's findings quoted verbatim, the contracts named, earlier and later rulings cited, finality hints.
`--solution` picks the reading order of the plan (wins, then rejections, then the rest). Resumable: rulings with a
status.json are skipped. Stops every worker at the usage limit; rerun after the reset.

`--check` only (re)runs the checks and writes extract/checked.jsonl (problems: invalid JSON, quote not in ruling.txt,
low confidence, class A without a contract, ...) and extract/to-second.txt: rulings with a problem or class A or C, for
a second reading (`--model mistral/deepseek-v4-1-flash-1017 --out .../extract-deepseek --only $(cat to-second.txt)`).
The model runners are those of tools/extract-korea-court-rulings.py.
"""
import argparse
import html
import importlib.util
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('kor', HERE / 'extract-korea-court-rulings.py')
kor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kor)

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/france-admin'
WINS = {'Satisfaction totale', 'Satisfaction partielle'}
META = ('Nom_Juridiction', 'Numero_Dossier', 'Date_Lecture', 'Type_Decision', 'Type_Recours', 'Solution')

# The sentences inline_prompt() rewrites for models without file tools are kept word for word from the Korean prompt.
PROMPT = """ruling.txt in this directory is one French administrative-court ruling (tribunal administratif, cour
administrative d'appel or Conseil d'État) about public procurement. Many are about running a contract, not awarding
it. Read ALL of it (use your file tools; it can be long, so read it in parts and do not
stop early) and write result.json in this directory (nothing else), one JSON object:

relevant: true if the court rules on whether the AWARD of one or more specific public contracts, concessions or
  framework agreements (publicity, competition, choice of procedure, specifications, criteria, offer analysis,
  choice of the winner, amendments that are in effect a new contract) was lawful. false for disputes about running a
  contract (payment, price revision, penalties, final account, termination, works damage, decennial liability),
  inadmissible or withdrawn claims, no need to rule, expert appointments, and anything else.
relevant_reason: one short sentence.
case: {case_no (numéro as printed), court, level ("TA" / "CAA" / "CE"), decision_date (YYYY-MM-DD), action: one of
  "refere_precontractuel" (L. 551-1), "refere_contractuel" (L. 551-13), "validity_third_party" (Tarn-et-Garonne,
  or contesting the validity of the contract), "prefect_referral" (déféré préfectoral), "damages_ousted_bidder"
  (indemnisation d'un candidat évincé), "excess_of_power" (recours pour excès de pouvoir, e.g. against a detachable
  act), "execution" (running the contract), "other";
  claimant_role ("ousted_bidder" / "buyer" / "contractor" / "prefect" / "third_party" / "other"),
  remedy (short, e.g. "procédure annulée au stade de l'analyse des offres", "contrat résilié", "rejet", null),
  lower_rulings (earlier rulings cited in this case: list of {court, case_no, date}),
  appeal_hints (short: anything printed on appeal or cassation, e.g. "jugement du TA de Lyon annulé", null)}.
outcome_class: one of
  "A1" steering: the court holds the award irregular because criteria or specifications were tailored to a firm,
    information or negotiation was unequal, there was a conflict of interest or impartiality breach, or an offer was
    accepted that should have been rejected (irregular, unacceptable, inappropriate or abnormally low after
    examination);
  "A2" no competition: no publicity or competition where required, wrong procedure, unlawful splitting, unlawful
    direct award, or an amendment or extension that is in effect a new contract;
  "A3" procedural: any other irregularity of the award held by the court (faulty offer analysis, an offer misread or
    mis-scored (dénaturation), an unlawful scoring method, criteria, weighting or method not disclosed, abnormally
    low offer not examined, reasons not given to the losing bidder, ...);
  "C": the award was challenged and the court finds no irregularity (or none that it holds), including challenges
    rejected because the irregularity did not harm the claimant ONLY if the court says there was none;
  "X": everything else (execution disputes, inadmissible, withdrawn, no need to rule, expert appointed, ...).
  If the court holds several irregularities, pick the first of A1, A2, A3 that applies. An irregularity found but
  without harm to the claimant (claim rejected for that reason) still counts as A1-A3. An irregularity found by the
  lower court and overturned here is not held: use the class for what THIS ruling holds.
findings: list, one per ground of irregularity the court examines (empty for X):
  {class ("A1" / "A2" / "A3"), ground (short, in French, e.g. "critère de notation non communiqué"),
   held (true: the court holds it; false: rejected; null: not decided), quote (verbatim excerpt of ruling.txt, at
   most 250 characters, where the court decides it)}.
contracts: list, EVERY contract or award procedure the ruling is about:
  {buyer (pouvoir adjudicateur / entité adjudicatrice as printed), object (objet du marché as printed), lot (as printed
   or null), procedure ("appel d'offres ouvert" / "procédure adaptée" / "négociée" / "dialogue compétitif" /
   "sans publicité ni mise en concurrence" / "concession" / other as printed, null if not stated), notice_date,
   award_date (attribution or signature, YYYY-MM-DD or YYYY-MM or null), amount (euros as a number, null if not
   stated), amount_vat ("HT" / "TTC" / null), winner (attributaire as printed, null if none or anonymised),
   winner_siren (only if printed), signed (true if the contract was signed, false if the procedure was stopped
   before signature, null if unclear), quote (verbatim excerpt, at most 250 characters, that names this contract)}.
outcome_quote: verbatim excerpt (at most 250 characters) of the operative part (dispositif, "DÉCIDE" / "ORDONNE")
  or the conclusion.
confidence: "high" if the text was clear and you read all of it; "low" if anything was unclear, cut off, or you are
  unsure of the class or of which contract is meant.
unsure: short note on what is unclear, else null.

Rules: copy names, numbers and quotes exactly as in ruling.txt (quotes must be found verbatim in the file; copy them
from the file, do not retype). Never guess a buyer, date or amount that is not printed. If relevant is false,
outcome_class is "X" and findings may be []. When done, answer only: DONE <number of contracts>.
"""

MISSING = """result.json is not in the working directory. Write it now, exactly as the instructions above say, then
answer only: DONE <number of contracts>."""

_paths = None


def paths():
    global _paths
    if _paths is None:
        _paths = {p.stem: p for p in (BASE / 'rulings').glob('*/*.xml')}
    return _paths


def parse(rid):
    # tag regexes, not an XML parser: some published files are not well-formed (stray "&" or "<" in the text)
    raw = paths()[rid].read_text(encoding='utf-8-sig', errors='replace')
    tag = lambda t: (m.group(1) if (m := re.search(f'<{t}>(.*?)</{t}>', raw, re.S)) else '')
    meta = {f: html.unescape(tag(f)).strip() for f in META}
    body = tag('Texte_Integral')
    body = re.sub(r'</p>|<br\s*/?>', '\n', body)
    body = html.unescape(re.sub(r'<[^>]+>', '', body))
    body = re.sub(r'[ \t\xa0]+', ' ', body)
    body = re.sub(r'\n\s*\n+', '\n', body).strip()
    return meta, body


def ruling_text(rid):
    meta, body = parse(rid)
    head = '\n'.join(f'{f}: {meta[f]}' for f in META if meta[f])
    return meta, f'{head}\n\n{body}\n'


def solution_group(sol):
    return 'wins' if sol in WINS else 'rejections' if sol.startswith('Rejet') else 'rest'


def pending(only, out, force, group):
    todo = []
    for rid in sorted(paths()):
        if only and rid not in only:
            continue
        if group and solution_group(parse(rid)[0]['Solution']) != group:
            continue
        st = out / rid / 'status.json'
        if st.exists() and not force and json.loads(st.read_text()).get('ok'):
            continue
        todo.append(rid)
    return todo


CLASSES = {'A1', 'A2', 'A3', 'C', 'X'}


def check(out):
    squash = kor.squash
    rows, second = [], []
    for d in sorted(p for p in out.iterdir() if p.is_dir() and not p.name.startswith('.')):
        st = json.loads((d / 'status.json').read_text()) if (d / 'status.json').exists() else {}
        problems, res = [], None
        if not st.get('ok'):
            problems.append('extraction failed')
        else:
            try:
                res = json.loads((d / 'result.json').read_text())
            except (json.JSONDecodeError, OSError):
                problems.append('result.json not valid JSON')
        cls = None
        if res is not None:
            text = squash((d / 'ruling.txt').read_text())
            cls = res.get('outcome_class')
            if cls not in CLASSES:
                problems.append(f'outcome_class {cls!r}')
            if res.get('relevant') is None:
                problems.append('relevant missing')
            if res.get('confidence') != 'high':
                problems.append('low confidence')
            quotes = [res.get('outcome_quote')] + [f.get('quote') for f in res.get('findings') or []] \
                + [c.get('quote') for c in res.get('contracts') or []]
            bad = sum(1 for q in quotes if q and squash(q) not in text)
            if bad:
                problems.append(f'{bad} quote(s) not in ruling.txt')
            if cls in ('A1', 'A2', 'A3', 'C') and not res.get('contracts'):
                problems.append(f'class {cls} without a contract')
            if cls in ('A1', 'A2', 'A3') and not any(f.get('held') for f in res.get('findings') or []):
                problems.append(f'class {cls} without a held finding')
        rows.append({'id': d.name, 'model': st.get('model'), 'problems': problems, 'result': res})
        if (problems or cls in ('A1', 'A2', 'A3', 'C')) and st.get('model') not in kor.STRONG:
            second.append(d.name)
    with open(out / 'checked.jsonl', 'w') as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    (out / 'to-second.txt').write_text('\n'.join(second) + ('\n' if second else ''))
    counts = {}
    for r in rows:
        k = (r['result'] or {}).get('outcome_class') or 'none'
        counts[k] = counts.get(k, 0) + 1
    print(f'{len(rows)} rulings read, classes {dict(sorted(counts.items()))}, '
          f'{sum(1 for r in rows if r["problems"])} with problems, {len(second)} for a second reading (to-second.txt)')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--workers', type=int, default=12)
    parser.add_argument('--model', default='gpt-6-luna', help='as in extract-korea-court-rulings.py')
    parser.add_argument('--effort', default='medium')
    parser.add_argument('--out', type=Path, default=BASE / 'extract')
    parser.add_argument('--timeout', type=int, default=1800, help='seconds per ruling')
    parser.add_argument('--solution', choices=('wins', 'rejections', 'rest'), help='only rulings with this court-reported outcome')
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
    # the Korean runner reads these module globals
    kor.PROMPT, kor.MISSING, kor.ruling_text, kor.selected = PROMPT, MISSING, ruling_text, lambda rid: True
    kor.CLAUDE_LEAN[-1] = 'You extract data from French court rulings. Answer only with the JSON object asked for.'
    todo = pending(set(args.only or []), args.out, args.force, args.solution)[:args.limit]
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
    check(args.out)


if __name__ == '__main__':
    main()
