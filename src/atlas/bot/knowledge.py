import json
from pathlib import Path

_KNOWLEDGE_CACHE = None

def load_knowledge() -> dict:
    global _KNOWLEDGE_CACHE
    if _KNOWLEDGE_CACHE is not None:
        return _KNOWLEDGE_CACHE

    p = Path(__file__).resolve().parent / "knowledge" / "atlas_knowledge.json"
    if not p.exists():
        _KNOWLEDGE_CACHE = {}
        return _KNOWLEDGE_CACHE

    try:
        _KNOWLEDGE_CACHE = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        _KNOWLEDGE_CACHE = {}
    return _KNOWLEDGE_CACHE

def get_symbol_knowledge(symbol: str) -> dict:
    kb = load_knowledge()
    if not symbol:
        return {}
    return kb.get(symbol, {})
