# src/atlas/core/knowledge/symbols/usoilz.py
"""
Knowledge PRO - USOILz (WTI)
"""

SYMBOL = "USOILz"

PROFILE = {
    "meta": {
        "symbol": SYMBOL,
        "asset_class": "COMMODITY",
        "notes": [
            "USOIL suele hacer movimientos limpios pero con latigazos en noticias.",
            "Respeta bien zonas intradía; cuidado con cambios bruscos de ritmo.",
        ],
    },
    "FOREX": {
        "tf_bias": "H1/H4",
        "tf_exec": "M5",
        "volatility": "MED_HIGH",
        "buffer_hint": 0.0025,  # 0.25% guía
        "range_min_hint": 1.3,
        "risk_style": "medio",
    },
    "SCALPING": {
        "tf_bias": "M15/H1",
        "tf_exec": "M1/M5",
        "volatility": "HIGH",
        "buffer_hint": 0.0035,  # 0.35% guía
        "range_min_hint": 1.1,
        "risk_style": "tactico",
    },
}