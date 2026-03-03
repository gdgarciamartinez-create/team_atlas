# TEAM ATLAS — Definition of DONE (Scope Lock)

Este documento “clava” el alcance. Si algo no está aquí, NO entra por accidente.

---

## V1 — DONE (Diagnóstico estable)

V1 se considera DONE cuando se cumple TODO:

### Backend / API
- [ ] `/api/status` responde `ok=true`.
- [ ] `/api/snapshot` responde `200` para:
  - `world=ATLAS_IA`
  - `atlas_mode=SCALPING_M1` y `SCALPING_M5`
  - `symbol=XAUUSDz` y al menos 1 símbolo FX con sufijo `z`
- [ ] El snapshot incluye siempre:
  - `world`, `atlas_mode`, `symbol`, `tf`, `ts_ms`
  - `analysis` con `status`, `reason`, `detail`
  - `ui.rows` (aunque esté vacío)
  - `ui.meta` con información mínima (timestamp y estado)
- [ ] No hay crashes del server por imports rotos o atributos inexistentes.

### Estados (sin resets)
- [ ] Existen y se usan 3 estados:
  - `WAIT`
  - `ZONA`
  - `GATILLO`
- [ ] El estado NO se reinicia solo por refresh/polling de UI.
- [ ] En `ZONA`: el plan queda congelado (no cambia cada refresh).
- [ ] En `GATILLO`: se emite señal solo en el momento de entrada (vela gatillo).

### UI
- [ ] UI hace polling único a `/api/snapshot`.
- [ ] UI NO resetea el símbolo/timeframe sin acción del usuario.
- [ ] UI muestra estado actual (`WAIT/ZONA/GATILLO`) sin parpadeos.

### Logs / Trazabilidad
- [ ] Cada snapshot deja un rastro (log) con:
  - world, mode, symbol, tf
  - estado (WAIT/ZONA/GATILLO)
  - reason/detail
- [ ] Si no hay trade: razón clara (`NO_TRADE` + motivo).

✅ Cuando todo lo anterior esté OK, V1 queda cerrada.

---

## V2 — DONE (Ejecución MT5 + Gestión)

V2 se considera DONE cuando, además de V1:

### Ejecución (MT5)
- [ ] El bot puede enviar orden real o simulada con wrapper único.
- [ ] Valida volumen, SL/TP, y maneja errores de MT5 sin romper el backend.

### Gestión
- [ ] BE automático según regla.
- [ ] Parciales (TP1) según regla.
- [ ] Cierre por invalidación / por tiempo / por evento.
- [ ] Registro de cada acción (entry / parcial / BE / cierre).

✅ Cuando todo lo anterior esté OK, V2 queda cerrada.

---

## Regla Anti-Humo (Scope Lock)
- NO se agregan “features” fuera de V1/V2 sin actualizar este archivo.
- Si aparece discusión nueva de gatillos/zonas: se redirige a `doctrine.md`.