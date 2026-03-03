from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import time
import uuid
import hashlib

from atlas.bot.state import (
    get_world_state,
    PHASE_WAIT,
    PHASE_ZONA,
    PHASE_GATILLO,
)

# Bitácora (Opción B)
try:
    from atlas.bot.bitacora.engine import process_snapshot_for_bitacora  # type: ignore
except Exception:
    process_snapshot_for_bitacora = None  # type: ignore


# ============================================================
# Utils
# ============================================================
def _now_ms() -> int:
    return int(time.time() * 1000)


def _f(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _s(x: Any, default: str = "") -> str:
    try:
        return str(x)
    except Exception:
        return default


def _normalize_side(side: Any) -> str:
    s = _s(side, "").upper().strip()
    return s if s in ("BUY", "SELL") else "WAIT"


def _normalize_tf(tf: str) -> str:
    t = (tf or "").upper().strip()
    return t or "M1"


def _normalize_candles(raw: Any) -> List[Dict[str, Any]]:
    """
    Siempre: [{t,o,h,l,c,v}, ...]
    """
    if raw is None:
        return []

    if isinstance(raw, dict) and "candles" in raw:
        raw = raw.get("candles")

    if not isinstance(raw, list):
        return []

    out: List[Dict[str, Any]] = []
    for c in raw:
        if not isinstance(c, dict):
            continue
        t = c.get("t", c.get("time", 0))
        o = c.get("o", c.get("open", 0))
        h = c.get("h", c.get("high", 0))
        l = c.get("l", c.get("low", 0))
        cl = c.get("c", c.get("close", 0))
        v = c.get("v", c.get("tick_volume", c.get("volume", 0)))
        out.append({"t": int(_f(t, 0)), "o": _f(o), "h": _f(h), "l": _f(l), "c": _f(cl), "v": _f(v)})
    return out


def _last_close(candles: List[Dict[str, Any]]) -> float:
    return _f(candles[-1].get("c"), 0.0) if candles else 0.0


def _plan_hash(symbol: str, tf: str, side: str, zlo: float, zhi: float) -> str:
    s = f"{symbol}|{tf}|{side}|{zlo:.6f}|{zhi:.6f}"
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]


def _ensure_attrs(obj: Any, **defaults: Any) -> None:
    """
    No asumimos qué trae WorldState; si le faltan attrs, los creamos.
    """
    for k, v in defaults.items():
        if not hasattr(obj, k):
            try:
                setattr(obj, k, v)
            except Exception:
                pass


# ============================================================
# Provider (MT5/Fake) - fallback seguro
# ============================================================
def _get_candles(symbol: str, tf: str, count: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Optional[str]]:
    """
    Retorna: (candles, meta, error_str)
    """
    try:
        from atlas.api.routes.mt5_provider import get_candles_payload  # type: ignore

        data = get_candles_payload(world="ATLAS_IA", symbol=symbol, tf=tf, count=count)
        candles = _normalize_candles(data)
        meta = {"source": "mt5_provider"}
        return candles, meta, None
    except Exception as e1:
        try:
            from atlas.bot.worlds.feed import get_feed_with_meta  # type: ignore

            candles2, meta2 = get_feed_with_meta(symbol=symbol, tf=tf, n=count)
            candles2 = _normalize_candles(candles2)
            meta2 = meta2 if isinstance(meta2, dict) else {}
            meta2["source"] = "feed"
            return candles2, meta2, None
        except Exception as e2:
            return [], {"source": "none"}, f"{type(e1).__name__}: {e1} | {type(e2).__name__}: {e2}"


