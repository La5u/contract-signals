#!/usr/bin/env python3
"""Research only: commercial-court judgments on Antimonopoly Committee (AMCU) decisions that quote Prozorro tenders.

Bid-rigging decisions of the AMCU (anticompetitive concerted actions distorting tender results, Law on
Protection of Economic Competition art. 50 p. 4) are challenged in the commercial courts, whose judgments
quote the decision's operative part with the Prozorro tender IDs. The register's yearly exports (already
downloaded by tools/sweep-ukraine-verdicts.py) list those judgments by category.

  select   commercial cases in the competition categories, judgments on the merits (Рішення, Постанова), active
  fetch    their texts, serially and slowly, into a cache of their own
  scan     tender IDs, bid-rigging wording and the court's disposition -> research/labels/ukraine-amcu-court-cases.json
  labels   per case, the highest and latest judgment decides; bid-rigging tenders of decisions that stand become
           research labels in the verdict-cohort builder's input format -> research/labels/ukraine-amcu-candidates.json

A judgment is a lead, not a label: whether the AMCU found bid rigging in that tender, and whether the decision
stood, still needs a review of the text. Changes no score, weight or dataset.
"""
import argparse
import gzip
import importlib.util
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sweep_verdicts', ROOT / 'tools/sweep-ukraine-verdicts.py')
sw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sw)
BASE = sw.BASE / 'amcu'
SELECTED = BASE / 'selected.jsonl.gz'
TEXTS = BASE / 'texts'
OUT = ROOT / 'research/labels/ukraine-amcu-court-cases.json'
COMMERCIAL = '3'
MERITS = {'2': 'Постанова', '3': 'Рішення'}
CATEGORY_NAMES = {
    'Питання конкуренції', 'Інший акт, що видано Антимонопольним комітетом або його територіальним органом',
    'Антимонопольним комітетом або його територіальним органом', 'Застосування антимонопольного законодавства',
    'захисту економічної конкуренції', 'Антимонопольного комітету України та його територіальних відділень',
    'Антимонопольна діяльність', 'оскарження рішень Антимонопольного комітету або його територіальних органів',
    'Справи у спорах щодо застосування антимонопольного та конкурентного законодавства, з них',
    'щодо захисту економічної конкуренції, з них', 'Справи у спорах щодо застосування антимонопольного та конкурентного законодавства',
    'про захист економічної конкуренції'}
INTERVAL = 3.0                     # slower than the verdict fetch, which may run at the same time
BID_RIGGING_RE = re.compile(r'спотворення\s+результатів\s+(?:торгів|тендер)|пункт\w*\s+4\s+(?:частини\s+другої\s+)?статті\s+6', re.I)
ANNULLED_RE = re.compile(r'визнати\s+недійсним\w*\s+(?:та\s+скасувати\s+)?(?:пункт\w*\s+[\d,\s і]+\s+)?рішенн\w*', re.I)


def select(args):
    rows, seen = [], set()
    for year in sw.complete_years():
        z = zipfile.ZipFile(sw.ZIPS / f'edrsr_data_{year}.zip')
        cats = {r['category_code'] for r in sw.read_csv(z, sw.member(z, 'cause_categories.csv')) if r['name'].strip('"') in CATEGORY_NAMES}
        courts = {r['court_code']: (r['name'], r['instance_code']) for r in sw.read_csv(z, sw.member(z, 'courts.csv'))}
        kept = 0
        for r in sw.read_csv(z, sw.member(z, 'documents.csv')):
            if r['justice_kind'] != COMMERCIAL or r['category_code'] not in cats or r['judgment_code'] not in MERITS \
                    or r['status'] != '1' or not r['doc_url'] or r['doc_id'] in seen:
                continue
            seen.add(r['doc_id'])
            court, instance = courts.get(r['court_code'], ('', ''))
            rows.append({'doc_id': r['doc_id'], 'export_year': year, 'cause_num': r['cause_num'], 'court': court, 'instance': instance,
                         'form': MERITS[r['judgment_code']], 'adjudication_date': (r['adjudication_date'] or '')[:10], 'doc_url': r['doc_url']})
            kept += 1
        print(year, kept, 'kept', flush=True)
    BASE.mkdir(parents=True, exist_ok=True)
    with gzip.open(SELECTED, 'wt', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'{len(rows)} judgments -> {SELECTED}')


