# src/atlas/bot/analysis/elliott.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ElliottLabel:
    mode: str  # "IMPULSE" | "CORRECTION" | "FLAG" | "UNKNOWN"
    stage: str  # "W3"|"W4"|"W5"|"A"|"B"|"C"|"FLAG_BULL"|"FLAG_BEAR"|"..."
    confidence: float  # 0..1
    note: str


def _c(o: Dict[str, Any], k: str, d: float = 0.0) -> float:
    try:
        return float(o.get(k, d))
    except Exception:
        return d


def _ohlc(c: Dict[str, Any]) -> Tuple[float, float, float, float]:
    return _c(c, "o"), _c(c, "h"), _c(c, "l"), _c(c, "c")


def _fractal_pivots(candles: List[Dict[str, Any]], left: int = 2, right: int = 2) -> List[Tuple[int, str, float]]:
    """
    Pivotes simples tipo fractal:
      - HIGH pivot: H[i] mayor que H[i-left..i-1] y H[i+1..i+right]
      - LOW  pivot: L[i] menor que L[i-left..i-1] y L[i+1..i+right]
    Devuelve: [(idx, "H"/"L", price), ...]
    """
    n = len(candles)
    if n < left + right + 5:
        return []

    piv: List[Tuple[int, str, float]] = []
    for i in range(left, n - right):
        hi = _c(candles[i], "h")
        lo = _c(candles[i], "l")

        ok_hi = True
        ok_lo = True
        for j in range(i - left, i):
            if _c(candles[j], "h") >= hi:
                ok_hi = False
            if _c(candles[j], "l") <= lo:
                ok_lo = False
        for j in range(i + 1, i + right + 1):
            if _c(candles[j], "h") >= hi:
                ok_hi = False
            if _c(candles[j], "l") <= lo:
                ok_lo = False

        if ok_hi:
            piv.append((i, "H", hi))
        if ok_lo:
            piv.append((i, "L", lo))

    # orden y limpieza: evitar pivotes consecutivos iguales quedándonos con el más extremo
    piv.sort(key=lambda x: x[0])
    cleaned: List[Tuple[int, str, float]] = []
    for p in piv:
        if not cleaned:
            cleaned.append(p)
            continue
        last = cleaned[-1]
        if p[1] != last[1]:
            cleaned.append(p)
            continue
        # mismo tipo: mantener el más extremo
        if p[1] == "H":
            if p[2] > last[2]:
                cleaned[-1] = p
        else:
            if p[2] < last[2]:
                cleaned[-1] = p

    return cleaned[-12:]  # suficiente para etiquetar


def _range(a: float, b: float) -> float:
    return abs(a - b)


