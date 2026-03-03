from typing import List, Dict, Any
from atlas.config import settings
from atlas.bot.scoring import calculate_score

def analyze_windows(symbol: str, session: str, candles: List[Dict]) -> Dict[str, Any]:
    """
    Retorna estructura de decisión:
    { "decision": "SIGNAL"|"NO_TRADE", "signal": {...}|None, "reasons": [...] }
    """
    if not candles or len(candles) < 20:
        return {"decision": "NO_TRADE", "signal": None, "reasons": ["not_enough_candles"]}

    # 1. Data Prep (Lookback dinámico para definir rango reciente)
    lookback = 20
    relevant_candles = candles[-lookback:]
    
    # Excluir vela actual para definir el rango previo
    prev_candles = relevant_candles[:-1]
    if not prev_candles:
        return {"decision": "NO_TRADE", "signal": None, "reasons": ["data_error"]}

    highs = [c["high"] for c in prev_candles]
    lows = [c["low"] for c in prev_candles]
    
    window_high = max(highs)
    window_low = min(lows)
    rng = window_high - window_low
    
    # ATR aprox (simple high-low avg)
    atr = sum([c["high"] - c["low"] for c in prev_candles]) / len(prev_candles)
    range_min = atr * 1.2
    
    # A) Filtro Rango
    if rng < range_min:
        return {"decision": "NO_TRADE", "signal": None, "reasons": ["range_too_small"]}

    # B) Detectar Barrida (Sweep) en la vela actual (última)
    current = candles[-1]
    price = current["close"]
    buffer_sweep = max(0.0005 * price, atr * 0.2)
    
    sweep_type = None
    
    # Barrida Arriba (Venta): High supera max previo, Close cierra abajo
    if current["high"] > window_high + buffer_sweep and current["close"] <= window_high:
        sweep_type = "SELL"
        
    # Barrida Abajo (Compra): Low rompe min previo, Close cierra arriba
    elif current["low"] < window_low - buffer_sweep and current["close"] >= window_low:
        sweep_type = "BUY"
        
    if not sweep_type:
        return {"decision": "NO_TRADE", "signal": None, "reasons": ["no_sweep_or_no_close_back"]}

    # C) Confirmación + Fib
    # Validar si el precio tocó el nivel 78.6% del rango antes de cerrar
    # Para Venta: (High - Low_Rango) / Rango >= 0.786? (aprox)
    # Simplificación: Si hubo sweep del extremo, implícitamente cruzó todo el rango o gran parte.
    # Pero la regla pide "Fibonacci obligatorio 0.786".
    # Verificamos si el retroceso desde el sweep es válido.
    
    fib_ok = False
    fib_level = settings.fib_key
    
    if sweep_type == "SELL":
        # Barrida arriba. ¿El precio llegó al 78.6% del rango medido desde abajo?
        # Rango total = window_high - window_low.
        # Nivel 786 = window_low + (rng * 0.786)
        if current["high"] >= (window_low + (rng * fib_level)):
            fib_ok = True
    else:
        # Barrida abajo. ¿El precio bajó al 78.6% del rango medido desde arriba?
        # Nivel 786 bajista = window_high - (rng * 0.786)
        if current["low"] <= (window_high - (rng * fib_level)):
            fib_ok = True
            
    if not fib_ok:
        return {"decision": "NO_TRADE", "signal": None, "reasons": ["no_fib_786_reaction"]}

    # LEVEL 3: TRIGGERS ONLY (No SL/TP/Entry)
    trigger = {
        "type": "WINDOW_SWEEP",
        "confidence": "high" if fib_ok else "medium",
        "message": f"Window Sweep {sweep_type} confirmed",
        "details": {
            "range_size": rng,
            "sweep_price": current["high"] if sweep_type == "SELL" else current["low"]
        },
        "ts": current.get("time")
    }
    return {"decision": "SIGNAL", "signal": trigger, "reasons": ["Sweep detected", "Range OK", "Fib 0.786 reaction"]}