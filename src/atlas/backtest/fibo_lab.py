# src/atlas/backtest/fibo_lab.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import os
import math
import json
from datetime import datetime


# =============================================================================
# CSV Loader (MT5)
# =============================================================================

def _try_import_pandas():
    try:
        import pandas as pd  # type: ignore
        return pd
    except Exception:
        return None


def _sniff_sep(first_line: str) -> str:
    # MT5 suele venir TAB con header <DATE><TIME>...
    if "\t" in first_line:
        return "\t"
    # a veces viene separado por comas/; dependiendo export
    if ";" in first_line and first_line.count(";") > first_line.count(","):
        return ";"
    return ","


def load_mt5_csv(path: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Devuelve candles normalizadas:
      { "t": int(ms), "o": float, "h": float, "l": float, "c": float, "v": float }
    Acepta export MT5 con header tipo: <DATE>\t<TIME>\t<OPEN>...
    """
    meta = {"path": path, "ok": False}
    if not os.path.exists(path):
        meta["error"] = "file_not_found"
        return [], meta

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        first = f.readline().strip()

    sep = _sniff_sep(first)
    pd = _try_import_pandas()

    # Ruta 1: pandas (rápido)
    if pd is not None:
        try:
            df = pd.read_csv(path, sep=sep, engine="python")
            # Normalizar headers tipo <DATE>
            df.columns = [str(c).strip().replace("<", "").replace(">", "") for c in df.columns]

            # Soportar variantes comunes
            # DATE, TIME, OPEN, HIGH, LOW, CLOSE, TICKVOL, VOL, SPREAD
            need = {"DATE", "TIME", "OPEN", "HIGH", "LOW", "CLOSE"}
            if not need.issubset(set(df.columns)):
                # a veces viene "Date" etc
                cols = {c.upper(): c for c in df.columns}
                if not need.issubset(set(cols.keys())):
                    meta["error"] = f"bad_columns:{df.columns.tolist()}"
                    return [], meta
                # renombrar
                df = df.rename(columns={cols[k]: k for k in need})

            # Fecha/hora
            # MT5: DATE=YYYY.MM.DD  TIME=HH:MM:SS
            dt = pd.to_datetime(df["DATE"].astype(str) + " " + df["TIME"].astype(str), errors="coerce")
            df = df.assign(_dt=dt).dropna(subset=["_dt"])

            def _col(name: str, default: float = 0.0) -> List[float]:
                if name in df.columns:
                    return [float(x) if x is not None else default for x in df[name].tolist()]
                return [default] * len(df)

            t_ms = [(int(x.to_pydatetime().timestamp() * 1000)) for x in df["_dt"].tolist()]
            o = _col("OPEN")
            h = _col("HIGH")
            l = _col("LOW")
            c = _col("CLOSE")

            # volumen opcional
            v = _col("TICKVOL", 0.0)
            if all(x == 0.0 for x in v) and "VOL" in df.columns:
                v = _col("VOL", 0.0)

            candles = []
            for i in range(len(t_ms)):
                candles.append({"t": t_ms[i], "o": o[i], "h": h[i], "l": l[i], "c": c[i], "v": v[i]})

            meta["ok"] = True
            meta["rows"] = len(candles)
            meta["sep"] = sep
            return candles, meta
        except Exception as e:
            meta["error"] = f"pandas_read_failed:{e}"
            # sigue a modo manual

    # Ruta 2: manual (sin pandas)
    try:
        candles: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            header = f.readline().strip().split(sep)
            header = [h.strip().replace("<", "").replace(">", "") for h in header]
            idx = {name.upper(): i for i, name in enumerate(header)}

            def _get(row: List[str], k: str, default: str = "") -> str:
                i = idx.get(k.upper(), -1)
                if i < 0 or i >= len(row):
                    return default
                return row[i].strip()

            while True:
                line = f.readline()
                if not line:
                    break
                parts = [p.strip() for p in line.strip().split(sep)]
                if len(parts) < 6:
                    continue

                date = _get(parts, "DATE")
                tm = _get(parts, "TIME")
                dt = datetime.strptime(date + " " + tm, "%Y.%m.%d %H:%M:%S")
                t_ms = int(dt.timestamp() * 1000)

                o = float(_get(parts, "OPEN", "0") or 0)
                h = float(_get(parts, "HIGH", "0") or 0)
                l = float(_get(parts, "LOW", "0") or 0)
                c = float(_get(parts, "CLOSE", "0") or 0)

                v = 0.0
                tv = _get(parts, "TICKVOL", "")
                if tv:
                    try:
                        v = float(tv)
                    except Exception:
                        v = 0.0

                candles.append({"t": t_ms, "o": o, "h": h, "l": l, "c": c, "v": v})

        meta["ok"] = True
        meta["rows"] = len(candles)
        meta["sep"] = sep
        return candles, meta
    except Exception as e:
        meta["error"] = f"manual_read_failed:{e}"
        return [], meta


# =============================================================================
# Swing / pivots (simple + robusto)
# =============================================================================

def _pivot_points(candles: List[Dict[str, Any]], left: int = 3, right: int = 3) -> List[Tuple[int, str]]:
    """
    Detecta pivotes tipo fractal:
    - pivot high: high mayor que highs vecinos
    - pivot low: low menor que lows vecinos
    Devuelve lista de (index, "H"|"L") ordenada.
    """
    n = len(candles)
    if n < left + right + 5:
        return []

    pivots: List[Tuple[int, str]] = []
    highs = [float(c["h"]) for c in candles]
    lows = [float(c["l"]) for c in candles]

    for i in range(left, n - right):
        hi = highs[i]
        lo = lows[i]

        is_hi = True
        for j in range(i - left, i + right + 1):
            if j == i:
                continue
            if highs[j] >= hi:
                is_hi = False
                break

        is_lo = True
        for j in range(i - left, i + right + 1):
            if j == i:
                continue
            if lows[j] <= lo:
                is_lo = False
                break

        if is_hi:
            pivots.append((i, "H"))
        elif is_lo:
            pivots.append((i, "L"))

    # limpiar alternancia (evitar H H o L L seguidos quedándonos con el más extremo)
    cleaned: List[Tuple[int, str]] = []
    for idx, typ in pivots:
        if not cleaned:
            cleaned.append((idx, typ))
            continue
        pidx, ptyp = cleaned[-1]
        if typ != ptyp:
            cleaned.append((idx, typ))
            continue

        # mismo tipo: conservar el más extremo
        if typ == "H":
            if highs[idx] > highs[pidx]:
                cleaned[-1] = (idx, typ)
        else:
            if lows[idx] < lows[pidx]:
                cleaned[-1] = (idx, typ)

    return cleaned


@dataclass
class LegSample:
    direction: str  # "UP" | "DOWN"
    impulse_points: float
    retrace_ratio: float
    touched_618: bool
    touched_786: bool
    continued: bool


def _measure_legs(
    candles: List[Dict[str, Any]],
    pivots: List[Tuple[int, str]],
    tol: float = 0.008,        # tolerancia en ratio (0.8% del swing)
    lookahead: int = 120,      # velas máximas para verificar continuidad post retroceso
) -> List[LegSample]:
    """
    Para cada par de pivotes alternados (L->H o H->L) forma un impulso.
    Luego busca el retroceso siguiente hasta el siguiente pivot contrario y mide ratio.

    ratio = retrace / impulse
      - impulso UP: retrace = (impulse_high - retrace_low)
      - impulso DOWN: retrace = (retrace_high - impulse_low)

    "touch" 0.618 y 0.786:
      - touched si retrace_ratio >= level - tol
    "continuidad":
      - después del retroceso, rompe el extremo del impulso dentro de lookahead velas
    """
    if len(pivots) < 4:
        return []

    highs = [float(c["h"]) for c in candles]
    lows = [float(c["l"]) for c in candles]

    out: List[LegSample] = []

    # Usamos triples pivotes: A (inicio impulso) -> B (fin impulso) -> C (fin retroceso)
    for i in range(len(pivots) - 2):
        a_idx, a_typ = pivots[i]
        b_idx, b_typ = pivots[i + 1]
        c_idx, c_typ = pivots[i + 2]

        # impulso válido es L->H (UP) o H->L (DOWN)
        if a_typ == "L" and b_typ == "H" and c_typ == "L":
            impulse = highs[b_idx] - lows[a_idx]
            if impulse <= 0:
                continue
            retr = highs[b_idx] - lows[c_idx]
            rr = max(retr / impulse, 0.0)

            # continuidad: después del c_idx, rompe el high de b_idx
            end = min(len(candles), c_idx + lookahead)
            cont = any(highs[j] > highs[b_idx] for j in range(c_idx + 1, end))

            out.append(
                LegSample(
                    direction="UP",
                    impulse_points=float(impulse),
                    retrace_ratio=float(rr),
                    touched_618=rr >= (0.618 - tol),
                    touched_786=rr >= (0.786 - tol),
                    continued=bool(cont),
                )
            )

        elif a_typ == "H" and b_typ == "L" and c_typ == "H":
            impulse = highs[a_idx] - lows[b_idx]
            if impulse <= 0:
                continue
            retr = highs[c_idx] - lows[b_idx]
            rr = max(retr / impulse, 0.0)

            # continuidad: después del c_idx, rompe el low de b_idx
            end = min(len(candles), c_idx + lookahead)
            cont = any(lows[j] < lows[b_idx] for j in range(c_idx + 1, end))

            out.append(
                LegSample(
                    direction="DOWN",
                    impulse_points=float(impulse),
                    retrace_ratio=float(rr),
                    touched_618=rr >= (0.618 - tol),
                    touched_786=rr >= (0.786 - tol),
                    continued=bool(cont),
                )
            )

        else:
            continue

    return out


# =============================================================================
# Reporte
# =============================================================================

def _pct(a: int, b: int) -> float:
    if b <= 0:
        return 0.0
    return float(a) * 100.0 / float(b)


def fibo_report_from_csv(
    path: str,
    pivot_left: int = 3,
    pivot_right: int = 3,
    tol: float = 0.008,
    lookahead: int = 120,
    min_rows: int = 400,
) -> Dict[str, Any]:
    candles, meta = load_mt5_csv(path)
    if not candles or len(candles) < min_rows:
        return {
            "ok": False,
            "path": path,
            "meta": meta,
            "reason": f"not_enough_rows({len(candles)})",
        }

    pivots = _pivot_points(candles, left=pivot_left, right=pivot_right)
    legs = _measure_legs(candles, pivots, tol=tol, lookahead=lookahead)

    if not legs:
        return {
            "ok": False,
            "path": path,
            "meta": meta,
            "reason": "no_legs_detected",
            "pivots": len(pivots),
        }

    n = len(legs)
    t618 = sum(1 for x in legs if x.touched_618)
    t786 = sum(1 for x in legs if x.touched_786)

    cont_total = sum(1 for x in legs if x.continued)
    cont_618 = sum(1 for x in legs if x.touched_618 and x.continued)
    cont_786 = sum(1 for x in legs if x.touched_786 and x.continued)

    # Distribución básica de ratios
    ratios = sorted([x.retrace_ratio for x in legs])
    def _q(q: float) -> float:
        if not ratios:
            return 0.0
        k = int(round((len(ratios) - 1) * q))
        return float(ratios[max(0, min(len(ratios) - 1, k))])

    up = [x for x in legs if x.direction == "UP"]
    down = [x for x in legs if x.direction == "DOWN"]

    return {
        "ok": True,
        "path": path,
        "meta": meta,
        "params": {
            "pivot_left": pivot_left,
            "pivot_right": pivot_right,
            "tol": tol,
            "lookahead": lookahead,
            "min_rows": min_rows,
        },
        "counts": {
            "legs": n,
            "touch_618": t618,
            "touch_786": t786,
            "continued": cont_total,
            "continued_when_touch_618": cont_618,
            "continued_when_touch_786": cont_786,
        },
        "rates_pct": {
            "touch_618": _pct(t618, n),
            "touch_786": _pct(t786, n),
            "continued": _pct(cont_total, n),
            "continued_given_618": _pct(cont_618, t618),
            "continued_given_786": _pct(cont_786, t786),
        },
        "ratio_quantiles": {
            "q10": _q(0.10),
            "q25": _q(0.25),
            "q50": _q(0.50),
            "q75": _q(0.75),
            "q90": _q(0.90),
        },
        "by_direction": {
            "UP": {
                "legs": len(up),
                "touch_786_pct": _pct(sum(1 for x in up if x.touched_786), len(up)),
                "continued_pct": _pct(sum(1 for x in up if x.continued), len(up)),
            },
            "DOWN": {
                "legs": len(down),
                "touch_786_pct": _pct(sum(1 for x in down if x.touched_786), len(down)),
                "continued_pct": _pct(sum(1 for x in down if x.continued), len(down)),
            },
        },
    }


def scan_folder(
    root_dir: str,
    exts: Tuple[str, ...] = (".csv",),
    pivot_left: int = 3,
    pivot_right: int = 3,
    tol: float = 0.008,
    lookahead: int = 120,
    min_rows: int = 400,
) -> Dict[str, Any]:
    """
    Escanea una carpeta (recursivo) y genera reporte por archivo.
    """
    results: List[Dict[str, Any]] = []
    for base, _, files in os.walk(root_dir):
        for fn in files:
            if not fn.lower().endswith(exts):
                continue
            path = os.path.join(base, fn)
            rep = fibo_report_from_csv(
                path,
                pivot_left=pivot_left,
                pivot_right=pivot_right,
                tol=tol,
                lookahead=lookahead,
                min_rows=min_rows,
            )
            results.append(rep)

    ok = [r for r in results if r.get("ok")]
    bad = [r for r in results if not r.get("ok")]

    return {
        "ok": True,
        "root_dir": root_dir,
        "summary": {
            "files_total": len(results),
            "files_ok": len(ok),
            "files_bad": len(bad),
        },
        "results": results,
    }


def save_report(report: Dict[str, Any], out_path: str) -> str:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return out_path