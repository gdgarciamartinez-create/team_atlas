"""
Estado único del bot.
Todavía NO conectado a MT5.
El snapshot leerá de acá en el futuro.
"""

class BotState:
    def __init__(self):
        self.connected = False
        self.last_tick = None
        self.symbol_map = {
            "XAUUSD": "XAUUSDz",
            "NAS100": "USTEC_x100z",
            "EURUSD": "EURUSDz",
            "USDJPY": "USDJPYz",
        }
        self.prices = {}
        self.exec_state = {
            "armed": False,
            "last_action": None,
            "last_exec": None
        }

BOT_STATE = BotState()