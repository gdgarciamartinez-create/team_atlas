# src/atlas/bot/triggers.py
from atlas.bot.state import BOT_STATE

def detect_triggers(structure):
    if not structure.get("fibo_ok"):
        return None

    candles = BOT_STATE.get("candles", [])
    if not isinstance(candles, list) or len(candles) < 3:
        return None

    fib = structure.get("fibonacci", {})
    direction = fib.get("direction")
    level = float(fib.get("fib_79"))
    level_786 = float(fib.get("fib_786"))

    c1, c2, c3 = candles[-3], candles[-2], candles[-1]

    # A) CIERRE A FAVOR EN ZONA (Direct Entry)
    # Toca zona y cierra a favor
    if fib.get("in_zone"):
        if direction == "UP" and c3["close"] > c3["open"]:
             return {"kind": "A_CIERRE_FAVOR", "direction": direction, "price": float(c3["close"]), "note": "A) Cierre a favor en zona"}
        if direction == "DOWN" and c3["close"] < c3["open"]:
             return {"kind": "A_CIERRE_FAVOR", "direction": direction, "price": float(c3["close"]), "note": "A) Cierre a favor en zona"}

    # B) BARRIDA + RECUPERACION
    # Barre el nivel extremo y recupera con cierre
    if direction == "UP":
        swept = float(c1["low"]) < level
        recovered = float(c3["close"]) > level_786
    else:
        swept = float(c1["high"]) > level
        recovered = float(c3["close"]) < level_786

    if swept and recovered:
        return {"kind": "B_BARRIDA_RECUPERACION", "direction": direction, "price": float(c3["close"]), "note": "B) Barrida + recuperación"}

    # C) RUPTURA + RETEST
    # Sale de la zona con fuerza y retestea
    if direction == "UP":
        broke = float(c2["close"]) > float(c1["high"])
        retest = float(c3["low"]) <= float(c1["high"])
    else:
        broke = float(c2["close"]) < float(c1["low"])
        retest = float(c3["high"]) >= float(c1["low"])

    if broke and retest:
        return {"kind": "C_RUPTURA_RETEST", "direction": direction, "price": float(c3["close"]), "note": "C) Ruptura + retest"}

    return None
