from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

# =========================
# Config
# =========================
MAX_GLOBAL = 200
MAX_PER_WORLD = 200
MAX_EVENTS = 400

# Estados internos bitácora
STATUS_OPEN = "OPEN"
STATUS_CLOSED = "CLOSED"

# Close / event types
EV_ENTRY = "ENTRY"
EV_PARTIAL = "PARTIAL"
EV_TP = "TP"
EV_SL = "SL"
EV_MANUAL = "MANUAL"

CLOSE_TP = "TP"
CLOSE_SL = "SL"
CLOSE_MANUAL = "MANUAL"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _safe_str(x: Any, default: str = "") -> str:
    try:
        return str(x)
    except Exception:
        return default


def _normalize_side(side: Any) -> str:
    s = _safe_str(side, "").upper().strip()
    if s in ("BUY", "SELL"):
        return s
    return "WAIT"


@dataclass
class PaperEvent:
    id: str
    ts_ms: int
    world: str
    symbol: str
    tf: str
    trade_id: str
    type: str  # ENTRY | PARTIAL | TP | SL | MANUAL
    price: float
    note: str


@dataclass
class PaperTrade:
    id: str
    ts_open_ms: int
    world: str
    symbol: str
    tf: str
    side: str  # BUY/SELL
    entry: float
    sl: float
    tp1: float
    tp2: float
    status: str  # OPEN/CLOSED
    partial_done: bool
    close_reason: str
    ts_close_ms: int
    close_price: float
    pnl_points: float
    note: str


# In-memory store
_OPEN: Dict[str, PaperTrade] = {}
_CLOSED: List[PaperTrade] = []
_EVENTS: List[PaperEvent] = []


def _key(world: str, symbol: str, tf: str) -> str:
    return f"{world}::{symbol}::{tf}"


def _push_event(world: str, symbol: str, tf: str, trade_id: str, ev_type: str, price: float, note: str = "") -> None:
    global _EVENTS
    e = PaperEvent(
        id=str(uuid.uuid4())[:10],
        ts_ms=_now_ms(),
        world=world,
        symbol=symbol,
        tf=tf,
        trade_id=trade_id,
        type=ev_type,
        price=float(price),
        note=_safe_str(note, "")[:240],
    )
    _EVENTS.append(e)
    if len(_EVENTS) > MAX_EVENTS:
        _EVENTS = _EVENTS[-MAX_EVENTS:]


def _trim_limits() -> None:
    """Mantiene límites globales y por mundo."""
    global _CLOSED

    if len(_CLOSED) > MAX_GLOBAL:
        _CLOSED = _CLOSED[-MAX_GLOBAL:]

    # per-world trimming (closed list)
    per: Dict[str, List[PaperTrade]] = {}
    for t in _CLOSED:
        per.setdefault(t.world, []).append(t)

    new_closed: List[PaperTrade] = []
    for w, arr in per.items():
        if len(arr) > MAX_PER_WORLD:
            arr = arr[-MAX_PER_WORLD:]
        new_closed.extend(arr)

    # orden por ts_close_ms
    new_closed.sort(key=lambda x: x.ts_close_ms)
    _CLOSED = new_closed[-MAX_GLOBAL:]


def _extract_trade_plan(snapshot: Dict[str, Any]) -> Optional[Tuple[str, float, float, float, float]]:
    """
    Busca un plan de trade en snapshot.
    Acepta:
      - snapshot["trade"] con {"entry","sl","tp","side"}  (tp=tp1)
      - snapshot plano con entry/sl/tp
      - si existe signal.tp2 lo toma como TP2
    """
    if not isinstance(snapshot, dict):
        return None

    side = _normalize_side(snapshot.get("side"))

    # tp2 si viene en signal
    tp2_from_signal = 0.0
    sig = snapshot.get("signal")
    if isinstance(sig, dict):
        tp2_from_signal = _safe_float(sig.get("tp2"), 0.0)

    trade = snapshot.get("trade")
    if isinstance(trade, dict):
        entry = _safe_float(trade.get("entry"), 0.0)
        sl = _safe_float(trade.get("sl"), 0.0)
        tp1 = _safe_float(trade.get("tp"), 0.0)
        tside = _normalize_side(trade.get("side", side))
        if entry > 0 and sl > 0 and tp1 > 0 and tside in ("BUY", "SELL"):
            tp2 = tp2_from_signal if tp2_from_signal > 0 else tp1
            return tside, entry, sl, tp1, tp2

    entry = _safe_float(snapshot.get("entry"), 0.0)
    sl = _safe_float(snapshot.get("sl"), 0.0)
    tp1 = _safe_float(snapshot.get("tp"), 0.0)
    if entry > 0 and sl > 0 and tp1 > 0 and side in ("BUY", "SELL"):
        tp2 = tp2_from_signal if tp2_from_signal > 0 else tp1
        return side, entry, sl, tp1, tp2

    return None


def _extract_price(snapshot: Dict[str, Any]) -> float:
    return _safe_float(snapshot.get("price"), 0.0)


