import React from "react";

export default function Home({ onNavigate }) {
  return (
    <div style={{
      height: "100vh", background: "#050505", color: "#fff",
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      fontFamily: "sans-serif"
    }}>
      <h1 style={{ fontSize: "4rem", letterSpacing: "10px", marginBottom: "40px", textShadow: "0 0 20px rgba(255,255,255,0.1)" }}>ATLAS</h1>
      <div style={{ display: "flex", gap: "20px" }}>
        <button onClick={() => onNavigate("presesion")} style={btnStyle}>PRESESIÓN</button>
        <button onClick={() => onNavigate("trigger")} style={{...btnStyle, border: "1px solid #4db8ff", color: "#4db8ff"}}>GATILLO</button>
        <button onClick={() => onNavigate("gap")} style={btnStyle}>GAP</button>
      </div>
    </div>
  );
}

const btnStyle = {
  background: "transparent", border: "1px solid #333", color: "#888",
  padding: "15px 40px", fontSize: "1.2rem", cursor: "pointer", borderRadius: "4px",
  transition: "all 0.3s"
};