from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # repo root (tools/..)

TARGETS = [
    "gap_build_row",
    "presesion_build_row",
    "atlas_ia_build_row",
    "gatillo_build_row",
]

# reemplazos por función evaluadora (lo que debe importarse)
REPL_MAP = {
    "gap_build_row": "eval_gap",
    "presesion_build_row": "eval_presesion",
    "atlas_ia_build_row": "eval_atlas_ia",
    "gatillo_build_row": "eval_gatillo",
}

# módulos esperados (ajustá si en tu repo difieren)
MOD_MAP = {
    "gap_build_row": "atlas.bot.gap.engine",
    "presesion_build_row": "atlas.bot.presesion.engine",
    "atlas_ia_build_row": "atlas.bot.atlas_ia.engine",
    "gatillo_build_row": "atlas.bot.gatillo.engine",
}

PY_FILES = [p for p in ROOT.rglob("*.py") if ".venv" not in str(p).lower() and "\\.venv" not in str(p).lower()]

def fix_text(text: str) -> tuple[str, bool, list[str]]:
    changed = False
    notes: list[str] = []

    for bad in TARGETS:
        good = REPL_MAP[bad]
        mod = MOD_MAP[bad]

        # 1) from X import bad  -> from X import good
        pat1 = re.compile(rf"(^\s*from\s+{re.escape(mod)}\s+import\s+)(.*\b{re.escape(bad)}\b.*)$", re.MULTILINE)
        def _sub1(m):
            nonlocal changed
            line = m.group(0)
            newline = line.replace(bad, good)
            if newline != line:
                changed = True
                notes.append(f"Replaced import name: {bad} -> {good} in {mod}")
            return newline

        text2 = pat1.sub(_sub1, text)

        # 2) cualquier uso directo de bad(...)  -> good(...)
        # (esto es más agresivo; lo dejamos solo si aparece la llamada)
        pat2 = re.compile(rf"\b{re.escape(bad)}\s*\(")
        if pat2.search(text2):
            text3 = pat2.sub(f"{good}(", text2)
            if text3 != text2:
                changed = True
                notes.append(f"Replaced call: {bad}(...) -> {good}(...)")
            text2 = text3

        text = text2

    return text, changed, notes

def main():
    touched = 0
    for p in PY_FILES:
        original = p.read_text(encoding="utf-8", errors="ignore")
        updated, changed, notes = fix_text(original)
        if changed:
            # backup
            bak = p.with_suffix(p.suffix + ".bak")
            if not bak.exists():
                bak.write_text(original, encoding="utf-8")
            p.write_text(updated, encoding="utf-8")
            touched += 1
            print(f"\n[UPDATED] {p.relative_to(ROOT)}")
            for n in notes:
                print("  -", n)

    print(f"\nDone. Files modified: {touched}")

if __name__ == "__main__":
    main()
