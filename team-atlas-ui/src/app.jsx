import React, { useEffect, useState } from "react";

export default function App() {
  const [health, setHealth] = useState("probando...");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => setHealth(JSON.stringify(d, null, 2)))
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div style={{ fontFamily: "sans-serif", padding: 20 }}>
      <h1>TEAM ATLAS UI</h1>

      <p>
        Backend (via proxy): <b>/api</b>
      </p>

      <div style={{ padding: 12, border: "1px solid #333", borderRadius: 10 }}>
        <h3>Health</h3>
        {error ? (
          <pre style={{ color: "tomato" }}>{error}</pre>
        ) : (
          <pre>{health}</pre>
        )}
      </div>
    </div>
  );
}
