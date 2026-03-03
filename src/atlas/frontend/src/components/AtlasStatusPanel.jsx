// src/atlas/frontend/src/components/AtlasStatusPanel.jsx
import React, { useMemo } from "react";
import { Card, Badge } from "./ui.jsx";

function Pill({ tone, label, sub }) {
  return (
    <div
      style={{
        border: "1px solid rgba(255,255,255,0.10)",
        background: "rgba(255,255,255,0.04)",
        borderRadius: 14,
        padding: 12,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 10,
      }}
    >
      <div>
        <div style={{ fontWeight: 900 }}>{label}</div>
        <div style={{ fontSize: 12, opacity: 0.75 }}>{sub}</div>
      </div>
      <Badge tone={tone} text={label} />
    </div>
  );
}

export default function AtlasStatusPanel({ world, snapshot }) {
  const action = snapshot?.analysis?.action || "WAIT";
  const reason = snapshot?.analysis?.reason || "—";
  const frozen = !!snapshot?.analysis?.frozen;

  const tone = useMemo(() => {
    if (action === "SIGNAL") return "OK";
    if (action === "WAIT_GATILLO") return "hot";
    return "WAIT";
  }, [action]);

  const label = useMemo(() => {
    if (action === "SIGNAL") return "GATILLO";
    if (action === "WAIT_GATILLO") return "ZONA";
    return "WAIT";
  }, [action]);

  return (
    <Card title="Estado" subtitle={`Mundo: ${world}`} right={<Badge tone={tone} text={label} />}>
      <div style={{ display: "grid", gap: 10 }}>
        <Pill
          tone={tone}
          label={label}
          sub={`${reason}${frozen ? " • congelado ✅" : ""}`}
        />

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          <div style={{ borderRadius: 14, padding: 12, border: "1px solid rgba(255,255,255,0.10)", background: "rgba(255,255,255,0.03)" }}>
            <div style={{ fontWeight: 900 }}>WAIT</div>
            <div style={{ fontSize: 12, opacity: 0.7 }}>Sin plan</div>
          </div>
          <div style={{ borderRadius: 14, padding: 12, border: "1px solid rgba(255,255,255,0.10)", background: "rgba(255,255,255,0.03)" }}>
            <div style={{ fontWeight: 900 }}>ZONA</div>
            <div style={{ fontSize: 12, opacity: 0.7 }}>Plan congelado</div>
          </div>
          <div style={{ borderRadius: 14, padding: 12, border: "1px solid rgba(255,255,255,0.10)", background: "rgba(255,255,255,0.03)" }}>
            <div style={{ fontWeight: 900 }}>GATILLO</div>
            <div style={{ fontSize: 12, opacity: 0.7 }}>Condición lista</div>
          </div>
        </div>
      </div>
    </Card>
  );
}
