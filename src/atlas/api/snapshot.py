from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Query

from atlas.data.market_data import get_candles_payload

from atlas.bot.gatillo.engine import eval_gatillo
from atlas.bot.gap.engine import eval_gap
from atlas.bot.presesion.engine import eval_presesion
from atlas.bot.atlas_ia.engine import eval_atlas_ia

router = APIRouter()


def _normalize_world(w: Optional[str]) -> str:
    w = (w or "").strip().upper()
    return w


@router.get("/snapshot")
def snapshot(
    world: str = Query("GATILLO"),
    symbol: str = Query("EURUSDz"),
    tf: str = Query("M5"),
    count: int = Query(220),
    atlas_mode: Optional[str] = Query(None),
    bias: Optional[str] = Query(None),
    floor: Optional[float] = Query(None),
    ceiling: Optional[float] = Query(None),
    debug: bool = Query(False),
    lite: bool = Query(True),
) -> Dict[str, Any]:
    w = _normalize_world(world)

    # 1) Traer velas estándar
    md = get_candles_payload(symbol=symbol, tf=tf, count=int(count))

    # Base de respuesta
    base: Dict[str, Any] = {
        "ok": bool(md.get("ok")),
        "world": w,
        "symbol": symbol,
        "tf": tf,
        "count": int(count),
        "atlas_mode": atlas_mode,
        "candles": md.get("candles", []) if md.get("ok") else [],
        "last_error": md.get("last_error"),
        "feed": md.get("feed"),
    }

    # Si no hay data: devolvemos sin romper
    if not md.get("ok"):
        base["analysis"] = {
            "world": w,
            "status": "NO_DATA",
            "reason": md.get("reason") or md.get("error") or "no candles",
        }
        base["ui"] = {"rows": [{"k": "error", "v": base["analysis"]["reason"]}]}
        return base

    # 2) Enrutado por mundo
    raw_query = {
        "world": w,
        "symbol": symbol,
        "tf": tf,
        "count": int(count),
        "atlas_mode": atlas_mode,
        "bias": bias,
        "floor": floor,
        "ceiling": ceiling,
        "debug": debug,
        "lite": lite,
    }

    try:
        if w == "GATILLO":
            analysis, ui = eval_gatillo(md, raw_query=raw_query)
        elif w == "GAP":
            analysis, ui = eval_gap(md, raw_query=raw_query)
        elif w == "PRESESION":
            analysis, ui = eval_presesion(md, raw_query=raw_query)
        elif w == "ATLAS_IA":
            analysis, ui = eval_atlas_ia(md, raw_query=raw_query)
        else:
            analysis = {
                "world": w,
                "status": "UNKNOWN_WORLD",
                "reason": f"Unknown world: {w}",
                "raw_query": raw_query,
            }
            ui = {"rows": [{"k": "world", "v": w}, {"k": "status", "v": "UNKNOWN_WORLD"}]}

        base["analysis"] = analysis
        base["ui"] = ui
        base["ok"] = base["ok"] and (analysis.get("status") not in ("IMPORT_ERROR", "CRASH"))
        return base

    except Exception as e:
        base["analysis"] = {
            "world": w,
            "status": "CRASH",
            "reason": f"snapshot crash: {repr(e)}",
            "raw_query": raw_query,
        }
        base["ui"] = {"rows": [{"k": "error", "v": base["analysis"]["reason"]}]}
        base["ok"] = False
        return base
