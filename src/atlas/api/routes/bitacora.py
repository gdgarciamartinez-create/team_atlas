from __future__ import annotations

import csv
import io
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse

from atlas.runtime import runtime

router = APIRouter(prefix="/bitacora", tags=["bitacora"])

TRADE_EXPORT_FIELDS = [
    "time",
    "world",
    "atlas_mode",
    "mode",
    "symbol",
    "tf",
    "score",
    "side",
    "trade_id",
    "parent_trade_id",
    "leg_id",
    "is_partial",
    "partial_percent",
    "entry_price",
    "exit_price",
    "sl_price",
    "tp1_price",
    "tp2_price",
    "entry",
    "sl",
    "tp",
    "tp1",
    "tp2",
    "price_move",
    "pip_move",
    "point_move",
    "usd_result",
    "lot",
    "lot_raw",
    "lot_capped",
    "lot_cap_reason",
    "lot_error",
    "risk_percent",
    "opened_at",
    "closed_at",
    "duration_sec",
    "exit_reason",
]

SUMMARY_EXPORT_FIELDS = [
    "trade_id",
    "world",
    "atlas_mode",
    "mode",
    "symbol",
    "tf",
    "side",
    "entry_price",
    "sl_price",
    "tp1_price",
    "tp2_price",
    "entry",
    "sl",
    "tp1",
    "tp2",
    "lot_total",
    "risk_percent",
    "pnl_total_usd",
    "pnl_total_points",
    "opened_at",
    "closed_at",
    "duration_sec",
    "legs_count",
    "exit_final_reason",
    "score_max",
    "score_avg",
    "had_partial",
    "had_be_close",
    "had_tp2",
]


def _safe_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except Exception:
        return None


def _safe_int(v: Any) -> Optional[int]:
    try:
        return int(float(v))
    except Exception:
        return None


def _asset_type_from_symbol(symbol: str) -> str:
    sym = str(symbol or "").upper().strip()
    if sym.startswith("XAU"):
        return "GOLD"
    if sym.startswith("USTEC") or sym.startswith("NAS") or sym.startswith("US30") or sym.startswith("SPX"):
        return "INDICES"
    if sym.startswith("USOIL") or sym.startswith("UKOIL"):
        return "OIL"
    if sym.startswith("BTC") or sym.startswith("ETH") or sym.startswith("SOL") or sym.startswith("XRP"):
        return "CRYPTO"
    return "FOREX"


def _price_move(entry: float, exit_price: float, side: str) -> float:
    side_u = str(side or "").upper().strip()
    if side_u == "BUY":
        return exit_price - entry
    return entry - exit_price


def _calc_usd(symbol: str, entry: float, exit_price: float, side: str, lot: Optional[float]) -> Optional[float]:
    lot_f = _safe_float(lot)
    if lot_f is None:
        return None

    move = _price_move(entry, exit_price, side)
    sym = str(symbol or "").upper().strip()

    if "JPY" in sym:
        return move * 100.0 * 9.0 * lot_f
    if _asset_type_from_symbol(sym) == "FOREX":
        return move * 10000.0 * 10.0 * lot_f
    if sym.startswith("XAU") or sym.startswith("USOIL"):
        return move * 100.0 * lot_f
    return move * lot_f


def _trade_metrics(symbol: str, entry: float, exit_price: float, side: str, lot: Optional[float]) -> Dict[str, Any]:
    sym = str(symbol or "").upper().strip()
    asset_type = _asset_type_from_symbol(sym)
    price_move = _price_move(entry, exit_price, side)
    pip_move: Optional[float] = None
    point_move: Optional[float] = None

    if asset_type == "FOREX":
        pip_move = price_move * (100.0 if "JPY" in sym else 10000.0)
    elif asset_type in {"GOLD", "INDICES", "OIL"}:
        point_move = price_move

    usd_result = _calc_usd(symbol, entry, exit_price, side, lot)
    return {
        "asset_type": asset_type,
        "price_move": round(price_move, 6),
        "pip_move": round(pip_move, 2) if pip_move is not None else None,
        "point_move": round(point_move, 6) if point_move is not None else None,
        "usd_result": round(usd_result, 2) if usd_result is not None else None,
        "usd": round(usd_result, 2) if usd_result is not None else None,
    }


