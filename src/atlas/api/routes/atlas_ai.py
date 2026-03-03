from fastapi import APIRouter, Query
from datetime import datetime

from atlas.core.mt5_service import get_candles, mt5_status

router = APIRouter()


@router.get("/atlas/ai", tags=["atlas-ai"])
def atlas_ai(
    world: str = Query("GAP"),
    symbol: str = Query("XAUUSDz"),
    tf: str = Query("M5"),
    count: int = Query(120),
):
    """
    Endpoint AI (modo laboratorio):
    - Trae velas reales
    - Devuelve estado base (placeholder)
    """
    st = mt5_status()
    candles_res = get_candles(symbol, tf, count)

    if not candles_res.get("ok"):
        return {
            "ok": False,
            "world": world,
            "symbol": symbol,
            "tf": tf,
            "timestamp": datetime.utcnow().isoformat(),
            "state": "NO_DATA",
            "logic": "Sin velas o MT5 no respondió.",
            "mt5": st,
            "candles": [],
            "last_error": candles_res.get("last_error"),
        }

    # Placeholder limpio (después metemos lógica real)
    return {
        "ok": True,
        "world": world,
        "symbol": candles_res.get("symbol_resolved", symbol),
        "tf": tf,
        "timestamp": datetime.utcnow().isoformat(),
        "state": "WAITING_TRIGGER",
        "logic": "Esperando validación de gatillo (laboratorio).",
        "mt5": st,
        "candles": candles_res.get("candles", []),
        "last_error": None,
    }