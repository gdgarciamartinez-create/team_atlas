# src/atlas/api/routes/mt5.py
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from atlas.api.mt5_client import MT5Client, normalize_symbol

router = APIRouter(prefix="/mt5", tags=["mt5"])


class MT5InitIn(BaseModel):
    login: Optional[str] = None
    password: Optional[str] = None
    server: Optional[str] = None


@router.get("/ping")
def mt5_ping():
    """
    2.1 Healthcheck MT5 (solo lectura):
    - Si está conectado devuelve conn.connected=true
    - Si no, devuelve conn.connected=false pero NO rompe la API
    """
    c = MT5Client.instance()
    info = c.ensure_connected()
    return {"ok": True, "conn": info.__dict__}


@router.post("/init")
def mt5_init(payload: MT5InitIn):
    """
    2.1 Init/Login robusto:
    - Configura credenciales (si vienen)
    - Intenta conectar ahora
    """
    c = MT5Client.instance()
    c.configure(login=payload.login, password=payload.password, server=payload.server)
    info = c.ensure_connected()
    return {"ok": True, "conn": info.__dict__}


@router.get("/symbols")
def mt5_symbols(q: str = Query("", description="Filtro substring, ej: 'XAU' o 'EUR'")):
    """
    2.2 Lista símbolos del terminal (solo lectura)
    """
    c = MT5Client.instance()
    return c.symbols(q=q)


@router.get("/tick")
def mt5_tick(symbol: str = Query("XAUUSDz", description="MT5 symbol, ej: XAUUSDz o EURUSDz; acepta XAUUSD y lo normaliza")):
    """
    2.2 + 2.4 Tick robusto (NO_DATA si mercado cerrado/sin tick)
    """
    c = MT5Client.instance()
    return c.tick(symbol=symbol)


@router.get("/candles")
def mt5_candles(
    symbol: str = Query("XAUUSDz", description="MT5 symbol; acepta sin sufijo y lo normaliza"),
    tf: str = Query("M5", description="TF: M1/M3/M5/M15/M30/H1/H4/D1..."),
    count: int = Query(200, ge=1, le=5000, description="Cantidad de velas"),
):
    """
    2.3 + 2.4 Velas robustas:
    - OK con candles
    - NO_DATA si no hay histórico / mercado cerrado / símbolo inválido
    """
    c = MT5Client.instance()
    return c.candles(symbol=symbol, tf=tf, count=count)