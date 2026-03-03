# src/atlas/bot/worlds/time_windows.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time as dtime
from typing import Optional


@dataclass
class WindowDecision:
  world: str
  reason: str
  now_local: str


def _parse_hhmm(hhmm: str) -> dtime:
  hh, mm = hhmm.split(":")
  return dtime(hour=int(hh), minute=int(mm))


def _in_range(now: dtime, start: dtime, end: dtime) -> bool:
  # rango normal (no cruza medianoche)
  if start <= end:
    return start <= now <= end
  # rango que cruza medianoche
  return now >= start or now <= end


def pick_world_by_time(
  now: Optional[datetime] = None,
  season_mode: str = "INV",  # INV | VER (Chile)
) -> WindowDecision:
  """
  Decide el world "prioritario" según hora local (Santiago),
  manteniendo la lógica acordada del proyecto:
  - Primero GAP (ventana detección)
  - Si no, ventanas Londres/NY
  - Si no, ATLAS_IA (laboratorio) o FOREX como fallback (pero aquí devolvemos ATLAS_IA)
  """
  now = now or datetime.now()
  t = now.time()
  season_mode = (season_mode or "INV").upper().strip()

  # Ventanas por modo (guardadas en memoria del proyecto)
  # INV: Londres 02-06, NY 07-09, GAP 19:55-20:30
  # VER: Londres 03-07, NY 08-10, GAP 20:55-21:30
  if season_mode == "VER":
    london = (_parse_hhmm("03:00"), _parse_hhmm("07:00"))
    ny = (_parse_hhmm("08:00"), _parse_hhmm("10:00"))
    gap = (_parse_hhmm("20:55"), _parse_hhmm("21:30"))
  else:
    london = (_parse_hhmm("02:00"), _parse_hhmm("06:00"))
    ny = (_parse_hhmm("07:00"), _parse_hhmm("09:00"))
    gap = (_parse_hhmm("19:55"), _parse_hhmm("20:30"))

  if _in_range(t, gap[0], gap[1]):
    return WindowDecision(world="GAP", reason="gap_window", now_local=now.isoformat())

  if _in_range(t, london[0], london[1]):
    return WindowDecision(world="FOREX", reason="london_window", now_local=now.isoformat())

  if _in_range(t, ny[0], ny[1]):
    return WindowDecision(world="FOREX", reason="ny_window", now_local=now.isoformat())

  return WindowDecision(world="ATLAS_IA", reason="outside_windows", now_local=now.isoformat())