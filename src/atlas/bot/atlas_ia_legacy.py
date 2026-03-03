# src/atlas/bot/atlas_ia.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import math


# ==========================================================
# CONFIG (motor real v0.1)
# ==========================================================
ATLAS_CFG: Dict[str, Any] = {
    "enabled": True,

    # ZONA ÓPTIMA OBLIGATORIA
    "fib_level": 0.786,          # NO usar 0.79 acá
    "zone_width_atr": 0.35,      # ancho de zona en múltiplos de ATR
    "min_impulse_atr": 1.20,     # impulso mínimo medido en ATR para considerar escenario
    "lookback_swings": 120,      # velas para buscar swing

    # TIMING
    "confirm_closes": 1,         # 1 = explosivo (vela gatillo del momento)
                                # 2 = más conservador (si algún día querés)
    "tf_exec_default": "M3",
    "tf_ref_default": "M15",

    # RISK (solo señal)
    "tp_r": 2.0,                 # TP = 2R
    "sl_atr": 0.25,              # SL técnico con buffer ATR

    # Congelar plan
    "freeze_plan": True,
    "invalidate_on_close_outside_zone": 2,  # 2 cierres fuera invalidan hipótesis contraria (tu regla)
}


# Estado congelado por símbolo + modo (SCALPING/FOREX)
# key = f"{atlas_mode}:{symbol}"
_ATLAS_STATE: Dict[str, Dict[str, Any]] = {}


