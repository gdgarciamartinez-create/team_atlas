from __future__ import annotations

import time
from typing import Any, Dict, Tuple

from atlas.bot.worlds.feed import get_feed_with_meta
from atlas.bot.worlds.forex_world import build_forex_world


def _now_ms() -> int:
    return int(time.time() * 1000)


def _local_hm() -> Tuple[int, int]:
    lt = time.localtime()
    return int(lt.tm_hour), int(lt.tm_min)


def _in_window(h: int, m: int, start_h: int, start_m: int, end_h: int, end_m: int) -> bool:
    cur = h * 60 + m
    a = start_h * 60 + start_m
    b = end_h * 60 + end_m
    return a <= cur <= b


def build_presesion_world(symbol: str, tf: str, count: int = 220) -> Dict[str, Any]:
    """
    PRESESION:
    - Muestra velas siempre (para chart).
    - Pero SOLO habilita análisis “operable” dentro de la ventana previa NY.
    - Si está fuera de ventana => WAIT con razones (NO_TRADE).
    """
    candles, meta = get_feed_with_meta(symbol=symbol, tf=tf, n=count)
    price = float(candles[-1].get("c", 0.0)) if candles else 0.0

    h, m = _local_hm()

    # Ventana previa NY (Chile) - simple y editable:
    # Invierno: 06:00–07:00 (ejemplo corto)
    # Verano:   07:00–08:00
    # (Lo dejamos como “pre NY” reducido porque vos querés exactitud quirúrgica y pocos trades.)
    mode = (meta or {}).get("season_mode") or "WINTER"
    mode = str(mode).upper().strip()
    if mode not in ("WINTER", "SUMMER"):
        mode = "WINTER"

    if mode == "WINTER":
        ok_time = _in_window(h, m, 6, 0, 7, 0)
        window = "06:00-07:00"
    else:
        ok_time = _in_window(h, m, 7, 0, 8, 0)
        window = "07:00-08:00"

    if not ok_time:
        return {
            "ok": True,
            "world": "PRESESION",
            "symbol": symbol,
            "tf": tf,
            "ts_ms": _now_ms(),
            "candles": candles or [],
            "meta": {**(meta or {}), "window": window, "season_mode": mode},
            "state": "WAIT",
            "side": "WAIT",
            "price": float(price),
            "zone": (0.0, 0.0),
            "note": f"fuera de ventana pre NY ({window})",
            "score": 10,
            "light": "GRAY",
            "analysis": {
                "reason": "OUT_OF_WINDOW",
                "window": window,
                "season_mode": mode,
            },
            "ui": {
                "rows": [
                    {"k": "Estado", "v": "WAIT"},
                    {"k": "Nota", "v": f"fuera de ventana pre NY ({window})"},
                ]
            },
            "last_error": None,
        }

    # Dentro de ventana: delegamos al motor FOREX (multi-timeframe)
    base = build_forex_world(symbol=symbol, tf=tf if tf in ("M5", "M15") else "M5", count=count)
    # ajustamos marca
    base["world"] = "PRESESION"
    base_meta = base.get("meta", {}) if isinstance(base, dict) else {}
    if isinstance(base_meta, dict):
        base_meta["window"] = window
        base_meta["season_mode"] = mode
        base_meta["pre_ny"] = True
        base["meta"] = base_meta

    # Nota más directa
    if isinstance(base, dict):
        base["note"] = f"pre NY activo ({window}) | {base.get('note','')}"
    return base