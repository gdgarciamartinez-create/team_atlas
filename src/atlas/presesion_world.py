import base64
from typing import Dict, Any, List, Optional


def _to_float(x, d=0.0):
    try:
        return float(x)
    except Exception:
        return d


def _pick_candidate(rows: List[Dict[str, Any]]) -> Optional[str]:
    # primer símbolo que esté en "tomaría/toma"
    for r in rows:
        st = str(r.get("state", ""))
        if st in ("WAIT_GATILLO", "SIGNAL", "TRIGGER_OK"):
            sym = r.get("symbol")
            if sym:
                return str(sym)
    return None


def _svg_line_chart_base64(candles: List[Dict[str, Any]], title: str) -> str:
    """
    SVG simple: sin matplotlib, sin PIL.
    Render: línea de closes.
    """
    w, h = 1200, 420
    pad_l, pad_r, pad_t, pad_b = 60, 30, 50, 45

    if not candles:
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">
  <rect width="100%" height="100%" fill="#0b1220"/>
  <text x="{w//2}" y="{h//2}" fill="#e5e7eb" font-family="monospace" font-size="18" text-anchor="middle">NO DATA</text>
  <text x="{w//2}" y="28" fill="#9aa4b2" font-family="monospace" font-size="14" text-anchor="middle">{title}</text>
</svg>"""
        return base64.b64encode(svg.encode("utf-8")).decode("ascii")

    closes = [_to_float(c.get("c", 0.0)) for c in candles]
    n = len(closes)
    if n < 2:
        return _svg_line_chart_base64([], title)

    mn = min(closes)
    mx = max(closes)
    if mx <= mn:
        mx = mn + 1e-9

    # helpers
    def x(i: int) -> float:
        return pad_l + (i / (n - 1)) * (w - pad_l - pad_r)

    def y(v: float) -> float:
        # invert y
        return pad_t + (1.0 - (v - mn) / (mx - mn)) * (h - pad_t - pad_b)

    # path
    pts = []
    for i, v in enumerate(closes):
        pts.append(f"{x(i):.2f},{y(v):.2f}")
    path = "M " + " L ".join(pts)

    # grid lines
    grid = []
    for k in range(6):
        yy = pad_t + k * (h - pad_t - pad_b) / 5
        grid.append(f'<line x1="{pad_l}" y1="{yy:.2f}" x2="{w-pad_r}" y2="{yy:.2f}" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>')

    # last value label
    last = closes[-1]
    last_y = y(last)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">
  <rect width="100%" height="100%" fill="#0b1220"/>
  {"".join(grid)}
  <text x="{w//2}" y="28" fill="#9aa4b2" font-family="monospace" font-size="14" text-anchor="middle">{title}</text>

  <path d="{path}" fill="none" stroke="#cfd6e4" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
  <circle cx="{x(n-1):.2f}" cy="{last_y:.2f}" r="4" fill="#cfd6e4"/>

  <rect x="{w-pad_r-140}" y="{last_y-16:.2f}" width="130" height="26" rx="10" fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.10)"/>
  <text x="{w-pad_r-75}" y="{last_y+2:.2f}" fill="#e5e7eb" font-family="monospace" font-size="12" text-anchor="middle">{last:.5f}</text>
</svg>"""

    return base64.b64encode(svg.encode("utf-8")).decode("ascii")


def build_presesion_snapshot(provider, engine_atlas, symbols: List[str], tf: str, count: int) -> Dict[str, Any]:
    rows = []

    for sym in symbols:
        try:
            s = engine_atlas.snapshot(symbol=sym, tf=tf, count=count)
            st = s.get("state", "WAIT")
            reason = (s.get("analysis") or {}).get("reason", "")
            txt = (s.get("analysis") or {}).get("last_decision", "")
            rows.append({
                "ts": (s.get("ts_ms") or 0),
                "world": "PRESESION",
                "symbol": sym,
                "tf": tf,
                "state": st,
                "reason": reason,
                "text": txt or f"[{sym} {tf}] {st} | {reason}",
            })
        except Exception:
            continue

    candidate = _pick_candidate(rows) or (symbols[0] if symbols else "")

    candles = []
    if candidate:
        try:
            candles = provider.get_candles(candidate, tf, count)
        except Exception:
            candles = []

    image_b64 = _svg_line_chart_base64(candles, f"PRESESION {candidate} {tf}")

    return {
        "service": "TEAM_ATLAS",
        "world": "PRESESION",
        "atlas_mode": "PRESESION",
        "symbol": candidate,
        "tf": tf,
        "count": count,
        "ts_ms": 0,
        "price": 0.0,
        "candles": candles,  # útil para debug
        "state": "WAIT",
        "side": "WAIT",
        "entry": 0.0,
        "sl": 0.0,
        "tp": 0.0,
        "analysis": {
            "reason": "PRESESION",
            "reason_raw": "PRESESION",
            "last_decision": f"[PRESESION] mostrando {candidate}",
            "note": "no interactivo: SVG + bitácora",
            "plan_hash": "",
        },
        "ui": {
            "image_b64": image_b64,
            "image_mime": "image/svg+xml",
            "rows": rows[-30:],
        }
    }