def _normalize_lot_fields(item: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(item)
    lot = _safe_float(out.get("lot"))
    lot_raw = _safe_float(out.get("lot_raw"))
    lot_capped = _safe_float(out.get("lot_capped"))

    if lot is None:
        lot = lot_capped if lot_capped is not None else lot_raw
    if lot is None:
        lot = 0.0
        if not out.get("lot_error"):
            out["lot_error"] = "MISSING_LOT"

    out["lot"] = lot
    out["lot_raw"] = lot_raw if lot_raw is not None else 0.0
    out["lot_capped"] = lot_capped if lot_capped is not None else 0.0
    return out


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


def _normalized_exit_reason(value: Any) -> Optional[str]:
    raw = str(value or "").upper().strip()
    if not raw:
        return None
    if raw == "TP1":
        return "TP1_PARTIAL"
    if raw in {"TP2", "TP"}:
        return "TP2_FINAL"
    if raw in {"TP1_CLOSE", "RUN_CLOSE", "BE"}:
        return "BE_CLOSE"
    if raw == "SL":
        return "SL"
    if raw == "MANUAL_CLOSE":
        return "MANUAL_CLOSE"
    if raw == "TIME_CLOSE":
        return "TIME_CLOSE"
    if raw in {"INVALIDATION_CLOSE", "TP1_PARTIAL", "TP2_FINAL", "BE_CLOSE"}:
        return raw
    return "INVALIDATION_CLOSE"


def _normalize_closed_trade(item: Dict[str, Any]) -> Dict[str, Any]:
    normalized_reason = _normalized_exit_reason(item.get("exit_reason") or item.get("result"))
    usd_result = item.get("usd_result")
    if usd_result is None:
        usd_result = item.get("usd")

    trade = {
        "time": item.get("time") or item.get("ts"),
        "ts": item.get("ts"),
        "world": item.get("world"),
        "atlas_mode": item.get("atlas_mode"),
        "mode": item.get("mode") or item.get("atlas_mode"),
        "symbol": item.get("symbol"),
        "tf": item.get("tf"),
        "side": item.get("side"),
        "score": item.get("score"),
        "state_at_entry": item.get("state_at_entry"),
        "trade_id": item.get("trade_id"),
        "parent_trade_id": item.get("parent_trade_id"),
        "leg_id": item.get("leg_id"),
        "is_partial": item.get("is_partial"),
        "partial_percent": item.get("partial_percent"),
        "lot": item.get("lot"),
        "lot_raw": item.get("lot_raw"),
        "lot_capped": item.get("lot_capped"),
        "lot_cap_reason": item.get("lot_cap_reason"),
        "lot_error": item.get("lot_error"),
        "risk_percent": item.get("risk_percent"),
        "entry_price": item.get("entry_price", item.get("entry")),
        "tp1_price": item.get("tp1_price"),
        "tp2_price": item.get("tp2_price", item.get("tp")),
        "sl_price": item.get("sl_price", item.get("sl")),
        "exit_price": item.get("exit_price", item.get("exit")),
        "entry": item.get("entry"),
        "sl": item.get("sl"),
        "tp": item.get("tp"),
        "exit": item.get("exit"),
        "close_price": item.get("close_price", item.get("exit")),
        "exit_reason": normalized_reason,
        "result": normalized_reason,
        "raw_result": item.get("raw_result") or item.get("result"),
        "asset_type": item.get("asset_type"),
        "price_move": item.get("price_move"),
        "pip_move": item.get("pip_move"),
        "point_move": item.get("point_move"),
        "pips": item.get("pips"),
        "usd_result": usd_result,
        "usd": item.get("usd"),
        "opened_at": item.get("opened_at", item.get("entry_ts")),
        "signal_ts": item.get("signal_ts"),
        "entry_ts": item.get("entry_ts"),
        "closed_at": item.get("closed_at", item.get("closed_ts", item.get("ts"))),
        "closed_ts": item.get("closed_ts", item.get("ts")),
        "duration_sec": item.get("duration_sec"),
    }
    trade["tp1"] = trade.get("tp1_price")
    trade["tp2"] = trade.get("tp2_price")
    return _normalize_lot_fields(_enrich_trade_units(trade))


def _normalize_trade_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "trade_id": item.get("trade_id"),
        "world": item.get("world"),
        "atlas_mode": item.get("atlas_mode"),
        "mode": item.get("mode") or item.get("atlas_mode"),
        "symbol": item.get("symbol"),
        "tf": item.get("tf"),
        "side": item.get("side"),
        "entry_price": item.get("entry_price"),
        "sl_price": item.get("sl_price"),
        "tp1_price": item.get("tp1_price"),
        "tp2_price": item.get("tp2_price"),
        "entry": item.get("entry_price"),
        "sl": item.get("sl_price"),
        "tp1": item.get("tp1_price"),
        "tp2": item.get("tp2_price"),
        "lot_total": item.get("lot_total"),
        "risk_percent": item.get("risk_percent"),
        "pnl_total_usd": item.get("pnl_total_usd"),
        "pnl_total_points": item.get("pnl_total_points"),
        "opened_at": item.get("opened_at"),
        "closed_at": item.get("closed_at"),
        "duration_sec": item.get("duration_sec"),
        "legs_count": item.get("legs_count"),
        "exit_final_reason": item.get("exit_final_reason"),
        "score_max": item.get("score_max"),
        "score_avg": item.get("score_avg"),
        "had_partial": item.get("had_partial"),
        "had_be_close": item.get("had_be_close"),
        "had_tp2": item.get("had_tp2"),
    }


