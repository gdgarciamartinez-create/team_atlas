# src/atlas/snapshot_core.py
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from importlib import import_module
from typing import Any, Dict, List, Optional, Tuple, Callable


@dataclass
class UIScannerRow:
    symbol: str
    tf: str
    score: int = 0
    state: str = "WAIT"
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    lot: Optional[float] = None
    reason: Optional[str] = None


@dataclass
class SnapshotAnalysis:
    status: str = "OK"
    world: str = ""
    symbol: str = ""
    tf: str = ""
    atlas_mode: Optional[str] = None
    provider: str = "mt5"
    last_error: Optional[Tuple[int, str]] = None
    msg: Optional[str] = None
    ts: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


def _safe_last_error(err: Any) -> Optional[Tuple[int, str]]:
    if err is None:
        return None
    try:
        code, text = err
        code_i = int(code)
        text_s = str(text)
        if code_i == 1 and text_s.strip().lower() == "success":
            return None
        return (code_i, text_s)
    except Exception:
        return (999, str(err))


def _normalize_tf(tf: str) -> str:
    tf = (tf or "").strip().upper()
    allowed = {"M1", "M3", "M5", "M15", "H1", "H4", "D1"}
    return tf if tf in allowed else "M5"


def _normalize_symbol(symbol: str) -> str:
    return (symbol or "").strip()


def _normalize_world(world: str) -> str:
    w = (world or "").strip().upper()
    allowed = {"ATLAS_IA", "SCALPING_M1", "SCALPING_M5", "FOREX", "GAP"}
    return w if w in allowed else "ATLAS_IA"


def _normalize_atlas_mode(mode: Optional[str]) -> Optional[str]:
    if mode is None:
        return None
    m = str(mode).strip().upper()
    allowed = {"SCALPING", "FOREX"}
    return m if m in allowed else None


def _base_snapshot(world: str, symbol: str, tf: str, count: int, atlas_mode: Optional[str]) -> Dict[str, Any]:
    analysis = SnapshotAnalysis(
        status="OK",
        world=world,
        symbol=symbol,
        tf=tf,
        atlas_mode=atlas_mode,
        provider="mt5",
        last_error=None,
        msg=None,
    )
    return {
        "ok": True,
        "world": world,
        "symbol": symbol,
        "tf": tf,
        "count": int(count),
        "atlas_mode": atlas_mode,
        "analysis": asdict(analysis),
        "ui": {"rows": []},
    }


def _finalize(base: Dict[str, Any], analysis: SnapshotAnalysis, rows: List[UIScannerRow]) -> Dict[str, Any]:
    base["analysis"] = asdict(analysis)
    base["ui"] = {"rows": [asdict(r) for r in rows]}
    base["ok"] = analysis.status not in ("PROVIDER_ERROR", "ENGINE_ERROR", "INVALID_REQUEST")
    return base


def _try_import(module_path: str) -> Any:
    try:
        return import_module(module_path)
    except Exception:
        return None


def _wrap_mt5_provider_functions(mod: Any) -> Any:
    candles_fn = getattr(mod, "get_candles", None)
    if not callable(candles_fn):
        return None

    class _ModuleProviderWrapper:
        def __init__(self, candles_func: Callable[..., Any], module_obj: Any) -> None:
            self._fn = candles_func
            self._mod = module_obj

        @property
        def last_error(self) -> Any:
            return getattr(self._mod, "last_error", None)

        def get_candles(self, *, symbol: str, tf: str, count: int) -> Any:
            return self._fn(symbol=symbol, tf=tf, count=int(count))

    return _ModuleProviderWrapper(candles_fn, mod)


def _get_provider() -> Any:
    mod = _try_import("atlas.providers.mt5_provider")
    if mod is None:
        return None
    return _wrap_mt5_provider_functions(mod)


