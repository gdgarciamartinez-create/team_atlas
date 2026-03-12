from __future__ import annotations

from fastapi import APIRouter, Query
import requests
import time
from typing import Any, Dict

from atlas.snapshot_core import build_snapshot

router = APIRouter()


def _now_ms() -> int:
    return int(time.time() * 1000)


@router.get("/snapshot")
def snapshot(
    world: str = Query("ATLAS_IA"),
    symbol: str = Query("XAUUSDz"),
    tf: str = Query("M5"),
    count: int = Query(200),
    atlas_mode: str = Query("SCALPING"),
):

    url = f"http://127.0.0.1:8001/api/mt5/candles?symbol={symbol}&tf={tf}&count={count}"

    errors: list[str] = []
    candles_payload: Dict[str, Any]

    t0 = time.time()
    try:
        r = requests.get(url, timeout=3)
        candles_payload = r.json() if r.ok else {}
        if not isinstance(candles_payload, dict):
            candles_payload = {}
    except Exception as e:
        candles_payload = {}
        errors.append(f"MT5_FETCH_FAIL: {type(e).__name__}({e})")

    dt_ms = int((time.time() - t0) * 1000)

    # normalización mínima del payload (blindaje)
    ok = bool(candles_payload.get("ok", False))
    candles = candles_payload.get("candles", [])
    if not isinstance(candles, list):
        candles = []
    candles_payload["candles"] = candles

    if not ok:
        candles_payload["ok"] = False
        candles_payload.setdefault("reason", "mt5 payload not ok")
        candles_payload.setdefault("last_error", [-2, "NO_DATA"])
        candles_payload.setdefault("digits", 2)

    # etiqueta provider (solo informativa)
    candles_payload.setdefault("feed", "MT5")

    out = build_snapshot(
        world=world,
        symbol=symbol,
        tf=tf,
        count=count,
        candles_payload=candles_payload,
        atlas_mode=atlas_mode,
        raw_query={
            "world": world,
            "atlas_mode": atlas_mode,
            "symbol": symbol,
            "tf": tf,
            "count": count,
        },
    )

    # post-blindaje contract
    if not isinstance(out, dict):
        out = {"ok": False, "world": world, "symbol": symbol, "tf": tf, "count": count, "atlas_mode": atlas_mode}

    out.setdefault("errors", [])
    if isinstance(out["errors"], list) and errors:
        out["errors"].extend(errors)

    out.setdefault("meta", {})
    if isinstance(out["meta"], dict):
        out["meta"].setdefault("ts", _now_ms())
        out["meta"].setdefault("provider", "MT5")
        out["meta"]["fetch_ms"] = dt_ms

    return out