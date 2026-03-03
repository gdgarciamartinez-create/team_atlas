# TEAM ATLAS — Doctrina Congelada (No se vuelve a discutir)

Este archivo es la fuente de verdad doctrinal.  
El motor lo referencia para dejar constancia de que NO se reabre el diseño.

---

## Principio operativo
- El sistema **solo avisa** cuando ocurre la **vela gatillo** (momento de entrada).
- Si no hay gatillo válido, el sistema se calla (NO_TRADE con razón clara).
- El silencio operativo es una decisión válida.

---

## Estados oficiales (únicos)
1) WAIT  
- No hay zona válida o no hay contexto habilitante.
- Resultado: `NO_TRADE`.

2) ZONA  
- Hay una zona válida y el plan queda **congelado**.
- El plan NO cambia en cada refresh.
- Resultado: `NO_TRADE` mientras no haya confirmación.

3) GATILLO  
- Aparece la vela/confirmación de entrada (trigger).
- Resultado: `SIGNAL` exactamente en el momento de entrada.

---

## Anti-reset (regla dura)
- `entry/SL/TP` no deben “bailar” con cada refresh.
- En `ZONA`: el plan se mantiene fijo hasta:
  - invalidación, o
  - evolución natural a `GATILLO`.

---

## Universos y activos
- Universo FX: todos los pares EUR* y USD* (excluye BTC).
- Oro: `XAUUSDz` separado (módulo propio).

---

## Qué NO se hace en V1
- No ejecución real en MT5.
- No gestión (BE/parciales/cierre).
- No optimización por resultados aislados.