def _fetch_market_data(provider: Any, symbol: str, tf: str, count: int) -> Dict[str, Any]:
    out = {"ok": False, "candles": [], "last_error": None, "reason": None}

    if provider is None:
        out["last_error"] = (500, "MT5 provider not available")
        out["reason"] = "provider is None"
        return out

    try:
        raw = provider.get_candles(symbol=symbol, tf=tf, count=int(count))

        # ✅ si provider retorna dict (como tu mt5_provider), respetar raw["ok"]
        if isinstance(raw, dict):
            ok = bool(raw.get("ok", False))
            candles = raw.get("candles", [])
            out["reason"] = raw.get("reason")
            out["last_error"] = _safe_last_error(raw.get("last_error"))

            if not ok:
                out["ok"] = False
                out["candles"] = []
                return out

            # ok=True pero sin velas -> también es error práctico (no alimentar engines)
            if not isinstance(candles, list) or len(candles) == 0:
                out["ok"] = False
                out["candles"] = []
                out["last_error"] = out["last_error"] or (502, "MT5 ok=True but returned empty candles")
                return out

            out["ok"] = True
            out["candles"] = candles
            return out

        # fallback: si retorna lista directa
        if not isinstance(raw, list) or len(raw) == 0:
            out["last_error"] = (502, f"MT5 returned invalid candles type: {type(raw).__name__}")
            out["reason"] = "invalid raw candles"
            return out

        out["ok"] = True
        out["candles"] = raw
        return out

    except Exception as e:
        out["last_error"] = (501, str(e))
        out["reason"] = "exception calling provider"
        return out


def _import_engine_builder(module_path: str, fn_name: str) -> Any:
    try:
        mod = import_module(module_path)
        return getattr(mod, fn_name, None)
    except Exception:
        return None

build_gap_snapshot = _import_engine_builder("atlas.engines.gap_engine", "build_gap_snapshot")
build_scalping_snapshot = _import_engine_builder("atlas.engines.scalping_engine", "build_scalping_snapshot")
build_forex_snapshot = _import_engine_builder("atlas.engines.forex_engine", "build_forex_snapshot")
build_atlas_ia_snapshot = _import_engine_builder("atlas.engines.atlas_ia_engine", "build_atlas_ia_snapshot")


def _merge_engine_snapshot(base: Dict[str, Any], snap: Any) -> Dict[str, Any]:
    if not isinstance(snap, dict):
        analysis = SnapshotAnalysis(
            status="ENGINE_ERROR",
            world=str(base.get("world", "")),
            symbol=str(base.get("symbol", "")),
            tf=str(base.get("tf", "")),
            atlas_mode=base.get("atlas_mode"),
            provider="mt5",
            last_error=None,
            msg="engine returned non-dict snapshot",
        )
        rows = [UIScannerRow(symbol=str(base.get("symbol", "")), tf=str(base.get("tf", "")), reason="ENGINE_BAD_SNAPSHOT")]
        return _finalize(base, analysis, rows)

    a = snap.get("analysis", {}) if isinstance(snap.get("analysis", {}), dict) else {}
    analysis = SnapshotAnalysis(
        status=str(a.get("status", "OK")),
        world=str(a.get("world", base.get("world", ""))),
        symbol=str(a.get("symbol", base.get("symbol", ""))),
        tf=str(a.get("tf", base.get("tf", ""))),
        atlas_mode=a.get("atlas_mode", base.get("atlas_mode")),
        provider=str(a.get("provider", "mt5")),
        last_error=_safe_last_error(a.get("last_error")),
        msg=a.get("msg"),
    )

    ui = snap.get("ui", {}) if isinstance(snap.get("ui", {}), dict) else {}
    rows_raw = ui.get("rows", []) or []
    rows: List[UIScannerRow] = []
    if isinstance(rows_raw, list):
        for r in rows_raw:
            if isinstance(r, dict):
                rows.append(
                    UIScannerRow(
                        symbol=str(r.get("symbol", base.get("symbol", ""))),
                        tf=str(r.get("tf", base.get("tf", ""))),
                        score=int(r.get("score", 0) or 0),
                        state=str(r.get("state", "WAIT")),
                        entry=r.get("entry"),
                        sl=r.get("sl"),
                        tp=r.get("tp"),
                        lot=r.get("lot"),
                        reason=r.get("reason"),
                    )
                )

    if not rows:
        rows = [UIScannerRow(symbol=str(base.get("symbol", "")), tf=str(base.get("tf", "")), reason="EMPTY_ROWS")]

    base["analysis"] = asdict(analysis)
    base["ui"] = {"rows": [asdict(r) for r in rows]}
    base["ok"] = analysis.status not in ("PROVIDER_ERROR", "ENGINE_ERROR", "INVALID_REQUEST")
    return base


