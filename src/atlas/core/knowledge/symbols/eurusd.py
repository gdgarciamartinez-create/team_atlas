# src/atlas/core/knowledge/symbols/eurusdz.py
"""
Knowledge PRO - EURUSDz
"""

SYMBOL = "EURUSDz"

PROFILE = {
    "meta": {
        "symbol": SYMBOL,
        "asset_class": "FX",
        "notes": [
            "EURUSD: suele ser de los más 'limpios' para estructura.",
            "Buen candidato para setups repetibles en H4→H1→M15.",
        ],
    },
    "FOREX": {
        "tf_bias": "H1/H4",
        "tf_exec": "M5",
        "volatility": "MED",
        "buffer_hint": 0.0010,
        "range_min_hint": 1.2,
        "risk_style": "conservador",
    },
    "SCALPING": {
        "tf_bias": "M15/H1",
        "tf_exec": "M1/M5",
        "volatility": "MED",
        "buffer_hint": 0.0012,
        "range_min_hint": 1.05,
        "risk_style": "tactico",
    },
}