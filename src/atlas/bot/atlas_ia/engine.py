# src/atlas/bot/atlas_ia/engine.py
from __future__ import annotations

from typing import Dict, List, Tuple, Any, Optional

from atlas.bot.atlas_ia.state import (
    get_plan,
    clear_plan,
    upsert_plan_wait_gatillo,
    promote_to_signal,
    expire_if_needed,
)


# =========================================================
# Helpers
# =========================================================

def _last_two_closes(candles: List[Dict[str, Any]]):
    if len(candles) < 2:
        return None, None
    return candles[-2].get("c"), candles[-1].get("c")


def _round_price(x: float, digits: int) -> float:
    try:
        return round(float(x), int(digits))
    except Exception:
        return float(x)


def _norm_tf(tf: str) -> str:
    t = (tf or "").strip().lower()
    if t in ("1m", "m1", "1"):
        return "M1"
    if t in ("5m", "m5", "5"):
        return "M5"
    if t.endswith("m") and t[:-1].isdigit():
        return f"M{t[:-1]}"
    return (tf or "").strip().upper()


def _fib_levels(high: float, low: float):
    diff = high - low
    return {
        "0.5": high - diff * 0.5,
        "0.618": high - diff * 0.618,
        "0.786": high - diff * 0.786,
    }


def _bars_elapsed(candles: List[Dict[str, Any]], plan_created_t: int) -> int:
    # cuenta cuántas velas pasaron desde created_t usando el timestamp de vela (t)
    if not candles:
        return 0
    ts = [c.get("t") for c in candles if c.get("t") is not None]
    if not ts:
        return 0
    # cuántas velas tienen t >= created_t (aprox “pasos”)
    return sum(1 for t in ts if int(t) >= int(plan_created_t))


def _invalidated(plan_side: str, last_close: float, zone_low: Optional[float], zone_high: Optional[float]) -> bool:
    # invalidación simple y dura
    if plan_side == "BUY":
        if zone_low is not None and last_close < zone_low:
            return True
    if plan_side == "SELL":
        if zone_high is not None and last_close > zone_high:
            return True
    return False


# =========================================================
# Plan builder (congelación)
# =========================================================

def _maybe_build_plan_m5(symbol: str, tf_norm: str, candles: List[Dict[str, Any]], digits: int):
    if len(candles) < 20:
        return None

    highs = [c.get("h") for c in candles[-20:]]
    lows = [c.get("l") for c in candles[-20:]]
    if any(x is None for x in highs) or any(x is None for x in lows):
        return None

    high = max(highs)
    low = min(lows)
    fib = _fib_levels(high, low)

    prev_close, last_close = _last_two_closes(candles)
    if prev_close is None or last_close is None:
        return None

    t_last = int(candles[-1].get("t") or 0)

    # --- BUY plan: precio en zona profunda (<= 0.786), congelar plan
    if last_close <= fib["0.786"]:
        return {
            "t": t_last,
            "side": "BUY",
            "text": "M5: Plan en zona profunda (congelado)",
            "zone_low": low,
            "zone_high": fib["0.786"],
            "ttl_bars": 12,  # ~12 velas M5 (1h aprox en modo fake)
            "confirm": (prev_close > fib["0.786"] and last_close > fib["0.786"]),
            "entry": last_close,
            "sl": low,
            "tp": high,
        }

    # --- SELL plan: precio arriba (>= 0.5), congelar plan
    if last_close >= fib["0.5"]:
        return {
            "t": t_last,
            "side": "SELL",
            "text": "M5: Plan en zona alta (congelado)",
            "zone_low": fib["0.5"],
            "zone_high": high,
            "ttl_bars": 12,
            "confirm": (prev_close < fib["0.5"] and last_close < fib["0.5"]),
            "entry": last_close,
            "sl": high,
            "tp": low,
        }

    return None


