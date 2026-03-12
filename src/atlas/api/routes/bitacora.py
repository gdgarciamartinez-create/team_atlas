from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Query

from atlas.runtime import runtime

router = APIRouter(prefix="/bitacora", tags=["bitacora"])


def _safe_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except Exception:
        return None


def _deep_payload(item: Dict[str, Any]) -> Dict[str, Any]:
    p1 = item.get("payload") or {}
    p2 = p1.get("payload") if isinstance(p1, dict) else {}
    out: Dict[str, Any] = {}

    if isinstance(p1, dict):
        out.update(p1)
    if isinstance(p2, dict):
        out.update(p2)

    return out


def _event_name(item: Dict[str, Any]) -> str:
    return str(item.get("event") or "").upper().strip()


def _trade_key(symbol: Any, tf: Any, entry: Any, side: Any) -> str:
    return f"{symbol}|{tf}|{entry}|{side}"


def _normalize_closed_trade(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ts": item.get("ts"),
        "symbol": item.get("symbol"),
        "tf": item.get("tf"),
        "side": item.get("side"),
        "entry": item.get("entry"),
        "sl": item.get("sl"),
        "tp": item.get("tp"),
        "exit": item.get("exit"),
        "result": item.get("result"),
        "pips": item.get("pips"),
        "usd": item.get("usd"),
    }


def _dedupe_closed(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[Tuple[Any, ...]] = set()
    out: List[Dict[str, Any]] = []

    for item in items:
        key = (
            item.get("ts"),
            item.get("symbol"),
            item.get("tf"),
            item.get("side"),
            item.get("entry"),
            item.get("exit"),
            item.get("result"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(item)

    return out


def _fallback_tick(symbol: str) -> float:
    s = str(symbol or "").upper()
    if "JPY" in s:
        return 0.001
    if s.startswith("XAU"):
        return 0.01
    if s.startswith("USTEC"):
        return 1.0
    if s.startswith("BTC"):
        return 1.0
    if s.startswith("USOIL"):
        return 0.01
    return 0.00001


def _calc_fallback_pips(symbol: str, entry: float, exit_price: float, side: str) -> float:
    tick = _fallback_tick(symbol)
    if tick <= 0:
        return 0.0

    side_u = str(side or "").upper()
    if side_u == "BUY":
        return (exit_price - entry) / tick
    return (entry - exit_price) / tick


def _parse_closed_from_ops(ops: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    active: Dict[str, Dict[str, Any]] = {}
    closed: List[Dict[str, Any]] = []

    for raw in ops:
        event = _event_name(raw)
        payload = _deep_payload(raw)

        symbol = payload.get("symbol") or raw.get("symbol")
        tf = payload.get("tf") or raw.get("tf")
        side = payload.get("side") or raw.get("side")
        entry = payload.get("entry", raw.get("entry"))
        sl = payload.get("sl", raw.get("sl"))
        tp = payload.get("tp", raw.get("tp"))
        ts = raw.get("ts") or payload.get("ts")

        if not symbol or not tf:
            continue

        key = _trade_key(symbol, tf, entry, side)

        if event == "ENTRY":
            active[key] = {
                "ts": ts,
                "symbol": symbol,
                "tf": tf,
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
            }
            continue

        if event in {"IN_TRADE", "TP1", "TP2", "RUN"}:
            prev = active.get(key)
            if prev:
                prev["sl"] = sl if sl is not None else prev.get("sl")
                prev["tp"] = tp if tp is not None else prev.get("tp")
            continue

        if event == "TRADE_CLOSED":
            result = payload.get("result")
            exit_price = payload.get("exit", payload.get("price"))
            pips = payload.get("pips")
            usd = payload.get("usd")

            base = active.get(key, {})
            closed.append(
                {
                    "ts": ts,
                    "symbol": symbol,
                    "tf": tf,
                    "side": side or base.get("side"),
                    "entry": entry if entry is not None else base.get("entry"),
                    "sl": sl if sl is not None else base.get("sl"),
                    "tp": tp if tp is not None else base.get("tp"),
                    "exit": exit_price,
                    "result": result,
                    "pips": pips,
                    "usd": usd,
                }
            )
            active.pop(key, None)
            continue

        if event in {"SL", "TP2", "RUN_CLOSE", "TP1_CLOSE"}:
            base = active.get(key, {})
            exit_price = payload.get("price", payload.get("exit"))

            trade = {
                "ts": ts,
                "symbol": symbol,
                "tf": tf,
                "side": side or base.get("side"),
                "entry": entry if entry is not None else base.get("entry"),
                "sl": sl if sl is not None else base.get("sl"),
                "tp": tp if tp is not None else base.get("tp"),
                "exit": exit_price,
                "result": event,
                "pips": None,
                "usd": None,
            }

            entry_f = _safe_float(trade.get("entry"))
            exit_f = _safe_float(trade.get("exit"))
            side_s = str(trade.get("side") or "").upper()

            if entry_f is not None and exit_f is not None and side_s in {"BUY", "SELL"}:
                pips = _calc_fallback_pips(str(symbol), entry_f, exit_f, side_s)
                trade["pips"] = round(pips, 2)
                trade["usd"] = round(pips * 1.0, 2)

            closed.append(trade)
            active.pop(key, None)

    closed = _dedupe_closed(closed)
    return closed[-limit:]


@router.get("/ops")
def get_ops(limit: int = Query(default=200, ge=1, le=2000)) -> dict:
    items = runtime.get_ops_log(limit)
    return {
        "ok": True,
        "count": len(items),
        "items": items,
    }


@router.get("/tail")
def get_tail(limit: int = Query(default=50, ge=1, le=500)) -> dict:
    items = runtime.get_ops_log(limit)
    return {
        "ok": True,
        "count": len(items),
        "items": items,
    }


@router.get("/closed")
def get_closed(limit: int = Query(default=200, ge=1, le=2000)) -> dict:
    closed_runtime = runtime.get_closed_trades(limit)
    normalized_runtime = [_normalize_closed_trade(x) for x in closed_runtime if isinstance(x, dict)]
    normalized_runtime = _dedupe_closed(normalized_runtime)

    if normalized_runtime:
        return {
            "ok": True,
            "source": "runtime_closed_trades",
            "count": len(normalized_runtime),
            "items": normalized_runtime[-limit:],
        }

    ops = runtime.get_ops_log(2000)
    rebuilt = _parse_closed_from_ops(ops, limit)

    return {
        "ok": True,
        "source": "rebuilt_from_ops",
        "count": len(rebuilt),
        "items": rebuilt,
    }