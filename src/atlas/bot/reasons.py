# src/atlas/bot/reasons.py

REASONS = {
    "FALTAN_VELAS": "Faltan velas para analizar (mínimo aún no alcanzado).",
    "MODO_INACTIVO": "Modo inactivo (IDLE).",

    "FUERA_DE_VENTANA": "Fuera de ventana operativa (Londres/NY/GAP).",
    "WINDOW_LIMIT_REACHED": "Límite de trades por ventana alcanzado.",

    "SIMBOLO_INVALIDO": "Símbolo inválido o vacío.",

    "NO_CONTEXT": "Falla contexto (impulso + corrección no claros).",
    "CONFLICT_DIRECTION": "Conflicto direccional detectado.",
    
    "NO_0_786_TOUCH": "Precio no tocó zona 0.786–0.79 (Mandamiento).",
    "FIB_INVALIDO": "Fibonacci inválido o sin rango suficiente.",

    "NO_TRIGGER": "Sin gatillo válido (A/B/C).",
    "CHAOTIC_ARRIVAL": "Llegada caótica/sucia a la zona.",
    "LLEGADA_VIOLENTA": "Llegada violenta (prohibido).",
    "ZONA_MUERTA": "Zona muerta (sin aceptación).",
    "CASI_LINDO": "Rechazado por 'casi lindo' (duda).",
    
    "GAP_NOT_VALID": "Gap no válido o fuera de horario (XAUUSD).",
    "RISK_NOT_FEASIBLE": "Riesgo/Beneficio no viable.",

    # Legacy/Internal
    "ESPERANDO_CORRECCION": "Esperando corrección válida.",
    "ESPERANDO_GATILLO": "Contexto armado, esperando gatillo.",
    "GATILLO_VALIDO": "Gatillo válido detectado.",

    "IDEA_DIARIA_YA_EMITIDA": "Ya se emitió la idea diaria para este símbolo (silencio).",
    "PARCIAL_YA_EMITIDO": "Parcial ya emitido para esta idea (silencio).",
}

def reason_text(code: str) -> str:
    return REASONS.get(code, code)