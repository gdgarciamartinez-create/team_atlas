# src/atlas/bot/gatillo_params.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Optional, Tuple, Any
import time
import math


@dataclass
class GatilloParams:
    world: str
    symbol: str
    tf: str
    side: str                  # "BUY" | "SELL"
    zone_low: float
    zone_high: float
    account_usd: float = 10000.0
    risk_pct: float = 1.0      # % (ej: 1.0 = 1%)
    created_ts_ms: int = 0
    updated_ts_ms: int = 0
    note: str = ""


# Key: (symbol, tf)
_STORE: Dict[Tuple[str, str], GatilloParams] = {}


def _now_ms() -> int:
    return int(time.time() * 1000)


def set_params(p: GatilloParams) -> GatilloParams:
    ts = _now_ms()
    if not p.created_ts_ms:
        p.created_ts_ms = ts
    p.updated_ts_ms = ts
    _STORE[(p.symbol, p.tf)] = p
    return p


def clear_params(symbol: str, tf: str) -> None:
    _STORE.pop((symbol, tf), None)


def get_params(symbol: str, tf: str) -> Optional[GatilloParams]:
    return _STORE.get((symbol, tf))


def dump_params(symbol: str, tf: str) -> Optional[dict]:
    p = get_params(symbol, tf)
    return asdict(p) if p else None


def _clamp(x: float, a: float, b: float) -> float:
    return max(a, min(b, x))


def _round_lot(x: float) -> float:
    # redondeo típico a 0.01 (MT5). Ajustalo si tu broker usa diferente.
    return round(x / 0.01) * 0.01


def calc_lot_simple(
    account_usd: float,
    risk_pct: float,
    entry: float,
    sl: float,
    pip_value_per_lot_usd: float = 10.0,
    pip_size: float = 0.1,
) -> float:
    """
    Calculadora UNIVERSAL (simple) para demo:
    - risk_usd = account * risk_pct
    - stop_pips = abs(entry - sl) / pip_size
    - lot = risk_usd / (stop_pips * pip_value_per_lot_usd)

    Para XAU/NAS y símbolos raros esto es aproximado; sirve para simulación pro.
    Si querés exactitud por símbolo, lo refinamos con contract_size/tick_value del broker.
    """
    risk_usd = float(account_usd) * (float(risk_pct) / 100.0)
    dist = abs(float(entry) - float(sl))
    stop_pips = dist / float(pip_size) if pip_size > 0 else 0.0
    stop_pips = max(stop_pips, 0.000001)

    lot = risk_usd / (stop_pips * float(pip_value_per_lot_usd))
    lot = _clamp(lot, 0.01, 50.0)
    return _round_lot(lot)


def apply_gatillo_world(
    snapshot: Dict[str, Any],
    candles: list,
    symbol: str,
    tf: str,
) -> Dict[str, Any]:
    """
    Enchufa al snapshot:
    - action: WAIT | WAIT_GATILLO | SIGNAL
    - ui.rows[0] con plan congelado + parámetros pro
    NO inventa precios si no hay params.
    """
    p = get_params(symbol, tf)

    analysis = snapshot.setdefault("analysis", {})
    ui = snapshot.setdefault("ui", {})
    ui.setdefault("rows", [])

    # default base
    analysis.setdefault("world", "GATILLO")
    analysis.setdefault("source", analysis.get("source", "engine"))
    analysis.setdefault("reason", "—")
    analysis.setdefault("action", "WAIT")
    analysis.setdefault("plan_id", None)
    analysis.setdefault("plan_updated_ts_ms", None)
    analysis.setdefault("frozen", False)

    ui["rows"] = []

    if not p:
        analysis["action"] = "WAIT"
        analysis["reason"] = "Sin parámetros cargados (zona vacía)."
        return snapshot

    # Plan cargado: queda congelado (WAIT_GATILLO) hasta que el bot “active”
    analysis["action"] = "WAIT_GATILLO"
    analysis["reason"] = "Zona armada. Esperando reacción."
    analysis["plan_id"] = f"GATILLO:{p.symbol}:{p.tf}:{p.side}:{p.zone_low:.2f}-{p.zone_high:.2f}"
    analysis["plan_updated_ts_ms"] = p.updated_ts_ms
    analysis["frozen"] = True

    # Si no hay velas, igual mostramos el plan (sin inventar)
    last_price = None
    if candles and isinstance(candles, list):
        try:
            last_price = float(candles[-1].get("c"))
        except Exception:
            last_price = None

    # Trigger demo (provisional): si el precio entra en zona => SIGNAL
    # Luego lo refinás con tus 3 gatillos (ruptura+retest / barrida+recuperación / toque directo).
    in_zone = False
    if last_price is not None:
        in_zone = (p.zone_low <= last_price <= p.zone_high)

    # Para demo: ENTRY = último precio si está en zona, si no, vacío
    entry = last_price if in_zone else None

    # SL/TP demo (provisional, técnico corto):
    # - BUY: SL bajo zone_low, TP arriba zone_high
    # - SELL: SL sobre zone_high, TP bajo zone_low
    sl = None
    tp = None
    if entry is not None:
        if p.side.upper() == "BUY":
            sl = p.zone_low - (abs(p.zone_high - p.zone_low) * 0.25)
            tp = p.zone_high + (abs(p.zone_high - p.zone_low) * 0.75)
        else:
            sl = p.zone_high + (abs(p.zone_high - p.zone_low) * 0.25)
            tp = p.zone_low - (abs(p.zone_high - p.zone_low) * 0.75)

        # señal
        analysis["action"] = "SIGNAL"
        analysis["reason"] = "Precio dentro de zona. Gatillo listo (demo)."

    lot = None
    if entry is not None and sl is not None and math.isfinite(entry) and math.isfinite(sl):
        lot = calc_lot_simple(
            account_usd=p.account_usd,
            risk_pct=p.risk_pct,
            entry=entry,
            sl=sl,
            pip_value_per_lot_usd=10.0,
            pip_size=0.1,
        )

    ui["rows"].append(
        {
            "symbol": p.symbol,
            "tf": p.tf,
            "action": analysis["action"],
            "side": p.side,
            "zone_low": p.zone_low,
            "zone_high": p.zone_high,
            "entry": None if entry is None else round(entry, 2),
            "sl": None if sl is None else round(sl, 2),
            "tp": None if tp is None else round(tp, 2),
            "account_usd": p.account_usd,
            "risk_pct": p.risk_pct,
            "lot": lot,
            "text": "Zona cargada. Esperando gatillo. (Demo: señal al entrar en zona)",
            "why": analysis["reason"],
            "plan_id": analysis["plan_id"],
        }
    )

    return snapshot
