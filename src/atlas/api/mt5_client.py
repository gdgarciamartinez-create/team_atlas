# src/atlas/api/mt5_client.py
from __future__ import annotations

import os
import time
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, List

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception:  # pragma: no cover
    mt5 = None  # type: ignore


# Regla UX del proyecto: last_error [1,"Success"] NO es error real
def _safe_last_error() -> Optional[Tuple[int, str]]:
    if mt5 is None:
        return None
    try:
        err = mt5.last_error()
        if not err:
            return None
        code, msg = err[0], err[1]
        if code == 1 and str(msg).lower() == "success":
            return None
        return (int(code), str(msg))
    except Exception:
        return None


TF_MAP = {
    "M1": "TIMEFRAME_M1",
    "M2": "TIMEFRAME_M2",
    "M3": "TIMEFRAME_M3",
    "M4": "TIMEFRAME_M4",
    "M5": "TIMEFRAME_M5",
    "M6": "TIMEFRAME_M6",
    "M10": "TIMEFRAME_M10",
    "M12": "TIMEFRAME_M12",
    "M15": "TIMEFRAME_M15",
    "M20": "TIMEFRAME_M20",
    "M30": "TIMEFRAME_M30",
    "H1": "TIMEFRAME_H1",
    "H2": "TIMEFRAME_H2",
    "H3": "TIMEFRAME_H3",
    "H4": "TIMEFRAME_H4",
    "H6": "TIMEFRAME_H6",
    "H8": "TIMEFRAME_H8",
    "H12": "TIMEFRAME_H12",
    "D1": "TIMEFRAME_D1",
    "W1": "TIMEFRAME_W1",
    "MN1": "TIMEFRAME_MN1",
}


def normalize_symbol(symbol: str) -> str:
    s = (symbol or "").strip()
    if not s:
        return "XAUUSDz"

    # Canonicalización rápida
    s_upper = s.upper()

    # Alias típicos para tu broker
    if s_upper in ("NAS100", "US100", "USTEC", "NASDAQ"):
        return "USTEC_x100z"

    # Si ya viene con z al final o contiene _x100z
    if s.endswith("z") or s.endswith("Z") or s_upper.endswith("_X100Z"):
        return s

    # Si viene sin sufijo
    suffix = os.getenv("ATLAS_SYMBOL_SUFFIX", "z")
    if suffix and not suffix.startswith("."):
        return f"{s}{suffix}"
    return f"{s}z"


def _tf_to_mt5(tf: str) -> int:
    if mt5 is None:
        raise RuntimeError("MetaTrader5 package no disponible en este entorno.")
    key = (tf or "").strip().upper()
    if key not in TF_MAP:
        raise ValueError(f"TF inválido: {tf}. Usa: {', '.join(sorted(TF_MAP.keys()))}")
    attr = TF_MAP[key]
    if not hasattr(mt5, attr):
        raise ValueError(f"TF {tf} no soportado por tu MetaTrader5 build (faltante {attr}).")
    return getattr(mt5, attr)


@dataclass
class MT5ConnInfo:
    connected: bool
    account: Optional[int] = None
    server: Optional[str] = None
    terminal: Optional[str] = None
    last_error: Optional[Tuple[int, str]] = None
    note: str = ""


