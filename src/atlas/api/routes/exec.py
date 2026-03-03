# src/atlas/api/routes/exec.py
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import time
import traceback

router = APIRouter()

# Importá TU función real que arma el snapshot.
# Si tu proyecto usa otro nombre, dejalo igual y cambiá SOLO este import.
# (La idea es envolverlo, no reescribir tu lógica)
try:
    from atlas.api.routes.snapshot_core import build_snapshot  # si existe
except Exception:
    build_snapshot = None

# Fallback: si tu lógica está en otro módulo típico
if build_snapshot is None:
    try:
        from atlas.api.routes.snapshot import build_snapshot  # si existe
    except Exception:
        build_snapshot = None

# Último intento: muchas veces está en atlas.data / bot / etc.
# Si sigue None, te va a decir claramente "build_snapshot missing".
# Así no adivinamos más.
@router.get("/snapshot")
def snapshot(
    world: str = Query("ATLAS_IA"),
    atlas_mode: str | None = Query(None),
    symbol: str = Query("XAUUSDz"),
    tf: str = Query("M5"),
    count: int = Query(200),
    debug: int = Query(0),
):
    started = time.perf_counter()
    steps = []
    def mark(step: str):
        steps.append({"t_ms": int((time.perf_counter() - started) * 1000), "step": step})

    mark("enter")

    if build_snapshot is None:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": "build_snapshot missing",
                "hint": "En exec.py ajustá el import al nombre real de tu función que arma el snapshot.",
                "steps": steps,
            },
        )

    try:
        mark("call_build_snapshot")
        data = build_snapshot(world=world, atlas_mode=atlas_mode, symbol=symbol, tf=tf, count=count)

        mark("got_snapshot")
        # Si el backend devuelve candles vacías, lo mostramos claro en debug
        if debug:
            candles = data.get("candles") if isinstance(data, dict) else None
            c_n = len(candles) if isinstance(candles, list) else 0
            data["_debug"] = {
                "ms_total": int((time.perf_counter() - started) * 1000),
                "steps": steps,
                "candles_len": c_n,
                "meta_in": {"world": world, "atlas_mode": atlas_mode, "symbol": symbol, "tf": tf, "count": count},
            }

        return data

    except Exception as e:
        mark("exception")
        payload = {
            "ok": False,
            "where": "snapshot",
            "error": repr(e),
            "ms_total": int((time.perf_counter() - started) * 1000),
            "steps": steps,
            "trace": traceback.format_exc().splitlines()[-30:],  # últimas 30 líneas
            "meta_in": {"world": world, "atlas_mode": atlas_mode, "symbol": symbol, "tf": tf, "count": count},
        }
        return JSONResponse(status_code=500, content=payload)
