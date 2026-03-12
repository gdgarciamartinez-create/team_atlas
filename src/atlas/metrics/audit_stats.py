from __future__ import annotations

from typing import Any, Dict, List


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def build_audit_stats(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(trades)

    wins = 0
    losses = 0
    breakeven = 0

    gross_profit = 0.0
    gross_loss = 0.0
    net_profit = 0.0

    total_pips = 0.0
    total_usd = 0.0

    by_symbol: Dict[str, Dict[str, Any]] = {}

    for t in trades:
        symbol = str(t.get("symbol") or "UNKNOWN")
        result = str(t.get("result") or "").upper().strip()
        pips = _f(t.get("pips"))
        usd = _f(t.get("usd", t.get("pnl", 0)))

        total_pips += pips
        total_usd += usd
        net_profit += usd

        if symbol not in by_symbol:
            by_symbol[symbol] = {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "breakeven": 0,
                "pips": 0.0,
                "usd": 0.0,
                "gross_profit": 0.0,
                "gross_loss": 0.0,
                "winrate": 0.0,
                "profit_factor": 0.0,
            }

        s = by_symbol[symbol]
        s["trades"] += 1
        s["pips"] += pips
        s["usd"] += usd

        if result in {"TP1", "TP2", "RUN", "TP2_CLOSE", "RUN_CLOSE"} and usd > 0:
            wins += 1
            gross_profit += usd
            s["wins"] += 1
            s["gross_profit"] += usd

        elif result == "SL" and usd < 0:
            losses += 1
            gross_loss += abs(usd)
            s["losses"] += 1
            s["gross_loss"] += abs(usd)

        elif result == "BE" or abs(usd) < 1e-9:
            breakeven += 1
            s["breakeven"] += 1

        else:
            if usd > 0:
                wins += 1
                gross_profit += usd
                s["wins"] += 1
                s["gross_profit"] += usd
            elif usd < 0:
                losses += 1
                gross_loss += abs(usd)
                s["losses"] += 1
                s["gross_loss"] += abs(usd)
            else:
                breakeven += 1
                s["breakeven"] += 1

    winrate = round((wins / total) * 100, 2) if total > 0 else 0.0
    avg_pips = round(total_pips / total, 2) if total > 0 else 0.0
    avg_usd = round(total_usd / total, 2) if total > 0 else 0.0
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0.0

    avg_win = round(gross_profit / wins, 2) if wins > 0 else 0.0
    avg_loss = round(gross_loss / losses, 2) if losses > 0 else 0.0
    expectancy = round((winrate / 100.0) * avg_win - ((100.0 - winrate) / 100.0) * avg_loss, 2) if total > 0 else 0.0

    for symbol, s in by_symbol.items():
        trades_n = int(s["trades"])
        s["winrate"] = round((s["wins"] / trades_n) * 100, 2) if trades_n > 0 else 0.0
        s["profit_factor"] = round(s["gross_profit"] / s["gross_loss"], 2) if s["gross_loss"] > 0 else 0.0
        s["pips"] = round(s["pips"], 2)
        s["usd"] = round(s["usd"], 2)
        s["gross_profit"] = round(s["gross_profit"], 2)
        s["gross_loss"] = round(s["gross_loss"], 2)

    best_symbol = None
    worst_symbol = None

    if by_symbol:
        ordered = sorted(by_symbol.items(), key=lambda kv: kv[1]["usd"], reverse=True)
        best_symbol = {"symbol": ordered[0][0], **ordered[0][1]}
        worst_symbol = {"symbol": ordered[-1][0], **ordered[-1][1]}

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven,
        "winrate": winrate,
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "net_profit": round(net_profit, 2),
        "profit_factor": profit_factor,
        "avg_pips": avg_pips,
        "avg_usd": avg_usd,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "best_symbol": best_symbol,
        "worst_symbol": worst_symbol,
        "by_symbol": by_symbol,
    }