from datetime import datetime
from zoneinfo import ZoneInfo
from atlas.config import settings

SCL = ZoneInfo("America/Santiago")

def now_scl() -> datetime:
    return datetime.now(SCL)

def current_session(dt: datetime = None) -> str:
    if dt is None:
        dt = now_scl()
    
    h = dt.hour
    m = dt.minute
    mode = settings.atlas_mode.lower()

    # Definición de ventanas según modo (Santiago)
    if mode == "invierno":
        # Presesion: 06:00 -> 11:00
        if 6 <= h < 11: return "PRE"
        # Gap Oro: 19:55 -> 20:30
        if (h == 19 and m >= 55) or (h == 20 and m <= 30): return "GOLD_GAP"
        
    elif mode == "verano":
        # Presesion: 06:00 -> 11:00
        if 6 <= h < 11: return "PRE"
        # Gap Oro: 20:55 -> 21:30
        if (h == 20 and m >= 55) or (h == 21 and m <= 30): return "GOLD_GAP"

    return "IDLE"