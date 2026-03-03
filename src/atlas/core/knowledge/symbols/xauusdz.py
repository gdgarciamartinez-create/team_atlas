{
  "schema": "atlas.knowledge.v1",
  "symbol": "XAUUSDz",
  "asset_class": "metal",
  "source": "mt5_csv",
  "notes": [
    "Símbolo demo Exness con sufijo z.",
    "Oro vive en 3 mundos: GAP (horario), PRESESIÓN (horario) y ATLAS_IA (24/7 para lectura).",
    "SCALPING usa M1/M5 y FOREX usa H1/M30/M15 según disponibilidad.",
    "Contadores: todo diario (no por sesión)."
  ],
  "timeframes": {
    "M1": {
      "file": "XAUUSDz_M1_202511061212_202602192338.csv",
      "path_hint": "/mnt/data/XAUUSDz_M1_202511061212_202602192338.csv"
    },
    "M2": {
      "file": "XAUUSDz_M2_202507290020_202602192338.csv",
      "path_hint": "/mnt/data/XAUUSDz_M2_202507290020_202602192338.csv"
    },
    "M3": {
      "file": "XAUUSDz_M3_202504160733_202602192336.csv",
      "path_hint": "/mnt/data/XAUUSDz_M3_202504160733_202602192336.csv"
    },
    "M4": {
      "file": "XAUUSDz_M4_202501031356_202602192336.csv",
      "path_hint": "/mnt/data/XAUUSDz_M4_202501031356_202602192336.csv"
    },
    "M5": {
      "file": "XAUUSDz_M5_202409200945_202602192335.csv",
      "path_hint": "/mnt/data/XAUUSDz_M5_202409200945_202602192335.csv"
    },
    "M6": {
      "file": "XAUUSDz_M6_202406111836_202602192336.csv",
      "path_hint": "/mnt/data/XAUUSDz_M6_202406111836_202602192336.csv"
    },
    "M10": {
      "file": "XAUUSDz_M10_202304261630_202602192330.csv",
      "path_hint": "/mnt/data/XAUUSDz_M10_202304261630_202602192330.csv"
    },
    "M15": {
      "file": "XAUUSDz_M15_202111251130_202602192330.csv",
      "path_hint": "/mnt/data/XAUUSDz_M15_202111251130_202602192330.csv"
    },
    "M30": {
      "file": "XAUUSDz_M30_202101032300_202602192330.csv",
      "path_hint": "/mnt/data/XAUUSDz_M30_202101032300_202602192330.csv"
    },
    "H1": {
      "file": "XAUUSDz_H1_202101032300_202602192300.csv",
      "path_hint": "/mnt/data/XAUUSDz_H1_202101032300_202602192300.csv"
    }
  },
  "rules_profile": {
    "worlds_enabled": ["GAP", "PRESESIÓN", "ATLAS_IA", "FOREX", "SCALPING_M1", "SCALPING_M5"],
    "max_signals_daily": {
      "GAP": 1,
      "PRESESIÓN": 4,
      "ATLAS_IA": 1,
      "FOREX": 1,
      "SCALPING_M1": 1,
      "SCALPING_M5": 1
    },
    "cooldown_seconds": 0,
    "counters_reset": "daily"
  }
}