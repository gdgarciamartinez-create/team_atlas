from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


DEFAULT_PATH = os.path.join("data", "fib_opt.json")


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def _u(x: str) -> str:
    return (x or "").strip().upper()


def _clamp(x: float, a: float, b: float) -> float:
    return max(a, min(b, x))


def _percentile(xs: List[float], p: float) -> float:
    if not xs:
        return 0.786
    ys = sorted(xs)
    p = _clamp(float(p), 0.0, 1.0)
    k = int(round((len(ys) - 1) * p))
    k = max(0, min(k, len(ys) - 1))
    return float(ys[k])


@dataclass
class FibOpt:
    symbol: str
    opt_level: float
    band_low: float
    band_high: float
    n: int
    confidence: float
    updated_at: str
    note: str = "auto"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FibOptStore:
    """
    Persistencia simple (pro) de fib óptimo por símbolo.
    Guarda/lee: data/fib_opt.json
    """

    def __init__(self, path: str = DEFAULT_PATH) -> None:
        self.path = path
        _ensure_dir(self.path)
        self._db: Dict[str, FibOpt] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            self._db = {}
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                self._db = {}
                return

            out: Dict[str, FibOpt] = {}
            for sym, v in raw.items():
                if not isinstance(v, dict):
                    continue
                s = _u(v.get("symbol") or sym)
                out[s] = FibOpt(
                    symbol=s,
                    opt_level=float(v.get("opt_level", 0.786)),
                    band_low=float(v.get("band_low", 0.70)),
                    band_high=float(v.get("band_high", 0.82)),
                    n=int(v.get("n", 0)),
                    confidence=float(v.get("confidence", 0.0)),
                    updated_at=str(v.get("updated_at", _now_iso())),
                    note=str(v.get("note", "auto")),
                )
            self._db = out
        except Exception:
            self._db = {}

    def _save(self) -> None:
        _ensure_dir(self.path)
        tmp = self.path + ".tmp"
        raw = {sym: fo.to_dict() for sym, fo in self._db.items()}
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def get(self, symbol: str) -> FibOpt:
        sym = _u(symbol)
        if sym in self._db:
            return self._db[sym]
        return FibOpt(
            symbol=sym,
            opt_level=0.786,
            band_low=0.70,
            band_high=0.82,
            n=0,
            confidence=0.0,
            updated_at=_now_iso(),
            note="default",
        )

    def all(self) -> Dict[str, Dict[str, Any]]:
        return {sym: fo.to_dict() for sym, fo in self._db.items()}

    def update_from_ratios(
        self,
        symbol: str,
        ratios: List[float],
        *,
        p_opt: float = 0.70,
        band: float = 0.06,
        min_n: int = 40,
        note: str = "auto",
        auto_save: bool = True,
    ) -> FibOpt:
        sym = _u(symbol)
        xs = [float(x) for x in ratios if x is not None]
        xs = [x for x in xs if 0.20 <= x <= 1.60]

        if not xs:
            return self.get(sym)

        opt = _percentile(xs, p_opt)
        band_low = _clamp(opt - band, 0.20, 1.60)
        band_high = _clamp(opt + band, 0.20, 1.60)

        n = len(xs)
        confidence = _clamp(n / float(max(1, min_n)), 0.0, 1.0)

        fo = FibOpt(
            symbol=sym,
            opt_level=float(opt),
            band_low=float(band_low),
            band_high=float(band_high),
            n=int(n),
            confidence=float(confidence),
            updated_at=_now_iso(),
            note=str(note),
        )
        self._db[sym] = fo
        if auto_save:
            self._save()
        return fo


__all__ = ["FibOptStore", "FibOpt"]