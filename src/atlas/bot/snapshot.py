# src/atlas/bot/snapshot.py

from atlas.bot.state import BOT_STATE, PERF
from atlas.bot.context import build_context
from atlas.bot.structure import build_structure
from atlas.bot.decision_engine import decide
from atlas.bot.ia_engine import scan_all_symbols
from atlas.bot.atlas_ia import run_atlas_ia


def _as_list(x):
    return x if isinstance(x, list) else []


def _as_dict(x):
    return x if isinstance(x, dict) else {}


def build_bot_snapshot():
    """
    Snapshot unificado del BOT.
    Compatible con:
    - UI PRO
    - Motor clásico (decide)
    - ATLAS_IA (islas Scalping/Forex)
    """

    # -----------------------------
    # ESTADO BASE
    # -----------------------------

    engine = _as_dict(BOT_STATE.get("engine"))
    BOT_STATE["engine"] = engine

    candles = _as_list(BOT_STATE.get("candles"))
    BOT_STATE["candles"] = candles

    logs = _as_list(BOT_STATE.get("logs"))
    BOT_STATE["logs"] = logs

    universe = _as_dict(BOT_STATE.get("universe"))
    BOT_STATE["universe"] = universe

    board = _as_dict(BOT_STATE.get("board"))
    BOT_STATE["board"] = board

    config = _as_dict(BOT_STATE.get("config"))
    BOT_STATE["config"] = config

    # -----------------------------
    # CONTEXTO + ESTRUCTURA
    # -----------------------------

    context = build_context()
    structure = build_structure()

    # -----------------------------
    # IA SCAN (si está activa)
    # -----------------------------

    if bool(engine.get("ia_on", False)):
        scan_all_symbols()

    tick = int(engine.get("tick", BOT_STATE.get("tick", 0) or 0))

    status = {
        "bot": BOT_STATE.get("bot", "paused"),
        "symbol": BOT_STATE.get("symbol", "XAUUSDz"),
        "tf": BOT_STATE.get("tf_exec", "M1"),
        "tick": tick,
    }

    base_snapshot = {
        "status": status,
        "engine": engine,
        "candles": candles,
        "context": context,
        "structure": structure,
        "logs": logs,
        "universe": universe,
        "board": board,
        "config": config,
    }

    # -----------------------------
    # DECISION ENGINE CLÁSICO
    # -----------------------------

    decision = decide(base_snapshot)

    fibonacci = (structure or {}).get("fibonacci")
    trigger = (structure or {}).get("trigger")

    # -----------------------------
    # ATLAS IA (NUEVO MOTOR)
    # -----------------------------

    atlas_mode = engine.get("atlas_mode", "SCALPING")

    # Construir mapa de velas por símbolo desde universe
    candles_by_symbol = {}

    for sym, data in universe.items():
        if isinstance(data, dict):
            sym_candles = _as_list(data.get("candles"))
            candles_by_symbol[sym] = sym_candles

    # Fallback: si universe está vacío, usar velas actuales
    if not candles_by_symbol:
        current_symbol = status.get("symbol")
        candles_by_symbol[current_symbol] = candles

    atlas_payload = run_atlas_ia(
        candles_by_symbol=candles_by_symbol,
        atlas_mode=atlas_mode,
    )

    # -----------------------------
    # SNAPSHOT FINAL
    # -----------------------------

    final_snapshot = {
        **base_snapshot,
        "tick": tick,
        "fibonacci": fibonacci,
        "trigger": trigger,
        "decision": decision,
        "analysis": atlas_payload.get("analysis", {}),
        "ui": atlas_payload.get("ui", decision.get("ui", {})),
        "daily": BOT_STATE.get("daily", {}),
        "ia": BOT_STATE.get("ia", {}),
        "last_decision": decision.get("state", "NO_TRADE"),
        "debug": {
            "id": BOT_STATE.get("_id"),
            "ver": BOT_STATE.get("_ver", 0),
        },
    }

    return final_snapshot
