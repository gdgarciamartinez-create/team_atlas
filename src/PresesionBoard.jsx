import React, { useEffect, useState } from "react";
import { getPresesionBoard } from "./api";

const COLORS = {
  red: "#ff4d4f",
  yellow: "#faad14",
  green: "#52c41a",
};

export default function PresesionBoard() {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    const fetchBoard = async () => {
      try {
        const data = await getPresesionBoard();
        setItems(data);
      } catch (e) {
        console.error("Presesion fetch error:", e);
      }
    };
    fetchBoard();
    const id = setInterval(fetchBoard, 5000); // Polling 5s
    return () => clearInterval(id);
  }, []);

  return (
    <div style={{ 
      background: "#141414", 
      color: "#e0e0e0", 
      padding: 12, 
      borderRadius: 4,
      border: "1px solid #333",
      fontFamily: "Consolas, monospace",
      height: "100%",
      overflowY: "auto"
    }}>
      <h3 style={{ 
        marginTop: 0, 
        marginBottom: 12, 
        borderBottom: "1px solid #333", 
        paddingBottom: 8,
        fontSize: "1rem",
        textTransform: "uppercase",
        letterSpacing: "1px",
        color: "#888"
      }}>
        Pared de Presesion
      </h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {items.length === 0 && <div style={{color: "#666"}}>Cargando datos...</div>}
        {items.map((item) => (
          <div
            key={item.symbol}
            onClick={() => setSelected(item.symbol)}
            style={{
              display: "grid",
              gridTemplateColumns: "60px 20px 50px 1fr",
              alignItems: "center",
              padding: "6px 8px",
              background: selected === item.symbol ? "#2a2a2a" : "#1a1a1a",
              cursor: "pointer",
              borderLeft: `3px solid ${COLORS[item.light] || "#333"}`,
              fontSize: "0.85rem"
            }}
          >
            {/* Símbolo */}
            <div style={{ fontWeight: "bold", color: "#fff" }}>{item.symbol}</div>

            {/* Semáforo (Visual) */}
            <div style={{ display: "flex", justifyContent: "center" }}>
               <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: COLORS[item.light] || "#555",
                  boxShadow: `0 0 6px ${COLORS[item.light] || "transparent"}`
                }}
              />
            </div>
            
            
            {/* Bias */}
            <div style={{ 
              color: item.bias === "buy" ? "#52c41a" : item.bias === "sell" ? "#ff4d4f" : "#666",
              fontWeight: "bold",
              fontSize: "0.8rem"
            }}>
              {item.bias === "none" ? "-" : item.bias.toUpperCase()}
            </div>
            
            {/* Nota */}
            <div style={{ 
              opacity: 0.7, 
              whiteSpace: "nowrap", 
              overflow: "hidden", 
              textOverflow: "ellipsis",
              color: "#aaa"
            }}>
              {item.note}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}