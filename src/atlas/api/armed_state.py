from __future__ import annotations

class ArmedState:
    def __init__(self):
        self.armed = False  # OFF por defecto (mandamiento)
        self.last_exec = None

ARMED = ArmedState()