import React, { useState, useEffect } from "react";
import Charts from "./Charts";

const SYMBOLS = [
  "XAUUSD", "USOIL", "NAS100",
  "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF",
  "EURJPY", "EURGBP", "EURAUD", "EURNZD", "EURCAD", "EURCHF",
  "GBPJPY", "GBPAUD", "GBPNZD", "GBPCAD", "GBPCHF",
  "AUDJPY", "AUDNZD", "AUDCAD", "AUDCHF",
  "NZDJPY", "NZDCAD", "NZDCHF",
  "CADJPY", "CADCHF", "CHFJPY"
];

export default function TriggerView({ onBack }) {
  const [snap, setSnap] = useState(null);
  const [paramsDraft, setParamsDraft] = useState({});
  const [scenarios, setScenarios] = useState([]);

  // Polling
  useEffect(() => {
    const interval = setInterval(() => {
      fetch("/api/snapshot")
        .then(r => r.json())
        .then(d => setSnap(d))
        .catch(e => console.error(e));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Sync params from snapshot initially
  useEffect(() => {
    if (snap?.params && Object.keys(paramsDraft).length === 0) {
      setParamsDraft(snap.params);
    }
    if (snap?.config?.symbol && !symbol) setSymbol(snap.config.symbol);
  }, [snap]); // eslint-disable-line

  const handleSaveConfig = async (newSym, newTf) => {
    await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: newSym || symbol, tf_exec: newTf || tf }),
    });
  };

  const handleSaveParams = async () => {
    await fetch("/api/params", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ params: paramsDraft }),
    });
  };

  const loadScenario = (scen) => {
    setSymbol(scen.symbol);
    setTf(scen.tf);
    setParamsDraft(scen.params);
    handleSaveConfig(scen.symbol, scen.tf);
    // Also save params to backend so snapshot updates
    fetch("/api/params", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ params: scen.params }),
    });
  };

  return (
    <div style={{ padding: 20, background: "#000", minHeight: "100vh", color: "#ccc", fontFamily: "sans-serif" }}>
      {/* HEADER */}
      <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 20, background: "#111", padding: 10, borderRadius: 6 }}>
        <button onClick={onBack} style={{ background: "transparent", border: "none", color: "#666", cursor: "pointer", fontSize: "1.2rem" }}>←</button>
        <div style={{ fontWeight: "bold", color: "#fff" }}>MODO GATILLO</div>
        
        <div style={{ height: 20, width: 1, background: "#333" }}></div>

        <select value={symbol} onChange={e => { setSymbol(e.target.value); handleSaveConfig(e.target.value, tf); }} style={selStyle}>
          {SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <select value={tf} onChange={e => { setTf(e.target.value); handleSaveConfig(symbol, e.target.value); }} style={selStyle}>
          <option value="M1">M1</option>
          <option value="M3">M3</option>
          <option value="M5">M5</option>
        </select>

        <div style={{ marginLeft: "auto", fontSize: "0.8rem", color: "#666" }}>
          Tick: {snap?.status?.tick}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "3fr 1fr", gap: 20 }}>
        {/* LEFT: CHARTS */}
        <div style={{ border: "1px solid #333", background: "#0b0c0e" }}>
          <Charts candles={snap?.candles || []} symbol={symbol} />
        </div>

        {/* RIGHT: PARAMS & SCENARIOS */}
        <div>
          {/* PARAMS PANEL */}
          <div style={{ border: "1px solid #2b2b2b", borderRadius: 10, padding: 12, background: "#111" }}>
            <div style={{ fontSize: 12, letterSpacing: 1, opacity: 0.8, marginBottom: 10 }}>SETUP PARAMETERS</div>
            
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
              <Input label="ZONA LOW" val={paramsDraft.zone_low} set={v => setParamsDraft({...paramsDraft, zone_low: v})} />
              <Input label="ZONA HIGH" val={paramsDraft.zone_high} set={v => setParamsDraft({...paramsDraft, zone_high: v})} />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 10 }}>
              <Input label="ENTRY" val={paramsDraft.entry} set={v => setParamsDraft({...paramsDraft, entry: v})} />
              <Input label="SL" val={paramsDraft.sl} set={v => setParamsDraft({...paramsDraft, sl: v})} />
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

            <div style={{ display: "flex", gap: 10 }}>
              <button onClick={handleSaveParams} style={btnSaveStyle}>GUARDAR PARÁMETROS</button>
              <button onClick={() => setParamsDraft(snap?.params || {})} style={btnResetStyle}>RESET</button>
            </div>
          </div>

          {/* SCENARIOS PANEL */}
          <ScenarioPanel 
            currentParams={paramsDraft} 
            currentSymbol={symbol} 
            currentTf={tf} 
            onLoadScenario={loadScenario} 
          />
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

const selStyle = {
  background: "#222", color: "#fff", border: "1px solid #444", padding: "5px 10px", borderRadius: 4
};

const btnSaveStyle = {
  flex: 1, background: "#1b5cff", color: "#fff", border: "none", padding: "8px", borderRadius: 4, cursor: "pointer", fontWeight: "bold", fontSize: "0.8rem"
};

const btnResetStyle = {
  background: "#222", color: "#ccc", border: "none", padding: "8px 12px", borderRadius: 4, cursor: "pointer", fontSize: "0.8rem"
};