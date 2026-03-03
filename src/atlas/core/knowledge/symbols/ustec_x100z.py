# src/atlas/core/knowledge/symbols/ustec_x100z.py
"""
Knowledge PRO - USTEC_x100z (NASDAQ)
Basado en tu módulo NASDAQ que ya quedó doctrinal.
"""

SYMBOL = "USTEC_x100z"

PROFILE = {
    "meta": {
        "symbol": SYMBOL,
        "asset_class": "INDEX",
        "notes": [
            "NASDAQ tiende a expansión vertical + pausa + último empujón.",
            "No perseguir expansión: esperar corrección o señal clara.",
            "TP1 temprano y BE rápido (regla ya definida).",
        ],
    },
    "FOREX": {
        "tf_bias": "H1/H4",
        "tf_exec": "M5",
        "volatility": "HIGH",
        "buffer_hint": 0.0020,  # 0.2% guía
        "range_min_hint": 1.4,
        "risk_style": "conservador",
        "tp1_points_hint": 35,  # guía, no es orden (motor decide)
    },
    "SCALPING": {
        "tf_bias": "M15/H1",
        "tf_exec": "M1/M5",
        "volatility": "VERY_HIGH",
        "buffer_hint": 0.0025,
        "range_min_hint": 1.2,
        "risk_style": "tactico",
        "tp1_points_hint": 30,
    },
}