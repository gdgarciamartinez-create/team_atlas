from dataclasses import dataclass
from typing import Any, Dict, Optional
import copy

@dataclass
class FeedControl:
    mode: str = "pause"   # "play" | "pause"
    ticks: int = 0
    last_snapshot: Optional[Dict[str, Any]] = None

    def play(self) -> None:
        self.mode = "play"

    def pause(self) -> None:
        self.mode = "pause"

    def reset(self) -> None:
        self.ticks = 0
        self.last_snapshot = None

    def on_tick(self) -> None:
        self.ticks += 1

    def set_last_snapshot(self, snap: Dict[str, Any]) -> None:
        self.last_snapshot = copy.deepcopy(snap)

    def get_last_snapshot(self) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self.last_snapshot) if self.last_snapshot is not None else None

    def state(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "ticks": self.ticks,
            "has_last_snapshot": self.last_snapshot is not None,
        }

feed_control = FeedControl()