# ==========================================================
# Helpers numéricos
# ==========================================================
def _f(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        v = float(x)
        if math.isfinite(v):
            return v
    except Exception:
        pass
    return default


def _last_n(candles: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    if not candles:
        return []
    return candles[-n:] if len(candles) >= n else candles[:]


def _sma(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / float(len(values))


def _atr(candles: List[Dict[str, Any]], period: int = 14) -> Optional[float]:
    c = _last_n(candles, period + 1)
    if len(c) < 2:
        return None
    trs: List[float] = []
    prev_close = _f(c[0].get("close"))
    for k in c[1:]:
        h = _f(k.get("high"))
        l = _f(k.get("low"))
        cl = _f(k.get("close"))
        if h is None or l is None or cl is None or prev_close is None:
            continue
        tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        trs.append(tr)
        prev_close = cl
    return _sma(trs) if trs else None


def _round(x: Optional[float], digits: int) -> Optional[float]:
    if x is None:
        return None
    try:
        return round(float(x), int(digits))
    except Exception:
        return x


def _digits_default(symbol: str) -> int:
    # placeholder razonable
    if "JPY" in symbol:
        return 3
    if symbol.upper().startswith("XAU"):
        return 2
    return 5


# ==========================================================
# Modelo de salida
# ==========================================================
@dataclass
class RowOut:
    symbol: str
    tf: str
    text: str
    action: str  # WAIT | WAIT_GATILLO | SIGNAL
    side: Optional[str] = None  # BUY | SELL
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    reason: Optional[str] = None
    vela_gatillo: Optional[int] = None
    likely_type: Optional[str] = None


# ==========================================================
# Núcleo: encontrar impulso + corrección y zona 0.786
# ==========================================================
def _find_swing(candles: List[Dict[str, Any]], lookback: int) -> Optional[Tuple[int, int]]:
    """
    Devuelve (i_low, i_high) del swing dominante reciente.
    Simple y robusto:
    - buscamos el mínimo y máximo en ventana lookback
    - elegimos el orden temporal válido para formar impulso
    """
    if len(candles) < 20:
        return None

    c = candles[-lookback:] if len(candles) > lookback else candles[:]
    lows = [(idx, _f(k.get("low"))) for idx, k in enumerate(c)]
    highs = [(idx, _f(k.get("high"))) for idx, k in enumerate(c)]
    lows = [(i, v) for i, v in lows if v is not None]
    highs = [(i, v) for i, v in highs if v is not None]
    if not lows or not highs:
        return None

    i_low, v_low = min(lows, key=lambda t: t[1])
    i_high, v_high = max(highs, key=lambda t: t[1])

    if i_low == i_high:
        return None

    # impulso alcista si low ocurre antes que high
    # impulso bajista si high ocurre antes que low
    return (i_low, i_high)


def _build_fib_zone(
    candles: List[Dict[str, Any]],
    digits: int,
) -> Optional[Dict[str, Any]]:
    """
    Crea un plan:
    - detecta swing (low/high)
    - mide impulso en ATR
    - define zona alrededor de fib 0.786 (ancho por ATR)
    """
    atr = _atr(candles, 14)
    if atr is None or atr <= 0:
        return None

    swing = _find_swing(candles, ATLAS_CFG["lookback_swings"])
    if not swing:
        return None

    # swing indices en ventana recortada, necesitamos mapear a indices reales
    c = candles[-ATLAS_CFG["lookback_swings"]:] if len(candles) > ATLAS_CFG["lookback_swings"] else candles[:]
    base_idx = len(candles) - len(c)

    i_low, i_high = swing
    i_low += base_idx
    i_high += base_idx

    low = _f(candles[i_low].get("low"))
    high = _f(candles[i_high].get("high"))
    if low is None or high is None:
        return None

    # Definir dirección del impulso por orden temporal
    if i_low < i_high:
        side = "BUY"
        impulse = high - low
        # retroceso desde high hacia low
        level = high - impulse * ATLAS_CFG["fib_level"]
        zone_center = level
    else:
        side = "SELL"
        impulse = high - low  # sigue siendo (max-min)
        # retroceso desde low hacia high (para sell el impulso real es hacia abajo)
        level = low + impulse * ATLAS_CFG["fib_level"]
        zone_center = level

    if impulse <= 0:
        return None

    if impulse < atr * ATLAS_CFG["min_impulse_atr"]:
        return None

    width = atr * ATLAS_CFG["zone_width_atr"]
    zone_low = zone_center - width
    zone_high = zone_center + width

    return {
        "side": side,
        "swing": {"i_low": i_low, "i_high": i_high, "low": low, "high": high},
        "atr": atr,
        "zone_low": _round(zone_low, digits),
        "zone_high": _round(zone_high, digits),
        "zone_center": _round(zone_center, digits),
        "fib_level": ATLAS_CFG["fib_level"],
    }


# ==========================================================
# Detección de gatillos (los 3)
# ==========================================================
def _in_zone(px: float, zlow: float, zhigh: float) -> bool:
    return zlow <= px <= zhigh


def _trigger_touch(candles: List[Dict[str, Any]], side: str, zlow: float, zhigh: float) -> Optional[int]:
    """
    TOQUE: la vela actual toca zona y cierra a favor.
    Devuelve timestamp (t) de vela gatillo si aplica.
    """
    if len(candles) < 2:
        return None
    last = candles[-1]
    o = _f(last.get("open"))
    h = _f(last.get("high"))
    l = _f(last.get("low"))
    c = _f(last.get("close"))
    t = int(last.get("time") or last.get("t") or 0)

    if None in (o, h, l, c) or t == 0:
        return None

    touched = _in_zone(h, zlow, zhigh) or _in_zone(l, zlow, zhigh) or _in_zone(c, zlow, zhigh)
    if not touched:
        return None

    if side == "BUY":
        # cierre con cuerpo hacia arriba dentro/por encima de zona
        if c > o:
            return t
    else:
        if c < o:
            return t
    return None


def _trigger_sweep_reclaim(candles: List[Dict[str, Any]], side: str, zlow: float, zhigh: float) -> Optional[int]:
    """
    BARRIDA_RECUPERACION:
    - BUY: mecha por debajo de zlow y cierre de vuelta dentro de zona
    - SELL: mecha por encima de zhigh y cierre de vuelta dentro de zona
    """
    if len(candles) < 2:
        return None
    last = candles[-1]
    h = _f(last.get("high"))
    l = _f(last.get("low"))
    c = _f(last.get("close"))
    t = int(last.get("time") or last.get("t") or 0)
    if None in (h, l, c) or t == 0:
        return None

    if side == "BUY":
        if l < zlow and _in_zone(c, zlow, zhigh):
            return t
    else:
        if h > zhigh and _in_zone(c, zlow, zhigh):
            return t
    return None


def _trigger_break_retest(candles: List[Dict[str, Any]], side: str, zlow: float, zhigh: float) -> Optional[int]:
    """
    RUPTURA_RETEST simple:
    - define micro nivel con vela previa (high/low)
    - BUY: rompe high previo y retestea (cierra >= high previo) dentro de 2 velas
    - SELL: rompe low previo y retestea (cierra <= low previo) dentro de 2 velas
    """
    if len(candles) < 4:
        return None

    prev = candles[-2]
    prev_h = _f(prev.get("high"))
    prev_l = _f(prev.get("low"))
    if prev_h is None or prev_l is None:
        return None

    last = candles[-1]
    h = _f(last.get("high"))
    l = _f(last.get("low"))
    c = _f(last.get("close"))
    t = int(last.get("time") or last.get("t") or 0)
    if None in (h, l, c) or t == 0:
        return None

    if side == "BUY":
        if h > prev_h and c >= prev_h and _in_zone(c, zlow, zhigh):
            return t
    else:
        if l < prev_l and c <= prev_l and _in_zone(c, zlow, zhigh):
            return t
    return None


def _pick_trigger(candles: List[Dict[str, Any]], side: str, zlow: float, zhigh: float) -> Tuple[str, Optional[int]]:
    """
    Orden de prioridad (explosivo):
    1) BARRIDA_RECUPERACION
    2) TOQUE
    3) RUPTURA_RETEST
    """
    t = _trigger_sweep_reclaim(candles, side, zlow, zhigh)
    if t:
        return "BARRIDA_RECUPERACION", t

    t = _trigger_touch(candles, side, zlow, zhigh)
    if t:
        return "TOQUE", t

    t = _trigger_break_retest(candles, side, zlow, zhigh)
    if t:
        return "RUPTURA_RETEST", t

    return "WAIT", None


# ==========================================================
# Construcción de señal (entry/sl/tp) usando vela gatillo
# ==========================================================
def _build_signal(candles: List[Dict[str, Any]], side: str, atr: float, digits: int) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    last = candles[-1]
    entry = _f(last.get("close"))
    if entry is None:
        return None, None, None

    buffer = atr * ATLAS_CFG["sl_atr"]
    if side == "BUY":
        sl = min([_f(last.get("low")) or entry, entry - buffer]) - (buffer * 0.25)
        tp = entry + abs(entry - sl) * ATLAS_CFG["tp_r"]
    else:
        sl = max([_f(last.get("high")) or entry, entry + buffer]) + (buffer * 0.25)
        tp = entry - abs(entry - sl) * ATLAS_CFG["tp_r"]

    return _round(entry, digits), _round(sl, digits), _round(tp, digits)


def _count_closes_outside_zone(candles: List[Dict[str, Any]], zlow: float, zhigh: float, n: int) -> int:
    """
    Cuenta cierres consecutivos fuera de zona (desde el final).
    Si hay 2 cierres fuera => invalidación (tu regla).
    """
    if n <= 0:
        return 0
    c = _last_n(candles, n)
    closes = [_f(k.get("close")) for k in c]
    closes = [x for x in closes if x is not None]
    if not closes:
        return 0
    count = 0
    for cl in reversed(closes):
        if cl < zlow or cl > zhigh:
            count += 1
        else:
            break
    return count


# ==========================================================
# Motor principal por símbolo
# ==========================================================
def _key(atlas_mode: Optional[str], symbol: str) -> str:
    return f"{(atlas_mode or 'NONE').upper()}:{symbol}"


def analyze_symbol(
    atlas_mode: Optional[str],
    symbol: str,
    tf: str,
    candles: List[Dict[str, Any]],
    digits: int,
) -> RowOut:
    if not ATLAS_CFG.get("enabled", True):
        return RowOut(symbol=symbol, tf=tf, text="Motor apagado", action="WAIT", reason="NO_TRADE: disabled")

    if len(candles) < 40:
        return RowOut(symbol=symbol, tf=tf, text="Pocas velas", action="WAIT", reason="NO_TRADE: historial insuficiente")

    digits = int(digits or _digits_default(symbol))
    k = _key(atlas_mode, symbol)

    # Si hay plan congelado, úsalo
    st = _ATLAS_STATE.get(k) or {}
    frozen = bool(st.get("frozen", False)) and ATLAS_CFG.get("freeze_plan", True)

    if frozen:
        plan = st.get("plan") or {}
    else:
        plan = _build_fib_zone(candles, digits)

    if not plan:
        _ATLAS_STATE[k] = {"frozen": False, "status": "WAIT", "plan": None}
        return RowOut(
            symbol=symbol,
            tf=tf,
            text="Sin escenario (0.786 no habilitado)",
            action="WAIT",
            reason="NO_TRADE: no hay impulso válido o ATR insuficiente",
            likely_type="WAIT",
        )

    side = plan["side"]
    zlow = float(plan["zone_low"])
    zhigh = float(plan["zone_high"])
    atr = float(plan["atr"])

    # Congelar plan cuando el precio entra o roza la zona (WAIT_GATILLO)
    last_close = _f(candles[-1].get("close"))
    if last_close is None:
        return RowOut(symbol=symbol, tf=tf, text="Sin close", action="WAIT", reason="NO_TRADE: sin close", likely_type="WAIT")

    in_or_near = _in_zone(last_close, zlow, zhigh)

    status = "WAIT"
    if in_or_near:
        status = "WAIT_GATILLO"
        if ATLAS_CFG.get("freeze_plan", True):
            _ATLAS_STATE[k] = {"frozen": True, "status": status, "plan": plan, "since": int(candles[-1].get("time") or candles[-1].get("t") or 0)}
    else:
        # si estaba congelado pero se fue lejos, descongelar
        if frozen:
            _ATLAS_STATE[k] = {"frozen": False, "status": "WAIT", "plan": None}

    # Invalidación por 2 cierres fuera de zona (si estamos esperando contra-idea)
    out_n = _count_closes_outside_zone(candles, zlow, zhigh, ATLAS_CFG["invalidate_on_close_outside_zone"])
    if frozen and out_n >= ATLAS_CFG["invalidate_on_close_outside_zone"]:
        _ATLAS_STATE[k] = {"frozen": False, "status": "WAIT", "plan": None}
        return RowOut(
            symbol=symbol,
            tf=tf,
            text="Plan invalidado (aceptación fuera de zona)",
            action="WAIT",
            reason="NO_TRADE: 2 cierres consecutivos fuera de zona",
            likely_type="WAIT",
        )

    # Si estamos en WAIT_GATILLO, buscamos gatillo
    if status == "WAIT_GATILLO":
        trig_name, trig_t = _pick_trigger(candles, side, zlow, zhigh)

        if trig_t:
            entry, sl, tp = _build_signal(candles, side, atr, digits)
            _ATLAS_STATE[k] = {
                "frozen": True,
                "status": "SIGNAL",
                "plan": plan,
                "signal": {"entry": entry, "sl": sl, "tp": tp, "vela_gatillo": trig_t, "type": trig_name},
            }
            return RowOut(
                symbol=symbol,
                tf=tf,
                text=f"{trig_name} (vela gatillo)",
                action="SIGNAL",
                side=side,
                entry=entry,
                sl=sl,
                tp=tp,
                reason="SIGNAL: vela del momento de entrada",
                vela_gatillo=trig_t,
                likely_type=trig_name,
            )

        # Aún no hay gatillo: mostrar el “más probable” (sin mentir: solo por scores básicos)
        return RowOut(
            symbol=symbol,
            tf=tf,
            text=f"Zona 0.786 activa [{_round(zlow, digits)} - {_round(zhigh, digits)}]",
            action="WAIT_GATILLO",
            side=side,
            reason="WAIT_GATILLO: plan congelado, esperando gatillo",
            vela_gatillo=None,
            likely_type="WAIT",
        )

    # WAIT normal
    return RowOut(
        symbol=symbol,
        tf=tf,
        text="Esperando llegada a zona 0.786",
        action="WAIT",
        side=side,
        reason="WAIT: sin llegada a la zona",
        vela_gatillo=None,
        likely_type="WAIT",
    )


# ==========================================================
# API para snapshot_core: run_world_rows
# ==========================================================
def run_world_rows(
    world: str,
    tf: str,
    symbols: List[str],
    candles_by_symbol: Dict[str, Dict[str, Any]],
    atlas_mode: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    rows_out: List[RowOut] = []
    signals = 0
    wait_gatillo = 0

    for sym in symbols:
        payload = candles_by_symbol.get(sym) or {}
        c = payload.get("candles") or []
        digits = int(payload.get("digits") or _digits_default(sym))
        ok = bool(payload.get("ok", False))

        if not ok:
            rows_out.append(
                RowOut(
                    symbol=sym,
                    tf=tf,
                    text="Sin datos MT5",
                    action="WAIT",
                    reason="NO_TRADE: mt5_candles failed",
                )
            )
            continue

        r = analyze_symbol(atlas_mode, sym, tf, c, digits)
        if r.action == "SIGNAL":
            signals += 1
        if r.action == "WAIT_GATILLO":
            wait_gatillo += 1
        rows_out.append(r)

    analysis: Dict[str, Any] = {
        "world": world,
        "status": "OK",
        "atlas_mode": (atlas_mode or "").upper() or None,
        "action": "SIGNAL" if signals else ("WAIT_GATILLO" if wait_gatillo else "WAIT"),
        "signals": signals,
        "wait_gatillo": wait_gatillo,
        "reason": "ATLAS_REAL: señal activa" if signals else ("ATLAS_REAL: plan congelado" if wait_gatillo else "ATLAS_REAL: esperando zona"),
    }

    rows: List[Dict[str, Any]] = []
    for r in rows_out:
        rows.append(
            {
                "symbol": r.symbol,
                "tf": r.tf,
                "text": r.text,
                "action": r.action,
                "side": r.side,
                "entry": r.entry,
                "sl": r.sl,
                "tp": r.tp,
                "reason": r.reason or r.text,
                "vela_gatillo": r.vela_gatillo,
                "likely_type": r.likely_type,
            }
        )

    return analysis, rows
