# src/atlas/bot/debt.py

SESSION_LOOKBACK = 120  # velas para definir sesión previa

# CATALOGO CERRADO DE DEUDAS
DEBT_EXTREME = "deuda_extremo"  # High/Low del impulso
DEBT_FAST = "deuda_rapida"      # Desplazamiento rápido (Imbalance)
DEBT_SESSION = "deuda_sesion"   # High/Low sesión previa


def detect_session_extremes(candles):
    if len(candles) < SESSION_LOOKBACK:
        return None

    session = candles[-SESSION_LOOKBACK:]
    high = max(c["high"] for c in session)
    low = min(c["low"] for c in session)

    return {
        "high": high,
        "low": low
    }


def detect_impulse_debt(impulse):
    if impulse is None:
        return []

    debts = []

    # Deuda de extremo: zona de cierre del high/low del impulso
    if impulse.get("end"):
        debts.append({
            "type": DEBT_EXTREME,
            "price": impulse["end"]
        })

    return debts


def detect_imbalance(candles):
    # Deuda rápida: zonas internas del impulso con desplazamiento rápido
    return []


def filter_mitigated_debts(debts, candles, tolerance=0.1):
    """
    Elimina deudas ya mitigadas por el precio.
    tolerance: margen aceptado para considerar mitigación
    """
    active = []

    closes = [c["close"] for c in candles]

    for d in debts:
        price = d["price"]

        touched = any(abs(c - price) <= tolerance for c in closes)
        if not touched:
            active.append(d)

    return active


def detect_debts(candles, impulse=None):
    debts = []

    # Deudas de sesión
    session_extremes = detect_session_extremes(candles)
    if session_extremes:
        debts.append({
            "type": DEBT_SESSION,
            "price": session_extremes["high"]
        })
        debts.append({
            "type": DEBT_SESSION,
            "price": session_extremes["low"]
        })

    # Deudas de impulso (Extremo)
    if impulse:
        debts.extend(detect_impulse_debt(impulse))

    # Deudas rápidas
    imbalances = detect_imbalance(candles)
    if imbalances:
        debts.extend(imbalances)

    # Filtrar mitigadas
    debts = filter_mitigated_debts(debts, candles)

    return debts
