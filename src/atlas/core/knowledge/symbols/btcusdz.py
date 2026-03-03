{
  "schema": "atlas.knowledge.v1",
  "symbol": "BTCUSDz",
  "asset_class": "crypto",
  "source": "mt5_csv",
  "notes": [
    "Símbolo demo Exness con sufijo z.",
    "BTC se opera en dos islas: FOREX (swing/HTF) y SCALPING (M1/M5).",
    "Contadores: todo diario (no por sesión).",
    "Si el broker no entrega tick_value fiable, el sizing debe apoyarse en mt5 contract specs o tabla interna."
  ],
  "timeframes": {
    "M1": {
      "file": "BTCUSDz_M1_202512061503_202602132308.csv",
      "path_hint": "/mnt/data/BTCUSDz_M1_202512061503_202602132308.csv"
    },
    "M5": {
      "file": "BTCUSDz_M5_202503031925_202602132305.csv",
      "path_hint": "/mnt/data/BTCUSDz_M5_202503031925_202602132305.csv"
    },
    "M15": {
      "file": "BTCUSDz_M15_202304090630_202602132300.csv",
      "path_hint": "/mnt/data/BTCUSDz_M15_202304090630_202602132300.csv"
    },
    "M30": {
      "file": "BTCUSDz_M30_202101010000_202602132300.csv",
      "path_hint": "/mnt/data/BTCUSDz_M30_202101010000_202602132300.csv"
    },
    "H1": {
      "file": "BTCUSDz_H1_202101010000_202602132300.csv",
      "path_hint": "/mnt/data/BTCUSDz_H1_202101010000_202602132300.csv"
    },
    "H4": {
      "file": "BTCUSDz_H4_202101010000_202602132000.csv",
      "path_hint": "/mnt/data/BTCUSDz_H4_202101010000_202602132000.csv"
    },
    "H8": {
      "file": "BTCUSDz_H8_202101010000_202602131600.csv",
      "path_hint": "/mnt/data/BTCUSDz_H8_202101010000_202602131600.csv"
    }
  },
  "rules_profile": {
    "worlds_enabled": ["FOREX", "SCALPING_M1", "SCALPING_M5"],
    "max_signals_daily": {
      "FOREX": 1,
      "SCALPING_M1": 1,
      "SCALPING_M5": 1
    },
    "cooldown_seconds": 0,
    "counters_reset": "daily"
  }
}