import React from "react";
import Charts from "./Charts";

export default function GapView({ onBack }) {
  const [snap, setSnap] = useState(null);
  const [paramsDraft, setParamsDraft] = useState({});

  useEffect(() => {
    // Force XAUUSD config on mount
    fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: "XAUUSD", tf_exec: "M1" }),
    });

    const interval = setInterval(() => {
      fetch("/api/snapshot")
        .then(r => r.json())
        .then(d => setSnap(d))
        .catch(e => console.error(e));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Load GAP params
  useEffect(() => {
    fetch("/api/params/get?symbol=XAUUSD&tf=GAP")
      .then(r => r.json())
      .then(p => setParamsDraft(p || {}));
  }, []);

  const handleSaveParams = async () => {
    await fetch("/api/params/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: "XAUUSD", tf: "GAP", params: paramsDraft }),
    });
  };

  const gapState = snap?.gap_state || { active: false, valid: false };

  return (
    <div style={{ background: "#000", minHeight: "100vh", padding: 20, color: "#ccc", fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 20 }}>
        <button onClick={onBack} style={{ background: "transparent", border: "none", color: "#666", cursor: "pointer", fontSize: "1.2rem" }}>←</button>
        <h2 style={{ margin: 0, color: "#e6b800" }}>MODO GAP (GOLD ONLY)</h2>
      </div>
      
      <div style={{ display: "grid", gridTemplateColumns: "3fr 1fr", gap: 20 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ border: "1px solid #333", background: "#0b0c0e" }}>
            <Charts candles={snap?.candles || []} symbol="XAUUSD" />
          </div>
          
          {/* SEMAFORO GAP */}
          <div style={{ display: "flex", gap: 10, padding: 15, background: "#111", borderRadius: 8, alignItems: "center" }}>
             <div style={{ width: 20, height: 20, borderRadius: "50%", background: gapState.active ? (gapState.valid ? "#52c41a" : "#faad14") : "#333" }}></div>
             <div style={{ fontWeight: "bold" }}>ESTADO: {gapState.active ? (gapState.valid ? "VALID GAP" : "WAITING") : "NO GAP"}</div>
             <div style={{ marginLeft: "auto", color: "#888" }}>{gapState.details?.gap_size ? `Size: ${gapState.details.gap_size}` : ""}</div>
          </div>
        </div>

        <div style={{ border: "1px solid #e6b800", borderRadius: 10, padding: 12, background: "#111", height: "fit-content" }}>
          <div style={{ fontSize: 12, letterSpacing: 1, opacity: 0.8, marginBottom: 10, color: "#e6b800" }}>GAP PARAMETERS</div>
          
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
            <Input label="ENTRY" val={paramsDraft.entry} set={v => setParamsDraft({...paramsDraft, entry: v})} />
            <Input label="SL" val={paramsDraft.sl} set={v => setParamsDraft({...paramsDraft, sl: v})} />
          </div>
          <div style={{ marginBottom: 10 }}>
             <Input label="TP1" val={paramsDraft.tp} set={v => setParamsDraft({...paramsDraft, tp: v})} />
          </div>

          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 10, color: "#666", marginBottom: 4 }}>NOTA</div>
            <textarea 
              value={paramsDraft.note || ""} 
              onChange={e => setParamsDraft({...paramsDraft, note: e.target.value})}
              style={{ width: "100%", background: "#0b0b0b", border: "1px solid #333", color: "#fff", padding: 8, borderRadius: 4, minHeight: 60 }}
            />
          </div>

          <button onClick={handleSaveParams} style={{ width: "100%", background: "#e6b800", color: "#000", border: "none", padding: "10px", borderRadius: 4, cursor: "pointer", fontWeight: "bold" }}>
            GUARDAR GAP
          </button>
        </div>
      </div>
    </div>
  );
}

const Input = ({ label, val, set }) => (
  <div>
    <div style={{ fontSize: 10, color: "#666", marginBottom: 4 }}>{label}</div>
    <input 
      value={val || ""} 
      onChange={e => set(e.target.value)} 
      style={{ width: "100%", background: "#0b0b0b", border: "1px solid #333", color: "#fff", padding: "6px 8px", borderRadius: 4 }}
    />
  </div>
);