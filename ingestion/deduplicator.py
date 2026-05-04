import hashlib
import json
from pathlib import Path
from typing import Any

import diskcache

_DEDUP_DIR = ".cache/dedup"
_dedup_store = diskcache.Cache(_DEDUP_DIR)

def _content_hash(content: Any) -> str:
    serialised = json.dumps(content, sort_keys=True, default=str)
    return hashlib.md5(serialised.encode()).hexdigest()

def is_duplicate(content: Any) -> bool:
    h = _content_hash(content)
    return h in _dedup_store

def mark_ingested(content: Any) -> str:
    h = _content_hash(content)
    _dedup_store[h] = True
    return h

def file_hash(path: str | Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def is_file_duplicate(path: str | Path) -> bool:
    h = file_hash(path)
    return h in _dedup_store

def mark_file_ingested(path: str | Path) -> str:
    h = file_hash(path)
    _dedup_store[h] = True
    return h
