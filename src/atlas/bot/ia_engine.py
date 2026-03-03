# src/atlas/bot/ia_engine.py
from __future__ import annotations

from typing import Dict, Any, List, Optional

from atlas.bot.state import BOT_STATE
from atlas.bot.universe import DEFAULT_WATCHLIST, SPECIALISTS, is_special
from atlas.bot.resample import resample_ohlc
from atlas.bot.indicators import atr, rsi, trend_dir, last_poi
from atlas.bot.patterns import last_engulfing, last_pinbar
from atlas.bot.decision_engine import daily_has_idea, mark_daily_idea

# TFs “macro→micro” que vos pediste (IA puede mirar todos, ejecución decide por modo)
IA_TFS = ["H8", "H4", "H1", "M30", "M15", "M5"]

def get_watchlist() -> List[str]:
    eng = BOT_STATE.get("engine", {}) if isinstance(BOT_STATE.get("engine", {}), dict) else {}
    wl = eng.get("watchlist")
    if isinstance(wl, list) and wl:
        return [str(x).upper().strip() for x in wl if str(x).strip()]
    return DEFAULT_WATCHLIST[:]

def _style() -> str:
    eng = BOT_STATE.get("engine", {}) if isinstance(BOT_STATE.get("engine", {}), dict) else {}
    return str(eng.get("ia_style", "FX")).upper()

def scan_all_symbols() -> Dict[str, Any]:
    """
    Genera ideas IA para todo el watchlist.
    Guardado en BOT_STATE["ia"]["ideas"].
    Respeta 1 idea diaria por símbolo.
    """
    candles = BOT_STATE.get("candles", [])
    if not isinstance(candles, list) or len(candles) < 50:
        return {"ok": False, "error": "not_enough_candles"}

    wl = get_watchlist()
    style = _style()

    ideas = {}
    for sym in wl:
        idea = analyze_symbol(sym, candles, style=style)
        if idea:
            ideas[sym] = idea

    ia = BOT_STATE.setdefault("ia", {})
    ia["style"] = style
    ia["watchlist"] = wl
    ia["ideas"] = ideas
    ia["ts"] = _now()
    return {"ok": True, "count": len(ideas), "style": style}

