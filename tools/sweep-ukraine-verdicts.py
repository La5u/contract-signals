#!/usr/bin/env python3
"""Find Ukrainian criminal verdicts that quote a Prozorro tender ID, from the court register's bulk export.

Research only. Replaces web-search discovery (research/labels/ukraine-verdict-candidates.json) with a
sweep of the register's yearly metadata exports (data.gov.ua, CC BY), so every verdict in the chosen
article categories is read, not just those a search engine shows.

Steps, each resumable:
  select  read edrsr_data_<year>.zip exports already on disk; keep criminal decisions in the chosen
          categories (verdicts to read, plus later decisions in the same case for finality).
  fetch   download verdict texts from doc_url, one at a time (serial, spaced, capped, stops on 403).
  scan    find tender IDs in the cached texts and write the candidate list.
  finality  read "Дата набрання законної сили" from the register page for each candidate, one at a time.
  merge   combine a reviewer's JSON Lines (one row per verdict and tender: outcome, tender_role,
          official_involved, stage, quote) with finality into the input of build-ukraine-verdict-cohort.py.

Outputs: research/labels/ukraine-verdict-sweep.json (candidates, not labels: official involvement
and the role of the tender in the scheme still need review) and, after merge,
research/labels/ukraine-verdict-sweep-reviewed.json (proposed labels).
"""
import argparse
import csv
import gzip
import html
import io
import json
import re
import sys
import urllib.error
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import importlib.util
spec = importlib.util.spec_from_file_location('verdict_sweep_cohort', ROOT / 'tools/build-ukraine-label-cohort.py')
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)

BASE = Path.home() / '.cache/contract-signals/court-register'
ZIPS = BASE / 'zips'
SELECTED = BASE / 'selected.jsonl.gz'
TEXTS = BASE / 'texts'
PAGES = BASE / 'review-pages'
OUT = ROOT / 'research/labels/ukraine-verdict-sweep.json'
REVIEWED = ROOT / 'research/labels/ukraine-verdict-sweep-reviewed.json'
KNOWN = ROOT / 'research/labels/ukraine-verdict-candidates.json'
USER_AGENT = 'contract-signals-label-research/1.0 (public open-data research)'
CRIMINAL, VERDICT = '2', '1'
FIRST_YEAR = 2017                      # Prozorro tender IDs start in 2016; verdicts quoting them follow
TEXT_CAP, PAGE_CAP = 120_000, 2_000
TEXT_INTERVAL, PAGE_INTERVAL = 1.0, 6.0

# Category names (both taxonomies share them), with the Criminal Code article and a fetch priority.
# Bribe offers (369) are mostly drivers and police; fraud (190) is mostly private victims. Both are read later.
CATEGORIES = {
    'Привласнення, розтрата майна або заволодіння ним шляхом зловживання службовим становищем': ('191', 1),
    'Зловживання владою або службовим становищем': ('364', 1),
    'Зловживання повноваженнями службовою особою юридичної особи приватного права незалежно від організаційно-правової форми': ('364-1', 1),
    'Зловживання повноваженнями особами, які надають публічні послуги': ('365-2', 1),
    'Службове підроблення': ('366', 1),
    'Службова недбалість': ('367', 1),
    'Прийняття пропозиції, обіцянки або одержання неправомірної вигоди службовою особою': ('368', 1),
    'Пропозиція, обіцянка або надання неправомірної вигоди службовій особі': ('369', 2),
    'Пропозиція або надання неправомірної вигоди': ('369', 2),
    'Зловживання впливом': ('369-2', 1),
    'Зловживання впливом (стара категорія)': ('369-2', 1),
    'Підкуп працівника підприємства, установи чи організації': ('354', 1),
    'Шахрайство': ('190', 3),
}

# Tender ID as printed: Latin or Cyrillic look-alikes, stray spaces, Cyrillic suffix letters.
LOOKALIKE = str.maketrans('АаВЕеКкМНОоРрСсТХхУуІіЬь', 'AaBEeKkMHOoPpCcTXxYyIibb')
# The prefix also comes glued to the previous word ("закупівліUA-…"), followed by a space instead of a hyphen,
# or mangled by text recognition ("ІІА-", "иА-", "ПА-"); Prozorro.Sale IDs (UA-PS-…) have letters before the date.
TENDER_RE = re.compile(r'(?<![A-Za-z\d])(?:[UuУуИиЦцПпЛл]|[ІI]{1,2})\s?[AaАа]\s?(?:[-–—]\s?|\s)?(20[12]\d)\s?[-–—]\s?(\d{2})\s?[-–—]\s?(\d{2})\s?[-–—]\s?(\d{6})'
                       r'(?:\s?[-–—]\s?([a-zA-Zа-яА-ЯіІ])(?![a-zA-Zа-яА-ЯіІ]))?')
