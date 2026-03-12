from __future__ import annotations

from atlas.metrics.bitacora_store import BITACORA
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional
import csv
import math

CSV_PATH = Path("atlas_trades.csv")
DAILY_CSV_PATH = Path("atlas_daily_log.csv")

VALID_STATES = {
    "SIN_SETUP",
    "SET_UP",
    "ENTRY",
    "IN_TRADE",
    "TP1",
    "TP2",
    "RUN",
    "CLOSED",
}


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass
class FrozenPlan:
    symbol: str
    tf: str
    state: str = "SIN_SETUP"

    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    parcial: Optional[float] = None

    lot: Optional[float] = None
    risk_percent: Optional[float] = None
    score: Optional[float] = None

    side: Optional[str] = None
    note: Optional[str] = None

    signal_ts: Optional[str] = None
    signal_candle_time: Optional[str] = None

    entry_ts: Optional[str] = None
    entry_candle_time: Optional[str] = None

    tp1_ts: Optional[str] = None
    tp2_ts: Optional[str] = None
    run_ts: Optional[str] = None

    closed_ts: Optional[str] = None
    close_reason: Optional[str] = None
    close_price: Optional[float] = None

    updated_at: Optional[str] = None

    extra: Dict[str, Any] = field(default_factory=dict)

    def to_row_patch(self) -> Dict[str, Any]:
        patch: Dict[str, Any] = {
            "state": self.state,
            "entry": self.entry,
            "sl": self.sl,
            "tp": self.tp,
            "parcial": self.parcial,
            "lot": self.lot,
            "risk_percent": self.risk_percent,
            "score": self.score,
            "side": self.side,
            "note": self.note,
            "signal_ts": self.signal_ts,
            "signal_candle_time": self.signal_candle_time,
            "entry_ts": self.entry_ts,
            "entry_candle_time": self.entry_candle_time,
            "tp1_ts": self.tp1_ts,
            "tp2_ts": self.tp2_ts,
            "run_ts": self.run_ts,
            "closed_ts": self.closed_ts,
            "close_reason": self.close_reason,
            "close_price": self.close_price,
            "updated_at": self.updated_at,
        }
        if self.extra:
            patch.update(deepcopy(self.extra))
        return patch


