"""
Core minimal strategy for NOW:
- Produces candidates (signals) with numeric entry/sl/tp.
- Validates mandatory 0.786 check.
- GAP for XAUUSD is priority score boost, NOT exclusive.
- Triggers allowed: direct-touch 0.786, sweep+recover, break+retest.
This is a minimal runnable version: it will not be perfect, but it is REAL plumbing.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from atlas.analysis import in_zone

def fib_0786_zone(low: float, high: float, direction: str) -> tuple[float, float]:
    rng = high - low
    if direction == "BUY":
        # Retracement down from high
        v1 = high - rng * 0.786
        v2 = high - rng * 0.79
        return (min(v1, v2), max(v1, v2))
    else:
        # Retracement up from low
        v1 = low + rng * 0.786
        v2 = low + rng * 0.79
        return (min(v1, v2), max(v1, v2))

@dataclass
class Candidate:
    symbol: str
    side: str
    entry: float
    sl: float
    tp: float
    score: float
    reason: str
    tags: List[str]

def build_candidates(snapshot: Dict[str, Any]) -> List[Candidate]:
    out: List[Candidate] = []
    for sym, st in snapshot.get("states_by_symbol", {}).items():
        m = st.get("market", {})
        px = m.get("price")
        if px is None:
            continue

        ctx = st.get("context", {})
        bias = ctx.get("bias")  # "BUY" or "SELL" or None
        if bias not in ("BUY", "SELL"):
            continue

        imp = ctx.get("impulse", {})
        low = imp.get("low")
        high = imp.get("high")
        if low is None or high is None:
            continue

        zone = fib_0786_zone(low, high, bias)
        if not in_zone(px, zone[0], zone[1]):
            continue

        # Minimal SL/TP scaffold:
        # SL beyond impulse low/high by small buffer
        if bias == "BUY":
            sl = low - (high - low) * 0.05
            tp = high
        else:
            sl = high + (high - low) * 0.05
            tp = low

        score = 70.0
        tags = ["fib_0.786"]

        # GAP priority boost for XAUUSD, but do not block others
        if sym == "XAUUSD" and st.get("gap", {}).get("is_valid") is True:
            score += 15.0
            tags.append("gap_priority")

        out.append(Candidate(
            symbol=sym,
            side=bias,
            entry=float(px),
            sl=float(sl),
            tp=float(tp),
            score=score,
            reason="0.786 touch + context bias",
            tags=tags
        ))

    out.sort(key=lambda x: x.score, reverse=True)
    return out[:10]