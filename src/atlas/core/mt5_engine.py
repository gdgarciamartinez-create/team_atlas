# src/atlas/core/mt5_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import time

try:
    import MetaTrader5 as mt5
except Exception as e:
    mt5 = None


TF_MAP = {
    "M1": 1,
    "M2": 2,
    "M3": 3,
    "M4": 4,
    "M5": 5,
    "M6": 6,
    "M10": 10,
    "M12": 12,
    "M15": 15,
    "M20": 20,
    "M30": 30,
    "H1": 60,
    "H2": 120,
    "H4": 240,
    "D1": 1440,
}

def _tf_to_mt5(tf: str):
    # mt5 tiene constantes, pero podemos mapear por minutos con TIMEFRAME_M1 etc.
    if mt5 is None:
        return None
    tf = (tf or "M5").upper().strip()
    if tf == "M1": return mt5.TIMEFRAME_M1
    if tf == "M2": return mt5.TIMEFRAME_M2
    if tf == "M3": return mt5.TIMEFRAME_M3
    if tf == "M4": return mt5.TIMEFRAME_M4
    if tf == "M5": return mt5.TIMEFRAME_M5
    if tf == "M6": return mt5.TIMEFRAME_M6
    if tf == "M10": return mt5.TIMEFRAME_M10
    if tf == "M12": return mt5.TIMEFRAME_M12
    if tf == "M15": return mt5.TIMEFRAME_M15
    if tf == "M20": return mt5.TIMEFRAME_M20
    if tf == "M30": return mt5.TIMEFRAME_M30
    if tf == "H1": return mt5.TIMEFRAME_H1
    if tf == "H2": return mt5.TIMEFRAME_H2
    if tf == "H4": return mt5.TIMEFRAME_H4
    if tf == "D1": return mt5.TIMEFRAME_D1
    # default
    return mt5.TIMEFRAME_M5


@dataclass
class Mt5Status:
    ok: bool
    initialized: bool
    authorized: bool
    terminal: Optional[str]
    last_error: str
    symbols_count: int


class Mt5Engine:
    def __init__(self):
        self.last_error: str = ""
        self._initialized_once = False

    def _set_err(self, msg: str):
        self.last_error = msg

    def ensure_initialized(self) -> bool:
        if mt5 is None:
            self._set_err("MetaTrader5 package not available (pip install MetaTrader5)")
            return False

        # Si ya está inicializado, ok
        if mt5.terminal_info() is not None and mt5.account_info() is not None:
            self._initialized_once = True
            return True

        # Intentar inicializar
        ok = mt5.initialize()
        if not ok:
            code, detail = mt5.last_error()
            self._set_err(f"MT5 initialize failed: ({code}, {detail})")
            return False

        self._initialized_once = True

        # Validar autorización
        acc = mt5.account_info()
        if acc is None:
            code, detail = mt5.last_error()
            self._set_err(f"MT5 account_info failed: ({code}, {detail})")
            return False

        return True

    def status(self) -> Mt5Status:
        if mt5 is None:
            return Mt5Status(
                ok=False, initialized=False, authorized=False,
                terminal=None, last_error=self.last_error or "MetaTrader5 not installed",
                symbols_count=0
            )

        initialized = mt5.terminal_info() is not None
        authorized = mt5.account_info() is not None
        term = None
        try:
            ti = mt5.terminal_info()
            term = getattr(ti, "path", None) if ti else None
        except Exception:
            term = None

        symbols_count = 0
        try:
            syms = mt5.symbols_get()
            symbols_count = len(syms) if syms else 0
        except Exception:
            symbols_count = 0

        ok = initialized and authorized
        return Mt5Status(
            ok=ok,
            initialized=initialized,
            authorized=authorized,
            terminal=term,
            last_error=self.last_error,
            symbols_count=symbols_count,
        )

    def symbols(self, suffix: str = "z") -> List[str]:
        if not self.ensure_initialized():
            return []
        syms = mt5.symbols_get()
        if not syms:
            return []
        suffix = suffix or ""
        out = []
        for s in syms:
            name = getattr(s, "name", "")
            if suffix and name.endswith(suffix):
                out.append(name)
        # orden bonito
        out.sort()
        return out

    def candles(self, symbol: str, tf: str, count: int) -> List[Dict[str, Any]]:
        if not self.ensure_initialized():
            return []

        symbol = (symbol or "").strip()
        if not symbol:
            self._set_err("Symbol empty")
            return []

        # Asegurar que el símbolo esté visible
        info = mt5.symbol_info(symbol)
        if info is None:
            code, detail = mt5.last_error()
            self._set_err(f"Symbol not found in MT5: {symbol} ({code}, {detail})")
            return []
        if not info.visible:
            mt5.symbol_select(symbol, True)

        timeframe = _tf_to_mt5(tf)
        if timeframe is None:
            self._set_err("Timeframe invalid")
            return []

        count = int(count or 120)
        count = max(10, min(count, 2000))

        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None:
            code, detail = mt5.last_error()
            self._set_err(f"copy_rates_from_pos failed: ({code}, {detail})")
            return []

        out = []
        for r in rates:
            # r['time'] viene en segundos unix
            out.append({
                "time": int(r["time"]),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "tick_volume": int(r["tick_volume"]),
            })
        return out


ENGINE = Mt5Engine()