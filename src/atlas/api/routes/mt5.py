from fastapi import APIRouter

router = APIRouter()


@router.get("/mt5/symbols")
def mt5_symbols():
    try:
        from atlas.providers.mt5_provider import get_symbols
        symbols = get_symbols()
        return {"ok": True, "symbols": symbols, "count": len(symbols)}
    except Exception as e:
        return {"ok": False, "symbols": [], "count": 0, "error": str(e)}