# A вирок can acquit. Pleas and the presumption of innocence repeat the same words, so only the
# operative part (after the last УХВАЛИВ / ПОСТАНОВИВ / ЗАСУДИВ heading) is read.
OPERATIVE_RE = re.compile(r'(?:У\s?Х\s?В\s?А\s?Л\s?И\s?В|П\s?О\s?С\s?Т\s?А\s?Н\s?О\s?В\s?И\s?В|З\s?А\s?С\s?У\s?Д\s?И\s?В)\s*:', re.I)
CONVICTED_RE = re.compile(r'(?<!не)винуват(?:им|ою|ими)\b|засудити|призначити\s+(?:\S+\s+){0,4}покарання', re.I)
ACQUITTED_RE = re.compile(r'невинуват(?:им|ою|ими)\b|виправдати\b|виправдан(?:им|ою|ими)\b', re.I)
PROCUREMENT_RE = re.compile(r'prozorro|прозорро|закупів|тендер', re.I)
FORCE_RE = re.compile(r'Дата набрання законної сили:(?:&nbsp;|\s)*<b>\s*(\d{2})\.(\d{2})\.(\d{4})')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def read_csv(z, name):
    with z.open(name) as f:
        yield from csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig', newline=''), delimiter='\t', quotechar='"')


def member(z, name):
    return next(i.filename for i in z.infolist() if i.filename.split('/')[-1] == name)


def complete_years():
    return sorted(int(p.name.split('_')[1]) for p in ZIPS.glob('done_*') if int(p.name.split('_')[1]) >= FIRST_YEAR)


