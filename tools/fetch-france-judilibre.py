#!/usr/bin/env python3
"""Research only: fetch French criminal rulings on public-procurement offences from Judilibre (Cour de cassation).

Judilibre (PISTE, open-data CGU V8) covers the Cour de cassation, the appeal courts and first-instance courts.
Each query in QUERIES is searched in every jurisdiction; every hit's full decision is saved to
~/.cache/contract-signals/france-judilibre/decisions/<id>.json and the hit list to hits.jsonl (query, jurisdiction).
Credentials: ~/.config/contract-signals/piste.json {"client_id", "client_secret"} (OAuth client credentials), never
in the repo. Resumable: saved decisions are not fetched again. Requests go through polite_http (1 s apart).
"""
import argparse
import json
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import polite_http  # noqa: E402

API = 'https://api.piste.gouv.fr/cassation/judilibre/v1.0/'
TOKEN_URL = 'https://oauth.piste.gouv.fr/api/oauth/token'
BASE = polite_http.CACHE / 'france-judilibre'
KEY = Path.home() / '.config/contract-signals/piste.json'
# (query, operator[, jurisdictions]): single offences exactly; broad offences only together with public contracts.
# The long phrase matches almost everything outside the Cour de cassation (645k/764k hits on 2026-10-28), and
# "L. 420-6 code de commerce" pulled thousands of unrelated articles, so it was dropped for the bid-rigging query.
QUERIES = [
    ('favoritisme', 'exact'),
    ("atteinte à la liberté d'accès et à l'égalité des candidats", 'exact', ['cc']),
    ("prise illégale d'intérêts marché public", 'and'),
    ('corruption marché public', 'and'),
    ("trafic d'influence marché public", 'and'),
    ('détournement de fonds publics marché public', 'and'),
    ('entente marché public soumission', 'and'),
    ('recel de favoritisme', 'exact'),
]
JURISDICTIONS = ['cc', 'ca', 'tj']
PAGE_SIZE = 50


class Judilibre:
    def __init__(self, log_path):
        self.client = polite_http.PoliteClient(log_path=log_path, obey_robots=False)  # an authenticated API, not a site
        self.key = json.loads(KEY.read_text())
        self.token, self.expires = None, 0

    def headers(self):
        if time.time() > self.expires - 60:
            body = urllib.parse.urlencode({'grant_type': 'client_credentials', 'scope': 'openid', **self.key}).encode()
            r = self.client.request('POST', TOKEN_URL, body=body,
                                    headers={'Content-Type': 'application/x-www-form-urlencoded'})
            if r.status != 200:
                sys.exit(f'token: HTTP {r.status}')
            t = r.json()
            self.token, self.expires = t['access_token'], time.time() + int(t.get('expires_in', 3600))
        return {'Authorization': 'Bearer ' + self.token, 'Accept': 'application/json'}

    def get(self, path, **params):
        r = self.client.get(API + path + '?' + urllib.parse.urlencode(params), headers=self.headers())
        if r.status != 200:
            raise RuntimeError(f'{path} {params}: HTTP {r.status} {r.body[:200]!r}')
        return r.json()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--out', type=Path, default=BASE)
    parser.add_argument('--max-pages', type=int, default=200, help='per query and jurisdiction (50 hits a page)')
    args = parser.parse_args()
    api = Judilibre(args.out / 'requests.jsonl')
    decisions = args.out / 'decisions'
    decisions.mkdir(parents=True, exist_ok=True)
    seen = {}
    for query, operator, *only in QUERIES:
        for jur in (only[0] if only else JURISDICTIONS):
            page, n = 0, 0
            while page < args.max_pages:
                res = api.get('search', query=query, operator=operator, jurisdiction=jur, page=page,
                              page_size=PAGE_SIZE, resolve_references='false')
                for hit in res.get('results', []):
                    seen.setdefault(hit['id'], []).append([query, jur])
                    n += 1
                if not res.get('next_page'):
                    break
                page += 1
            print(f'{query!r} {jur}: {n} hits (total {res.get("total")})', flush=True)
    with open(args.out / 'hits.jsonl', 'w') as f:
        for i, q in seen.items():
            f.write(json.dumps({'id': i, 'queries': q}, ensure_ascii=False) + '\n')
    todo = [i for i in seen if not (decisions / f'{i}.json').exists()]
    print(f'{len(seen)} distinct decisions, {len(todo)} to fetch', flush=True)
    for k, i in enumerate(todo, 1):
        try:
            d = api.get('decision', id=i, resolve_references='false')
        except RuntimeError as e:
            print(f'{i}: {e}', flush=True)
            continue
        (decisions / f'{i}.json').write_text(json.dumps(d, ensure_ascii=False))
        if k % 100 == 0:
            print(f'{k}/{len(todo)}', flush=True)
    print('done', flush=True)


if __name__ == '__main__':
    main()
