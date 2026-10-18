"""One polite HTTP client for every evidence fetcher: honest User-Agent, robots.txt, one request at a time per host.

Rules, shared by every source module so no single script can go faster:
- An honest User-Agent naming the project; never a browser string.
- robots.txt is read once per host and obeyed: a disallowed URL raises Disallowed (a 404/missing robots.txt allows all).
- Per host, one request in flight and starts at least INTERVALS[host] (default 1 s) apart, across processes too:
  a lock file per host in ~/.cache/contract-signals/http-locks/ is held for the whole request.
- 429/503 honour Retry-After (capped) and give up after a few; 401/403 raise Refused at once and are never retried.
  A block is final: record it, do not work around it.
- Redirects are followed by hand, each hop through the same rules (its host's robots.txt and lock), query intact.
- Bodies are capped; every request is appended to a JSONL log (url, status, final url, bytes, sha256).
"""
import fcntl
import hashlib
import http.client
import json
import os
import time
import urllib.parse
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = 'contract-signals/0.1 (public research; https://contracts.lasu.dev)'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals'
INTERVALS = {}  # host -> minimum seconds between request starts; default below
DEFAULT_INTERVAL = 1.0
MAX_RETRY_AFTER = 120


class Refused(Exception):
    """The server refused (401/403) or kept throttling: stop, do not retry or work around it."""


class Disallowed(Exception):
    """robots.txt disallows this URL for our User-Agent."""


class Response:
    def __init__(self, url, status, headers, body, hops):
        self.url, self.status, self.headers, self.body, self.hops = url, status, headers, body, hops

    def json(self):
        return json.loads(self.body)


def _default_transport(method, url, headers, body, timeout):
    parts = urllib.parse.urlsplit(url)
    connection = (http.client.HTTPSConnection if parts.scheme == 'https' else http.client.HTTPConnection)(parts.netloc, timeout=timeout)
    try:
        path = parts.path or '/'
        connection.request(method, path + ('?' + parts.query if parts.query else ''), body=body, headers=headers)
        response = connection.getresponse()
        return response.status, {k.lower(): v for k, v in response.getheaders()}, response
    except BaseException:
        connection.close()
        raise


class PoliteClient:
    def __init__(self, log_path=None, max_bytes=50 * 1024 * 1024, timeout=60, transport=None, sleep=time.sleep,
                 clock=time.time, lock_dir=None, obey_robots=True):
        self.log_path, self.max_bytes, self.timeout = log_path, max_bytes, timeout
        self.transport, self.sleep, self.clock = transport or _default_transport, sleep, clock
        self.lock_dir = Path(lock_dir) if lock_dir else CACHE / 'http-locks'
        self.obey_robots = obey_robots
        self.robots = {}

    # robots.txt -----------------------------------------------------------------------------------------
    def allowed(self, url):
        parts = urllib.parse.urlsplit(url)
        origin = f'{parts.scheme}://{parts.netloc}'
        if origin not in self.robots:
            status, _, body = self._raw('GET', origin + '/robots.txt', {}, None, record=True)
            parser = urllib.robotparser.RobotFileParser()
            text = body.decode('utf-8', 'replace') if status == 200 else ''
            # A web app answering robots.txt with its HTML page publishes no rules.
            parser.parse([] if text.lstrip().lower().startswith(('<!doctype', '<html')) else text.splitlines())
            self.robots[origin] = parser
        return self.robots[origin].can_fetch(USER_AGENT, url)

    # one request, spaced and serialised per host ---------------------------------------------------------
    def _raw(self, method, url, headers, body, record=True):
        host = urllib.parse.urlsplit(url).netloc
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        with open(self.lock_dir / f'{host}.lock', 'a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)  # held for the whole request: one in flight per host
            try:
                lock.seek(0)
                last = float(lock.read().strip() or 0)
                wait = last + INTERVALS.get(host, DEFAULT_INTERVAL) - self.clock()
                if wait > 0:
                    self.sleep(wait)
                lock.seek(0), lock.truncate(), lock.write(repr(self.clock())), lock.flush()
                status, response_headers, stream = self.transport(method, url, {'User-Agent': USER_AGENT, **headers}, body, self.timeout)
                data = stream.read(self.max_bytes + 1)
                stream.close()
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
        if len(data) > self.max_bytes:
            raise ValueError(f'Response over {self.max_bytes} bytes: {url}')
        if record:
            self._log({'at': datetime.now(timezone.utc).isoformat(), 'method': method, 'url': url, 'status': status,
                       'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        return status, response_headers, data

    def _log(self, entry):
        if self.log_path:
            Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def request(self, method, url, headers=None, body=None, max_redirects=5, max_throttles=4):
        hops, throttles = [], 0
        while True:
            if self.obey_robots and not self.allowed(url):
                raise Disallowed(url)
            status, response_headers, data = self._raw(method, url, headers or {}, body)
            if status in (401, 403):
                raise Refused(f'HTTP {status}: {url}')
            if status in (429, 503):
                throttles += 1
                if throttles > max_throttles:
                    raise Refused(f'HTTP {status} {throttles} times: {url}')
                retry = response_headers.get('retry-after', '')
                self.sleep(min(MAX_RETRY_AFTER, int(retry) if retry.isdigit() else 5 * 2 ** throttles))
                continue
            if status in (301, 302, 303, 307, 308) and response_headers.get('location'):
                if len(hops) >= max_redirects:
                    raise ValueError(f'More than {max_redirects} redirects: {hops[0]}')
                hops.append(url)
                # The Location is used as given: signed queries (Signature=, temp_url_sig=) must stay intact.
                url = urllib.parse.urljoin(url, response_headers['location'])
                if status == 303:
                    method, body = 'GET', None
                continue
            return Response(url, status, response_headers, data, hops)

    def get(self, url, **kwargs):
        return self.request('GET', url, **kwargs)