def load_selected():
    with gzip.open(SELECTED, 'rt', encoding='utf-8') as f:
        return [json.loads(line) for line in f]


def fetch(args):
    todo = sorted(load_selected(), key=lambda r: r['adjudication_date'], reverse=True)   # Prozorro IDs appear from about 2018
    f = sw.bc.Fetcher(TEXTS, budget=args.budget, network=True, min_interval=args.interval, opener=sw.opener('text/html'), prior=0)
    missing = [r for r in todo if not f.cached(r['doc_url'])]
    print(f'{len(todo)} judgments, {len(missing)} not cached; cap {args.budget}, used {f.requests}', flush=True)
    done = 0
    try:
        for r in missing:
            f.fetch(r['doc_url'])
            f.responses.clear()
            done += 1
            if done % 200 == 0:
                print(f'{done}/{len(missing)} fetched, requests {f.requests}, throttled {f.state["throttled"]}', flush=True)
    except (sw.bc.BudgetExceeded, sw.bc.Blocked, sw.bc.Throttled) as e:
        print(f'stopped: {e}', flush=True)
    print(f'fetched {done}; requests {f.requests}, throttled {f.state["throttled"]}')


# Commercial courts open the operative part with ВИРІШИВ (first instance) or ПОСТАНОВИВ (appeal, cassation);
# УХВАЛИВ also heads procedural rulings quoted earlier in the text, so the last heading wins.
OPERATIVE_RE = re.compile(r'(?:В\s?И\s?Р\s?І\s?Ш\s?И\s?В|П\s?О\s?С\s?Т\s?А\s?Н\s?О\s?В\s?И\s?В|У\s?Х\s?В\s?А\s?Л\s?И\s?В)\s*:', re.I)


def operative(text):
    parts = OPERATIVE_RE.split(text)
    return parts[-1] if len(parts) > 1 else ''


AMCU_RE = re.compile(r'антимонопольн', re.I)
APPEAL_RE = re.compile(r'(апеляційн\w*|касаційн\w*)\s+скарг\w*(?P<party>.{0,300}?)(?P<verb>залишити\s+без\s+задоволення|задовольнити(?:\s+частково)?)', re.I | re.S)
CLAIM_DISMISSED_RE = re.compile(r'(?:у|в)\s+задоволенні\s+(?:позову|позовних\s+вимог)[^.]{0,200}?відмовити', re.I)
CLAIM_GRANTED_RE = re.compile(r'позов\w*(?:\s+\S+){0,30}?\s+задовольнити', re.I)
COLLECT_RE = re.compile(r'стягнути', re.I)
# Wordings the first rules miss (long party descriptions, verb first, "скаргу X - без задоволення").
APPEAL_PLAIN_RE = re.compile(r'(?:апеляційн\w*|касаційн\w*)\s+скарг\w*(?P<party>.{0,400}?)[\s,–—-]*(?:залишити\s+)?без\s+задоволення', re.I | re.S)
REFUSED_RE = re.compile(r'(?:у|в)\s+задоволенні\s+(?:позову|позовних\s+вимог|позовної\s+заяви)(?P<a>.{0,900}?)\s+відмовити'
                        r'|відмовити\s+(?:повністю\s+)?(?:у|в)\s+задоволенні\s+(?:позову|позовних\s+вимог|позовної\s+заяви)(?P<b>[^\n]{0,400}?)(?:\.\s|$)'
                        r'|(?:у|в)\s+позові(?P<c>.{0,900}?)\s+відмовити', re.I | re.S)
