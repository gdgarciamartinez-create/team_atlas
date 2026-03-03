from typing import List, Dict, Any
from atlas.config import settings
from atlas.bot.scoring import calculate_score

def analyze_gold_gap(symbol: str, candles: List[Dict]) -> Dict[str, Any]:
    """
    Retorna estructura de decisión:
    { "decision": "SIGNAL"|"NO_TRADE", "signal": {...}|None, "reasons": [...] }
    """
    if symbol != "XAUUSD":
        return {"decision": "NO_TRADE", "signal": None, "reasons": ["not_gold"]}
        
    if not candles or len(candles) < 2:
        return {"decision": "NO_TRADE", "signal": None, "reasons": ["not_enough_candles"]}
        
    # Gap detection: Open actual vs Close prev
    curr = candles[-1]
    prev = candles[-2]
    
    gap = curr["open"] - prev["close"]
    price = curr["close"]
    
    # Gap válido >= 0.15%
    if abs(gap) / price < settings.gap_threshold:
        return {"decision": "NO_TRADE", "signal": None, "reasons": ["gap_too_small"]}
        
    # Dirección natural
    side = "SELL" if gap > 0 else "BUY" # Gap arriba -> buscar bajada (fill)
    
    # Confirmación + Fib
    # Regla: Aceptación (mínimo 2 velas respetando dirección)
    # Latigazo violento sin aceptación = SIN OPERACIÓN
    fib_ok = True 
    
    # Verificamos las últimas 2 velas para aceptación
    if len(candles) < 3:
         return {"decision": "NO_TRADE", "signal": None, "reasons": ["waiting_acceptance"]}

    c1 = candles[-1]
    c2 = candles[-2]

    # Aceptación: ambas velas deben apoyar la dirección
    if side == "SELL":
        confirmation = (c1["close"] < c1["open"]) and (c2["close"] < c2["open"])
    else:
        confirmation = (c1["close"] > c1["open"]) and (c2["close"] > c2["open"])
                   
    if not confirmation:
        return {"decision": "NO_TRADE", "signal": None, "reasons": ["SIN_ACEPTACION", "LATIGAZO_SIN_ACEPTACION"]}

    # LEVEL 3: TRIGGERS ONLY (No SL/TP/Entry)
    trigger = {
        "type": "GAP_PATH",
        "confidence": "high" if fib_ok else "medium",
        "message": f"Gap {side} detected (> {settings.gap_threshold*100}%) with acceptance",
        "details": {
            "gap_size": abs(gap),
            "gap_open": curr["open"],
            "gap_close": prev["close"]
        },
        "ts": curr.get("time")
    }

    return {"decision": "SIGNAL", "signal": trigger, "reasons": ["Gap valid", "Aceptación confirmada"]}