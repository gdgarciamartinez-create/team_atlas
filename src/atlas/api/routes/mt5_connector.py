# src/atlas/data/mt5_connector.py
from __future__ import annotations

from typing import Any, Dict, Tuple, Optional
import MetaTrader5 as mt5

from atlas.data.symbol_map import resolve_symbol


class MT5Connector:
    """
    Conector simple y estable:
    - inicializa MT5
    - resuelve símbolo ATLAS -> MT5
    - asegura visibilidad (symbol_select)
    - trae velas (rates)
    """

    def __init__(self) -> None:
        self.connected = False

    def connect(self) -> Tuple[bool, str]:
        if self.connected:
            return True, "ALREADY_CONNECTED"
        ok = mt5.initialize()
        if not ok:
            return False, f"INIT_FAIL: {mt5.last_error()}"
        self.connected = True
        return True, "OK"

    def shutdown(self) -> None:
        try:
            mt5.shutdown()
        finally:
            self.connected = False

    def ensure_symbol(self, atlas_symbol: str) -> Tuple[bool, str, str]:
        mt5_symbol = resolve_symbol(atlas_symbol)

        info = mt5.symbol_info(mt5_symbol)
        if info is None:
            return False, f"SYMBOL_NOT_FOUND: {atlas_symbol} -> {mt5_symbol}", mt5_symbol

        if not info.visible:
            if not mt5.symbol_select(mt5_symbol, True):
                return False, f"SYMBOL_NOT_VISIBLE: {mt5_symbol}", mt5_symbol

        return True, "OK", mt5_symbol

    def get_rates(
        self, atlas_symbol: str, timeframe: int, count: int = 200
    ) -> Tuple[Optional[Any], str, str]:
        ok, reason, mt5_symbol = self.ensure_symbol(atlas_symbol)
        if not ok:
            return None, reason, mt5_symbol

        rates = mt5.copy_rates_from_pos(mt5_symbol, timeframe, 0, int(count))
        if rates is None:
            return None, f"RATES_FAIL: {atlas_symbol} -> {mt5_symbol} | {mt5.last_error()}", mt5_symbol

        return rates, "OK", mt5_symbol

    def terminal_info(self) -> Dict[str, Any]:
        ti = mt5.terminal_info()
        return {} if ti is None else ti._asdict()


# -------------------------
# COMPATIBILIDAD (CLAVE)
# -------------------------
# Muchos archivos legacy aún importan: MT5, mt5_symbol
# Esto evita que Uvicorn muera.
MT5 = MT5Connector

def mt5_symbol(atlas_symbol: str) -> str:
    return resolve_symbol(atlas_symbol)
