"""Small helpers shared by the tools.

Import with the tools directory on the path, as for polite_http and decp_feeds:

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import canonical, sha  # noqa: E402

Only helpers whose copies behaved identically live here; variants that differ in
coercion (for example text() that strips, or returns '' for None) stay in their tools.
"""
import gzip
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    """Canonical JSON bytes for hashing: sorted keys, no spaces, UTF-8, NaN refused."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def without_hashes(value):
    """The value with hash fields removed, so frozen evidence compares by content (hashes are metadata only)."""
    if isinstance(value, dict):
        return {k: without_hashes(v) for k, v in value.items()
                if k not in ('inputHashes', 'rawSnapshotHashes', 'checksum') and not k.lower().endswith('sha256')}
    if isinstance(value, list):
        return [without_hashes(v) for v in value]
    return value


def require(condition, message):
    if not condition:
        raise ValueError(message)


def many(value):
    """A JSON field that may hold one item, a list or nothing, as a list."""
    return value if isinstance(value, list) else [] if value is None else [value]


def text(value):
    """The '#text' of an XML-derived JSON node, or the value unchanged."""
    return value.get('#text') if isinstance(value, dict) else value


def load(name, path):
    """Load a tool script (hyphenated file names cannot be imported) from a path relative to the repository."""
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_private(path, blob):
    """Write a new file readable by the owner only; fails if it exists."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(blob)
        stream.flush()
        os.fsync(stream.fileno())


def load_gz(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def save_json_gz(path, value):
    """Reproducible gzip of indented JSON (mtime 0)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress((json.dumps(value, ensure_ascii=False, indent=1) + '\n').encode(), mtime=0))


def to_int(v):
    """An integer, or a string of digits with optional thousands commas; anything else is None."""
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str) and re.fullmatch(r'[\d,]+', v.strip()):
        return int(v.replace(',', ''))
    return None
