import math

def calc_lot_1pct(account_size: float, risk_pct: float, entry: float, sl: float, symbol: str = "", pip_value_hint: float = None) -> float:
    if account_size <= 0 or risk_pct <= 0:
        return 0.0
    
    risk_money = account_size * (risk_pct / 100.0)
    dist = abs(entry - sl)
    
    if dist <= 0:
        return 0.0

    # Estimación simple: lot = risk / dist (asumiendo 1 lote = 1 unidad de precio por ahora si no hay hint)
    # En FX real esto requiere tick_value. Para indices/crypto a veces es directo.
    # Aquí usamos una aproximación genérica segura o el hint si existe.
    
    # Si no hay info de tick value, asumimos comportamiento "lineal" simple (ej: crypto spot) 
    # o usamos un fallback conservador.
    # Para cumplir el requerimiento "versión inicial simple (robusta)":
    
    raw_lot = risk_money / dist
    
    # Ajuste muy básico para no devolver locuras:
    # Si es XAUUSD (precio ~2000), dist ~1.0 -> risk 100 -> lot 100? No, en XAU 1 lote = 1 usd/pip? 
    # Depende del contrato. Asumiremos standard lot size 100k units para FX o 100 oz para XAU si fuera necesario.
    # PERO la instrucción dice: "lot = risk_money / sl_distance" tal cual.
    
    lot = raw_lot
    
    # Redondear a 2 decimales
    lot = round(lot, 2)
    
    # Mínimo 0.01
    return max(0.01, lot)