class AtlasRuntime:
    def __init__(self) -> None:
        self._lock = Lock()

        self.engine_running: bool = True
        self.feed_running: bool = True

        self._plans: Dict[str, FrozenPlan] = {}
        self._closed_trades: List[Dict[str, Any]] = []
        self._ops_log: List[Dict[str, Any]] = []
        self._partials_log: List[Dict[str, Any]] = []

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def _key(self, symbol: str, tf: str) -> str:
        return f"{symbol}|{tf}"

    def _safe_float(self, v: Any) -> Optional[float]:
        try:
            return float(v)
        except Exception:
            return None

    def _extract_last_candle(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        candles = row.get("candles")
        if isinstance(candles, list) and candles:
            last = candles[-1]
            if isinstance(last, dict):
                return last
        return None

    def _last_candle_time(self, row: Dict[str, Any]) -> Optional[str]:
        last_candle = self._extract_last_candle(row)
        if not last_candle:
            return None
        t = last_candle.get("t", last_candle.get("time"))
        return str(t) if t is not None else None

    def _candle_touches_entry(self, row: Dict[str, Any], entry: Optional[float]) -> bool:
        entry_f = self._safe_float(entry)
        if entry_f is None:
            return False

        last_candle = self._extract_last_candle(row)
        if not last_candle:
            return False

        low = self._safe_float(last_candle.get("l", last_candle.get("low")))
        high = self._safe_float(last_candle.get("h", last_candle.get("high")))

        if low is None or high is None:
            return False

        return low <= entry_f <= high

    def _candle_hits_tp(self, row: Dict[str, Any], side: Optional[str], tp: Optional[float]) -> bool:
        tp_f = self._safe_float(tp)
        if tp_f is None:
            return False

        last_candle = self._extract_last_candle(row)
        if not last_candle:
            return False

        high = self._safe_float(last_candle.get("h", last_candle.get("high")))
        low = self._safe_float(last_candle.get("l", last_candle.get("low")))
        if high is None or low is None:
            return False

        s = str(side or "").upper()
        if s == "BUY":
            return high >= tp_f
        if s == "SELL":
            return low <= tp_f
        return False

    def _candle_hits_sl(self, row: Dict[str, Any], side: Optional[str], sl: Optional[float]) -> bool:
        sl_f = self._safe_float(sl)
        if sl_f is None:
            return False

        last_candle = self._extract_last_candle(row)
        if not last_candle:
            return False

        high = self._safe_float(last_candle.get("h", last_candle.get("high")))
        low = self._safe_float(last_candle.get("l", last_candle.get("low")))
        if high is None or low is None:
            return False

        s = str(side or "").upper()
        if s == "BUY":
            return low <= sl_f
        if s == "SELL":
            return high >= sl_f
        return False

    def _risk_distance(self, plan: FrozenPlan) -> Optional[float]:
        entry = self._safe_float(plan.entry)
        sl = self._safe_float(plan.sl)
        if entry is None or sl is None:
            return None
        dist = abs(entry - sl)
        return dist if dist > 0 else None

    def _last_close(self, row: Dict[str, Any]) -> Optional[float]:
        last_candle = self._extract_last_candle(row)
        if not last_candle:
            return None
        return self._safe_float(last_candle.get("c", last_candle.get("close")))

    def _favorable_distance(self, plan: FrozenPlan, last_close: Optional[float]) -> Optional[float]:
        if last_close is None:
            return None

        entry = self._safe_float(plan.entry)
        if entry is None:
            return None

        side = str(plan.side or "").upper()
        if side == "BUY":
            return last_close - entry
        if side == "SELL":
            return entry - last_close
        return None

    def _hit_1r(self, plan: FrozenPlan, row: Dict[str, Any]) -> bool:
        risk = self._risk_distance(plan)
        last_close = self._last_close(row)
        fav = self._favorable_distance(plan, last_close)

        if risk is None or fav is None:
            return False

        return fav >= risk

    def _row_wants_run(self, row: Dict[str, Any]) -> bool:
        if bool(row.get("run")):
            return True
        if bool(row.get("allow_run")):
            return True
        if bool(row.get("run_candidate")):
            return True

        note = str(row.get("note") or "").lower()
        return any(k in note for k in ["run", "continuidad", "displacement"])

    def _be_positive_price(self, plan: FrozenPlan) -> Optional[float]:
        entry = self._safe_float(plan.entry)
        risk = self._risk_distance(plan)
        side = str(plan.side or "").upper()

        if entry is None:
            return None

        if risk is None:
            return entry

        offset = risk * 0.10

        if side == "BUY":
            return entry + offset
        if side == "SELL":
            return entry - offset
        return entry

    def _event_payload(
        self,
        *,
        symbol: str,
        tf: str,
        state: Optional[str] = None,
        side: Optional[str] = None,
        entry: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        price: Optional[float] = None,
        score: Optional[float] = None,
        note: Optional[str] = None,
        result: Optional[str] = None,
        parcial: Optional[float] = None,
        usd: Optional[float] = None,
        pips: Optional[float] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "symbol": symbol,
            "tf": tf,
        }

        if state is not None:
            payload["state"] = state
        if side is not None:
            payload["side"] = side
        if entry is not None:
            payload["entry"] = entry
        if sl is not None:
            payload["sl"] = sl
        if tp is not None:
            payload["tp"] = tp
        if price is not None:
            payload["price"] = price
        if score is not None:
            payload["score"] = score
        if note is not None:
            payload["note"] = note
        if result is not None:
            payload["result"] = result
        if parcial is not None:
            payload["parcial"] = parcial
        if usd is not None:
            payload["usd"] = usd
        if pips is not None:
            payload["pips"] = pips

        return payload

    def _log_state_event(
        self,
        event: str,
        *,
        symbol: str,
        tf: str,
        state: Optional[str] = None,
        side: Optional[str] = None,
        entry: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        price: Optional[float] = None,
        score: Optional[float] = None,
        note: Optional[str] = None,
        result: Optional[str] = None,
        parcial: Optional[float] = None,
        usd: Optional[float] = None,
        pips: Optional[float] = None,
    ) -> None:
        self.log_op(
            event,
            self._event_payload(
                symbol=symbol,
                tf=tf,
                state=state,
                side=side,
                entry=entry,
                sl=sl,
                tp=tp,
                price=price,
                score=score,
                note=note,
                result=result,
                parcial=parcial,
                usd=usd,
                pips=pips,
            ),
        )

    def _close_event_name(self, result: str) -> str:
        r = str(result or "").upper().strip()

        if r == "SL":
            return "SL"
        if r == "RUN_CLOSE":
            return "RUN_CLOSE"
        if r == "TP2":
            return "TP2"
        if r == "TP":
            return "TP2"
        if r == "BE":
            return "BE"
        if r == "TP1_CLOSE":
            return "TP1_CLOSE"

        return r or "TRADE_CLOSE"

    def _calc_pips(self, symbol: str, entry: float, exit_price: float, side: str) -> float:
        spec = self._symbol_spec_from_row({}, symbol)
        tick_size = spec["trade_tick_size"]
        if tick_size <= 0:
            return 0.0

        if side == "BUY":
            return (exit_price - entry) / tick_size
        return (entry - exit_price) / tick_size

    def _build_trade_row(
        self,
        *,
        ts: str,
        symbol: str,
        tf: str,
        side: str,
        entry: float,
        sl: float,
        tp: float,
        exit_price: float,
        result: str,
    ) -> Dict[str, Any]:
        pips = self._calc_pips(symbol, entry, exit_price, side)
        usd = round(pips * 1.0, 2)

        return {
            "ts": ts,
            "symbol": symbol,
            "tf": tf,
            "side": side,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "exit": exit_price,
            "result": result,
            "pips": round(pips, 2),
            "usd": usd,
        }

    def _save_csv(self, row: Dict[str, Any]) -> None:
        exists = CSV_PATH.exists()

        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "ts",
                    "symbol",
                    "tf",
                    "side",
                    "entry",
                    "sl",
                    "tp",
                    "exit",
                    "result",
                    "pips",
                    "usd",
                ],
            )

            if not exists:
                writer.writeheader()

            writer.writerow(row)

    def _save_daily_csv(self, row: Dict[str, Any]) -> None:
        exists = DAILY_CSV_PATH.exists()

        ts = str(row.get("ts") or "")
        date_part = ""
        time_part = ""
        if "T" in ts:
            base = ts.replace("Z", "")
            parts = base.split("T", 1)
            date_part = parts[0]
            time_part = parts[1] if len(parts) > 1 else ""
        else:
            date_part = ts

        daily_row = {
            "date": date_part,
            "time": time_part,
            "symbol": row.get("symbol"),
            "tf": row.get("tf"),
            "side": row.get("side"),
            "entry": row.get("entry"),
            "sl": row.get("sl"),
            "tp": row.get("tp"),
            "exit": row.get("exit"),
            "result": row.get("result"),
            "pips": row.get("pips"),
            "usd": row.get("usd"),
        }

        with open(DAILY_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "date",
                    "time",
                    "symbol",
                    "tf",
                    "side",
                    "entry",
                    "sl",
                    "tp",
                    "exit",
                    "result",
                    "pips",
                    "usd",
                ],
            )

            if not exists:
                writer.writeheader()

            writer.writerow(daily_row)

    def _register_partial_tp1(self, plan: FrozenPlan) -> Optional[Dict[str, Any]]:
        if not plan:
            return None

        if bool(plan.extra.get("tp1_logged")):
            return None

        entry = self._safe_float(plan.entry)
        parcial = self._safe_float(plan.parcial)
        sl = self._safe_float(plan.sl)
        tp = self._safe_float(plan.tp)
        side = str(plan.side or "").upper()

        if entry is None or parcial is None or side not in {"BUY", "SELL"}:
            return None

        trade = self._build_trade_row(
            ts=_now(),
            symbol=plan.symbol,
            tf=plan.tf,
            side=side,
            entry=entry,
            sl=sl or 0.0,
            tp=tp or parcial,
            exit_price=parcial,
            result="TP1",
        )

        with self._lock:
            self._partials_log.append(trade)
            if len(self._partials_log) > 5000:
                self._partials_log = self._partials_log[-2000:]

            live_plan = self._plans.get(self._key(plan.symbol, plan.tf))
            if live_plan:
                live_plan.extra["tp1_logged"] = True

        try:
            self._save_csv(trade)
        except Exception:
            pass

        try:
            self._save_daily_csv(trade)
        except Exception:
            pass

        try:
            log_closed = getattr(BITACORA, "log_closed", None)
            if callable(log_closed):
                log_closed(trade)
        except Exception:
            pass

        self._log_state_event(
            "TP1",
            symbol=trade["symbol"],
            tf=trade["tf"],
            state="TP1",
            side=trade["side"],
            entry=trade["entry"],
            sl=trade["sl"],
            tp=trade["tp"],
            price=trade["exit"],
            result="TP1",
            parcial=trade["exit"],
            usd=trade["usd"],
            pips=trade["pips"],
        )

        return trade

    # --------------------------------------------------
    # Risk and lot
    # --------------------------------------------------

    def _risk_pct_from_score(self, score: float | None) -> Optional[float]:
        if score is None:
            return None

        try:
            s = float(score)
        except Exception:
            return None

        if s >= 11:
            return 1.5
        if s >= 9:
            return 1.0
        if s >= 7:
            return 0.5
        return None

    def _assumed_balance(self, row: Dict[str, Any]) -> float:
        balance = self._safe_float(row.get("balance"))
        if balance is not None and balance > 0:
            return balance

        equity = self._safe_float(row.get("equity"))
        if equity is not None and equity > 0:
            return equity

        return 10000.0

    def _symbol_spec_from_row(self, row: Dict[str, Any], symbol: str) -> Dict[str, float]:
        trade_tick_value = self._safe_float(row.get("trade_tick_value"))
        trade_tick_size = self._safe_float(row.get("trade_tick_size"))
        volume_min = self._safe_float(row.get("volume_min"))
        volume_max = self._safe_float(row.get("volume_max"))
        volume_step = self._safe_float(row.get("volume_step"))

        if trade_tick_size is None or trade_tick_size <= 0:
            if symbol.startswith("XAU"):
                trade_tick_size = 0.01
            elif symbol.startswith("USTEC"):
                trade_tick_size = 1.0
            elif symbol.startswith("USOIL"):
                trade_tick_size = 0.01
            elif "JPY" in symbol:
                trade_tick_size = 0.001
            else:
                trade_tick_size = 0.00001

        if trade_tick_value is None or trade_tick_value <= 0:
            trade_tick_value = 1.0

        if volume_min is None or volume_min <= 0:
            volume_min = 0.01

        if volume_step is None or volume_step <= 0:
            volume_step = 0.01

        if volume_max is None or volume_max <= 0:
            volume_max = 100.0

        return {
            "trade_tick_value": trade_tick_value,
            "trade_tick_size": trade_tick_size,
            "volume_min": volume_min,
            "volume_max": volume_max,
            "volume_step": volume_step,
        }

    def _round_volume_to_step(self, volume: float, volume_min: float, volume_max: float, volume_step: float) -> float:
        if volume <= 0:
            return volume_min

        steps = math.floor(volume / volume_step)
        rounded = steps * volume_step

        if rounded < volume_min:
            rounded = volume_min
        if rounded > volume_max:
            rounded = volume_max

        step_str = f"{volume_step:.10f}".rstrip("0")
        if "." in step_str:
            decimals = len(step_str.split(".")[1])
        else:
            decimals = 0

        return round(rounded, decimals)

    def _calc_real_lot(
        self,
        symbol: str,
        entry: Optional[float],
        sl: Optional[float],
        score: Optional[float],
        row: Dict[str, Any],
    ) -> Optional[float]:
        entry_f = self._safe_float(entry)
        sl_f = self._safe_float(sl)
        risk_pct = self._risk_pct_from_score(score)

        if entry_f is None or sl_f is None or risk_pct is None:
            return None

        stop_distance = abs(entry_f - sl_f)
        if stop_distance <= 0:
            return None

        spec = self._symbol_spec_from_row(row, symbol)
        trade_tick_value = spec["trade_tick_value"]
        trade_tick_size = spec["trade_tick_size"]
        volume_min = spec["volume_min"]
        volume_max = spec["volume_max"]
        volume_step = spec["volume_step"]

        if trade_tick_size <= 0 or trade_tick_value <= 0:
            return None

        balance = self._assumed_balance(row)
        risk_money = balance * (risk_pct / 100.0)

        loss_per_1_lot = (stop_distance / trade_tick_size) * trade_tick_value
        if loss_per_1_lot <= 0:
            return None

        raw_lot = risk_money / loss_per_1_lot

        return self._round_volume_to_step(
            volume=raw_lot,
            volume_min=volume_min,
            volume_max=volume_max,
            volume_step=volume_step,
        )

    # --------------------------------------------------
    # Control / public state
    # --------------------------------------------------

    def get_control_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "engine_running": self.engine_running,
                "feed_running": self.feed_running,
                "frozen_plans": len(self._plans),
            }

    def set_engine_running(self, value: bool) -> Dict[str, Any]:
        with self._lock:
            self.engine_running = bool(value)
        return self.get_control_state()

    def set_feed_running(self, value: bool) -> Dict[str, Any]:
        with self._lock:
            self.feed_running = bool(value)
        return self.get_control_state()

    def reset_feed(self) -> Dict[str, Any]:
        return self.get_control_state()

    def log_op_event(self, event: str, data: Any) -> None:
        try:
            BITACORA.log_op(event, data)
        except Exception:
            pass

    def log_op(self, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
        item = {
            "ts": _now(),
            "event": event,
            "payload": payload or {},
        }

        with self._lock:
            self._ops_log.append(item)
            if len(self._ops_log) > 5000:
                self._ops_log = self._ops_log[-2000:]

        self.log_op_event(event, item)

    def get_ops_log(self, limit: int = 200) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 2000))

        try:
            ops = BITACORA.get_ops(limit)
            if isinstance(ops, list):
                return ops
        except Exception:
            pass

        with self._lock:
            return deepcopy(self._ops_log[-limit:])

    def get_active_plan(self, symbol: str, tf: str | None = None) -> Optional[Dict[str, Any]]:
        with self._lock:
            if tf is not None:
                plan = self._plans.get(self._key(symbol, tf))
                return deepcopy(plan.to_row_patch()) if plan else None

            matches = [p for p in self._plans.values() if p.symbol == symbol]
            if not matches:
                return None

            matches.sort(key=lambda p: (p.updated_at or "", p.tf))
            return deepcopy(matches[-1].to_row_patch())

    # --------------------------------------------------
    # Freeze from scanner
    # --------------------------------------------------

    def freeze_plan(self, row: Dict[str, Any]) -> Dict[str, Any]:
        symbol = row.get("symbol")
        tf = row.get("tf")

        if not symbol or not tf:
            return row

        state = str(row.get("state") or "").upper().strip()
        if state not in {"SET_UP", "ENTRY"}:
            return row

        created_plan: Optional[FrozenPlan] = None

        with self._lock:
            key = self._key(symbol, tf)
            existing = self._plans.get(key)

            if existing and existing.state in {"SET_UP", "ENTRY", "IN_TRADE", "TP1", "TP2", "RUN"}:
                patch = existing.to_row_patch()
            else:
                lot = self._calc_real_lot(
                    symbol=symbol,
                    entry=row.get("entry"),
                    sl=row.get("sl"),
                    score=row.get("score"),
                    row=row,
                )
                risk_percent = self._risk_pct_from_score(row.get("score"))

                plan = FrozenPlan(
                    symbol=symbol,
                    tf=tf,
                    state=state,
                    entry=row.get("entry"),
                    sl=row.get("sl"),
                    tp=row.get("tp"),
                    parcial=row.get("parcial"),
                    lot=lot,
                    risk_percent=risk_percent,
                    score=row.get("score"),
                    side=row.get("side"),
                    note=row.get("note") or row.get("text"),
                    signal_ts=_now(),
                    signal_candle_time=self._last_candle_time(row),
                    updated_at=_now(),
                    extra={
                        "zone_low": row.get("zone_low"),
                        "zone_high": row.get("zone_high"),
                        "sweep_valid": row.get("sweep_valid"),
                        "sweep_strength": row.get("sweep_strength"),
                        "tp1_logged": False,
                    },
                )
                self._plans[key] = plan
                patch = plan.to_row_patch()
                created_plan = plan

        if created_plan:
            self._log_state_event(
                "SET_UP" if created_plan.state == "SET_UP" else "ENTRY",
                symbol=created_plan.symbol,
                tf=created_plan.tf,
                state=created_plan.state,
                side=created_plan.side,
                entry=created_plan.entry,
                sl=created_plan.sl,
                tp=created_plan.tp,
                score=created_plan.score,
                note=created_plan.note,
            )

        merged = deepcopy(row)
        merged.update(patch)
        return merged

    # --------------------------------------------------
    # State creation / update
    # --------------------------------------------------

    def freeze_sin_setup(self, symbol: str, tf: str, row: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            key = self._key(symbol, tf)
            existing = self._plans.get(key)

            if existing and existing.state in {"SET_UP", "ENTRY", "IN_TRADE", "TP1", "TP2", "RUN"}:
                return existing.to_row_patch()

            if key in self._plans:
                del self._plans[key]

            patch = {
                "state": "SIN_SETUP",
                "entry": None,
                "sl": None,
                "tp": None,
                "parcial": None,
                "lot": None,
                "risk_percent": None,
                "signal_ts": None,
                "signal_candle_time": None,
                "entry_ts": None,
                "entry_candle_time": None,
                "tp1_ts": None,
                "tp2_ts": None,
                "run_ts": None,
                "closed_ts": None,
                "close_reason": None,
                "close_price": None,
                "updated_at": _now(),
            }

            if row:
                if row.get("score") is not None:
                    patch["score"] = row.get("score")
                if row.get("side") is not None:
                    patch["side"] = row.get("side")
                if row.get("note") is not None:
                    patch["note"] = row.get("note")

            return patch

    def promote_setup_to_entry(self, symbol: str, tf: str, row: Dict[str, Any]) -> Dict[str, Any]:
        promoted_plan: Optional[FrozenPlan] = None

        with self._lock:
            plan = self._plans.get(self._key(symbol, tf))
            if not plan:
                return row

            if plan.state not in {"SET_UP", "ENTRY"}:
                return plan.to_row_patch()

            if plan.state == "SET_UP":
                plan.state = "ENTRY"
                plan.entry_ts = _now()
                plan.entry_candle_time = self._last_candle_time(row)
                plan.updated_at = _now()
                promoted_plan = deepcopy(plan)

            patch = plan.to_row_patch()

        if promoted_plan:
            self._log_state_event(
                "ENTRY",
                symbol=promoted_plan.symbol,
                tf=promoted_plan.tf,
                state=promoted_plan.state,
                side=promoted_plan.side,
                entry=promoted_plan.entry,
                sl=promoted_plan.sl,
                tp=promoted_plan.tp,
                score=promoted_plan.score,
                note=promoted_plan.note,
            )

        return patch

    def promote_entry_to_in_trade(self, symbol: str, tf: str, row: Dict[str, Any]) -> Dict[str, Any]:
        promoted_plan: Optional[FrozenPlan] = None

        with self._lock:
            plan = self._plans.get(self._key(symbol, tf))
            if not plan:
                return row

            if plan.state != "ENTRY":
                return plan.to_row_patch()

            last_ct = self._last_candle_time(row)
            if last_ct and plan.entry_candle_time and str(last_ct) != str(plan.entry_candle_time):
                plan.state = "IN_TRADE"
                plan.updated_at = _now()
                promoted_plan = deepcopy(plan)

            patch = plan.to_row_patch()

        if promoted_plan:
            self._log_state_event(
                "IN_TRADE",
                symbol=promoted_plan.symbol,
                tf=promoted_plan.tf,
                state=promoted_plan.state,
                side=promoted_plan.side,
                entry=promoted_plan.entry,
                sl=promoted_plan.sl,
                tp=promoted_plan.tp,
                score=promoted_plan.score,
                note=promoted_plan.note,
            )

        return patch

    def promote_in_trade_to_tp1(self, symbol: str, tf: str) -> Dict[str, Any]:
        promoted_plan: Optional[FrozenPlan] = None

        with self._lock:
            plan = self._plans.get(self._key(symbol, tf))
            if not plan:
                return {}

            if plan.state not in {"IN_TRADE", "ENTRY"}:
                return plan.to_row_patch()

            plan.state = "TP1"
            plan.tp1_ts = _now()
            plan.updated_at = _now()

            original_sl = plan.sl
            be_price = self._be_positive_price(plan)
            if be_price is not None:
                plan.sl = be_price
            if original_sl is not None:
                plan.extra["sl_before_tp1"] = original_sl

            promoted_plan = deepcopy(plan)
            patch = plan.to_row_patch()

        if promoted_plan:
            self._register_partial_tp1(promoted_plan)

            self._log_state_event(
                "TP1",
                symbol=promoted_plan.symbol,
                tf=promoted_plan.tf,
                state=promoted_plan.state,
                side=promoted_plan.side,
                entry=promoted_plan.entry,
                sl=promoted_plan.sl,
                tp=promoted_plan.tp,
                score=promoted_plan.score,
                note=promoted_plan.note,
                parcial=promoted_plan.parcial,
            )

        return patch

    def promote_tp1_to_tp2(self, symbol: str, tf: str) -> Dict[str, Any]:
        promoted_plan: Optional[FrozenPlan] = None

        with self._lock:
            plan = self._plans.get(self._key(symbol, tf))
            if not plan:
                return {}

            if plan.state != "TP1":
                return plan.to_row_patch()

            plan.state = "TP2"
            plan.tp2_ts = _now()
            plan.updated_at = _now()

            promoted_plan = deepcopy(plan)
            patch = plan.to_row_patch()

        if promoted_plan:
            self._log_state_event(
                "TP2",
                symbol=promoted_plan.symbol,
                tf=promoted_plan.tf,
                state=promoted_plan.state,
                side=promoted_plan.side,
                entry=promoted_plan.entry,
                sl=promoted_plan.sl,
                tp=promoted_plan.tp,
                score=promoted_plan.score,
                note=promoted_plan.note,
            )

        return patch

    def promote_tp1_to_run(self, symbol: str, tf: str) -> Dict[str, Any]:
        promoted_plan: Optional[FrozenPlan] = None

        with self._lock:
            plan = self._plans.get(self._key(symbol, tf))
            if not plan:
                return {}

            if plan.state != "TP1":
                return plan.to_row_patch()

            plan.state = "RUN"
            plan.run_ts = _now()
            plan.updated_at = _now()

            be_pos = self._be_positive_price(plan)
            if be_pos is not None:
                plan.sl = be_pos

            promoted_plan = deepcopy(plan)
            patch = plan.to_row_patch()

        if promoted_plan:
            self._log_state_event(
                "RUN",
                symbol=promoted_plan.symbol,
                tf=promoted_plan.tf,
                state=promoted_plan.state,
                side=promoted_plan.side,
                entry=promoted_plan.entry,
                sl=promoted_plan.sl,
                tp=promoted_plan.tp,
                score=promoted_plan.score,
                note=promoted_plan.note,
            )

        return patch

    # --------------------------------------------------
    # Live price update
    # --------------------------------------------------

    def update_live_trades(self, price_by_symbol: Dict[str, Any]) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []

        with self._lock:
            plans_snapshot = [
                (key, plan.symbol, plan.tf)
                for key, plan in self._plans.items()
            ]

        for key, symbol, tf in plans_snapshot:
            price = self._safe_float(price_by_symbol.get(symbol))
            if price is None:
                continue

            with self._lock:
                plan = self._plans.get(key)

            if not plan:
                continue

            entry = self._safe_float(plan.entry)
            sl = self._safe_float(plan.sl)
            tp = self._safe_float(plan.tp)
            side = str(plan.side or "").upper()
            state = str(plan.state or "").upper()

            if side not in {"BUY", "SELL"}:
                continue

            if state == "ENTRY" and entry is not None:
                if (side == "BUY" and price >= entry) or (side == "SELL" and price <= entry):
                    with self._lock:
                        live_plan = self._plans.get(key)
                        if live_plan and live_plan.state == "ENTRY":
                            live_plan.state = "IN_TRADE"
                            live_plan.updated_at = _now()
                            if live_plan.entry_ts is None:
                                live_plan.entry_ts = _now()
                            snap = deepcopy(live_plan)
                        else:
                            snap = None

                    if snap:
                        event = {
                            "symbol": symbol,
                            "tf": tf,
                            "event": "IN_TRADE",
                            "price": price,
                        }
                        events.append(event)
                        self._log_state_event(
                            "IN_TRADE",
                            symbol=snap.symbol,
                            tf=snap.tf,
                            state=snap.state,
                            side=snap.side,
                            entry=snap.entry,
                            sl=snap.sl,
                            tp=snap.tp,
                            price=price,
                            score=snap.score,
                            note=snap.note,
                        )

                    with self._lock:
                        plan = self._plans.get(key)
                    if not plan:
                        continue

                    entry = self._safe_float(plan.entry)
                    sl = self._safe_float(plan.sl)
                    tp = self._safe_float(plan.tp)
                    side = str(plan.side or "").upper()
                    state = str(plan.state or "").upper()

            if state in {"IN_TRADE", "ENTRY"}:
                if side == "BUY":
                    if sl is not None and price <= sl:
                        closed = self._close_plan(symbol, tf, "SL", sl)
                        if closed:
                            events.append({
                                "symbol": symbol,
                                "tf": tf,
                                "event": "SL",
                                "price": sl,
                            })
                        continue

                    if tp is not None and price >= tp:
                        closed = self._close_plan(symbol, tf, "TP2", tp)
                        if closed:
                            events.append({
                                "symbol": symbol,
                                "tf": tf,
                                "event": "TP2",
                                "price": tp,
                            })
                        continue

                elif side == "SELL":
                    if sl is not None and price >= sl:
                        closed = self._close_plan(symbol, tf, "SL", sl)
                        if closed:
                            events.append({
                                "symbol": symbol,
                                "tf": tf,
                                "event": "SL",
                                "price": sl,
                            })
                        continue

                    if tp is not None and price <= tp:
                        closed = self._close_plan(symbol, tf, "TP2", tp)
                        if closed:
                            events.append({
                                "symbol": symbol,
                                "tf": tf,
                                "event": "TP2",
                                "price": tp,
                            })
                        continue

            if state == "TP1":
                if side == "BUY" and sl is not None and price <= sl:
                    closed = self._close_plan(symbol, tf, "TP1_CLOSE", sl)
                    if closed:
                        events.append({
                            "symbol": symbol,
                            "tf": tf,
                            "event": "TP1_CLOSE",
                            "price": sl,
                        })
                    continue

                if side == "SELL" and sl is not None and price >= sl:
                    closed = self._close_plan(symbol, tf, "TP1_CLOSE", sl)
                    if closed:
                        events.append({
                            "symbol": symbol,
                            "tf": tf,
                            "event": "TP1_CLOSE",
                            "price": sl,
                        })
                    continue

                if tp is not None:
                    if (side == "BUY" and price >= tp) or (side == "SELL" and price <= tp):
                        closed = self._close_plan(symbol, tf, "TP2", tp)
                        if closed:
                            events.append({
                                "symbol": symbol,
                                "tf": tf,
                                "event": "TP2",
                                "price": tp,
                            })
                        continue

            if state == "RUN":
                if side == "BUY" and sl is not None and price <= sl:
                    closed = self._close_plan(symbol, tf, "RUN_CLOSE", sl)
                    if closed:
                        events.append({
                            "symbol": symbol,
                            "tf": tf,
                            "event": "RUN_CLOSE",
                            "price": sl,
                        })
                    continue

                if side == "SELL" and sl is not None and price >= sl:
                    closed = self._close_plan(symbol, tf, "RUN_CLOSE", sl)
                    if closed:
                        events.append({
                            "symbol": symbol,
                            "tf": tf,
                            "event": "RUN_CLOSE",
                            "price": sl,
                        })
                    continue

                if tp is not None:
                    if (side == "BUY" and price >= tp) or (side == "SELL" and price <= tp):
                        closed = self._close_plan(symbol, tf, "TP2", tp)
                        if closed:
                            events.append({
                                "symbol": symbol,
                                "tf": tf,
                                "event": "TP2",
                                "price": tp,
                            })
                        continue

        return events

    def _close_plan(self, symbol: str, tf: str, result: str, exit_price: float) -> Dict[str, Any]:
        close_event_name = self._close_event_name(result)
        closed_plan: Optional[FrozenPlan] = None

        with self._lock:
            key = self._key(symbol, tf)
            plan = self._plans.get(key)
            if not plan:
                return {}

            if plan.state == "CLOSED":
                return plan.to_row_patch()

            entry = self._safe_float(plan.entry) or 0.0
            sl = self._safe_float(plan.sl) or 0.0
            tp = self._safe_float(plan.tp) or 0.0
            side = plan.side or ""

            plan.state = "CLOSED"
            plan.closed_ts = _now()
            plan.close_reason = result
            plan.close_price = exit_price
            plan.updated_at = plan.closed_ts

            closed_patch = plan.to_row_patch()
            closed_plan = deepcopy(plan)

            self.register_trade_result(
                symbol=symbol,
                tf=tf,
                side=side,
                entry=entry,
                sl=sl,
                tp=tp,
                exit_price=exit_price,
                result=result,
            )

            del self._plans[key]

        if closed_plan:
            self._log_state_event(
                close_event_name,
                symbol=closed_plan.symbol,
                tf=closed_plan.tf,
                state="CLOSED",
                side=closed_plan.side,
                entry=closed_plan.entry,
                sl=closed_plan.sl,
                tp=closed_plan.tp,
                price=exit_price,
                score=closed_plan.score,
                note=closed_plan.note,
                result=result,
            )

        return closed_patch

    # --------------------------------------------------
    # Main merge
    # --------------------------------------------------

    def merge_row_with_freeze(self, row: Dict[str, Any]) -> Dict[str, Any]:
        symbol = row.get("symbol")
        tf = row.get("tf")

        if not symbol or not tf:
            return row

        raw_state = str(row.get("state") or "").upper()

        if raw_state in {"WAIT", "SIN_SETUP"}:
            incoming_state = "SIN_SETUP"
        elif raw_state in {"WAIT_GATILLO", "SIGNAL", "SET_UP"}:
            incoming_state = "SET_UP"
        elif raw_state == "ENTRY":
            incoming_state = "ENTRY"
        elif raw_state == "IN_TRADE":
            incoming_state = "IN_TRADE"
        elif raw_state == "TP1":
            incoming_state = "TP1"
        elif raw_state == "TP2":
            incoming_state = "TP2"
        elif raw_state == "RUN":
            incoming_state = "RUN"
        elif raw_state == "CLOSED":
            incoming_state = "CLOSED"
        else:
            incoming_state = "SIN_SETUP"

        if incoming_state == "SIN_SETUP":
            patch = self.freeze_sin_setup(symbol, tf, row)
            merged = deepcopy(row)
            merged.update(patch)
            return merged

        key = self._key(symbol, tf)
        with self._lock:
            existing = self._plans.get(key)

        if existing is None:
            merged = self.freeze_plan(row)
        else:
            merged = deepcopy(row)
            merged.update(existing.to_row_patch())

        with self._lock:
            current_plan = self._plans.get(key)

        if current_plan and merged.get("state") == "SET_UP" and self._candle_touches_entry(row, current_plan.entry):
            merged.update(self.promote_setup_to_entry(symbol, tf, row))

        with self._lock:
            current_plan = self._plans.get(key)

        if current_plan and merged.get("state") == "ENTRY":
            merged.update(self.promote_entry_to_in_trade(symbol, tf, row))

        with self._lock:
            current_plan = self._plans.get(key)

        if current_plan and merged.get("state") in {"ENTRY", "IN_TRADE"} and self._hit_1r(current_plan, row):
            merged.update(self.promote_in_trade_to_tp1(symbol, tf))

        with self._lock:
            current_plan = self._plans.get(key)

        if merged.get("state") == "TP1" and current_plan and self._candle_hits_tp(row, current_plan.side, current_plan.tp):
            if self._row_wants_run(row):
                merged.update(self.promote_tp1_to_run(symbol, tf))
            else:
                merged.update(self.promote_tp1_to_tp2(symbol, tf))

        with self._lock:
            current_plan = self._plans.get(key)

        if merged.get("state") == "TP2" and current_plan:
            tp_price = self._safe_float(current_plan.tp)
            if tp_price is not None:
                merged.update(self._close_plan(symbol, tf, "TP2", tp_price))

        with self._lock:
            current_plan = self._plans.get(key)

        if merged.get("state") == "RUN" and current_plan and self._candle_hits_sl(row, current_plan.side, current_plan.sl):
            sl_price = self._safe_float(current_plan.sl)
            if sl_price is not None:
                merged.update(self._close_plan(symbol, tf, "RUN_CLOSE", sl_price))

        with self._lock:
            current_plan = self._plans.get(key)

        if merged.get("state") in {"ENTRY", "IN_TRADE", "TP1"} and current_plan and self._candle_hits_sl(row, current_plan.side, current_plan.sl):
            sl_price = self._safe_float(current_plan.sl)
            if sl_price is not None:
                close_reason = "TP1_CLOSE" if str(current_plan.state).upper() == "TP1" else "SL"
                merged.update(self._close_plan(symbol, tf, close_reason, sl_price))

        return merged

    # --------------------------------------------------
    # Closed trades / CSV
    # --------------------------------------------------

    def register_trade_result(
        self,
        symbol: str,
        tf: str,
        side: str,
        entry: float,
        sl: float,
        tp: float,
        exit_price: float,
        result: str,
    ) -> None:
        trade = self._build_trade_row(
            ts=_now(),
            symbol=symbol,
            tf=tf,
            side=side,
            entry=entry,
            sl=sl,
            tp=tp,
            exit_price=exit_price,
            result=result,
        )

        with self._lock:
            self._closed_trades.append(trade)
            if len(self._closed_trades) > 5000:
                self._closed_trades = self._closed_trades[-2000:]

        try:
            self._save_csv(trade)
        except Exception:
            pass

        try:
            self._save_daily_csv(trade)
        except Exception:
            pass

        try:
            log_closed = getattr(BITACORA, "log_closed", None)
            if callable(log_closed):
                log_closed(trade)
        except Exception:
            pass

        self.log_op("TRADE_CLOSED", trade)

    def get_closed_trades(self, limit: int = 200) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 2000))

        try:
            closed = BITACORA.get_closed(limit)
            if isinstance(closed, list):
                return closed
        except Exception:
            pass

        with self._lock:
            combined = self._partials_log + self._closed_trades
            return deepcopy(combined[-limit:])


runtime = AtlasRuntime()
RUNTIME = runtime
