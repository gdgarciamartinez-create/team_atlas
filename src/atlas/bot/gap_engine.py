from atlas.bot.time_engine import current_session
from atlas.bot.state import BOT_STATE

def update_gap_state():
    """
    Actualiza BOT_STATE['gap_state'] basado en horario y símbolo.
    Solo activo para XAUUSD en ventana GOLD_GAP.
    """
    symbol = BOT_STATE.get("symbol", "XAUUSD")
    session = current_session() # LONDON, NY, GOLD_GAP, IDLE
    
    # Actualizar sesión global
    BOT_STATE["session"] = session

    if symbol != "XAUUSD":
        BOT_STATE["gap_state"] = {"active": False, "valid": False, "reason": "Not XAUUSD"}
        return

    if session != "GOLD_GAP":
        BOT_STATE["gap_state"] = {"active": False, "valid": False, "reason": "Out of window"}
        return

    # Lógica GAP (Simplificada para laboratorio)
    candles = BOT_STATE.get("candles", [])
    if len(candles) < 2:
        BOT_STATE["gap_state"] = {"active": True, "valid": False, "reason": "No data"}
        return

    # Detectar gap entre close anterior y open actual (simulado o real)
    # En LAB, el generador fake puede simular gaps si el perfil es 'gap_on'
    last = candles[-1]
    prev = candles[-2]
    
    gap_size = last["open"] - prev["close"]
    threshold = 1.0 # Ejemplo: 1 USD
    
    valid = abs(gap_size) >= threshold
    direction = "UP" if gap_size > 0 else "DOWN"

    BOT_STATE["gap_state"] = {
        "active": True,
        "valid": valid,
        "details": {
            "gap_size": round(gap_size, 2),
            "direction": direction,
            "threshold": threshold
        }
    }