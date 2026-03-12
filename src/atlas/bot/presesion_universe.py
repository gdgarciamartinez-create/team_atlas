from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


_CACHE: Dict[str, Any] = {
    "ts": 0,
    "symbols": [],
    "reason": ""
}

DEFAULT_TTL_SEC = 60


def _now() -> int:
    return int(time.time())


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def _normalize_symbol(s: Any) -> Optional[str]:
    if not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    return s


def _extract_symbols(obj: Any) -> List[str]:
    """
    Acepta múltiples formas:
    - ["EURUSDz", ...]
    - {"symbols":[...]}
    - {"data":[{"name":"EURUSDz"}, ...]}
    """
    out: List[str] = []

    if isinstance(obj, list):
        for x in obj:
            if isinstance(x, str):
                sx = _normalize_symbol(x)
                if sx:
                    out.append(sx)
            elif isinstance(x, dict):
                # casos posibles: {"name": "..."} o {"symbol":"..."}
                sx = _normalize_symbol(x.get("name") or x.get("symbol"))
                if sx:
                    out.append(sx)

    if isinstance(obj, dict):
        if "symbols" in obj and isinstance(obj["symbols"], list):
            out.extend(_extract_symbols(obj["symbols"]))
        if "data" in obj and isinstance(obj["data"], list):
            out.extend(_extract_symbols(obj["data"]))
        if "result" in obj and isinstance(obj["result"], list):
            out.extend(_extract_symbols(obj["result"]))

    return _dedupe_keep_order(out)


def _fetch_mt5_symbols() -> Dict[str, Any]:
    """
    Intenta obtener símbolos desde el provider.
    Si no existe get_symbols(), no rompe: devuelve ok False.
    """
    # 1) Provider directo
    try:
        from atlas.providers.mt5_provider import get_symbols  # type: ignore
        res = get_symbols()  # puede devolver list o dict
        return {"ok": True, "raw": res, "src": "atlas.providers.mt5_provider.get_symbols"}
    except Exception as e1:
        # 2) Intento alternativo: a veces el provider expone symbols() o list_symbols()
        try:
            from atlas.providers import mt5_provider  # type: ignore
            if hasattr(mt5_provider, "symbols"):
                res = mt5_provider.symbols()
                return {"ok": True, "raw": res, "src": "atlas.providers.mt5_provider.symbols"}
            if hasattr(mt5_provider, "list_symbols"):
                res = mt5_provider.list_symbols()
                return {"ok": True, "raw": res, "src": "atlas.providers.mt5_provider.list_symbols"}
        except Exception as e2:
            return {"ok": False, "raw": None, "src": "NONE", "error": f"{type(e1).__name__}:{e1} | {type(e2).__name__}:{e2}"}

    return {"ok": False, "raw": None, "src": "NONE", "error": "no_provider"}


def build_presesion_universe(
    *,
    ttl_sec: int = DEFAULT_TTL_SEC,
    suffix: str = "z",
    max_symbols: int = 80,
    include_usdxxx: bool = True
) -> Dict[str, Any]:
    """
    Devuelve:
    {
      ok: bool,
      symbols: [..],
      reason: str,
      meta: {src, cached, ts}
    }

    Reglas:
    - incluir todos los EUR* y USD* (con sufijo z)
    - excluir BTC
    - opcional: include_usdxxx para permitir USDJPYz, USDCADz, etc.
    """
    now = _now()

    # cache
    if _CACHE["symbols"] and (now - int(_CACHE["ts"] or 0) <= int(ttl_sec or 60)):
        return {
            "ok": True,
            "symbols": list(_CACHE["symbols"]),
            "reason": _CACHE.get("reason") or "cached",
            "meta": {"cached": True, "ts": _CACHE["ts"], "src": _CACHE.get("src", "")},
        }

    fetch = _fetch_mt5_symbols()
    if not fetch.get("ok"):
        return {
            "ok": False,
            "symbols": [],
            "reason": f"MT5 symbols fetch failed: {fetch.get('error')}",
            "meta": {"cached": False, "ts": now, "src": fetch.get("src")},
        }

    raw = fetch.get("raw")
    all_symbols = _extract_symbols(raw)

    # filtros base
    out: List[str] = []
    for s in all_symbols:
        S = s.upper()

        # excluir BTC
        if "BTC" in S:
            continue

        # solo sufijo z si corresponde
        if suffix and not S.endswith(suffix.upper()):
            continue

        # EUR* siempre
        if S.startswith("EUR"):
            out.append(s)
            continue

        # USD* (incluye USDJPYz, USDCHFz, etc)
        if include_usdxxx and S.startswith("USD"):
            out.append(s)
            continue

        # *USD (EURUSDz, GBPUSDz, etc) también cae acá
        if S.endswith("USD" + suffix.upper()):
            out.append(s)
            continue

    out = _dedupe_keep_order(out)

    if max_symbols and len(out) > max_symbols:
        out = out[:max_symbols]

    _CACHE["symbols"] = out
    _CACHE["ts"] = now
    _CACHE["src"] = fetch.get("src", "")
    _CACHE["reason"] = "fresh"

    return {
        "ok": True,
        "symbols": out,
        "reason": "fresh",
        "meta": {"cached": False, "ts": now, "src": fetch.get("src")},
    }