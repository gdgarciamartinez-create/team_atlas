# src/atlas/api/routes/robusta.py

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from atlas.bot.robusta.ab_calculator import (
    calc_A_B,
    find_csv_files,
    load_candles_csv,
    parse_symbol_tf_from_filename,
)

router = APIRouter(prefix="/robusta", tags=["robusta"])


@router.get("/ab")
def robusta_ab(
    csv_root: str = Query("data/csv", description="Carpeta raíz donde están los CSV exportados de MT5"),
    symbol: Optional[str] = Query(None, description="Filtrar por símbolo exacto, ej: EURUSDz"),
    tf: Optional[str] = Query(None, description="Filtrar por TF, ej: M5, H1, D1"),
    limit: int = Query(6000, ge=200, le=200000, description="Máximo de velas a leer por archivo"),
) -> Dict[str, Any]:
    """
    Calcula A+B sobre los CSV exportados desde MT5.
    Devuelve lista de resultados por archivo (symbol/tf).

    A = ATR14 * 1.2
    B = max(0.05% precio, ATR14 * 0.2)
    """
    # normalizar ruta
    csv_root = csv_root.replace("\\", "/").strip()
    if not os.path.isabs(csv_root):
        # relativo al root del proyecto
        csv_root = os.path.join(os.getcwd(), csv_root)

    if not os.path.exists(csv_root):
        return {"ok": False, "error": f"csv_root no existe: {csv_root}", "items": []}

    files = find_csv_files(csv_root)

    items: List[Dict[str, Any]] = []
    for path in files:
        try:
            sym, tf_found = parse_symbol_tf_from_filename(path)

            if symbol and sym != symbol:
                continue
            if tf and tf_found.upper() != tf.upper():
                continue

            candles = load_candles_csv(path, limit=limit)
            ab = calc_A_B(candles)

            items.append(
                {
                    "symbol": sym,
                    "tf": tf_found,
                    "file": path.replace("\\", "/"),
                    "count": len(candles),
                    **ab,
                }
            )
        except Exception as e:
            items.append(
                {
                    "symbol": None,
                    "tf": None,
                    "file": path.replace("\\", "/"),
                    "count": 0,
                    "error": str(e),
                }
            )

    # orden: symbol, tf
    items.sort(key=lambda x: (str(x.get("symbol")), str(x.get("tf"))))

    return {"ok": True, "csv_root": csv_root.replace("\\", "/"), "items": items}
