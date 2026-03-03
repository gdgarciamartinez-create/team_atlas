# src/atlas/bot/structure.py
from atlas.bot.state import BOT_STATE
from atlas.bot.impulse import detect_impulse
from atlas.bot.correction import detect_correction
from atlas.bot.fibonacci import compute_fibonacci
from atlas.bot.triggers import detect_triggers

def build_structure():
    impulse = detect_impulse()
    correction = detect_correction(impulse)
    continuity_ok = impulse.get("has_impulse") and correction.get("has_correction")

    structure = {
        "impulse": impulse,
        "correction": correction,
        "continuity_ok": continuity_ok,
    }

    fibonacci = compute_fibonacci(structure)
    structure["fibonacci"] = fibonacci
    structure["fibo_ok"] = fibonacci.get("valid") and fibonacci.get("in_zone")

    trigger = detect_triggers(structure)
    structure["trigger"] = trigger
    structure["has_trigger"] = trigger is not None

    BOT_STATE["structure"] = structure
    return structure