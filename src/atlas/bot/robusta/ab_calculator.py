# src/atlas/bot/robusta/ab_calculator.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import csv
import os
import re
from datetime import datetime, timezone


Candle = Dict[str, Any]  # {"t": int, "o": float, "h": float, "l": float, "c": float, "v": float}


@dataclass
class ABResult:
    symbol: str
    tf: str
    n: int
    price_ref: float
    A_atr: float
    B_buffer: float
    AB: float
    meta: Dict[str, Any]


def _safe_float(x: Any) -> float:
    try:
        if x is None:
            return 0.0
        s = str(x).strip()
        if not s:
            return 0.0
        # MT5 suele venir con punto, pero igual protegemos comas
        s = s.replace(",", ".")
        return float(s)
    except Exception:
        return 0.0


def _parse_mt5_datetime(date_str: str, time_str: str) -> Optional[int]:
    """
    MT5 export típico:
      DATE = '2025.06.15'
      TIME = '22:00:00'
    """
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y.%m.%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return None


def load_candles_csv(path: str, limit: int = 5000) -> List[Candle]:
    """
    Lee CSV exportado por MT5:
    <DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>

    Soporta delimitador TAB (principal) y fallback a coma/; si viniera raro.
    """
    if not os.path.exists(path):
        return []

    # Leemos un sample para detectar delimiter
    with open(path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        sample = f.read(4096)
        f.seek(0)

        # Detect delimiter: MT5 es tab casi siempre
        delimiter = "\t"
        if "\t" not in sample:
            # fallback simple
            if ";" in sample and "," not in sample:
                delimiter = ";"
            elif "," in sample:
                delimiter = ","

        reader = csv.reader(f, delimiter=delimiter)
        rows = []
        for row in reader:
            if not row:
                continue
            rows.append(row)
            if len(rows) >= (limit + 5):  # header + margen
                break

    if not rows:
        return []

    # Header puede venir como <DATE> <TIME> etc, a veces con <>.
    header = [c.strip() for c in rows[0]]
    header_norm = [re.sub(r"[<> ]+", "", h).upper() for h in header]

    def idx(name: str) -> int:
        name = name.upper()
        try:
            return header_norm.index(name)
        except ValueError:
            return -1

    i_date = idx("DATE")
    i_time = idx("TIME")
    i_open = idx("OPEN")
    i_high = idx("HIGH")
    i_low = idx("LOW")
    i_close = idx("CLOSE")
    i_tickvol = idx("TICKVOL")
    i_vol = idx("VOL")

    # Validación mínima
    if min(i_date, i_time, i_open, i_high, i_low, i_close) < 0:
        return []

    candles: List[Candle] = []
    for r in rows[1:]:
        if len(r) < len(header):
            # si viene cortada, saltamos
            continue

        t = _parse_mt5_datetime(r[i_date], r[i_time])
        if t is None:
            continue

        o = _safe_float(r[i_open])
        h = _safe_float(r[i_high])
        l = _safe_float(r[i_low])
        c = _safe_float(r[i_close])

        # volumen: preferimos tickvol, si no vol
        v = 0.0
        if i_tickvol >= 0:
            v = _safe_float(r[i_tickvol])
        elif i_vol >= 0:
            v = _safe_float(r[i_vol])

        candles.append({"t": t, "o": o, "h": h, "l": l, "c": c, "v": v})

        if len(candles) >= limit:
            break

    return candles


def _atr(candles: List[Candle], period: int = 14) -> float:
    if len(candles) < (period + 2):
        return 0.0

    trs: List[float] = []
    prev_close = candles[0]["c"]
    for k in range(1, len(candles)):
        h = float(candles[k]["h"])
        l = float(candles[k]["l"])
        c_prev = float(prev_close)
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        trs.append(tr)
        prev_close = candles[k]["c"]

    if len(trs) < period:
        return 0.0

    window = trs[-period:]
    return float(sum(window) / period)


def calc_A_B(
    candles: List[Candle],
    atr_period: int = 14,
    b_price_pct: float = 0.0005,   # 0.05% = 0.0005
    b_atr_mult: float = 0.2,
) -> Tuple[int, float, float, float, float, Dict[str, Any]]:
    """
    Devuelve:
      n, price_ref, A_atr, B_buffer, AB, meta

    Definición:
      A = ATR(atr_period)
      B = max(price_ref * b_price_pct, A * b_atr_mult)
      AB = A + B
    """
    if not candles:
        return 0, 0.0, 0.0, 0.0, 0.0, {"reason": "no_candles_loaded"}

    n = len(candles)
    price_ref = float(candles[-1]["c"])  # último close
    A = _atr(candles, period=atr_period)

    # Buffer mínimo por precio vs por ATR
    b_by_price = abs(price_ref) * float(b_price_pct)
    b_by_atr = float(A) * float(b_atr_mult)
    B = float(max(b_by_price, b_by_atr))

    AB = float(A + B)

    meta = {
        "atr_period": int(atr_period),
        "b_price_pct": float(b_price_pct),
        "b_atr_mult": float(b_atr_mult),
        "b_by_price": float(b_by_price),
        "b_by_atr": float(b_by_atr),
    }
    return n, price_ref, A, B, AB, meta