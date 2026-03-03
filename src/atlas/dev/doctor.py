# src/atlas/dev/doctor.py
from __future__ import annotations
import importlib

CRITICAL_IMPORTS = [
    "atlas.api.main",
    "atlas.api.routes.router",
    "atlas.api.routes.snapshot",
    "atlas.core.doctrine_guard",
    "atlas.core.gap_fsm",
]

def main() -> int:
    print("ATLAS DOCTOR ✅")
    ok = True
    for mod in CRITICAL_IMPORTS:
        try:
            importlib.import_module(mod)
            print(f"  OK   {mod}")
        except Exception as e:
            ok = False
            print(f"  FAIL {mod} -> {type(e).__name__}: {e}")

    if not ok:
        print("\n🚨 Hay FAIL. No levantes uvicorn todavía.")
        return 1

    print("\n✅ Todo OK. Podés levantar uvicorn.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