def detect_elliott_pro(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Elliott PRO (heurístico, robusto, sin “conteo perfecto”):
    - Detecta si el tramo reciente parece: impulso (W3/W4/W5), corrección (ABC) o bandera.
    - Se usa como CONTEXTO y FILTRO de score, no como gatillo único.
    """
    if len(candles) < 80:
        lab = ElliottLabel("UNKNOWN", "UNKNOWN", 0.0, "pocas velas")
        return {"label": asdict(lab), "pivots": []}

    piv = _fractal_pivots(candles, left=2, right=2)
    if len(piv) < 6:
        lab = ElliottLabel("UNKNOWN", "UNKNOWN", 0.15, "sin pivotes suficientes")
        return {"label": asdict(lab), "pivots": piv}

    # Tomamos los últimos pivotes alternados para inferir estructura
    # Buscamos patrones tipo:
    # Impulso alcista: L-H-L-H-L-H (máximos crecientes y mínimos crecientes)
    # Impulso bajista: H-L-H-L-H-L (mínimos decrecientes y máximos decrecientes)
    recent = piv[-6:]
    types = [t for _, t, _ in recent]
    prices = [p for _, _, p in recent]

    def inc(xs: List[float]) -> bool:
        return all(xs[i] < xs[i + 1] for i in range(len(xs) - 1))

    def dec(xs: List[float]) -> bool:
        return all(xs[i] > xs[i + 1] for i in range(len(xs) - 1))

    # separar highs y lows
    highs = [prices[i] for i in range(len(recent)) if types[i] == "H"]
    lows = [prices[i] for i in range(len(recent)) if types[i] == "L"]

    # bandera: rango estrecho + ruptura reciente
    last_40 = candles[-40:]
    hi40 = max(_c(x, "h") for x in last_40)
    lo40 = min(_c(x, "l") for x in last_40)
    rng40 = max(hi40 - lo40, 1e-9)
    body_sum = 0.0
    for x in last_40:
        o, _, _, c = _ohlc(x)
        body_sum += abs(c - o)
    body_avg = body_sum / max(len(last_40), 1)
    tight = body_avg < (rng40 * 0.10)

    # impulso alcista/bajista
    bull_imp = (types in (["L", "H", "L", "H", "L", "H"], ["L", "H", "L", "H", "L", "H"])) and inc(highs) and inc(lows)
    bear_imp = (types in (["H", "L", "H", "L", "H", "L"], ["H", "L", "H", "L", "H", "L"])) and dec(highs) and dec(lows)

    # corrección ABC: tres tramos contra el impulso previo
    # Simplificación: si el último tramo rompe la estructura del impulso (W5 agotada) y hay zigzag
    # Usamos ratio de tramos: A y C similares.
    def abc_like() -> Optional[str]:
        if len(piv) < 8:
            return None
        p8 = piv[-8:]
        t8 = [t for _, t, _ in p8]
        pr8 = [p for _, _, p in p8]
        # zigzag alternado siempre
        if any(t8[i] == t8[i + 1] for i in range(len(t8) - 1)):
            return None
        # tramo A ~ C en tamaño
        a = _range(pr8[-8], pr8[-7])
        b = _range(pr8[-7], pr8[-6])
        c = _range(pr8[-6], pr8[-5])
        # tolerancia amplia
        if a > 0 and c > 0 and (0.6 <= (c / a) <= 1.6) and b > (0.35 * a):
            return "ABC"
        return None

    abc = abc_like()

    # Etiquetado final
    if tight:
        # Bandera bull/bear por inclinación simple
        c_last = _c(candles[-1], "c")
        c_prev = _c(candles[-20], "c")
        if c_last >= c_prev:
            lab = ElliottLabel("FLAG", "FLAG_BULL", 0.55, "consolidación estrecha (bandera alcista probable)")
        else:
            lab = ElliottLabel("FLAG", "FLAG_BEAR", 0.55, "consolidación estrecha (bandera bajista probable)")
        return {"label": asdict(lab), "pivots": piv}

    if bull_imp:
        # W3/W4/W5 por posición relativa: si el último high está muy extendido → W5
        ext = (highs[-1] - lows[-1]) / max(highs[-1] - lows[0], 1e-9)
        if ext > 0.65:
            lab = ElliottLabel("IMPULSE", "W5", 0.68, "impulso alcista extendido (W5 probable)")
        else:
            lab = ElliottLabel("IMPULSE", "W3", 0.62, "impulso alcista en desarrollo (W3/W4 probable)")
        return {"label": asdict(lab), "pivots": piv}

    if bear_imp:
        ext = (lows[0] - highs[-1]) / max(highs[0] - lows[-1], 1e-9)
        if ext > 0.65:
            lab = ElliottLabel("IMPULSE", "W5", 0.68, "impulso bajista extendido (W5 probable)")
        else:
            lab = ElliottLabel("IMPULSE", "W3", 0.62, "impulso bajista en desarrollo (W3/W4 probable)")
        return {"label": asdict(lab), "pivots": piv}

    if abc == "ABC":
        lab = ElliottLabel("CORRECTION", "ABC", 0.58, "corrección tipo ABC probable (zigzag)")
        return {"label": asdict(lab), "pivots": piv}

    lab = ElliottLabel("UNKNOWN", "UNKNOWN", 0.25, "estructura mixta (transición/ruido)")
    return {"label": asdict(lab), "pivots": piv}