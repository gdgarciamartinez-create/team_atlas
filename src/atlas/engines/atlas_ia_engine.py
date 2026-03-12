from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from atlas.fib_opt_store import FibOptStore
from atlas.worlds_tf import get_world_tf
from atlas.bot.plan_lock import (
    get_plan,
    lock_plan,
    set_signal,
    invalidate_plan,
    plan_to_dict,
)


# ============================================================
# Utilidades
# ============================================================

def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _u(x: str) -> str:
    return (x or "").strip().upper()


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _get_candle(c: Any) -> Tuple[Optional[int], Optional[float], Optional[float], Optional[float], Optional[float]]:
    if isinstance(c, dict):
        t = c.get("t") or c.get("time")
        o = c.get("o") or c.get("open")
        h = c.get("h") or c.get("high")
        l = c.get("l") or c.get("low")
        cl = c.get("c") or c.get("close")
        return (int(t) if t is not None else None, _safe_float(o), _safe_float(h), _safe_float(l), _safe_float(cl))
    t = getattr(c, "t", None) or getattr(c, "time", None)
    o = getattr(c, "o", None) or getattr(c, "open", None)
    h = getattr(c, "h", None) or getattr(c, "high", None)
    l = getattr(c, "l", None) or getattr(c, "low", None)
    cl = getattr(c, "c", None) or getattr(c, "close", None)
    return (int(t) if t is not None else None, _safe_float(o), _safe_float(h), _safe_float(l), _safe_float(cl))


def _last_close(candles: List[Any]) -> Optional[float]:
    if not candles:
        return None
    _, _, _, _, cl = _get_candle(candles[-1])
    return cl


def _body(o: float, c: float) -> float:
    return abs(c - o)


def _in_zone(px: float, zlow: float, zhigh: float) -> bool:
    return zlow <= px <= zhigh


# ============================================================
# Pivots + ratios (para fib_opt)
# ============================================================

@dataclass
class Swing:
    idx: int
    price: float
    kind: str  # H | L


def _detect_pivots(candles: List[Any], left: int = 2, right: int = 2) -> List[Swing]:
    n = len(candles)
    if n < left + right + 3:
        return []
    highs: List[float] = []
    lows: List[float] = []
    for c in candles:
        _, _, h, l, _ = _get_candle(c)
        highs.append(h or 0.0)
        lows.append(l or 0.0)

    piv: List[Swing] = []
    for i in range(left, n - right):
        hi = highs[i]
        lo = lows[i]
        if hi <= 0 or lo <= 0:
            continue
        if all(hi > highs[j] for j in range(i - left, i)) and all(hi >= highs[j] for j in range(i + 1, i + right + 1)):
            piv.append(Swing(i, hi, "H"))
        if all(lo < lows[j] for j in range(i - left, i)) and all(lo <= lows[j] for j in range(i + 1, i + right + 1)):
            piv.append(Swing(i, lo, "L"))

    piv.sort(key=lambda s: s.idx)
    cleaned: List[Swing] = []
    for p in piv:
        if not cleaned:
            cleaned.append(p)
            continue
        last = cleaned[-1]
        if p.kind != last.kind:
            cleaned.append(p)
            continue
        if p.kind == "H" and p.price > last.price:
            cleaned[-1] = p
        if p.kind == "L" and p.price < last.price:
            cleaned[-1] = p
    return cleaned


def _retro_ratios(pivots: List[Swing]) -> List[float]:
    out: List[float] = []
    if len(pivots) < 3:
        return out
    for i in range(len(pivots) - 2):
        a, b, c = pivots[i], pivots[i + 1], pivots[i + 2]
        imp = abs(b.price - a.price)
        cor = abs(b.price - c.price)
        if imp <= 1e-9:
            continue
        r = cor / imp
        if 0.20 <= r <= 1.60:
            out.append(float(r))
    return out


# ============================================================
# Zona desde último impulso usando fib_opt
# ============================================================

@dataclass
class Zone:
    side: str
    zone_low: float
    zone_high: float
    target: float  # TP objetivo simple (último extremo del impulso)
    reason: str = "FIB_OPT_BAND"