def _maybe_build_plan_m1(symbol: str, tf_norm: str, candles: List[Dict[str, Any]], digits: int):
    if len(candles) < 15:
        return None

    prev_close, last_close = _last_two_closes(candles)
    if prev_close is None or last_close is None:
        return None

    t_last = int(candles[-1].get("t") or 0)

    last_high = max(c.get("h") for c in candles[-10:] if c.get("h") is not None)
    last_low = min(c.get("l") for c in candles[-10:] if c.get("l") is not None)

    rng = float(last_high - last_low)
    if rng <= 0:
        return None

    # buffer “cerca del extremo”
    buf = rng * 0.15

    # Si estamos cerca del low: plan BUY esperando ruptura alcista del micro-techo
    if last_close <= (last_low + buf):
        return {
            "t": t_last,
            "side": "BUY",
            "text": "M1: Plan cerca del piso (congelado)",
            "zone_low": last_low,
            "zone_high": last_low + buf,
            "ttl_bars": 60,  # 60 velas M1
            "confirm": (last_close > last_high),  # trigger real
            "entry": last_close,
            "sl": last_low,
            "tp": last_close + (last_close - last_low),
        }

    # Si estamos cerca del high: plan SELL esperando ruptura bajista del micro-piso
    if last_close >= (last_high - buf):
        return {
            "t": t_last,
            "side": "SELL",
            "text": "M1: Plan cerca del techo (congelado)",
            "zone_low": last_high - buf,
            "zone_high": last_high,
            "ttl_bars": 60,
            "confirm": (last_close < last_low),  # trigger real
            "entry": last_close,
            "sl": last_high,
            "tp": last_close - (last_high - last_close),
        }

    return None


# =========================================================
# WORLD ENGINE
# =========================================================

