from __future__ import annotations

from typing import Any, Dict, List, Tuple

STATE_PRIORITY = {
    "RUN": 70,
    "TP2": 60,
    "TP1": 50,
    "IN_TRADE": 40,
    "ENTRY": 30,
    "SET_UP": 20,
    "SIN_SETUP": 10,
    "CLOSED": 0,
}


def _normalize_state(state: Any) -> str:
    s = str(state or "").upper().strip()

    if s == "WAIT":
        return "SIN_SETUP"

    if s in {"WAIT_GATILLO", "SIGNAL", "SETUP"}:
        return "SET_UP"

    valid = {
        "SIN_SETUP",
        "SET_UP",
        "ENTRY",
        "IN_TRADE",
        "TP1",
        "TP2",
        "RUN",
        "CLOSED",
    }

    if s in valid:
        return s

    return "SIN_SETUP"


def _sort_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def key_fn(row: Dict[str, Any]):
        state = _normalize_state(row.get("state"))
        score = float(row.get("score") or 0)
        return (STATE_PRIORITY.get(state, 0), score)

    return sorted(rows, key=key_fn, reverse=True)


def _relax_row_for_mode(row: Dict[str, Any], atlas_mode: str) -> Dict[str, Any]:
    """
    Relaja un poco la lógica visual del scanner sin tocar el motor interno.
    Esto sirve para que M5 y FOREX no aparezcan muertos cuando sí hay contexto.
    """
    clean = dict(row)
    state = _normalize_state(clean.get("state"))
    score = float(clean.get("score") or 0)
    rr = float(clean.get("rr") or 0)
    side = clean.get("side")
    entry = clean.get("entry")
    sl = clean.get("sl")
    tp = clean.get("tp")

    has_plan = entry is not None and sl is not None and tp is not None
    mode = str(atlas_mode or "").upper().strip()

    if mode == "SCALPING_M1":
        # M1 más suelto: score 8 mantiene setup claro
        if state == "SIN_SETUP" and has_plan and score >= 8:
            clean["state"] = "SET_UP"
            if side is None:
                clean["side"] = clean.get("action") if clean.get("action") in {"BUY", "SELL"} else None

    elif mode == "SCALPING_M5":
        # M5 necesita respirar: si hay plan y score 7+ lo mostramos
        if state == "SIN_SETUP" and has_plan and score >= 7:
            clean["state"] = "SET_UP"
            if side is None:
                clean["side"] = clean.get("action") if clean.get("action") in {"BUY", "SELL"} else None

    elif mode == "FOREX":
        # Forex: si hay estructura razonable, mostrar SET_UP aunque no llegue a ENTRY
        if state == "SIN_SETUP" and has_plan and (score >= 6 or rr >= 1.2):
            clean["state"] = "SET_UP"
            if score < 7:
                clean["score"] = 7

    return clean


def _run_mode_for_symbol(
    atlas_mode: str,
    symbol: str,
    candles: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    mode = str(atlas_mode or "").upper().strip()

    if mode == "SCALPING_M1":
        from atlas.bot.atlas_ia_m1.engine import run_world_rows
        return run_world_rows(
            world="ATLAS_IA",
            tf="M1",
            symbols=[symbol],
            candles_by_symbol={symbol: {"candles": candles}},
        )

    if mode == "SCALPING_M5":
        from atlas.bot.atlas_ia_m5.engine import run_world_rows
        return run_world_rows(
            world="ATLAS_IA",
            tf="M5",
            symbols=[symbol],
            candles_by_symbol={symbol: {"candles": candles}},
        )

    from atlas.bot.atlas_ia.forex_engine import eval_forex
    analysis, ui = eval_forex(
        {"symbol": symbol, "candles": candles},
        {"symbol": symbol, "tf": "H1"},
    )

    rows: List[Dict[str, Any]] = []
    if isinstance(ui, dict):
        maybe_rows = ui.get("rows", [])
        if isinstance(maybe_rows, list):
            rows = maybe_rows

    return analysis, rows


def scan_opportunities(
    atlas_mode: str,
    candles_by_symbol: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    analyses: List[Dict[str, Any]] = []
    mode = str(atlas_mode or "").upper().strip()

    for symbol, payload in candles_by_symbol.items():
        try:
            candles = payload.get("candles", [])
            analysis, raw_rows = _run_mode_for_symbol(mode, symbol, candles)

            if isinstance(analysis, dict):
                analyses.append(analysis)
            else:
                analyses.append({"symbol": symbol})

            if not isinstance(raw_rows, list):
                raw_rows = []

            for row in raw_rows:
                if not isinstance(row, dict):
                    continue

                clean_row = dict(row)
                clean_row["symbol"] = clean_row.get("symbol") or symbol
                clean_row["state"] = _normalize_state(clean_row.get("state"))
                clean_row["score"] = float(clean_row.get("score") or 0)

                if "tf" not in clean_row or not clean_row.get("tf"):
                    if mode == "SCALPING_M1":
                        clean_row["tf"] = "M1"
                    elif mode == "SCALPING_M5":
                        clean_row["tf"] = "M5"
                    else:
                        clean_row["tf"] = "H1"

                clean_row = _relax_row_for_mode(clean_row, mode)
                rows.append(clean_row)

        except Exception as e:
            rows.append({
                "symbol": symbol,
                "tf": "M1" if mode == "SCALPING_M1" else "M5" if mode == "SCALPING_M5" else "H1",
                "score": 0,
                "state": "SIN_SETUP",
                "side": None,
                "entry": None,
                "sl": None,
                "tp": None,
                "parcial": None,
                "lot": None,
                "risk_percent": 0.0,
                "rr": 0.0,
                "sweep_valid": False,
                "note": f"scanner_error: {repr(e)}",
            })

    sorted_rows = _sort_rows(rows)

    top_entry = next((r for r in sorted_rows if _normalize_state(r.get("state")) == "ENTRY"), None)
    top_setup = next((r for r in sorted_rows if _normalize_state(r.get("state")) == "SET_UP"), None)
    top_live = next(
        (r for r in sorted_rows if _normalize_state(r.get("state")) in {"IN_TRADE", "TP1", "TP2", "RUN"}),
        None,
    )

    summary = {
        "mode": mode,
        "total_symbols": len(candles_by_symbol),
        "total_rows": len(sorted_rows),
        "entries": sum(1 for r in sorted_rows if _normalize_state(r.get("state")) == "ENTRY"),
        "setups": sum(1 for r in sorted_rows if _normalize_state(r.get("state")) == "SET_UP"),
        "live": sum(1 for r in sorted_rows if _normalize_state(r.get("state")) in {"IN_TRADE", "TP1", "TP2", "RUN"}),
        "top_entry": top_entry,
        "top_setup": top_setup,
        "top_live": top_live,
    }

    return {
        "ok": True,
        "summary": summary,
        "rows": sorted_rows,
        "analyses": analyses,
    }