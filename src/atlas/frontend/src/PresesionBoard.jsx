import React from "react";

const COLORS = {
  red: "#ff4d4f",
  yellow: "#faad14",
  green: "#52c41a",
  neutral: "#555"
};

export default function PresesionBoard({ data }) {
  if (!data || data.length === 0) {
    return <div style={{ color: "#666", fontStyle: "italic" }}>Esperando datos de presesion...</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {data.map((item) => (
        <div
          key={item.symbol}
          style={{
            display: "grid",
            gridTemplateColumns: "60px 30px 50px 1fr",
            alignItems: "center",
            background: "#1a1a1a",
            padding: "8px 12px",
            borderRadius: 4,
            borderLeft: `4px solid ${COLORS[item.light] || COLORS.neutral}`
          }}
        >
          <div style={{ fontWeight: "bold" }}>{item.symbol}</div>
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: COLORS[item.light] || COLORS.neutral }}></div>
          <div style={{ fontWeight: "bold", color: item.bias === "buy" ? COLORS.green : item.bias === "sell" ? COLORS.red : "#aaa" }}>{item.bias ? item.bias.toUpperCase() : "-"}</div>
          <div style={{ fontSize: "0.85rem", color: "#ccc", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.note}</div>
        </div>
      ))}
    </div>
  );
}