export function explainReason(code) {
  const map = {
    OK: "Todo alineado: contexto + zona + gatillo + plan.",
    NO_CONTEXT: "No hay impulso claro en TF mayor.",
    RANGE_REACTIVE: "Mercado en rango/reactivo, baja continuidad.",
    CONFLICT_DIRECTION: "TF mayor y ejecución no coinciden.",
    NO_0_786_TOUCH: "No llegó a la zona 0.786–0.79.",
    CORRECTION_NOT_VALID: "Corrección violenta o sin desaceleración.",
    CHAOTIC_ARRIVAL: "Llegada caótica (mechas/solape).",
    NO_TRIGGER: "No apareció gatillo A/B/C.",
    SETUP_EXPIRED: "Setup viejo: tardó demasiado sin decidir.",
    WINDOW_LIMIT_REACHED: "Ya hubo trade para ese símbolo en la ventana.",
    GAP_NOT_VALID: "Gap no es real/limpio (threshold no cumple).",
    RISK_NOT_FEASIBLE: "No hay plan sano (entry/SL/TPs).",
  };
  return map[code] || "Sin explicación (code nuevo).";
}