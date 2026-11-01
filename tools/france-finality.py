#!/usr/bin/env python3
"""Research only: find later French administrative rulings and assess finality."""
import argparse
import calendar
import datetime as dt
import html
import json
import os
import re
import sqlite3
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/france-admin'
CLASSES = {'A1', 'A2', 'A3', 'C'}
NUMBER = re.compile(r'(?<![A-Z0-9])(?:\d{2}[A-Z]{2}\d{4,6}|\d{6,8})(?![A-Z0-9])', re.I)


def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(s or '').lower()) if not unicodedata.combining(c))


def identity(rid):
    m = re.fullmatch(r'(?:D|OR)(TA|CA|CE)_(.+)_(\d{8})', rid)
    if not m:
        return None
    try:
        return {'level': {'TA': 'TA', 'CA': 'CAA', 'CE': 'CE'}[m[1]], 'number': m[2].upper(),
                'date': dt.datetime.strptime(m[3], '%Y%m%d').date()}
    except ValueError:
        return None


def six_months(date):
    month = date.month + 6
    year = date.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return dt.date(year, month, min(date.day, calendar.monthrange(year, month)[1]))


def load_readings(base):
    reads, terra = defaultdict(list), {}
    for path in sorted(base.glob('extract*/checked.jsonl')):
        with path.open() as f:
            for line in f:
                row = json.loads(line)
                r = row.get('result') or {}
                if row.get('id') and r:
                    reads[row['id']].append((path.parent.name, r))
                    if 'terra' in (row.get('model') or '').lower() or path.parent.name == 'extract-terra':
                        terra[row['id']] = r
    return reads, terra


