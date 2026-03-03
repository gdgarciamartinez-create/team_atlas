from __future__ import annotations
import json
import sqlite3
import time
from typing import Any, Dict, List, Optional

class AuditLog:
    def __init__(self, path: str = "atlas_audit.sqlite"):
        self.path = path
        self._init()

    def _conn(self):
        return sqlite3.connect(self.path, check_same_thread=False)

    def _init(self):
        con = self._conn()
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            kind TEXT NOT NULL,
            symbol TEXT,
            window TEXT,
            payload TEXT NOT NULL
        )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_events_symbol ON events(symbol)")
        con.commit()
        con.close()

    def write(self, kind: str, payload: Dict[str, Any], symbol: Optional[str] = None, window: Optional[str] = None):
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO events(ts,kind,symbol,window,payload) VALUES(?,?,?,?,?)",
            (int(time.time()), kind, symbol, window, json.dumps(payload, ensure_ascii=False))
        )
        con.commit()
        con.close()

    def tail(self, limit: int = 200) -> List[Dict[str, Any]]:
        con = self._conn()
        cur = con.cursor()
        cur.execute("SELECT id,ts,kind,symbol,window,payload FROM events ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        con.close()
        out = []
        for r in rows:
            out.append({
                "id": r[0], "ts": r[1], "kind": r[2], "symbol": r[3], "window": r[4],
                "payload": json.loads(r[5])
            })
        return out[::-1]

    def by_symbol(self, symbol: str, limit: int = 200) -> List[Dict[str, Any]]:
        con = self._conn()
        cur = con.cursor()
        cur.execute("SELECT id,ts,kind,symbol,window,payload FROM events WHERE symbol=? ORDER BY id DESC LIMIT ?", (symbol, limit))
        rows = cur.fetchall()
        con.close()
        out = []
        for r in rows:
            out.append({
                "id": r[0], "ts": r[1], "kind": r[2], "symbol": r[3], "window": r[4],
                "payload": json.loads(r[5])
            })
        return out[::-1]

    def get_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        con = self._conn()
        cur = con.cursor()
        cur.execute("SELECT id,ts,kind,symbol,window,payload FROM events WHERE id=?", (event_id,))
        r = cur.fetchone()
        con.close()
        if not r:
            return None
        return {"id": r[0], "ts": r[1], "kind": r[2], "symbol": r[3], "window": r[4], "payload": json.loads(r[5])}