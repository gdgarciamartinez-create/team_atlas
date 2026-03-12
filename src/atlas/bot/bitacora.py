from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, List

DEFAULT_PATH = os.path.join("data", "bitacora.jsonl")


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _mt5():
    try:
        import MetaTrader5 as mt5  # type: ignore
        return mt5
    except Exception:
        return None


def _mt5_init() -> bool:
    mt5 = _mt5()
    if mt5 is None:
        return False
    try:
        return bool(mt5.initialize())
    except Exception:
        return False


def get_value_per_point_per_lot(symbol: str) -> Optional[float]:
    mt5 = _mt5()
    if mt5 is None:
        return None
    if not _mt5_init():
        return None
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        tick_value = float(getattr(info, "trade_tick_value", 0.0) or 0.0)
        tick_size = float(getattr(info, "trade_tick_size", 0.0) or 0.0)
        point = float(getattr(info, "point", 0.0) or 0.0)
        if tick_value > 0 and tick_size > 0 and point > 0:
            return tick_value * (point / tick_size)
        return None
    except Exception:
        return None


def get_point(symbol: str) -> Optional[float]:
    mt5 = _mt5()
    if mt5 is None:
        return None
    if not _mt5_init():
        return None
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        p = float(getattr(info, "point", 0.0) or 0.0)
        return p if p > 0 else None
    except Exception:
        return None


def calc_pnl_usd(symbol: str, entry: float, exit_price: float, lot: float, side: str) -> Tuple[Optional[float], Optional[float]]:
    point = get_point(symbol)
    vpp = get_value_per_point_per_lot(symbol)
    if point is None or vpp is None or point <= 0 or vpp <= 0:
        return None, None

    side_u = (side or "").upper()
    signed = (exit_price - entry) if side_u == "BUY" else (entry - exit_price)
    signed_points = signed / point

    pnl = signed_points * vpp * lot
    return float(pnl), float(signed_points)


def calc_r_multiple(entry: float, sl: float, exit_price: float, side: str) -> Optional[float]:
    risk = abs(entry - sl)
    if risk <= 1e-12:
        return None
    side_u = (side or "").upper()
    signed = (exit_price - entry) if side_u == "BUY" else (entry - exit_price)
    return float(signed / risk)


@dataclass
class BitacoraEvent:
    ts: str
    kind: str
    symbol: str
    tf: str
    atlas_mode: str
    state: str
    reason: str

    side: Optional[str] = None
    trigger: Optional[str] = None
    signal_id: Optional[str] = None

    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None

    exit: Optional[float] = None
    lot: Optional[float] = None

    pnl_usd: Optional[float] = None
    move_points: Optional[float] = None
    r_multiple: Optional[float] = None

    note: Optional[str] = None


class Bitacora:
    def __init__(self, path: str = DEFAULT_PATH) -> None:
        self.path = path
        _ensure_dir(self.path)

    def append(self, ev: BitacoraEvent) -> None:
        _ensure_dir(self.path)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(ev), ensure_ascii=False) + "\n")

    def tail(self, n: int = 50) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            lines = lines[-max(1, int(n)):]
            out: List[Dict[str, Any]] = []
            for ln in lines:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    out.append(json.loads(ln))
                except Exception:
                    continue
            return out
        except Exception:
            return []

    def log_signal(self, payload: Dict[str, Any], note: Optional[str] = None) -> None:
        rows = payload.get("ui", {}).get("rows", None)
        row = rows[0] if isinstance(rows, list) and rows else payload

        ev = BitacoraEvent(
            ts=_now_iso(),
            kind="SIGNAL",
            symbol=str(row.get("symbol", "")),
            tf=str(row.get("tf", "")),
            atlas_mode=str(payload.get("atlas_mode") or "SCALPING"),
            state=str(row.get("state", "SIGNAL")),
            reason=str(row.get("reason", "SIGNAL")),
            side=row.get("side"),
            trigger=row.get("trigger"),
            signal_id=row.get("signal_id"),
            entry=_safe_float(row.get("entry")),
            sl=_safe_float(row.get("sl")),
            tp=_safe_float(row.get("tp")),
            note=note,
        )
        self.append(ev)

    def log_no_trade(self, payload: Dict[str, Any], note: Optional[str] = None) -> None:
        rows = payload.get("ui", {}).get("rows", None)
        row = rows[0] if isinstance(rows, list) and rows else payload

        ev = BitacoraEvent(
            ts=_now_iso(),
            kind="NO_TRADE",
            symbol=str(row.get("symbol", "")),
            tf=str(row.get("tf", "")),
            atlas_mode=str(payload.get("atlas_mode") or "SCALPING"),
            state=str(row.get("state", "WAIT")),
            reason=str(row.get("reason", "NO_TRADE")),
            note=note,
        )
        self.append(ev)

    def log_exit(self, symbol: str, tf: str, atlas_mode: str, side: str, entry: float, sl: float, exit_price: float, lot: float, signal_id: Optional[str] = None, note: Optional[str] = None) -> Dict[str, Any]:
        pnl_usd, move_points = calc_pnl_usd(symbol, entry, exit_price, lot, side)
        r_mult = calc_r_multiple(entry, sl, exit_price, side)

        ev = BitacoraEvent(
            ts=_now_iso(),
            kind="EXIT",
            symbol=symbol,
            tf=tf,
            atlas_mode=atlas_mode,
            state="EXIT",
            reason="MANUAL_EXIT",
            side=side,
            signal_id=signal_id,
            entry=float(entry),
            sl=float(sl),
            exit=float(exit_price),
            lot=float(lot),
            pnl_usd=pnl_usd,
            move_points=move_points,
            r_multiple=r_mult,
            note=note,
        )
        self.append(ev)
        return asdict(ev)