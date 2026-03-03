import React, { useState, useEffect } from "react";

export default function ScenarioPanel({ currentParams, currentSymbol, currentTf, onLoadScenario }) {
  const [scenarios, setScenarios] = useState([]);
  const [newName, setNewName] = useState("");

  useEffect(() => {
    fetchScenarios();
  }, []);

  const fetchScenarios = async () => {
    try {
      const res = await fetch("/api/scenarios");
      if (res.ok) setScenarios(await res.json());
    } catch (e) { console.error(e); }
  };

  const handleSave = async () => {
    if (!newName.trim()) return;
    const payload = {
      name: newName,
      symbol: currentSymbol,
      tf: currentTf,
      params: currentParams,
      note: currentParams.note || ""
    };
    await fetch("/api/scenarios/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    setNewName("");
    fetchScenarios();
  };

  const handleDelete = async (name) => {
    if (!confirm("Delete scenario?")) return;
    await fetch("/api/scenarios/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name })
    });
    fetchScenarios();
  };

  return (
    <div style={{ border: "1px solid #2b2b2b", borderRadius: 10, padding: 12, background: "#111", marginTop: 20 }}>
      <div style={{ fontSize: 12, letterSpacing: 1, opacity: 0.8, marginBottom: 10 }}>ESCENARIOS</div>
      
      <div style={{ display: "flex", gap: 5, marginBottom: 10 }}>
        <input 
          value={newName} 
          onChange={e => setNewName(e.target.value)} 
          placeholder="Nombre escenario..." 
          style={{ flex: 1, background: "#0b0b0b", border: "1px solid #333", color: "#fff", padding: "5px 10px", borderRadius: 4 }}
        />
        <button onClick={handleSave} style={{ background: "#28a745", color: "#fff", border: "none", borderRadius: 4, padding: "0 10px", cursor: "pointer" }}>+</button>
      </div>

      <div style={{ maxHeight: 200, overflowY: "auto", display: "flex", flexDirection: "column", gap: 5 }}>
        {scenarios.map(s => (
          <div key={s.name} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#1a1a1a", padding: "6px 10px", borderRadius: 4 }}>
            <div 
              onClick={() => onLoadScenario(s)} 
              style={{ cursor: "pointer", flex: 1, fontSize: "0.9rem" }}
            >
              <span style={{ color: "#4db8ff", fontWeight: "bold" }}>{s.name}</span>
              <span style={{ fontSize: "0.75rem", color: "#666", marginLeft: 8 }}>{s.symbol} {s.tf}</span>
            </div>
            <button 
              onClick={() => handleDelete(s.name)}
              style={{ background: "transparent", border: "none", color: "#666", cursor: "pointer", fontSize: "0.8rem" }}
            >
              ✕
            </button>
          </div>
        ))}
        {scenarios.length === 0 && <div style={{ color: "#444", fontSize: "0.8rem", fontStyle: "italic" }}>Sin escenarios guardados</div>}
      </div>
    </div>
  );
}