def _zone_from_last_impulse(candles: List[Any], opt_level: float, band_low: float, band_high: float) -> Optional[Zone]:
    piv = _detect_pivots(candles, left=2, right=2)
    if len(piv) < 3:
        return None
    a, b, _c = piv[-3], piv[-2], piv[-1]

    imp = b.price - a.price
    if abs(imp) <= 1e-9:
        return None

    if imp > 0:
        # impulso alcista -> zona BUY en retroceso desde b (high)
        lo = a.price
        hi = b.price
        rng = hi - lo
        p1 = hi - rng * band_high
        p2 = hi - rng * band_low
        zlow = min(p1, p2)
        zhigh = max(p1, p2)
        return Zone(side="BUY", zone_low=float(zlow), zone_high=float(zhigh), target=float(hi))
    else:
        # impulso bajista -> zona SELL en retroceso desde b (low)
        hi = a.price
        lo = b.price
        rng = hi - lo
        p1 = lo + rng * band_low
        p2 = lo + rng * band_high
        zlow = min(p1, p2)
        zhigh = max(p1, p2)
        return Zone(side="SELL", zone_low=float(zlow), zone_high=float(zhigh), target=float(lo))


# ============================================================
# Gatillos PRO (M1/M3)
# ============================================================

def _trigger_close_confirm(candles: List[Any], side: str, zlow: float, zhigh: float) -> bool:
    if len(candles) < 2:
        return False
    _, o, _, _, c = _get_candle(candles[-1])
    if o is None or c is None:
        return False
    # confirmación: cierre con cuerpo fuera del borde correcto
    if side == "BUY":
        return c > zhigh and _body(o, c) > 0
    return c < zlow and _body(o, c) > 0


def _trigger_sweep_return(candles: List[Any], side: str, zlow: float, zhigh: float) -> bool:
    if len(candles) < 2:
        return False
    _, o, h, l, c = _get_candle(candles[-1])
    if h is None or l is None or c is None:
        return False
    # barrida + vuelta: atraviesa y cierra dentro
    if side == "BUY":
        return l < zlow and c >= zlow
    return h > zhigh and c <= zhigh


def _trigger_double_close(candles: List[Any], side: str, zlow: float, zhigh: float) -> bool:
    if len(candles) < 3:
        return False
    c1 = _get_candle(candles[-1])[4]
    c2 = _get_candle(candles[-2])[4]
    if c1 is None or c2 is None:
        return False
    if side == "BUY":
        return c2 > zhigh and c1 > zhigh
    return c2 < zlow and c1 < zlow


def _trigger_break_retest_simple(candles: List[Any], side: str, zlow: float, zhigh: float) -> bool:
    """
    Versión simple: si sale de zona y vuelve a testear borde y rechaza.
    BUY: cierre > zhigh en vela -2, luego vela -1 testea zhigh y cierra arriba.
    SELL: cierre < zlow en vela -2, luego vela -1 testea zlow y cierra abajo.
    """
    if len(candles) < 4:
        return False

    # vela -2 (ruptura)
    _, o2, h2, l2, c2 = _get_candle(candles[-2])
    # vela -1 (retest)
    _, o1, h1, l1, c1 = _get_candle(candles[-1])

    if c2 is None or h1 is None or l1 is None or c1 is None:
        return False

    if side == "BUY":
        broke = c2 > zhigh
        retest = l1 <= zhigh and c1 > zhigh
        return broke and retest

    broke = c2 < zlow
    retest = h1 >= zlow and c1 < zlow
    return broke and retest


def _pick_trigger(candles: List[Any], side: str, zlow: float, zhigh: float) -> Optional[str]:
    # Orden de prioridad (efectividad)
    if _trigger_sweep_return(candles, side, zlow, zhigh):
        return "SWEEP_RETURN"
    if _trigger_break_retest_simple(candles, side, zlow, zhigh):
        return "BREAK_RETEST"
    if _trigger_double_close(candles, side, zlow, zhigh):
        return "DOUBLE_CLOSE"
    if _trigger_close_confirm(candles, side, zlow, zhigh):
        return "CLOSE_CONFIRM"
    return None


