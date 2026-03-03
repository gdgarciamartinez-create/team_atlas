from fastapi import APIRouter
import time

router = APIRouter()

def now() -> int:
    return int(time.time())

@router.get("/reports")
def reports():
    return {
        "ts": now(),
        "standby": True,
        "modules": {
            "GENERAL": {
                "titulo": "GENERAL",
                "estado": "STANDBY",
                "detalle": "Observa y reporta (laboratorio).",
                "checklist": ["contexto", "zona", "timing", "fibo_0.786"],
                "tf_default": "M3",
            },
            "PRESESION": {
                "titulo": "PRESESION",
                "estado": "STANDBY",
                "detalle": "Contexto previo a NY. Aqui se permite mencionar 0.79.",
                "checklist": ["franja_ok", "zona_ok", "timing_ok", "fibo_0.786", "fibo_0.79_only_here"],
                "tf_default": "M5",
                "tf_hint": "M3",
            },
            "GAP": {
                "titulo": "GAP XAUUSD",
                "estado": "STANDBY",
                "detalle": "Gap = objetivo (deuda potencial). Solo tras ritual completo.",
                "ritual": ["exageracion", "fallo_continuidad", "ruptura", "recuperacion", "aceptacion"],
                "tf_default": "M1",
                "symbol_forced": "XAUUSD",
            },
            "GATILLOS": {
                "titulo": "GATILLOS",
                "estado": "STANDBY",
                "detalle": "Solo 3 gatillos permitidos. Silencio es válido.",
                "permitidos": ["toque_0.786", "barrida_recuperacion", "ruptura_retest_secundario"],
                "tf_default": "M3",
            },
            "ATLAS_IA": {
                "titulo": "ATLAS_IA",
                "estado": "STANDBY",
                "detalle": "Explica NO_TRADE/WAIT/CONFIRMED. Si avisa, es confirmado.",
                "salida": ["razones", "riesgo", "fibo", "tiempo", "estado"],
                "tf_default": "M5",
            },
        }
    }