def analyze_symbol(symbol: str, candles_m1: List[dict], style: str = "FX") -> Optional[Dict[str, Any]]:
    """
    IA no “inventa”: arma idea si detecta alineación macro→micro + POI + patrón.
    NO manda orden real. Solo sugiere parámetros (más adelante se conecta a MT5).
    """
    symbol = str(symbol).upper().strip()
    if not symbol:
        return None

    # 1 idea diaria por símbolo (silencio)
    if daily_has_idea(symbol):
        return None

    # Resample por TFs
    frames = {}
    for tf in IA_TFS:
        frames[tf] = resample_ohlc(candles_m1, tf)
        if len(frames[tf]) < 40:
            return None

    # Macro dirección (H8/H4)
    macro_dir_h8 = trend_dir(frames["H8"], 60)
    macro_dir_h4 = trend_dir(frames["H4"], 80)
    macro_dir = macro_dir_h8 if macro_dir_h8 != "FLAT" else macro_dir_h4

    # Micro dirección (M15/M5)
    micro_dir = trend_dir(frames["M15"], 60)
    micro_dir_m5 = trend_dir(frames["M5"], 80)

    # POI de H1 (techo/piso)
    poi_hi, poi_lo = last_poi(frames["H1"], 80)
    if poi_hi is None or poi_lo is None:
        return None

    # Indicadores y patrones (en M5)
    rsi_m5 = rsi(frames["M5"], 14)
    atr_m5 = atr(frames["M5"], 14)
    eng = last_engulfing(frames["M5"])
    pin = last_pinbar(frames["M5"])

    last_price = float(frames["M5"][-1]["close"])
    if atr_m5 is None:
        return None

    # --------- Especialización por activo ---------
    spec = SPECIALISTS.get(symbol, {})
    is_gold = (symbol == "XAUUSD")
    is_nas = (symbol == "NAS100")

    # Estilo: FX = paciencia y confirmación; SCALPING = gatillo rápido en POI
    style = style.upper().strip()
    if style not in ("FX", "SCALPING"):
        style = "FX"

    # “Profesional”: no operar contra macro salvo que haya reversión fuerte (por ahora: no)
    if macro_dir in ("UP", "DOWN") and micro_dir != "FLAT":
        if macro_dir != micro_dir and macro_dir != micro_dir_m5:
            # micro contradice macro: evitar ideas dudosas
            return None

    # Cercanía a POI (latigazo suele aparecer ahí)
    near_hi = abs(last_price - float(poi_hi)) <= atr_m5 * (1.0 if (is_gold or is_nas) else 0.8)
    near_lo = abs(last_price - float(poi_lo)) <= atr_m5 * (1.0 if (is_gold or is_nas) else 0.8)

    # Direccion propuesta
    direction = None
    poi = None

    if macro_dir == "UP":
        direction = "buy"
        poi = poi_lo  # continuidad compra desde piso POI
        if not near_lo:
            # en FX pedimos que esté cerca del POI para idea; en scalping toleramos más si hay patrón
            if style == "FX":
                return None
    elif macro_dir == "DOWN":
        direction = "sell"
        poi = poi_hi
        if not near_hi:
            if style == "FX":
                return None
    else:
        # si macro FLAT, no idea
        return None

    # Confirmaciones mínimas (sin score): patrón de vela o RSI extremo o ambos
    confirmations = []
    if eng:
        confirmations.append(eng)
    if pin:
        confirmations.append(pin)
    if rsi_m5 is not None:
        if direction == "buy" and rsi_m5 <= 35:
            confirmations.append("RSI_BAJO")
        if direction == "sell" and rsi_m5 >= 65:
            confirmations.append("RSI_ALTO")

    if style == "FX":
        # FX exige al menos 2 confirmaciones
        if len(confirmations) < 2:
            return None
    else:
        # SCALPING exige al menos 1 confirmación + cerca del POI
        if len(confirmations) < 1:
            return None
        if direction == "buy" and not near_lo:
            return None
        if direction == "sell" and not near_hi:
            return None

    # Parámetros base (no ejecución)
    # SL: por ATR (más largo en FX, más corto en scalping). Oro/Nasdaq ajusta agresivo.
    atr_mult_sl = 1.8 if style == "FX" else 1.1
    if is_gold or is_nas:
        atr_mult_sl = atr_mult_sl * 0.9

    sl_dist = atr_m5 * atr_mult_sl

    entry = last_price
    sl = entry - sl_dist if direction == "buy" else entry + sl_dist

    # TP: proyección simple por “ondas” (multiplicador)
    rr = 1.5 if style == "FX" else 1.0
    if is_gold:
        rr = rr + 0.2  # oro suele dar recorrido si está alineado
    if is_nas:
        rr = rr + 0.1

    tp1 = entry + sl_dist * rr if direction == "buy" else entry - sl_dist * rr

    # Parcial recomendado (dispara aviso luego cuando price alcance algo, se cablea luego)
    partial_at = entry + (tp1 - entry) * (0.45 if (is_gold or is_nas) else 0.5)

    # Confianza textual (sin score)
    confidence = "ALTA" if len(confirmations) >= 3 else "MEDIA"

    idea = {
        "symbol": symbol,
        "style": style,
        "direction": direction,
        "macro_dir": macro_dir,
        "poi": {"high": poi_hi, "low": poi_lo, "chosen": poi},
        "confirmations": confirmations,
        "confidence": confidence,
        "entry": round(entry, 5),
        "sl": round(sl, 5),
        "tp1": round(tp1, 5),
        "partial_at": round(partial_at, 5),
        "notes": _special_notes(symbol),
        "tf_stack": IA_TFS,
    }

    # Registrar “idea diaria” para no spamear
    summary = f"IA {style} {direction} (macro {macro_dir}) conf:{confidence}"
    mark_daily_idea(symbol, "IA", summary, payload=idea)

    return idea

def _special_notes(symbol: str) -> str:
    s = SPECIALISTS.get(symbol)
    if not s:
        return ""
    return s.get("notes", "")

def _now() -> str:
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")