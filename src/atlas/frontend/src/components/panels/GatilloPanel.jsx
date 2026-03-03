import React, { useEffect, useMemo, useState } from "react";
import { Card, Badge, Btn } from "../ui.jsx";
import { getGatilloConfig, setGatilloConfig, resetGatillo } from "../../utils/api.js";
import { symbolsForWorld } from "../../utils/symbols.js";

const TF_LIST = ["M1", "M3", "M5", "M15", "H1", "H4"];

function clampNum(x, fallback = 0) {
  const n = Number(x);
  return Number.isFinite(n) ? n : fallback;
}

export default function GatilloPanel({ snapshot, symbol, tf, setTf }) {
  const symbols = useMemo(() => symbolsForWorld("GATILLO"), []);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [cfg, setCfg] = useState(null);
  const [note, setNote] = useState("");

  const state = snapshot?.analysis?.state || "WAIT";
  const tone = state === "SIGNAL" ? "hot" : state === "WAIT_GATILLO" ? "OK" : "WAIT";

  // carga cfg backend
  useEffect(() => {
    let alive = true;
    async function boot() {
      try {
        setLoading(true);
        const r = await getGatilloConfig();
        if (!alive) return;
        setCfg(r);
        setTf(r.tf || "M5");
      } catch (e) {
        if (!alive) return;
        setNote(`No pude leer config: ${String(e)}`);
      } finally {
        if (!alive) return;
        setLoading(false);
      }
    }
    boot();
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onSave() {
    if (!cfg) return;
    setSaving(true);
    setNote("");
    try {
      const payload = {
        ...cfg,
        // normalizamos zona
        zone_low: clampNum(cfg.zone_low, 0),
        zone_high: clampNum(cfg.zone_high, 0),
        risk_pct: clampNum(cfg.risk_pct, 1),
        account_usd: clampNum(cfg.account_usd, 10000),
        tf: cfg.tf || tf,
        symbol: cfg.symbol || symbol,
      };
      const out = await setGatilloConfig(payload);
      setCfg(out.cfg);
      setTf(out.cfg.tf || "M5");
      setNote("Guardado OK ✅ (plan reiniciado por seguridad).");
    } catch (e) {
      setNote(`Error guardando: ${String(e)}`);
    } finally {
      setSaving(false);
    }
  }

  async function onReset() {
    setSaving(true);
    setNote("");
    try {
      const out = await resetGatillo();
      setCfg(out.cfg);
      setTf(out.cfg.tf || "M5");
      setNote("Reset OK ✅");
    } catch (e) {
      setNote(`Error reset: ${String(e)}`);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <Card title="GATILLO" subtitle="Cargando configuración..." right={<Badge tone="WAIT" text="WAIT" />}>
        <div style={{ fontSize: 12, opacity: 0.8 }}>Leyendo /api/gatillo/config…</div>
      </Card>
    );
  }

  const reseña = snapshot?.analysis?.reseña || "Reseña: esperando datos…";

  return (
    <Card
      title="GATILLO"
      subtitle="Zona manual + dirección + TF. ATLAS congela plan y espera 1 de 3 gatillos."
      right={<Badge tone={tone} text={state} />}
    >
      {/* Selector TF */}
      <div style={{ display: "grid", gap: 10 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ fontSize: 12, opacity: 0.8 }}>TF</div>
          <select
            value={cfg?.tf || "M5"}
            onChange={(e) => setCfg((p) => ({ ...p, tf: e.target.value }))}
            style={{
              padding: "8px 10px",
              borderRadius: 10,
              background: "rgba(255,255,255,0.06)",
              color: "#e5e7eb",
              border: "1px solid rgba(255,255,255,0.12)",
              outline: "none",
            }}
          >
            {TF_LIST.map((x) => (
              <option key={x} value={x} style={{ background: "#111827" }}>
                {x}
              </option>
            ))}
          </select>

          <div style={{ flex: 1 }} />

          {/* BUY/SELL */}
          <div style={{ display: "flex", gap: 8 }}>
            <Btn
              tone={cfg?.side === "BUY" ? "hot" : "ghost"}
              onClick={() => setCfg((p) => ({ ...p, side: "BUY" }))}
            >
              BUY
            </Btn>
            <Btn
              tone={cfg?.side === "SELL" ? "hot" : "ghost"}
              onClick={() => setCfg((p) => ({ ...p, side: "SELL" }))}
            >
              SELL
            </Btn>
          </div>
        </div>

        {/* Selector símbolo desplegable */}
        <div style={{ display: "grid", gap: 6 }}>
          <div style={{ fontSize: 12, opacity: 0.8 }}>Símbolo</div>
          <select
            value={cfg?.symbol || symbol}
            onChange={(e) => setCfg((p) => ({ ...p, symbol: e.target.value }))}
            style={{
              padding: "10px 12px",
              borderRadius: 12,
              background: "rgba(255,255,255,0.06)",
              color: "#e5e7eb",
              border: "1px solid rgba(255,255,255,0.12)",
              outline: "none",
            }}
          >
            {symbols.map((s) => (
              <option key={s} value={s} style={{ background: "#111827" }}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {/* Zona */}
        <div style={{ display: "grid", gap: 8 }}>
          <div style={{ fontSize: 12, opacity: 0.85, fontWeight: 900 }}>Zona manual (visual)</div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <div style={{ display: "grid", gap: 6 }}>
              <div style={{ fontSize: 12, opacity: 0.75 }}>Low</div>
              <input
                value={cfg?.zone_low ?? 0}
                onChange={(e) => setCfg((p) => ({ ...p, zone_low: e.target.value }))}
                placeholder="ej: 4994.96"
                style={{
                  padding: "10px 12px",
                  borderRadius: 12,
                  background: "rgba(255,255,255,0.06)",
                  color: "#e5e7eb",
                  border: "1px solid rgba(255,255,255,0.12)",
                  outline: "none",
                }}
              />
            </div>
            <div style={{ display: "grid", gap: 6 }}>
              <div style={{ fontSize: 12, opacity: 0.75 }}>High</div>
              <input
                value={cfg?.zone_high ?? 0}
                onChange={(e) => setCfg((p) => ({ ...p, zone_high: e.target.value }))}
                placeholder="ej: 5002.04"
                style={{
                  padding: "10px 12px",
                  borderRadius: 12,
                  background: "rgba(255,255,255,0.06)",
                  color: "#e5e7eb",
                  border: "1px solid rgba(255,255,255,0.12)",
                  outline: "none",
                }}
              />
            </div>
          </div>

          <div style={{ fontSize: 12, opacity: 0.7 }}>
            Tip: poné low/high y guardá. ATLAS pasa a <b>WAIT_GATILLO</b> y congela el plan.
          </div>
        </div>

        {/* Cuenta y riesgo */}
        <div style={{ display: "grid", gap: 8 }}>
          <div style={{ fontSize: 12, opacity: 0.85, fontWeight: 900 }}>Simulación de cuenta</div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <div style={{ display: "grid", gap: 6 }}>
              <div style={{ fontSize: 12, opacity: 0.75 }}>Account (USD)</div>
              <input
                value={cfg?.account_usd ?? 10000}
                onChange={(e) => setCfg((p) => ({ ...p, account_usd: e.target.value }))}
                style={{
                  padding: "10px 12px",
                  borderRadius: 12,
                  background: "rgba(255,255,255,0.06)",
                  color: "#e5e7eb",
                  border: "1px solid rgba(255,255,255,0.12)",
                  outline: "none",
                }}
              />
            </div>
            <div style={{ display: "grid", gap: 6 }}>
              <div style={{ fontSize: 12, opacity: 0.75 }}>Risk %</div>
              <input
                value={cfg?.risk_pct ?? 1}
                onChange={(e) => setCfg((p) => ({ ...p, risk_pct: e.target.value }))}
                style={{
                  padding: "10px 12px",
                  borderRadius: 12,
                  background: "rgba(255,255,255,0.06)",
                  color: "#e5e7eb",
                  border: "1px solid rgba(255,255,255,0.12)",
                  outline: "none",
                }}
              />
            </div>
          </div>
        </div>

        {/* Toggles de gatillos */}
        <div style={{ display: "grid", gap: 10 }}>
          <div style={{ fontSize: 12, opacity: 0.85, fontWeight: 900 }}>Gatillos habilitados</div>

          <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12, opacity: 0.9 }}>
            <input
              type="checkbox"
              checked={!!cfg?.use_touch_reject}
              onChange={(e) => setCfg((p) => ({ ...p, use_touch_reject: e.target.checked }))}
            />
            TOQUE + RECHAZO
          </label>

          <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12, opacity: 0.9 }}>
            <input
              type="checkbox"
              checked={!!cfg?.use_sweep_recover}
              onChange={(e) => setCfg((p) => ({ ...p, use_sweep_recover: e.target.checked }))}
            />
            BARRIDA + RECUPERACIÓN
          </label>

          <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12, opacity: 0.9 }}>
            <input
              type="checkbox"
              checked={!!cfg?.use_break_retest}
              onChange={(e) => setCfg((p) => ({ ...p, use_break_retest: e.target.checked }))}
            />
            RUPTURA + RETEST
          </label>
        </div>

        {/* Acciones */}
        <div style={{ display: "flex", gap: 10, marginTop: 6 }}>
          <Btn tone="hot" onClick={onSave} disabled={saving}>
            {saving ? "Guardando..." : "Guardar zona + plan"}
          </Btn>
          <Btn tone="ghost" onClick={onReset} disabled={saving}>
            Reset
          </Btn>
        </div>

        {/* Nota */}
        {note ? (
          <div style={{ fontSize: 12, opacity: 0.85, padding: "10px 12px", borderRadius: 12, background: "rgba(255,255,255,0.06)" }}>
            {note}
          </div>
        ) : null}

        {/* Reseña */}
        <div style={{ marginTop: 4, padding: "10px 12px", borderRadius: 12, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.10)" }}>
          <div style={{ fontWeight: 900, marginBottom: 6 }}>Reseña</div>
          <pre style={{ margin: 0, fontSize: 12, opacity: 0.85, whiteSpace: "pre-wrap" }}>{reseña}</pre>
        </div>
      </div>
    </Card>
  );
}
