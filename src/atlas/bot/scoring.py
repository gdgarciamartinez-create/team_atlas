def calculate_score(setup_type: str, fib_ok: bool, sweep_quality: str = "normal") -> int:
    score = 0
    
    # Base scores
    if setup_type == "GOLD_GAP_FILL":
        score += 35 # Prioridad alta
    elif setup_type == "WINDOW_SWEEP":
        score += 20
        
    # Validation bonuses
    if fib_ok:
        score += 30
        
    # Quality adjustments
    if sweep_quality == "clean":
        score += 15
    elif sweep_quality == "messy":
        score -= 25
        
    # Clamp 0-100
    return max(0, min(100, score))