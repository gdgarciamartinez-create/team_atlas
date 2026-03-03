"""
TEAM ATLAS — BLOQUE A
LÓGICA CENTRAL Y FILOSOFÍA OPERATIVA (SELLADA)

1. NATURALEZA DEL SISTEMA
ATLAS no es un bot de ejecución.
ATLAS es un sistema de lectura, diagnóstico y decisión.

Su función es replicar el análisis humano disciplinado,
no operar mercados ni buscar beneficios directos.

2. PRINCIPIO MADRE
ATLAS opera estados del mercado, no señales.

Nunca entra por:
- patrones aislados
- indicadores sueltos
- necesidad de operar
- anticipación

Solo actúa cuando el mercado ya se explicó por sí mismo.
"""

from enum import Enum

# 3. ACCIONES POSIBLES
class AtlasAction(Enum):
    NO_TRADE = "NO_TRADE"
    OBSERVE = "OBSERVE"
    SETUP_VALIDO = "SETUP_VALIDO"

# 4. CONDICIONES DE NO_TRADE
# ATLAS devuelve NO_TRADE cuando:
# - No hay contexto claro
# - Falta información (velas insuficientes)
# - El precio está en zona sin timing
# - Hay aceptación contraria
# - No se cumple la doctrina (doc_trine_ok = false)
# NO_TRADE es una decisión válida y protegida.

# 5. CONTEXTO Y DOCTRINA
# Toda decisión debe cumplir:
# - Coherencia estructural
# - Relación impulso–corrección válida
# - Proporción precio–tiempo
# - Ausencia de exageración no resuelta
# Si la doctrina falla, no se permite operar.

# 6. GAP (XAUUSD)
# El GAP:
# - No es señal
# - No es entrada
# - Es una deuda potencial
# Solo se considera si:
# - Hubo exageración previa
# - Falló la continuidad
# - Existe ruptura + recuperación
# - El tiempo valida el escenario
# Si no, GAP descartado.

# 7. TIEMPO COMO FILTRO
# Precio correcto en tiempo incorrecto = NO_TRADE.
# El tiempo invalida niveles, no los confirma.

# 8. HIGIENE COGNITIVA
# ATLAS está diseñado para eliminar:
# - FOMO
# - anticipación
# - sobreinterpretación
# - ego operativo
# - necesidad de acción
# El silencio operativo es una acción.

# 9. REGISTRO Y SEGUIMIENTO
# ATLAS registra:
# - Contexto
# - Decisión
# - Razón
# - Estado del bot
# El seguimiento se realiza externamente (vía Excel / CSV / Journal manual).

# 10. PROHIBICIONES
# ATLAS NO:
# - ejecuta trades
# - gestiona riesgo
# - optimiza por resultados
# - modifica reglas por pérdidas
# Las reglas solo cambian por evidencia estructural repetida.

# FIN DEL BLOQUE A
# ESTADO: SELLADO