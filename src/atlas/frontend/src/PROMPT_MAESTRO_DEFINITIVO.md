# 🧠📘 PROMPT MAESTRO DEFINITIVO — TEAM ATLAS

**(Contrato técnico + diseño UI + flujo operativo + límites IA)**

## CONTEXTO GENERAL

Estás construyendo **TEAM ATLAS**, un sistema de análisis de trading **NO ejecutor**, orientado a:
- Forex
- XAUUSD
- Scalping táctico
- Análisis contextual y pedagógico

**ATLAS no opera, no gestiona, no insiste.**
ATLAS observa, diagnostica, explica y alerta.

El humano ejecuta.

---

## PRINCIPIO FUNDAMENTAL

ATLAS opera por **estado del mercado**, no por patrones ni indicadores sueltos.

**Flujo obligatorio e inalterable:**
OBSERVAR → CONTEXTO → ZONA → TIMING → POI (Punto Óptimo de Ingreso) → ALERTA → SILENCIO OPERATIVO

Si un paso falla → **NO_TRADE**.

---

## DEFINICIÓN DE POI (OBLIGATORIA)

**POI = Punto Óptimo de Ingreso**

Un POI solo existe cuando:
1. Contexto correcto
2. Zona correcta
3. Timing confirmado
4. Riesgo definido
5. RR mínimo aceptable (≥ 2.5)

**Formato estándar de POI (cuando existe):**
```text
POI — XAUUSD
BUY 4500.56
SL 4479.76
Parcial 4550.67
TP2 4632.43
RR estimado: 3.1
```

Sin POI → no hay trade.

---

## MUNDOS OPERATIVOS (NO LLAMAR “VENTANAS”)

### 1️⃣ GENERAL
- Observación global del mercado.
- No genera POI.
- Solo estado y contexto.

### 2️⃣ PRESESION (con S, ley permanente)
**Definición:** Contexto previo a NY. Es temporal, no geométrico.

**Función:**
- Detectar contexto
- Detectar zonas potenciales
- Avisar, no ejecutar

**Alarma PRESESION:**
- Activable/desactivable
- Avisa cuando: Franja horaria válida + Contexto alineado + Zona relevante detectada
- Mensaje ejemplo: *“ATLAS: Presesión activa en XAUUSD. Contexto válido. Aún sin POI.”*

### 3️⃣ GAP (solo XAUUSD)
**Reglas duras:**
- El gap es deuda potencial, nunca señal
- Solo se considera si falla la continuidad
- Debe cumplirse el ritual completo: Exageración → Fallo de continuidad → Ruptura → Recuperación → Aceptación

**Alarma GAP:**
- Solo se activa si el ritual está casi completo
- Nunca anticipa

### 4️⃣ GATILLOS
**Motor sellado.** Solo existen 3 gatillos válidos:
1. Toque directo 0.79
2. Barrida + recuperación
3. Ruptura + retest secundario

**Función:**
- Mostrar símbolos en estado de gatillo
- Generar POI cuando corresponde

### 5️⃣ ATLAS IA
**Rol:** Explicar y simular, no decidir por el humano.

**Muestra:**
- Escenarios posibles
- Qué ve ATLAS
- Qué espera
- Qué invalida
- RR estimado
- Simulación sobre cuenta 10.000 USD

**Modos:** Forex / Scalping

**Alarma IA:**
- Avisa cuando un escenario es válido
- No envía POI si no está completo

---

## SISTEMA DE ALERTAS (LOS 3 NIVELES)

Todas las alertas son activables por el usuario:

🟡 **Contexto:** “Puede haber movimiento”
🟠 **Escenario válido:** “Esto es interesante”
🔴 **POI:** “Este es el punto óptimo”

Las alertas se envían por: **UI** y **Telegram**.
- Nunca se repiten.
- Nunca se persiguen.

---

## UI — DISEÑO POR PANTALLA

### Dashboard
- Estado general
- Mundo activo
- Hora / sesión
- Botón global de alertas

### Presesión
- Gráfico velas reales (M1)
- Símbolo por defecto: XAUUSD
- Panel inferior con estados: Franja, Contexto, Zona, Timing
- Botón 🔔 Activar alerta Presesión

### GAP
- Solo XAUUSD
- Gap visual
- Checklist del ritual
- Botón 🔔 Activar alerta GAP

### Gatillos
- Lista horizontal de símbolos
- Click carga gráfico
- Estados de gatillo
- Si hay POI → habilita alerta final

### Atlas IA
- Selector Forex / Scalping
- Lista de escenarios
- Explicaciones claras
- RR y riesgo
- Botón de alerta por escenario

---

## SIMULACIÓN Y MÉTRICAS

ATLAS mantiene:
- Conteo de trades analizados
- RR promedio
- Winrate simulado
- Riesgo por trade
- Cuenta base: 10.000 USD

El humano:
- Revisa semanalmente
- Completa Excel real
- Decide ajustes

ATLAS no se optimiza por resultados aislados.

---

## LÍMITES NO NEGOCIABLES

**ATLAS NO PUEDE:**
- Ejecutar trades
- Gestionar SL/TP
- Repetir alertas
- Convencer al humano
- Forzar entradas

**ATLAS DEBE:**
- Guardar silencio cuando no hay trade
- Explicar el NO_TRADE
- Priorizar continuidad sobre anticipación
- Respetar geometría, tiempo y estado

---

## ESTADO ACTUAL DEL PROYECTO

- Arquitectura backend + frontend: OK
- Snapshot único: OK
- Velas reales MT5: OK
- UI base funcional: OK
- Lógica operativa definida: OK

**Faltante (siguiente fase técnica):**
- Conectar UI a cada mundo
- Colores por estado
- Checklist visual
- Alertas Telegram
- Resumen semanal automático

---

## REGLA FINAL

**ATLAS no entra porque puede.**
**ATLAS entra cuando el mercado ya se explicó solo.**