# ============================================================
# Motores (simple, estable)
# Estados: WAIT / WAIT_GATILLO / SIGNAL
#
# Internamente:
#   PHASE_WAIT      -> "WAIT"
#   PHASE_ZONA      -> "WAIT_GATILLO"  (plan congelado)
#   PHASE_GATILLO   -> "SIGNAL"
# ============================================================
def _engine_scalping(symbol: str, tf: str, candles: List[Dict[str, Any]], *, st: Any) -> Dict[str, Any]:
    _ensure_attrs(st, phase=PHASE_WAIT, last_note="")
    _ensure_attrs(st, plan=type("Plan", (), {})())
    _ensure_attrs(st, signal=type("Signal", (), {})())

    _ensure_attrs(st.plan, bias="WAIT", zone_lo=0.0, zone_hi=0.0, note="", plan_hash="")
    _ensure_attrs(st.signal, side="WAIT", entry=0.0, sl=0.0, tp=0.0, signal_id="")

    if len(candles) < 30:
        st.phase = PHASE_WAIT
        return {
            "phase": PHASE_WAIT,
            "side": "WAIT",
            "reason": "NOT_ENOUGH_CANDLES",
            "note": "historial corto",
            "plan_hash": "",
            "entry": 0.0,
            "sl": 0.0,
            "tp": 0.0,
        }

    closes = [_f(c.get("c"), 0.0) for c in candles[-30:]]
    highs = [_f(c.get("h"), 0.0) for c in candles[-30:]]
    lows = [_f(c.get("l"), 0.0) for c in candles[-30:]]

    if not closes or not highs or not lows:
        st.phase = PHASE_WAIT
        return {
            "phase": PHASE_WAIT,
            "side": "WAIT",
            "reason": "INCOMPLETE_DATA",
            "note": "datos incompletos",
            "plan_hash": "",
            "entry": 0.0,
            "sl": 0.0,
            "tp": 0.0,
        }

    price = closes[-1]

    # --------------------------------------------------------
    # ✅ 4.2: si YA estamos en WAIT_GATILLO, NO recalcular plan.
    # --------------------------------------------------------
    if st.phase == PHASE_ZONA and st.plan.zone_lo and st.plan.zone_hi and st.plan.bias in ("BUY", "SELL"):
        zlo = float(st.plan.zone_lo)
        zhi = float(st.plan.zone_hi)
        side = str(st.plan.bias)

        in_zone = (zlo <= price <= zhi)

        # gatillo: 2 cierres seguidos fuera a favor (igual que antes)
        c1 = closes[-2]
        c2 = closes[-1]
        fired = False
        if side == "BUY":
            fired = (c1 > zhi) and (c2 > zhi) and (not in_zone)
        else:
            fired = (c1 < zlo) and (c2 < zlo) and (not in_zone)

        if fired:
            entry = float(c2)
            if side == "BUY":
                sl = float(zlo)
                tp = float(entry + (entry - sl) * 1.5)
            else:
                sl = float(zhi)
                tp = float(entry - (sl - entry) * 1.5)

            st.signal.side = side
            st.signal.entry = entry
            st.signal.sl = sl
            st.signal.tp = tp
            st.signal.signal_id = st.signal.signal_id or str(uuid.uuid4())[:8]

            st.plan.note = "plan congelado, gatillo confirmado"
            st.last_note = "SIGNAL"
            st.phase = PHASE_GATILLO

            return {
                "phase": PHASE_GATILLO,
                "side": side,
                "reason": "TRIGGER_OK",
                "note": "SIGNAL: 2 cierres confirmatorios",
                "plan_hash": str(st.plan.plan_hash or ""),
                "entry": entry,
                "sl": sl,
                "tp": tp,
            }

        # seguimos esperando gatillo, plan congelado
        st.last_note = "WAIT_GATILLO"
        return {
            "phase": PHASE_ZONA,
            "side": side,
            "reason": "WAITING_TRIGGER",
            "note": "WAIT_GATILLO: plan congelado",
            "plan_hash": str(st.plan.plan_hash or ""),
            "entry": 0.0,
            "sl": 0.0,
            "tp": 0.0,
        }

    # --------------------------------------------------------
    # Si NO hay plan congelado, calculamos zona NUEVA (solo aquí)
    # --------------------------------------------------------
    hi = max(highs)
    lo = min(lows)
    rng = hi - lo
    if rng <= 0:
        st.phase = PHASE_WAIT
        return {
            "phase": PHASE_WAIT,
            "side": "WAIT",
            "reason": "RANGE_ZERO",
            "note": "rango nulo",
            "plan_hash": "",
            "entry": 0.0,
            "sl": 0.0,
            "tp": 0.0,
        }

    zlo = lo + rng * 0.40
    zhi = lo + rng * 0.60

    drift = closes[-1] - closes[0]
    side = "BUY" if drift > 0 else "SELL" if drift < 0 else "WAIT"

    in_zone = (zlo <= price <= zhi)

    # si entra en zona: congelamos plan => WAIT_GATILLO
    if in_zone and side in ("BUY", "SELL"):
        st.plan.bias = side
        st.plan.zone_lo = float(zlo)
        st.plan.zone_hi = float(zhi)
        st.plan.plan_hash = _plan_hash(symbol, tf, side, float(zlo), float(zhi))
        st.plan.note = "plan congelado (zona detectada)"
        st.last_note = "WAIT_GATILLO"
        st.phase = PHASE_ZONA  # internamente ZONA

        return {
            "phase": PHASE_ZONA,
            "side": side,
            "reason": "PLAN_FROZEN",
            "note": "WAIT_GATILLO: plan congelado",
            "plan_hash": str(st.plan.plan_hash or ""),
            "entry": 0.0,
            "sl": 0.0,
            "tp": 0.0,
        }

    # si no está en zona: WAIT normal
    st.phase = PHASE_WAIT
    st.plan.bias = side  # informativo, NO congelado
    st.plan.note = "esperando zona"
    st.last_note = "WAIT"
    return {
        "phase": PHASE_WAIT,
        "side": side,
        "reason": "WAITING_ZONE",
        "note": "WAIT: fuera de zona",
        "plan_hash": "",
        "entry": 0.0,
        "sl": 0.0,
        "tp": 0.0,
    }


