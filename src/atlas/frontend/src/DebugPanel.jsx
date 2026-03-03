import { useMemo, useState } from "react";

function fmt(v) {
  if (v === null || v === undefined) return "-";
  if (typeof v === "boolean") return v ? "true" : "false";
  return String(v);
}

export default function DebugPanel({ snapshot, world }) {
  const armed = Boolean(snapshot?.armed?.armed);
  const state = snapshot?.analysis?.state || snapshot?.analysis?.state_es || snapshot?.analysis?.state_key || "ESPERANDO";

  // Solo permitir armado cuando hay SEÑAL
  const canArm = String(state).toUpperCase().includes("SEÑAL") || String(state).toUpperCase().includes("SENAL");

  const [busy, setBusy] = useState(false);

  const reseña = useMemo(() => {
    // Si tu snapshot trae story/notes, lo mostramos. Si no, dejamos texto corto.
    const story = snapshot?.analysis?.story;
    if (story) return story;

    // fallback pro y corto
    const sym = snapshot?.symbol || "";
    const tf = snapshot?.tf || "";
    return `Fibo trazado sobre swing(60). Símbolo ${sym} (${tf}). Esperar gatillo en zona.`;
  }, [snapshot]);

  async function toggleArmed() {
    try {
      setBusy(true);
      await fetch("/api/armed/toggle", { method: "POST" });
      // No hacemos polling extra: el snapshot se actualizará solo con tu poll normal
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ borderRadius: 16, border: "1px solid rgba(255,255,255,0.10)", background: "rgba(255,255,255,0.03)", padding: 14 }}>
        <div style={{ fontWeight: 950, fontSize: 18 }}>Reseña</div>
        <div style={{ marginTop: 10, opacity: 0.9, fontSize: 13, lineHeight: 1.4, whiteSpace: "pre-wrap" }}>
          {reseña}
        </div>
      </div>

      <div style={{ borderRadius: 16, border: "1px solid rgba(255,255,255,0.10)", background: "rgba(255,255,255,0.03)", padding: 14 }}>
        <div style={{ fontWeight: 950, fontSize: 18 }}>Control</div>

        <div style={{ marginTop: 10, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <div>
            <div style={{ fontWeight: 900 }}>DEJAR CORRER</div>
            <div style={{ opacity: 0.7, fontSize: 12 }}>
              {canArm ? "Habilitado solo con SEÑAL." : "Bloqueado: solo se arma cuando hay SEÑAL."}
            </div>
          </div>

          <button
            onClick={toggleArmed}
            disabled={!canArm || busy}
            style={{
              padding: "10px 12px",
              borderRadius: 12,
              border: "1px solid rgba(255,255,255,0.10)",
              background: armed ? "rgba(34,197,94,0.22)" : "rgba(255,255,255,0.06)",
              color: "white",
              cursor: !canArm || busy ? "not-allowed" : "pointer",
              fontWeight: 950,
              minWidth: 140,
              opacity: !canArm || busy ? 0.5 : 1,
            }}
          >
            {armed ? "ARMED: ON" : "ARMED: OFF"}
          </button>
        </div>
      </div>

      <div style={{ borderRadius: 16, border: "1px solid rgba(255,255,255,0.10)", background: "rgba(255,255,255,0.03)", padding: 14 }}>
        <div style={{ fontWeight: 950, fontSize: 18 }}>Datos clave</div>

        <div style={{ marginTop: 10, display: "grid", gap: 10, fontSize: 13 }}>
          <Row k="world" v={snapshot?.world || world} />
          <Row k="atlas_mode" v={snapshot?.atlas_mode} />
          <Row k="symbol" v={snapshot?.symbol} />
          <Row k="tf" v={snapshot?.tf} />
          <Row k="estado" v={state} />
          <Row k="armed" v={armed} />
          <Row k="candles" v={`${Array.isArray(snapshot?.candles) ? snapshot.candles.length : 0}`} />
          <Row k="mt5.ok" v={snapshot?.mt5?.ok} />
          <Row k="mt5.last_error" v={JSON.stringify(snapshot?.mt5?.last_error || null)} />
        </div>
      </div>
    </div>
  );
}

function Row({ k, v }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: 8 }}>
      <div style={{ opacity: 0.75 }}>{k}</div>
      <div style={{ fontWeight: 900 }}>{fmt(v)}</div>
    </div>
  );
}
