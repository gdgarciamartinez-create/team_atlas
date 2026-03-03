from __future__ import annotations

from typing import Any, Dict, List, Optional
import time

from atlas.api.feed import get_candles_payload

# Estado simple por (world,symbol,tf) para congelar plan si lo necesitás después
try:
    from atlas.bot.state import get_world_state, set_world_state  # opcional
except Exception:
    get_world_state = None  # type: ignore
    set_world_state = None  # type: ignore


def _now_ms() -> int:
    return int(time.time() * 1000)


def _safe_candles_from_payload(payload: Any) -> List[Dict[str, Any]]:
    """
    A prueba de balas:
    - Si payload es dict y tiene "candles": devuelve esa lista
    - Si ya es lista: devuelve lista
    - Si viene cualquier cosa: []
    """
    if isinstance(payload, list):
        return payload  # ya es lista de velas

    if isinstance(payload, dict):
        c = payload.get("candles", [])
        if isinstance(c, list):
            return c
        return []

    return []


def _micro_ruptura_hint(candles: List[Dict[str, Any]]) -> Optional[str]:
    """
    Señal MUY simple (solo para no dejar todo muerto):
    - Si las últimas 3 velas rompen máximos crecientes o mínimos decrecientes con cierres,
      devolvemos "Micro ruptura".
    """
    if len(candles) < 10:
        return None

    last = candles[-5:]
    closes = [float(x.get("c", 0.0)) for x in last if "c" in x]
    highs = [float(x.get("h", 0.0)) for x in last if "h" in x]
    lows = [float(x.get("l", 0.0)) for x in last if "l" in x]

    if len(closes) < 5 or len(highs) < 5 or len(lows) < 5:
        return None

    # ruptura alcista: cierres suben y rompen el high previo
    if closes[-1] > closes[-2] > closes[-3] and highs[-1] > max(highs[:-1]):
        return "Micro ruptura"

    # ruptura bajista: cierres bajan y rompen el low previo
    if closes[-1] < closes[-2] < closes[-3] and lows[-1] < min(lows[:-1]):
        return "Micro ruptura"

    return None


def build_snapshot(
    *,
    world: str,
    atlas_mode: Optional[str],
    symbol: Optional[str],
    tf: Optional[str],
    count: int = 220,
) -> Dict[str, Any]:
    """
    Builder central (robusto) que arma el payload que consume la UI.
    NO debe romper nunca.
    """
    w = (world or "").strip()
    m = (atlas_mode or "").strip() if atlas_mode else ""
    s = (symbol or "").strip()
    t = (tf or "").strip().upper()

    # Defaults coherentes
    if not s:
        s = "XAUUSDz"
    if not t:
        # si es scalping_m1/m5 lo inferimos
        if "M1" in m.upper():
            t = "M1"
        elif "M5" in m.upper():
            t = "M5"
        else:
            t = "M5"

    # 1) Pedimos velas al feed (MT5 o fallback)
    feed_payload = get_candles_payload(world=w, symbol=s, tf=t, count=int(count or 220))
    candles = _safe_candles_from_payload(feed_payload)

    # 2) Opcional: estado por mundo/símbolo/tf
    st: Dict[str, Any] = {}
    if get_world_state is not None:
        try:
            st = get_world_state(world=w, symbol=s, tf=t)  # type: ignore
        except Exception:
            st = {}

    # 3) Análisis mínimo (por ahora)
    detail = _micro_ruptura_hint(candles)
    if detail:
        analysis = {"status": "SIGNAL", "reason": "SIGNAL", "detail": detail}
    else:
        analysis = {"status": "NO_TRADE", "reason": "OK", "detail": "Sin gatillo"}

    # 4) Si querés congelar cosas a futuro, dejamos hook listo
    if set_world_state is not None:
        try:
            set_world_state(world=w, symbol=s, tf=t, state=st)  # type: ignore
        except Exception:
            pass

    return {
        "world": w,
        "atlas_mode": m or None,
        "symbol": s,
        "tf": t,
        "ts_ms": _now_ms(),
        "candles": candles,
        "analysis": analysis,
        "ui": {
            "rows": [],
            "meta": {
                "note": "ok",
                "feed_source": feed_payload.get("source") if isinstance(feed_payload, dict) else "unknown",
            },
        },
    }