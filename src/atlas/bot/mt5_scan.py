import os
import re

CSV_RE = re.compile(r"^ATLAS_(?P<symbol>.+)_(?P<tf>[A-Za-z0-9]+)\.csv$")

def scan_mt5_files(base_path: str):
    symbols = {}
    if not base_path or not os.path.isdir(base_path):
        return {"symbols": [], "tfs": [], "matrix": {}}

    for f in os.listdir(base_path):
        full_path = os.path.join(base_path, f)
        
        # 1. Detectar carpetas (ej: data/mt5/EURUSDz/)
        if os.path.isdir(full_path):
            sym = f
            # Escanear TFs dentro (ej: M1.csv)
            for sub in os.listdir(full_path):
                if sub.endswith(".csv"):
                    tf = sub.replace(".csv", "")
                    symbols.setdefault(sym, set()).add(tf)
            continue

        # 2. Detectar archivos planos (ej: ATLAS_EURUSDz_M1.csv)
        m = CSV_RE.match(f)
        if m:
            sym = m.group("symbol")
            tf = m.group("tf")
            symbols.setdefault(sym, set()).add(tf)

    sym_list = sorted(symbols.keys())
    tf_set = set()
    matrix = {}
    for s, tfs in symbols.items():
        matrix[s] = sorted(tfs)
        tf_set |= set(tfs)

    return {"symbols": sym_list, "tfs": sorted(list(tf_set)), "matrix": matrix}