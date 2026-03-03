// =========================
// FILE: src/atlas/frontend/src/components/ui.jsx
// (REEMPLAZAR COMPLETO)  -> FIX "Field" export
// =========================
import React from "react";

export function Card({ title, subtitle, right, children }) {
  return (
    <div style={{
      border: "1px solid rgba(255,255,255,0.12)",
      borderRadius: 16,
      padding: 14,
      background: "rgba(0,0,0,0.35)",
      backdropFilter: "blur(6px)",
    }}>
      {(title || subtitle || right) && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, marginBottom: 10 }}>
          <div>
            {title && <div style={{ fontWeight: 700, fontSize: 14 }}>{title}</div>}
            {subtitle && <div style={{ opacity: 0.75, fontSize: 12, marginTop: 2 }}>{subtitle}</div>}
          </div>
          {right && <div>{right}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

export function Badge({ text, tone = "OK" }) {
  const bg = tone === "RUN" ? "rgba(0,180,120,0.18)" : tone === "WAIT" ? "rgba(200,200,200,0.12)" : "rgba(80,140,255,0.18)";
  const bd = tone === "RUN" ? "rgba(0,180,120,0.35)" : tone === "WAIT" ? "rgba(200,200,200,0.25)" : "rgba(80,140,255,0.35)";
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      padding: "4px 10px",
      borderRadius: 999,
      border: `1px solid ${bd}`,
      background: bg,
      fontSize: 12,
      opacity: 0.95,
    }}>
      {text}
    </span>
  );
}

export function Input({ value, onChange, placeholder }) {
  return (
    <input
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
      placeholder={placeholder}
      style={{
        width: "100%",
        borderRadius: 12,
        border: "1px solid rgba(255,255,255,0.14)",
        background: "rgba(0,0,0,0.25)",
        color: "white",
        padding: "10px 12px",
        outline: "none",
      }}
    />
  );
}

export function Btn({ children, onClick, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        borderRadius: 12,
        border: "1px solid rgba(255,255,255,0.16)",
        background: disabled ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.10)",
        color: "white",
        padding: "10px 12px",
        cursor: disabled ? "not-allowed" : "pointer",
        width: "100%",
      }}
    >
      {children}
    </button>
  );
}

export function Select({ value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
      style={{
        width: "100%",
        borderRadius: 12,
        border: "1px solid rgba(255,255,255,0.14)",
        background: "rgba(0,0,0,0.25)",
        color: "white",
        padding: "10px 12px",
        outline: "none",
      }}
    >
      {(options || []).map((o) => (
        <option key={o.value} value={o.value} style={{ background: "#111" }}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

export function Field({ label, value, children }) {
  return (
    <div style={{ display: "grid", gap: 6 }}>
      {label && <div style={{ fontSize: 12, opacity: 0.8 }}>{label}</div>}
      {children ? children : (
        <div style={{
          borderRadius: 12,
          border: "1px solid rgba(255,255,255,0.12)",
          background: "rgba(0,0,0,0.18)",
          padding: "10px 12px",
          fontSize: 13,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}>
          {String(value ?? "")}
        </div>
      )}
    </div>
  );
}
