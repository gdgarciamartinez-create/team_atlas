{
  "schema": "atlas.knowledge.v1",
  "symbol": "USDJPYz",
  "asset_class": "forex",
  "source": "mt5_csv",
  "notes": [
    "Símbolo demo Exness con sufijo z.",
    "Usar para ATLAS_IA: scalping (M1/M5) y forex (H1/H4/H12/H2 según disponibilidad).",
    "Contadores: todo diario (no por sesión)."
  ],
  "timeframes": {
    "M5": {
      "file": "USDJPYz_M5.csv",
      "path_hint": "/mnt/data/USDJPYz_M5.csv"
    },
    "M30": {
      "file": "USDJPYz_M30.csv",
      "path_hint": "/mnt/data/USDJPYz_M30.csv"
    },
    "H1": {
      "file": "USDJPYz_H1.csv",
      "path_hint": "/mnt/data/USDJPYz_H1.csv"
    },
    "H2": {
      "file": "USDJPYz_H2.csv",
      "path_hint": "/mnt/data/USDJPYz_H2.csv"
    },
    "H4": {
      "file": "USDJPYz_H4.csv",
      "path_hint": "/mnt/data/USDJPYz_H4.csv"
    },
    "H12": {
      "file": "USDJPYz_H12.csv",
      "path_hint": "/mnt/data/USDJPYz_H12.csv"
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