from __future__ import annotations
from typing import List, Tuple


def fibo_0_786_zone(high: float, low: float, direction: str, pad: float = 0.0) -> Tuple[float, float]:
    """
    Devuelve la zona alrededor del 0.786 (solo 0.786, sin 0.79).
    - direction "UP": retroceso desde high hacia low
    - direction "DOWN": retroceso desde low hacia high
    """
    if high <= low:
        return (0.0, 0.0)

    rng = high - low

    if direction == "UP":
        lvl = high - rng * 0.786
    elif direction == "DOWN":
        lvl = low + rng * 0.786
    else:
        return (0.0, 0.0)

    z_low = lvl - pad
    z_high = lvl + pad
    if z_low > z_high:
        z_low, z_high = z_high, z_low
    return (z_low, z_high)


def touched_zone_last(prices: List[float], z_low: float, z_high: float, lookback: int = 3) -> bool:
    """
    ¿Alguno de los últimos N precios tocó la zona?
    prices: lista de precios (ej cierres o lows/highs según tu uso)
    """
    if not prices or lookback <= 0:
        return False

    recent = prices[-lookback:]
    for p in recent:
        if z_low <= p <= z_high:
            return True
    return False


def closes_outside_zone_against(
    closes: List[float],
    z_low: float,
    z_high: float,
    direction: str,
    consecutive: int = 2
) -> bool:
    """
    Regla timing: "Dos cierres consecutivos con cuerpo fuera de la zona invalidan la hipótesis contraria (aceptación)."

    Interpretación:
    - Si esperás reacción UP (direction="UP") pero el precio CIERRA por DEBAJO de la zona (z_low),
      eso es "en contra" de la hipótesis. Si pasa N veces seguidas => invalidación.
    - Si esperás reacción DOWN (direction="DOWN") pero el precio CIERRA por ENCIMA de la zona (z_high),
      eso es "en contra" de la hipótesis. N cierres seguidos => invalidación.
    """
    if not closes or consecutive <= 0:
        return False

    recent = closes[-consecutive:]

    if direction == "UP":
        return all(c < z_low for c in recent)

    if direction == "DOWN":
        return all(c > z_high for c in recent)

    return False
