# src/atlas/bot/fibo_catalog.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class FiboQuantiles:
    q10: float
    q25: float
    q50: float
    q75: float
    q90: float


@dataclass(frozen=True)
class FiboStats:
    symbol: str
    tf: str
    legs: int
    touch_618_pct: float
    touch_786_pct: float
    continued_pct: float
    continued_given_618_pct: float
    continued_given_786_pct: float
    quantiles: FiboQuantiles


class FiboCatalog:
    """
    Lee artifacts/fibo_lab_report.json y lo convierte en un catálogo accesible por (symbol, tf).

    Espera estructura como la que pegaste:
    - results[] con items:
      - path: ...\\data\\csv\\<SYMBOL>\\<SYMBOL>_<TF>.csv
      - counts.legs
      - rates_pct.touch_618, rates_pct.touch_786, rates_pct.continued, rates_pct.continued_given_618, rates_pct.continued_given_786
      - ratio_quantiles.q10/q25/q50/q75/q90
    """

    def __init__(self, repo_root: Path, artifact_relpath: str = "artifacts/fibo_lab_report.json") -> None:
        self.repo_root = repo_root
        self.artifact_path = (repo_root / artifact_relpath).resolve()
        self._by_key: Dict[Tuple[str, str], FiboStats] = {}
        self._loaded_ok: bool = False
        self._last_error: Optional[str] = None

    @property
    def loaded_ok(self) -> bool:
        return self._loaded_ok

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def load(self) -> None:
        self._by_key.clear()
        self._loaded_ok = False
        self._last_error = None

        if not self.artifact_path.exists():
            self._last_error = f"artifact_not_found: {self.artifact_path}"
            return

        try:
            raw = json.loads(self.artifact_path.read_text(encoding="utf-8"))
        except Exception as e:
            self._last_error = f"artifact_read_error: {e}"
            return

        try:
            results = raw.get("results", [])
            for item in results:
                if not isinstance(item, dict):
                    continue
                if item.get("ok") is not True:
                    continue

                path_str = str(item.get("path", ""))
                symbol, tf = self._parse_symbol_tf_from_path(path_str)
                if not symbol or not tf:
                    continue

                counts = item.get("counts", {}) or {}
                rates = item.get("rates_pct", {}) or {}
                q = item.get("ratio_quantiles", {}) or {}

                legs = int(counts.get("legs", 0) or 0)
                if legs <= 0:
                    continue

                stats = FiboStats(
                    symbol=symbol,
                    tf=tf,
                    legs=legs,
                    touch_618_pct=float(rates.get("touch_618", 0.0) or 0.0),
                    touch_786_pct=float(rates.get("touch_786", 0.0) or 0.0),
                    continued_pct=float(rates.get("continued", 0.0) or 0.0),
                    continued_given_618_pct=float(rates.get("continued_given_618", 0.0) or 0.0),
                    continued_given_786_pct=float(rates.get("continued_given_786", 0.0) or 0.0),
                    quantiles=FiboQuantiles(
                        q10=float(q.get("q10", 0.0) or 0.0),
                        q25=float(q.get("q25", 0.0) or 0.0),
                        q50=float(q.get("q50", 0.0) or 0.0),
                        q75=float(q.get("q75", 0.0) or 0.0),
                        q90=float(q.get("q90", 0.0) or 0.0),
                    ),
                )

                self._by_key[(symbol, tf)] = stats

            self._loaded_ok = True
        except Exception as e:
            self._last_error = f"artifact_parse_error: {e}"
            self._loaded_ok = False

    def get(self, symbol: str, tf: str) -> Optional[FiboStats]:
        return self._by_key.get((symbol, tf))

    def to_debug_dict(self, symbol: str, tf: str) -> Dict[str, Any]:
        """
        Útil para meterlo al snapshot como info de diagnóstico (sin ruido).
        """
        st = self.get(symbol, tf)
        if not st:
            return {"ok": False, "symbol": symbol, "tf": tf, "reason": "no_stats"}
        return {
            "ok": True,
            "symbol": st.symbol,
            "tf": st.tf,
            "legs": st.legs,
            "touch_618_pct": st.touch_618_pct,
            "touch_786_pct": st.touch_786_pct,
            "continued_pct": st.continued_pct,
            "continued_given_618_pct": st.continued_given_618_pct,
            "continued_given_786_pct": st.continued_given_786_pct,
            "quantiles": {
                "q10": st.quantiles.q10,
                "q25": st.quantiles.q25,
                "q50": st.quantiles.q50,
                "q75": st.quantiles.q75,
                "q90": st.quantiles.q90,
            },
        }

    @staticmethod
    def _parse_symbol_tf_from_path(path_str: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Ejemplos que vimos:
          ...\\data\\csv\\XAUUSD\\XAUUSDz_M5.csv
          ...\\data\\csv\\USTEC_x100\\USTEC_x100z_M15.csv

        Regla:
          - el último archivo: <NAME>_<TF>.csv
          - TF es lo que va después del último "_"
        """
        if not path_str:
            return None, None

        p = Path(path_str)
        fname = p.name  # e.g. "XAUUSDz_M5.csv"
        stem = fname.replace(".csv", "")
        if "_" not in stem:
            return None, None

        parts = stem.split("_")
        tf = parts[-1].upper().strip()  # "M5"
        name = "_".join(parts[:-1]).strip()  # "XAUUSDz" o "USTEC_x100z"

        # símbolo lo sacamos de carpeta madre (más confiable)
        # .../csv/<SYMBOL>/<FILE>
        try:
            symbol = p.parent.name.strip()
        except Exception:
            symbol = None

        if not symbol:
            symbol = name

        # normalizamos símbolo para que sea idéntico a tu universo (con z en el archivo real, pero carpeta sin z).
        # Si tu carpeta viniera con z, igual sirve.
        symbol = symbol.strip()

        return symbol, tf