def run(base, links_path, out):
    out.mkdir(parents=True, exist_ok=True)
    links = {}
    with links_path.open() as f:
        for line in f:
            row = json.loads(line)
            if row.get('class') in CLASSES:
                rid = row['ruling']
                if rid in links and links[rid]['class'] != row['class']:
                    raise ValueError(f'conflicting classes for {rid}')
                links[rid] = row
    reads, terra = load_readings(base)
    corpus, numbers = {}, defaultdict(set)
    for path in (base / 'rulings').glob('*/*.xml'):
        rid = path.stem
        meta = identity(rid)
        if meta:
            corpus[rid] = (meta, path)
            for n in NUMBER.findall(meta['number']):
                numbers[n.upper()].add(rid)
    if not corpus:
        raise ValueError('no rulings found')
    today = max(m['date'] for m, _ in corpus.values())
    missing = sorted(set(links) - corpus.keys())
    # Block on a distinctive buyer word, then require buyer, winner and contract words in the text.
    parties = defaultdict(list)
    for rid, rr in reads.items():
        if rid not in links:
            continue
        for _, r in rr:
            for c in r.get('contracts') or []:
                buyer, winner = (re.sub(r'[^a-z0-9]+', ' ', norm(c.get(k))).strip() for k in ('buyer', 'winner'))
                words = {w for w in re.findall(r'[a-z0-9]+', norm(c.get('object'))) if len(w) >= 6}
                buyer_words = [w for w in re.findall(r'[a-z0-9]+', buyer) if len(w) >= 6]
                if buyer_words and len(winner) >= 6 and len(words) >= 3:
                    parties[max(buyer_words, key=len)].append((rid, buyer, winner, words))
    # References are stored on disk; each XML tree is discarded before the next file.
    db = sqlite3.connect(out / 'references.sqlite')
    db.execute('drop table if exists refs')
    db.execute('create table refs (earlier text, later text, how text, unique(earlier, later, how))')
    malformed = []
    for later, (meta, path) in corpus.items():
        try:
            root = ET.parse(path).getroot()
            text = ' '.join(root.itertext()).upper()
        except ET.ParseError:
            malformed.append(later)
            text = html.unescape(re.sub(r'<[^>]*>', ' ', path.read_text(encoding='utf-8-sig', errors='replace'))).upper()
        plain = re.sub(r'[^a-z0-9]+', ' ', norm(text))
        plain_words = set(plain.split())
        for token in plain_words & parties.keys():
            for earlier, buyer, winner, words in parties[token]:
                if earlier not in corpus or corpus[earlier][0]['date'] >= meta['date'] or corpus[earlier][0]['level'] == 'CE':
                    continue
                if buyer in plain and winner in plain and len(words & plain_words) >= 3:
                    db.execute('insert or ignore into refs values (?, ?, ?)', (earlier, later, 'same parties and contract words'))
        for n in set(NUMBER.findall(text)) & numbers.keys():
            for earlier in numbers[n]:
                em = corpus[earlier][0]
                if em['date'] < meta['date'] and em['level'] != 'CE':
                    db.execute('insert or ignore into refs values (?, ?, ?)', (earlier, later, 'case number cited'))
    # Structured lower-ruling citations can identify a judgment even without its number in the text.
    for later, rr in reads.items():
        if later not in corpus:
            continue
        for _, r in rr:
            for lower in (r.get('case') or {}).get('lower_rulings') or []:
                if not isinstance(lower, dict):
                    continue
                nums = NUMBER.findall(str(lower.get('case_no') or '').upper())
                for n in nums:
                    for earlier in numbers.get(n, ()):
                        em = corpus[earlier][0]
                        date = lower.get('date')
                        if em['date'] < corpus[later][0]['date'] and (not date or str(em['date']) == date):
                            db.execute('insert or ignore into refs values (?, ?, ?)', (earlier, later, 'reading: lower ruling'))
    db.commit()
    db.execute('create index refs_earlier on refs(earlier)')
    db.execute('create index refs_later on refs(later)')

    def later_class(rid):
        if rid in links:
            return links[rid]['class']
        if rid in terra:
            return terra[rid].get('outcome_class')
        classes = {r.get('outcome_class') for _, r in reads.get(rid, [])} - {None}
        return next(iter(classes)) if len(classes) == 1 else None

    unread, counts = set(), Counter()
    with (out / 'finality.jsonl').open('w') as f:
        for rid, link in sorted(links.items()):
            meta = corpus.get(rid, (identity(rid),))[0]
            if not meta:
                raise ValueError(f'unrecognised ruling id: {rid}')
            refs = db.execute('select later, group_concat(how, "; ") from refs where earlier = ? group by later', (rid,)).fetchall()
            refs.sort(key=lambda x: (corpus[x[0]][0]['date'], x[0]))
            details = [{'ruling': x, 'how': how, 'class': later_class(x)} for x, how in refs]
            unresolved = [d['ruling'] for d in details if d['class'] not in CLASSES]
            unread.update(x for x in unresolved if not reads.get(x))
            if rid not in corpus:
                status, weight, reason = 'pending', (0.91 if meta['level'] == 'TA' else 0.85), 'ruling XML missing from corpus'
            elif meta['level'] == 'CE':
                status, weight, reason = 'final', 1, 'Conseil d’État ruling'
            elif details and unresolved:
                status, weight, reason = 'pending', (0.91 if meta['level'] == 'TA' else 0.85), 'later ruling requires review: unread, disputed or class X'
            elif details:
                last = details[-1]
                same = (last['class'] == 'C') == (link['class'] == 'C')
                status, weight = ('upheld_by_later', 1) if same else ('overturned', 0)
                reason = f"later ruling {last['ruling']} class {last['class']}; compare findings and contract"
            elif meta['date'] <= today and six_months(meta['date']) <= today:
                status, weight, reason = 'final', 1, 'no later ruling found within corpus; at least six months elapsed'
            else:
                status, weight, reason = 'pending', (0.91 if meta['level'] == 'TA' else 0.85), 'less than six months of corpus follow-up'
            row = {'ruling': rid, 'class': link['class'], 'status': status, 'w': weight,
                   'later_rulings': details, 'reason': reason, 'today': str(today)}
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
            counts[status] += 1
    (out / 'malformed-xml.txt').write_text(''.join(x + '\n' for x in sorted(malformed)))
    (out / 'unread-appeals.txt').write_text(''.join(x + '\n' for x in sorted(unread)))
    with (out / 'damages-only.tsv').open('w') as f:
        f.write('ruling\tearlier_rulings\treason\n')
        for rid, r in sorted(terra.items()):
            reason = norm(r.get('relevant_reason'))
            if (r.get('outcome_class') != 'X' or not re.search(r'indemnis|prejudice|dommages', reason)
                    or not re.search(r'anterior|anterieur|precedent|prealable', reason)
                    or not re.search(r'irregul|regularite|legalite|passation|eviction', reason)):
                continue
            earlier = [x[0] for x in db.execute('select distinct earlier from refs where later = ? order by earlier', (rid,))]
            f.write(f"{rid}\t{','.join(earlier)}\t{str(r.get('relevant_reason') or '').replace(chr(9), ' ').replace(chr(10), ' ')}\n")
    db.close()
    print(json.dumps({'today': str(today), 'statuses': dict(counts), 'unread': len(unread), 'malformed_xml': len(malformed), 'missing_xml': missing}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, default=BASE)
    p.add_argument('--links', type=Path)
    p.add_argument('--out', type=Path, default=BASE / 'finality-2026-11-01')
    a = p.parse_args()
    run(a.base, a.links or a.base / 'links-2026-11-01/links.jsonl', a.out)


if __name__ == '__main__':
    main()