def open_trade_from_snapshot(world: str, snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Abre trade paper SOLO si:
      - snapshot["state"] == "SIGNAL"
      - hay entry/sl/tp1 válidos
      - no hay uno abierto para (world,symbol,tf)
    Registra evento ENTRY.
    """
    if not isinstance(snapshot, dict):
        return None

    state = _safe_str(snapshot.get("state"), "").upper().strip()
    if state != "SIGNAL":
        return None

    symbol = _safe_str(snapshot.get("symbol"), "")
    tf = _safe_str(snapshot.get("tf"), "")
    if not symbol or not tf:
        return None

    plan = _extract_trade_plan(snapshot)
    if not plan:
        return None

    side, entry, sl, tp1, tp2 = plan

    k = _key(world, symbol, tf)
    if k in _OPEN:
        return asdict(_OPEN[k])

    t = PaperTrade(
        id=str(uuid.uuid4())[:8],
        ts_open_ms=_now_ms(),
        world=world,
        symbol=symbol,
        tf=tf,
        side=side,
        entry=float(entry),
        sl=float(sl),
        tp1=float(tp1),
        tp2=float(tp2 if tp2 > 0 else tp1),
        status=STATUS_OPEN,
        partial_done=False,
        close_reason="",
        ts_close_ms=0,
        close_price=0.0,
        pnl_points=0.0,
        note=_safe_str(snapshot.get("note"), "auto"),
    )
    _OPEN[k] = t

    # EVENT: ENTRY (tomamos entry como precio evento, aunque el mercado esté en otro)
    _push_event(world, symbol, tf, t.id, EV_ENTRY, float(entry), note=t.note)

    return asdict(t)


def _hit_tp(side: str, price: float, tp: float) -> bool:
    if price <= 0 or tp <= 0:
        return False
    return (price >= tp) if side == "BUY" else (price <= tp)


def _hit_sl(side: str, price: float, sl: float) -> bool:
    if price <= 0 or sl <= 0:
        return False
    return (price <= sl) if side == "BUY" else (price >= sl)


def update_open_trades_with_snapshot(world: str, snapshot: Dict[str, Any]) -> None:
    """
    Actualiza trade abierto con el precio actual.
    - Registra PARTIAL cuando toca TP1 si existe TP2 != TP1 y partial_done=False.
    - Cierra por TP2/SL.
    """
    if not isinstance(snapshot, dict):
        return

    symbol = _safe_str(snapshot.get("symbol"), "")
    tf = _safe_str(snapshot.get("tf"), "")
    if not symbol or not tf:
        return

    k = _key(world, symbol, tf)
    t = _OPEN.get(k)
    if not t:
        return

    price = _extract_price(snapshot)
    if price <= 0:
        return

    # 1) PARTIAL
    has_tp2 = (t.tp2 > 0) and (abs(t.tp2 - t.tp1) > 1e-9)
    if has_tp2 and (not t.partial_done) and _hit_tp(t.side, price, t.tp1):
        t.partial_done = True
        _push_event(world, symbol, tf, t.id, EV_PARTIAL, float(price), note="TP1 alcanzado (parcial)")

    # 2) SL (siempre manda)
    if _hit_sl(t.side, price, t.sl):
        t.status = STATUS_CLOSED
        t.close_reason = CLOSE_SL
        t.ts_close_ms = _now_ms()
        t.close_price = float(price)
        t.pnl_points = (price - t.entry) if t.side == "BUY" else (t.entry - price)

        _CLOSED.append(t)
        _OPEN.pop(k, None)

        _push_event(world, symbol, tf, t.id, EV_SL, float(price), note="SL alcanzado")
        _trim_limits()
        return

    # 3) TP final (TP2 si existe, si no TP1)
    final_tp = t.tp2 if has_tp2 else t.tp1
    if _hit_tp(t.side, price, final_tp):
        t.status = STATUS_CLOSED
        t.close_reason = CLOSE_TP
        t.ts_close_ms = _now_ms()
        t.close_price = float(price)
        t.pnl_points = (price - t.entry) if t.side == "BUY" else (t.entry - price)

        _CLOSED.append(t)
        _OPEN.pop(k, None)

        _push_event(world, symbol, tf, t.id, EV_TP, float(price), note="TP alcanzado")
        _trim_limits()
        return


def get_bitacora_payload() -> Dict[str, Any]:
    """
    Payload “limpio” para UI.
    Incluye eventos recientes (ENTRY/PARTIAL/TP/SL).
    """
    open_list = [asdict(x) for x in _OPEN.values()]
    closed_list = [asdict(x) for x in _CLOSED]
    events_list = [asdict(x) for x in _EVENTS]

    return {
        "open": open_list,
        "closed": closed_list,
        "events": events_list,
        "stats": {
            "open": len(open_list),
            "closed": len(closed_list),
            "events": len(events_list),
            "max_global": MAX_GLOBAL,
            "max_per_world": MAX_PER_WORLD,
            "max_events": MAX_EVENTS,
        },
    }


def build_bitacora_world(symbol: str, tf: str, candles: List[Dict[str, Any]], meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    World BITACORA snapshot estándar: incluye candles del símbolo (para chart)
    + bitácora global.
    """
    last_price = 0.0
    if isinstance(meta, dict):
        last_price = _safe_float(meta.get("last_price"), 0.0)

    return {
        "ok": True,
        "world": "BITACORA",
        "symbol": symbol,
        "tf": tf,
        "ts_ms": _now_ms(),
        "candles": candles or [],
        "meta": meta or {},
        "state": "WAIT",
        "side": "WAIT",
        "price": float(last_price),
        "zone": (0.0, 0.0),
        "note": "bitácora (auto)",
        "score": 0,
        "light": "GRAY",
        "bitacora": get_bitacora_payload(),
    }