def select(args):
    years = complete_years()
    if not years:
        raise SystemExit(f'no complete export in {ZIPS}; download first')
    rows, seen = [], set()
    stats = {}
    for year in years:
        z = zipfile.ZipFile(ZIPS / f'edrsr_data_{year}.zip')
        cats = {r['category_code']: CATEGORIES[r['name']] for r in read_csv(z, member(z, 'cause_categories.csv')) if r['name'] in CATEGORIES}
        courts = {r['court_code']: (r['name'], r['instance_code']) for r in read_csv(z, member(z, 'courts.csv'))}
        kept = Counter()
        for r in read_csv(z, member(z, 'documents.csv')):
            if r['justice_kind'] != CRIMINAL or r['category_code'] not in cats or r['doc_id'] in seen:
                continue
            seen.add(r['doc_id'])
            article, priority = cats[r['category_code']]
            court, instance = courts.get(r['court_code'], ('', ''))
            rows.append({'doc_id': r['doc_id'], 'export_year': year, 'cause_num': r['cause_num'], 'court': court,
                         'instance': instance, 'judgment_code': r['judgment_code'], 'article': article, 'priority': priority,
                         'adjudication_date': (r['adjudication_date'] or '')[:10], 'doc_url': r['doc_url'],
                         'status': r['status'], 'date_publ': (r['date_publ'] or '')[:10]})
            kept[(article, r['judgment_code'] == VERDICT)] += 1
        stats[year] = {f'{a} {"verdicts" if v else "other decisions"}': n for (a, v), n in sorted(kept.items())}
        print(year, sum(kept.values()), 'kept', flush=True)
    with gzip.open(SELECTED, 'wt', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    (BASE / 'selected-stats.json').write_text(json.dumps({'years': years, 'built': now(), 'counts': stats}, ensure_ascii=False, indent=1))
    print(f'{len(rows)} decisions from {years} -> {SELECTED}')


def load_selected(only_verdicts=False):
    with gzip.open(SELECTED, 'rt', encoding='utf-8') as f:
        rows = (json.loads(line) for line in f)
        return [r for r in rows if not only_verdicts or r['judgment_code'] == VERDICT]


def verdicts(rows):
    out = [r for r in rows if r['judgment_code'] == VERDICT and r['status'] == '1' and r['doc_url']]
    return sorted(out, key=lambda r: (r['priority'], r['adjudication_date']))


def opener(accept):
    def open_url(url):
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': accept})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, b'', dict(e.headers or {})
    return open_url


def fetch(args):
    todo = [{k: r[k] for k in ('priority', 'adjudication_date', 'doc_url')} for r in verdicts(load_selected(only_verdicts=True))]
    if args.priority:
        todo = [r for r in todo if r['priority'] <= args.priority]
    f = bc.Fetcher(TEXTS, budget=args.budget, network=True, min_interval=args.interval, opener=opener('text/html'), prior=0)
    missing = [r for r in todo if not f.cached(r['doc_url'])]
    print(f'{len(todo)} verdicts, {len(missing)} not cached; cap {args.budget}, used {f.requests}', flush=True)
    done = 0
    try:
        for r in missing:
            f.fetch(r['doc_url'])
            f.responses.clear()  # the shared Fetcher keeps every body otherwise
            done += 1
            if done % 200 == 0:
                print(f'{done}/{len(missing)} fetched, requests {f.requests}, throttled {f.state["throttled"]}', flush=True)
    except (bc.BudgetExceeded, bc.Blocked, bc.Throttled) as e:
        print(f'stopped: {e}', flush=True)
    print(f'fetched {done}; requests {f.requests}, throttled {f.state["throttled"]}')


RTF_TOKEN = re.compile(rb"\\'([0-9a-fA-F]{2})|\\u(-?\d+)\??|\\([a-zA-Z]+)(-?\d+)? ?|\\([^a-zA-Z])|([{}])|([^\\{}]+)")
RTF_SKIP = {b'fonttbl', b'colortbl', b'stylesheet', b'info', b'pict', b'header', b'footer', b'*'}
RTF_BREAK = {b'par', b'line', b'row', b'cell', b'tab', b'page', b'sect'}


def rtf_text(body):
    """Plain text of a register RTF judgment (cp1251 escapes, \\uN code points, skipped destinations)."""
    out, raw, depth, skip = [], bytearray(), 0, []

    def flush():
        if raw:
            out.append(raw.decode('cp1251', 'replace'))
            raw.clear()
    for hexbyte, uni, word, num, sym, brace, chars in RTF_TOKEN.findall(body):
        if brace == b'{':
            depth += 1
        elif brace == b'}':
            if skip and skip[-1] == depth:
                skip.pop()
            depth -= 1
        elif skip:
            continue
        elif word or sym:
            if word in RTF_SKIP or sym == b'*':
                skip.append(depth)
            elif word in RTF_BREAK:
                flush(); out.append('\n')
        elif hexbyte:
            raw.append(int(hexbyte, 16))
        elif uni:
            flush(); out.append(chr(int(uni) % 65536))
        elif chars:
            raw.extend(chars.replace(b'\r', b'').replace(b'\n', b''))
    flush()
    return ''.join(out)


def plain(body):
    if body.lstrip().startswith(b'{\\rtf'):
        text = rtf_text(body)
    else:
        text = re.sub(r'(?is)<(script|style).*?</\1>', ' ', body.decode('utf-8', 'replace'))
        text = html.unescape(re.sub(r'<[^>]+>', ' ', text))
    return re.sub(r'[ \t\xa0]+', ' ', text)


def decode(body):
    head = body[:2000].decode('ascii', 'ignore').lower()
    charset = re.search(r'charset=["\']?([\w-]+)', head)
    for enc in ([charset.group(1)] if charset else []) + ['utf-8', 'cp1251']:
        try:
            return body.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode('utf-8', 'replace')


def tender_ids(text):
    found = {}
    for m in TENDER_RE.finditer(text):
        y, mo, d, n, suffix = m.groups()
        tid = f'UA-{y}-{mo}-{d}-{n}' + (f'-{suffix.translate(LOOKALIKE).lower()}' if suffix else '')
        if not (1 <= int(mo) <= 12 and 1 <= int(d) <= 31):
            continue
        a, b = max(0, m.start() - 300), min(len(text), m.end() + 200)
        found.setdefault(tid, {'as_printed': m.group(0), 'context': text[a:b].strip()})
    # An ID printed once without its suffix and once with it is one tender.
    return {t: v for t, v in found.items() if not any(o != t and o.startswith(t + '-') for o in found)}


def outcome(text):
    heads = list(OPERATIVE_RE.finditer(text))
    if not heads:
        return 'unclear'
    part = text[heads[-1].end():]
    convicted, acquitted = bool(CONVICTED_RE.search(part)), bool(ACQUITTED_RE.search(part))
    return {(True, False): 'conviction', (False, True): 'acquittal', (True, True): 'mixed'}.get((convicted, acquitted), 'unclear')


def appeals(rows):
    """Later decisions in the same case at a higher instance, from the exports (finality evidence)."""
    by_case = defaultdict(list)
    for r in rows:
        if r['instance'] in ('1', '2'):
            by_case[r['cause_num']].append({k: r[k] for k in ('doc_id', 'court', 'instance', 'judgment_code', 'adjudication_date')})
    return by_case


def stream_selected():
    with gzip.open(SELECTED, 'rt', encoding='utf-8') as f:
        yield from (json.loads(line) for line in f)


def scan(args):
    higher = appeals(stream_selected())
    rows = load_selected(only_verdicts=True)
    f = bc.Fetcher(TEXTS, network=False, prior=0)
    known = {v['reyestr_id']: v for v in json.loads(KNOWN.read_text())['verdicts']} if KNOWN.exists() else {}
    pages = json.loads((BASE / 'finality.json').read_text()) if (BASE / 'finality.json').exists() else {}
    read, cands = Counter(), []
    for r in verdicts(rows):
        hit = f.fetch(r['doc_url'])
        f.responses.clear()
        if hit is None:
            continue
        read[r['article']] += 1
        if hit['body'] is None:
            continue
        text = plain(hit['body'])
        ids = tender_ids(text)
        if not ids:
            continue
        cands.append({'doc_id': r['doc_id'], 'reyestr_url': f'https://reyestr.court.gov.ua/Review/{r["doc_id"]}',
                      'case_number': r['cause_num'], 'court': r['court'], 'instance': r['instance'],
                      'category_article': r['article'], 'verdict_date': r['adjudication_date'],
                      'tender_ids': ids, 'mentions_procurement': bool(PROCUREMENT_RE.search(text)),
                      'outcome': outcome(text),
                      'later_higher_court_decisions': [d for d in higher.get(r['cause_num'], []) if d['adjudication_date'] >= r['adjudication_date'] and d['doc_id'] != r['doc_id']],
                      'entry_into_force': pages.get(r['doc_id']),
                      'in_web_search_candidates': r['doc_id'] in known})
    total = {a: n for a, n in sorted(read.items())}
    selected = Counter(r['article'] for r in verdicts(rows))
    recall = [k for k in known if k not in {c['doc_id'] for c in cands}]
    out = {
        'status': 'candidates from a register sweep; not labels. Official involvement, the tender\'s role and finality need review.',
        'generated': now(),
        'source': 'Єдиний державний реєстр судових рішень, yearly exports on data.gov.ua (CC BY); texts from each doc_url',
        'export_years': json.loads((BASE / 'selected-stats.json').read_text())['years'],
        'verdicts_selected_by_article': dict(sorted(selected.items())),
        'verdicts_read_by_article': total,
        'candidates': len(cands),
        'distinct_tenders': len({t for c in cands for t in c['tender_ids']}),
        'web_search_candidates_not_found': recall,
        'verdicts': sorted(cands, key=lambda c: c['verdict_date']),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'verdicts'}, ensure_ascii=False, indent=1))


