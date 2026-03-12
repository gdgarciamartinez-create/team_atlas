from __future__ import annotations

from dataclasses import dataclass

try:
    import MetaTrader5 as mt5
except Exception:
    mt5 = None


@dataclass
class RiskPlan:
    lots: float
    sl: float
    tp: float
    risk_percent: float


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def round_to_step(value: float, step: float) -> float:
    if step <= 0:
        return round(value, 2)
    return round(round(value / step) * step, 2)


def risk_percent_from_score(score: float) -> float:
    """
    Score >= 11 -> 1.5%
    Score >= 9  -> 1.0%
    Score >= 7  -> 0.5%
    Menor a 7   -> 0.0%
    """
    s = float(score or 0)

    if s >= 11:
        return 1.5
    if s >= 9:
        return 1.0
    if s >= 7:
        return 0.5
    return 0.0


def _fallback_lot_by_symbol(symbol: str) -> float:
    symbol = str(symbol or "").upper()

    if symbol.startswith("XAU"):
        return 0.01
    if symbol.startswith("BTC"):
        return 0.01
    if symbol.startswith("USTEC"):
        return 0.01
    if symbol.startswith("USOIL"):
        return 0.01
    return 0.01


def calc_lots(symbol: str, entry: float, sl: float, risk_percent: float = 1.0) -> float:
    if entry is None or sl is None:
        return 0.0

    if float(risk_percent or 0) <= 0:
        return 0.0

    if abs(float(entry) - float(sl)) <= 0:
        return 0.0

    if mt5 is None:
        return _fallback_lot_by_symbol(symbol)

    info = mt5.symbol_info(symbol)
    acc = mt5.account_info()

    if info is None or acc is None:
        return _fallback_lot_by_symbol(symbol)

    balance = float(acc.balance or 0)
    if balance <= 0:
        return float(getattr(info, "volume_min", 0.01) or 0.01)

    risk_money = balance * (float(risk_percent) / 100.0)

    price_distance = abs(float(entry) - float(sl))
    if price_distance <= 0:
        return float(getattr(info, "volume_min", 0.01) or 0.01)

    tick_value = float(getattr(info, "trade_tick_value", 0.0) or 0.0)
    tick_size = float(getattr(info, "trade_tick_size", 0.0) or 0.0)

    if tick_value <= 0 or tick_size <= 0:
        return float(getattr(info, "volume_min", 0.01) or 0.01)

    value_per_price = tick_value / tick_size
    if value_per_price <= 0:
        return float(getattr(info, "volume_min", 0.01) or 0.01)

    raw_lot = risk_money / (price_distance * value_per_price)

    volume_min = float(getattr(info, "volume_min", 0.01) or 0.01)
    volume_max = float(getattr(info, "volume_max", 100.0) or 100.0)
    volume_step = float(getattr(info, "volume_step", 0.01) or 0.01)

    lot = clamp(raw_lot, volume_min, volume_max)
    lot = round_to_step(lot, volume_step)
    lot = clamp(lot, volume_min, volume_max)

    return lot


def calc_lots_from_score(symbol: str, entry: float, sl: float, score: float) -> tuple[float, float]:
    rp = risk_percent_from_score(score)
    if rp <= 0:
        return 0.0, 0.0

    lots = calc_lots(symbol=symbol, entry=entry, sl=sl, risk_percent=rp)
    return lots, rp