class MT5Client:
    """
    Cliente robusto:
    - initialize + login (si hay creds)
    - reconexión suave al fallar
    - NO ejecuta operaciones (solo lectura)
    """

    _instance: Optional["MT5Client"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_init_ts = 0.0
        self._connected = False
        self._last_note = ""

        # Credenciales (opcionales)
        self.login = os.getenv("MT5_LOGIN", "").strip()
        self.password = os.getenv("MT5_PASSWORD", "").strip()
        self.server = os.getenv("MT5_SERVER", "").strip()

        # Backoff
        self.retries = int(os.getenv("MT5_RETRIES", "3"))
        self.retry_sleep_ms = int(os.getenv("MT5_RETRY_SLEEP_MS", "600"))

    @classmethod
    def instance(cls) -> "MT5Client":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = MT5Client()
            return cls._instance

    def configure(self, login: Optional[str] = None, password: Optional[str] = None, server: Optional[str] = None) -> None:
        if login is not None:
            self.login = str(login).strip()
        if password is not None:
            self.password = str(password).strip()
        if server is not None:
            self.server = str(server).strip()

    def _initialize_once(self) -> bool:
        if mt5 is None:
            self._connected = False
            self._last_note = "MetaTrader5 package no instalado."
            return False

        ok = mt5.initialize()
        if not ok:
            self._connected = False
            self._last_note = "mt5.initialize() falló"
            return False

        # Si hay creds, intentamos login
        if self.login and self.password and self.server:
            try:
                login_int = int(self.login)
            except Exception:
                login_int = 0

            if login_int > 0:
                ok_login = mt5.login(login=login_int, password=self.password, server=self.server)
                if not ok_login:
                    self._connected = False
                    self._last_note = "mt5.login() falló"
                    return False

        self._connected = True
        self._last_note = "connected"
        self._last_init_ts = time.time()
        return True

    def ensure_connected(self) -> MT5ConnInfo:
        with self._lock:
            # Si está conectado, chequeo mínimo
            if self._connected and mt5 is not None:
                ai = mt5.account_info()
                ti = mt5.terminal_info()
                if ai is not None and ti is not None:
                    return MT5ConnInfo(
                        connected=True,
                        account=getattr(ai, "login", None),
                        server=getattr(ai, "server", None),
                        terminal=getattr(ti, "name", None),
                        last_error=_safe_last_error(),
                        note=self._last_note,
                    )

            # Reintentar conexión
            last_err = None
            for i in range(max(1, self.retries)):
                ok = self._initialize_once()
                last_err = _safe_last_error()
                if ok:
                    ai = mt5.account_info() if mt5 is not None else None
                    ti = mt5.terminal_info() if mt5 is not None else None
                    return MT5ConnInfo(
                        connected=True,
                        account=getattr(ai, "login", None) if ai else None,
                        server=getattr(ai, "server", None) if ai else None,
                        terminal=getattr(ti, "name", None) if ti else None,
                        last_error=last_err,
                        note=f"reconnected (try {i+1})" if i > 0 else "connected",
                    )
                time.sleep(self.retry_sleep_ms / 1000.0)

            return MT5ConnInfo(
                connected=False,
                account=None,
                server=None,
                terminal=None,
                last_error=last_err,
                note=self._last_note or "not connected",
            )

    def symbols(self, q: str = "") -> Dict[str, Any]:
        info = self.ensure_connected()
        if not info.connected or mt5 is None:
            return {"ok": True, "status": "DISCONNECTED", "conn": info.__dict__, "symbols": []}

        q = (q or "").strip()
        syms = mt5.symbols_get(q) if q else mt5.symbols_get()
        out = []
        if syms:
            for s in syms:
                out.append({
                    "name": getattr(s, "name", ""),
                    "path": getattr(s, "path", ""),
                    "visible": bool(getattr(s, "visible", False)),
                    "trade_mode": int(getattr(s, "trade_mode", 0)),
                })
        return {"ok": True, "status": "OK", "conn": info.__dict__, "symbols": out}

    def tick(self, symbol: str) -> Dict[str, Any]:
        sym = normalize_symbol(symbol)
        info = self.ensure_connected()
        if not info.connected or mt5 is None:
            return {"ok": True, "status": "DISCONNECTED", "conn": info.__dict__, "symbol": sym, "tick": None}

        # asegurar símbolo seleccionado
        mt5.symbol_select(sym, True)

        t = mt5.symbol_info_tick(sym)
        if t is None:
            # mercado cerrado / sin datos / símbolo inválido
            return {"ok": True, "status": "NO_DATA", "conn": info.__dict__, "symbol": sym, "tick": None, "note": "No tick"}

        return {
            "ok": True,
            "status": "OK",
            "conn": info.__dict__,
            "symbol": sym,
            "tick": {
                "time": int(getattr(t, "time", 0)),
                "bid": float(getattr(t, "bid", 0.0)),
                "ask": float(getattr(t, "ask", 0.0)),
                "last": float(getattr(t, "last", 0.0)),
                "volume": float(getattr(t, "volume", 0.0)),
            },
        }

    def candles(self, symbol: str, tf: str, count: int = 200) -> Dict[str, Any]:
        sym = normalize_symbol(symbol)
        tf_mt5 = _tf_to_mt5(tf)
        info = self.ensure_connected()
        if not info.connected or mt5 is None:
            return {"ok": True, "status": "DISCONNECTED", "conn": info.__dict__, "symbol": sym, "tf": tf, "candles": []}

        count = int(max(1, min(int(count), 5000)))
        mt5.symbol_select(sym, True)

        rates = mt5.copy_rates_from_pos(sym, tf_mt5, 0, count)
        if rates is None or len(rates) == 0:
            return {
                "ok": True,
                "status": "NO_DATA",
                "conn": info.__dict__,
                "symbol": sym,
                "tf": tf,
                "candles": [],
                "note": "No rates (market closed / no history / symbol invalid)",
            }

        candles: List[Dict[str, Any]] = []
        for r in rates:
            # r["time"] viene en seconds
            candles.append({
                "t": int(r["time"]) * 1000,
                "o": float(r["open"]),
                "h": float(r["high"]),
                "l": float(r["low"]),
                "c": float(r["close"]),
                "v": float(r["tick_volume"]) if "tick_volume" in r.dtype.names else float(r.get("tick_volume", 0.0)),
            })

        return {
            "ok": True,
            "status": "OK",
            "conn": info.__dict__,
            "symbol": sym,
            "tf": tf,
            "count": count,
            "candles": candles,
        }