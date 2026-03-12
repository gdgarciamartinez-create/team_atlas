def calculate_score(analysis: dict) -> int:
    """
    Score robusto:
    - No depende de llaves "bonitas" que quizá tu engine aún no entrega.
    - Sube cuando hay plan (zona) y sube fuerte cuando hay gatillo/entrada.
    """
    if not isinstance(analysis, dict):
        return 0

    score = 0

    # Si el engine al menos está vivo
    if analysis.get("status") not in (None, "", "ENGINE_FAIL"):
        score += 10

    # Si hay zona / plan
    if analysis.get("zone") is not None:
        score += 30

    # Si el engine marca gatillo
    if analysis.get("trigger"):
        score += 30

    # Si ya hay números de trade
    has_entry = analysis.get("entry") is not None
    has_sl = analysis.get("sl") is not None
    has_tp = analysis.get("tp") is not None

    if has_entry and has_sl:
        score += 20
    if has_tp:
        score += 10

    # Cap 0..100
    if score < 0:
        score = 0
    if score > 100:
        score = 100

    return score