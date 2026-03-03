// src/atlas/frontend/src/components/panels/PresesionPanel.jsx
import { useMemo } from "react";
import { Card, Badge, Btn } from "../ui.jsx";
import { fmtDateTimeSantiago, isInPresesionWindowSantiago } from "../../utils/format.js";

export default function PresesionPanel({ snapshot, symbol, tf, setTf }) {
  const ts = Number(snapshot?.ts_ms || Date.now());

  const pres = snapshot?.analysis?.presesion || {};
  const inWindowBackend = Boolean(pres?.in_window);
  const followActive = Boolean(pres?.follow_active);

  // Fallback si backend no trae presesion (blindaje)
  const inWindow = typeof pres?.in_window === "boolean"
    ? inWindowBackend
    : isInPresesionWindowSantiago(ts);

  const tfLabel = useMemo(() => {
    if (tf === "M3") return "3 minutos";
    if (tf === "M5") return "5 minutos";
    return tf;
  }, [tf]);

  const tone = inWindow ? "OK" : "WAIT";
  const windowText = inWindow ? "EN VENTANA PRESESIÓN" : "FUERA DE VENTANA";

  const followTone = followActive ? "OK" : "WAIT";
  const followText = followActive ? "SEGUIMIENTO ACTIVO" : "SEGUIMIENTO APAGADO (11:00)";

  return (
    <Card
      title="PRESESIÓN"
      subtitle={`API: PRESESION • ${symbol} • TF: ${tfLabel} • Hora: ${fmtDateTimeSantiago(ts)} (Santiago)`}
      right={<Badge tone={tone} text={windowText} />}
    >
      <div style={{ display: "grid", gap: 12 }}>
        {/* TF selector (M3 / M5) */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <Btn tone={tf === "M3" ? "hot" : "ghost"} onClick={() => setTf("M3")}>M3</Btn>
          <Btn tone={tf === "M5" ? "hot" : "ghost"} onClick={() => setTf("M5")}>M5</Btn>
        </div>

        {/* Nota fija (informativa, no interactiva) */}
        <div style={{ fontSize: 12, opacity: 0.80, lineHeight: 1.45 }}>
          <b>PRESESIÓN</b> es margen operativo previo a NY. <br />
          <b>Fibo 0.79</b> se usa <b>solo aquí</b> (OB + IMB). <br />
          Esta pantalla es <b>informativa</b> (no interactiva).
        </div>

        {/* Semáforo seguimiento */}
        <div style={{
          padding: 12,
          borderRadius: 14,
          border: "1px solid rgba(255,255,255,0.10)",
          background: "rgba(0,0,0,0.20)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 10
        }}>
          <div>
            <div style={{ fontWeight: 900, fontSize: 12, opacity: 0.85 }}>Seguimiento</div>
            <div style={{ fontSize: 12, opacity: 0.75 }}>
              Activo solo entre <b>07:00</b> y <b>11:00</b> (Santiago)
            </div>
          </div>
          <Badge tone={followTone} text={followText} />
        </div>

        {/* Resumen (solo lectura) */}
        <div style={{
          padding: 12,
          borderRadius: 14,
          border: "1px solid rgba(255,255,255,0.10)",
          background: "rgba(0,0,0,0.20)",
          display: "grid",
          gap: 8
        }}>
          <div style={{ fontWeight: 900, fontSize: 12, opacity: 0.85 }}>Resumen</div>
          <div style={{ fontSize: 12, opacity: 0.82, lineHeight: 1.5 }}>
            • Ventana: <b>{pres?.window || "07:00–11:00 Santiago"}</b><br />
            • Estado: <b>{windowText}</b><br />
            • TF análisis: <b>{tf}</b><br />
            • OB: <b>{pres?.ob || "—"}</b><br />
            • IMB: <b>{pres?.imb || "—"}</b><br />
            • Fibo: <b>0.79 SOLO PRESESIÓN</b><br />
          </div>

          <div style={{ fontSize: 12, opacity: 0.70, marginTop: 4 }}>
            {pres?.note || "—"}
          </div>
        </div>
      </div>
    </Card>
  );
}
