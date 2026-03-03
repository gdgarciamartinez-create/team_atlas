from __future__ import annotations

import os
import time
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "bitacora.sqlite3")


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts INTEGER NOT NULL,
              symbol TEXT NOT NULL,
              tf TEXT NOT NULL,
              side TEXT NOT NULL,
              entry REAL NOT NULL,
              sl REAL,
              tp REAL,
              exit REAL,
              result TEXT,
              pips REAL,
              notes TEXT
            );
            """
        )
        con.commit()


def _pip_size(symbol: str) -> float:
    s = (symbol or "").upper()
    if "JPY" in s:
        return 0.01
    if "XAU" in s or "GOLD" in s:
        return 0.01
    return 0.0001


def _calc_pips(symbol: str, side: str, entry: float, exit: float) -> float:
    pip = _pip_size(symbol)
    if pip <= 0:
        return 0.0
    diff = (exit - entry)
    if side.upper() == "SELL":
        diff = -diff
    return float(diff / pip)


def add_trade(t: Dict[str, Any]) -> int:
    ts = int(t.get("ts") or int(time.time()))
    symbol = str(t.get("symbol"))
    tf = str(t.get("tf") or "M5")
    side = str(t.get("side"))
    entry = float(t.get("entry"))
    sl = t.get("sl")
    tp = t.get("tp")
    exitp = t.get("exit")
    result = t.get("result")
    notes = t.get("notes")

    pips = None
    if exitp is not None:
        pips = _calc_pips(symbol, side, entry, float(exitp))

    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO trades (ts, symbol, tf, side, entry, sl, tp, exit, result, pips, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                symbol,
                tf,
                side.upper(),
                entry,
                float(sl) if sl is not None else None,
                float(tp) if tp is not None else None,
                float(exitp) if exitp is not None else None,
                str(result) if result is not None else None,
                float(pips) if pips is not None else None,
                str(notes) if notes is not None else None,
            ),
        )
        con.commit()
        return int(cur.lastrowid)


def list_trades(limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(
            """
            SELECT * FROM trades
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (int(limit), int(offset)),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def summary() -> Dict[str, Any]:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(1) FROM trades")
        n = int(cur.fetchone()[0] or 0)

        cur.execute("SELECT COALESCE(SUM(pips),0) FROM trades WHERE pips IS NOT NULL")
        total_pips = float(cur.fetchone()[0] or 0.0)

        cur.execute("SELECT COUNT(1) FROM trades WHERE result='WIN'")
        wins = int(cur.fetchone()[0] or 0)

        cur.execute("SELECT COUNT(1) FROM trades WHERE result='LOSS'")
        losses = int(cur.fetchone()[0] or 0)

        winrate = (wins / (wins + losses) * 100.0) if (wins + losses) > 0 else 0.0

        return {
            "trades": n,
            "wins": wins,
            "losses": losses,
            "winrate": round(winrate, 2),
            "total_pips": round(total_pips, 2),
        }