def _engine_forex(symbol: str, tf: str, candles: List[Dict[str, Any]], *, st: Any) -> Dict[str, Any]:
    return _engine_scalping(symbol, tf, candles, st=st)


def _public_state(phase: str) -> str:
    if phase == PHASE_ZONA:
        return "WAIT_GATILLO"
    if phase == PHASE_GATILLO:
        return "SIGNAL"
    return "WAIT"


# ============================================================
# Build snapshot (único)
# ============================================================
def build_snapshot(
    *,
    world: str,
    atlas_mode: Optional[str] = None,
    symbol: str,
    tf: str,
    count: int = 220,
) -> Dict[str, Any]:
    world_u = (world or "").upper().strip()
    mode_u = (atlas_mode or "").upper().strip() if atlas_mode else None
    tf_u = _normalize_tf(tf)

    candles, meta, err = _get_candles(symbol=symbol, tf=tf_u, count=count)
    ts = _now_ms()

    if err:
        payload = {
            "world": world_u,
            "atlas_mode": mode_u,
            "symbol": symbol,
            "tf": tf_u,
            "ts_ms": ts,
            "candles": [],
            "analysis": {"status": "NO_TRADE", "reason": "CANDLES_ERROR", "detail": err},
            "ui": {"rows": [{"k": "Estado", "v": "WAIT"}, {"k": "Reason", "v": "CANDLES_ERROR"}], "meta": {"note": "candles_error"}},
        }
        if process_snapshot_for_bitacora is not None:
            try:
                process_snapshot_for_bitacora(payload)
            except Exception:
                pass
        return payload

    st = get_world_state(world=world_u, atlas_mode=mode_u, symbol=symbol, tf=tf_u)

    decision: Dict[str, Any]
    if world_u == "ATLAS_IA":
        if mode_u in ("SCALPING_M1", "SCALPING_M5"):
            decision = _engine_scalping(symbol, tf_u, candles, st=st)
        elif mode_u == "FOREX":
            decision = _engine_forex(symbol, tf_u, candles, st=st)
        else:
            decision = {"phase": PHASE_WAIT, "side": "WAIT", "reason": "INVALID_ATLAS_MODE", "note": "atlas_mode inválido", "plan_hash": "", "entry": 0.0, "sl": 0.0, "tp": 0.0}
    else:
        decision = {"phase": PHASE_WAIT, "side": "WAIT", "reason": "NO_ENGINE_FOR_WORLD", "note": "world sin motor", "plan_hash": "", "entry": 0.0, "sl": 0.0, "tp": 0.0}

    phase_internal = decision.get("phase", PHASE_WAIT)
    state_public = _public_state(phase_internal)

    side = _normalize_side(decision.get("side", "WAIT"))
    reason = _s(decision.get("reason", ""), "NO_REASON")
    note = _s(decision.get("note", ""), "")
    plan_hash = _s(decision.get("plan_hash", ""), "")

    price = _last_close(candles)
    entry = float(_f(decision.get("entry", 0.0), 0.0))
    sl = float(_f(decision.get("sl", 0.0), 0.0))
    tp = float(_f(decision.get("tp", 0.0), 0.0))

    status = "SIGNAL" if state_public == "SIGNAL" and side in ("BUY", "SELL") and entry > 0 and sl > 0 and tp > 0 else "NO_TRADE"

    payload: Dict[str, Any] = {
        "world": world_u,
        "atlas_mode": mode_u,
        "symbol": symbol,
        "tf": tf_u,
        "ts_ms": ts,
        "candles": candles,
        "meta": meta or {},
        "price": float(price),

        "state": state_public,
        "side": side,

        "entry": 0.0,
        "sl": 0.0,
        "tp": 0.0,
        "trade": None,

        "analysis": {
            "world": world_u,
            "atlas_mode": mode_u,
            "symbol": symbol,
            "tf": tf_u,
            "status": status,
            "state": state_public,
            "side": side,
            "reason": reason,
            "note": note,
            "plan_hash": plan_hash,
            "entry": 0.0,
            "sl": 0.0,
            "tp": 0.0,
        },
        "ui": {
            "rows": [
                {"k": "Estado", "v": state_public},
                {"k": "Lado", "v": side},
                {"k": "Precio", "v": float(price)},
                {"k": "Reason", "v": reason},
                {"k": "Nota", "v": note},
                {"k": "PlanHash", "v": plan_hash},
            ],
            "meta": {"plan_hash": plan_hash},
        },
    }

    if status == "SIGNAL":
        payload["entry"] = entry
        payload["sl"] = sl
        payload["tp"] = tp
        payload["trade"] = {"side": side, "entry": entry, "sl": sl, "tp": tp}
        payload["analysis"]["entry"] = entry
        payload["analysis"]["sl"] = sl
        payload["analysis"]["tp"] = tp

    if process_snapshot_for_bitacora is not None:
        try:
            process_snapshot_for_bitacora(payload)
        except Exception:
            pass

    return payload