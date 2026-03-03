from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


def _try_import_mt5():
    try:
        import MetaTrader5 as mt5  # type: ignore
        return mt5, None
    except Exception as e:
        return None, str(e)


def mt5_status() -> Dict[str, Any]:
    mt5, err = _try_import_mt5()
    if not mt5:
        return {
            "ok": False,
            "note": "MetaTrader5 package no disponible en este Python/venv.",
            "error": err,
        }

    try:
        # initialize() conecta al terminal MT5 abierto/instalado
        ok = mt5.initialize()
        if not ok:
            return {
                "ok": False,
                "note": "mt5.initialize() falló. Abrí MT5 y logueate en tu cuenta.",
                "last_error": mt5.last_error(),
            }

        term = mt5.terminal_info()
        acc = mt5.account_info()

        return {
            "ok": True,
            "note": "MT5 conectado OK.",
            "terminal": term._asdict() if term else None,
            "account": acc._asdict() if acc else None,
            "last_error": mt5.last_error(),
        }

    except Exception as e:
        return {"ok": False, "note": "Excepción en bridge MT5.", "error": str(e)}
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass