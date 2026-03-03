from __future__ import annotations
import logging
import time
import math
from typing import Optional, Tuple
from atlas.config import settings
from atlas.models import Setup, Proposal
from atlas.mt5_service import MT5Service
from atlas.service import ai_service
from atlas.telegram import TelegramNotifier
from atlas import analysis
from atlas.risk import calc_lot_1pct
from atlas.simulation import calculate_poi

logger = logging.getLogger("atlas.engine")

def make_message(p: Proposal, reason_short: str, reason_long: str, decision: str) -> str:
    # Per request: SYMBOL, gatillo/condición, BUY/SELL, ENTRY, SL, PARCIAL, TP2, motivo
    lines = [
        f"{p.symbol.upper()}",
        f"{p.gatillo}",
        "",
        f"{p.direction.upper()} {p.entry:.5f}",
        f"SL: {p.sl:.5f}",
        f"PARCIAL: {p.tp1:.5f}",
    ]
    if p.tp2 and p.tp2 > 0:
        lines.append(f"TP2: {p.tp2:.5f}")

    if reason_short:
        lines.append(f"\n{reason_short}")

    return "\n".join(lines)

def evaluate_setup(setup: Setup, mt5: MT5Service) -> Optional[Proposal]:
    tf = "M5" if "M5" in setup.tfs else ("M1" if "M1" in setup.tfs else setup.tfs[0])
    rates = mt5.rates(setup.symbol, tf, 160)
    if len(rates) < 40:
        return None

    price = rates[-1]["close"]
    zlo, zhi = min(setup.zone_low, setup.zone_high), max(setup.zone_low, setup.zone_high)
    pad = (zhi - zlo) * 0.10

    if not analysis.in_zone(price, zlo, zhi, pad=pad):
        return None

    gatillo = None
    level = zhi if setup.direction == "buy" else zlo

    if analysis.detect_breakout_close(rates, level, setup.direction):
        gatillo = "Breakout con cierre"
    elif analysis.detect_pullback_reject(rates, zlo, zhi, setup.direction):
        gatillo = "Pullback + rechazo"
    elif analysis.detect_momentum_continuation(rates, setup.direction):
        gatillo = "Continuación por momentum"

    if not gatillo:
        return None

    # Pre-calculation for snapshot (Simulation Logic)
    entry = float(price)
    # Rough SL for context based on zone
    sl_rough = setup.zone_low if setup.direction == "buy" else setup.zone_high 
    
    # Use simulation helper to get initial structure
    sim_poi = calculate_poi(setup.symbol, entry, setup.direction.upper(), atr=abs(entry-sl_rough))

    # We return a partial proposal to be enriched by AI
    # Using dummy values for targets/lots as AI will provide them

    return Proposal(
        symbol=setup.symbol,
        direction=setup.direction,
        tf=tf,
        mode=setup.mode,
        gatillo=gatillo,
        entry=entry,
        sl=sim_poi["sl"], 
        tp1=sim_poi["tp1"],
        tp2=sim_poi["tp2"],
        partial_pct=50,
        lots=sim_poi["lot_sim"],
        rr_tp1=0.0,
        rr_tp2=0.0,
        fib_ok=True,
        context={"zone_low": setup.zone_low, "zone_high": setup.zone_high, "notes": setup.notes},
    )

def run_once(setups, store, mt5: MT5Service, tg: TelegramNotifier) -> None:
    evaluated_count = 0
    for s in setups:
        if not s.enabled:
            continue
        if not store.can_alert(s.id, settings.alert_cooldown_min):
            continue
        evaluated_count += 1

        proposal = evaluate_setup(s, mt5)
        if proposal is None:
            continue

        # Prepare snapshot for AI
        snapshot = {
            "symbol": proposal.symbol,
            "price_now": proposal.entry,
            "gatillo_detected": proposal.gatillo,
            "zone_low": proposal.context.get("zone_low"),
            "zone_high": proposal.context.get("zone_high")
        }

        # Call AI
        ai_decision = ai_service.evaluate(s.to_dict(), snapshot)
        
        if ai_decision.decision != "APPROVE":
            # Optional: Log debug alert for WAIT/REJECT if needed
            continue

        # Update proposal with AI values
        proposal.entry = ai_decision.entry
        proposal.sl = ai_decision.sl
        proposal.tp1 = ai_decision.tp1
        proposal.tp2 = ai_decision.tp2 or 0.0
        proposal.lots = ai_decision.lot_1pct
        
        # Recalculate RR
        risk = abs(proposal.entry - proposal.sl)
        if risk > 0:
            proposal.rr_tp1 = abs(proposal.tp1 - proposal.entry) / risk
            if proposal.tp2:
                proposal.rr_tp2 = abs(proposal.tp2 - proposal.entry) / risk

        # Send Alert
        msg = make_message(proposal, ai_decision.reason_short, ai_decision.reason_long, ai_decision.decision)
        
        if tg.send(msg):
            store.mark_alert(s.id)
            store.add_alert({
                "timestamp": time.time(),
                "symbol": proposal.symbol,
                "tf": proposal.tf,
                "mode": proposal.mode,
                "direction": proposal.direction,
                "gatillo": proposal.gatillo,
                "entry": proposal.entry,
                "sl": proposal.sl,
                "tp1": proposal.tp1,
                "tp2": proposal.tp2,
                "lots": proposal.lots,
                "rr": proposal.rr_tp1,
                "decision": ai_decision.decision,
                "confidence": ai_decision.confidence,
                "reason_short": ai_decision.reason_short,
                "reason_long": ai_decision.reason_long,
                "partial": ai_decision.partial
            })

    store.update_engine_status(evaluated_count)
