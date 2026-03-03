from dataclasses import dataclass, field
from typing import Dict, List
import time

@dataclass
class Bitacora:
    counts: Dict[str, int] = field(default_factory=lambda: {
        "ATLAS_IA_FOREX": 0,
        "ATLAS_IA_SCALPING": 0,
        "PRESESION": 0,
        "GAP": 0,
        "GATILLO": 0,
    })
    last_events: List[dict] = field(default_factory=list)

    def push(self, world_key: str, symbol: str, action: str, note: str = "") -> None:
        self.counts[world_key] = int(self.counts.get(world_key, 0)) + 1
        self.last_events.append({
            "ts": int(time.time()),
            "world": world_key,
            "symbol": symbol,
            "action": action,
            "note": note,
        })
        # mantener liviano
        if len(self.last_events) > 200:
            self.last_events = self.last_events[-200:]

BITACORA = Bitacora()