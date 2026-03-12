from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional


VALID_LIVE_STATES = {"SET_UP", "ENTRY", "IN_TRADE", "TP1", "TP2", "RUN"}


class TradeManager:
    """
    Gestor de vida del trade para ATLAS.

    Ciclo:

    SET_UP
        ↓
    ENTRY   ← aquí comienza la bitácora
        ↓
    IN_TRADE
        ↓
    TP1
        ↓
    TP2 / RUN
        ↓
    CLOSED
    """

    def __init__(self) -> None:
        pass

    # --------------------------------------------------

    def _safe_float(self, v: Any) -> Optional[float]:
        try:
            return float(v)
        except Exception:
            return None

    def _merge(self, row: Dict[str, Any], patch: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        merged = deepcopy(row)
        if isinstance(patch, dict):
            merged.update(patch)
        return merged

    def _last(self, row, key):
        candles = row.get("candles")
        if isinstance(candles, list) and candles:
            return candles[-1].get(key)
        return None

    def _high(self, row):
        return self._safe_float(self._last(row, "h"))

    def _low(self, row):
        return self._safe_float(self._last(row, "l"))

    def _close(self, row):
        return self._safe_float(self._last(row, "c"))

    # --------------------------------------------------

    def _entry_touched(self, row, entry):

        entry = self._safe_float(entry)
        low = self._low(row)
        high = self._high(row)

        if None in (entry, low, high):
            return False

        return low <= entry <= high

    def _sl_hit(self, row, side, sl):

        sl = self._safe_float(sl)

        high = self._high(row)
        low = self._low(row)

        if None in (sl, high, low):
            return False

        if side == "BUY":
            return low <= sl

        if side == "SELL":
            return high >= sl

        return False

    def _tp_hit(self, row, side, tp):

        tp = self._safe_float(tp)

        high = self._high(row)
        low = self._low(row)

        if None in (tp, high, low):
            return False

        if side == "BUY":
            return high >= tp

        if side == "SELL":
            return low <= tp

        return False

    # --------------------------------------------------

    def step_row(self, runtime, row: Dict[str, Any]) -> Dict[str, Any]:

        if not isinstance(row, dict):
            return row

        symbol = row.get("symbol")
        tf = row.get("tf")

        if not symbol or not tf:
            return row

        plan = runtime.get_active_plan(symbol, tf)

        if not plan:
            return row

        state = str(plan.get("state")).upper()

        merged = self._merge(row, plan)

        # --------------------------------------------------
        # SETUP → ENTRY
        # --------------------------------------------------

        if state == "SET_UP":

            if self._entry_touched(row, plan.get("entry")):

                patch = runtime.promote_setup_to_entry(symbol, tf, row)

                merged = self._merge(merged, patch)

                runtime.log_op_event(
                    "ENTRY",
                    {
                        "symbol": symbol,
                        "tf": tf,
                        "side": merged.get("side"),
                        "entry": merged.get("entry"),
                        "sl": merged.get("sl"),
                        "tp": merged.get("tp"),
                        "score": merged.get("score"),
                    },
                )

                return merged

        # --------------------------------------------------
        # ENTRY → IN_TRADE
        # --------------------------------------------------

        if state == "ENTRY":

            patch = runtime.promote_entry_to_in_trade(symbol, tf, row)

            merged = self._merge(merged, patch)

            runtime.log_op_event("IN_TRADE", merged)

            return merged

        # --------------------------------------------------
        # SL
        # --------------------------------------------------

        if state in {"ENTRY", "IN_TRADE", "TP1"}:

            if self._sl_hit(row, plan.get("side"), plan.get("sl")):

                sl = self._safe_float(plan.get("sl"))

                patch = runtime._close_plan(symbol, tf, "SL", sl)

                merged = self._merge(merged, patch)

                runtime.log_op_event("SL", merged)

                return merged

        # --------------------------------------------------
        # TP1
        # --------------------------------------------------

        if state in {"ENTRY", "IN_TRADE"}:

            if self._tp_hit(row, plan.get("side"), plan.get("tp1")):

                patch = runtime.promote_in_trade_to_tp1(symbol, tf)

                merged = self._merge(merged, patch)

                runtime.log_op_event("TP1", merged)

                return merged

        # --------------------------------------------------
        # TP2
        # --------------------------------------------------

        if state == "TP1":

            if self._tp_hit(row, plan.get("side"), plan.get("tp2")):

                patch = runtime.promote_tp1_to_tp2(symbol, tf)

                merged = self._merge(merged, patch)

                runtime.log_op_event("TP2", merged)

                return merged

        return merged

    # --------------------------------------------------

    def step_rows(self, runtime, rows):

        out = []

        for row in rows:

            out.append(self.step_row(runtime, row))

        return out


trade_manager = TradeManager()
TRADE_MANAGER = trade_manager