def page_state(hit):
    """Entry-into-force date (YYYY-MM-DD) from a Review page, 'no date shown' when the page has the field
    but no date, else 'page unreadable'. A captcha page stops the run: no bypass."""
    body = decode(hit['body']) if hit and hit['body'] else ''
    if 'modalcaptcha' in body:
        raise bc.Blocked(f"register answered with a captcha for {hit['url']}: stopping, no bypass")
    m = FORCE_RE.search(body)
    if m:
        return f'{m.group(3)}-{m.group(2)}-{m.group(1)}'
    return 'no date shown' if 'Дата набрання законної сили' in body else 'page unreadable'


def finality(args):
    data = json.loads(OUT.read_text())
    path = BASE / 'finality.json'
    pages = json.loads(path.read_text()) if path.exists() else {}
    f = bc.Fetcher(PAGES, budget=args.budget, network=True, min_interval=args.interval, opener=opener('text/html'), prior=0)
    try:
        for c in data['verdicts']:
            if c['doc_id'] in pages:
                continue
            hit = f.fetch(c['reyestr_url'])
            pages[c['doc_id']] = page_state(hit)
            path.write_text(json.dumps(pages, indent=1))
    except (bc.BudgetExceeded, bc.Blocked, bc.Throttled) as e:
        print(f'stopped: {e}')
    print(Counter(v if v in ('no date shown', 'page unreadable') else 'date' for v in pages.values()))


