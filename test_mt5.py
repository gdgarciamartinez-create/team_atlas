import MetaTrader5 as mt5

symbol = "USTECz"

if not mt5.initialize():
    print("init failed", mt5.last_error())
else:
    info = mt5.symbol_info(symbol)
    acc = mt5.account_info()

    if info is None:
        print("symbol_info None")
    else:
        print("symbol:", symbol)
        print("trade_tick_value:", info.trade_tick_value)
        print("trade_tick_size:", info.trade_tick_size)
        print("volume_min:", info.volume_min)
        print("volume_max:", info.volume_max)
        print("volume_step:", info.volume_step)
        print("point:", info.point)

    if acc is not None:
        print("balance:", acc.balance)
        print("equity:", acc.equity)

    mt5.shutdown()