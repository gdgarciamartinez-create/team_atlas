from __future__ import annotations


def calc_lot_1pct(
    balance: float,
    stop_pips: float,
    pip_value_per_lot: float = 10.0,
    min_lot: float = 0.01,
    lot_step: float = 0.01,
) -> float:
    """
    Lotaje para riesgo 1% por trade.

    balance: saldo cuenta
    stop_pips: distancia SL en pips
    pip_value_per_lot: valor de 1 pip por 1.00 lote (default 10 para muchos FX)
    """
    if balance <= 0 or stop_pips <= 0 or pip_value_per_lot <= 0:
        return 0.0

    risk_amount = balance * 0.01
    raw_lot = risk_amount / (stop_pips * pip_value_per_lot)

    # cuantizar a lot_step
    steps = round(raw_lot / lot_step)
    lot = steps * lot_step

    if lot < min_lot:
        lot = min_lot

    return round(lot, 2)
