#!/usr/bin/env python3
"""Recheck the finality of verdicts whose labels are not yet final.

Research only. Works on every verdict behind a cohort tender marked pending-appeal or too-recent.

  pages    re-read https://reyestr.court.gov.ua/Review/<id> (serial, spaced, capped; new dated cache
           directory, so earlier reads stay intact) for "Дата набрання законної сили". A date found
           replaces the earlier value in court-register/finality.json; replaced values go to
           finality-history.json. A captcha stops the run (no bypass).
  appeals  download the texts of the later higher-court decisions in the same case (doc_url from the
           register export, od.reyestr.court.gov.ua) and write their operative parts for review to
           verdict-work/appeals/extracts.jsonl. Nothing in the labels changes.
  apply    take a reviewed outcome file (JSON Lines: verdict_id, status final | not final | unclear, …),
           write research/labels/ukraine-verdict-appeal-outcomes.json (no court-text quotes) and set
           verification.finality of those verdicts in the label files: upheld -> confirmed, verdict
           quashed with a retrial -> quashed, appellate ruling quashed in cassation -> pending-appeal.

Rebuild the labels afterwards and run tools/publish-ukraine-labels.py.
"""
import argparse
import gzip
import importlib.util
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sweep', ROOT / 'tools/sweep-ukraine-verdicts.py')
sw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sw)
bc = sw.bc

COHORTS = [ROOT / 'research/labels/ukraine-verdict-plus-linked-cohort.json.gz']
NOT_FINAL = ('pending-appeal', 'too-recent')
WORK = Path.home() / '.cache/contract-signals/verdict-work/appeals'
OPERATIVE_CHARS = 2500
OUTCOMES = ROOT / 'research/labels/ukraine-verdict-appeal-outcomes.json'
LABEL_FILES = ['ukraine-verdict-sweep-reviewed.json', 'ukraine-verdict-linked.json', 'ukraine-verdict-sweep-plus-linked.json']
UNREDACTED = Path.home() / '.cache/contract-signals/unredacted/labels-2026-10-14'


def pending_verdicts(paths):
    ids = set()
    for path in paths:
        for t in json.load(gzip.open(path))['tenders']:
            if t.get('finality') in NOT_FINAL:
                ids.update(str(v) for v in t['verdict_ids'])
    return sorted(ids)


def pages(args, ids):
    path, history_path = sw.BASE / 'finality.json', sw.BASE / 'finality-history.json'
    found_pages = json.loads(path.read_text()) if path.exists() else {}
    history = json.loads(history_path.read_text()) if history_path.exists() else {}
    f = bc.Fetcher(sw.BASE / f'review-pages-recheck-{args.day}', budget=args.budget, network=True,
                   min_interval=args.interval, opener=sw.opener('text/html'), prior=0)
    found, still = {}, {}
    try:
        for doc in ids:
            if (found_pages.get(doc) or '')[:2] == '20':
                continue
            state = sw.page_state(f.fetch(f'https://reyestr.court.gov.ua/Review/{doc}'))
            if state[:2] == '20':
                found[doc] = state
                history.setdefault(doc, []).append({'value': found_pages.get(doc), 'replaced': args.day})
                found_pages[doc] = state
                path.write_text(json.dumps(found_pages, indent=1))
                history_path.write_text(json.dumps(history, indent=1))
            else:
                still[doc] = state
    except (bc.BudgetExceeded, bc.Blocked, bc.Throttled) as e:
        print(f'stopped: {e}')
    print(json.dumps({'verdicts': len(ids), 'now_final': found, 'still_no_date': still}, indent=1))


def operative(text):
    """Text after the last УХВАЛИВ / ПОСТАНОВИВ / ЗАСУДИВ heading, or the end of the text."""
    heads = list(sw.OPERATIVE_RE.finditer(text))
    part = text[heads[-1].end():] if heads else text[-OPERATIVE_CHARS:]
    return ' '.join(part.split())[:OPERATIVE_CHARS]


