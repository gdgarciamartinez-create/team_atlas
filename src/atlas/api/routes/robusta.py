# src/atlas/api/routes/robusta.py
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from atlas.bot.robusta.ab_calculator import load_candles_csv, calc_A_B

router = APIRouter(prefix="/robusta", tags=["robusta"])


def infer_symbol_tf_from_filename(path: str) -> Dict[str, str]:
    """
    Soporta:
      EURUSDz_M5.csv
      EURUSDz_M1_202511120424_202602192328.csv
      USOILz_Daily_202101030000_202602200000.csv
      USTEC_x100z_M5_202506152200_202602192320.csv
    """
    base = os.path.basename(path)
    name = base.replace(".csv", "")

    # 1) patrón: SYMBOL_TF_rest...
    # TF permitidos (extensible)
    tf_candidates = [
        "M1", "M2", "M3", "M4", "M5", "M6", "M10", "M15", "M20", "M30",
        "H1", "H2", "H4", "H8", "H12",
        "DAILY", "D1",
    ]

    # buscamos "_TF" en el nombre
    symbol = ""
    tf = ""
    for tfc in tf_candidates:
        m = re.search(rf"^(.*)_{tfc}(_.*)?$", name, flags=re.IGNORECASE)
        if m:
            symbol = m.group(1)
            tf = tfc.upper()
            break

    if not symbol:
        # fallback: todo antes del primer "_"
        parts = name.split("_")
        symbol = parts[0]
        tf = parts[1].upper() if len(parts) > 1 else "NA"

    # normalizamos TF daily
    if tf == "D1":
        tf = "DAILY"

    return {"file": base, "symbol": symbol, "tf": tf}


def _list_csv_files(csv_root: str, limit_files: int) -> List[str]:
    files: List[str] = []
    if not os.path.exists(csv_root):
        return files

    # Recorremos recursivo por si tenés subcarpetas
    for root, _, filenames in os.walk(csv_root):
        for fn in filenames:
            if fn.lower().endswith(".csv"):
                files.append(os.path.join(root, fn))

    # orden estable
    files.sort()
    if limit_files and limit_files > 0:
        files = files[:limit_files]
    return files


@router.get("/ab")
def robusta_ab(
    csv_root: str = Query("data/csv", description="Carpeta donde están los CSV (relativa o absoluta)"),
    limit_files: int = Query(50, ge=1, le=5000, description="Máximo de archivos a procesar"),
    limit_rows: int = Query(5000, ge=100, le=500000, description="Máximo de velas por CSV"),
    atr_period: int = Query(14, ge=2, le=200, description="Periodo ATR"),
    b_price_pct: float = Query(0.0005, ge=0.0, le=0.05, description="0.05% del precio (0.0005)"),
    b_atr_mult: float = Query(0.2, ge=0.0, le=10.0, description="Multiplicador ATR para buffer"),
    symbol: Optional[str] = Query(None, description="Filtro opcional por símbolo (ej: XAUUSDz)"),
    tf: Optional[str] = Query(None, description="Filtro opcional por TF (ej: M5, H1, DAILY)"),
) -> Dict[str, Any]:
    csv_root_abs = os.path.abspath(csv_root)
    files = _list_csv_files(csv_root_abs, limit_files=limit_files)

    sym_filter = (symbol or "").strip()
    tf_filter = (tf or "").strip().upper()

    rows: List[Dict[str, Any]] = []

    for path in files:
        info = infer_symbol_tf_from_filename(path)
        sym = info["symbol"]
        tff = info["tf"]

        # filtros opcionales
        if sym_filter and sym != sym_filter:
            continue
        if tf_filter and tff != tf_filter:
            continue

        try:
            candles = load_candles_csv(path, limit=limit_rows)
            n, price_ref, A, B, AB, meta = calc_A_B(
                candles=candles,
                atr_period=atr_period,
                b_price_pct=b_price_pct,
                b_atr_mult=b_atr_mult,
            )

            rows.append({
                "file": info["file"],
                "symbol": sym,
                "tf": tff,
                "n": n,
                "price_ref": price_ref,
                "A_atr": A,
                "B_buffer": B,
                "A_plus_B": AB,
                "meta": meta,
            })
        except Exception as e:
            rows.append({
                "file": info["file"],
                "symbol": sym,
                "tf": tff,
                "error": repr(e),
            })

    return {
        "ok": True,
        "csv_root": csv_root_abs,
        "filters": {"symbol": sym_filter or None, "tf": tf_filter or None},
        "params": {
            "limit_files": limit_files,
            "limit_rows": limit_rows,
            "atr_period": atr_period,
            "b_price_pct": b_price_pct,
            "b_atr_mult": b_atr_mult,
        },
        "rows": rows,
        "count": len(rows),
    }