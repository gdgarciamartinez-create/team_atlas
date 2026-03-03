# src/atlas/bot/decision_engine.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import math
import hashlib
import json

from atlas.bot.state import get_plan, set_plan, clear_plan


# =========================
# Helpers deterministas
# =========================

def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _hash_candles(candles: List[Dict[str, Any]], take_last: int = 120) -> str:
    """
    Hash determinista del input.
    Si el feed no cambia, el hash no cambia.
    """
    tail = candles[-take_last:] if len(candles) > take_last else candles
    payload = [
        {
            "t": int(c.get("t", 0)),
            "o": round(_safe_float(c.get("o")), 6),
            "h": round(_safe_float(c.get("h")), 6),
            "l": round(_safe_float(c.get("l")), 6),
            "c": round(_safe_float(c.get("c")), 6),
        }
        for c in tail
    ]
    s = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _norm_candles(candles: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    out = []
    for c in candles:
        out.append({
            "t": float(int(c.get("t", 0))),
            "o": _safe_float(c.get("o")),
            "h": _safe_float(c.get("h")),
            "l": _safe_float(c.get("l")),
            "c": _safe_float(c.get("c")),
        })
    # Orden por tiempo, determinista
    out.sort(key=lambda x: x["t"])
    return out


def _slope(values: List[float]) -> float:
    # Pendiente simple determinista (regresión lineal mínima)
    n = len(values)
    if n < 3:
        return 0.0
    xs = list(range(n))
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum((xs[i] - x_mean) * (values[i] - y_mean) for i in range(n))
    den = sum((xs[i] - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    return num / den


def _trend_from_last(candles: List[Dict[str, float]]) -> str:
    closes = [c["c"] for c in candles]
    m = _slope(closes[-48:])  # "TF mayor" sintético: 48 velas M5 ~ 4h
    # thresholds deterministas, sin depender del instrumento
    if m > 0.05:
        return "UP"
    if m < -0.05:
        return "DOWN"
    return "FLAT"


def _swing_range(candles: List[Dict[str, float]], lookback: int = 60) -> Tuple[float, float]:
    tail = candles[-lookback:] if len(candles) > lookback else candles
    hi = max(c["h"] for c in tail) if tail else 0.0
    lo = min(c["l"] for c in tail) if tail else 0.0
    return lo, hi


def _fibo_levels(lo: float, hi: float) -> Dict[str, float]:
    """
    Fibonacci retracements clásicos.
    Nota: usamos 0.786 como validación obligatoria.
    """
    rng = hi - lo
    if rng <= 0:
        return {"0.618": hi, "0.786": hi}
    return {
        "0.618": hi - rng * 0.618,
        "0.786": hi - rng * 0.786,
    }


def _two_closes_confirm(candles: List[Dict[str, float]], side: str) -> bool:
    """
    Confirmación determinista: 2 cierres consecutivos a favor.
    BUY: c[-1] > c[-2] > c[-3]
    SELL: c[-1] < c[-2] < c[-3]
    """
    if len(candles) < 4:
        return False
    c1 = candles[-1]["c"]
    c2 = candles[-2]["c"]
    c3 = candles[-3]["c"]
    if side == "BUY":
        return (c1 > c2) and (c2 > c3)
    if side == "SELL":
        return (c1 < c2) and (c2 < c3)
    return False


def _make_ui_rows(state: str, side: str, price: float, note: str, input_hash: str) -> List[Dict[str, Any]]:
    return [
        {"k": "Estado", "v": state},
        {"k": "Lado", "v": side or "-"},
        {"k": "Precio", "v": price},
        {"k": "Nota", "v": note},
        {"k": "InputHash", "v": input_hash[:10]},
    ]


# =========================
# Motor (V1 diagnóstico)
# =========================

def decide(
    *,
    world: str,
    atlas_mode: str,
    symbol: str,
    tf: str,
    candles: List[Dict[str, Any]],
    price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    V1: BOT PIENSA.
    - Determinista.
    - No ejecuta.
    - Congela plan en WAIT_GATILLO / GATILLO.
    - Define entry/sl/tp solo en SIGNAL.
    """
    norm = _norm_candles(candles)
    input_hash = _hash_candles(candles)

    # NO inventar precios: si no hay velas suficientes, NO_TRADE
    if len(norm) < 20:
        clear_plan(world, atlas_mode, symbol, tf)
        note = "NO_TRADE: NO_DATA (faltan velas)"
        p = _safe_float(price, norm[-1]["c"] if norm else 0.0)
        return {
            "world": world,
            "atlas_mode": atlas_mode,
            "symbol": symbol,
            "tf": tf,
            "state": "NO_TRADE",
            "side": None,
            "entry": None,
            "sl": None,
            "tp": None,
            "note": note,
            "input_hash": input_hash,
            "ui": {"rows": _make_ui_rows("NO_TRADE", "-", p, note, input_hash), "meta": {}},
        }

    p = _safe_float(price, norm[-1]["c"])

    # Pipeline fijo:
    # 1) TF mayor sintético (48 velas) define contexto
    trend = _trend_from_last(norm)

    # 2) Zona por fibo 0.786 (validación obligatoria)
    lo, hi = _swing_range(norm, lookback=60)
    fib = _fibo_levels(lo, hi)

    # Side sugerida por contexto:
    # UP -> BUY en pullback
    # DOWN -> SELL en pullback
    # FLAT -> NO_TRADE (para V1 evitamos ruido)
    if trend == "FLAT":
        clear_plan(world, atlas_mode, symbol, tf)
        note = "NO_TRADE: mercado en equilibrio (FLAT)"
        return {
            "world": world,
            "atlas_mode": atlas_mode,
            "symbol": symbol,
            "tf": tf,
            "state": "NO_TRADE",
            "side": None,
            "entry": None,
            "sl": None,
            "tp": None,
            "note": note,
            "input_hash": input_hash,
            "ui": {"rows": _make_ui_rows("NO_TRADE", "-", p, note, input_hash), "meta": {}},
        }

    side = "BUY" if trend == "UP" else "SELL"

    # Zona objetivo: fib 0.786 con buffer determinista según rango
    rng = max(hi - lo, 0.000001)
    buf = max(rng * 0.003, 0.4)  # 0.3% del rango o mínimo 0.4 (oro-friendly sin ser loco)
    z = fib["0.786"]
    zone_low = z - buf
    zone_high = z + buf

    in_zone = (zone_low <= p <= zone_high)

    # Leer plan congelado si existe
    plan = get_plan(world, atlas_mode, symbol, tf)
    prev_state = plan.get("state")
    prev_hash = plan.get("input_hash")

    # Si ya teníamos plan, NO cambiarlo mientras no se invalide
    if prev_state in ("WAIT_GATILLO", "GATILLO", "SIGNAL"):
        # Mantener plan fijo aunque el precio se mueva (hasta invalidación)
        # Invalida solo si se aleja demasiado de la zona (determinista)
        zlo = _safe_float(plan.get("zone_low"))
        zhi = _safe_float(plan.get("zone_high"))
        far = (p < (zlo - buf * 2.0)) or (p > (zhi + buf * 2.0))
        if far:
            clear_plan(world, atlas_mode, symbol, tf)
        else:
            # devolver el plan tal cual (determinista)
            note = plan.get("note", "PLAN_CONGELADO")
            state = plan.get("state", "WAIT_GATILLO")
            out = {
                "world": world,
                "atlas_mode": atlas_mode,
                "symbol": symbol,
                "tf": tf,
                "state": state,
                "side": plan.get("side"),
                "entry": plan.get("entry"),
                "sl": plan.get("sl"),
                "tp": plan.get("tp"),
                "note": note,
                "input_hash": plan.get("input_hash", input_hash),
                "ui": {"rows": _make_ui_rows(state, plan.get("side") or "-", p, note, plan.get("input_hash", input_hash)), "meta": {}},
            }
            return out

    # Si no hay plan congelado, solo se crea en zona
    if not in_zone:
        clear_plan(world, atlas_mode, symbol, tf)
        note = f"WAIT: esperando pullback a 0.786 (zona {round(zone_low,2)}–{round(zone_high,2)})"
        return {
            "world": world,
            "atlas_mode": atlas_mode,
            "symbol": symbol,
            "tf": tf,
            "state": "WAIT",
            "side": side,
            "entry": None,
            "sl": None,
            "tp": None,
            "note": note,
            "input_hash": input_hash,
            "ui": {"rows": _make_ui_rows("WAIT", side, p, note, input_hash), "meta": {}},
        }

    # Estamos en zona -> congelamos plan (WAIT_GATILLO)
    plan = {
        "state": "WAIT_GATILLO",
        "side": side,
        "zone_low": zone_low,
        "zone_high": zone_high,
        "entry": None,
        "sl": None,
        "tp": None,
        "note": "WAIT_GATILLO: plan congelado (zona fib 0.786)",
        "input_hash": input_hash,
    }

    # Confirmación por 2 cierres a favor
    if _two_closes_confirm(norm[-12:], side):
        plan["state"] = "GATILLO"
        plan["note"] = "GATILLO: 2 cierres confirmatorios"
        # ⚠️ OJO: seguimos sin entry/sl/tp aquí (solo se definen en SIGNAL)
        # SIGNAL lo dejamos para cuando haya “ruptura mínima” adicional determinista:
        # BUY: cierre rompe máximo de últimas 6 velas
        # SELL: cierre rompe mínimo de últimas 6 velas
        tail = norm[-6:]
        last_close = tail[-1]["c"]
        hi6 = max(c["h"] for c in tail)
        lo6 = min(c["l"] for c in tail)
        if side == "BUY" and last_close >= hi6:
            plan["state"] = "SIGNAL"
        if side == "SELL" and last_close <= lo6:
            plan["state"] = "SIGNAL"

    # Si llega a SIGNAL, ahora sí definimos entry/sl/tp (una vez)
    if plan["state"] == "SIGNAL":
        # Entry: precio actual (determinista)
        entry = p
        # SL: fuera de zona + buffer (determinista)
        if side == "BUY":
            sl = zone_low - buf
            tp = entry + (entry - sl) * 1.5
        else:
            sl = zone_high + buf
            tp = entry - (sl - entry) * 1.5

        plan["entry"] = float(entry)
        plan["sl"] = float(sl)
        plan["tp"] = float(tp)
        plan["note"] = "SIGNAL: plan final (entry/sl/tp definidos)"

    set_plan(world, atlas_mode, symbol, tf, plan)

    return {
        "world": world,
        "atlas_mode": atlas_mode,
        "symbol": symbol,
        "tf": tf,
        "state": plan["state"],
        "side": plan["side"],
        "entry": plan.get("entry"),
        "sl": plan.get("sl"),
        "tp": plan.get("tp"),
        "note": plan.get("note"),
        "input_hash": plan.get("input_hash"),
        "ui": {"rows": _make_ui_rows(plan["state"], plan["side"], p, plan.get("note",""), plan.get("input_hash", input_hash)), "meta": {}},
    }