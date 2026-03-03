import React from "react";

export default function TriggerBanner({ trigger, silence_reason, presesion_active }) {
  if (!presesion_active) {
    return (
      <div style={{ padding: 10, border: "1px solid #444", borderRadius: 8, marginBottom: 10, opacity: 0.75 }}>
        <b>ATLAS: SILENCIO</b>
        <span style={{ marginLeft: 8, fontSize: "0.85rem", color: "#666" }}>
          (FUERA_DE_PRESESION)
        </span>
      </div>
    );
  }

  if (!trigger) {
    return (
      <div style={{ padding: 10, border: "1px solid #333", borderRadius: 8, marginBottom: 10 }}>
        <b>ATLAS: SILENCIO</b>
        <span style={{ marginLeft: 8, fontSize: "0.85rem", color: "#888" }}>
          ({silence_reason || "ESPERANDO_SETUP"})
        </span>
      </div>
    );
  }

  return (
    <div style={{ padding: 12, border: "2px solid #52c41a", borderRadius: 8, marginBottom: 10 }}>
      <b>ATLAS 🔫 GATILLO VÁLIDO</b>
      <div style={{ fontFamily: "Consolas, monospace", fontSize: "0.9rem", marginTop: 8 }}>
        KIND: {trigger.kind} | SIDE: {trigger.side} | LEVEL: {trigger.level}
      </div>
    </div>
  );
}