# ============================================================
# SL/TP pro (simple y estable)
# ============================================================

def _calc_sl_tp(side: str, zlow: float, zhigh: float, entry: float, target: float) -> Tuple[float, float]:
    # SL técnico fuera de zona (buffer mínimo relativo)
    buf = max(abs(zhigh - zlow) * 0.20, 0.00001)
    if side == "BUY":
        sl = zlow - buf
        tp = max(target, entry + (entry - sl) * 1.2)  # target o 1.2R mínimo
        return float(sl), float(tp)
    sl = zhigh + buf
    tp = min(target, entry - (sl - entry) * 1.2)
    return float(sl), float(tp)


# ============================================================
# Engine principal
# ============================================================

_FIB = FibOptStore()

def build_atlas_ia_snapshot(
    *,
    symbol: str,
    tf: str,
    count: int,
    candles: List[Any],
    atlas_mode: Optional[str] = None,
    provider: Any = None,
) -> Dict[str, Any]:
    sym = str(symbol)
    tf_u = _u(tf)
    mode = _u(atlas_mode or "SCALPING")

    if not candles:
        return {
            "ok": True,
            "world": "ATLAS_IA",
            "symbol": sym,
            "tf": tf_u,
            "count": int(count),
            "atlas_mode": mode,
            "analysis": {
                "status": "NO_TRADE",
                "world": "ATLAS_IA",
                "symbol": sym,
                "tf": tf_u,
                "atlas_mode": mode,
                "provider": "mt5",
                "last_error": None,
                "msg": "no candles",
                "ts": _now_iso(),
            },
            "ui": {"rows": [{
                "symbol": sym, "tf": tf_u, "score": 0, "state": "WAIT",
                "entry": None, "sl": None, "tp": None, "lot": None, "reason": "NO_CANDLES"
            }]}
        }

    cfg = get_world_tf("ATLAS_IA", atlas_mode=mode, symbol=sym)
    analysis_tfs = [_u(x) for x in cfg.analysis_tfs]
    trigger_tfs = [_u(x) for x in cfg.trigger_tfs]

    last_px = _last_close(candles) or 0.0
    if last_px <= 0:
        return {
            "ok": True,
            "world": "ATLAS_IA",
            "symbol": sym,
            "tf": tf_u,
            "count": int(count),
            "atlas_mode": mode,
            "analysis": {
                "status": "NO_TRADE",
                "world": "ATLAS_IA",
                "symbol": sym,
                "tf": tf_u,
                "atlas_mode": mode,
                "provider": "mt5",
                "last_error": None,
                "msg": "bad price",
                "ts": _now_iso(),
            },
            "ui": {"rows": [{
                "symbol": sym, "tf": tf_u, "score": 0, "state": "WAIT",
                "entry": None, "sl": None, "tp": None, "lot": None, "reason": "BAD_PRICE"
            }]}
        }

    # --------------------------------------------------------
    # 1) FIB OPT update SOLO en TF de análisis
    # --------------------------------------------------------
    fib = _FIB.get(sym)
    msg_bits: List[str] = []

    if tf_u in analysis_tfs:
        piv = _detect_pivots(candles, left=2, right=2)
        ratios = _retro_ratios(piv)
        if len(ratios) >= 60:
            fib = _FIB.update_from_ratios(
                sym, ratios,
                p_opt=0.70,
                band=0.06,
                min_n=60,
                note="auto_from_live",
                auto_save=True,
            )
            msg_bits.append(f"fib_opt updated n={fib.n} opt={fib.opt_level:.3f}")
        else:
            msg_bits.append(f"fib_opt keep need>=60 now={len(ratios)}")

    # --------------------------------------------------------
    # 2) Plan Lock: si existe, lo usamos (NO recalcular zona)
    # --------------------------------------------------------
    p = get_plan(sym, tf_u, mode)

    # Si hay plan pero el precio ya invalidó fuerte (salió muy lejos), lo borramos
    if p and p.state == "WAIT_GATILLO":
        # invalidación simple: se alejó más de 2x ancho de zona en contra del plan
        zone_w = max(1e-9, p.zone_high - p.zone_low)
        if p.side == "BUY" and last_px < p.zone_low - 2.0 * zone_w:
            invalidate_plan(sym, tf_u, mode, reason="INVALID_BREAK_DOWN")
            p = None
        if p.side == "SELL" and last_px > p.zone_high + 2.0 * zone_w:
            invalidate_plan(sym, tf_u, mode, reason="INVALID_BREAK_UP")
            p = None

    # --------------------------------------------------------
    # 3) Si NO hay plan, construimos zona desde último impulso
    # --------------------------------------------------------
    z: Optional[Zone] = None
    if not p:
        z = _zone_from_last_impulse(candles, fib.opt_level, fib.band_low, fib.band_high)

        if not z:
            return {
                "ok": True,
                "world": "ATLAS_IA",
                "symbol": sym,
                "tf": tf_u,
                "count": int(count),
                "atlas_mode": mode,
                "analysis": {
                    "status": "OK",
                    "world": "ATLAS_IA",
                    "symbol": sym,
                    "tf": tf_u,
                    "atlas_mode": mode,
                    "provider": "mt5",
                    "last_error": None,
                    "msg": "WAIT (no zone)",
                    "ts": _now_iso(),
                    "tfs": {"analysis": analysis_tfs, "trigger": trigger_tfs},
                    "fib_opt": fib.to_dict(),
                },
                "ui": {"rows": [{
                    "symbol": sym, "tf": tf_u, "score": 10, "state": "WAIT",
                    "entry": None, "sl": None, "tp": None, "lot": None,
                    "reason": "NO_ZONE",
                }]}
            }

        # Si no está en zona: WAIT
        if not _in_zone(last_px, z.zone_low, z.zone_high):
            return {
                "ok": True,
                "world": "ATLAS_IA",
                "symbol": sym,
                "tf": tf_u,
                "count": int(count),
                "atlas_mode": mode,
                "analysis": {
                    "status": "OK",
                    "world": "ATLAS_IA",
                    "symbol": sym,
                    "tf": tf_u,
                    "atlas_mode": mode,
                    "provider": "mt5",
                    "last_error": None,
                    "msg": "WAIT (not in zone)",
                    "ts": _now_iso(),
                    "tfs": {"analysis": analysis_tfs, "trigger": trigger_tfs},
                    "fib_opt": fib.to_dict(),
                },
                "ui": {"rows": [{
                    "symbol": sym, "tf": tf_u, "score": 10, "state": "WAIT",
                    "entry": None, "sl": None, "tp": None, "lot": None,
                    "reason": "OUTSIDE_ZONE",
                    "plan": {
                        "side": z.side,
                        "zone_low": z.zone_low,
                        "zone_high": z.zone_high,
                        "target": z.target,
                        "opt_level": fib.opt_level,
                        "band_low": fib.band_low,
                        "band_high": fib.band_high,
                        "confidence": fib.confidence,
                        "n": fib.n,
                    }
                }]}
            }

        # Entró en zona: lock plan
        p = lock_plan(
            symbol=sym,
            tf=tf_u,
            atlas_mode=mode,
            side=z.side,
            zone_low=z.zone_low,
            zone_high=z.zone_high,
            opt_level=fib.opt_level,
            band_low=fib.band_low,
            band_high=fib.band_high,
            confidence=fib.confidence,
            n=fib.n,
            ttl_minutes=90,
            reason="PLAN_LOCKED_FIB_OPT",
        )

    # --------------------------------------------------------
    # 4) Si plan está locked y estamos en TF de gatillo -> buscar SIGNAL
    # --------------------------------------------------------
    if p and p.state == "WAIT_GATILLO":
        trig = None
        if tf_u in trigger_tfs:
            trig = _pick_trigger(candles, p.side, p.zone_low, p.zone_high)

        if trig:
            entry = float(last_px)
            sl, tp = _calc_sl_tp(p.side, p.zone_low, p.zone_high, entry, target=(p.zone_high if p.side == "BUY" else p.zone_low))
            # Nota: target más “serio” se puede mejorar luego usando pivots del TF análisis.
            p2 = set_signal(symbol=sym, tf=tf_u, atlas_mode=mode, entry=entry, sl=sl, tp=tp, trigger_used=trig) or p

            return {
                "ok": True,
                "world": "ATLAS_IA",
                "symbol": sym,
                "tf": tf_u,
                "count": int(count),
                "atlas_mode": mode,
                "analysis": {
                    "status": "OK",
                    "world": "ATLAS_IA",
                    "symbol": sym,
                    "tf": tf_u,
                    "atlas_mode": mode,
                    "provider": "mt5",
                    "last_error": None,
                    "msg": f"SIGNAL ({trig})",
                    "ts": _now_iso(),
                    "tfs": {"analysis": analysis_tfs, "trigger": trigger_tfs},
                    "fib_opt": fib.to_dict(),
                },
                "ui": {"rows": [{
                    "symbol": sym,
                    "tf": tf_u,
                    "score": 100,
                    "state": "SIGNAL",
                    "entry": p2.entry,
                    "sl": p2.sl,
                    "tp": p2.tp,
                    "lot": None,
                    "reason": f"SIGNAL_{trig}",
                    "plan": plan_to_dict(p2),
                }]}
            }

        # locked pero sin gatillo
        return {
            "ok": True,
            "world": "ATLAS_IA",
            "symbol": sym,
            "tf": tf_u,
            "count": int(count),
            "atlas_mode": mode,
            "analysis": {
                "status": "OK",
                "world": "ATLAS_IA",
                "symbol": sym,
                "tf": tf_u,
                "atlas_mode": mode,
                "provider": "mt5",
                "last_error": None,
                "msg": "WAIT_GATILLO locked",
                "ts": _now_iso(),
                "tfs": {"analysis": analysis_tfs, "trigger": trigger_tfs},
                "fib_opt": fib.to_dict(),
            },
            "ui": {"rows": [{
                "symbol": sym,
                "tf": tf_u,
                "score": 90,
                "state": "WAIT_GATILLO",
                "entry": None,
                "sl": None,
                "tp": None,
                "lot": None,
                "reason": p.reason or "PLAN_LOCKED",
                "plan": plan_to_dict(p),
            }]}
        }

    # --------------------------------------------------------
    # 5) Si por alguna razón ya estaba SIGNAL, devolvemos estable
    # --------------------------------------------------------
    if p and p.state == "SIGNAL":
        return {
            "ok": True,
            "world": "ATLAS_IA",
            "symbol": sym,
            "tf": tf_u,
            "count": int(count),
            "atlas_mode": mode,
            "analysis": {
                "status": "OK",
                "world": "ATLAS_IA",
                "symbol": sym,
                "tf": tf_u,
                "atlas_mode": mode,
                "provider": "mt5",
                "last_error": None,
                "msg": f"SIGNAL locked ({p.trigger_used or 'TRIGGER'})",
                "ts": _now_iso(),
                "tfs": {"analysis": analysis_tfs, "trigger": trigger_tfs},
                "fib_opt": fib.to_dict(),
            },
            "ui": {"rows": [{
                "symbol": sym,
                "tf": tf_u,
                "score": 100,
                "state": "SIGNAL",
                "entry": p.entry,
                "sl": p.sl,
                "tp": p.tp,
                "lot": None,
                "reason": "SIGNAL_LOCKED",
                "plan": plan_to_dict(p),
            }]}
        }

    # fallback
    return {
        "ok": True,
        "world": "ATLAS_IA",
        "symbol": sym,
        "tf": tf_u,
        "count": int(count),
        "atlas_mode": mode,
        "analysis": {
            "status": "OK",
            "world": "ATLAS_IA",
            "symbol": sym,
            "tf": tf_u,
            "atlas_mode": mode,
            "provider": "mt5",
            "last_error": None,
            "msg": "WAIT (fallback)",
            "ts": _now_iso(),
        },
        "ui": {"rows": [{
            "symbol": sym, "tf": tf_u, "score": 10, "state": "WAIT",
            "entry": None, "sl": None, "tp": None, "lot": None, "reason": "FALLBACK"
        }]}
    }