# src/atlas/core/telemetry.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Literal
import time

Action = Literal["TRADE", "WAIT", "NO_TRADE"]
Phase  = Literal["IDLE", "OBSERVANDO", "ALERTADO"]

# ------------------------------------------------------------
# 1) BUFFER DE EVENTOS (historial corto)
# ------------------------------------------------------------
_DECISIONS: List[Dict[str, Any]] = []     # decisiones (últimas N)
_EVENTS: List[Dict[str, Any]] = []        # eventos genéricos (últimas N)

def _now() -> int:
    return int(time.time())

def _clip_list(buf: List[Dict[str, Any]], max_len: int = 200, trim: int = 50) -> None:
    if len(buf) > max_len:
        del buf[:trim]

def log_event(kind: str, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
    """Evento simple (para debug humano/UI)."""
    _EVENTS.append({
        "ts": _now(),
        "kind": str(kind),
        "message": str(message),
        "extra": extra or {},
    })
    _clip_list(_EVENTS)

def log_decision(
    world: str,
    symbol: str,
    tf: str,
    action: Action,
    reason: str,
    phase: Phase,
    checklist: Optional[Dict[str, bool]] = None,
    tags: Optional[List[str]] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Guarda la decisión del motor.
    - payload: opcional (entry/sl/tp/poi/gap_info) para UI.
    """
    _DECISIONS.append({
        "ts": _now(),
        "world": (world or "GENERAL").strip().upper(),
        "symbol": (symbol or "XAUUSD").strip().upper(),
        "tf": (tf or "M1").strip().upper(),
        "phase": phase,
        "action": action,
        "reason": str(reason or ""),
        "checklist": checklist or {},
        "tags": tags or [],
        "payload": payload or {},
    })
    _clip_list(_DECISIONS)

def get_decisions_snapshot(limit: int = 25) -> Dict[str, Any]:
    lim = max(0, min(int(limit), 200))
    items = _DECISIONS[-lim:] if lim > 0 else list(_DECISIONS)
    return {"count": len(_DECISIONS), "items": items}

def get_events_snapshot(limit: int = 25) -> Dict[str, Any]:
    lim = max(0, min(int(limit), 200))
    items = _EVENTS[-lim:] if lim > 0 else list(_EVENTS)
    return {"count": len(_EVENTS), "items": items}

def clear_logs() -> None:
    _DECISIONS.clear()
    _EVENTS.clear()

# ------------------------------------------------------------
# 2) CONTADORES LAB (resumen numérico simple)
# ------------------------------------------------------------
LAB_STATS: Dict[str, Any] = {
    "started_ts": _now(),
    "total_ticks": 0,     # cuántas veces corrió el snapshot con velas
    "total_decisions": 0, # cuántas veces se registró una decisión
    "trade": 0,
    "wait": 0,
    "no_trade": 0,
    "last_action": "NO_TRADE",
    "last_reason": "BOOT",
    "last_ts": 0,
}

def lab_tick() -> None:
    LAB_STATS["total_ticks"] = int(LAB_STATS.get("total_ticks", 0)) + 1
    LAB_STATS["last_ts"] = _now()

def lab_count_decision(action: Action, reason: str) -> None:
    LAB_STATS["total_decisions"] = int(LAB_STATS.get("total_decisions", 0)) + 1
    LAB_STATS["last_action"] = action
    LAB_STATS["last_reason"] = str(reason or "")
    if action == "TRADE":
        LAB_STATS["trade"] = int(LAB_STATS.get("trade", 0)) + 1
    elif action == "WAIT":
        LAB_STATS["wait"] = int(LAB_STATS.get("wait", 0)) + 1
    else:
        LAB_STATS["no_trade"] = int(LAB_STATS.get("no_trade", 0)) + 1

def get_lab_stats() -> Dict[str, Any]:
    return dict(LAB_STATS)

# ------------------------------------------------------------
# 3) NORMALIZADOR DE RAZONES
# ------------------------------------------------------------
def normalize_reason(action: Action, reason: str) -> str:
    r = (reason or "").strip().upper()
    if not r:
        return "NO_REASON"
    mapping = {
        "LAB_MODE": "LAB_MODE_SILENT",
        "BOOT": "BOOT",
        "NO_CANDLES": "NO_CANDLES",
        "MT5_FAIL": "DATA_FAIL",
        "SCENARIO_CLOSED": "SCENARIO_CLOSED",
        "INVALIDATED_BY_TWO_CLOSES": "INVALIDATED_BY_TWO_CLOSES",
        "BAD_RISK_GEOMETRY": "BAD_RISK_GEOMETRY",
        "NO_POI": "NO_POI",
        "DOCTRINAL_GUARD": "DOCTRINAL_GUARD",
    }
    return mapping.get(r, r)

# ------------------------------------------------------------
# 4) CONSTRUCTOR DE PANEL_TEXT
# ------------------------------------------------------------
def build_panel_text(world: str, symbol: str, tf: str, candles_len: int, data_ok: bool, last_error: str, bot_phase: str, decision_action: str, decision_reason: str) -> List[str]:
    lines = []
    lines.append("LAB_ENGINE: backend OK")
    lines.append(f"symbol={symbol} tf={tf} mundo={world}")
    lines.append(f"velas={candles_len} " + ("DATA OK" if data_ok else f"DATA FAIL: {last_error[:20]}"))
    lines.append(f"PHASE={bot_phase} DECISION={decision_action} REASON={decision_reason}")
    return lines