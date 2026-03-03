import os

def mt5_symbol(atlas_symbol: str) -> str:
    # atlas_symbol is canonical: "XAUUSD", "NAS100", "EURUSD"
    key = f"ATLAS_MT5_{atlas_symbol}"
    return os.getenv(key, atlas_symbol)