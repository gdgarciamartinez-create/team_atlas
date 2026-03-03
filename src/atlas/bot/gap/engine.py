from __future__ import annotations

from typing import Any, Dict, Tuple
import os
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo


TZ = ZoneInfo("America/Santiago")


def _season() -> str:
    # Si no existe, por defecto SUMMER (como venías usando)
    s = (os.getenv("ATLAS_CHILE_SEASON") or "SUMMER").upper().strip()
    return "WINTER" if s == "WINTER" else "SUMMER"


def _window_for(season: str) -> Tuple[dtime, dtime]:
    # SUMMER: 19:55–20:30 (apertura ~20:00)
    # WINTER: 18:55–19:30 (1h menos)
    if season == "WINTER":
        return dtime(18, 55), dtime(19, 30)
    return dtime(19, 55), dtime(20, 30)


def _hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def _in_window(now: datetime, start: dtime, end: dtime) -> bool:
    nt = now.time()
    return (nt >= start) and (nt <= end)


def eval_gap(md: Dict[str, Any], raw_query: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    GAP = mundo independiente dentro del orden ATLAS_IA (atlas_mode=GAP)
    - Fuera de ventana: SLEEP (meta.sleep=true)
    - Dentro de ventana: WAIT (monitoreando)
    - Si no hay data: NO_TRADE (NO_DATA) sin inventar
    """
    season = _season()
    start, end = _window_for(season)
    now = datetime.now(TZ)

    symbol = str(raw_query.get("symbol") or "")
    tf = str(raw_query.get("tf") or "M5").upper().strip()

    candles = md.get("candles") or []
    price = float(md.get("price") or 0.0)

    window_str = f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"

    # 1) Fuera de ventana: dormir
    if not _in_window(now, start, end):
        analysis = {
            "world": "GAP",
            "status": "SLEEP",
            "state": "SLEEP",
            "reason": "OUT_OF_GAP_WINDOW",
            "season": season,
            "now": _hhmm(now),
            "window": window_str,
            "note": "Fuera de ventana GAP",
            "side": "WAIT",
            "entry": 0.0,
            "sl": 0.0,
            "tp": 0.0,
        }
        ui = {
            "rows": [
                {"k": "Estado", "v": "SLEEP"},
                {"k": "Temporada", "v": season},
                {"k": "Hora", "v": _hhmm(now)},
                {"k": "Ventana", "v": window_str},
                {"k": "Nota", "v": "Fuera de ventana GAP"},
            ],
            "meta": {"sleep": True},
        }
        return analysis, ui

    # 2) Dentro de ventana: si no hay data, no inventar
    if not candles or price <= 0:
        analysis = {
            "world": "GAP",
            "status": "NO_TRADE",
            "state": "WAIT",
            "reason": "NO_DATA",
            "season": season,
            "now": _hhmm(now),
            "window": window_str,
            "note": "Ventana activa, pero sin velas (mercado cerrado o provider vacío)",
            "side": "WAIT",
            "entry": 0.0,
            "sl": 0.0,
            "tp": 0.0,
        }
        ui = {
            "rows": [
                {"k": "Estado", "v": "WAIT"},
                {"k": "Temporada", "v": season},
                {"k": "Hora", "v": _hhmm(now)},
                {"k": "Ventana", "v": window_str},
                {"k": "Nota", "v": "NO_TRADE: sin velas"},
            ],
            "meta": {"sleep": False, "window_active": True},
        }
        return analysis, ui

    # 3) Dentro de ventana con data: monitoreo (todavía sin lógica de escenario)
    analysis = {
        "world": "GAP",
        "status": "OK",
        "state": "WAIT",
        "reason": "MONITOR",
        "season": season,
        "now": _hhmm(now),
        "window": window_str,
        "symbol": symbol,
        "tf": tf,
        "note": "Ventana activa: monitoreando GAP",
        "side": "WAIT",
        "entry": 0.0,
        "sl": 0.0,
        "tp": 0.0,
    }
    ui = {
        "rows": [
            {"k": "Estado", "v": "WAIT"},
            {"k": "Temporada", "v": season},
            {"k": "Hora", "v": _hhmm(now)},
            {"k": "Ventana", "v": window_str},
            {"k": "Precio", "v": price},
            {"k": "Nota", "v": "Ventana activa: monitoreando GAP"},
        ],
        "meta": {"sleep": False, "window_active": True},
    }
    return analysis, ui