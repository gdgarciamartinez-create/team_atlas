from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from atlas.bot.bitacora.store import get_open_trade, open_trade, close_trade


def _float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _get_last_closes(candles: List[Dict[str, Any]], n: int = 2) -> List[float]:
    if not candles:
        return []
    tail = candles[-n:]
    closes: List[float] = []
    for c in tail:
        v = _float(c.get("c"))
        if v is None:
            return []
        closes.append(v)
    return closes


def _confirm_double(side: str, tp: float, sl: float, closes2: List[float]) -> Optional[Tuple[str, float]]:
    if len(closes2) < 2:
        return None

    c1, c2 = closes2[-2], closes2[-1]
    side = side.upper()

    if side == "BUY":
        if c1 >= tp and c2 >= tp:
            return ("TP", c2)
        if c1 <= sl and c2 <= sl:
            return ("SL", c2)
    else:
        if c1 <= tp and c2 <= tp:
            return ("TP", c2)
        if c1 >= sl and c2 >= sl:
            return ("SL", c2)

    return None


def process_snapshot_for_bitacora(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    1) Si state in (GATILLO, SIGNAL) y trae entry/sl/tp -> abre trade (si no hay uno open).
    2) Si hay trade open -> revisa 2 cierres consecutivos para TP/SL y cierra.
    """
    world = (snapshot.get("world") or "").upper()
    symbol = snapshot.get("symbol") or ""
    tf = snapshot.get("tf") or ""

    state = (snapshot.get("state") or "").upper()
    side = (snapshot.get("side") or "").upper()

    entry = _float(snapshot.get("entry"))
    sl = _float(snapshot.get("sl"))
    tp = _float(snapshot.get("tp"))

    candles = snapshot.get("candles") or []
    closes2 = _get_last_closes(candles, n=2)

    # === A) abrir trade ===
    if (
        state in ("GATILLO", "SIGNAL")
        and all(v is not None and v > 0 for v in [entry, sl, tp])
        and side in ("BUY", "SELL")
    ):
        open_trade(
            world=world,
            symbol=str(symbol),
            tf=str(tf),
            side=side,
            entry=float(entry),
            sl=float(sl),
            tp=float(tp),
            note=f"auto-open ({state})",
            source="atlas",
        )

    # === B) cerrar trade si hay open ===
    open_row = get_open_trade(world, str(symbol), str(tf))
    if not open_row:
        return snapshot

    t_side = (open_row.get("side") or "").upper()
    t_tp = _float(open_row.get("tp"))
    t_sl = _float(open_row.get("sl"))
    t_trade_id = open_row.get("trade_id")

    if not t_trade_id or t_tp is None or t_sl is None:
        return snapshot

    decision = _confirm_double(t_side, float(t_tp), float(t_sl), closes2)
    if decision:
        reason, exit_price = decision
        close_trade(
            trade_id=t_trade_id,
            exit_price=float(exit_price),
            reason=reason,
            note="auto-close (double-confirm closes)",
        )

    return snapshot