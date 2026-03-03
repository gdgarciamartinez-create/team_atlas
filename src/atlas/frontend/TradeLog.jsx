import { useEffect, useMemo, useState } from "react";

function nowISO() {
  const d = new Date();
  return d.toISOString();
}

function toCSV(rows) {
  const header = ["time", "world", "symbol", "result", "R", "idea", "note"];
  const lines = [header.join(",")];

  for (const r of rows) {
    const values = header.map(k => {
      const v = (r[k] ?? "").toString().replaceAll('"', '""');
      return `"${v}"`;
    });
    lines.push(values.join(","));
  }
  return lines.join("\n");
}

export default function TradeLog({ defaultWorld, defaultSymbol }) {
  const KEY = "atlas_tradelog_v1";

  const [rows, setRows] = useState([]);
  const [world, setWorld] = useState(defaultWorld || "GATILLO");
  const [symbol, setSymbol] = useState(defaultSymbol || "XAUUSDz");
  const [result, setResult] = useState("WAIT"); // TRADE/NO_TRADE/WAIT/ERROR
  const [R, setR] = useState("");
  const [idea, setIdea] = useState("");
  const [note, setNote] = useState("");

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) setRows(JSON.parse(raw));
    } catch {}
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(rows));
    } catch {}
  }, [rows]);

  useEffect(() => {
    setWorld(defaultWorld || "GATILLO");
  }, [defaultWorld]);

  useEffect(() => {
    setSymbol(defaultSymbol || "XAUUSDz");
  }, [defaultSymbol]);

  const last5 = useMemo(() => rows.slice(0, 5), [rows]);

  function addRow() {
    const row = {
      time: nowISO(),
      world,
      symbol,
      result,
      R,
      idea,
      note
    };
    setRows([row, ...rows]);
    setR("");
    setIdea("");
    setNote("");
  }

  function exportCSV() {
    const csv = toCSV(rows);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "atlas_tradelog.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function clearAll() {
    if (!confirm("Borrar toda la bitácora?")) return;
    setRows([]);
  }

  return (
    <div style={{
      marginTop: 6,
      borderRadius: 14,
      border: "1px solid rgba(255,255,255,0.08)",
      background: "rgba(0,0,0,0.20)",
      padding: 12
    }}>
      <div style={{ fontWeight: 900, marginBottom: 8 }}>Bitácora</div>

      <div style={{ display: "grid", gap: 8 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <input
            value={world}
            onChange={(e) => setWorld(e.target.value)}
            placeholder="Mundo"
            style={{
              padding: 10, borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.10)",
              background: "rgba(255,255,255,0.04)", color: "white"
            }}
          />
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="Símbolo"
            style={{
              padding: 10, borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.10)",
              background: "rgba(255,255,255,0.04)", color: "white"
            }}
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 90px", gap: 8 }}>
          <select
            value={result}
            onChange={(e) => setResult(e.target.value)}
            style={{
              padding: 10, borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.10)",
              background: "rgba(255,255,255,0.04)", color: "white"
            }}
          >
            <option>TRADE</option>
            <option>WAIT</option>
            <option>NO_TRADE</option>
            <option>ERROR</option>
          </select>

          <input
            value={R}
            onChange={(e) => setR(e.target.value)}
            placeholder="R"
            style={{
              padding: 10, borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.10)",
              background: "rgba(255,255,255,0.04)", color: "white"
            }}
          />
        </div>

        <input
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          placeholder="Idea (setup / contexto / objetivo)"
          style={{
            padding: 10, borderRadius: 10,
            border: "1px solid rgba(255,255,255,0.10)",
            background: "rgba(255,255,255,0.04)", color: "white"
          }}
        />
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Nota (qué pasó / por qué / aprendizaje)"
          style={{
            padding: 10, borderRadius: 10,
            border: "1px solid rgba(255,255,255,0.10)",
            background: "rgba(255,255,255,0.04)", color: "white"
          }}
        />

        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={addRow} style={{
            flex: 1,
            padding: 10,
            borderRadius: 12,
            border: "1px solid rgba(255,255,255,0.12)",
            background: "rgba(34,197,94,0.18)",
            color: "white",
            fontWeight: 900,
            cursor: "pointer"
          }}>
            Guardar
          </button>

          <button onClick={exportCSV} style={{
            padding: 10,
            borderRadius: 12,
            border: "1px solid rgba(255,255,255,0.12)",
            background: "rgba(59,130,246,0.18)",
            color: "white",
            fontWeight: 900,
            cursor: "pointer"
          }}>
            CSV
          </button>

          <button onClick={clearAll} style={{
            padding: 10,
            borderRadius: 12,
            border: "1px solid rgba(255,255,255,0.12)",
            background: "rgba(239,68,68,0.18)",
            color: "white",
            fontWeight: 900,
            cursor: "pointer"
          }}>
            Borrar
          </button>
        </div>

        <div style={{ opacity: 0.65, fontSize: 12 }}>
          Últimos 5 registros:
        </div>

        <div style={{ display: "grid", gap: 6 }}>
          {last5.length === 0 && (
            <div style={{ opacity: 0.6, fontSize: 12 }}>Vacía todavía.</div>
          )}
          {last5.map((r, i) => (
            <div key={i} style={{
              padding: 10,
              borderRadius: 12,
              border: "1px solid rgba(255,255,255,0.08)",
              background: "rgba(255,255,255,0.03)"
            }}>
              <div style={{ fontWeight: 900, fontSize: 12 }}>
                {r.symbol} • {r.result} • R={r.R || "-"}
              </div>
              <div style={{ opacity: 0.7, fontSize: 12 }}>
                {r.world} • {r.time}
              </div>
              {r.idea ? <div style={{ marginTop: 6, fontSize: 12 }}>{r.idea}</div> : null}
              {r.note ? <div style={{ marginTop: 4, fontSize: 12, opacity: 0.85 }}>{r.note}</div> : null}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}