from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SymbolConfig:
    symbol: str
    pip_size: float
    min_lot: float
    lot_step: float
    max_spread_points: Optional[float] = None  # si lo tienes en MT5, aplica filtro
    tp_mode: str = "FIBO"  # FIBO | GAP_CLOSE
    gap_threshold_pct: float = 0.0015

# Ajusta según tu broker/MT5
SYMBOL_CFG: Dict[str, SymbolConfig] = {
    "EURUSD": SymbolConfig("EURUSD", pip_size=0.0001, min_lot=0.01, lot_step=0.01),
    "GBPUSD": SymbolConfig("GBPUSD", pip_size=0.0001, min_lot=0.01, lot_step=0.01),
    "USDJPY": SymbolConfig("USDJPY", pip_size=0.01,   min_lot=0.01, lot_step=0.01),
    "EURJPY": SymbolConfig("EURJPY", pip_size=0.01,   min_lot=0.01, lot_step=0.01),
    "XAUUSD": SymbolConfig("XAUUSD", pip_size=0.1,    min_lot=0.01, lot_step=0.01, tp_mode="GAP_CLOSE", gap_threshold_pct=0.0015),
    "NAS100": SymbolConfig("NAS100", pip_size=1.0,    min_lot=0.01, lot_step=0.01),
}

def round_to_step(value: float, step: float) -> float:
    if step <= 0:
        return value
    return round(round(value / step) * step, 6)

def normalize_lots(symbol: str, lots: float) -> float:
    cfg = SYMBOL_CFG.get(symbol)
    if not cfg:
        return max(0.01, round(lots, 2))
    lots = max(cfg.min_lot, lots)
    lots = round_to_step(lots, cfg.lot_step)
    return float(lots)