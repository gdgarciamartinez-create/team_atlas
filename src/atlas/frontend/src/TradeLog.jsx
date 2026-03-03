import React from "react";

export default function TradeLog() {
  return (
    <div className="card m-bit" style={{ minHeight: 520 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 800 }}>📓 Bitácora</div>
          <div style={{ color: "var(--muted)", marginTop: 4 }}>
            Registro de operaciones + estadísticas (winrate, R, etc.)
          </div>
        </div>
        <span className="badge">v1 (placeholder)</span>
      </div>

      <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        <div className="card" style={{ background: "rgba(0,0,0,0.25)" }}>
          <div style={{ color: "var(--muted)", fontSize: 12 }}>Operaciones</div>
          <div style={{ fontSize: 22, fontWeight: 800 }}>0</div>
        </div>
        <div className="card" style={{ background: "rgba(0,0,0,0.25)" }}>
          <div style={{ color: "var(--muted)", fontSize: 12 }}>Winrate</div>
          <div style={{ fontSize: 22, fontWeight: 800 }}>0%</div>
        </div>
        <div className="card" style={{ background: "rgba(0,0,0,0.25)" }}>
          <div style={{ color: "var(--muted)", fontSize: 12 }}>R promedio</div>
          <div style={{ fontSize: 22, fontWeight: 800 }}>0.00</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 14, background: "rgba(0,0,0,0.25)" }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Historial</div>
        <div style={{ color: "var(--muted)" }}>Sin operaciones registradas aún.</div>
      </div>
    </div>
  );
}