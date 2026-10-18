#!/usr/bin/env python3
"""Bounded, resumable national Prozorro *identifier feed*, NOT contract records.

The feed is ordered by dateModified; each row also carries dateCreated, procurementMethodType and status
(the feed's opt_fields), so in-window tenders can be counted without detail requests; do not assume
strict date ordering or stop at a date boundary. To find created-in-window
tenders, validate complete discovery, retrieve details and filter dateCreated. Never call this a census
of contracts. No attachments, bidder/contact details or paid services are used.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import urllib.parse
import urllib.request

API = 'https://public-api.prozorro.gov.ua/api/2.5/tenders'
MAX_RESPONSE = 1024 * 1024
OPT_FIELDS = 'dateCreated,procurementMethodType,status'
PAGE_ROWS = 1000


def iso(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    return result.astimezone(timezone.utc)


def validate_url(url):
    parsed, base = urllib.parse.urlsplit(url), urllib.parse.urlsplit(API)
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if ((parsed.scheme, parsed.netloc, parsed.path) != (base.scheme, base.netloc, base.path)
            or parsed.fragment or set(query) - {'offset', 'limit', 'opt_fields'}
            or any(len(values) != 1 for values in query.values())
            or sorted(query.get('opt_fields', [OPT_FIELDS])[0].split(',')) != sorted(OPT_FIELDS.split(','))):
        raise ValueError('Unexpected feed continuation URL')
    return url


def parse_page(body, since, until):
    value = json.loads(body)
    if not isinstance(value.get('data'), list):
        raise ValueError('Missing feed data')
    rows, beyond = [], False
    for row in value['data']:
        ident, modified = row.get('id', ''), row.get('dateModified', '')
        if not re.fullmatch('[a-f0-9]{32}', ident):
            raise ValueError('Invalid tender identifier')
        date = iso(modified)
        if date >= until:
            beyond = True
        elif date >= since:
            created = row.get('dateCreated')
            rows.append((ident, date.isoformat(), iso(created).isoformat() if created else None,
                         row.get('procurementMethodType'), row.get('status')))
    next_url = value.get('next_page', {}).get('uri')
    if next_url:
        validate_url(next_url)
    return rows, next_url, beyond, not value['data']


def open_index(path, since, until):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    connection = sqlite3.connect(path)
    os.chmod(path, 0o600)
    connection.executescript('''CREATE TABLE IF NOT EXISTS tenders(id TEXT PRIMARY KEY, date_modified TEXT NOT NULL, date_created TEXT, method TEXT, status TEXT);
    CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS pages(page_no INTEGER PRIMARY KEY, url TEXT, sha256 TEXT, bytes INTEGER, rows INTEGER);''')
    state = dict(connection.execute('SELECT key,value FROM state'))
    if state:
        if iso(state['since']) != since or (until and iso(state['until']) != until):
            connection.close()
            raise ValueError('Existing index has different frozen modification window')
    else:
        until = until or datetime.now(timezone.utc)
        if since >= until:
            raise ValueError('Invalid modification window')
        state = {'since': since.isoformat(), 'until': until.isoformat(), 'phase': 'partial',
                 'next': API + '?' + urllib.parse.urlencode({'limit': PAGE_ROWS, 'offset': str(since.timestamp()), 'opt_fields': OPT_FIELDS})}
        with connection:
            connection.executemany('INSERT INTO state VALUES (?,?)', state.items())
    return connection, state


def collect(path, since, until=None, max_pages=3, max_bytes=1024 * 1024, delay=1, fetch=None):
    if max_pages < 1 or max_bytes < 1 or delay < 1:
        raise ValueError('Positive budgets and at least one second between requests required')
    db, state = open_index(path, since, until)
    used, pages, reason = 0, 0, 'budget'
    try:
        while state['phase'] == 'partial' and pages < max_pages and used < max_bytes:
            url = validate_url(state['next'])
            limit = min(MAX_RESPONSE, max_bytes - used)
            if pages:
                time.sleep(delay)
            if fetch:
                body = fetch(url, limit)
            else:
                request = urllib.request.Request(url, headers={'User-Agent': 'contract-signals/0.1 (bounded public identifier index)'})
                with urllib.request.urlopen(request, timeout=30) as response:
                    body = response.read(limit + 1)
            if len(body) > limit:
                reason = 'response-budget'; break  # No cursor advance, partial response never committed.
            rows, next_url, beyond, empty = parse_page(body, iso(state['since']), iso(state['until']))
            if next_url == url and not empty:
                raise ValueError('Continuation cursor did not advance')
            new_state = dict(state)
            # Dates within a real feed page can be out of order. Seeing a date
            # beyond the frozen bound does NOT establish a complete prefix.
            if empty:
                reason = 'feed-empty-observed-not-completeness-proof'
            elif not next_url:
                raise ValueError('Nonempty feed page lacks continuation')
            if next_url:
                new_state['next'] = next_url
            with db:
                # A tender modified again appears again later in the feed: keep its latest observation.
                db.executemany('''INSERT INTO tenders VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                    (date_modified, date_created, method, status) = (excluded.date_modified, excluded.date_created, excluded.method, excluded.status)
                    WHERE excluded.date_modified >= tenders.date_modified''', rows)
                db.execute('INSERT INTO pages(url,sha256,bytes,rows) VALUES (?,?,?,?)', (url, hashlib.sha256(body).hexdigest(), len(body), len(rows)))
                db.executemany('INSERT OR REPLACE INTO state VALUES (?,?)', new_state.items())
            state = new_state
            used += len(body); pages += 1
            if empty:
                break
        count = db.execute('SELECT COUNT(*) FROM tenders').fetchone()[0]
        created = db.execute('SELECT COUNT(*) FROM tenders WHERE date_created >= ? AND date_created < ?',
                             (state['since'], state['until'])).fetchone()[0]
        total_pages, total_bytes = db.execute('SELECT COUNT(*),COALESCE(SUM(bytes),0) FROM pages').fetchone()
        return {'phase': state['phase'], 'stopReason': reason, 'uniqueTenderIds': count, 'createdInWindow': created,
                'pagesThisRun': pages, 'responseBytesThisRun': used,
                'totalPages': total_pages, 'totalResponseBytes': total_bytes,
                'modificationWindow': {'sinceInclusive': state['since'], 'untilExclusive': state['until']},
                'fullTenderDetails': 0, 'attachmentsDownloaded': 0,
                'nationalContractCompletenessEstablished': False}
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--since', default='2024-09-01T00:00:00+03:00')
    parser.add_argument('--until', help='Frozen observation end; defaults to current time on first run')
    parser.add_argument('--index', type=Path, default=Path.home() / '.cache/contract-signals/prozorro-national/feed-index-v2.sqlite')
    parser.add_argument('--max-pages', type=int, default=3)
    parser.add_argument('--max-bytes', type=int, default=1024 * 1024)
    args = parser.parse_args()
    os.umask(0o077)
    root = Path(__file__).resolve().parents[1]
    if args.index.resolve().is_relative_to(root):
        parser.error('National index must stay outside the repository/web root')
    print(json.dumps(collect(args.index, iso(args.since), iso(args.until) if args.until else None,
                             args.max_pages, args.max_bytes), indent=2))


if __name__ == '__main__':
    main()