def run_world_rows(
    world: str,
    tf_norm: str,
    symbols: List[str],
    candles_by_symbol: Dict[str, Any],
    digits: int = 2,
    atlas_mode: str = "SCALPING",
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:

    rows: List[Dict[str, Any]] = []
    signals = 0
    action = "WAIT"

    for symbol in symbols:
        payload = candles_by_symbol.get(symbol)
        if not payload or not payload.get("ok"):
            continue

        candles = payload.get("candles", [])
        if world != "ATLAS_IA":
            continue

        prev_close, last_close = _last_two_closes(candles)
        if last_close is None:
            continue

        # --- 1) Si hay plan existente, lo respetamos (congelado)
        existing = get_plan(symbol, tf_norm, atlas_mode)
        if existing:
            bars_elapsed = _bars_elapsed(candles, existing.created_t)
            expire_if_needed(symbol=symbol, tf_norm=tf_norm, atlas_mode=atlas_mode, bars_elapsed=bars_elapsed)

            existing = get_plan(symbol, tf_norm, atlas_mode)
            if existing:
                # invalidación simple
                if existing.side and _invalidated(existing.side, float(last_close), existing.zone_low, existing.zone_high):
                    clear_plan(symbol, tf_norm, atlas_mode)
                    existing = None

        # --- 2) Si sigue existiendo:
        if existing:
            if existing.status == "SIGNAL":
                action = "SIGNAL"
                signals += 1
                rows.append({
                    "symbol": symbol,
                    "tf": tf_norm,
                    "text": existing.text or "SIGNAL (congelado)",
                    "action": "SIGNAL",
                    "side": existing.side,
                    "entry": _round_price(existing.entry, digits) if existing.entry is not None else None,
                    "sl": _round_price(existing.sl, digits) if existing.sl is not None else None,
                    "tp": _round_price(existing.tp, digits) if existing.tp is not None else None,
                    "plan_id": existing.plan_id,
                    "zone_low": _round_price(existing.zone_low, digits) if existing.zone_low is not None else None,
                    "zone_high": _round_price(existing.zone_high, digits) if existing.zone_high is not None else None,
                })
                continue

            if existing.status == "WAIT_GATILLO":
                action = "WAIT_GATILLO"
                rows.append({
                    "symbol": symbol,
                    "tf": tf_norm,
                    "text": existing.text or "WAIT_GATILLO (plan congelado)",
                    "action": "WAIT_GATILLO",
                    "side": existing.side,
                    "entry": None,
                    "sl": None,
                    "tp": None,
                    "plan_id": existing.plan_id,
                    "zone_low": _round_price(existing.zone_low, digits) if existing.zone_low is not None else None,
                    "zone_high": _round_price(existing.zone_high, digits) if existing.zone_high is not None else None,
                })
                continue

        # --- 3) No hay plan: intentamos construir plan según TF
        plan_candidate = None
        if tf_norm == "M5":
            plan_candidate = _maybe_build_plan_m5(symbol, tf_norm, candles, digits)
        elif tf_norm == "M1":
            plan_candidate = _maybe_build_plan_m1(symbol, tf_norm, candles, digits)

        if plan_candidate:
            # congelamos WAIT_GATILLO
            plan = upsert_plan_wait_gatillo(
                symbol=symbol,
                tf_norm=tf_norm,
                atlas_mode=atlas_mode,
                t=int(plan_candidate["t"]),
                side=str(plan_candidate["side"]),
                text=str(plan_candidate["text"]),
                zone_low=plan_candidate.get("zone_low"),
                zone_high=plan_candidate.get("zone_high"),
                ttl_bars=int(plan_candidate.get("ttl_bars") or 60),
            )

            # si además hay confirmación, promovemos a SIGNAL y congelamos entry/sl/tp
            if bool(plan_candidate.get("confirm", False)):
                plan = promote_to_signal(
                    symbol=symbol,
                    tf_norm=tf_norm,
                    atlas_mode=atlas_mode,
                    t=int(plan_candidate["t"]),
                    entry=float(plan_candidate["entry"]),
                    sl=float(plan_candidate["sl"]),
                    tp=float(plan_candidate["tp"]),
                    text=str(plan_candidate.get("text") or "SIGNAL"),
                )
                action = "SIGNAL"
                signals += 1
                rows.append({
                    "symbol": symbol,
                    "tf": tf_norm,
                    "text": plan.text,
                    "action": "SIGNAL",
                    "side": plan.side,
                    "entry": _round_price(plan.entry, digits) if plan.entry is not None else None,
                    "sl": _round_price(plan.sl, digits) if plan.sl is not None else None,
                    "tp": _round_price(plan.tp, digits) if plan.tp is not None else None,
                    "plan_id": plan.plan_id,
                    "zone_low": _round_price(plan.zone_low, digits) if plan.zone_low is not None else None,
                    "zone_high": _round_price(plan.zone_high, digits) if plan.zone_high is not None else None,
                })
            else:
                action = "WAIT_GATILLO"
                rows.append({
                    "symbol": symbol,
                    "tf": tf_norm,
                    "text": plan.text,
                    "action": "WAIT_GATILLO",
                    "side": plan.side,
                    "entry": None,
                    "sl": None,
                    "tp": None,
                    "plan_id": plan.plan_id,
                    "zone_low": _round_price(plan.zone_low, digits) if plan.zone_low is not None else None,
                    "zone_high": _round_price(plan.zone_high, digits) if plan.zone_high is not None else None,
                })
            continue

        # --- 4) Nada: WAIT
        rows.append({
            "symbol": symbol,
            "tf": tf_norm,
            "text": "WAIT (sin plan)",
            "action": "WAIT",
            "side": None,
            "entry": None,
            "sl": None,
            "tp": None,
            "plan_id": None,
            "zone_low": None,
            "zone_high": None,
        })

    analysis = {
        "world": world,
        "action": action,
        "signals": signals,
        "reason": "Hay condiciones activas" if signals else "Sin condiciones",
    }

    return analysis, rows


# =========================================================
# ✅ Adapter estable para snapshot_core
# =========================================================

def eval_atlas_ia(
    *,
    symbol: str,
    tf: str,
    candles: List[Dict[str, Any]],
    digits: int = 2,
    atlas_mode: str = "SCALPING",
    raw_query: Optional[Dict[str, Any]] = None,
    debug: bool = False,
) -> Dict[str, Any]:

    tf_norm = _norm_tf(tf)

    candles_by_symbol = {symbol: {"ok": True, "candles": candles}}

    analysis, rows = run_world_rows(
        world="ATLAS_IA",
        tf_norm=tf_norm,
        symbols=[symbol],
        candles_by_symbol=candles_by_symbol,
        digits=int(digits or 2),
        atlas_mode=(atlas_mode or "SCALPING"),
    )

    # Estado visible para snapshot/UI
    # frozen = True cuando estamos en WAIT_GATILLO o SIGNAL (plan fijo)
    frozen = bool(analysis.get("action") in ("WAIT_GATILLO", "SIGNAL"))
    plan_id = None
    if rows and isinstance(rows[0], dict):
        plan_id = rows[0].get("plan_id")

    analysis_out = {
        **analysis,
        "frozen": frozen,
        "plan_id": plan_id,
        "raw_query": raw_query or {},
        "debug": bool(debug),
    }

    # La UI suele querer ver tf como el request original ("1m"/"5m")
    for r in rows:
        r["tf"] = tf

    return {"analysis": analysis_out, "ui": {"rows": rows}}
