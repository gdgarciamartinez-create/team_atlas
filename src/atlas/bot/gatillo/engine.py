# src/atlas/bot/gatillo/engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


def get_gatillo_cfg(symbol: str, tf: str, world: str = "GATILLOS") -> Dict[str, Any]:
    """
    Config del motor de gatillo.
    La idea: esto existe SIEMPRE para que dispatch/imports no revienten.

    Si después querés settings por símbolo / tf / world, se enchufa acá.
    """
    return {
        "enabled": True,
        "world": (world or "").upper().strip(),
        "symbol": symbol,
        "tf": (tf or "").upper().strip(),
        # naming tuyo:
        "state_names": {"wait": "WAIT", "zona": "ZONA", "gatillo": "GATILLO"},
    }


@dataclass
class GatilloEngine:
    """
    Clase opcional: la dejamos para compatibilidad con imports viejos.
    Hoy no hace magia: solo aplica una transición limpia de estados.
    """
    cfg: Dict[str, Any]

    def apply(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return apply_gatillo_world(payload, cfg=self.cfg)


def _ensure_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload.setdefault("analysis", {})
    payload["analysis"].setdefault("state", "WAIT")
    payload["analysis"].setdefault("message", "")
    payload.setdefault("ui", {})
    payload["ui"].setdefault("rows", [])
    return payload


def apply_gatillo_world(payload: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Aplica el 'world' de gatillo sobre el payload base.
    IMPORTANTE: No debe romper nunca. Si no hay datos, se queda en WAIT.

    Naming (tu regla):
      WAIT -> ZONA -> GATILLO
    """
    payload = _ensure_analysis(payload)
    cfg = cfg or get_gatillo_cfg(
        symbol=str(payload.get("symbol", "")),
        tf=str(payload.get("tf", "")),
        world=str(payload.get("world_real", "GATILLOS")),
    )

    if not cfg.get("enabled", True):
        payload["analysis"]["state"] = "WAIT"
        payload["analysis"]["message"] = "Gatillo deshabilitado"
        payload["ui"]["rows"].append({"k": "gatillo", "v": "disabled"})
        return payload

    candles = payload.get("candles") or []
    if not isinstance(candles, list) or len(candles) < 30:
        payload["analysis"]["state"] = "WAIT"
        payload["analysis"]["message"] = "Sin velas suficientes para evaluar gatillo"
        payload["ui"]["rows"].append({"k": "gatillo", "v": "WAIT (no candles)"})
        return payload

    # Estado actual (si viene desde otro mundo lo respetamos)
    state = str(payload["analysis"].get("state", "WAIT")).upper().strip()

    # Si ya venía con plan (ZONA), mantenemos.
    # Si venía WAIT, pasamos a ZONA (placeholder).
    if state == "WAIT":
        payload["analysis"]["state"] = "ZONA"
        payload["analysis"]["message"] = "Zona detectada (placeholder) - esperando condición"
        payload["ui"]["rows"].append({"k": "gatillo_state", "v": "ZONA"})
        return payload

    # Si ya estaba en ZONA, por ahora NO disparamos GATILLO automáticamente
    # (la lógica real va después).
    if state == "ZONA":
        payload["analysis"]["state"] = "ZONA"
        payload["analysis"]["message"] = "En zona - esperando gatillo real"
        payload["ui"]["rows"].append({"k": "gatillo_state", "v": "ZONA (waiting)"})
        return payload

    # Si por alguna razón viene GATILLO, lo respetamos.
    if state == "GATILLO":
        payload["analysis"]["state"] = "GATILLO"
        payload["analysis"]["message"] = payload["analysis"].get("message", "Gatillo activo")
        payload["ui"]["rows"].append({"k": "gatillo_state", "v": "GATILLO"})
        return payload

    # Default seguro
    payload["analysis"]["state"] = "WAIT"
    payload["analysis"]["message"] = "Estado desconocido -> WAIT"
    payload["ui"]["rows"].append({"k": "gatillo_state", "v": "WAIT (unknown)"})
    return payload