from __future__ import annotations

from typing import Any, Dict, List


class StatsBuilder:
    def build_stats(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(trades)

        wins = 0
        losses = 0
        be = 0

        profit = 0.0
        loss = 0.0

        by_symbol = {}

        for t in trades:
            result = str(t.get("result", "")).upper().strip()
            symbol = t.get("symbol")
            pnl = float(t.get("pnl", t.get("usd", 0)) or 0)

            if symbol not in by_symbol:
                by_symbol[symbol] = {
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "breakeven": 0,
                    "profit": 0.0,
                    "loss": 0.0,
                }

            by_symbol[symbol]["trades"] += 1

            if result in {"TP1", "TP2", "RUN", "TP2_CLOSE", "RUN_CLOSE"}:
                wins += 1
                by_symbol[symbol]["wins"] += 1
                by_symbol[symbol]["profit"] += pnl
                profit += pnl

            elif result == "SL":
                losses += 1
                by_symbol[symbol]["losses"] += 1
                by_symbol[symbol]["loss"] += abs(pnl)
                loss += abs(pnl)

            elif result == "BE":
                be += 1
                by_symbol[symbol]["breakeven"] += 1

            else:
                if pnl > 0:
                    wins += 1
                    by_symbol[symbol]["wins"] += 1
                    by_symbol[symbol]["profit"] += pnl
                    profit += pnl
                elif pnl < 0:
                    losses += 1
                    by_symbol[symbol]["losses"] += 1
                    by_symbol[symbol]["loss"] += abs(pnl)
                    loss += abs(pnl)
                else:
                    be += 1
                    by_symbol[symbol]["breakeven"] += 1

        winrate = round((wins / total) * 100, 2) if total > 0 else 0.0
        profit_factor = round(profit / loss, 2) if loss > 0 else 0.0

        for symbol, data in by_symbol.items():
            trades_n = int(data["trades"])
            data["profit"] = round(data["profit"], 2)
            data["loss"] = round(data["loss"], 2)
            data["winrate"] = round((data["wins"] / trades_n) * 100, 2) if trades_n > 0 else 0.0
            data["profit_factor"] = round(data["profit"] / data["loss"], 2) if data["loss"] > 0 else 0.0

        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "breakeven": be,
            "winrate": winrate,
            "profit": round(profit, 2),
            "loss": round(loss, 2),
            "profit_factor": profit_factor,
            "by_symbol": by_symbol,
        }


stats_builder = StatsBuilder()
STATS_BUILDER = stats_builder


def build_stats(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    return stats_builder.build_stats(trades)