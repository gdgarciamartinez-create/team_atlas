import csv
import os

class MT5Feed:
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.candles = []

    def load(self, symbol: str, tf: str, limit: int = 500):
        # Intenta formato carpeta: data/mt5/{SYMBOL}/{TF}.csv
        path = os.path.join(self.base_path, symbol, f"{tf}.csv")
        
        # Fallback: formato plano ATLAS_{SYMBOL}_{TF}.csv
        if not os.path.exists(path):
            path = os.path.join(self.base_path, f"ATLAS_{symbol}_{tf}.csv")
            
        if not os.path.exists(path):
            self.candles = []
            return

        try:
            with open(path, mode="r", encoding="utf-8-sig", errors="replace", newline="") as f:
                rows = list(csv.DictReader(f))
        except Exception:
            self.candles = []
            return

        out = []
        for r in rows[-limit:]:
            try:
                out.append({
                    "time": int(float(r["time"])),  # ms desde MT5 export
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                })
            except Exception:
                continue

        self.candles = out
