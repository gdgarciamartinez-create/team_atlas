"""
PUENTE MT5 (NO ACTIVO TODAVÍA)

Este archivo SOLO define la estructura.
No se importa desde ningún lado aún.
No bloquea backend ni UI.
"""

class MT5Bridge:
    def __init__(self):
        self.ready = False

    def connect(self):
        # aquí irá MetaTrader5.initialize()
        pass

    def fetch_ticks(self, symbol):
        pass

    def shutdown(self):
        pass
