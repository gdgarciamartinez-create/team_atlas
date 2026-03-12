from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any


# ------------------------------------------------------------
# Config oficial de TF por world (PRE-UI FINAL)
# ------------------------------------------------------------

@dataclass(frozen=True)
class WorldTF:
    world: str
    analysis_tfs: List[str]   # donde nace zona / mapa
    trigger_tfs: List[str]    # donde se gatilla / confirma
    note: str = ""


# Normalizadores simples
def _u(x: str) -> str:
    return (x or "").strip().upper()


def _norm_world(w: str) -> str:
    w = _u(w)
    allowed = {"GAP", "PRESESION", "SCALPING", "FOREX", "ATLAS_IA"}
    # compat: si te llega ATLAS_IA, lo tratamos como SCALPING/FOREX según atlas_mode fuera
    return w if w in allowed else "ATLAS_IA"


def _norm_tf(tf: str) -> str:
    tf = _u(tf)
    allowed = {"M1", "M2", "M3", "M5", "M15", "M30", "H1", "H4", "D1"}
    return tf if tf in allowed else "M5"


# ------------------------------------------------------------
# TF oficiales por world (lo que pediste)
# ------------------------------------------------------------
WORLDS: Dict[str, WorldTF] = {
    # GAP: ultra táctico
    "GAP": WorldTF(
        world="GAP",
        analysis_tfs=["M1"],
        trigger_tfs=["M1"],
        note="GAP opera en M1: detección y gatillo en el mismo TF.",
    ),

    # PRESESION: mapa limpio + gatillo fino
    "PRESESION": WorldTF(
        world="PRESESION",
        analysis_tfs=["M5"],
        trigger_tfs=["M3", "M1"],
        note="PRESESION: zona en M5; gatillo en M3/M1.",
    ),

    # SCALPING: base M5 + ejecución M1, M3 opcional cuando hay ruido
    "SCALPING": WorldTF(
        world="SCALPING",
        analysis_tfs=["M5"],
        trigger_tfs=["M1", "M3"],
        note="SCALPING: zona en M5; gatillo M1; M3 opcional (ruido/NAS).",
    ),

    # FOREX: mapa serio + confirmación + gatillo
    "FOREX": WorldTF(
        world="FOREX",
        analysis_tfs=["H1", "M15"],
        trigger_tfs=["M5", "M3"],
        note="FOREX: zona H1, confirmación M15, gatillo M5/M3.",
    ),

    # ATLAS_IA: world agregado (la UI usa /api/snapshot world=ATLAS_IA con atlas_mode=SCALPING|FOREX)
    "ATLAS_IA": WorldTF(
        world="ATLAS_IA",
        analysis_tfs=["M5"],
        trigger_tfs=["M1", "M3"],
        note="ATLAS_IA: por defecto SCALPING (M5->M1). En modo FOREX, se usa config FOREX.",
    ),
}


# ------------------------------------------------------------
# Overrides por símbolo (si quieres “carácter” por activo)
# Ej: NAS más cómodo con M3 como trigger principal
# ------------------------------------------------------------
SYMBOL_OVERRIDES: Dict[str, Dict[str, Any]] = {
    # ejemplo: NASDAQ
    "USTEC_X100Z": {
        "SCALPING": {"analysis_tfs": ["M5"], "trigger_tfs": ["M1", "M3"], "note": "NAS: M3 ayuda a filtrar ruido."},
    },
    # ejemplo: Oro gap ya separado por world, no necesita override aquí.
}


def get_world_tf(world: str, *, atlas_mode: Optional[str] = None, symbol: Optional[str] = None) -> WorldTF:
    """
    Devuelve la configuración TF final:
    - Si world=ATLAS_IA, usa SCALPING o FOREX según atlas_mode.
    - Aplica overrides por símbolo si existen.
    """
    w = _norm_world(world)
    m = _u(atlas_mode or "")
    sym = _u(symbol or "")

    # Resolver ATLAS_IA a modo real
    if w == "ATLAS_IA":
        if m == "FOREX":
            base = WORLDS["FOREX"]
        else:
            base = WORLDS["SCALPING"]
    else:
        base = WORLDS.get(w, WORLDS["ATLAS_IA"])

    # Aplicar override por símbolo si corresponde
    ov = SYMBOL_OVERRIDES.get(sym, {}).get(base.world)
    if isinstance(ov, dict):
        a = [_norm_tf(x) for x in (ov.get("analysis_tfs") or base.analysis_tfs)]
        t = [_norm_tf(x) for x in (ov.get("trigger_tfs") or base.trigger_tfs)]
        note = str(ov.get("note") or base.note)
        return WorldTF(world=base.world, analysis_tfs=a, trigger_tfs=t, note=note)

    return base


def as_dict(world: str, *, atlas_mode: Optional[str] = None, symbol: Optional[str] = None) -> Dict[str, Any]:
    cfg = get_world_tf(world, atlas_mode=atlas_mode, symbol=symbol)
    return asdict(cfg)