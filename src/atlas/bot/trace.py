from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import json
import time


# ============================================================
# Catálogo fijo de razones NO_TRADE / SIGNAL
# (esto NO cambia por refresh)
# ============================================================
REASON_NO_DATA = "NO_DATA"
REASON_OUT_OF_WINDOW = "OUT_OF_WINDOW"
REASON_NO_CONTEXT = "NO_CONTEXT"
REASON_NO_CONFIRMATION = "NO_CONFIRMATION"
REASON_INVALIDATED = "INVALIDATED"
REASON_INVALID_CONFIG = "INVALID_CONFIG"
REASON_SIGNAL = "SIGNAL"

REASONS_CATALOG = {
    REASON_NO_DATA,
    REASON_OUT_OF_WINDOW,
    REASON_NO_CONTEXT,
    REASON_NO_CONFIRMATION,
    REASON_INVALIDATED,
    REASON_INVALID_CONFIG,
    REASON_SIGNAL,
}


def _now_ms() -> int:
    return int(time.time() * 1000)


def normalize_reason(raw_reason: str, *, state_public: str, world: str, atlas_mode: Optional[str]) -> str:
    """
    Convertimos motivos internos (raw) a un catálogo fijo humano y estable.
    - analysis.reason será SIEMPRE uno de REASONS_CATALOG
    - analysis.reason_raw conserva lo original
    """
    rr = (raw_reason or "").upper().strip()
    w = (world or "").upper().strip()
    m = (atlas_mode or "").upper().strip() if atlas_mode else ""

    # SIGNAL manda
    if state_public == "SIGNAL":
        return REASON_SIGNAL

    # errores / no data
    if rr in ("CANDLES_ERROR", "NOT_ENOUGH_CANDLES", "INCOMPLETE_DATA", "RANGE_ZERO"):
        return REASON_NO_DATA

    # config inválida
    if rr in ("INVALID_ATLAS_MODE", "NO_ENGINE_FOR_WORLD"):
        return REASON_INVALID_CONFIG

    # invalidación explícita si el motor la usa (ahora o a futuro)
    if "INVALID" in rr or rr in ("INVALIDATED", "PLAN_INVALIDATED", "SIGNAL_INVALIDATED"):
        return REASON_INVALIDATED

    # esperando confirmación (gatillo) o esperando zona (falta contexto/setup)
    if rr in ("WAITING_TRIGGER", "PLAN_FROZEN"):
        return REASON_NO_CONFIRMATION

    if rr in ("WAITING_ZONE",):
        return REASON_NO_CONTEXT

    # fallback seguro: si no calza, lo metemos a NO_CONTEXT
    return REASON_NO_CONTEXT


def build_last_decision(payload: Dict[str, Any]) -> str:
    """
    Texto humano, corto y definitivo.
    Siempre existe (NO_TRADE o SIGNAL).
    """
    world = payload.get("world", "")
    mode = payload.get("atlas_mode", "")
    symbol = payload.get("symbol", "")
    tf = payload.get("tf", "")
    state = payload.get("state", "")
    side = payload.get("side", "")
    reason = payload.get("analysis", {}).get("reason", "")
    reason_raw = payload.get("analysis", {}).get("reason_raw", "")
    note = payload.get("analysis", {}).get("note", "")
    price = payload.get("price", 0.0)
    plan_hash = payload.get("analysis", {}).get("plan_hash", "")

    entry = payload.get("entry", 0.0)
    sl = payload.get("sl", 0.0)
    tp = payload.get("tp", 0.0)

    if state == "SIGNAL":
        return (
            f"[{symbol} {tf}] {side} SIGNAL ✅ | entry={entry} sl={sl} tp={tp} | "
            f"reason={reason} | hash={plan_hash} | note={note}"
        )

    # NO_TRADE
    rr = f" (raw={reason_raw})" if reason_raw and reason_raw != reason else ""
    return (
        f"[{symbol} {tf}] NO_TRADE ⛔ | state={state} side={side} | reason={reason}{rr} | "
        f"price={price} | hash={plan_hash} | note={note}"
    )


def _logs_dir() -> Path:
    # repo_root/var/logs
    return Path("var") / "logs"


def log_decision(payload: Dict[str, Any]) -> None:
    """
    5.3 Log por símbolo:
    var/logs/EURUSDz.log
    Formato: ts_ms | symbol | tf | state | side | reason | entry | sl | tp | hash
    """
    try:
        symbol = str(payload.get("symbol", "UNKNOWN"))
        tf = str(payload.get("tf", ""))
        state = str(payload.get("state", ""))
        side = str(payload.get("side", ""))
        reason = str(payload.get("analysis", {}).get("reason", ""))
        plan_hash = str(payload.get("analysis", {}).get("plan_hash", ""))
        entry = payload.get("entry", 0.0)
        sl = payload.get("sl", 0.0)
        tp = payload.get("tp", 0.0)
        ts_ms = int(payload.get("ts_ms", _now_ms()))

        d = _logs_dir()
        d.mkdir(parents=True, exist_ok=True)
        fp = d / f"{symbol}.log"

        line = f"{ts_ms} | {symbol} | {tf} | {state} | {side} | {reason} | entry={entry} | sl={sl} | tp={tp} | hash={plan_hash}\n"
        fp.write_text(fp.read_text(encoding="utf-8") + line, encoding="utf-8")
    except Exception:
        # logging no debe romper snapshot
        pass