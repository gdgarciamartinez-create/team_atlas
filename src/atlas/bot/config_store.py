import json
import os

DEFAULT_CONFIG = {
  "mode": "MT5",                 # MT5 | LAB
  "symbol": "AUTO",              # AUTO o símbolo real (EURUSDz, XAUUSDz, etc)
  "tf_exec": "M1",               # M1/M5/M15/H1...
  "force_presesion_mode": "AUTO",# AUTO | ON | OFF
  "params": {
    "range_min_atr_mult": 1.2,
    "gap_threshold": 0.0015,
    "buffer_sweep_pct": 0.0005,
    "buffer_sweep_atr_mult": 0.2,
    "max_trades_per_window": 1
  },
  "universe_rules": {
    "include_prefixes": ["EUR", "USD"],
    "exclude_contains": ["BTC"]
  },
  "gap_menu": {
    "enabled": True,
    "xau_mode": "GAP",           # GAP | OFF
    "winter": {"gap_window": "19:55-20:30"},
    "summer": {"gap_window": "20:55-21:30"}
  }
}

CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".atlas_config.json")
CFG_PATH = os.path.abspath(CFG_PATH)

def load_config():
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(cfg):
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False