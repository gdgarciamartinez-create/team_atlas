def fib_0786_zone(low: float, high: float, direction: str):
    # direction: "BUY" means correction down from high to 0.786 of impulse (low->high)
    # returns (zone_low, zone_high) around 0.786 for tolerance
    direction = direction.upper()
    if high <= low:
        return None
    lvl = low + (high - low) * 0.786
    tol = (high - low) * 0.01  # 1% of impulse size (tunable)
    return (lvl - tol, lvl + tol)

def in_zone(price: float, zone):
    if zone is None:
        return False
    a, b = zone
    return a <= price <= b