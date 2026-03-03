# src/atlas/bot/superbloque.py

"""
ATLAS — SUPERBLOQUE vFINAL (Forex · Nasdaq · Scalping · Gestión · Prohibiciones)

────────────────────────────────────────────────────────
I) PRINCIPIOS INQUEBRANTABLES
- Contexto > señal
- Continuidad > anticipación
- Menos trades = más dinero
- Silencio es decisión
- Una entrada vale más que tres intentos
- Zonas, no precios exactos

────────────────────────────────────────────────────────
II) ORDEN DE LECTURA (MANDAMIENTO)
Si no se respeta este orden: NO_TRADE
1) Contexto mayor (último impulso dominante)
2) Impulso reciente
3) Corrección
4) Zona
5) Gatillo
6) Gestión

────────────────────────────────────────────────────────
III) CONTEXTO VÁLIDO (FILTRO DURO)
Solo se opera si:
- Hay impulso claro
- Hay corrección real
- No hay rango reactivo
- El precio llega a zona operable
Si falta uno: NO_TRADE (silencio)

────────────────────────────────────────────────────────
IV) ZONA OPERABLE (COMÚN A TODO)
- Corrección mínima válida:
  - 0.5–0.618 aceptable
  - 0.786–0.79 zona reina (preferida)
- Requisitos de corrección:
  - llegada lenta/escalonada
  - pérdida de momentum
  - NO llegada violenta
Corrección rápida/violenta: NO_TRADE

────────────────────────────────────────────────────────
V) GATILLOS PERMITIDOS (ÚNICOS)
Se entra solo con UNO:
A) Cierre a favor en zona
B) Barrida + recuperación
C) Ruptura + retest
Regla: primera reacción avisa, segunda reacción paga.
Sin A/B/C: NO_TRADE

────────────────────────────────────────────────────────
VI) GESTIÓN UNIVERSAL (SELLADA)
- Riesgo fijo por trade: 2%
- Cuando el precio avanza +2% desde la entrada:
  - cerrar 1% de la posición (parcial fijo)
  - SL a BE
  - resto en run
Prohibido:
- mover SL en contra
- promediar
- reentrar por frustración

────────────────────────────────────────────────────────
VII) FOREX (OPTIMIZADO)
- Compra o venta depende del contexto (bidireccional)
- Preferencia: correcciones lentas
Prohibido:
- rangos chicos / mercado chicoteado
- entradas en ruptura o aceleración
- “casi lindo”
TP:
- TP1 temprano y obligatorio (asegurar)
- run solo con cuerpo claro y continuidad

────────────────────────────────────────────────────────
VIII) NASDAQ (OPTIMIZADO)
- Continuidad por tramos
- Corrección profunda preferida: 0.786–1
- Gatillo preferido: B (barrida + recuperación)
Prohibido:
- scalping en rotación/lateral
- entradas en medio de rango
TP:
- por escalones (TP1, TP2, TP3) según recorrido/fibo
- aceptar pausas; solo invalida si cambia contexto

────────────────────────────────────────────────────────
IX) SCALPING (QUIRÚRGICO)
Scalping NO es otro sistema: es recorte del setup.
Permitido solo si:
- hubo impulso previo (desplazamiento)
- hay micro-corrección
- decisión rápida
Reglas:
- 1 entrada
- 1 TP principal (corto)
- si no acelera: salir/BE
- si tarda demasiado: cancelar
Scalping lento = scalping muerto

────────────────────────────────────────────────────────
X) PROHIBICIONES ABSOLUTAS
- Entradas tempranas
- “Casi lindo”
- Duda > 10 segundos
- Zonas muertas (sin aceptación)
- Reintentos múltiples
- Analizar después de entrar (setup ya definido)

────────────────────────────────────────────────────────
XI) ELLIOTT / EOSS (USO REAL, NO ACADÉMICO)
No se cuentan ondas.
Solo responder:
1) ¿Impulso o corrección?
2) ¿El impulso ya fue pagado?
3) ¿Pausa o agotamiento?
Se usa como filtro, no como gatillo.

────────────────────────────────────────────────────────
XII) EXPECTATIVA REALISTA POR ACTIVO
- Forex: recorrido medio y limpio
- Nasdaq: tramos explosivos con pausas
- Scalping: corto y rápido
Esperar de más = perder trades ganados

────────────────────────────────────────────────────────
XIII) CHECKLIST FINAL (ANTES DE ENTRAR)
Si falla 1: SILENCIO
- Contexto claro
- Corrección válida
- Zona viva
- Gatillo limpio (A/B/C)
- Gestión definida

────────────────────────────────────────────────────────
FIN SUPERBLOQUE ATLAS vFINAL
"""