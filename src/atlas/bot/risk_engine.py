def calculate_lot(entry, sl, risk_percent=1, account=10000):

    risk_money = account * (risk_percent/100)

    sl_pips = abs(entry - sl) * 100

    pip_value = 10

    lot = risk_money / (sl_pips * pip_value)

    return round(lot,2)