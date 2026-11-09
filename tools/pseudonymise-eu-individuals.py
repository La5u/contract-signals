#!/usr/bin/env python3
"""Replace individual suppliers (sole traders, natural persons) in everything published with a keyed pseudonym.

Owner 2026-11-09 (publisher based in France, so GDPR covers every country). The same person always gets the same
pseudonym, "individual #<12 hex>", so their contracts still link; name and identifier leave the published files. The
pseudonym is an HMAC-SHA256 of country + identifier under a secret key outside the repository
(~/.config/contract-signals/pseudonym.key). It replaces the older unsalted "masked-" SHA-256 of national IDs, which
could be reversed by enumerating ID numbers. A pseudonym is still personal data.

  find   add to the private list (~/.cache/contract-signals/eu-individuals.json) from the published rows. France: SIREN
         with legal category 1000 in the Sirene stock file (only with the SIRENE argument); Czechia: IČO with a
         natural-person form in ARES; Portugal: NIF 1, 2, 3 or 45; Ukraine, Colombia, Paraguay, Chile: identifiers of
         persons (already masked by tools/personal_ids.py); Paraguay's sanction list: Persona Física; Ukrainian verdict
         links: 10-digit taxpayer codes. Entries are merged, because a pseudonymised row no longer shows its name.
           ~/.cache/contract-signals/venv/bin/python3 -I tools/pseudonymise-eu-individuals.py find [SIRENE.parquet]
  apply  rewrite the published JSON under data/ and research/labels/, and write data/private/individuals.json
         (git-ignored, never deployed), which the explorer reads only on localhost to show the real names. Run after
         every rebuild of these datasets:   python3 -I tools/pseudonymise-eu-individuals.py apply

Not covered: French rows without a SIREN, Romanian TED rows, UK rows (their identifiers do not show who is a person).
"""
import collections
import gzip
import hashlib
import hmac
import json
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from personal_ids import mask  # noqa: E402

CACHE = Path.home() / '.cache/contract-signals'
LIST = CACHE / 'eu-individuals.json'
ARES = CACHE / 'ares/forms.json'
KEY = Path.home() / '.config/contract-signals/pseudonym.key'
PRIVATE = ROOT / 'data/private/individuals.json'
SOURCES = [('data/contracts.json', 'FR'), ('data/decp-history.json', 'FR'), ('data/decp-cities.json', 'FR'),
           ('data/tours-notices.json', 'FR'), ('data/ted-czechia.json', 'CZ'), ('data/ted-portugal.json', 'PT'),
           ('data/prozorro.json', 'UA'), ('data/prozorro-slice-2026-06-08/contracts.json', 'UA'),
           ('data/prozorro-expansion/contracts.json', 'UA'), ('data/colombia-secop2.json', 'CO'),
           ('data/paraguay-dncp.json', 'PY'), ('data/paraguay-dncp-3buyers.json', 'PY'), ('data/chile-mp.json', 'CL')]
CZ_PERSON = {'101', '102', '105', '107', '108'}  # ARES pravniForma: natural persons in business
MASKED = re.compile(r'masked-[0-9a-f]{16}')
PSEUDO = re.compile(r'^individual #[0-9a-f]{12}$')
# Identifier types whose rows keep their type (other code reads it, e.g. Colombian person documents).
KEEP_TYPE = {'Cédula de Ciudadanía', 'Cédula de Extranjería', 'RNOKPP', 'RUC', 'CL-RUT'}


def rows(path):
    d = json.loads((ROOT / path).read_text(encoding='utf-8'))
    return d if isinstance(d, list) else next((v for v in d.values() if isinstance(v, list)), [])


def ident(i):
    return re.sub(r'\s', '', i if isinstance(i, str) else str(i.get('id') or i.get('value') or ''))


def digits(v):
    return re.sub(r'\D', '', v)


def ares_forms(icos):
    forms = json.loads(ARES.read_text()) if ARES.exists() else {}
    for ico in sorted(set(icos) - set(forms)):
        url = f'https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}'
        try:
            req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'contract-signals'})
            forms[ico] = json.load(urllib.request.urlopen(req, timeout=30)).get('pravniForma')
        except urllib.error.HTTPError as e:
            forms[ico] = f'http{e.code}'
        except OSError:
            continue  # retried next run
        time.sleep(0.25)
    ARES.parent.mkdir(parents=True, exist_ok=True)
    ARES.write_text(json.dumps(forms))
    return forms


