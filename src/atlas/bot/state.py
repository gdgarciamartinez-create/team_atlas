# src/atlas/bot/state.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Tuple, Optional
import time


# ============================================================
# Constantes de fase (compatibilidad snapshot_core)
# ============================================================
PHASE_WAIT = "WAIT"
PHASE_ZONA = "ZONA"
PHASE_WAIT_GATILLO = "WAIT_GATILLO"
PHASE_GATILLO = "GATILLO"
PHASE_SIGNAL = "SIGNAL"
PHASE_TRADE = "TRADE"
PHASE_NO_TRADE = "NO_TRADE"
PHASE_INVALID = "INVALID"

PHASE_IDLE = PHASE_WAIT
PHASE_PLAN = PHASE_ZONA


def now_ms() -> int:
    return int(time.time() * 1000)


# ============================================================
# Modelos (state con atributos)
# ============================================================
@dataclass
class Plan:
    bias: Optional[str] = None          # "BUY"/"SELL"
    note: str = ""
    zone_low: Optional[float] = None
    zone_high: Optional[float] = None

    # Se congelan en WAIT_GATILLO
    frozen: bool = False

    # Niveles finales (solo cuando pasa a SIGNAL)
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None


@dataclass
class Signal:
    # 👇 snapshot_core espera esto
    signal_id: Optional[str] = None

    side: Optional[str] = None          # "BUY"/"SELL"
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    note: str = ""
    ts_ms: int = field(default_factory=now_ms)


@dataclass
class Trade:
    # V1 no ejecuta, pero guardamos la info
    side: Optional[str] = None
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    status: str = "NONE"               # NONE|OPEN|CLOSED
    ts_open_ms: Optional[int] = None
    ts_close_ms: Optional[int] = None
    result: Optional[str] = None       # WIN|LOSS|BE
    pnl_pts: Optional[float] = None


@dataclass
class WorldState:
    world: str = "ATLAS_IA"
    atlas_mode: str = "SCALPING_M5"
    symbol: str = "XAUUSDz"
    tf: str = "M5"

    phase: str = PHASE_WAIT
    updated_at_ms: int = field(default_factory=now_ms)

    plan: Plan = field(default_factory=Plan)
    signal: Signal = field(default_factory=Signal)
    trade: Trade = field(default_factory=Trade)

    # Extras para compatibilidad y datos sueltos
    extras: Dict[str, Any] = field(default_factory=dict)

    # --- Compat: comportamiento tipo dict ---
    def __getitem__(self, k: str) -> Any:
        if hasattr(self, k):
            return getattr(self, k)
        return self.extras.get(k)

    def __setitem__(self, k: str, v: Any) -> None:
        if hasattr(self, k):
            setattr(self, k, v)
        else:
            self.extras[k] = v
        self.updated_at_ms = now_ms()

    def get(self, k: str, default: Any = None) -> Any:
        v = None
        if hasattr(self, k):
            v = getattr(self, k)
        else:
            v = self.extras.get(k)
        return default if v is None else v

    def update(self, patch: Dict[str, Any]) -> None:
        for k, v in (patch or {}).items():
            self.__setitem__(k, v)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k, v in self.extras.items():
            if k not in d:
                d[k] = v
        return d


# ============================================================
# Estado global (fallback)
# ============================================================
BOT_STATE: Dict[str, Any] = {
    "world": "ATLAS_IA",
    "atlas_mode": "SCALPING_M5",
    "symbol": "XAUUSDz",
    "tf": "M5",
    "armed": False,   # V1 = NO ejecuta
    "running": True,
    "phase": PHASE_WAIT,
    "updated_at_ms": now_ms(),
}

_WORLD_STATE: Dict[Tuple[str, str, str, str], WorldState] = {}


# ============================================================
# Normalización
# ============================================================
def _norm(s: Optional[str], default: str) -> str:
    x = (s or "").strip()
    return x if x else default


def _key(world: Optional[str], atlas_mode: Optional[str], symbol: Optional[str], tf: Optional[str]) -> Tuple[str, str, str, str]:
    return (
        _norm(world, BOT_STATE.get("world", "ATLAS_IA")),
        _norm(atlas_mode, BOT_STATE.get("atlas_mode", "SCALPING_M5")),
        _norm(symbol, BOT_STATE.get("symbol", "XAUUSDz")),
        _norm(tf, BOT_STATE.get("tf", "M5")),
    )


# ============================================================
# API COMPATIBLE con snapshot_core.py
# ============================================================
def get_world_state(
    world: Optional[str] = None,
    atlas_mode: Optional[str] = None,
    symbol: Optional[str] = None,
    tf: Optional[str] = None,
) -> WorldState:
    k = _key(world, atlas_mode, symbol, tf)
    if k not in _WORLD_STATE:
        _WORLD_STATE[k] = WorldState(
            world=k[0],
            atlas_mode=k[1],
            symbol=k[2],
            tf=k[3],
            phase=PHASE_WAIT,
        )
    return _WORLD_STATE[k]


def set_world_state(
    world: Optional[str] = None,
    atlas_mode: Optional[str] = None,
    symbol: Optional[str] = None,
    tf: Optional[str] = None,
    patch: Optional[Dict[str, Any]] = None,
) -> WorldState:
    st = get_world_state(world=world, atlas_mode=atlas_mode, symbol=symbol, tf=tf)
    if patch:
        st.update(patch)
    st.updated_at_ms = now_ms()
    return st


def clear_world_state(
    world: Optional[str] = None,
    atlas_mode: Optional[str] = None,
    symbol: Optional[str] = None,
    tf: Optional[str] = None,
) -> None:
    k = _key(world, atlas_mode, symbol, tf)
    _WORLD_STATE.pop(k, None)


# ============================================================
# Bot state helpers
# ============================================================
def get_bot_state() -> Dict[str, Any]:
    return BOT_STATE


def patch_bot_state(patch: Dict[str, Any]) -> Dict[str, Any]:
    if patch:
        BOT_STATE.update(patch)
    BOT_STATE["updated_at_ms"] = now_ms()
    return BOT_STATE