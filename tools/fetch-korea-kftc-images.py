#!/usr/bin/env python3
"""Research only: download the table images of KFTC bid-rigging decisions from law.go.kr, for label extraction.

The decision texts (tools/fetch-korea-lawgokr.py --target ftc) leave out the tender tables: they are images,
`<img src="/LSW/flDownload.do?flSeq=N">`, served by www.law.go.kr without a credential. This writes, per decision,
~/.cache/contract-signals/korea/ftc/images/<serial>/decision.txt (text with [IMAGE imgNNN.png] markers where the tables
sit) and imgNNN.png. Selection: decision names with 입찰 and 공동행위 (bid rigging), decided in --since-year or later,
newest first. One request at a time, --delay seconds apart (robots.txt allows all; no documented limit found).
One kept-alive HTTPS connection (no new handshake per image). Resumable: finished files are skipped. Stops on HTTP 403/429 after backing off, so a block is never hammered.
"""
import argparse
import gzip
import html
import http.client
import os
import re
import time
from pathlib import Path

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea/ftc'
HOST, PATH = 'www.law.go.kr', '/LSW/flDownload.do?flSeq={}'
AGENT = 'contract-signals/0.1 (research; KFTC decision tables, one request at a time)'


def decisions(source, since_year):
    found = []
    for path in source.glob('*.xml.gz'):
        text = gzip.open(path).read().decode('utf-8', 'replace')
        name = re.search(r'<사건명><!\[CDATA\[(.*?)\]\]>', text, re.S)
        date = re.search(r'<결정일자>\s*(\d{4})\.?\s*(\d{1,2})?\.?\s*(\d{1,2})?', text)
        if not name or '입찰' not in name.group(1) or '공동행위' not in name.group(1) or not date:
            continue
        if int(date.group(1)) >= since_year:
            key = (int(date.group(1)), int(date.group(2) or 0), int(date.group(3) or 0))
            found.append((key, path.name.removesuffix('.xml.gz'), text))
    return [(serial, text) for _, serial, text in sorted(found, reverse=True)]


def as_text(text):
    count = 0
    def marker(m):  # numbered like the downloads; law.go.kr leaves some tables as dead relative links (table_image_N.png)
        nonlocal count
        if 'flSeq=' not in m.group(0):
            return '\n[IMAGE MISSING: not published on law.go.kr]\n'
        count += 1
        return f'\n[IMAGE img{count:03d}.png]\n'
    text = re.sub(r'<img[^>]*>(</img>)?', marker, text)
    return html.unescape(re.sub(r'<[^>]+>', ' ', text))


class Client:
    def __init__(self):
        self.connection = None

    def get(self, seq):
        if self.connection is None:
            self.connection = http.client.HTTPSConnection(HOST, timeout=60)
        self.connection.request('GET', PATH.format(seq), headers={'User-Agent': AGENT, 'Connection': 'keep-alive'})
        response = self.connection.getresponse()
        body = response.read()
        if response.getheader('Connection', '').lower() == 'close':
            self.close()
        return response.status, body

    def close(self):
        if self.connection:
            self.connection.close()
        self.connection = None


def fetch(client, seq):
    for attempt in range(4):
        try:
            status, body = client.get(seq)
            if status == 200:
                return body
            if status in (403, 429) and attempt == 3:
                raise SystemExit(f'flSeq={seq}: HTTP {status} after backing off; stopping (blocked or rate limited)')
            if status not in (403, 429, 500, 502, 503, 504):
                raise SystemExit(f'flSeq={seq}: HTTP {status}')
        except (OSError, http.client.HTTPException):
            client.close()
            if attempt == 3:
                raise
        client.close()
        time.sleep(60 * 2 ** attempt)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--source', type=Path, default=BASE / 'decisions')
    parser.add_argument('--out', type=Path, default=BASE / 'images')
    parser.add_argument('--since-year', type=int, default=2010)
    parser.add_argument('--delay', type=float, default=1.5, help='seconds between requests (at least 1)')
    args = parser.parse_args()
    delay = max(1.0, args.delay)
    chosen = decisions(args.source, args.since_year)
    total = sum(len(re.findall(r'flSeq=\d+', t)) for _, t in chosen)
    print(f'{len(chosen)} bid-rigging decisions since {args.since_year}, {total} images', flush=True)
    calls = 0
    client = Client()
    for done, (serial, text) in enumerate(chosen, 1):
        folder = args.out / serial
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'decision.txt').write_text(as_text(text), encoding='utf-8')
        seqs = re.findall(r'flSeq=(\d+)', text)
        for i, seq in enumerate(seqs, 1):
            path = folder / f'img{i:03d}.png'
            if path.exists():
                continue
            body = fetch(client, seq)
            if not body.startswith(b'\x89PNG') and not body[:3] == b'\xff\xd8\xff' and not body[:4] == b'GIF8':
                raise SystemExit(f'{serial} flSeq={seq}: not an image ({body[:60]!r}); stopping')
            part = path.with_suffix('.part')
            part.write_bytes(body)
            part.rename(path)
            calls += 1
            time.sleep(delay)
        print(f'{done}/{len(chosen)} {serial}: {len(seqs)} images ({calls} downloaded this run)', flush=True)


if __name__ == '__main__':
    main()
