from typing import List, Dict, Any
from atlas.bot.debt import detect_debts

def analyze_context(symbol: str, candles: List[Dict]) -> Dict[str, Any]:
    """
    LEVEL 2: MARKET READING (NERVOUS SYSTEM)
    Identifies bias, phase, and state.
    """
    if not candles or len(candles) < 20:
        return {
            "tipo": "invalid",
            "estado": "silencio",
            "validez": "nula",
            "razon": "insufficient_data",
            "deudas": [],
            "impulse": None
        }

    # Basic Context Logic (SMA 20 as baseline for structure)
    # In a full production system, this would use Market Structure (HH/HL)
    current = candles[-1]
    close = current["close"]
    
    # Calculate SMA 20
    closes = [c["close"] for c in candles[-20:]]
    sma20 = sum(closes) / len(closes)
    
    # Bias determination
    bias = "bullish" if close > sma20 else "bearish"
    
    # Phase determination (Expansion vs Correction)
    # Logic to define "Valid Context" per brief:
    # 1. Impulso claro.
    # 2. Corrección (no expansión/agotamiento).
    
    window = candles[-20:]
    if bias == "bullish":
        impulse_low = min(c["low"] for c in window)
        impulse_high = max(c["high"] for c in window)
        impulse = {"direction": "bullish", "start": impulse_low, "end": impulse_high}
        
        # Correction if price is retracing from high
        rng = impulse_high - impulse_low
        retracement = (impulse_high - close) / rng if rng > 0 else 0
        phase = "correction" if retracement > 0.2 else "expansion"
        
    else:
        impulse_high = max(c["high"] for c in window)
        impulse_low = min(c["low"] for c in window)
        impulse = {"direction": "bearish", "start": impulse_high, "end": impulse_low}
        
        rng = impulse_high - impulse_low
        retracement = (close - impulse_low) / rng if rng > 0 else 0
        phase = "correction" if retracement > 0.2 else "expansion"
    
    # State determination
    # If volume is extremely low or price is flat, state = waiting
    vol_avg = sum(c.get("volume", 0) for c in candles[-5:]) / 5
    state = "active"
    reason = f"{bias}_{phase}"

    if vol_avg < 10 and current.get("volume", 0) < 10: 
        state = "waiting"
        reason = "low_activity"

    # Debt detection (Level 2: Attached to context)
    debts = detect_debts(candles, impulse)

    # Level 2 Output Structure
    tipo = f"{bias}_{phase}" if bias != "neutral" else "neutral"
    # Valid only if correction, not expansion/exhaustion.
    validez = "alta" if phase == "correction" and state == "active" else "nula"
    
    if validez == "nula":
        state = "silencio"
        reason = "contexto_no_valido_para_gatillo"

    return {
        "tipo": tipo,
        "estado": state,
        "validez": validez,
        "razon": reason,
        "deudas": debts,
        "impulse": impulse
    }
