import json
import os
import sqlite3
import threading
from typing import Any, Optional

from .config import settings

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(os.path.abspath(settings.cache_path)), exist_ok=True)
        _conn = sqlite3.connect(settings.cache_path, check_same_thread=False)
        _conn.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
        _conn.commit()
    return _conn


def get(key: str) -> Optional[Any]:
    with _lock:
        row = _db().execute("SELECT v FROM cache WHERE k=?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def put(key: str, value: Any) -> None:
    with _lock:
        _db().execute("INSERT OR REPLACE INTO cache (k, v) VALUES (?, ?)", (key, json.dumps(value)))
        _db().commit()
