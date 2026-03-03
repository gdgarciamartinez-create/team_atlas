from atlas.api.routes.router import get_candles, mt5_status

def get_market_snapshot(symbol: str, tf: str, count: int):
    st = mt5_status()
    candles_res = get_candles(symbol, tf=tf, count=count)


    return {
        "mt5": st,
        "candles": candles_res.get("candles", []),
        "ok": candles_res.get("ok", False)
    }