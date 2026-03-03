# src/atlas/api/data_source.py
from dataclasses import dataclass

@dataclass
class Candle:
    ts: int
    o: float
    h: float
    l: float
    c: float
    v: float