def _metrics_summary(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_trades = len(items)
    pnl_values: List[float] = []
    win_values: List[float] = []
    loss_values: List[float] = []
    flat_values: List[float] = []
    symbol_totals: Dict[str, float] = {}
    total_partials = 0
    total_be_close = 0
    total_tp2_final = 0
    total_sl = 0
    total_manual_close = 0

    for item in items:
        usd = _safe_float(item.get("pnl_total_usd"))
        if usd is None:
            usd = _safe_float(item.get("usd_result"))
        if usd is None:
            usd = _safe_float(item.get("usd"))
        if usd is None:
            continue
        pnl_values.append(usd)
        if usd > 0:
            win_values.append(usd)
        elif usd < 0:
            loss_values.append(usd)
        else:
            flat_values.append(usd)

        symbol = str(item.get("symbol") or "").strip()
        if symbol:
            symbol_totals[symbol] = symbol_totals.get(symbol, 0.0) + usd

        if item.get("had_partial") or str(item.get("result") or item.get("exit_reason") or "").upper().strip() == "TP1_PARTIAL":
            total_partials += 1

        exit_reason = str(item.get("exit_final_reason") or item.get("result") or item.get("exit_reason") or "").upper().strip()
        if exit_reason == "BE_CLOSE" or item.get("had_be_close"):
            total_be_close += 1
        if exit_reason == "TP2_FINAL" or item.get("had_tp2"):
            total_tp2_final += 1
        if exit_reason == "SL":
            total_sl += 1
        if exit_reason == "MANUAL_CLOSE":
            total_manual_close += 1

    win_trades = len(win_values)
    loss_trades = len(loss_values)
    flat_trades = total_trades - win_trades - loss_trades
    total_pnl_usd = round(sum(pnl_values), 2) if pnl_values else 0.0
    best_symbol = None
    worst_symbol = None
    if symbol_totals:
        best_key = max(symbol_totals, key=lambda x: symbol_totals[x])
        worst_key = min(symbol_totals, key=lambda x: symbol_totals[x])
        best_symbol = {"symbol": best_key, "usd": round(symbol_totals[best_key], 2)}
        worst_symbol = {"symbol": worst_key, "usd": round(symbol_totals[worst_key], 2)}

    return {
        "total_trades": total_trades,
        "win_trades": win_trades,
        "loss_trades": loss_trades,
        "flat_trades": flat_trades,
        "win_rate": round((win_trades / total_trades) * 100.0, 2) if total_trades else 0.0,
        "total_pnl_usd": total_pnl_usd,
        "avg_trade_usd": round(total_pnl_usd / total_trades, 2) if total_trades else 0.0,
        "avg_win_usd": round(sum(win_values) / win_trades, 2) if win_trades else 0.0,
        "avg_loss_usd": round(sum(loss_values) / loss_trades, 2) if loss_trades else 0.0,
        "max_win_usd": round(max(win_values), 2) if win_values else 0.0,
        "max_loss_usd": round(min(loss_values), 2) if loss_values else 0.0,
        "total_partials": total_partials,
        "total_be_close": total_be_close,
        "total_tp2_final": total_tp2_final,
        "total_sl": total_sl,
        "total_manual_close": total_manual_close,
        "symbols_count": len(symbol_totals),
        "best_symbol_by_usd": best_symbol,
        "worst_symbol_by_usd": worst_symbol,
    }


def _resolve_filters(
    world: Optional[str],
    atlas_mode: Optional[str],
    mode: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    mode_u = str(mode or "").upper().strip()
    world_u = str(world or "").upper().strip() or None
    atlas_mode_u = str(atlas_mode or "").upper().strip() or None

    if mode_u in {"GAP", "PRESESION"}:
        return mode_u, None

    if mode_u and not atlas_mode_u:
        return world_u or "ATLAS_IA", mode_u

    return world_u, atlas_mode_u


def _matches_filters(
    item: Dict[str, Any],
    world: Optional[str],
    atlas_mode: Optional[str],
    symbol: Optional[str] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
) -> bool:
    item_world = str(item.get("world") or "").upper().strip()
    item_mode = str(item.get("atlas_mode") or "").upper().strip()
    item_symbol = str(item.get("symbol") or "").upper().strip()
    item_time = str(item.get("closed_at") or item.get("closed_ts") or item.get("ts") or "")

    if world and item_world != str(world).upper().strip():
        return False

    if atlas_mode and item_mode != str(atlas_mode).upper().strip():
        return False

    if symbol and item_symbol != str(symbol).upper().strip():
        return False

    if from_ts and item_time and item_time < str(from_ts):
        return False

    if to_ts and item_time and item_time > str(to_ts):
        return False

    return True


def _normalize_ops_item(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = _deep_payload(item)
    cloned = deepcopy(item)
    if payload.get("world") is not None:
        cloned["world"] = payload.get("world")
    if payload.get("atlas_mode") is not None:
        cloned["atlas_mode"] = payload.get("atlas_mode")
    return cloned


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
        return 0.01
    if s.startswith("XAU"):
        return 0.01
    if s.startswith("USTEC"):
        return 1.0
    if s.startswith("BTC"):
        return 1.0
    if s.startswith("USOIL"):
        return 0.01
    return 0.0001


def _calc_fallback_pips(symbol: str, entry: float, exit_price: float, side: str) -> float:
    tick = _fallback_tick(symbol)
    if tick <= 0:
        return 0.0

    side_u = str(side or "").upper()
    if side_u == "BUY":
        return (exit_price - entry) / tick
    return (entry - exit_price) / tick


def _calc_fallback_usd(symbol: str, pips: float, lot: Optional[float]) -> float:
    lot_f = _safe_float(lot)
    if lot_f is None or lot_f <= 0:
        lot_f = 0.01

    sym = str(symbol or "").upper()

    if "JPY" in sym:
        return pips * 9.0 * lot_f

    forex_6 = {
        "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD",
        "USDCHF", "USDCAD", "EURGBP", "EURCAD",
        "EURAUD", "GBPNZD",
    }
    forex_7 = {s + "Z" for s in forex_6}

    if sym in forex_6 or sym in forex_7:
        return pips * 10.0 * lot_f

    if sym.startswith("XAU"):
        return pips * 1.0 * lot_f

    if sym.startswith("USTEC"):
        return pips * 1.0 * lot_f

    if sym.startswith("BTC"):
        return pips * 1.0 * lot_f

    if sym.startswith("USOIL"):
        return pips * 1.0 * lot_f

    return pips * lot_f


def _enrich_trade_units(item: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(item)
    symbol = str(out.get("symbol") or "")
    side = str(out.get("side") or "").upper().strip()
    entry = _safe_float(out.get("entry_price") if out.get("entry_price") is not None else out.get("entry"))
    exit_price = _safe_float(out.get("exit_price") if out.get("exit_price") is not None else out.get("exit"))
    lot = _safe_float(out.get("lot"))
    out["asset_type"] = out.get("asset_type") or _asset_type_from_symbol(symbol)

    if entry is None or exit_price is None or side not in {"BUY", "SELL"}:
        return out

    metrics = _trade_metrics(symbol, entry, exit_price, side, lot)
    if out.get("price_move") is None:
        out["price_move"] = metrics["price_move"]
    if out.get("pip_move") is None and out["asset_type"] == "FOREX":
        out["pip_move"] = metrics["pip_move"]
    if out.get("point_move") is None and out["asset_type"] in {"GOLD", "INDICES", "OIL"}:
        out["point_move"] = metrics["point_move"]
    if out.get("usd_result") is None:
        out["usd_result"] = metrics["usd_result"]
    if out.get("usd") is None:
        out["usd"] = out.get("usd_result")
    if out.get("pips") is None:
        out["pips"] = round(_calc_fallback_pips(symbol, entry, exit_price, side), 2)
    return out


def _summary_points_value(trade: Dict[str, Any]) -> float:
    point_move = _safe_float(trade.get("point_move"))
    if point_move is not None:
        return point_move
    pip_move = _safe_float(trade.get("pip_move"))
    if pip_move is not None:
        return pip_move
    return _safe_float(trade.get("price_move")) or 0.0


def _duration_sec(opened_at: Optional[str], closed_at: Optional[str]) -> Optional[int]:
    try:
        if not opened_at or not closed_at:
            return None
        from datetime import datetime

        start_dt = datetime.fromisoformat(str(opened_at).replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(str(closed_at).replace("Z", "+00:00"))
        return max(0, int((end_dt - start_dt).total_seconds()))
    except Exception:
        return None


def _rebuild_trade_summaries(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        summary_id = str(item.get("parent_trade_id") or item.get("trade_id") or "").strip()
        if summary_id:
            grouped.setdefault(summary_id, []).append(item)

    summaries: List[Dict[str, Any]] = []
    for summary_id, legs in grouped.items():
        legs_sorted = sorted(
            legs,
            key=lambda x: (
                str(x.get("closed_at") or x.get("ts") or ""),
                _safe_int(x.get("leg_id")) or 0,
            ),
        )
        final_leg = next(
            (leg for leg in reversed(legs_sorted) if str(leg.get("exit_reason") or "") != "TP1_PARTIAL"),
            None,
        )
        if not final_leg:
            continue

        first_leg = legs_sorted[0]
        lot_candidates = [
            _safe_float(leg.get("lot_capped"))
            for leg in legs_sorted
            if _safe_float(leg.get("lot_capped")) is not None
        ]
        if not lot_candidates:
            lot_candidates = [
                _safe_float(leg.get("lot"))
                for leg in legs_sorted
                if _safe_float(leg.get("lot")) is not None
            ]

        opened_at = first_leg.get("opened_at") or first_leg.get("entry_ts") or first_leg.get("signal_ts")
        closed_at = final_leg.get("closed_at") or final_leg.get("closed_ts") or final_leg.get("ts")

        summaries.append(
            {
                "trade_id": summary_id,
                "world": first_leg.get("world"),
                "atlas_mode": first_leg.get("atlas_mode"),
                "mode": first_leg.get("mode") or first_leg.get("atlas_mode"),
                "symbol": first_leg.get("symbol"),
                "tf": first_leg.get("tf"),
                "side": first_leg.get("side"),
                "entry_price": first_leg.get("entry_price", first_leg.get("entry")),
                "sl_price": first_leg.get("sl_price", first_leg.get("sl")),
                "tp1_price": first_leg.get("tp1_price"),
                "tp2_price": first_leg.get("tp2_price", first_leg.get("tp")),
                "lot_total": max(lot_candidates) if lot_candidates else 0.0,
                "risk_percent": first_leg.get("risk_percent"),
                "pnl_total_usd": round(sum(_safe_float(leg.get("usd_result")) or 0.0 for leg in legs_sorted), 2),
                "pnl_total_points": round(sum(_summary_points_value(leg) for leg in legs_sorted), 6),
                "opened_at": opened_at,
                "closed_at": closed_at,
                "duration_sec": _duration_sec(opened_at, closed_at),
                "legs_count": len(legs_sorted),
                "exit_final_reason": final_leg.get("exit_reason"),
                "score_max": round(
                    max(_safe_float(leg.get("score")) or 0.0 for leg in legs_sorted),
                    2,
                ),
                "score_avg": round(
                    sum(_safe_float(leg.get("score")) or 0.0 for leg in legs_sorted) / max(len(legs_sorted), 1),
                    2,
                ),
                "had_partial": any(str(leg.get("exit_reason") or "") == "TP1_PARTIAL" for leg in legs_sorted),
                "had_be_close": any(str(leg.get("exit_reason") or "") == "BE_CLOSE" for leg in legs_sorted),
                "had_tp2": any(str(leg.get("exit_reason") or "") == "TP2_FINAL" for leg in legs_sorted),
            }
        )

    summaries.sort(key=lambda x: str(x.get("closed_at") or x.get("opened_at") or ""))
    return summaries


def _parse_closed_from_ops(ops: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    active: Dict[str, Dict[str, Any]] = {}
    closed: List[Dict[str, Any]] = []

    for raw in ops:
        event = _event_name(raw)
        payload = _deep_payload(raw)

        symbol = payload.get("symbol") or raw.get("symbol")
        tf = payload.get("tf") or raw.get("tf")
        world = payload.get("world") or raw.get("world")
        atlas_mode = payload.get("atlas_mode") or raw.get("atlas_mode")
        side = payload.get("side") or raw.get("side")
        entry = payload.get("entry", raw.get("entry"))
        sl = payload.get("sl", raw.get("sl"))
        tp = payload.get("tp", raw.get("tp"))
        score = payload.get("score", raw.get("score"))
        lot = payload.get("lot", raw.get("lot"))
        lot_raw = payload.get("lot_raw", raw.get("lot_raw"))
        lot_capped = payload.get("lot_capped", raw.get("lot_capped"))
        lot_cap_reason = payload.get("lot_cap_reason", raw.get("lot_cap_reason"))
        ts = raw.get("ts") or payload.get("ts")

        if not symbol or not tf:
            continue

        key = _trade_key(symbol, tf, entry, side)

        if event == "ENTRY":
            active[key] = {
                "time": ts,
                "ts": ts,
                "world": world,
                "atlas_mode": atlas_mode,
                "mode": atlas_mode,
                "symbol": symbol,
                "tf": tf,
                "side": side,
                "score": score,
                "state_at_entry": "ENTRY",
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lot": lot,
                "lot_raw": lot_raw,
                "lot_capped": lot_capped,
                "lot_cap_reason": lot_cap_reason,
                "entry_price": entry,
                "tp2_price": tp,
                "sl_price": sl,
                "signal_ts": payload.get("signal_ts"),
                "entry_ts": payload.get("entry_ts"),
            }
            continue

        if event in {"IN_TRADE", "TP1", "TP2", "RUN"}:
            prev = active.get(key)
            if prev:
                prev["sl"] = sl if sl is not None else prev.get("sl")
                prev["tp"] = tp if tp is not None else prev.get("tp")
                prev["score"] = score if score is not None else prev.get("score")
                prev["lot"] = lot if lot is not None else prev.get("lot")
                prev["lot_raw"] = lot_raw if lot_raw is not None else prev.get("lot_raw")
                prev["lot_capped"] = lot_capped if lot_capped is not None else prev.get("lot_capped")
                prev["lot_cap_reason"] = lot_cap_reason if lot_cap_reason is not None else prev.get("lot_cap_reason")
            continue

        if event == "TRADE_CLOSED":
            result = payload.get("result")
            exit_price = payload.get("exit", payload.get("price"))
            pips = payload.get("pips")
            usd = payload.get("usd")

            base = active.get(key, {})
            closed.append(
                _normalize_closed_trade(
                    {
                    "time": ts,
                    "ts": ts,
                    "world": world,
                    "atlas_mode": atlas_mode,
                    "mode": atlas_mode,
                    "symbol": symbol,
                    "tf": tf,
                    "side": side or base.get("side"),
                    "score": score if score is not None else base.get("score"),
                    "state_at_entry": base.get("state_at_entry", "ENTRY"),
                    "trade_id": payload.get("trade_id"),
                    "parent_trade_id": payload.get("parent_trade_id"),
                    "leg_id": payload.get("leg_id"),
                    "is_partial": payload.get("is_partial"),
                    "partial_percent": payload.get("partial_percent"),
                    "lot": lot if lot is not None else base.get("lot"),
                    "lot_raw": lot_raw if lot_raw is not None else base.get("lot_raw"),
                    "lot_capped": lot_capped if lot_capped is not None else base.get("lot_capped"),
                    "lot_cap_reason": lot_cap_reason if lot_cap_reason is not None else base.get("lot_cap_reason"),
                    "entry_price": entry if entry is not None else base.get("entry"),
                    "tp1_price": payload.get("tp1_price"),
                    "tp2_price": tp if tp is not None else base.get("tp"),
                    "sl_price": sl if sl is not None else base.get("sl"),
                    "exit_price": exit_price,
                    "entry": entry if entry is not None else base.get("entry"),
                    "sl": sl if sl is not None else base.get("sl"),
                    "tp": tp if tp is not None else base.get("tp"),
                    "exit": exit_price,
                    "close_price": exit_price,
                    "exit_reason": payload.get("exit_reason") or result,
                    "result": result,
                    "raw_result": result,
                    "pips": pips,
                    "usd_result": usd,
                    "usd": usd,
                    "opened_at": payload.get("opened_at") or base.get("entry_ts") or base.get("signal_ts"),
                    "signal_ts": payload.get("signal_ts") or base.get("signal_ts"),
                    "entry_ts": payload.get("entry_ts") or base.get("entry_ts"),
                    "closed_at": payload.get("closed_at") or payload.get("closed_ts") or ts,
                    "closed_ts": payload.get("closed_ts") or ts,
                    }
                )
            )
            active.pop(key, None)
            continue

        if event in {"SL", "TP2", "RUN_CLOSE", "TP1_CLOSE"}:
            base = active.get(key, {})
            exit_price = payload.get("price", payload.get("exit"))

            trade = {
                "time": ts,
                "ts": ts,
                "world": world,
                "atlas_mode": atlas_mode,
                "mode": atlas_mode,
                "symbol": symbol,
                "tf": tf,
                "side": side or base.get("side"),
                "score": score if score is not None else base.get("score"),
                "state_at_entry": base.get("state_at_entry", "ENTRY"),
                "lot": lot if lot is not None else base.get("lot"),
                "lot_raw": lot_raw if lot_raw is not None else base.get("lot_raw"),
                "lot_capped": lot_capped if lot_capped is not None else base.get("lot_capped"),
                "lot_cap_reason": lot_cap_reason if lot_cap_reason is not None else base.get("lot_cap_reason"),
                "entry_price": entry if entry is not None else base.get("entry"),
                "tp2_price": tp if tp is not None else base.get("tp"),
                "sl_price": sl if sl is not None else base.get("sl"),
                "exit_price": exit_price,
                "entry": entry if entry is not None else base.get("entry"),
                "sl": sl if sl is not None else base.get("sl"),
                "tp": tp if tp is not None else base.get("tp"),
                "exit": exit_price,
                "close_price": exit_price,
                "exit_reason": event,
                "result": event,
                "raw_result": event,
                "pips": None,
                "usd_result": None,
                "usd": None,
                "opened_at": payload.get("opened_at") or base.get("entry_ts") or base.get("signal_ts"),
                "signal_ts": payload.get("signal_ts") or base.get("signal_ts"),
                "entry_ts": payload.get("entry_ts") or base.get("entry_ts"),
                "closed_at": payload.get("closed_at") or payload.get("closed_ts") or ts,
                "closed_ts": payload.get("closed_ts") or ts,
            }

            entry_f = _safe_float(trade.get("entry"))
            exit_f = _safe_float(trade.get("exit"))
            side_s = str(trade.get("side") or "").upper()
            lot_f = _safe_float(lot if lot is not None else base.get("lot"))

            if entry_f is not None and exit_f is not None and side_s in {"BUY", "SELL"}:
                pips = _calc_fallback_pips(str(symbol), entry_f, exit_f, side_s)
                usd = _calc_fallback_usd(str(symbol), pips, lot_f)
                trade["pips"] = round(pips, 2)
                trade["usd_result"] = round(usd, 2)
                trade["usd"] = round(usd, 2)

            closed.append(_normalize_closed_trade(trade))
            active.pop(key, None)

    closed = _dedupe_closed(closed)
    return closed[-limit:]


def _get_closed_items(
    *,
    limit: int,
    world: Optional[str],
    atlas_mode: Optional[str],
    symbol: Optional[str],
    from_ts: Optional[str],
    to_ts: Optional[str],
) -> Tuple[str, List[Dict[str, Any]]]:
    fetch_limit = 5000 if (world or atlas_mode or symbol or from_ts or to_ts) else limit
    closed_runtime = runtime.get_closed_trades(fetch_limit)
    normalized_runtime = [_normalize_closed_trade(x) for x in closed_runtime if isinstance(x, dict)]
    normalized_runtime = _dedupe_closed(normalized_runtime)
    if world or atlas_mode or symbol or from_ts or to_ts:
        normalized_runtime = [
            x for x in normalized_runtime
            if _matches_filters(x, world, atlas_mode, symbol, from_ts, to_ts)
        ]

    if normalized_runtime:
        return "runtime_closed_trades", normalized_runtime[-limit:]

    ops = runtime.get_ops_log(2000)
    rebuilt = _parse_closed_from_ops(ops, fetch_limit)
    if world or atlas_mode or symbol or from_ts or to_ts:
        rebuilt = [
            x for x in rebuilt
            if _matches_filters(x, world, atlas_mode, symbol, from_ts, to_ts)
        ]
    return "rebuilt_from_ops", rebuilt[-limit:]


@router.get("/ops")
def get_ops(
    limit: int = Query(default=200, ge=1, le=2000),
    world: Optional[str] = Query(default=None),
    atlas_mode: Optional[str] = Query(default=None),
    mode: Optional[str] = Query(default=None),
) -> dict:
    world_f, atlas_mode_f = _resolve_filters(world, atlas_mode, mode)
    items = [_normalize_ops_item(x) for x in runtime.get_ops_log(2000)]
    if world_f or atlas_mode_f:
        items = [x for x in items if _matches_filters(x, world_f, atlas_mode_f)]
    return {
        "ok": True,
        "count": len(items[-limit:]),
        "items": items[-limit:],
    }


@router.get("/tail")
def get_tail(
    limit: int = Query(default=50, ge=1, le=500),
    world: Optional[str] = Query(default=None),
    atlas_mode: Optional[str] = Query(default=None),
    mode: Optional[str] = Query(default=None),
) -> dict:
    world_f, atlas_mode_f = _resolve_filters(world, atlas_mode, mode)
    items = [_normalize_ops_item(x) for x in runtime.get_ops_log(2000)]
    if world_f or atlas_mode_f:
        items = [x for x in items if _matches_filters(x, world_f, atlas_mode_f)]
    tail = items[-limit:]
    return {
        "ok": True,
        "count": len(tail),
        "items": tail,
    }


@router.get("/closed")
def get_closed(
    limit: int = Query(default=200, ge=1, le=2000),
    world: Optional[str] = Query(default=None),
    atlas_mode: Optional[str] = Query(default=None),
    mode: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    from_ts: Optional[str] = Query(default=None),
    to_ts: Optional[str] = Query(default=None),
) -> dict:
    world_f, atlas_mode_f = _resolve_filters(world, atlas_mode, mode)
    source, items = _get_closed_items(
        limit=limit,
        world=world_f,
        atlas_mode=atlas_mode_f,
        symbol=symbol,
        from_ts=from_ts,
        to_ts=to_ts,
    )
    summaries = _rebuild_trade_summaries(items)
    return {
        "ok": True,
        "source": source,
        "count": len(items),
        "items": items,
        "metrics_summary": _metrics_summary(summaries),
    }


@router.get("/summary")
def get_summary(
    limit: int = Query(default=200, ge=1, le=5000),
    world: Optional[str] = Query(default=None),
    atlas_mode: Optional[str] = Query(default=None),
    mode: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    from_ts: Optional[str] = Query(default=None),
    to_ts: Optional[str] = Query(default=None),
) -> dict:
    world_f, atlas_mode_f = _resolve_filters(world, atlas_mode, mode)
    _, closed_items = _get_closed_items(
        limit=5000,
        world=world_f,
        atlas_mode=atlas_mode_f,
        symbol=symbol,
        from_ts=from_ts,
        to_ts=to_ts,
    )
    items = [_normalize_trade_summary(x) for x in _rebuild_trade_summaries(closed_items)]
    return {
        "ok": True,
        "count": len(items[-limit:]),
        "items": items[-limit:],
        "metrics_summary": _metrics_summary(items[-limit:]),
    }


@router.get("/export")
def export_closed(
    world: Optional[str] = Query(default=None),
    atlas_mode: Optional[str] = Query(default=None),
    mode: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    from_ts: Optional[str] = Query(default=None),
    to_ts: Optional[str] = Query(default=None),
    limit: int = Query(default=5000, ge=1, le=10000),
    format: str = Query(default="csv"),
):
    world_f, atlas_mode_f = _resolve_filters(world, atlas_mode, mode)
    payload = get_closed(
        limit=limit,
        world=world_f,
        atlas_mode=atlas_mode_f,
        symbol=symbol,
        from_ts=from_ts,
        to_ts=to_ts,
    )
    items = payload.get("items") or []

    filename_parts = ["atlas_bitacora"]
    if world_f:
        filename_parts.append(str(world_f).lower())
    if atlas_mode_f:
        filename_parts.append(str(atlas_mode_f).lower())
    filename = "_".join(filename_parts)
    fmt = str(format or "csv").lower().strip()

    if fmt == "json":
        return JSONResponse(payload)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TRADE_EXPORT_FIELDS)
    writer.writeheader()
    for item in items:
        writer.writerow({key: item.get(key) for key in TRADE_EXPORT_FIELDS})

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )


@router.get("/summary/export")
def export_summary(
    world: Optional[str] = Query(default=None),
    atlas_mode: Optional[str] = Query(default=None),
    mode: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    from_ts: Optional[str] = Query(default=None),
    to_ts: Optional[str] = Query(default=None),
    limit: int = Query(default=5000, ge=1, le=10000),
    format: str = Query(default="csv"),
):
    world_f, atlas_mode_f = _resolve_filters(world, atlas_mode, mode)
    payload = get_summary(
        limit=limit,
        world=world_f,
        atlas_mode=atlas_mode_f,
        symbol=symbol,
        from_ts=from_ts,
        to_ts=to_ts,
    )
    items = payload.get("items") or []

    filename_parts = ["atlas_trade_summary"]
    if world_f:
        filename_parts.append(str(world_f).lower())
    if atlas_mode_f:
        filename_parts.append(str(atlas_mode_f).lower())
    filename = "_".join(filename_parts)
    fmt = str(format or "csv").lower().strip()

    if fmt == "json":
        return JSONResponse(payload)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=SUMMARY_EXPORT_FIELDS)
    writer.writeheader()
    for item in items:
        writer.writerow({key: item.get(key) for key in SUMMARY_EXPORT_FIELDS})

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )
