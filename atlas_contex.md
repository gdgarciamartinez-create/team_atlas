# TEAM_ATLAS

## Estructura
- Backend FastAPI: src/atlas/api
- Lógica bot: src/atlas/bot
- Frontend React + Vite: src/atlas/frontend
- Runtime principal: src/atlas/runtime.py

## Reglas del proyecto
- No duplicar endpoints
- Todo endpoint bajo /api
- El frontend consume /api/snapshot
- No crear archivos nuevos sin permiso
- No romper arquitectura existente
- Siempre explicar primero y editar después

## Estados importantes
WAIT
WAIT_GATILLO
SIGNAL
ENTRY
IN_TRADE
TP1
TP2
CLOSED

## Reglas operativas
- entry/sl/tp no deben variar en cada refresh
- WAIT_GATILLO debe congelar el plan
- SIGNAL define el plan final