def build_snapshot(
    *,
    world: str,
    symbol: str,
    tf: str,
    count: int = 200,
    atlas_mode: Optional[str] = None,
    season: Optional[str] = None,
) -> Dict[str, Any]:
    w = _normalize_world(world)
    s = _normalize_symbol(symbol)
    t = _normalize_tf(tf)
    c = max(50, min(int(count or 200), 2000))
    m = _normalize_atlas_mode(atlas_mode)

    base = _base_snapshot(w, s, t, c, m)

    analysis = SnapshotAnalysis(
        status="OK",
        world=w,
        symbol=s,
        tf=t,
        atlas_mode=m,
        provider="mt5",
        last_error=None,
        msg=None,
    )

    if not s:
        analysis.status = "INVALID_REQUEST"
        analysis.msg = "symbol is required"
        return _finalize(base, analysis, [])

    provider = _get_provider()
    feed = _fetch_market_data(provider, s, t, c)

    if not feed.get("ok", False):
        analysis.status = "PROVIDER_ERROR"
        analysis.last_error = _safe_last_error(feed.get("last_error"))
        analysis.msg = f"provider failed: {feed.get('reason')}"
        rows = [UIScannerRow(symbol=s, tf=t, score=0, state="WAIT", reason="PROVIDER_ERROR")]
        return _finalize(base, analysis, rows)

    candles = feed.get("candles", []) or []

    try:
        if w == "GAP":
            if not callable(build_gap_snapshot):
                analysis.status = "ENGINE_ERROR"
                analysis.msg = "gap_engine not available"
                rows = [UIScannerRow(symbol=s, tf=t, reason="ENGINE_MISSING")]
                return _finalize(base, analysis, rows)
            snap = build_gap_snapshot(symbol=s, tf=t, count=c, candles=candles, season=season, provider=provider)
            return _merge_engine_snapshot(base, snap)

        if w in ("SCALPING_M1", "SCALPING_M5"):
            if not callable(build_scalping_snapshot):
                analysis.status = "ENGINE_ERROR"
                analysis.msg = "scalping_engine not available"
                rows = [UIScannerRow(symbol=s, tf=t, reason="ENGINE_MISSING")]
                return _finalize(base, analysis, rows)
            snap = build_scalping_snapshot(world=w, symbol=s, tf=t, count=c, candles=candles, provider=provider)
            return _merge_engine_snapshot(base, snap)

        if w == "FOREX":
            if not callable(build_forex_snapshot):
                analysis.status = "ENGINE_ERROR"
                analysis.msg = "forex_engine not available"
                rows = [UIScannerRow(symbol=s, tf=t, reason="ENGINE_MISSING")]
                return _finalize(base, analysis, rows)
            snap = build_forex_snapshot(symbol=s, tf=t, count=c, candles=candles, provider=provider)
            return _merge_engine_snapshot(base, snap)

        if not callable(build_atlas_ia_snapshot):
            analysis.status = "ENGINE_ERROR"
            analysis.msg = "atlas_ia_engine not available"
            rows = [UIScannerRow(symbol=s, tf=t, reason="ENGINE_MISSING")]
            return _finalize(base, analysis, rows)

        snap = build_atlas_ia_snapshot(symbol=s, tf=t, count=c, candles=candles, atlas_mode=m, provider=provider)
        return _merge_engine_snapshot(base, snap)

    except Exception as e:
        analysis.status = "ENGINE_ERROR"
        analysis.msg = f"engine exception: {e}"
        rows = [UIScannerRow(symbol=s, tf=t, reason="ENGINE_ERROR")]
        return _finalize(base, analysis, rows)