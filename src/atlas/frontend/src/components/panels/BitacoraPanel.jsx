// src/atlas/frontend/src/components/panels/BitacoraPanel.jsx
import React, { useEffect, useMemo, useState } from "react";
import { Card, Badge, Btn } from "../ui.jsx";

const LS_KEY = "atlas_bitacora_v1";

function loadItems() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveItems(items) {
  localStorage.setItem(LS_KEY, JSON.stringify(items));
}

function nowStr() {
  return new Date().toLocaleString();
}

export default function BitacoraPanel({ snapshot }) {
  const [items, setItems] = useState(() => loadItems());
  const [note, setNote] = useState("");

  const row = snapshot?.ui?.rows?.[0] || null;

  // Auto-log cuando haya plan_id nuevo o cambio de action a “GATILLO”
  useEffect(() => {
    if (!snapshot) return;

    const action = snapshot?.analysis?.action || "WAIT";
    const planId = snapshot?.analysis?.plan_id || row?.plan_id || null;

    // clave única por “instante lógico”
    const key = `${snapshot?.world || "—"}|${snapshot?.symbol || "—"}|${snapshot?.tf || "—"}|${action}|${planId || "no_plan"}|${snapshot?.analysis?.plan_updated_ts_ms || snapshot?.ts_ms || Date.now()}`;

    // evita duplicar
    if (items.some((x) => x.key === key)) return;

    // guardamos solo cuando hay algo “registrable”
    const shouldLog =
      action === "WAIT_GATILLO" ||
      action === "SIGNAL" ||
      (row && (row.zone_low != null || row.entry != null));

    if (!shouldLog) return;

    const entry = {
      key,
      ts: Date.now(),
      when: nowStr(),
      world: snapshot?.world,
      symbol: snapshot?.symbol,
      tf: snapshot?.tf,
      action,
      reason: snapshot?.analysis?.reason || "—",
      text: row?.text || "—",
      side: row?.side || null,
      zone_low: row?.zone_low ?? null,
      zone_high: row?.zone_high ?? null,
      entry: row?.entry ?? null,
      sl: row?.sl ?? null,
      tp: row?.tp ?? null,
      lot: row?.lot ?? null,
      risk_pct: row?.risk_pct ?? null,
      account_usd: row?.account_usd ?? null,
      user_note: "",
    };

    const next = [entry, ...items].slice(0, 300); // límite razonable
    setItems(next);
    saveItems(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshot?.analysis?.action, snapshot?.analysis?.plan_id, snapshot?.analysis?.plan_updated_ts_ms, snapshot?.ts_ms]);

  const tone = useMemo(() => {
    const action = snapshot?.analysis?.action || "WAIT";
    if (action === "SIGNAL") return "OK";
    if (action === "WAIT_GATILLO") return "hot";
    return "WAIT";
  }, [snapshot]);

  function addNoteToLatest() {
    if (!items.length) return;
    const first = items[0];
    const updated = { ...first, user_note: (first.user_note ? first.user_note + "\n" : "") + note };
    const next = [updated, ...items.slice(1)];
    setItems(next);
    saveItems(next);
    setNote("");
  }

  function clearAll() {
    const next = [];
    setItems(next);
    saveItems(next);
  }

  return (
    <Card
      title="BITÁCORA"
      subtitle="Registro automático + reseña manual (queda guardado)."
      right={<Badge tone={tone} text="LIVE" />}
    >
      <div style={{ display: "grid", gap: 10 }}>
        <div style={{ display: "grid", gap: 8 }}>
          <div style={{ fontSize: 12, opacity: 0.8 }}>
            Último estado: <b>{snapshot?.analysis?.action || "—"}</b> • {snapshot?.analysis?.reason || "—"}
          </div>

          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Reseña del trade: SL / BE / parcial / lotaje / qué se analizó / qué se esperaba..."
            style={{
              width: "100%",
              minHeight: 90,
              padding: "10px 12px",
              borderRadius: 12,
              border: "1px solid rgba(255,255,255,0.12)",
              background: "rgba(255,255,255,0.04)",
              color: "#e5e7eb",
              outline: "none",
              resize: "vertical",
            }}
          />

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Btn tone="hot" onClick={addNoteToLatest}>Guardar reseña en el último registro</Btn>
            <Btn tone="ghost" onClick={clearAll}>Borrar bitácora</Btn>
          </div>
        </div>

        <div style={{ display: "grid", gap: 10 }}>
          {items.length === 0 ? (
            <div style={{ fontSize: 12, opacity: 0.75 }}>
              Aún no hay registros. Cuando el bot marque ZONA o GATILLO, se guardan solos.
            </div>
          ) : null}

          {items.map((it) => (
            <div
              key={it.key}
              style={{
                border: "1px solid rgba(255,255,255,0.10)",
                background: "rgba(255,255,255,0.04)",
                borderRadius: 14,
                padding: 12,
                display: "grid",
                gap: 8,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
                <div style={{ fontWeight: 900 }}>{it.symbol} • {it.tf}</div>
                <Badge
                  tone={it.action === "SIGNAL" ? "OK" : it.action === "WAIT_GATILLO" ? "hot" : "WAIT"}
                  text={it.action === "SIGNAL" ? "GATILLO" : it.action === "WAIT_GATILLO" ? "ZONA" : "WAIT"}
                />
              </div>

              <div style={{ fontSize: 12, opacity: 0.85 }}>
                <b>{it.when}</b> • {it.reason}
              </div>

              <div style={{ fontSize: 12, opacity: 0.9 }}>
                <b>Texto:</b> {it.text}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, fontSize: 12 }}>
                <div>
                  <b>Side:</b> {it.side || "—"} <br />
                  <b>Zona:</b> {it.zone_low ?? "—"} → {it.zone_high ?? "—"}
                </div>
                <div>
                  <b>Entry:</b> {it.entry ?? "—"} <br />
                  <b>SL:</b> {it.sl ?? "—"} • <b>TP:</b> {it.tp ?? "—"}
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, fontSize: 12, opacity: 0.95 }}>
                <div>
                  <b>Cuenta:</b> {it.account_usd ?? "—"} <br />
                  <b>Riesgo %:</b> {it.risk_pct ?? "—"}
                </div>
                <div>
                  <b>Lotaje:</b> {it.lot ?? "—"}
                </div>
              </div>

              {it.user_note ? (
                <div style={{ fontSize: 12, whiteSpace: "pre-wrap", opacity: 0.95 }}>
                  <b>Reseña:</b>{"\n"}{it.user_note}
                </div>
              ) : (
                <div style={{ fontSize: 12, opacity: 0.6 }}>
                  (Sin reseña aún)
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
