# src/atlas/bot/fibo_score.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .fibo_catalog import FiboStats


def clamp(x: float, lo: float, hi: float) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


@dataclass(frozen=True)
class LegInputs:
    """
    Representa una pierna (impulso->corrección) en formato mínimo.
    Todo en unidades de precio (o puntos) y tiempo (segundos o velas, da igual mientras seas consistente).
    """
    impulse_size: float        # tamaño del impulso
    retrace_size: float        # tamaño de la corrección (profundidad)
    t_impulse: float           # tiempo del impulso
    t_retrace: float           # tiempo de la corrección
    impulse_range_ok: bool     # pasa filtro range_min
    noise_penalty: float = 0.0 # opcional (0..10) para serrucho/pivotes malos


@dataclass(frozen=True)
class ScoreOutput:
    ok: bool
    score: int
    ratio: float
    zone: str
    tp1_mult: float
    tp2_mult: float
    runner_mult: float
    components: Dict[str, float]
    reason: Optional[str] = None


class FiboScorer:
    """
    Calcula score 0..100 para una pierna, usando:
      - profundidad del retroceso (ratio)
      - continuidad histórica del activo/tf (continued_pct)
      - simetría de tiempos (t_retrace / t_impulse)
      - penalización por ruido / rango insuficiente
    """

    def __init__(self, tol: float = 0.008) -> None:
        self.tol = tol

    def score_leg(self, leg: LegInputs, stats: Optional[FiboStats]) -> ScoreOutput:
        if leg.impulse_size <= 0:
            return ScoreOutput(
                ok=False, score=0, ratio=0.0, zone="NA",
                tp1_mult=1.0, tp2_mult=1.5, runner_mult=2.4,
                components={}, reason="bad_impulse_size"
            )
        if leg.retrace_size < 0:
            return ScoreOutput(
                ok=False, score=0, ratio=0.0, zone="NA",
                tp1_mult=1.0, tp2_mult=1.5, runner_mult=2.4,
                components={}, reason="bad_retrace_size"
            )

        ratio = leg.retrace_size / leg.impulse_size  # profundidad relativa

        # A) Profundidad (0..45)
        depth_pts = self._depth_points(ratio)

        # B) Continuidad histórica (0..25)
        hist_pts = self._historical_points(stats)

        # C) Simetría tiempo (0..20)
        time_pts = self._time_points(leg.t_impulse, leg.t_retrace)

        # D) Penalizaciones (0..-20)
        penalty = 0.0
        if not leg.impulse_range_ok:
            penalty -= 10.0
        penalty -= clamp(leg.noise_penalty, 0.0, 10.0)

        raw = depth_pts + hist_pts + time_pts + penalty
        raw = clamp(raw, 0.0, 100.0)

        # Zona recomendada (lectura operativa)
        zone = self._zone_from_ratio(ratio)

        # Multiplicadores TP desde cuantiles si existen, si no defaults robustos
        tp1, tp2, runner = self._tp_mults(stats)

        return ScoreOutput(
            ok=True,
            score=int(round(raw)),
            ratio=float(ratio),
            zone=zone,
            tp1_mult=tp1,
            tp2_mult=tp2,
            runner_mult=runner,
            components={
                "depth": float(depth_pts),
                "historical": float(hist_pts),
                "time": float(time_pts),
                "penalty": float(penalty),
                "raw": float(raw),
            },
        )

    def _depth_points(self, ratio: float) -> float:
        # Mapa robusto (no binario):
        # <0.50 → 0
        # 0.50..0.618 → 20
        # 0.618..0.786 → 40
        # 0.786..1.00 → 45
        # >1.00 → 30 (zona con más barridos / transición estadística)
        if ratio < 0.50:
            return 0.0
        if ratio < 0.618:
            # ramp 0.50..0.618 -> 0..20
            return 20.0 * ((ratio - 0.50) / (0.618 - 0.50))
        if ratio < 0.786:
            # ramp 0.618..0.786 -> 40..45 (ligeramente mejor)
            return 40.0 + 5.0 * ((ratio - 0.618) / (0.786 - 0.618))
        if ratio <= 1.00:
            return 45.0
        # >1.00: penaliza un poco, pero no mata (puede ser extensión y luego continuidad)
        # 1.00..1.27: 30..20, >1.27: 15
        if ratio <= 1.27:
            return 30.0 - 10.0 * ((ratio - 1.00) / (1.27 - 1.00))
        return 15.0

    def _historical_points(self, stats: Optional[FiboStats]) -> float:
        # Mapea continued_pct a 0..25 (75%→0, 85%→25)
        if not stats:
            return 10.0  # neutro razonable si no hay stats
        c = float(stats.continued_pct)
        return clamp((c - 75.0) * (25.0 / 10.0), 0.0, 25.0)

    def _time_points(self, t_impulse: float, t_retrace: float) -> float:
        if t_impulse <= 0:
            return 0.0
        r = t_retrace / t_impulse
        # <=0.8: 20
        # 0.8..1.3: 12
        # 1.3..2.0: 5
        # >2.0: 0
        if r <= 0.8:
            return 20.0
        if r <= 1.3:
            # lineal 20 -> 12
            return 20.0 - 8.0 * ((r - 0.8) / (1.3 - 0.8))
        if r <= 2.0:
            # lineal 12 -> 5
            return 12.0 - 7.0 * ((r - 1.3) / (2.0 - 1.3))
        return 0.0

    def _zone_from_ratio(self, ratio: float) -> str:
        # Zona operativa (texto simple para UI)
        if ratio < 0.618:
            return "SHALLOW(<0.618)"
        if ratio < 0.786:
            return "MID(0.618-0.786)"
        if ratio <= 1.00:
            return "DEEP(0.786-1.00)"
        return "OVER(>1.00)"

    def _tp_mults(self, stats: Optional[FiboStats]) -> tuple[float, float, float]:
        # Defaults universales si no hay cuantiles
        if not stats:
            return 1.0, 1.5, 2.4

        q = stats.quantiles
        # Si cuantiles vienen razonables, usamos:
        # TP1 ~ q50
        # TP2 ~ q75
        # Runner ~ q90
        tp1 = q.q50 if q.q50 > 0 else 1.0
        tp2 = q.q75 if q.q75 > 0 else 1.5
        runner = q.q90 if q.q90 > 0 else 2.4

        # Clamp para evitar valores locos por datasets raros
        tp1 = clamp(tp1, 0.5, 2.0)
        tp2 = clamp(tp2, 0.8, 3.5)
        runner = clamp(runner, 1.2, 6.0)

        return float(tp1), float(tp2), float(runner)

    def to_ui_rows(self, symbol: str, tf: str, out: ScoreOutput, stats: Optional[FiboStats]) -> list[dict[str, Any]]:
        """
        Devuelve filas listas para ui.rows del snapshot.
        """
        rows = []
        rows.append({
            "k": "FIBO_SCORE",
            "v": f"{out.score}/100",
            "hint": "Score de calidad de pierna (profundidad + historia + tiempo - penalizaciones)",
        })
        rows.append({
            "k": "RATIO",
            "v": f"{out.ratio:.3f}",
            "hint": "Profundidad relativa corrección/impulso",
        })
        rows.append({
            "k": "ZONE",
            "v": out.zone,
            "hint": "Clasificación de zona por profundidad",
        })
        rows.append({
            "k": "TP_MULTS",
            "v": f"TP1 {out.tp1_mult:.2f} | TP2 {out.tp2_mult:.2f} | RUN {out.runner_mult:.2f}",
            "hint": "Targets basados en cuantiles (q50/q75/q90) del activo/tf",
        })
        if stats:
            rows.append({
                "k": "HIST_CONT",
                "v": f"{stats.continued_pct:.2f}%",
                "hint": "Continuidad histórica del dataset para este symbol/tf",
            })
            rows.append({
                "k": "HIST_TOUCH",
                "v": f"618 {stats.touch_618_pct:.2f}% | 786 {stats.touch_786_pct:.2f}%",
                "hint": "Frecuencia de llegada a 0.618 y 0.786 en el lab",
            })
        else:
            rows.append({
                "k": "HIST",
                "v": "NO_STATS",
                "hint": "No se encontró stats en fibo_lab_report para este symbol/tf",
            })
        return rows