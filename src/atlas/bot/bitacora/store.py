from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

# Archivo único de bitácora (jsonl)
DEFAULT_PATH = os.path.abspath(os.path.join(os.getcwd(), "atlas_bitacora.jsonl"))


def _now_ms() -> int:
    return int(time.time() * 1000)


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def get_store_path(custom_path: Optional[str] = None) -> str:
    return custom_path or os.getenv("ATLAS_BITACORA_PATH") or DEFAULT_PATH


def append_row(row: Dict[str, Any], path: Optional[str] = None) -> Dict[str, Any]:
    """
    Append de una línea json a archivo .jsonl
    """
    p = get_store_path(path)
    _ensure_dir(p)

    row = dict(row or {})
    row.setdefault("id", str(uuid.uuid4()))
    row.setdefault("ts_ms", _now_ms())

    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return row


def read_rows(limit: int = 100, path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Lee las últimas N filas (desde el final del archivo).
    """
    p = get_store_path(path)
    if not os.path.exists(p):
        return []

    limit = max(1, min(int(limit or 100), 5000))

    with open(p, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    tail = lines[-limit:]
    out: List[Dict[str, Any]] = []
    for ln in tail:
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue

    return out


def wipe(path: Optional[str] = None) -> Dict[str, Any]:
    p = get_store_path(path)
    if os.path.exists(p):
        os.remove(p)
    return {"ok": True, "path": p}


# ----------------------------
# Helpers
# ----------------------------

def _norm(s: Any) -> str:
    return str(s or "").strip()


def _upper(s: Any) -> str:
    return _norm(s).upper()


def _float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _classify_trade(result_pts: float) -> str:
    if result_pts > 0:
        return "WIN"
    if result_pts < 0:
        return "LOSS"
    return "BE"


# ----------------------------
# Trades helpers (OPEN/CLOSE)
# ----------------------------

def _make_key(world: str, symbol: str, tf: str) -> Tuple[str, str, str]:
    return (_upper(world), _norm(symbol), _upper(tf))


def get_open_trade(world: str, symbol: str, tf: str, path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retorna el último OPEN que no tenga CLOSE correspondiente (por trade_id) para (world,symbol,tf).
    """
    rows = read_rows(limit=2000, path=path)
    key = _make_key(world, symbol, tf)

    closed_ids = set()
    for r in rows:
        ev = _upper(r.get("event"))
        trade_id = _norm(r.get("trade_id"))
        if ev == "CLOSE" and trade_id:
            closed_ids.add(trade_id)

    # buscar el OPEN más reciente no cerrado
    for r in reversed(rows):
        ev = _upper(r.get("event"))
        trade_id = _norm(r.get("trade_id"))
        w = _upper(r.get("world"))
        sym = _norm(r.get("symbol"))
        tframe = _upper(r.get("tf"))

        if (w, sym, tframe) != key:
            continue

        if ev == "OPEN" and trade_id and trade_id not in closed_ids:
            data = r.get("data") or {}
            return {
                "id": _norm(r.get("id")),
                "trade_id": trade_id,
                "world": w,
                "symbol": sym,
                "tf": tframe,
                "source": _norm(r.get("source")),
                "note": _norm(r.get("note")),
                "ts_ms": int(r.get("ts_ms") or 0),
                "status": "OPEN",
                "side": _upper(data.get("side")),
                "entry": _float(data.get("entry")),
                "sl": _float(data.get("sl")),
                "tp": _float(data.get("tp")),
            }

    return None


def open_trade(
    world: str,
    symbol: str,
    tf: str,
    side: str,
    entry: float,
    sl: float,
    tp: float,
    note: str = "",
    source: str = "atlas",
    path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Abre trade si NO hay trade open para (world,symbol,tf).
    """
    if get_open_trade(world, symbol, tf, path=path):
        return {"ok": True, "skipped": True, "reason": "already_open"}

    trade_id = str(uuid.uuid4())[:8]
    row = append_row(
        {
            "event": "OPEN",
            "trade_id": trade_id,
            "world": _upper(world),
            "symbol": _norm(symbol),
            "tf": _upper(tf),
            "source": _norm(source),
            "note": _norm(note) or "auto-open",
            "data": {
                "side": _upper(side),
                "entry": float(entry),
                "sl": float(sl),
                "tp": float(tp),
            },
        },
        path=path,
    )
    return {"ok": True, "trade_id": trade_id, "row": row}


def close_trade(
    trade_id: str,
    exit_price: float,
    reason: str = "TP",
    note: str = "",
    path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Cierra trade por trade_id (agrega fila CLOSE).
    Calcula result_pts y r de forma simple:
      pts = (entry - exit) para SELL, (exit - entry) para BUY
      r = pts / abs(entry - sl)
    """
    rows = read_rows(limit=5000, path=path)

    open_row: Optional[Dict[str, Any]] = None
    for r in reversed(rows):
        if _upper(r.get("event")) == "OPEN" and _norm(r.get("trade_id")) == _norm(trade_id):
            open_row = r
            break

    if not open_row:
        return {"ok": False, "error": "open_not_found"}

    data = open_row.get("data") or {}
    side = _upper(data.get("side"))
    entry = _float(data.get("entry")) or 0.0
    sl = _float(data.get("sl")) or 0.0

    if side == "SELL":
        result_pts = float(entry - exit_price)
    else:
        result_pts = float(exit_price - entry)

    denom = abs(entry - sl) if abs(entry - sl) > 0 else None
    rr = (result_pts / denom) if denom else None

    cls = _classify_trade(result_pts)

    row = append_row(
        {
            "event": "CLOSE",
            "trade_id": _norm(trade_id),
            "reason": _upper(reason),
            "note": _norm(note) or "auto-close",
            "data": {
                "exit_price": float(exit_price),
                "result_pts": float(result_pts),
                "r": (float(rr) if rr is not None else None),
                "class": cls,
            },
        },
        path=path,
    )
    return {"ok": True, "row": row}


# ----------------------------
# Stats LEGACY (para /api/bitacora/stats)
# ----------------------------

def compute_stats(limit: int = 100, path: Optional[str] = None) -> Dict[str, Any]:
    """
    Compatibilidad: esta función EXISTÍA y la usa atlas.api.routes.bitacora
    Hace stats generales mirando CLOSE (no filtra por world/symbol/tf).
    """
    rows = read_rows(limit=limit, path=path)

    total_rows = len(rows)
    closes = [r for r in rows if _upper(r.get("event")) == "CLOSE"]
    total_closed = len(closes)

    wins = 0
    losses = 0
    breakeven = 0

    gross_profit = 0.0
    gross_loss = 0.0
    sum_r = 0.0
    count_r = 0

    for r in closes:
        data = r.get("data") or {}
        result_pts = float(data.get("result_pts", 0) or 0)
        rr = data.get("r", None)

        if rr is not None:
            try:
                sum_r += float(rr)
                count_r += 1
            except Exception:
                pass

        cls = _upper(data.get("class") or "")
        if not cls:
            cls = _classify_trade(result_pts)

        if cls == "WIN":
            wins += 1
            gross_profit += max(0.0, result_pts)
        elif cls == "LOSS":
            losses += 1
            gross_loss += abs(min(0.0, result_pts))
        else:
            breakeven += 1

    net_pts = gross_profit - gross_loss
    winrate = (wins / total_closed * 100.0) if total_closed else 0.0
    avg_r = (sum_r / count_r) if count_r else 0.0

    profit_factor = None
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss

    return {
        "limit": int(limit),
        "total_rows": total_rows,
        "total_closed": total_closed,
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven,
        "winrate_pct": round(winrate, 2),
        "gross_profit_pts": round(gross_profit, 2),
        "gross_loss_pts": round(gross_loss, 2),
        "net_pts": round(net_pts, 2),
        "avg_r": round(avg_r, 4),
        "profit_factor": (round(float(profit_factor), 4) if profit_factor is not None else None),
        "path": get_store_path(path),
    }


# ----------------------------
# Stats FILTRADOS (C: world+symbol+tf)
# ----------------------------

def compute_stats_filtered(world: str, symbol: str, tf: str, limit: int = 500, path: Optional[str] = None) -> Dict[str, Any]:
    """
    Stats SOLO para (world,symbol,tf) usando los últimos N registros del archivo.
    Reconstruye trades cerrados mirando CLOSE + su OPEN asociado.
    """
    world_u = _upper(world)
    symbol_s = _norm(symbol)
    tf_u = _upper(tf)

    rows_all = read_rows(limit=max(1000, int(limit) * 10), path=path)
    rows = rows_all[-max(1, min(int(limit or 500), 5000)):]  # ventana final

    opens: Dict[str, Dict[str, Any]] = {}
    closes: List[Dict[str, Any]] = []

    for r in rows:
        ev = _upper(r.get("event"))
        tid = _norm(r.get("trade_id"))

        if ev == "OPEN":
            w = _upper(r.get("world"))
            sym = _norm(r.get("symbol"))
            tframe = _upper(r.get("tf"))
            if (w, sym, tframe) == (world_u, symbol_s, tf_u) and tid:
                opens[tid] = r

        if ev == "CLOSE" and tid:
            closes.append(r)

    closed_pairs: List[Dict[str, Any]] = []
    for c in closes:
        tid = _norm(c.get("trade_id"))
        if tid and tid in opens:
            closed_pairs.append({"open": opens[tid], "close": c})

    total_closed = len(closed_pairs)
    wins = losses = breakeven = 0
    gross_profit = 0.0
    gross_loss = 0.0
    sum_r = 0.0
    count_r = 0

    for item in closed_pairs:
        cdata = (item["close"].get("data") or {})
        result_pts = float(cdata.get("result_pts") or 0.0)
        rr = cdata.get("r", None)
        cls = _upper(cdata.get("class") or "")

        if rr is not None:
            try:
                sum_r += float(rr)
                count_r += 1
            except Exception:
                pass

        if not cls:
            cls = _classify_trade(result_pts)

        if cls == "WIN":
            wins += 1
            gross_profit += max(0.0, result_pts)
        elif cls == "LOSS":
            losses += 1
            gross_loss += abs(min(0.0, result_pts))
        else:
            breakeven += 1

    net_pts = gross_profit - gross_loss
    winrate = (wins / total_closed * 100.0) if total_closed else 0.0
    avg_r = (sum_r / count_r) if count_r else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None

    return {
        "scope": {"world": world_u, "symbol": symbol_s, "tf": tf_u},
        "limit": int(limit),
        "total_rows_scanned": len(rows),
        "total_closed": total_closed,
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven,
        "winrate_pct": round(winrate, 2),
        "gross_profit_pts": round(gross_profit, 2),
        "gross_loss_pts": round(gross_loss, 2),
        "net_pts": round(net_pts, 2),
        "avg_r": round(avg_r, 4),
        "profit_factor": (round(float(profit_factor), 4) if profit_factor is not None else None),
        "path": get_store_path(path),
    }