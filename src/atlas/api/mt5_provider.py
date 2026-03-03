"""
Shim de compatibilidad.

Hay partes del proyecto (o código legacy) que intentan:
    from atlas.api.mt5_provider import get_candles_payload

Pero el archivo real está en:
    atlas.api.routes.mt5_provider

Este módulo re-exporta la función para que nunca vuelva a romper.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def get_candles_payload(
    *,
    world: str,
    symbol: str,
    tf: str,
    count: int = 220,
) -> Dict[str, Any]:
    # Import diferido para evitar ciclos
    from atlas.api.routes.mt5_provider import get_candles_payload as _impl

    return _impl(world=world, symbol=symbol, tf=tf, count=count)