CONVICTED = {'conviction', 'conviction (plea agreement)', 'mixed'}


def proposed_label(row):
    if row.get('outcome') not in CONVICTED:
        return f"exclude: outcome {row.get('outcome')}"
    if row.get('tender_role') != 'scheme':
        return f"exclude: tender is {row.get('tender_role')}"
    return 'corruption (official involved)' if row.get('official_involved') == 'yes' else 'procurement fraud (no official established)'


def finality_state(verdict, force):
    """Text read by build-ukraine-verdict-cohort.py classify_finality."""
    if force and force[:2] == '20':
        return f'final {force} (register: date of entry into legal force)'
    if any(d['adjudication_date'] > verdict['verdict_date'] for d in verdict['later_higher_court_decisions']):
        return 'appeal: later higher-court decision in the export, result not read'
    return ''


def merge(args):
    sweep = {c['doc_id']: c for c in json.loads(OUT.read_text())['verdicts']}
    pages = json.loads((BASE / 'finality.json').read_text()) if (BASE / 'finality.json').exists() else {}
    rows = [json.loads(line) for path in sorted(Path(args.review).glob('out-*.jsonl'))
            for line in path.read_text().splitlines() if line.strip().startswith('{')]
    out, seen = [], set()
    for r in rows:
        c = sweep.get(str(r.get('doc_id')))
        if c is None or r.get('tender_id') not in c['tender_ids'] or (c['doc_id'], r['tender_id']) in seen:
            continue
        seen.add((c['doc_id'], r['tender_id']))
        force = pages.get(c['doc_id'])
        out.append({'reyestr_id': c['doc_id'], 'reyestr_url': c['reyestr_url'], 'case_number': c['case_number'], 'court': c['court'],
                    'verdict_date': c['verdict_date'], 'articles': [c['category_article']], 'outcome': r.get('outcome'),
                    'outcome_auto': c['outcome'], 'tender_id_as_printed': c['tender_ids'][r['tender_id']]['as_printed'],
                    'tender_id_normalised': r['tender_id'], 'tender_role': r.get('tender_role'),
                    'entry_into_force': force, 'later_higher_court_decisions': len(c['later_higher_court_decisions']),
                    'verification': {'finality': finality_state(c, force), 'official_involved': r.get('official_involved'),
                                     'official_reason': r.get('official_reason'), 'stage': r.get('stage'),
                                     'quote': r.get('quote'), 'notes': r.get('notes')},
                    'proposed_label': proposed_label(r)})
    expected = {(c['doc_id'], t) for c in sweep.values() if c['outcome'] != 'acquittal' for t in c['tender_ids']}
    missing = sorted(expected - seen)
    labels = Counter(v['proposed_label'] for v in out)
    REVIEWED.write_text(json.dumps({
        'status': 'proposed labels from a model review of local verdict texts; not owner-approved',
        'generated': now(), 'review': 'GPT-6.1-Sol over texts/<doc_id>.txt, prompt in the sweep work directory',
        'label_rule': 'conviction, plea-agreement conviction or mixed outcome, and the tender is part of the convicted scheme; '
                      'corruption if an official took part, otherwise procurement fraud',
        'counts': dict(labels), 'not_reviewed': [f'{d} {t}' for d, t in missing],
        'verdicts': sorted(out, key=lambda v: (v['verdict_date'], v['reyestr_id'], v['tender_id_normalised']))},
        ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({'rows': len(out), 'not_reviewed': len(missing), 'labels': labels}, ensure_ascii=False, indent=1))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('select')
    fp = sub.add_parser('fetch')
    fp.add_argument('--budget', type=int, default=TEXT_CAP)
    fp.add_argument('--interval', type=float, default=TEXT_INTERVAL)
    fp.add_argument('--priority', type=int, help='only categories up to this priority (1 = official crimes, 2 = also bribe offers, 3 = also fraud)')
    sub.add_parser('scan')
    fn = sub.add_parser('finality')
    fn.add_argument('--budget', type=int, default=PAGE_CAP)
    fn.add_argument('--interval', type=float, default=PAGE_INTERVAL)
    mp = sub.add_parser('merge')
    mp.add_argument('review', help='directory with the reviewer\'s out-*.jsonl files')
    args = p.parse_args(argv)
    {'select': select, 'fetch': fetch, 'scan': scan, 'finality': finality, 'merge': merge}[args.cmd](args)


if __name__ == '__main__':
    main()
