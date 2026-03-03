# src/atlas/bot/rate_limit.py
from __future__ import annotations

from datetime import date, datetime
from atlas.bot.state import BOT_STATE


def _today() -> str:
    return str(date.today())


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_daily():
    daily = BOT_STATE.setdefault("daily", {})
    if not isinstance(daily, dict):
        daily = {}
        BOT_STATE["daily"] = daily

    if daily.get("date") != _today():
        daily["date"] = _today()
        daily["symbols"] = {}  # reset diario

    symbols = daily.setdefault("symbols", {})
    if not isinstance(symbols, dict):
        symbols = {}
        daily["symbols"] = symbols

    return daily, symbols


def _symrec(symbol: str) -> dict:
    _, symbols = _ensure_daily()
    rec = symbols.setdefault(symbol, {})
    if not isinstance(rec, dict):
        rec = {}
        symbols[symbol] = rec
    rec.setdefault("entry_sent", False)
    rec.setdefault("partial_sent", False)
    rec.setdefault("entry", None)     # {price, sl, tp1, kind, ts}
    rec.setdefault("tp1", None)       # float
    rec.setdefault("sl", None)        # float
    rec.setdefault("ts_entry", None)
    rec.setdefault("ts_partial", None)
    return rec


def can_send_entry(symbol: str) -> bool:
    rec = _symrec(symbol)
    return rec.get("entry_sent") is False


def mark_entry_sent(symbol: str, entry_payload: dict):
    rec = _symrec(symbol)
    rec["entry_sent"] = True
    rec["entry"] = entry_payload
    rec["tp1"] = entry_payload.get("tp1")
    rec["sl"] = entry_payload.get("sl")
    rec["ts_entry"] = _iso_now()


def can_send_partial(symbol: str) -> bool:
    rec = _symrec(symbol)
    return rec.get("entry_sent") is True and rec.get("partial_sent") is False


def mark_partial_sent(symbol: str, partial_payload: dict):
    rec = _symrec(symbol)
    rec["partial_sent"] = True
    rec["ts_partial"] = _iso_now()
    rec["partial"] = partial_payload


def get_daily_symbol_state(symbol: str) -> dict:
    return _symrec(symbol)
