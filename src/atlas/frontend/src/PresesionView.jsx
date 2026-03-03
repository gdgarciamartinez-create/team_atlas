import React from "react";

export default function PresesionView({ onBack }) {
  return (
    <div style={{ padding: 20, background: "#000", minHeight: "100vh", color: "#ccc", fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 20 }}>
        <button onClick={onBack} style={{ background: "transparent", border: "none", color: "#666", cursor: "pointer", fontSize: "1.2rem" }}>←</button>
        <h2 style={{ margin: 0 }}>MODO PRESESIÓN</h2>
      </div>
      
      <div style={{ display: "grid", gap: 10, maxWidth: 600 }}>
        <Row sym="XAUUSD" bias="NEUTRAL" status="WAIT" color="#faad14" />
        <Row sym="EURUSD" bias="BULLISH" status="READY" color="#52c41a" />
        <Row sym="GBPUSD" bias="BEARISH" status="NO TRADE" color="#ff4d4f" />
        <Row sym="NAS100" bias="NEUTRAL" status="WAIT" color="#faad14" />
      </div>
    </div>
  );
}

const Row = ({ sym, bias, status, color }) => (
  <div style={{ 
    display: "grid", gridTemplateColumns: "1fr 1fr 1fr", alignItems: "center", 
    background: "#111", padding: "15px 20px", borderRadius: 8, borderLeft: `5px solid ${color}` 
  }}>
    <div style={{ fontWeight: "bold", fontSize: "1.1rem" }}>{sym}</div>
    <div style={{ color: "#888" }}>{bias}</div>
    <div style={{ fontWeight: "bold", color: color }}>{status}</div>
  </div>
);