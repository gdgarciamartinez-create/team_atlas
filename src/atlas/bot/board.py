from atlas.bot.state import BOT_STATE

def build_board():
    bot = BOT_STATE.get("bot", "idle")

    if bot == "running":
        light = "RUN"
    elif bot == "error":
        light = "ERROR"
    else:
        light = "WAIT"

    note = BOT_STATE.get("last_error") or BOT_STATE.get("last_action") or "OK"

    return [{
        "symbol": BOT_STATE.get("symbol", "XAUUSD"),
        "light": light,
        "bias": "NEUTRAL",
        "note": note,
    }]
