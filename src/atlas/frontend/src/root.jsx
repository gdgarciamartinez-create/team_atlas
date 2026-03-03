// src/atlas/frontend/src/Root.jsx
import React, { useMemo, useState, Suspense } from "react";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, err: null };
  }
  static getDerivedStateFromError(err) {
    return { hasError: true, err };
  }
  componentDidCatch(err, info) {
    console.error("💥 UI CRASH:", err, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 24, background: "#0b1220", color: "#e5e7eb", minHeight: "100vh", fontFamily: "system-ui" }}>
          <h2 style={{ margin: 0 }}>💥 React se cayó (capturado)</h2>
          <p style={{ opacity: 0.85 }}>
            Esto ya no debería quedar “blanco”. Copiá y pegá este error.
          </p>
          <pre style={{ whiteSpace: "pre-wrap", background: "rgba(255,255,255,0.06)", padding: 12, borderRadius: 12 }}>
            {String(this.state.err?.stack || this.state.err)}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function Root() {
  // ✅ Si esto se ve, React montó sí o sí
  const [loadApp, setLoadApp] = useState(true);

  // Lazy import de App: si App rompe en imports/exports, lo capturamos acá
  const AppLazy = useMemo(() => React.lazy(() => import("./App.jsx")), []);

  return (
    <div style={{ background: "#0b1220", minHeight: "100vh", color: "#e5e7eb", fontFamily: "system-ui" }}>
      <div style={{ padding: 18, borderBottom: "1px solid rgba(255,255,255,0.08)", background: "rgba(0,0,0,0.25)" }}>
        <div style={{ fontWeight: 950, fontSize: 22 }}>TEAM ATLAS ✅</div>
        <div style={{ opacity: 0.8, marginTop: 6 }}>
          Si ves esto, <b>React montó</b>. Si App rompe, lo vas a ver abajo (no blanco).
        </div>

        <div style={{ marginTop: 12, display: "flex", gap: 10 }}>
          <button
            onClick={() => setLoadApp(true)}
            style={{
              padding: "10px 14px",
              borderRadius: 12,
              border: "1px solid rgba(255,255,255,0.12)",
              background: loadApp ? "rgba(34,197,94,0.18)" : "rgba(255,255,255,0.06)",
              color: "#e5e7eb",
              cursor: "pointer",
              fontWeight: 900,
            }}
          >
            ON: Cargar App
          </button>

          <button
            onClick={() => setLoadApp(false)}
            style={{
              padding: "10px 14px",
              borderRadius: 12,
              border: "1px solid rgba(255,255,255,0.12)",
              background: !loadApp ? "rgba(239,68,68,0.18)" : "rgba(255,255,255,0.06)",
              color: "#e5e7eb",
              cursor: "pointer",
              fontWeight: 900,
            }}
          >
            OFF: Solo diagnóstico
          </button>
        </div>
      </div>

      <div style={{ padding: 18 }}>
        {!loadApp ? (
          <div style={{ opacity: 0.85 }}>
            App está en OFF. Si esto se ve, el blanco era por App/imports.
          </div>
        ) : (
          <ErrorBoundary>
            <Suspense
              fallback={
                <div style={{ opacity: 0.85 }}>
                  Cargando App…
                </div>
              }
            >
              <AppLazy />
            </Suspense>
          </ErrorBoundary>
        )}
      </div>
    </div>
  );
}
