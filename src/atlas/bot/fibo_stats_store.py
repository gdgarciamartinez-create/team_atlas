# src/atlas/bot/fibo_stats_store.py
from __future__ import annotations

import os
import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Tuple, List

import pandas as pd
import numpy as np


# =====================================================================
# Config
# =====================================================================

DEFAULT_DATA_DIR = os.path.join("data_csv")  # tu repo ya tiene data_csv/...
# formato esperado de MT5:
# <DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>


# =====================================================================
# Core calc (pivotes -> impulsos -> profundidad de retroceso)
# =====================================================================

def _read_mt5_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t")
    dt_str = df["<DATE>"].astype(str) + " " + df["<TIME>"].astype(str)
    df["dt"] = pd.to_datetime(dt_str, format="%Y.%m.%d %H:%M:%S", errors="coerce")
    df = df.dropna(subset=["dt"]).sort_values("dt")

    df["o"] = pd.to_numeric(df["<OPEN>"], errors="coerce")
    df["h"] = pd.to_numeric(df["<HIGH>"], errors="coerce")
    df["l"] = pd.to_numeric(df["<LOW>"], errors="coerce")
    df["c"] = pd.to_numeric(df["<CLOSE>"], errors="coerce")
    df = df.dropna(subset=["o", "h", "l", "c"]).reset_index(drop=True)
    return df[["dt", "o", "h", "l", "c"]]


def _find_pivots(close: np.ndarray, order: int = 6) -> List[Tuple[int, int, float]]:
    """
    Devuelve lista de pivotes: (idx, tipo, valor)
      tipo = +1 (max), -1 (min)
    Resuelve pivotes consecutivos del mismo tipo quedándose con el más extremo.
    """
    n = len(close)
    piv = np.zeros(n, dtype=np.int8)

    for i in range(order, n - order):
        w = close[i - order : i + order + 1]
        if close[i] == np.max(w):
            piv[i] = 1
        if close[i] == np.min(w):
            piv[i] = -1

    idx = np.where(piv != 0)[0]
    pivots: List[Tuple[int, int, float]] = []
    for j in idx:
        typ = int(piv[j])
        val = float(close[j])
        if not pivots:
            pivots.append((int(j), typ, val))
            continue

        pj, ptyp, pval = pivots[-1]
        if typ == ptyp:
            # si es max, quedate con el más alto; si es min, con el más bajo
            if (typ == 1 and val >= pval) or (typ == -1 and val <= pval):
                pivots[-1] = (int(j), typ, val)
        else:
            pivots.append((int(j), typ, val))

    return pivots


def _fib_stats_from_pivots(pivots: List[Tuple[int, int, float]]) -> Optional[Dict[str, Any]]:
    """
    Construye stats de profundidad de retroceso:
      ratio = (profundidad de corrección) / (rango del impulso)
    Para up: min->max->min
    Para down: max->min->max
    """
    ratios: List[float] = []

    for i in range(len(pivots) - 2):
        a = pivots[i]
        b = pivots[i + 1]
        c = pivots[i + 2]

        # Up impulse
        if a[1] == -1 and b[1] == 1 and c[1] == -1:
            lo = a[2]
            hi = b[2]
            corr_lo = c[2]
            rng = hi - lo
            if rng <= 0:
                continue
            depth = hi - corr_lo
            ratios.append(depth / rng)

        # Down impulse
        if a[1] == 1 and b[1] == -1 and c[1] == 1:
            hi = a[2]
            lo = b[2]
            corr_hi = c[2]
            rng = hi - lo
            if rng <= 0:
                continue
            depth = corr_hi - lo
            ratios.append(depth / rng)

    if not ratios:
        return None

    arr = np.array(ratios, dtype=float)

    def p(x: np.ndarray) -> float:
        return float(np.mean(x))

    out = {
        "n": int(arr.size),
        "p_reach_0_618": p(arr >= 0.618),
        "p_reach_0_786": p(arr >= 0.786),
        "p_reach_1_0": p(arr >= 1.0),
        "p_overshoot_gt1": p(arr > 1.0),
        "median": float(np.median(arr)),
        "mean": float(np.mean(arr)),
        "p_ge_1_272": p(arr >= 1.272),
        "p_ge_1_618": p(arr >= 1.618),
        "p_ge_2_0": p(arr >= 2.0),
    }
    return out


def compute_fibo_stats_from_csv(path: str, pivot_order: int = 6) -> Dict[str, Any]:
    df = _read_mt5_csv(path)
    if df.empty:
        return {"ok": False, "error": "empty_csv"}

    piv = _find_pivots(df["c"].values, order=pivot_order)
    st = _fib_stats_from_pivots(piv)
    if not st:
        return {"ok": False, "error": "not_enough_pivots"}

    return {
        "ok": True,
        "from": str(df["dt"].iloc[0]),
        "to": str(df["dt"].iloc[-1]),
        "rows": int(len(df)),
        "pivot_order": int(pivot_order),
        "stats": st,
    }


# =====================================================================
# Store (cache)
# =====================================================================

_STORE: Dict[str, Dict[str, Any]] = {}
_LOADED: bool = False


def _key(symbol: str, tf: str) -> str:
    return f"{symbol.upper().strip()}::{tf.upper().strip()}"


def load_fibo_store(data_dir: str = DEFAULT_DATA_DIR) -> Dict[str, Any]:
    """
    Lee todos los CSV dentro de data_dir/** y arma cache:
      key = SYMBOL::TF
    Convención de filename:
      EURUSDz_M5.csv
      USTEC_x100z_H1.csv
    """
    global _STORE, _LOADED
    _STORE = {}
    _LOADED = False

    if not os.path.isdir(data_dir):
        return {"ok": False, "error": f"data_dir_not_found: {data_dir}"}

    csvs: List[str] = []
    for root, _, files in os.walk(data_dir):
        for fn in files:
            if fn.lower().endswith(".csv"):
                csvs.append(os.path.join(root, fn))

    loaded = 0
    for path in csvs:
        base = os.path.basename(path)
        name = base.replace(".csv", "")

        # parse symbol + tf desde filename
        # Ej: USTEC_x100z_H1  -> symbol=USTEC_x100z, tf=H1
        if "_" not in name:
            continue
        parts = name.split("_")
        tf = parts[-1].upper()
        symbol = "_".join(parts[:-1])

        # computar y guardar
        res = compute_fibo_stats_from_csv(path, pivot_order=6)
        if res.get("ok"):
            _STORE[_key(symbol, tf)] = {
                "symbol": symbol,
                "tf": tf,
                "file": path,
                **res,
            }
            loaded += 1

    _LOADED = True
    return {"ok": True, "loaded": loaded, "keys": len(_STORE)}


def get_fibo_stats(symbol: str, tf: str) -> Optional[Dict[str, Any]]:
    if not _LOADED:
        # carga perezosa por si te olvidaste llamarlo en startup
        load_fibo_store(DEFAULT_DATA_DIR)

    return _STORE.get(_key(symbol, tf))


def attach_fibo_stats(meta: Dict[str, Any], symbol: str, tf: str) -> Dict[str, Any]:
    """
    Adjunta a meta:
      meta["fibo_stats"] = {...}
    Sin romper si no hay data.
    """
    if not isinstance(meta, dict):
        meta = {}

    st = get_fibo_stats(symbol, tf)
    if st and st.get("ok"):
        meta = dict(meta)
        meta["fibo_stats"] = st["stats"]
        meta["fibo_span"] = {"from": st.get("from"), "to": st.get("to"), "rows": st.get("rows")}
    return meta