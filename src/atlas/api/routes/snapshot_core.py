# src/atlas/snapshot_core.py
from __future__ import annotations

from typing import Any, Dict, Optional, List


def _safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _safe_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def build_snapshot(
    *,
    world: str,
    symbol: str,
    tf: str,
    count: int,
    candles_payload: Dict[str, Any],  # ✅ clave: este parámetro debe existir
    atlas_mode: Optional[str] = None,
    raw_query: Optional[Dict[str, Any]] = None,
    debug: bool = False,
    lite: bool = False,
    **_ignored: Any,  # ignora kwargs extra para no reventar
) -> Dict[str, Any]:
    """
    Snapshot unificado.
    - Nunca debería tirar 500.
    - Blindaje duro: si no hay candles o hay pocas -> NO_DATA (no se llama motor).
    """
    rq = _safe_dict(raw_query)

    ok = bool(candles_payload.get("ok", False))
    candles = _safe_list(candles_payload.get("candles"))
    digits = int(candles_payload.get("digits") or 2)
    last_error = candles_payload.get("last_error", None)
    feed = candles_payload.get("feed", None)
    payload_reason = str(candles_payload.get("reason") or "")

    base: Dict[str, Any] = {
        "ok": ok,
        "world": world,
        "symbol": symbol,
        "tf": tf,
        "count": int(count or 0),
        "atlas_mode": atlas_mode,
        "candles": candles if not lite else (candles[-min(len(candles), 200):] if candles else []),
        "analysis": {
            "world": world,
            "raw_query": rq,
            "debug": bool(debug),
            "lite": bool(lite),
            "feed": feed,
        },
        "ui": {"rows": []},
        "last_error": last_error,
    }

    # 1) No data
    if not ok:
        base["analysis"].update(
            {
                "status": "NO_DATA",
                "reason": payload_reason or "Sin datos (candles_payload.ok=false)",
            }
        )
        base["ui"]["rows"] = [
            {"k": "world", "v": (world or "").upper().strip()},
            {"k": "status", "v": "NO_DATA"},
            {"k": "reason", "v": base["analysis"]["reason"]},
        ]
        return base

    # 2) Blindaje duro contra KeyError(-1) / candles[-1]
    if len(candles) < 5:
        base["ok"] = False
        base["analysis"].update(
            {
                "status": "NO_DATA",
                "reason": f"Velas insuficientes para motor (len={len(candles)}).",
            }
        )
        base["ui"]["rows"] = [
            {"k": "world", "v": (world or "").upper().strip()},
            {"k": "status", "v": "NO_DATA"},
            {"k": "reason", "v": base["analysis"]["reason"]},
        ]
        base["last_error"] = [-3, "NO_DATA"]
        return base

    w = (world or "").upper().strip()

    # =========================
    # WORLD: ATLAS_IA
    # =========================
    if w == "ATLAS_IA":
        try:
            from atlas.bot.atlas_ia.engine import eval_atlas_ia  # type: ignore

            res = eval_atlas_ia(
                symbol=symbol,
                tf=tf,
                candles=candles,
                digits=digits,
                atlas_mode=(atlas_mode or "SCALPING"),
                raw_query=rq,
                debug=bool(debug),
            )

            base["analysis"] = res.get("analysis", base["analysis"])
            base["ui"] = res.get("ui", base["ui"])

            base["analysis"]["world"] = "ATLAS_IA"
            base["analysis"]["raw_query"] = rq
            base["analysis"]["debug"] = bool(debug)
            base["analysis"]["lite"] = bool(lite)
            base["analysis"]["feed"] = feed

            return base

        except Exception as e:
            base["ok"] = False
            base["analysis"].update(
                {
                    "world": "ATLAS_IA",
                    "status": "ENGINE_ERROR",
                    "reason": f"atlas_ia engine error: {type(e).__name__}({e})",
                    "raw_query": rq,
                }
            )
            base["ui"]["rows"] = [
                {"k": "world", "v": "ATLAS_IA"},
                {"k": "status", "v": "ENGINE_ERROR"},
                {"k": "reason", "v": base["analysis"]["reason"]},
            ]
            base["last_error"] = [-9, "CRASH"]
            return base

    # =========================
    # WORLD: GATILLO
    # =========================
    if w == "GATILLO":
        try:
            from atlas.bot.gatillo.engine import eval_gatillo  # type: ignore

            res = eval_gatillo(
                symbol=symbol,
                tf=tf,
                candles=candles,
                digits=digits,
                raw_query=rq,
                debug=bool(debug),
            )

            base["analysis"] = res.get("analysis", base["analysis"])
            base["ui"] = res.get("ui", base["ui"])

            base["analysis"]["world"] = "GATILLO"
            base["analysis"]["raw_query"] = rq
            base["analysis"]["debug"] = bool(debug)
            base["analysis"]["lite"] = bool(lite)
            base["analysis"]["feed"] = feed

            return base

        except Exception as e:
            base["ok"] = False
            base["analysis"].update(
                {
                    "world": "GATILLO",
                    "status": "ENGINE_ERROR",
                    "reason": f"gatillo engine error: {type(e).__name__}({e})",
                    "raw_query": rq,
                }
            )
            base["ui"]["rows"] = [
                {"k": "world", "v": "GATILLO"},
                {"k": "status", "v": "ENGINE_ERROR"},
                {"k": "reason", "v": base["analysis"]["reason"]},
            ]
            base["last_error"] = [-9, "CRASH"]
            return base

    # =========================
    # Otros worlds (GAP / PRESESION) passthrough
    # =========================
    base["analysis"].update(
        {
            "status": "OK",
            "reason": "World passthrough (sin motor dedicado en snapshot_core)",
        }
    )
    base["ui"]["rows"] = [{"k": "world", "v": w}, {"k": "status", "v": "OK"}]
    return base