GRANTED_LONG_RE = re.compile(r'позов\w*(?P<party>(?:\s+\S+){0,120}?)\s+задовольнити', re.I)
HEADER_PLAINTIFF_RE = re.compile(r'за\s+позовом(?P<x>.{0,400}?)\s+до\s+', re.I | re.S)


def plaintiff_is_amcu(text, party):
    """True/False when the claimant can be told (from the operative wording or the header), else None."""
    head = re.split(r'\s+до\s+', party or '', maxsplit=1)
    if party and len(head) == 2:
        return bool(AMCU_RE.search(head[0]))
    m = HEADER_PLAINTIFF_RE.search(text[:6000])
    return bool(AMCU_RE.search(m.group('x'))) if m else None


def disposition_more(text, form):
    """Second pass for judgments the first rules leave unclear."""
    op = ' '.join(operative(text).split())[:2500]
    if not op:
        return 'unclear'
    if form == 'Постанова':
        m = APPEAL_PLAIN_RE.search(op)
        if m:
            return 'annulled' if AMCU_RE.search(m.group('party')) else 'stands'
        return 'unclear'
    m = REFUSED_RE.search(op)
    if m and not ANNULLED_RE.search(op):
        party = m.group('a') or m.group('b') or m.group('c') or ''
        return {False: 'stands'}.get(plaintiff_is_amcu(text, party), 'unclear')
    m = GRANTED_LONG_RE.search(op)
    if m:
        amcu = plaintiff_is_amcu(text, m.group('party'))
        if amcu is False and ANNULLED_RE.search(op):
            return 'annulled'
        if amcu is True and COLLECT_RE.search(op):
            return 'stands'
    return 'unclear'




def disposition(text, form):
    """Does the AMCU decision stand after this judgment? From the operative part, by who brought the claim or appeal.

    Appeal/cassation: a company's appeal dismissed, or the AMCU's appeal granted -> stands; the reverse -> annulled.
    First instance: a company's claim dismissed, or an AMCU claim (fine or penalty collection) granted -> stands;
    a claim granted that annuls the decision -> annulled. Anything else is unclear.
    """
    op = ' '.join(operative(text).split())
    if not op:
        return 'unclear'
    m = APPEAL_RE.search(op[:1500])
    if form == 'Постанова' and m:
        amcu = bool(AMCU_RE.search(m.group('party')))
        dismissed = m.group('verb').lower().startswith('залишити')
        return 'stands' if dismissed != amcu else 'annulled'
    if CLAIM_DISMISSED_RE.search(op[:1500]) and not ANNULLED_RE.search(op[:1500]):
        return 'stands'
    if CLAIM_GRANTED_RE.search(op[:600]):
        if ANNULLED_RE.search(op):
            return 'annulled'
        if COLLECT_RE.search(op) and AMCU_RE.search(op):
            return 'stands'
    return disposition_more(text, form)


def scan(args):
    f = sw.bc.Fetcher(TEXTS, budget=0, network=False, prior=0)
    out, stats = [], Counter()
    for r in load_selected():
        resp = f.fetch(r['doc_url'])
        f.responses.clear()
        if not resp or resp['status'] != 200:
            stats['not fetched'] += 1
            continue
        text = sw.plain(resp['body'])
        ids = sw.tender_ids(text)
        stats['fetched'] += 1
        if not ids:
            continue
        stats['with tender IDs'] += 1
        rig = bool(BID_RIGGING_RE.search(text))
        stats['bid-rigging wording'] += rig
        out.append({**{k: r[k] for k in ('doc_id', 'cause_num', 'court', 'instance', 'form', 'adjudication_date')},
                    'reyestr_url': f"https://reyestr.court.gov.ua/Review/{r['doc_id']}", 'tender_ids': ids,
                    'bid_rigging_wording': rig, 'disposition_auto': disposition(text, r['form'])})
    OUT.write_text(json.dumps({'status': 'leads from an automatic scan; not labels', 'generated': sw.now(), 'counts': dict(stats),
                               'judgments': out}, ensure_ascii=False, indent=1) + '\n')
    tenders = {t for j in out if j['bid_rigging_wording'] for t in j['tender_ids']}
    print(json.dumps(dict(stats), ensure_ascii=False), f'distinct tenders in bid-rigging judgments: {len(tenders)}',
          dict(Counter(j['disposition_auto'] for j in out if j['bid_rigging_wording'])))