def appeals(args, ids):
    rows = list(sw.stream_selected())
    by_id = {r['doc_id']: r for r in rows}
    higher = sw.appeals(rows)
    f = bc.Fetcher(sw.TEXTS, budget=args.budget + bc.Fetcher(sw.TEXTS, prior=0).requests, network=True,
                   min_interval=args.interval, opener=sw.opener('*/*'), prior=0)
    WORK.mkdir(parents=True, exist_ok=True)
    out, missing = [], []
    try:
        for doc in ids:
            v = by_id.get(doc)
            if v is None:
                missing.append(doc)
                continue
            later = sorted((d for d in higher.get(v['cause_num'], []) if d['adjudication_date'] >= v['adjudication_date'] and d['doc_id'] != doc),
                           key=lambda d: (d['adjudication_date'], d['doc_id']))
            decisions = []
            for d in later:
                url = (by_id.get(d['doc_id']) or {}).get('doc_url')
                hit = f.fetch(url) if url else None
                f.responses.clear()
                decisions.append({**d, 'doc_url': url, 'operative': operative(sw.plain(hit['body'])) if hit and hit['body'] else None})
            out.append({'verdict_id': doc, 'case_number': v['cause_num'], 'court': v['court'], 'verdict_date': v['adjudication_date'],
                        'decisions': decisions})
    except (bc.BudgetExceeded, bc.Blocked, bc.Throttled) as e:
        print(f'stopped: {e}')
    path = WORK / 'extracts.jsonl'
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in out))
    print(json.dumps({'verdicts': len(ids), 'written': len(out), 'not_in_export': missing,
                      'decisions': sum(len(r['decisions']) for r in out),
                      'without_text': sum(d['operative'] is None for r in out for d in r['decisions']), 'output': str(path)}, indent=1))


def finality_text(o, decision):
    where = f"{decision['court']} on {decision['adjudication_date']} (decision {decision['doc_id']})"
    if o['status'] == 'final':
        return f'appeal: conviction upheld by {where}; in force when pronounced, CPC art. 532'
    if decision['instance'] == '1':
        return f'appeal: appellate ruling quashed by {where}, new appellate hearing ordered; not final'
    return f'appeal: verdict quashed by {where}, retrial ordered; not final'


def apply(args, ids):
    reviewed = [json.loads(line) for line in Path(args.reviewed).read_text().splitlines() if line.strip()]
    extracts = {json.loads(line)['verdict_id']: json.loads(line) for line in (WORK / 'extracts.jsonl').read_text().splitlines() if line.strip()}
    out, texts = [], {}
    for o in reviewed:
        decision = next((d for d in extracts[o['verdict_id']]['decisions'] if d['doc_id'] == o.get('decisive_doc_id')), None)
        row = {'verdict_id': o['verdict_id'], 'reyestr_url': f"https://reyestr.court.gov.ua/Review/{o['verdict_id']}", 'status': o['status']}
        if o['status'] in ('final', 'not final') and decision:
            texts[o['verdict_id']] = finality_text(o, decision)
            row.update({'how': o['how'], 'decision_date': decision['adjudication_date'], 'decision_court': decision['court'],
                        'decision_url': f"https://reyestr.court.gov.ua/Review/{decision['doc_id']}", 'finality': texts[o['verdict_id']]})
        else:
            row['note'] = 'no ruling on the appeal among the later decisions in the register export' if extracts[o['verdict_id']]['decisions'] else 'no later decision in the register export'
        out.append(row)
    OUTCOMES.write_text(json.dumps({
        'status': 'appeal outcomes of convictions that were not final, read from the operative part of the later decisions '
                  '(register export, texts from od.reyestr.court.gov.ua) by a model review following fixed rules; ' + args.checked,
        'generated': sw.now(), 'rules': 'tools/recheck-ukraine-finality.py; appellate rulings enter into force when pronounced (CPC art. 532)',
        'counts': {k: sum(r['status'] == k for r in out) for k in ('final', 'not final', 'unclear')},
        'verdicts': out}, ensure_ascii=False, indent=1) + '\n')
    for folder in (ROOT / 'research/labels', UNREDACTED):
        for name in LABEL_FILES:
            path = folder / name
            if not path.exists():
                continue
            data, n = json.loads(path.read_text()), 0
            for v in data['verdicts']:
                text = texts.get(str(v.get('reyestr_id')))
                if text and v['verification'].get('finality') != text:
                    v['verification']['finality'] = text
                    n += 1
            path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n')
            print(f'{path}: {n} verdict records updated')
    print(json.dumps(json.loads(OUTCOMES.read_text())['counts']))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('cmd', choices=('pages', 'appeals', 'apply'))
    p.add_argument('--reviewed', default=str(WORK / 'out-1.jsonl'), help='apply: reviewed outcomes, JSON Lines')
    p.add_argument('--checked', default='not checked by hand', help='apply: how the review was checked, for the status line')
    p.add_argument('--cohort', action='append', help='cohort .json.gz (default: conviction cohort with linked tenders)')
    p.add_argument('--day', default=date.today().isoformat(), help='names the Review-page cache directory')
    p.add_argument('--budget', type=int, default=300, help='new requests allowed in this run')
    p.add_argument('--interval', type=float)
    args = p.parse_args(argv)
    ids = pending_verdicts([Path(c) for c in args.cohort] if args.cohort else COHORTS)
    if args.cmd == 'apply':
        apply(args, ids)
    elif args.cmd == 'pages':
        args.interval = args.interval or sw.PAGE_INTERVAL
        pages(args, ids)
    else:
        args.interval = args.interval or sw.TEXT_INTERVAL
        appeals(args, ids)


if __name__ == '__main__':
    main()
