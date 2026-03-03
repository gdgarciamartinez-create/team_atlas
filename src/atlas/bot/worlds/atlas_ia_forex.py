from __future__ import annotations

from typing import Any, Callable, Dict, Optional


def _pick_forex_builder() -> Optional[Callable[..., Dict[str, Any]]]:
    """
    Intenta encontrar una función “builder” real en forex_world sin romper.
    Soporta varios nombres comunes.
    """
    try:
        import atlas.bot.worlds.forex_world as fw  # type: ignore
    except Exception:
        return None

    # Lista de candidatos (del más probable al menos probable)
    candidates = [
        "build_forex_world",
        "build_forex_snapshot",
        "build_forex_world_snapshot",
        "build_forex",
    ]

    for name in candidates:
        fn = getattr(fw, name, None)
        if callable(fn):
            return fn  # type: ignore

    return None


def build_forex_snapshot() -> Dict[str, Any]:
    """
    Isla FOREX (TF mayores). No mezcla con scalping.
    Si no encuentra builder real, devuelve payload vacío válido.
    """
    builder = _pick_forex_builder()

    # Default razonable (podés cambiarlo después)
    symbol = "EURUSDz"
    tf = "H1"

    if builder is None:
        return {
            "ok": True,
            "world": "ATLAS_IA",
            "atlas_mode": "FOREX",
            "analysis": {"status": "NO_TRADE", "reason": "FOREX_BUILDER_NOT_FOUND"},
            "ui": {"rows": [], "meta": {"note": "No forex builder found in atlas.bot.worlds.forex_world"}},
        }

    # Llamada tolerante a distintas firmas
    try:
        # Intento 1: builder(symbol=..., tf=...)
        payload = builder(symbol=symbol, tf=tf)  # type: ignore
    except TypeError:
        try:
            # Intento 2: builder(symbol, tf)
            payload = builder(symbol, tf)  # type: ignore
        except TypeError:
            # Intento 3: builder() sin args
            payload = builder()  # type: ignore

    if not isinstance(payload, dict):
        payload = {}

    payload["world"] = "ATLAS_IA"
    payload["atlas_mode"] = "FOREX"
    return payload