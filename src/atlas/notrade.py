from datetime import datetime
from atlas.bot.state import BOT_STATE

def _now_iso():
    return datetime.now().isoformat(timespec="seconds")

def record_notrade(symbol: str, mode: str, reasons: list[str], snapshot_hint: dict | None = None):
    # Dataset liviano en memoria (se puede persistir luego)
    ds = BOT_STATE.setdefault("notrade_dataset", [])
    if not isinstance(ds, list):
        ds = []
        BOT_STATE["notrade_dataset"] = ds

    item = {
        "ts": _now_iso(),
        "symbol": symbol,
        "mode": mode,
        "reasons": reasons,
        "hint": snapshot_hint or {},
    }
    ds.append(item)

    # mantener máximo
    if len(ds) > 500:
        del ds[0:len(ds)-500]