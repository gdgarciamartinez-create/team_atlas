from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple


# =========================
# Config
# =========================
BASE_SYMBOLS = [
    "XAUUSDz",
    "EURUSDz",
    "GBPUSDz",
    "USDJPYz",
    "AUDUSDz",
    "NZDUSDz",
    "NAS100z",
]

TIMEFRAMES = ["M1", "M5"]

ENABLE_PRESESION_UNIVERSE = True
PRESESION_TTL_SEC = 60
PRESESION_MAX_SYMBOLS = 80

# filtros de “solo mejores”
DEFAULT_LIMIT = 10
DEFAULT_MIN_ROWS = 6
DEFAULT_MIN_SCORE = 70


def _safe_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def _rank_key(s: Dict[str, Any]) -> Tuple:
    score = int(s.get("score") or 0)
    st = str(s.get("state") or "WAIT").upper()
    state_bonus = {"SIGNAL": 3, "WAIT_GATILLO": 2, "WAIT": 1}.get(st, 0)
    return (score, state_bonus)


def _build_symbol_universe() -> List[str]:
    symbols = list(BASE_SYMBOLS)

    if ENABLE_PRESESION_UNIVERSE:
        try:
            from atlas.bot.presesion_universe import build_presesion_universe
            res = build_presesion_universe(ttl_sec=PRESESION_TTL_SEC, max_symbols=PRESESION_MAX_SYMBOLS)
            if res.get("ok") and res.get("symbols"):
                symbols.extend(list(res["symbols"]))
        except Exception:
            # si falla, no rompe: seguimos con base
            pass

    return _dedupe_keep_order(symbols)


def analyze_pair(symbol: str, tf: str) -> Dict[str, Any]:
    # ---------- GET CANDLES ----------
    try:
        from atlas.providers.mt5_provider import get_candles
        payload = get_candles(symbol=symbol, tf=tf, count=200) or {}
        candles = payload.get("candles") or []
    except Exception as e:
        return {"symbol": symbol, "tf": tf, "score": 0, "state": "WAIT", "reason": f"MT5_FAIL {e}"}

    if not isinstance(candles, list) or len(candles) < 10:
        return {"symbol": symbol, "tf": tf, "score": 0, "state": "WAIT", "reason": "NO_CANDLES"}

    # ---------- ENGINE ----------
    analysis = {}
    try:
        from atlas.bot.atlas_ia.engine import eval_atlas_ia
        try:
            analysis = eval_atlas_ia(candles=candles, symbol=symbol, tf=tf) or {}
        except TypeError:
            analysis = eval_atlas_ia(candles, symbol, tf) or {}
    except Exception as e:
        analysis = {"status": "ENGINE_FAIL", "reason": str(e)}

    # ---------- SCORE ----------
    score = 0
    try:
        from atlas.bot.score_engine import calculate_score
        score = int(calculate_score(analysis) or 0)
    except Exception:
        score = 0

    # ---------- STATE ----------
    state = "WAIT"
    try:
        from atlas.bot.state_machine import update_state
        state = update_state(symbol, tf, analysis, score)
    except Exception:
        state = "WAIT"

    scenario: Dict[str, Any] = {
        "symbol": symbol,
        "tf": tf,
        "score": score,
        "state": state,
        "entry": None,
        "sl": None,
        "tp": None,
        "lot": None,
    }

    # ---------- SIGNAL ----------
    if str(state).upper() == "SIGNAL":
        entry = _safe_float(analysis.get("entry"))
        sl = _safe_float(analysis.get("sl"))
        tp = _safe_float(analysis.get("tp"))

        scenario["entry"] = entry
        scenario["sl"] = sl
        scenario["tp"] = tp

        risk = 1.5 if score >= 90 else 1.0

        try:
            from atlas.bot.risk_engine import calculate_lot
            if entry is not None and sl is not None:
                scenario["lot"] = calculate_lot(entry, sl, risk_percent=risk, account=10000)
                scenario["risk"] = risk
        except Exception:
            pass

        # bitácora
        try:
            from atlas.bot.trade_logger import log_trade
            log_trade(scenario)
        except Exception:
            pass

        # Telegram solo SIGNAL
        try:
            from atlas.bot.telegram_notifier import send_signal
            send_signal(scenario)
        except Exception:
            pass

    return scenario


def run_scanner(
    limit: int = DEFAULT_LIMIT,
    min_rows: int = DEFAULT_MIN_ROWS,
    min_score: int = DEFAULT_MIN_SCORE
) -> List[Dict[str, Any]]:

    universe = _build_symbol_universe()

    tasks = []
    scenarios: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        for symbol in universe:
            for tf in TIMEFRAMES:
                tasks.append(executor.submit(analyze_pair, symbol, tf))

        for future in as_completed(tasks):
            try:
                r = future.result()
                if r:
                    scenarios.append(r)
            except Exception:
                continue

    scenarios.sort(key=_rank_key, reverse=True)

    # 1) SIGNAL siempre visible
    signals = [s for s in scenarios if str(s.get("state")).upper() == "SIGNAL"]

    # 2) buenos por score
    good = [s for s in scenarios if int(s.get("score") or 0) >= int(min_score or 70)]
    good.sort(key=_rank_key, reverse=True)

    if good:
        merged = []
        seen = set()
        for s in signals + good:
            k = (s.get("symbol"), s.get("tf"))
            if k not in seen:
                merged.append(s)
                seen.add(k)
        return merged[: max(1, int(limit or 10))]

    # fallback: top min_rows para no dejar UI vacía
    return scenarios[: max(1, int(min_rows or 6))]