def french_sole_traders(data, sirene):
    if not sirene:
        return set()
    import pyarrow.parquet as pq
    fr = [x for p, cc in SOURCES if cc == 'FR' for x in data[p]]
    sirens = {digits(ident(i))[:9] for x in fr for i in x.get('supplierIds') or [] if len(digits(ident(i))) in (9, 14)}
    sirens |= {str(q['siren']) for x in fr for q in x.get('supplierProfiles') or [] if q.get('siren')}
    t = pq.read_table(sirene, columns=['siren', 'categorieJuridiqueUniteLegale'], filters=[('siren', 'in', sorted(sirens))])
    return {s for s, c in zip(t['siren'].to_pylist(), t['categorieJuridiqueUniteLegale'].to_pylist()) if str(c) == '1000'}


def person_key(cc, value, ei, cz, kind):
    d = digits(value)
    if cc == 'FR':
        return 'FR' + d[:9] if len(d) in (9, 14) and d[:9] in ei else None
    if cc == 'CZ':
        return 'CZ' + d.zfill(8) if d.zfill(8) in cz else None
    if cc == 'PT':
        return 'PT' + d if re.fullmatch(r'[123]\d{8}|45\d{7}', d) else None
    return cc + value if MASKED.fullmatch(value) else None


def find(sirene):
    data = {path: rows(path) for path, _ in SOURCES}
    ei = french_sole_traders(data, sirene)
    icos = {digits(ident(i)).zfill(8) for x in data['data/ted-czechia.json'] for i in x.get('supplierIds') or []
            if re.fullmatch(r'\d{6,8}', digits(ident(i)))}
    cz = {k for k, v in ares_forms(icos).items() if v in CZ_PERSON}
    old = json.loads(LIST.read_text(encoding='utf-8')) if LIST.exists() else {}
    people = collections.defaultdict(lambda: {'ids': set(), 'names': set()})
    for k, v in old.items():
        people[k]['ids'].update(v['ids'])
        people[k]['names'].update(v['names'])
    for path, cc in SOURCES:
        for x in data[path]:
            ids = x.get('supplierIds') or []
            parts = (x.get('supplier') or '').split(' / ')
            for q in x.get('supplierProfiles') or []:
                if str(q.get('siren')) in ei:
                    people['FR' + str(q['siren'])]['names'].add(q.get('name') or '')
            for n, i in enumerate(ids):
                v = ident(i)
                key = person_key(cc, v, ei, cz, i.get('identifierType') if isinstance(i, dict) else None)
                if not key:
                    continue
                people[key]['ids'].update({v} | ({digits(v)} if cc in ('FR', 'CZ', 'PT') else set()))
                if len(parts) == len(ids):  # joined names follow the identifier order
                    people[key]['names'].add(parts[n])
    for s in json.loads((ROOT / 'data/dncp-sanctions.json').read_text(encoding='utf-8'))['suppliers']:
        if 'Física' in str(s.get('entityType')) and MASKED.fullmatch(str(s.get('id'))):
            people['PY' + s['id']]['ids'].add(s['id'])
    # French rows whose identifier cannot be looked up in Sirene, but whose holder is named as a person.
    person = re.compile(r"(?i)\b(monsieur|madame|mme|entreprise individuelle|micro.?entrepr|auto.?entrepr)\b|^M\. ")
    for path, cc in SOURCES:
        if cc == 'FR':
            for x in data[path]:
                s = (x.get('supplier') or '').strip()
                if s and 'individual #' not in s and person.search(s):
                    people['FN' + re.sub(r'\W+', ' ', s).upper()]['names'].add(s)
    links = json.loads((ROOT / 'research/labels/ukraine-verdict-link-matches.json').read_text(encoding='utf-8'))
    for r in next(v for v in links.values() if isinstance(v, list)):
        code = str(r.get('supplier_code') or '')
        if re.fullmatch(r'\d{10}', code):
            m = mask('RNOKPP', code)
            people['UA' + m]['ids'].update({m, code})
            people['UA' + m]['names'].add(r.get('supplier_name') or '')
    out = {k: {**({'addresses': old[k]['addresses']} if old.get(k, {}).get('addresses') else {}), 'ids': sorted(v['ids']), 'names': sorted({n.strip() for n in v['names'] if len(n.strip()) >= 2 and not n.startswith('individual #')})}
           for k, v in sorted(people.items())}
    LIST.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(out)} individuals {dict(collections.Counter(k[:2] for k in out))}; '
          f'{sum(not v["names"] for v in out.values())} without a name; -> {LIST}')


