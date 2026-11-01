#!/usr/bin/env python3
"""Research only: keep the public-procurement rulings of the French administrative courts' open data.

Source: opendata.justice-administrative.fr (Conseil d'État, Licence Ouverte 2.0), one zip of XML rulings per court level
and month: DTA (tribunaux administratifs, from 2022-06), DCA (cours administratives d'appel, from 2022-03),
DCE (Conseil d'État, from 2021-06). Each zip (~66 MB for the tribunals) is read in memory through polite_http and
only rulings matching PROC are written to ~/.cache/contract-signals/france-admin/rulings/<level>/<file>.xml;
the zip is not kept. Resumable: months listed in done.txt are skipped (the current month is always refetched,
it grows twice a month).
"""
import argparse
import io
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import polite_http  # noqa: E402

SITE = 'https://opendata.justice-administrative.fr'
BASE = polite_http.CACHE / 'france-admin'
LEVELS = {'DTA': 'TA', 'DCA': 'CAA', 'DCE': 'CE'}
# A ruling on a public contract cites the procurement code, the pre-contractual or contractual summary procedure,
# the Tarn-et-Garonne action by third parties, or an ousted bidder. Loose on purpose: the reader decides relevance.
PROC = re.compile(r'code de la commande publique|code des march[ée]s publics|r[ée]f[ée]r[ée] (pr[ée])?contractuel'
                  r'|L\. ?551-(1|13)\b|Tarn-et-Garonne|candidat (irr[ée]guli[èe]rement )?[ée]vinc[ée]'
                  r'|march[ée]s? publics?|contrat de concession|d[ée]l[ée]gation de service public', re.I)


def months(level, client):
    page = client.get(f'{SITE}/{level}/').body.decode('utf-8', 'replace')
    return sorted(set(re.findall(rf'href="(/{level}/\d{{4}}/\d{{2}}/[A-Z]+_\d{{6}}\.zip)"', page)))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--levels', nargs='*', default=list(LEVELS))
    parser.add_argument('--out', type=Path, default=BASE)
    args = parser.parse_args()
    client = polite_http.PoliteClient(log_path=args.out / 'requests.jsonl', max_bytes=400 * 1024 * 1024, timeout=600)
    done_file = args.out / 'done.txt'
    done = set(done_file.read_text().split()) if done_file.exists() else set()
    current = date.today().strftime('%Y%m')
    for level in args.levels:
        for path in months(level, client):
            if path in done:
                continue
            r = client.get(SITE + path)
            if r.status != 200:
                print(f'{path}: HTTP {r.status}', flush=True)
                continue
            z = zipfile.ZipFile(io.BytesIO(r.body))
            out = args.out / 'rulings' / LEVELS[level]
            out.mkdir(parents=True, exist_ok=True)
            kept = 0
            for name in z.namelist():
                if not name.endswith('.xml'):
                    continue
                data = z.read(name)
                if PROC.search(data.decode('utf-8', 'replace')):
                    (out / Path(name).name).write_bytes(data)
                    kept += 1
            print(f'{path}: {len(z.namelist())} rulings, {kept} kept', flush=True)
            if not path.endswith(f'_{current}.zip'):
                with open(done_file, 'a') as f:
                    f.write(path + '\n')


if __name__ == '__main__':
    main()
