# src/atlas/bot/context.py
from datetime import datetime, time as dtime
from atlas.bot.state import BOT_STATE

# Horario Chile (Santiago)
WINDOWS = {
    "invierno": {
        "LONDRES": (dtime(2, 0), dtime(6, 0)),
        "NY":      (dtime(7, 0), dtime(9, 0)),
        "GAP":     (dtime(19, 55), dtime(20, 30)), # XAUUSD
    },
    "verano": {
        "LONDRES": (dtime(3, 0), dtime(7, 0)),
        "NY":      (dtime(8, 0), dtime(10, 0)),
        "GAP":     (dtime(20, 55), dtime(21, 30)), # XAUUSD
    }
}

# Universe
FOREX_UNIVERSE_HINT = "EUR* y USD* (excluye BTC)"
GAP_SYMBOLS = {"XAUUSD"}
NASDAQ_SYMBOLS = {"NAS100", "USTEC", "US100"}

ALLOWED_TFS = {"M1", "M5", "M15", "H1", "H4", "H8"}

def _now():
    return datetime.now().time()

def _season():
    eng = BOT_STATE.get("engine", {})
    if not isinstance(eng, dict):
        eng = {}
    return eng.get("season_mode", "invierno")

def _in_window(start: dtime, end: dtime, now: dtime):
    return start <= now <= end

def detect_session_and_mode(symbol: str):
    season = _season()
    now = _now()
    w = WINDOWS.get(season, WINDOWS["invierno"])

    # GAP (solo XAUUSD)
    if symbol in GAP_SYMBOLS:
        start, end = w["GAP"]
        if _in_window(start, end, now):
            return ("GAP", "GAP")

    # LONDRES / NY
    start_lon, end_lon = w["LONDRES"]
    start_ny, end_ny = w["NY"]

    if _in_window(start_lon, end_lon, now):
        return ("LONDRES", "PRESESION")

    if _in_window(start_ny, end_ny, now):
        return ("NY", "PRESESION")

    # Fuera de ventana
    return ("OFF", "IDLE")

def build_context():
    symbol = BOT_STATE.get("symbol", "XAUUSD")
    tf = BOT_STATE.get("tf_exec", "M1")

    session, mode = detect_session_and_mode(symbol)

    ctx = {
        "season": _season(),
        "session": session,             # LONDRES/NY/GAP/OFF
        "mode": mode,                   # GAP / PRESESION / IDLE
        "window_open": session in ("LONDRES", "NY", "GAP"),
        "symbol": symbol,
        "tf": tf,
        "tf_ok": tf in ALLOWED_TFS,
        "universe_hint": FOREX_UNIVERSE_HINT,
        "priority": ["GAP", "PRESESION"],
    }

    BOT_STATE["context"] = ctx
    return ctx