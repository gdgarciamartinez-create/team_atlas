from __future__ import annotations

from atlas.metrics.bitacora_store import BITACORA
from atlas.metrics.metrics_store import SetupMetric, metrics_store
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional
from uuid import uuid4
import csv
import math

CSV_PATH = Path("atlas_trades.csv")
DAILY_CSV_PATH = Path("atlas_daily_log.csv")
TRADE_SUMMARY_CSV_PATH = Path("atlas_trade_summaries.csv")

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


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None


@dataclass
class FrozenPlan:
    symbol: str
    tf: str
    world: Optional[str] = None
    atlas_mode: Optional[str] = None
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
    created_at: Optional[str] = None

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
            "world": self.world,
            "atlas_mode": self.atlas_mode,
            "state": self.state,
            "entry": self.entry,
            "sl": self.sl,
            "tp": self.tp,
            "tp1": self.parcial,
            "tp1_price": self.parcial,
            "tp2": self.tp,
            "parcial": self.parcial,
            "lot": self.lot,
            "risk_percent": self.risk_percent,
            "score": self.score,
            "side": self.side,
            "note": self.note,
            "text": self.state,
            "created_at": self.created_at,
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
        self._lock = RLock()

        self.engine_running: bool = True
        self.feed_running: bool = True

        self._plans: Dict[str, FrozenPlan] = {}
        self._active_plan_keys_by_slot: Dict[str, str] = {}
        self._closed_trades: List[Dict[str, Any]] = []
        self._ops_log: List[Dict[str, Any]] = []
        self._partials_log: List[Dict[str, Any]] = []
        self._trade_summaries: Dict[str, Dict[str, Any]] = {}
        self._load_trade_summaries_csv()

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def _norm_ctx(self, value: Any) -> str:
        return str(value or "").strip().upper()

    def _slot_key(self, symbol: str, tf: str) -> str:
        return f"{self._norm_ctx(symbol)}|{self._norm_ctx(tf)}"

    def _key(
        self,
        symbol: str,
        tf: str,
        world: Optional[str] = None,
        atlas_mode: Optional[str] = None,
    ) -> str:
        return (
            f"{self._norm_ctx(world)}|"
            f"{self._norm_ctx(atlas_mode)}|"
            f"{self._norm_ctx(symbol)}|"
            f"{self._norm_ctx(tf)}"
        )

    def _row_context(self, row: Optional[Dict[str, Any]]) -> tuple[Optional[str], Optional[str]]:
        if not isinstance(row, dict):
            return None, None
        return row.get("world"), row.get("atlas_mode")

    def _plan_sort_key(self, plan: FrozenPlan) -> tuple[str, str, str, str]:
        return (
            str(plan.updated_at or ""),
            self._norm_ctx(plan.world),
            self._norm_ctx(plan.atlas_mode),
            self._norm_ctx(plan.tf),
        )

    def _set_active_plan_key(self, plan_key: str, plan: FrozenPlan) -> None:
        self._active_plan_keys_by_slot[self._slot_key(plan.symbol, plan.tf)] = plan_key

    def _clear_active_plan_key(self, plan_key: str, plan: FrozenPlan) -> None:
        slot = self._slot_key(plan.symbol, plan.tf)
        if self._active_plan_keys_by_slot.get(slot) == plan_key:
            self._active_plan_keys_by_slot.pop(slot, None)

    def _candidate_plan_keys(
        self,
        symbol: str,
        tf: str,
        world: Optional[str] = None,
        atlas_mode: Optional[str] = None,
    ) -> List[str]:
        sym_u = self._norm_ctx(symbol)
        tf_u = self._norm_ctx(tf)
        world_u = self._norm_ctx(world)
        mode_u = self._norm_ctx(atlas_mode)

        out: List[str] = []
        for key, plan in self._plans.items():
            if self._norm_ctx(plan.symbol) != sym_u:
                continue
            if self._norm_ctx(plan.tf) != tf_u:
                continue
            if world_u and self._norm_ctx(plan.world) != world_u:
                continue
            if mode_u and self._norm_ctx(plan.atlas_mode) != mode_u:
                continue
            out.append(key)
        return out

    def _resolve_plan_key(
        self,
        symbol: str,
        tf: str,
        world: Optional[str] = None,
        atlas_mode: Optional[str] = None,
    ) -> Optional[str]:
        exact_key = self._key(symbol, tf, world, atlas_mode)
        if exact_key in self._plans:
            return exact_key

        slot_key = self._slot_key(symbol, tf)
        active_key = self._active_plan_keys_by_slot.get(slot_key)
        if active_key in self._plans:
            active_plan = self._plans[active_key]
            if (
                (not world or self._norm_ctx(active_plan.world) == self._norm_ctx(world))
                and (not atlas_mode or self._norm_ctx(active_plan.atlas_mode) == self._norm_ctx(atlas_mode))
            ):
                return active_key

        matches = self._candidate_plan_keys(symbol, tf, world, atlas_mode)
        if not matches and (world or atlas_mode):
            matches = self._candidate_plan_keys(symbol, tf)
        if not matches:
            return None

        matches.sort(key=lambda k: self._plan_sort_key(self._plans[k]))
        return matches[-1]

    def _get_plan_by_key(self, plan_key: Optional[str]) -> Optional[FrozenPlan]:
        if not plan_key:
            return None
        return self._plans.get(plan_key)

    def _get_plan(
        self,
        symbol: str,
        tf: str,
        world: Optional[str] = None,
        atlas_mode: Optional[str] = None,
    ) -> tuple[Optional[str], Optional[FrozenPlan]]:
        plan_key = self._resolve_plan_key(symbol, tf, world, atlas_mode)
        if not plan_key:
            return None, None
        plan = self._plans.get(plan_key)
        return plan_key, plan

    def _safe_float(self, v: Any) -> Optional[float]:
        try:
            return float(v)
        except Exception:
            return None

    def _safe_bool(self, v: Any) -> Optional[bool]:
        if v in (None, ""):
            return None
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in {"true", "1", "yes"}:
            return True
        if s in {"false", "0", "no"}:
            return False
        return None

    def _note_with_state(self, state: Any, note: Any) -> str:
        state_key = str(state or "").upper().strip() or "SIN_SETUP"
        raw_note = str(note or "").strip()

        if not raw_note:
            return state_key

        head, sep, tail = raw_note.partition("|")
        if not sep:
            return state_key

        return f"{state_key} | {tail.strip()}" if tail.strip() else state_key

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
        world: Optional[str] = None,
        atlas_mode: Optional[str] = None,
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

        if world is not None:
            payload["world"] = world
        if atlas_mode is not None:
            payload["atlas_mode"] = atlas_mode
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
        world: Optional[str] = None,
        atlas_mode: Optional[str] = None,
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
                world=world,
                atlas_mode=atlas_mode,
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

    def _normalize_exit_reason(self, result: str, is_partial: bool = False) -> str:
        raw = str(result or "").upper().strip()

        if raw == "TP1":
            return "TP1_PARTIAL"
        if raw in {"TP2", "TP"}:
            return "TP2_FINAL"
        if raw in {"TP1_CLOSE", "RUN_CLOSE", "BE"}:
            return "BE_CLOSE"
        if raw == "SL":
            return "SL"
        if raw == "MANUAL_CLOSE":
            return "MANUAL_CLOSE"
        if raw == "TIME_CLOSE":
            return "TIME_CLOSE"
        return "INVALIDATION_CLOSE"

    def _resolve_lot_fields(
        self,
        lot: Optional[float],
        lot_raw: Optional[float],
        lot_capped: Optional[float],
        lot_cap_reason: Optional[str],
    ) -> tuple[Optional[float], Optional[float], Optional[float], Optional[str], Optional[str]]:
        lot_f = self._safe_float(lot)
        lot_raw_f = self._safe_float(lot_raw)
        lot_capped_f = self._safe_float(lot_capped)
        lot_error: Optional[str] = None

        if lot_f is None or lot_f <= 0:
            if lot_capped_f is not None and lot_capped_f > 0:
                lot_f = lot_capped_f
            elif lot_raw_f is not None and lot_raw_f > 0 and not lot_cap_reason:
                lot_f = lot_raw_f

        if lot_capped_f is None and lot_f is not None and lot_f > 0:
            lot_capped_f = lot_f

        if lot_raw_f is None and lot_f is not None and lot_f > 0:
            lot_raw_f = lot_f

        if lot_f is None or lot_f <= 0:
            lot_f = None
            lot_error = "MISSING_LOT"

        return lot_f, lot_raw_f, lot_capped_f, lot_cap_reason, lot_error

    def _trade_root_id(self, plan: FrozenPlan) -> str:
        existing = str((plan.extra or {}).get("trade_id") or "").strip()
        if existing:
            return existing

        trade_id = str(uuid4())
        plan.extra["trade_id"] = trade_id
        return trade_id

    def _leg_trade_id(self, root_trade_id: str, leg_id: int) -> str:
        return f"{root_trade_id}:L{int(leg_id)}"

    def _price_move(self, entry: float, exit_price: float, side: str) -> float:
        side_u = str(side or "").upper().strip()
        if side_u == "BUY":
            return exit_price - entry
        return entry - exit_price

    def _trade_metrics(
        self,
        symbol: str,
        entry: float,
        exit_price: float,
        side: str,
        lot: Optional[float],
    ) -> Dict[str, Any]:
        sym = str(symbol or "").upper().strip()
        asset_type = self._asset_type_from_symbol(sym)
        price_move = self._price_move(entry, exit_price, side)
        pip_move: Optional[float] = None
        point_move: Optional[float] = None

        forex_6 = {
            "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD",
            "USDCHF", "USDCAD", "EURGBP", "EURCAD",
            "EURAUD", "GBPNZD",
        }
        forex_7 = {s + "Z" for s in forex_6}

        if asset_type == "FOREX":
            if "JPY" in sym:
                pip_move = price_move * 100.0
            elif sym in forex_6 or sym in forex_7:
                pip_move = price_move * 10000.0
            else:
                pip_move = price_move
        elif asset_type in {"GOLD", "INDICES", "OIL"}:
            point_move = price_move
        elif asset_type == "CRYPTO":
            point_move = None
        else:
            point_move = price_move

        usd_result = self._calc_usd(symbol, entry, exit_price, side, lot)
        legacy_pips = pip_move if pip_move is not None else point_move

        return {
            "asset_type": asset_type,
            "price_move": round(price_move, 6),
            "pip_move": round(pip_move, 2) if pip_move is not None else None,
            "point_move": round(point_move, 6) if point_move is not None else None,
            "pips": round(legacy_pips, 2) if legacy_pips is not None else None,
            "usd_result": round(usd_result, 2) if usd_result is not None else None,
            "usd": round(usd_result, 2) if usd_result is not None else None,
        }

    def _duration_sec(self, opened_at: Optional[str], closed_at: Optional[str]) -> Optional[int]:
        start_dt = _parse_ts(opened_at)
        end_dt = _parse_ts(closed_at)
        if not start_dt or not end_dt:
            return None
        return max(0, int((end_dt - start_dt).total_seconds()))

    def _trade_summary_fieldnames(self) -> List[str]:
        return [
            "trade_id",
            "world",
            "atlas_mode",
            "mode",
            "symbol",
            "tf",
            "side",
            "entry_price",
            "sl_price",
            "tp1_price",
            "tp2_price",
            "lot_total",
            "risk_percent",
            "pnl_total_usd",
            "pnl_total_points",
            "opened_at",
            "closed_at",
            "duration_sec",
            "legs_count",
            "exit_final_reason",
            "score_max",
            "score_avg",
            "had_partial",
            "had_be_close",
            "had_tp2",
        ]

    def _floating_epsilon(self, symbol: str, asset_type: Optional[str] = None) -> float:
        sym = str(symbol or "").upper().strip()
        kind = str(asset_type or self._asset_type_from_symbol(sym)).upper().strip()

        if kind == "FOREX":
            if "JPY" in sym:
                return 0.01
            return 0.0001

        if kind in {"GOLD", "OIL"}:
            return 0.01

        return 1.0

    def _trade_pnl_state(self, value: Any, symbol: str, asset_type: Optional[str] = None) -> str:
        amount = self._safe_float(value)
        if amount is None:
            return "FLAT"

        epsilon = self._floating_epsilon(symbol, asset_type)
        if abs(amount) < epsilon:
            return "FLAT"
        if amount > 0:
            return "POSITIVE"
        return "NEGATIVE"

    def _summary_points_value(self, trade: Dict[str, Any]) -> float:
        point_move = self._safe_float(trade.get("point_move"))
        if point_move is not None:
            return point_move
        pip_move = self._safe_float(trade.get("pip_move"))
        if pip_move is not None:
            return pip_move
        return self._safe_float(trade.get("pips")) or 0.0

    def _load_trade_summaries_csv(self) -> None:
        if not TRADE_SUMMARY_CSV_PATH.exists():
            return

        loaded: Dict[str, Dict[str, Any]] = {}

        try:
            with open(TRADE_SUMMARY_CSV_PATH, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    trade_id = str(row.get("trade_id") or "").strip()
                    if not trade_id:
                        continue
                    loaded[trade_id] = {
                        "trade_id": trade_id,
                        "world": row.get("world"),
                        "atlas_mode": row.get("atlas_mode"),
                        "mode": row.get("mode") or row.get("atlas_mode"),
                        "symbol": row.get("symbol"),
                        "tf": row.get("tf"),
                        "side": row.get("side"),
                        "entry_price": self._safe_float(row.get("entry_price")),
                        "sl_price": self._safe_float(row.get("sl_price")),
                        "tp1_price": self._safe_float(row.get("tp1_price")),
                        "tp2_price": self._safe_float(row.get("tp2_price")),
                        "lot_total": self._safe_float(row.get("lot_total")),
                        "risk_percent": self._safe_float(row.get("risk_percent")),
                        "pnl_total_usd": self._safe_float(row.get("pnl_total_usd")),
                        "pnl_total_points": self._safe_float(row.get("pnl_total_points")),
                        "opened_at": row.get("opened_at"),
                        "closed_at": row.get("closed_at"),
                        "duration_sec": int(float(row.get("duration_sec"))) if row.get("duration_sec") not in (None, "") else None,
                        "legs_count": int(float(row.get("legs_count"))) if row.get("legs_count") not in (None, "") else 0,
                        "exit_final_reason": row.get("exit_final_reason"),
                        "score_max": self._safe_float(row.get("score_max")),
                        "score_avg": self._safe_float(row.get("score_avg")),
                        "had_partial": self._safe_bool(row.get("had_partial")),
                        "had_be_close": self._safe_bool(row.get("had_be_close")),
                        "had_tp2": self._safe_bool(row.get("had_tp2")),
                    }
        except Exception:
            return

        self._trade_summaries = loaded

    def _save_trade_summaries_csv(self) -> None:
        fieldnames = self._trade_summary_fieldnames()
        with open(TRADE_SUMMARY_CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in self._trade_summaries.values():
                writer.writerow({key: item.get(key) for key in fieldnames})

    def _upsert_trade_summary(self, trade: Dict[str, Any]) -> None:
        summary_id = str(trade.get("parent_trade_id") or trade.get("trade_id") or "").strip()
        if not summary_id:
            return

        leg_id = int(self._safe_float(trade.get("leg_id")) or 1)
        usd_leg = self._safe_float(trade.get("usd_result") if trade.get("usd_result") is not None else trade.get("usd")) or 0.0
        points_leg = self._summary_points_value(trade)
        score_leg = self._safe_float(trade.get("score")) or 0.0
        exit_reason = str(trade.get("exit_reason") or "").upper().strip()
        is_partial = bool(trade.get("is_partial")) or exit_reason == "TP1_PARTIAL"

        with self._lock:
            existing = deepcopy(self._trade_summaries.get(summary_id) or {})
            pnl_total_usd = (self._safe_float(existing.get("pnl_total_usd")) or 0.0) + usd_leg
            pnl_total_points = (self._safe_float(existing.get("pnl_total_points")) or 0.0) + points_leg
            opened_at = existing.get("opened_at") or trade.get("opened_at") or trade.get("entry_ts") or trade.get("signal_ts")
            closed_at = trade.get("closed_at") or trade.get("closed_ts") or existing.get("closed_at")
            prev_legs_count = int(self._safe_float(existing.get("legs_count")) or 0)
            legs_count = max(prev_legs_count, leg_id)
            prev_score_avg = self._safe_float(existing.get("score_avg")) or 0.0
            prev_score_max = self._safe_float(existing.get("score_max")) or 0.0
            effective_prev_count = prev_legs_count if prev_legs_count > 0 else 0
            score_avg = score_leg if effective_prev_count == 0 else (
                ((prev_score_avg * effective_prev_count) + score_leg) / max(legs_count, 1)
            )
            score_max = max(prev_score_max, score_leg)
            had_partial = bool(existing.get("had_partial")) or is_partial
            had_be_close = bool(existing.get("had_be_close")) or exit_reason == "BE_CLOSE"
            had_tp2 = bool(existing.get("had_tp2")) or exit_reason == "TP2_FINAL"

            summary = {
                "trade_id": summary_id,
                "world": trade.get("world"),
                "atlas_mode": trade.get("atlas_mode"),
                "mode": trade.get("mode") or trade.get("atlas_mode"),
                "symbol": trade.get("symbol"),
                "tf": trade.get("tf"),
                "side": trade.get("side"),
                "entry_price": trade.get("entry_price", trade.get("entry")),
                "sl_price": trade.get("sl_price", trade.get("sl")),
                "tp1_price": trade.get("tp1_price"),
                "tp2_price": trade.get("tp2_price", trade.get("tp")),
                "lot_total": trade.get("lot_capped") or trade.get("lot") or trade.get("lot_raw"),
                "risk_percent": trade.get("risk_percent"),
                "pnl_total_usd": round(pnl_total_usd, 2),
                "pnl_total_points": round(pnl_total_points, 6),
                "opened_at": opened_at,
                "closed_at": closed_at,
                "duration_sec": self._duration_sec(opened_at, closed_at),
                "legs_count": legs_count,
                "exit_final_reason": trade.get("exit_reason"),
                "score_max": round(score_max, 2),
                "score_avg": round(score_avg, 2),
                "had_partial": had_partial,
                "had_be_close": had_be_close,
                "had_tp2": had_tp2,
            }
            self._trade_summaries[summary_id] = summary

        try:
            self._save_trade_summaries_csv()
        except Exception:
            pass

    def _patch_with_floating(self, patch: Dict[str, Any], live_price: Optional[float]) -> Dict[str, Any]:
        if not isinstance(patch, dict):
            return patch

        price_f = self._safe_float(live_price)
        entry_f = self._safe_float(patch.get("entry"))
        side = str(patch.get("side") or "").upper().strip()
        symbol = str(patch.get("symbol") or "")
        state = str(patch.get("state") or "").upper().strip()

        patch = deepcopy(patch)
        patch["floating_price_move"] = None
        patch["floating_point_move"] = None
        patch["floating_pip_move"] = None
        patch["floating_usd"] = None
        patch["trade_pnl_state"] = "FLAT"

        if state not in {"ENTRY", "IN_TRADE", "TP1", "TP2", "RUN"}:
            return patch

        if price_f is None or entry_f is None or side not in {"BUY", "SELL"}:
            return patch

        lot_f, _, _, _, _ = self._resolve_lot_fields(
            lot=self._safe_float(patch.get("lot")),
            lot_raw=self._safe_float(patch.get("lot_raw")),
            lot_capped=self._safe_float(patch.get("lot_capped")),
            lot_cap_reason=patch.get("lot_cap_reason"),
        )
        metrics = self._trade_metrics(symbol, entry_f, price_f, side, lot_f)

        point_move = metrics["point_move"]
        if point_move is None:
            point_move = metrics["price_move"]

        patch["floating_price_move"] = metrics["price_move"]
        patch["floating_point_move"] = point_move
        patch["floating_pip_move"] = metrics["pip_move"]
        patch["floating_usd"] = metrics["usd_result"]
        patch["trade_pnl_state"] = self._trade_pnl_state(
            metrics["usd_result"],
            symbol,
            metrics["asset_type"],
        )
        return patch

    def _calc_pips(self, symbol: str, entry: float, exit_price: float, side: str) -> float:
        side_u = str(side or "").upper().strip()

        if side_u == "BUY":
            move = exit_price - entry
        else:
            move = entry - exit_price

        sym = str(symbol or "").upper()

        # JPY: mostrar pip clásico de 0.01
        if "JPY" in sym:
            return move * 100.0

        forex_6 = {
            "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD",
            "USDCHF", "USDCAD", "EURGBP", "EURCAD",
            "EURAUD", "GBPNZD",
        }
        forex_7 = {s + "Z" for s in forex_6}

        if sym in forex_6 or sym in forex_7:
            return move * 10000.0

        return move

    def _calc_usd(self, symbol: str, entry: float, exit_price: float, side: str, lot: Optional[float]) -> Optional[float]:
        lot_f = self._safe_float(lot)
        if lot_f is None or lot_f <= 0:
            return None

        side_u = str(side or "").upper().strip()

        if side_u == "BUY":
            move = exit_price - entry
        else:
            move = entry - exit_price

        sym = str(symbol or "").upper()

        # JPY: usar pips clásicos * valor aproximado por pip/lote estándar
        if "JPY" in sym:
            pips = move * 100.0
            usd_per_pip_per_1_lot = 9.0
            return pips * usd_per_pip_per_1_lot * lot_f

        forex_6 = {
            "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD",
            "USDCHF", "USDCAD", "EURGBP", "EURCAD",
            "EURAUD", "GBPNZD",
        }
        forex_7 = {s + "Z" for s in forex_6}

        if sym in forex_6 or sym in forex_7:
            pips = move * 10000.0
            usd_per_pip_per_1_lot = 10.0
            return pips * usd_per_pip_per_1_lot * lot_f

        if sym.startswith("XAU"):
            return move * lot_f * 100.0

        if sym.startswith("USOIL"):
            return move * lot_f * 100.0

        if sym.startswith("USTEC"):
            return move * lot_f * 1.0

        if sym.startswith("BTC"):
            return move * lot_f * 1.0

        return move * lot_f

    def _build_trade_row(
        self,
        *,
        ts: str,
        symbol: str,
        tf: str,
        world: Optional[str],
        atlas_mode: Optional[str],
        side: str,
        entry: float,
        sl: float,
        tp: float,
        exit_price: float,
        result: str,
        lot: Optional[float] = None,
        lot_raw: Optional[float] = None,
        lot_capped: Optional[float] = None,
        lot_cap_reason: Optional[str] = None,
        score: Optional[float] = None,
        signal_ts: Optional[str] = None,
        entry_ts: Optional[str] = None,
        closed_ts: Optional[str] = None,
        trade_id: Optional[str] = None,
        parent_trade_id: Optional[str] = None,
        leg_id: Optional[int] = None,
        is_partial: Optional[bool] = None,
        partial_percent: Optional[float] = None,
        state_at_entry: Optional[str] = None,
        tp1_price: Optional[float] = None,
        tp2_price: Optional[float] = None,
        sl_price: Optional[float] = None,
        risk_percent: Optional[float] = None,
        opened_at: Optional[str] = None,
        lot_error: Optional[str] = None,
    ) -> Dict[str, Any]:
        lot_f, lot_raw_f, lot_capped_f, lot_cap_reason_s, resolved_lot_error = self._resolve_lot_fields(
            lot=lot,
            lot_raw=lot_raw,
            lot_capped=lot_capped,
            lot_cap_reason=lot_cap_reason,
        )
        metrics = self._trade_metrics(symbol, entry, exit_price, side, lot_f)
        closed_at = closed_ts or ts
        opened_at_v = opened_at or entry_ts or signal_ts
        duration_sec = self._duration_sec(opened_at_v, closed_at)
        exit_reason = self._normalize_exit_reason(result, is_partial=bool(is_partial))
        state_at_entry_v = str(state_at_entry or "ENTRY").upper().strip()
        parent_trade_id_v = parent_trade_id or trade_id

        return {
            "time": ts,
            "ts": ts,
            "world": world,
            "atlas_mode": atlas_mode,
            "mode": atlas_mode,
            "symbol": symbol,
            "tf": tf,
            "side": side,
            "score": score if score is not None else 0,
            "state_at_entry": state_at_entry_v,
            "trade_id": trade_id,
            "parent_trade_id": parent_trade_id_v,
            "leg_id": leg_id,
            "is_partial": bool(is_partial),
            "partial_percent": partial_percent,
            "entry_price": entry,
            "tp1_price": tp1_price,
            "tp2_price": tp2_price if tp2_price is not None else tp,
            "sl_price": sl_price if sl_price is not None else sl,
            "exit_price": exit_price,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "exit": exit_price,
            "close_price": exit_price,
            "exit_reason": exit_reason,
            "result": exit_reason,
            "raw_result": result,
            "asset_type": metrics["asset_type"],
            "price_move": metrics["price_move"],
            "pip_move": metrics["pip_move"],
            "point_move": metrics["point_move"],
            "pips": metrics["pips"],
            "usd_result": metrics["usd_result"],
            "usd": metrics["usd"],
            "lot": lot_f if lot_f is not None else 0.0,
            "lot_raw": lot_raw_f if lot_raw_f is not None else 0.0,
            "lot_capped": lot_capped_f if lot_capped_f is not None else 0.0,
            "lot_cap_reason": lot_cap_reason_s,
            "lot_error": lot_error or resolved_lot_error,
            "risk_percent": risk_percent,
            "opened_at": opened_at_v,
            "signal_ts": signal_ts,
            "entry_ts": entry_ts,
            "closed_at": closed_at,
            "closed_ts": closed_at,
            "duration_sec": duration_sec,
        }

    def _save_csv(self, row: Dict[str, Any]) -> None:
        fieldnames = [
            "time",
            "ts",
            "world",
            "atlas_mode",
            "mode",
            "symbol",
            "tf",
            "side",
            "score",
            "state_at_entry",
            "trade_id",
            "parent_trade_id",
            "leg_id",
            "is_partial",
            "partial_percent",
            "lot",
            "lot_raw",
            "lot_capped",
            "lot_cap_reason",
            "lot_error",
            "risk_percent",
            "entry_price",
            "tp1_price",
            "tp2_price",
            "sl_price",
            "exit_price",
            "entry",
            "sl",
            "tp",
            "exit",
            "close_price",
            "exit_reason",
            "result",
            "raw_result",
            "asset_type",
            "price_move",
            "pip_move",
            "point_move",
            "pips",
            "usd_result",
            "usd",
            "opened_at",
            "signal_ts",
            "entry_ts",
            "closed_at",
            "closed_ts",
            "duration_sec",
        ]
        exists = self._ensure_csv_header(CSV_PATH, fieldnames)

        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
            )

            if not exists:
                writer.writeheader()

            writer.writerow(row)

    def _save_daily_csv(self, row: Dict[str, Any]) -> None:
        fieldnames = [
            "date",
            "time",
            "world",
            "atlas_mode",
            "mode",
            "symbol",
            "tf",
            "side",
            "score",
            "state_at_entry",
            "trade_id",
            "parent_trade_id",
            "leg_id",
            "is_partial",
            "partial_percent",
            "lot",
            "lot_raw",
            "lot_capped",
            "lot_cap_reason",
            "lot_error",
            "risk_percent",
            "entry_price",
            "tp1_price",
            "tp2_price",
            "sl_price",
            "exit_price",
            "entry",
            "sl",
            "tp",
            "exit",
            "close_price",
            "exit_reason",
            "result",
            "raw_result",
            "asset_type",
            "price_move",
            "pip_move",
            "point_move",
            "pips",
            "usd_result",
            "usd",
            "opened_at",
            "signal_ts",
            "entry_ts",
            "closed_at",
            "closed_ts",
            "duration_sec",
        ]
        exists = self._ensure_csv_header(DAILY_CSV_PATH, fieldnames)

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
            "world": row.get("world"),
            "atlas_mode": row.get("atlas_mode"),
            "mode": row.get("mode"),
            "symbol": row.get("symbol"),
            "tf": row.get("tf"),
            "side": row.get("side"),
            "score": row.get("score"),
            "state_at_entry": row.get("state_at_entry"),
            "trade_id": row.get("trade_id"),
            "parent_trade_id": row.get("parent_trade_id"),
            "leg_id": row.get("leg_id"),
            "is_partial": row.get("is_partial"),
            "partial_percent": row.get("partial_percent"),
            "lot": row.get("lot"),
            "lot_raw": row.get("lot_raw"),
            "lot_capped": row.get("lot_capped"),
            "lot_cap_reason": row.get("lot_cap_reason"),
            "lot_error": row.get("lot_error"),
            "risk_percent": row.get("risk_percent"),
            "entry_price": row.get("entry_price"),
            "tp1_price": row.get("tp1_price"),
            "tp2_price": row.get("tp2_price"),
            "sl_price": row.get("sl_price"),
            "exit_price": row.get("exit_price"),
            "entry": row.get("entry"),
            "sl": row.get("sl"),
            "tp": row.get("tp"),
            "exit": row.get("exit"),
            "close_price": row.get("close_price"),
            "exit_reason": row.get("exit_reason"),
            "result": row.get("result"),
            "raw_result": row.get("raw_result"),
            "asset_type": row.get("asset_type"),
            "price_move": row.get("price_move"),
            "pip_move": row.get("pip_move"),
            "point_move": row.get("point_move"),
            "pips": row.get("pips"),
            "usd_result": row.get("usd_result"),
            "usd": row.get("usd"),
            "opened_at": row.get("opened_at"),
            "signal_ts": row.get("signal_ts"),
            "entry_ts": row.get("entry_ts"),
            "closed_at": row.get("closed_at"),
            "closed_ts": row.get("closed_ts"),
            "duration_sec": row.get("duration_sec"),
        }

        with open(DAILY_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
            )

            if not exists:
                writer.writeheader()

            writer.writerow(daily_row)

    def _ensure_csv_header(self, path: Path, fieldnames: List[str]) -> bool:
        if not path.exists():
            return False

        try:
            with open(path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                existing_fields = reader.fieldnames or []

                if existing_fields == fieldnames:
                    return True

                rows = list(reader)

            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for row in rows:
                    normalized = {key: row.get(key) for key in fieldnames}
                    if "time" in fieldnames and not normalized.get("time"):
                        normalized["time"] = row.get("ts")
                    if "mode" in fieldnames and not normalized.get("mode"):
                        normalized["mode"] = row.get("atlas_mode")
                    if "entry_price" in fieldnames and not normalized.get("entry_price"):
                        normalized["entry_price"] = row.get("entry")
                    if "lot" in fieldnames and not normalized.get("lot"):
                        normalized["lot"] = row.get("lot_capped") or row.get("lot_raw")
                    if "sl_price" in fieldnames and not normalized.get("sl_price"):
                        normalized["sl_price"] = row.get("sl")
                    if "tp2_price" in fieldnames and not normalized.get("tp2_price"):
                        normalized["tp2_price"] = row.get("tp")
                    if "exit_price" in fieldnames and not normalized.get("exit_price"):
                        normalized["exit_price"] = row.get("exit")
                    if "close_price" in fieldnames and not normalized.get("close_price"):
                        normalized["close_price"] = row.get("exit")
                    if "closed_at" in fieldnames and not normalized.get("closed_at"):
                        normalized["closed_at"] = row.get("closed_ts") or row.get("ts")
                    if "closed_ts" in fieldnames and not normalized.get("closed_ts"):
                        normalized["closed_ts"] = row.get("ts")
                    if "opened_at" in fieldnames and not normalized.get("opened_at"):
                        normalized["opened_at"] = row.get("entry_ts") or row.get("signal_ts")
                    if "usd_result" in fieldnames and not normalized.get("usd_result"):
                        normalized["usd_result"] = row.get("usd")
                    if "exit_reason" in fieldnames and not normalized.get("exit_reason"):
                        normalized["exit_reason"] = self._normalize_exit_reason(str(row.get("result") or ""))
                    if "raw_result" in fieldnames and not normalized.get("raw_result"):
                        normalized["raw_result"] = row.get("result")
                    if "result" in fieldnames and normalized.get("result") and "exit_reason" in fieldnames:
                        normalized["result"] = normalized.get("exit_reason") or normalized.get("result")
                    writer.writerow(normalized)
        except Exception:
            return path.exists()

        return True

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

        root_trade_id = self._trade_root_id(plan)
        original_sl = self._safe_float(plan.extra.get("sl_before_tp1")) or sl

        trade = self._build_trade_row(
            ts=_now(),
            symbol=plan.symbol,
            tf=plan.tf,
            world=plan.world,
            atlas_mode=plan.atlas_mode,
            side=side,
            entry=entry,
            sl=original_sl or 0.0,
            tp=tp or parcial,
            exit_price=parcial,
            result="TP1",
            lot=plan.lot,
            lot_raw=self._safe_float(plan.extra.get("lot_raw")),
            lot_capped=self._safe_float(plan.extra.get("lot_capped")),
            lot_cap_reason=plan.extra.get("lot_cap_reason"),
            score=plan.score,
            signal_ts=plan.signal_ts,
            entry_ts=plan.entry_ts,
            trade_id=self._leg_trade_id(root_trade_id, 1),
            parent_trade_id=root_trade_id,
            leg_id=1,
            is_partial=True,
            partial_percent=50.0,
            state_at_entry=str(plan.extra.get("state_at_entry") or "ENTRY"),
            tp1_price=parcial,
            tp2_price=tp or parcial,
            sl_price=original_sl,
            risk_percent=plan.risk_percent,
            opened_at=plan.entry_ts or plan.signal_ts,
        )

        with self._lock:
            self._partials_log.append(trade)
            if len(self._partials_log) > 5000:
                self._partials_log = self._partials_log[-2000:]

            live_key = self._resolve_plan_key(
                plan.symbol,
                plan.tf,
                plan.world,
                plan.atlas_mode,
            )
            live_plan = self._plans.get(live_key) if live_key else None
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

        self._upsert_trade_summary(trade)

        self._log_state_event(
            "TP1",
            symbol=trade["symbol"],
            tf=trade["tf"],
            world=plan.world,
            atlas_mode=plan.atlas_mode,
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
            score=trade["score"],
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

    def _asset_type_from_symbol(self, symbol: str) -> str:
        sym = str(symbol or "").upper().strip()

        if sym.startswith("XAU"):
            return "GOLD"

        if (
            sym.startswith("USTEC")
            or sym.startswith("NAS")
            or sym.startswith("US30")
            or sym.startswith("SPX")
            or sym.startswith("GER")
            or sym.startswith("DE40")
        ):
            return "INDICES"

        if sym.startswith("USOIL") or sym.startswith("UKOIL"):
            return "OIL"

        if (
            sym.startswith("BTC")
            or sym.startswith("ETH")
            or sym.startswith("SOL")
            or sym.startswith("XRP")
            or sym.startswith("LTC")
        ):
            return "CRYPTO"

        return "FOREX"

    def _apply_lot_cap(self, symbol: str, lot: float) -> tuple[float, Optional[str]]:
        asset_type = self._asset_type_from_symbol(symbol)

        if asset_type == "GOLD":
            capped = min(lot, 1.00)
            return capped, "XAU_CAP" if capped < lot else None

        if asset_type == "INDICES":
            capped = min(lot, 0.10)
            return capped, "INDEX_CAP" if capped < lot else None

        if asset_type == "OIL":
            capped = min(lot, 0.10)
            return capped, "OIL_CAP" if capped < lot else None

        if asset_type == "CRYPTO":
            capped = min(lot, 0.10)
            return capped, "CRYPTO_CAP" if capped < lot else None

        return lot, None

    def _symbol_spec_from_row(self, row: Dict[str, Any], symbol: str) -> Dict[str, float]:
        trade_tick_value = self._safe_float(row.get("trade_tick_value"))
        trade_tick_size = self._safe_float(row.get("trade_tick_size"))
        volume_min = self._safe_float(row.get("volume_min"))
        volume_max = self._safe_float(row.get("volume_max"))
        volume_step = self._safe_float(row.get("volume_step"))
        sym = str(symbol or "").upper()

        if trade_tick_size is None or trade_tick_size <= 0:
            if sym.startswith("XAU"):
                trade_tick_size = 0.01
            elif sym.startswith("USTEC"):
                trade_tick_size = 1.0
            elif sym.startswith("USOIL"):
                trade_tick_size = 0.01
            elif "JPY" in sym:
                trade_tick_size = 0.01
            elif sym.startswith("BTC"):
                trade_tick_size = 1.0
            else:
                trade_tick_size = 0.00001

        if trade_tick_value is None or trade_tick_value <= 0:
            if "JPY" in sym:
                trade_tick_value = 9.0
            elif sym.startswith("XAU"):
                trade_tick_value = 1.0
            elif sym.startswith("BTC"):
                trade_tick_value = 1.0
            elif sym.startswith("USTEC"):
                trade_tick_value = 1.0
            elif sym.startswith("USOIL"):
                trade_tick_value = 1.0
            else:
                trade_tick_value = 1.0

        if volume_min is None or volume_min <= 0:
            if str(symbol).upper().startswith("BTC"):
                volume_min = 0.10
            else:
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
        capped_lot, cap_reason = self._apply_lot_cap(symbol, raw_lot)
        final_lot = self._round_volume_to_step(
            volume=capped_lot,
            volume_min=volume_min,
            volume_max=volume_max,
            volume_step=volume_step,
        )

        row["lot_raw"] = round(raw_lot, 6)
        row["lot_capped"] = final_lot
        row["lot_cap_reason"] = cap_reason

        return final_lot

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

    def get_active_plan(
        self,
        symbol: str,
        tf: str | None = None,
        world: Optional[str] = None,
        atlas_mode: Optional[str] = None,
        live_price: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            if tf is not None:
                _, plan = self._get_plan(symbol, tf, world, atlas_mode)
                return self._patch_with_floating(plan.to_row_patch(), live_price) if plan else None

            matches = [
                p for p in self._plans.values()
                if self._norm_ctx(p.symbol) == self._norm_ctx(symbol)
                and (
                    not world
                    or self._norm_ctx(p.world) == self._norm_ctx(world)
                )
                and (
                    not atlas_mode
                    or self._norm_ctx(p.atlas_mode) == self._norm_ctx(atlas_mode)
                )
            ]
            if not matches:
                return None

            matches.sort(key=self._plan_sort_key)
            return self._patch_with_floating(matches[-1].to_row_patch(), live_price)

    # --------------------------------------------------
    # Freeze from scanner
    # --------------------------------------------------

    def freeze_plan(self, row: Dict[str, Any]) -> Dict[str, Any]:
        symbol = row.get("symbol")
        tf = row.get("tf")
        world, atlas_mode = self._row_context(row)

        if not symbol or not tf:
            return row

        state = str(row.get("state") or "").upper().strip()
        if state not in {"SET_UP", "ENTRY"}:
            return row

        created_plan: Optional[FrozenPlan] = None

        with self._lock:
            key = self._key(symbol, tf, world, atlas_mode)
            existing_key = self._resolve_plan_key(symbol, tf, world, atlas_mode)
            existing = self._plans.get(existing_key) if existing_key else None

            if existing and existing.state in {"SET_UP", "ENTRY", "IN_TRADE", "TP1", "TP2", "RUN"}:
                if existing_key:
                    self._set_active_plan_key(existing_key, existing)
                patch = existing.to_row_patch()
            else:
                root_trade_id = str(uuid4())
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
                    world=world,
                    atlas_mode=atlas_mode,
                    state=state,
                    entry=row.get("entry"),
                    sl=row.get("sl"),
                    tp=row.get("tp"),
                    parcial=row.get("parcial"),
                    lot=lot,
                    risk_percent=risk_percent,
                    score=row.get("score"),
                    side=row.get("side"),
                    note=self._note_with_state(state, row.get("note") or row.get("text")),
                    created_at=_now(),
                    signal_ts=_now(),
                    signal_candle_time=self._last_candle_time(row),
                    updated_at=_now(),
                    extra={
                        "trade_id": root_trade_id,
                        "parent_trade_id": root_trade_id,
                        "state_at_entry": "ENTRY" if state == "ENTRY" else None,
                        "setup_type": row.get("setup_type"),
                        "zone_low": row.get("zone_low"),
                        "zone_high": row.get("zone_high"),
                        "sweep_valid": row.get("sweep_valid"),
                        "sweep_strength": row.get("sweep_strength"),
                        "lot_raw": row.get("lot_raw"),
                        "lot_capped": row.get("lot_capped"),
                        "lot_cap_reason": row.get("lot_cap_reason"),
                        "tp1_logged": False,
                    },
                )
                self._plans[key] = plan
                self._set_active_plan_key(key, plan)
                patch = plan.to_row_patch()
                created_plan = plan

        if created_plan:
            self._log_state_event(
                "SET_UP" if created_plan.state == "SET_UP" else "ENTRY",
                symbol=created_plan.symbol,
                tf=created_plan.tf,
                world=created_plan.world,
                atlas_mode=created_plan.atlas_mode,
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
        world, atlas_mode = self._row_context(row)
        with self._lock:
            key = self._resolve_plan_key(symbol, tf, world, atlas_mode) or self._key(symbol, tf, world, atlas_mode)
            existing = self._plans.get(key)

            if existing and existing.state in {"SET_UP", "ENTRY", "IN_TRADE", "TP1", "TP2", "RUN"}:
                self._set_active_plan_key(key, existing)
                return existing.to_row_patch()

            if key in self._plans:
                old_plan = self._plans[key]
                self._clear_active_plan_key(key, old_plan)
                del self._plans[key]

            patch = {
                "world": world,
                "atlas_mode": atlas_mode,
                "state": "SIN_SETUP",
                "text": "SIN_SETUP",
                "side": None,
                "entry": None,
                "sl": None,
                "tp": None,
                "tp1": None,
                "tp1_price": None,
                "tp2": None,
                "parcial": None,
                "lot": None,
                "lot_raw": None,
                "lot_capped": None,
                "lot_cap_reason": None,
                "risk_percent": None,
                "note": None,
                "created_at": None,
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
                if row.get("note") is not None:
                    patch["note"] = self._note_with_state("SIN_SETUP", row.get("note"))
                elif row.get("text") is not None:
                    patch["note"] = self._note_with_state("SIN_SETUP", row.get("text"))

            return patch

    def _promote_setup_to_entry_key(self, plan_key: str, row: Dict[str, Any]) -> Dict[str, Any]:
        promoted_plan: Optional[FrozenPlan] = None

        with self._lock:
            plan = self._plans.get(plan_key)
            if not plan:
                return row

            if plan.state not in {"SET_UP", "ENTRY"}:
                return plan.to_row_patch()

            if plan.state == "SET_UP":
                plan.state = "ENTRY"
                plan.note = self._note_with_state(plan.state, plan.note)
                plan.entry_ts = _now()
                plan.entry_candle_time = self._last_candle_time(row)
                plan.updated_at = _now()
                plan.extra["state_at_entry"] = "ENTRY"
                promoted_plan = deepcopy(plan)

            patch = plan.to_row_patch()

        if promoted_plan:
            self._log_state_event(
                "ENTRY",
                symbol=promoted_plan.symbol,
                tf=promoted_plan.tf,
                world=promoted_plan.world,
                atlas_mode=promoted_plan.atlas_mode,
                state=promoted_plan.state,
                side=promoted_plan.side,
                entry=promoted_plan.entry,
                sl=promoted_plan.sl,
                tp=promoted_plan.tp,
                score=promoted_plan.score,
                note=promoted_plan.note,
            )

        return patch

    def promote_setup_to_entry(self, symbol: str, tf: str, row: Dict[str, Any]) -> Dict[str, Any]:
        world, atlas_mode = self._row_context(row)
        with self._lock:
            plan_key = self._resolve_plan_key(symbol, tf, world, atlas_mode)
        if not plan_key:
            return row
        return self._promote_setup_to_entry_key(plan_key, row)

    def _promote_entry_to_in_trade_key(self, plan_key: str, row: Dict[str, Any]) -> Dict[str, Any]:
        promoted_plan: Optional[FrozenPlan] = None

        with self._lock:
            plan = self._plans.get(plan_key)
            if not plan:
                return row

            if plan.state != "ENTRY":
                return plan.to_row_patch()

            last_ct = self._last_candle_time(row)
            if last_ct and plan.entry_candle_time and str(last_ct) != str(plan.entry_candle_time):
                plan.state = "IN_TRADE"
                plan.note = self._note_with_state(plan.state, plan.note)
                plan.updated_at = _now()
                promoted_plan = deepcopy(plan)

            patch = plan.to_row_patch()

        if promoted_plan:
            self._log_state_event(
                "IN_TRADE",
                symbol=promoted_plan.symbol,
                tf=promoted_plan.tf,
                world=promoted_plan.world,
                atlas_mode=promoted_plan.atlas_mode,
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
        world, atlas_mode = self._row_context(row)
        with self._lock:
            plan_key = self._resolve_plan_key(symbol, tf, world, atlas_mode)
        if not plan_key:
            return row
        return self._promote_entry_to_in_trade_key(plan_key, row)

    def _promote_in_trade_to_tp1_key(self, plan_key: str) -> Dict[str, Any]:
        promoted_plan: Optional[FrozenPlan] = None

        with self._lock:
            plan = self._plans.get(plan_key)
            if not plan:
                return {}

            if plan.state not in {"IN_TRADE", "ENTRY"}:
                return plan.to_row_patch()

            plan.state = "TP1"
            plan.note = self._note_with_state(plan.state, plan.note)
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
                world=promoted_plan.world,
                atlas_mode=promoted_plan.atlas_mode,
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

    def promote_in_trade_to_tp1(self, symbol: str, tf: str) -> Dict[str, Any]:
        with self._lock:
            plan_key = self._resolve_plan_key(symbol, tf)
        if not plan_key:
            return {}
        return self._promote_in_trade_to_tp1_key(plan_key)

    def _promote_tp1_to_tp2_key(self, plan_key: str) -> Dict[str, Any]:
        promoted_plan: Optional[FrozenPlan] = None

        with self._lock:
            plan = self._plans.get(plan_key)
            if not plan:
                return {}

            if plan.state != "TP1":
                return plan.to_row_patch()

            plan.state = "TP2"
            plan.note = self._note_with_state(plan.state, plan.note)
            plan.tp2_ts = _now()
            plan.updated_at = _now()

            promoted_plan = deepcopy(plan)
            patch = plan.to_row_patch()

        if promoted_plan:
            self._log_state_event(
                "TP2",
                symbol=promoted_plan.symbol,
                tf=promoted_plan.tf,
                world=promoted_plan.world,
                atlas_mode=promoted_plan.atlas_mode,
                state=promoted_plan.state,
                side=promoted_plan.side,
                entry=promoted_plan.entry,
                sl=promoted_plan.sl,
                tp=promoted_plan.tp,
                score=promoted_plan.score,
                note=promoted_plan.note,
            )

        return patch

    def promote_tp1_to_tp2(
        self,
        symbol: str,
        tf: str,
        world: Optional[str] = None,
        atlas_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            plan_key = self._resolve_plan_key(symbol, tf, world, atlas_mode)
        if not plan_key:
            return {}
        return self._promote_tp1_to_tp2_key(plan_key)

    def _promote_tp1_to_run_key(self, plan_key: str) -> Dict[str, Any]:
        promoted_plan: Optional[FrozenPlan] = None

        with self._lock:
            plan = self._plans.get(plan_key)
            if not plan:
                return {}

            if plan.state != "TP1":
                return plan.to_row_patch()

            plan.state = "RUN"
            plan.note = self._note_with_state(plan.state, plan.note)
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
                world=promoted_plan.world,
                atlas_mode=promoted_plan.atlas_mode,
                state=promoted_plan.state,
                side=promoted_plan.side,
                entry=promoted_plan.entry,
                sl=promoted_plan.sl,
                tp=promoted_plan.tp,
                score=promoted_plan.score,
                note=promoted_plan.note,
            )

        return patch

    def promote_tp1_to_run(
        self,
        symbol: str,
        tf: str,
        world: Optional[str] = None,
        atlas_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            plan_key = self._resolve_plan_key(symbol, tf, world, atlas_mode)
        if not plan_key:
            return {}
        return self._promote_tp1_to_run_key(plan_key)

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
                            live_plan.note = self._note_with_state(live_plan.state, live_plan.note)
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
                            world=snap.world,
                            atlas_mode=snap.atlas_mode,
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
                        closed = self._close_plan_key(key, "SL", sl)
                        if closed:
                            events.append({
                                "symbol": symbol,
                                "tf": tf,
                                "event": "SL",
                                "price": sl,
                            })
                        continue

                    if tp is not None and price >= tp:
                        closed = self._close_plan_key(key, "TP2", tp)
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
                        closed = self._close_plan_key(key, "SL", sl)
                        if closed:
                            events.append({
                                "symbol": symbol,
                                "tf": tf,
                                "event": "SL",
                                "price": sl,
                            })
                        continue

                    if tp is not None and price <= tp:
                        closed = self._close_plan_key(key, "TP2", tp)
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
                    closed = self._close_plan_key(key, "TP1_CLOSE", sl)
                    if closed:
                        events.append({
                            "symbol": symbol,
                            "tf": tf,
                            "event": "TP1_CLOSE",
                            "price": sl,
                        })
                    continue

                if side == "SELL" and sl is not None and price >= sl:
                    closed = self._close_plan_key(key, "TP1_CLOSE", sl)
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
                        closed = self._close_plan_key(key, "TP2", tp)
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
                    closed = self._close_plan_key(key, "RUN_CLOSE", sl)
                    if closed:
                        events.append({
                            "symbol": symbol,
                            "tf": tf,
                            "event": "RUN_CLOSE",
                            "price": sl,
                        })
                    continue

                if side == "SELL" and sl is not None and price >= sl:
                    closed = self._close_plan_key(key, "RUN_CLOSE", sl)
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
                        closed = self._close_plan_key(key, "TP2", tp)
                        if closed:
                            events.append({
                                "symbol": symbol,
                                "tf": tf,
                                "event": "TP2",
                                "price": tp,
                            })
                        continue

        return events

    def _close_plan_key(self, plan_key: str, result: str, exit_price: float) -> Dict[str, Any]:
        close_event_name = self._close_event_name(result)
        closed_plan: Optional[FrozenPlan] = None

        entry = 0.0
        sl = 0.0
        tp = 0.0
        side = ""
        lot = None
        score = None
        lot_raw = None
        lot_capped = None
        lot_cap_reason = None
        risk_percent = None
        trade_id = None
        parent_trade_id = None
        leg_id = None
        is_partial = None
        partial_percent = None
        state_at_entry = None
        tp1_price = None
        tp2_price = None
        sl_price = None
        opened_at = None
        closed_patch: Dict[str, Any] = {}
        symbol = ""
        tf = ""

        with self._lock:
            plan = self._plans.get(plan_key)
            if not plan:
                return {}

            if plan.state == "CLOSED":
                return plan.to_row_patch()

            symbol = plan.symbol
            tf = plan.tf
            entry = self._safe_float(plan.entry) or 0.0
            sl = self._safe_float(plan.sl) or 0.0
            tp = self._safe_float(plan.tp) or 0.0
            side = plan.side or ""
            lot = plan.lot
            score = plan.score
            lot_raw = self._safe_float(plan.extra.get("lot_raw"))
            lot_capped = self._safe_float(plan.extra.get("lot_capped"))
            lot_cap_reason = plan.extra.get("lot_cap_reason")
            risk_percent = plan.risk_percent
            root_trade_id = self._trade_root_id(plan)
            if bool(plan.extra.get("tp1_logged")):
                trade_id = self._leg_trade_id(root_trade_id, 2)
                parent_trade_id = root_trade_id
                leg_id = 2
                is_partial = True
                partial_percent = 50.0
            else:
                trade_id = root_trade_id
                parent_trade_id = root_trade_id
                leg_id = 1
                is_partial = False
                partial_percent = 100.0
            state_at_entry = str(plan.extra.get("state_at_entry") or "ENTRY")
            tp1_price = self._safe_float(plan.parcial)
            tp2_price = self._safe_float(plan.tp)
            sl_price = self._safe_float(plan.extra.get("sl_before_tp1")) or self._safe_float(plan.sl)
            opened_at = plan.entry_ts or plan.signal_ts

            plan.state = "CLOSED"
            plan.note = self._note_with_state(plan.state, plan.note)
            plan.closed_ts = _now()
            plan.close_reason = result
            plan.close_price = exit_price
            plan.updated_at = plan.closed_ts

            closed_patch = plan.to_row_patch()
            closed_plan = deepcopy(plan)

            self._clear_active_plan_key(plan_key, plan)
            del self._plans[plan_key]

        self.register_trade_result(
            symbol=symbol,
            tf=tf,
            world=closed_plan.world if closed_plan else None,
            atlas_mode=closed_plan.atlas_mode if closed_plan else None,
            side=side,
            entry=entry,
            sl=sl,
            tp=tp,
            exit_price=exit_price,
            result=result,
            lot=lot,
            lot_raw=lot_raw,
            lot_capped=lot_capped,
            lot_cap_reason=lot_cap_reason,
            score=score,
            signal_ts=closed_plan.signal_ts if closed_plan else None,
            entry_ts=closed_plan.entry_ts if closed_plan else None,
            closed_ts=closed_plan.closed_ts if closed_plan else None,
            trade_id=trade_id,
            parent_trade_id=parent_trade_id,
            leg_id=leg_id,
            is_partial=is_partial,
            partial_percent=partial_percent,
            state_at_entry=state_at_entry,
            tp1_price=tp1_price,
            tp2_price=tp2_price,
            sl_price=sl_price,
            risk_percent=risk_percent,
            opened_at=opened_at,
        )

        if closed_plan:
            try:
                entry_v = self._safe_float(closed_plan.entry) or 0.0
                sl_v = self._safe_float(closed_plan.sl) or 0.0
                tp_v = self._safe_float(closed_plan.tp) or 0.0
                close_v = self._safe_float(exit_price) or 0.0

                risk = abs(entry_v - sl_v)
                if risk > 0:
                    if str(closed_plan.side).upper() == "BUY":
                        r_multiple = (close_v - entry_v) / risk
                    else:
                        r_multiple = (entry_v - close_v) / risk
                else:
                    r_multiple = 0.0

                start_dt = _parse_ts(closed_plan.entry_ts) or _parse_ts(closed_plan.created_at)
                end_dt = _parse_ts(closed_plan.closed_ts)
                duration = int((end_dt - start_dt).total_seconds()) if start_dt and end_dt else 0

                setup_type = (
                    str((closed_plan.extra or {}).get("setup_type") or "").strip()
                    or str(closed_plan.atlas_mode or "").strip()
                    or str(closed_plan.world or "").strip()
                    or "UNKNOWN"
                )

                session = str(closed_plan.world or "UNKNOWN")

                metrics_store.record(
                    SetupMetric(
                        symbol=str(closed_plan.symbol or ""),
                        tf=str(closed_plan.tf or ""),
                        setup_type=setup_type,
                        entry=entry_v,
                        sl=sl_v,
                        tp=tp_v,
                        result=str(result),
                        r_multiple=float(r_multiple),
                        duration=duration,
                        mfe=0.0,
                        mae=0.0,
                        session=session,
                        timestamp=str(closed_plan.closed_ts or _now()),
                        world=str(closed_plan.world or ""),
                        atlas_mode=str(closed_plan.atlas_mode or ""),
                    )
                )
            except Exception:
                pass

            self._log_state_event(
                close_event_name,
                symbol=closed_plan.symbol,
                tf=closed_plan.tf,
                world=closed_plan.world,
                atlas_mode=closed_plan.atlas_mode,
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

    def _close_plan(
        self,
        symbol: str,
        tf: str,
        result: str,
        exit_price: float,
        world: Optional[str] = None,
        atlas_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            plan_key = self._resolve_plan_key(symbol, tf, world, atlas_mode)
        if not plan_key:
            return {}
        return self._close_plan_key(plan_key, result, exit_price)

    # --------------------------------------------------
    # Main merge
    # --------------------------------------------------

    def merge_row_with_freeze(self, row: Dict[str, Any]) -> Dict[str, Any]:
        symbol = row.get("symbol")
        tf = row.get("tf")
        world, atlas_mode = self._row_context(row)

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

        key = self._resolve_plan_key(symbol, tf, world, atlas_mode) or self._key(symbol, tf, world, atlas_mode)
        with self._lock:
            existing = self._plans.get(key)

        if existing is None:
            merged = self.freeze_plan(row)
            with self._lock:
                key = self._resolve_plan_key(symbol, tf, world, atlas_mode) or key
        else:
            merged = deepcopy(row)
            merged.update(existing.to_row_patch())
            with self._lock:
                if key in self._plans:
                    self._set_active_plan_key(key, self._plans[key])

        with self._lock:
            current_plan = self._plans.get(key)

        if current_plan and merged.get("state") == "SET_UP" and self._candle_touches_entry(row, current_plan.entry):
            merged.update(self._promote_setup_to_entry_key(key, row))

        with self._lock:
            current_plan = self._plans.get(key)

        if current_plan and merged.get("state") == "ENTRY":
            merged.update(self._promote_entry_to_in_trade_key(key, row))

        with self._lock:
            current_plan = self._plans.get(key)

        if current_plan and merged.get("state") in {"ENTRY", "IN_TRADE"} and self._hit_1r(current_plan, row):
            merged.update(self._promote_in_trade_to_tp1_key(key))

        with self._lock:
            current_plan = self._plans.get(key)

        if merged.get("state") == "TP1" and current_plan and self._candle_hits_tp(row, current_plan.side, current_plan.tp):
            if self._row_wants_run(row):
                merged.update(self._promote_tp1_to_run_key(key))
            else:
                merged.update(self._promote_tp1_to_tp2_key(key))

        with self._lock:
            current_plan = self._plans.get(key)

        if merged.get("state") == "TP2" and current_plan:
            tp_price = self._safe_float(current_plan.tp)
            if tp_price is not None:
                merged.update(self._close_plan_key(key, "TP2", tp_price))

        with self._lock:
            current_plan = self._plans.get(key)

        if merged.get("state") == "RUN" and current_plan and self._candle_hits_sl(row, current_plan.side, current_plan.sl):
            sl_price = self._safe_float(current_plan.sl)
            if sl_price is not None:
                merged.update(self._close_plan_key(key, "RUN_CLOSE", sl_price))

        with self._lock:
            current_plan = self._plans.get(key)

        if merged.get("state") in {"ENTRY", "IN_TRADE", "TP1"} and current_plan and self._candle_hits_sl(row, current_plan.side, current_plan.sl):
            sl_price = self._safe_float(current_plan.sl)
            if sl_price is not None:
                close_reason = "TP1_CLOSE" if str(current_plan.state).upper() == "TP1" else "SL"
                merged.update(self._close_plan_key(key, close_reason, sl_price))

        return merged

    # --------------------------------------------------
    # Closed trades / CSV
    # --------------------------------------------------

    def register_trade_result(
        self,
        symbol: str,
        tf: str,
        world: Optional[str],
        atlas_mode: Optional[str],
        side: str,
        entry: float,
        sl: float,
        tp: float,
        exit_price: float,
        result: str,
        lot: Optional[float] = None,
        lot_raw: Optional[float] = None,
        lot_capped: Optional[float] = None,
        lot_cap_reason: Optional[str] = None,
        score: Optional[float] = None,
        signal_ts: Optional[str] = None,
        entry_ts: Optional[str] = None,
        closed_ts: Optional[str] = None,
        trade_id: Optional[str] = None,
        parent_trade_id: Optional[str] = None,
        leg_id: Optional[int] = None,
        is_partial: Optional[bool] = None,
        partial_percent: Optional[float] = None,
        state_at_entry: Optional[str] = None,
        tp1_price: Optional[float] = None,
        tp2_price: Optional[float] = None,
        sl_price: Optional[float] = None,
        risk_percent: Optional[float] = None,
        opened_at: Optional[str] = None,
    ) -> None:
        trade = self._build_trade_row(
            ts=closed_ts or _now(),
            symbol=symbol,
            tf=tf,
            world=world,
            atlas_mode=atlas_mode,
            side=side,
            entry=entry,
            sl=sl,
            tp=tp,
            exit_price=exit_price,
            result=result,
            lot=lot,
            lot_raw=lot_raw,
            lot_capped=lot_capped,
            lot_cap_reason=lot_cap_reason,
            score=score,
            signal_ts=signal_ts,
            entry_ts=entry_ts,
            closed_ts=closed_ts,
            trade_id=trade_id,
            parent_trade_id=parent_trade_id,
            leg_id=leg_id,
            is_partial=is_partial,
            partial_percent=partial_percent,
            state_at_entry=state_at_entry,
            tp1_price=tp1_price,
            tp2_price=tp2_price,
            sl_price=sl_price,
            risk_percent=risk_percent,
            opened_at=opened_at,
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

        self._upsert_trade_summary(trade)

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

    def get_trade_summaries(self, limit: int = 2000) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 10000))
        with self._lock:
            items = list(self._trade_summaries.values())
        items.sort(key=lambda x: str(x.get("closed_at") or x.get("opened_at") or ""))
        return deepcopy(items[-limit:])


runtime = AtlasRuntime()
RUNTIME = runtime