def details(etablissements=None):
    """Add addresses and contact points from the private raw snapshots (OCDS-style parties) to the private list."""
    people = json.loads(LIST.read_text(encoding='utf-8'))
    found = collections.defaultdict(set)

    def text(a):
        return ', '.join(str(a[k]) for k in ('streetAddress', 'locality', 'region', 'postalCode', 'countryName') if a.get(k))

    def walk(v, cc):
        if isinstance(v, list):
            for x in v:
                walk(x, cc)
        elif isinstance(v, dict):
            i = v.get('identifier')
            if isinstance(i, dict) and i.get('id') is not None and isinstance(v.get('address'), dict):
                raw = str(i['id'])
                for key in ({cc + mask('RNOKPP', raw)} if cc == 'UA' else {cc + mask('RUC', raw), cc + mask('RUC', f'PY-RUC-{raw}')}):
                    if key in people:
                        found[key].add(text(v['address']))
                        c = v.get('contactPoint') or {}
                        found[key].update(str(c[k]) for k in ('email', 'telephone') if c.get(k))
            if cc == 'CO' and v.get('documento_proveedor'):
                key = cc + mask(v.get('tipodocproveedor') or 'Documento', str(v['documento_proveedor']).strip())
                if key in people and v.get('domicilio_representante_legal'):
                    found[key].add(str(v['domicilio_representante_legal']))
            for x in v.values():
                walk(x, cc)
    for pattern, cc in (('data/colombia-secop2/raw/page-*.json', 'CO'), ('data/prozorro/raw/records/*.json.gz', 'UA'), ('data/paraguay-dncp/raw/**/*.json*', 'PY'),
                        ('data/paraguay-dncp-3buyers/raw/**/*.json*', 'PY')):
        for p in ROOT.glob(pattern):
            b = p.read_bytes()
            b = gzip.decompress(b) if p.suffix == '.gz' else b
            try:
                walk(json.loads(b), cc)
            except ValueError:
                pass
    if etablissements:  # Sirene StockEtablissement parquet: French addresses (the venv with pyarrow is needed)
        import pyarrow.parquet as pq
        fields = ['siren', 'etatAdministratifEtablissement', 'numeroVoieEtablissement', 'typeVoieEtablissement',
                  'libelleVoieEtablissement', 'codePostalEtablissement', 'libelleCommuneEtablissement']
        for batch in pq.ParquetFile(etablissements).iter_batches(batch_size=50_000, columns=fields):
            for row in batch.to_pylist():
                key = 'FR' + str(row['siren'])
                if key in people:
                    parts = [row[c] for c in fields[2:] if row[c] and '[ND]' not in str(row[c])]
                    if parts:
                        found[key].add(' '.join(str(p) for p in parts) + (' (closed)' if row[fields[1]] == 'F' else ''))
    for k, v in found.items():
        people[k]['addresses'] = sorted(x for x in v if x)
    LIST.write_text(json.dumps(people, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'addresses or contacts for {len(found)} individuals')


def key():
    if not KEY.exists():
        KEY.parent.mkdir(parents=True, exist_ok=True)
        KEY.write_bytes(secrets.token_bytes(32))
        KEY.chmod(0o600)
    return KEY.read_bytes()


def codes(people, k):
    return {p: 'individual #' + hmac.new(k, p.encode(), hashlib.sha256).hexdigest()[:12] for p in people}


def transformer(people, k):
    """The function that pseudonymises any JSON value (also used by the rebuild tests)."""
    code = codes(people, k)
    by_name, masked, ids = {}, {}, {}
    for p, v in people.items():
        for n in v['names']:
            by_name[n] = code[p]
            by_name[n.upper()] = code[p]
        for i in v['ids']:
            (masked if MASKED.fullmatch(i) else ids)[i] = code[p]
        if p[:2] == 'FR':
            ids[p[2:]] = code[p]
    # Names are found through their first word: thousands of alternatives in one regular expression would be too slow.
    first = collections.defaultdict(list)
    for n in sorted(by_name, key=len, reverse=True):
        first[n.split()[0]].append(n)
    word = re.compile(r'\w+', re.UNICODE)
    id_re = re.compile(r'(?<![0-9A-Za-z])(?:' + '|'.join(sorted((re.escape(i) for i in ids), key=len, reverse=True)) +
                       r')(?:\d{5})?(?![0-9A-Za-z])') if ids else None

    def names(s):
        if s.strip() in by_name:
            return s.replace(s.strip(), by_name[s.strip()])  # surrounding spaces stay, as the importers keep them
        if ' / ' in s:  # joined supplier names: each part as a whole value
            return ' / '.join(names(p) for p in s.split(' / '))
        out, pos = [], 0
        for m in word.finditer(s):
            if m.start() < pos or m[0] not in first:
                continue
            for n in first[m[0]]:
                end = m.start() + len(n)
                # One or two words only as a whole value (above): inside longer text they
                # would hit other people and companies. Three words or more anywhere, on word boundaries.
                if len(n.split()) >= 3 and s.startswith(n, m.start()) and not (end < len(s) and s[end].isalnum()):
                    out += [s[pos:m.start()], by_name[n]]
                    pos = end
                    break
        return ''.join(out) + s[pos:] if out else s

    def fix(s):
        t = names(s)
        t = MASKED.sub(lambda m: masked.get(m[0], m[0]), t)
        return id_re.sub(lambda m: ids.get(m[0]) or ids[m[0][:-5]], t) if id_re else t

    def walk(v):
        if isinstance(v, str):
            return fix(v)
        if isinstance(v, list):
            return [walk(x) for x in v]
        if not isinstance(v, dict):
            return v
        d = {fix(a): walk(b) for a, b in v.items()}
        if PSEUDO.match(str(d.get('id'))) and 'identifierType' in d and d['identifierType'] not in KEEP_TYPE:
            d['identifierType'] = 'pseudonym'
        if isinstance(d.get('supplierProfiles'), list):
            d['supplierProfiles'] = [p for p in d['supplierProfiles'] if not PSEUDO.match(str(p.get('siren')))]
        if isinstance(d.get('identities'), list):
            d['identities'] = [p for p in d['identities'] if not PSEUDO.match(str(p.get('siren')))]
        return d
    return walk


def pseudonymise(value):
    """value with the listed individuals pseudonymised; unchanged where the private list or key is absent (CI)."""
    if not (LIST.exists() and KEY.exists()):
        return value
    return transformer(json.loads(LIST.read_text(encoding='utf-8')), KEY.read_bytes())(value)


def apply():
    people = json.loads(LIST.read_text(encoding='utf-8'))
    k = key()
    walk = transformer(people, k)
    files = subprocess.run(['git', 'ls-files', '-co', '--exclude-standard', 'data', 'research/labels'], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.split('\n')
    total = 0
    for f in (f for f in files if f.endswith('.json')):
        path = ROOT / f
        text = path.read_text(encoding='utf-8')
        data = json.loads(text)
        new = walk(data)
        if new == data:
            continue
        style = next(((i, a, sep) for i in (2, 1, None) for a in (False, True) for sep in (None, (',', ':'))
                      if json.dumps(data, indent=i, ensure_ascii=a, separators=sep) + '\n' == text), (1, False, None))
        path.write_text(json.dumps(new, indent=style[0], ensure_ascii=style[1], separators=style[2]) + '\n', encoding='utf-8')
        total += 1
        print(f'{f}: rewritten')
    PRIVATE.parent.mkdir(parents=True, exist_ok=True)
    code = codes(people, k)
    PRIVATE.write_text(json.dumps({code[p]: {'country': p[:2], 'names': v['names'], 'ids': v['ids'],
                                             'addresses': v.get('addresses', [])} for p, v in people.items()},
                                  ensure_ascii=False), encoding='utf-8')
    print(f'{total} files rewritten; {len(people)} individuals; private names -> {PRIVATE}')


if __name__ == '__main__':
    if sys.argv[1] == 'find':
        find(sys.argv[2] if len(sys.argv) > 2 else None)
    elif sys.argv[1] == 'details':
        details(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        apply()
