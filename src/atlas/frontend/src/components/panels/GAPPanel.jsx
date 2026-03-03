// src/atlas/frontend/src/components/panels/GAPPanel.jsx
import { Card, Badge } from "../ui.jsx";
import { fmtDateTimeSantiago, isInGapWindowSantiago, gapWindowLabel } from "../../utils/format.js";

export default function GAPPanel({ snapshot, symbol }) {
  const ts = Number(snapshot?.ts_ms || Date.now());

  // Si backend trae analysis.gap.in_window lo usamos; si no, fallback a cálculo UI.
  const gap = snapshot?.analysis?.gap || {};
  const hasBackendFlag = typeof gap?.in_window === "boolean";
  const inWindow = hasBackendFlag ? Boolean(gap.in_window) : isInGapWindowSantiago(ts);

  const tone = inWindow ? "OK" : "WAIT";
  const windowText = inWindow ? "EN VENTANA GAP" : "FUERA DE VENTANA";

  const sched = gapWindowLabel(); // verano: 19:55–20:30 (apertura ~20:00)

  return (
    <Card
      title="GAP"
      subtitle={`API: GAP • ${symbol} • Hora: ${fmtDateTimeSantiago(ts)} (Santiago) • Ventana: ${sched}`}
      right={<Badge tone={tone} text={windowText} />}
    >
      <div style={{ display: "grid", gap: 10 }}>
        <div style={{ fontSize: 12, opacity: 0.82, lineHeight: 1.45 }}>
          <b>Regla:</b> el gap es una deuda potencial. Se opera solo si falla la continuidad, con
          secuencia: <b>extensión → fallo → ruptura → recuperación</b>.
        </div>

        {/* Si el backend entrega texto/nota, lo mostramos */}
        {gap?.note && (
          <div style={{
            padding: 12,
            borderRadius: 14,
            border: "1px solid rgba(255,255,255,0.10)",
            background: "rgba(0,0,0,0.20)",
            fontSize: 12,
            opacity: 0.85
          }}>
            {gap.note}
          </div>
        )}
      </div>
    </Card>
  );
}