CANDIDATES_OUT = ROOT / 'research/labels/ukraine-amcu-candidates.json'
LABEL = 'bid rigging (AMCU decision upheld)'


def decisive(judgments):
    """Cassation (instance 1) over appeal (2) over first instance (3); the latest within an instance."""
    return min(judgments, key=lambda j: (j['instance'] or '9', [-int(x) for x in j['adjudication_date'].split('-')] if j['adjudication_date'] else [0]))


def finality_text(j):
    if j['instance'] == '1':
        return f"final {j['adjudication_date']} (cassation ruling)"
    if j['instance'] == '2':
        return f"final {j['adjudication_date']} (appeal ruling, in force when adopted; no later cassation in the exports)"
    return ''          # first instance: the builder's presumed rule (no appeal found, at least 3 months old)


def labels(args):
    scanned = json.loads(OUT.read_text())['judgments']
    by_case = {}
    for j in scanned:
        by_case.setdefault(j['cause_num'], []).append(j)
    # Later judgments of a case without tender IDs still decide it: take them from the selection.
    selected = {}
    for r in load_selected():
        if r['cause_num'] in by_case:
            selected.setdefault(r['cause_num'], []).append(r)
    out, stats = [], Counter()
    for case, js in sorted(by_case.items()):
        rigging = [j for j in js if j['bid_rigging_wording']]
        if not rigging:
            stats['no bid-rigging wording'] += 1
            continue
        known = {j['doc_id'] for j in js}
        later = [r for r in selected.get(case, []) if r['doc_id'] not in known]
        top = decisive(js + [{**r, 'disposition_auto': 'not scanned'} for r in later])
        state = top.get('disposition_auto')
        stats[f'case {state}'] += 1
        if state != 'stands':
            continue
        tenders = sorted({t for j in rigging for t in j['tender_ids']})
        for tid in tenders:
            out.append({'reyestr_id': top['doc_id'], 'case_number': case, 'court': top['court'], 'verdict_date': top['adjudication_date'],
                        'tender_id_normalised': tid, 'proposed_label': LABEL, 'source': 'commercial-court judgment on an AMCU decision',
                        'verification': {'finality': finality_text(top), 'stage': 'award (collusion)'}})
    CANDIDATES_OUT.write_text(json.dumps({'status': 'proposed research labels from an automatic scan; not owner-approved, not model-reviewed',
                                          'generated': sw.now(), 'label_rule': 'bid-rigging wording in a judgment quoting the tender, and the '
                                          'case\'s highest, latest judgment leaves the AMCU decision standing', 'counts': dict(stats),
                                          'verdicts': out}, ensure_ascii=False, indent=1) + '\n')
    print(dict(stats), f'{len(out)} tender labels, {len({v["tender_id_normalised"] for v in out})} distinct tenders')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('select')
    fp = sub.add_parser('fetch')
    fp.add_argument('--budget', type=int, default=20_000)
    fp.add_argument('--interval', type=float, default=INTERVAL)
    sub.add_parser('scan')
    sub.add_parser('labels')
    args = p.parse_args(argv)
    {'select': select, 'fetch': fetch, 'scan': scan, 'labels': labels}[args.cmd](args)


if __name__ == '__main__':
    main()
