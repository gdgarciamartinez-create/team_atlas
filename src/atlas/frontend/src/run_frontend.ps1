import { useMemo } from "react";

function fmt(v) {
  if (v === null || v === undefined) return "-";
  if (typeof v === "boolean") return v ? "true" : "false";
  return String(v);
}

function LightPill({ on, label, hint }) {
  return (
    <div
      style={{
        display: "flex",
        gap: 10,
        alignItems: "center",
        padding: "10px 12px",
        borderRadius: 12,
        border: "1px solid rgba(255,255,255,0.10)",
        background: "rgba(255,255,255,0.03)",
      }}
    >
      <div
        style={{
          width: 12,
          height: 12,
          borderRadius: 999,
          background: on ? "#60a5fa" : "rgba(255,255,255,0.12)",
          boxShadow: on ? "0 0 18px rgba(96,165,250,0.7)" : "none",
        }}
      />
      <div style={{ fontWeight: 950 }}>
        {label} <span style={{ opacity: 0.7, fontWeight: 700 }}>{on ? "ON" : "OFF"}</span>
      </div>
      <div style={{ marginLeft: "auto", opacity: 0.7, fontSize: 12 }}>{hint}</div>
    </div>
  );
}

export default function DebugPanel({ snapshot, world }) {
  const state =
    snapshot?.analysis?.state ||
    snapshot?.analysis?.state_es ||
    snapshot?.analysis?.state_key ||
    "ESPERANDO";

  // ✅ Dejar correr = decisión IA (run_hint)
  const runHint = Boolean(snapshot?.analysis?.run_hint);

  // ✅ Armed es otra cosa: estado de ejecución futura por símbolo (informativo)
  const armed = Boolean(snapshot?.armed?.armed);
  const clan = snapshot?.armed?.clan || "-";

  const reseña = useMemo(() => {
    // 1) Si ya viene story, lo usamos.
    const story = snapshot?.analysis?.story;
    if (story) return story;

    // 2) Reseña corta y contundente, como pediste
    const sym = snapshot?.symbol || "";
    const tf = snapshot?.tf || "";
    const side = snapshot?.analysis?.side || "-";
    const plan = snapshot?.analysis?.plan || {};
    const zl = plan?.zone_low;
    const zh = plan?.zone_high;
    const inv = plan?.invalidation;

    const zoneTxt =
      zl !== undefined && zh !== undefined
        ? `Zona/POI ${zl}–${zh}`
        : `Zona/POI (pendiente)`;

    const invTxt = inv !== undefined ? `Invalidación ${inv}` : `Invalidación (pendiente)`;

    return `Fibo trazado sobre swing(60). ${zoneTxt}. Sesgo: ${side}. Estado: ${state}. ${invTxt}. Esperar gatillo en zona.`;
  }, [snapshot, state]);

  return (
    <div style={{ display: "grid", gap: 14 }}>
      {/* Reseña */}
      <div
        style={{
          borderRadius: 16,
          border: "1px solid rgba(255,255,255,0.10)",
          background: "rgba(255,255,255,0.03)",
          padding: 14,
        }}
      >
        <div style={{ fontWeight: 950, fontSize: 18 }}>Reseña</div>
        <div style={{ marginTop: 10, opacity: 0.9, fontSize: 13, lineHeight: 1.4, whiteSpace: "pre-wrap" }}>
          {reseña}
        </div>
      </div>

      {/* Control (IA, no humano) */}
      <div
        style={{
          borderRadius: 16,
          border: "1px solid rgba(255,255,255,0.10)",
          background: "rgba(255,255,255,0.03)",
          padding: 14,
        }}
      >
        <div style={{ fontWeight: 950, fontSize: 18 }}>Control</div>

        <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
          {/* ✅ DEJAR CORRER = run_hint */}
          <LightPill
            on={runHint}
            label="DEJAR CORRER"
            hint="(decisión IA)"
          />

          {/* ✅ ARMED informativo (no clickable) */}
          <LightPill
            on={armed}
            label={`ARMED (${clan})`}
            hint="(ejecución futura)"
          />

          <div style={{ opacity: 0.7, fontSize: 12 }}>
            Nota: “DEJAR CORRER” lo activa la IA (run_hint). No hay botón manual.
          </div>
        </div>
      </div>

      {/* Datos clave */}
      <div
        style={{
          borderRadius: 16,
          border: "1px solid rgba(255,255,255,0.10)",
          background: "rgba(255,255,255,0.03)",
          padding: 14,
        }}
      >
        <div style={{ fontWeight: 950, fontSize: 18 }}>Datos clave</div>

        <div style={{ marginTop: 10, display: "grid", gap: 10, fontSize: 13 }}>
          <Row k="world" v={snapshot?.world || world} />
          <Row k="atlas_mode" v={snapshot?.atlas_mode} />
          <Row k="symbol" v={snapshot?.symbol} />
          <Row k="tf" v={snapshot?.tf} />
          <Row k="estado" v={state} />
          <Row k="run_hint (IA)" v={runHint} />
          <Row k="armed (futuro)" v={armed} />
          <Row k="clan" v={clan} />
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
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        gap: 12,
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        paddingBottom: 8,
      }}
    >
      <div style={{ opacity: 0.75 }}>{k}</div>
      <div style={{ fontWeight: 900 }}>{fmt(v)}</div>
    </div>
  );
}
