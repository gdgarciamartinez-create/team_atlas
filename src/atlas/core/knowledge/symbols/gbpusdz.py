{
  "schema": "atlas.knowledge.v1",
  "symbol": "GBPUSDz",
  "asset_class": "forex",
  "source": "mt5_csv",
  "notes": [
    "Símbolo demo Exness con sufijo z.",
    "Scalping con dos ventanas (M1 y M5). Forex con H1/H4/H8.",
    "Contadores: todo diario (no por sesión)."
  ],
  "timeframes": {
    "M1": {
      "file": "GBPUSDz_M1.csv",
      "path_hint": "/mnt/data/GBPUSDz_M1.csv"
    },
    "M3": {
      "file": "GBPUSDz_M3.csv",
      "path_hint": "/mnt/data/GBPUSDz_M3.csv"
    },
    "M5": {
      "file": "GBPUSDz_M5.csv",
      "path_hint": "/mnt/data/GBPUSDz_M5.csv"
    },
    "M30": {
      "file": "GBPUSDz_M30.csv",
      "path_hint": "/mnt/data/GBPUSDz_M30.csv"
    },
    "H1": {
      "file": "GBPUSDz_H1.csv",
      "path_hint": "/mnt/data/GBPUSDz_H1.csv"
    },
    "H4": {
      "file": "GBPUSDz_H4.csv",
      "path_hint": "/mnt/data/GBPUSDz_H4.csv"
    },
    "H8": {
      "file": "GBPUSDz_H8_202101031600_202602200000.csv",
      "path_hint": "/mnt/data/GBPUSDz_H8_202101031600_202602200000.csv"
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